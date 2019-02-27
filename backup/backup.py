#!/usr/bin/env python3

import sys
import os
import libvirt
import datetime
import tempfile
import shutil
import subprocess
import json
import math

#Modified version of tarfile
import tarfileProg

BUF_SIZE = 16*1024
SPACE_PADDING = ' ' * 40

def fail(message: str, code: int):
    print(message)
    exit(code)

def printNoNL(msg: str):
    sys.stdout.write(msg)
    sys.stdout.flush()

def getListOfFilesForDisk(conn: libvirt.virConnect,dom: libvirt.virDomain, disk:str):
    stats = conn.domainListGetStats([dom], libvirt.VIR_DOMAIN_STATS_BLOCK, libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_BACKING)[0][1]
    result = []
    for i in range(0, stats['block.count']):
        if(stats['block.' + str(i) + '.name'] == disk):
            result.append(stats['block.' + str(i) + '.path'])
    return result

def copyFile(file_to_copy: str, write_dir: str):
    base_msg = " Copying file " + file_to_copy
    printNoNL(base_msg + ".")
    size = os.path.getsize(file_to_copy)
    fsrc = open(file_to_copy, 'rb')
    dest_file = os.path.join(write_dir, os.path.join('root', file_to_copy[1:]))
    dest_folder = os.path.dirname(dest_file)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    fdst = open(dest_file, 'wb')
    copied = 0
    while True:
        buf = fsrc.read(BUF_SIZE)
        if not buf:
            break
        fdst.write(buf)
        copied += len(buf)
        message = ('\r' + base_msg + ': {:.2%}' + SPACE_PADDING).format(copied/size)
        printNoNL(message)
    print("\r" + base_msg + ". Done." + SPACE_PADDING)

def backupDisk(conn: libvirt.virConnect, dom: libvirt.virDomain, disk:str, write_dir:str):
    print("##Start backing up " + disk + "##")
    tmpDir = tempfile.mkdtemp(prefix="backup_tmp_")
    
    printNoNL(" Creating snapshot. ")
    #Should be done properly with bindings, but can't be bothered to research how the XML needs to look right now.
    new_snapshot_path = tmpDir + '/' + disk + '.qcow2'
    subprocess.run(['virsh', 'snapshot-create-as', '--no-metadata', '--domain', dom.name(), '--diskspec', 
                    disk + ',file=' + new_snapshot_path, '--disk-only', '--atomic'], stdout=subprocess.PIPE)
    print("Done.")
    
    files_to_copy = getListOfFilesForDisk(conn, dom, disk)
    for file_to_copy in files_to_copy:
        if file_to_copy != new_snapshot_path:
            copyFile(file_to_copy, write_dir)

    printNoNL(" Block committing snapshot back.")
    dom.blockCommit(disk, None, None, flags=libvirt.VIR_DOMAIN_BLOCK_COMMIT_SHALLOW | libvirt.VIR_DOMAIN_BLOCK_COMMIT_ACTIVE)
    while True:
        info = dom.blockJobInfo(disk)
        cur = info["cur"]
        end = info["end"]
        if cur >= end:
            break
        message = ('\r Block committing snapshot back: {:.2%}' + SPACE_PADDING).format(cur/end)
        printNoNL(message)
    printNoNL("\r Block committing snapshot back: Finishing." + SPACE_PADDING)
    dom.blockJobAbort(disk, flags=libvirt.VIR_DOMAIN_BLOCK_JOB_ABORT_PIVOT | libvirt.VIR_DOMAIN_BLOCK_JOB_ABORT_ASYNC)
    print("\r Block committing snapshot back. Done." + SPACE_PADDING)
    
    printNoNL(" Cleaning up. ")
    shutil.rmtree(tmpDir)
    print("Done.")

    print("##Done backing up " + disk + "##")

def get_dir_size(dir: str):
    size = 0
    for dirpath, _, filenames in os.walk(dir):
        for f in filenames:
            size += os.path.getsize(os.path.join(dir, os.path.join(dirpath, f)))
    return size

def print_tar_progress(size: int, full_size: int, base_msg: str):
    msg = ('\r' + base_msg + ': {:.2%}' + SPACE_PADDING).format(size / full_size)
    printNoNL(msg)


if len(sys.argv) < 3:
    fail("To few arguments.", 101)

domName = sys.argv[1]
backupDir = sys.argv[2]

conn = libvirt.open()
if conn == None:
    fail('Failed to open connection to the hypervisor', 102)

try:
    dom = conn.lookupByName(domName)
except:
    conn.__del__()
    fail('Failed to find the domain ' + domName, 1)

diskNames = []
for i in range(3,len(sys.argv)):
    diskName = sys.argv[i]
    try:
        dom.blockInfo(diskName)
    except:
        dom.__del__()
        conn.__del__()
        fail("Failed to find the block device " + diskName + " of domain " + domName, 103)
    diskNames.append(diskName)

time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
backup_name = "backup_" + dom.name() + "_" + time
backup_file_name = backup_name + ".tar.gz"
backup_file = backupDir + backup_file_name
backup_tmp_dir = tempfile.mkdtemp(prefix=backup_name + "_")

printNoNL("Writing backup of vm definition. ")
xmlFile = open(backup_tmp_dir + "/vm-def.xml", 'x')
xmlFile.write(dom.XMLDesc())
xmlFile.close()
print("Done.")

for disk in diskNames:
    backupDisk(conn, dom, disk, backup_tmp_dir)

base_msg = "Writing backup to tar file"
printNoNL(base_msg + ".")

full_size = get_dir_size(backup_tmp_dir)
tar = tarfileProg.open(name=backup_file, mode='w:gz')
tar.add(backup_tmp_dir, arcname=backup_name, progressCallback= lambda size: print_tar_progress(size, full_size, base_msg)) #filter=lambda info: print_tarinfo_progress(info, full_size, base_msg)
tar.close()
print("\r" + base_msg + " Done." + SPACE_PADDING)

printNoNL("Cleaning up. ")
shutil.rmtree(backup_tmp_dir)
print("Done.")

dom.__del__()
conn.__del__()