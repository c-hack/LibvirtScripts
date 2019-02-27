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

def print_progress(size: int, full_size: int, base_msg: str):
    msg = ('\r' + base_msg + ': {:.2%}' + SPACE_PADDING).format(size / full_size)
    printNoNL(msg)

def getListOfFilesForDisk(conn: libvirt.virConnect,dom: libvirt.virDomain, disk:str):
    stats = conn.domainListGetStats([dom], libvirt.VIR_DOMAIN_STATS_BLOCK, libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_BACKING)[0][1]
    result = []
    for i in range(0, stats['block.count']):
        if(stats['block.' + str(i) + '.name'] == disk):
            result.append(stats['block.' + str(i) + '.path'])
    return result

def addFile(file_to_copy: str, tar:tarfileProg.TarFile, inTarDir: str):
    base_msg = " Copying file " + file_to_copy
    printNoNL(base_msg + ".")
    full_size = os.path.getsize(file_to_copy)

    tar.add(file_to_copy, arcname=os.path.join(inTarDir, file_to_copy[1:]), 
            progressCallback= lambda size: print_progress(size, full_size, base_msg))
    print("\r" + base_msg + ". Done." + SPACE_PADDING)

def backupDisk(conn: libvirt.virConnect, dom: libvirt.virDomain, disk:str, tar:tarfileProg.TarFile, inTarDir: str):
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
            addFile(file_to_copy, tar, inTarDir)

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
backup_file = os.path.join(backupDir, backup_name + ".tar.gz")

tar = tarfileProg.open(name=backup_file, mode='w:gz')

printNoNL("Writing backup of vm definition. ")
_, xmlFile_path = tempfile.mkstemp(suffix=".xml", prefix="backup_vm_def_")
xmlFile = open(xmlFile_path, 'w')
xmlFile.write(dom.XMLDesc())
xmlFile.close()
tar.add(xmlFile_path, arcname=os.path.join(backup_name,"vm-def.xml"))
os.remove(xmlFile_path)
print("Done.")

for disk in diskNames:
    backupDisk(conn, dom, disk, tar, os.path.join(backup_name, "root"))

tar.close()

dom.__del__()
conn.__del__()