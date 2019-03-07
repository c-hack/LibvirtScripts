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

import xml.etree.cElementTree as ET

#Modified version of tarfile
import tarfileProg

BUF_SIZE = 16*1024
SPACE_PADDING = ' ' * 40

SNAPSHOT_XML_ROOT = "domainsnapshot"
SNAPSHOT_XML_DISK_LIST = "disks"
SNAPSHOT_XML_DISK = "disk"
SNAPSHOT_XML_DISK_NAME = "name"
SNAPSHOT_XML_DISK_SNAPSHOT = "snapshot"
SNAPSHOT_XML_SOURCE = "source"
SNAPSHOT_XML_SOURCE_FILE = "file"

#<domainsnapshot>
# <disks>
#  <disk name='hda'>
#   <source file='/storage/teamSpeak-Snap1.qcow2'/>
#  </disk> 
# </disks>
#</domainsnapshot>

def fail(message: str, code: int):
    print(message)
    exit(code)

def printNoNL(msg: str):
    sys.stdout.write(msg)
    sys.stdout.flush()

def print_progress(size: int, full_size: int, base_msg: str):
    msg = ('\r' + base_msg + ': {:.2%}' + SPACE_PADDING).format(size / full_size)
    printNoNL(msg)

def getDomainDisks(conn: libvirt.virConnect, dom: libvirt.virDomain):
    stats = conn.domainListGetStats([dom], libvirt.VIR_DOMAIN_STATS_BLOCK , libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_BACKING)[0][1]
    result = dict()
    for i in range(0, stats['block.count']):
        name = stats['block.' + str(i) + '.name']
        path = stats.get('block.' + str(i) + '.path', None)
        backing_index = stats.get('block.' + str(i) + '.backingIndex', 0)
        if not path:
            # Ignore non disks
            continue
        if not name in result:
            result[name] = dict()
            result[name]["name"] = name
            result[name]["files"] = dict()
        result[name]["files"][backing_index] = path
    return result

def addFile(file_to_copy: str, tar:tarfileProg.TarFile, inTarDir: str):
    base_msg = " Copying file " + file_to_copy
    printNoNL(base_msg + ".")
    full_size = os.path.getsize(file_to_copy)

    tar.add(file_to_copy, arcname=os.path.join(inTarDir, file_to_copy[1:]), 
            progressCallback= lambda size: print_progress(size, full_size, base_msg))
    print("\r" + base_msg + ". Done." + SPACE_PADDING)

def backup_disk(disk: dict, tar: tarfileProg.TarFile, inTarDir: str):
    print("Start backing up " + disk["name"])
    backingIndexes = list(disk["files"].keys())
    # As the dict is from before the tmp snapshot was made we take all.
    for index in backingIndexes:
            addFile(disk["files"][index], tar, inTarDir)
    print("Done backing up " + disk["name"])

def backup_vm_def(dom: libvirt.virDomain, tar:tarfileProg.TarFile):
    printNoNL("Writing backup of vm definition. ")
    _, xmlFile_path = tempfile.mkstemp(suffix=".xml", prefix="backup_vm_def_")
    xmlFile = open(xmlFile_path, 'w')
    xmlFile.write(dom.XMLDesc())
    xmlFile.close()
    tar.add(xmlFile_path, arcname=os.path.join(backup_name,"vm-def.xml"))
    os.remove(xmlFile_path)
    print("Done.")

def snapshot_domain(dom: libvirt.virDomain, tmpDir: str, disks: dict, wantedDisks: list):
    printNoNL("Creating temporary snapshot. ")

    xml_snapshot = ET.Element(SNAPSHOT_XML_ROOT)
    xml_disks = ET.SubElement(xml_snapshot, SNAPSHOT_XML_DISK_LIST)
    
    for disk in disks.values():
        params = dict()
        params[SNAPSHOT_XML_DISK_NAME] = disk["name"]
        if disk["name"] in wantedDisks:
            xml_disk = ET.SubElement(xml_disks, SNAPSHOT_XML_DISK, **params)
            new_snapshot_path = tmpDir + '/' + disk["name"] + '.qcow2'
            source_params = dict()
            source_params[SNAPSHOT_XML_SOURCE_FILE] = new_snapshot_path
            ET.SubElement(xml_disk, SNAPSHOT_XML_SOURCE, **source_params)
        else:
            params[SNAPSHOT_XML_DISK_SNAPSHOT] = "no"
            xml_disk = ET.SubElement(xml_disks, SNAPSHOT_XML_DISK, **params)
    
    xml_string = ET.tostring(xml_snapshot).decode('UTF-8')
    dom.snapshotCreateXML(xml_string, flags = libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_NO_METADATA | libvirt. VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY | libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_ATOMIC)
    print("Done.")

def revert_snapshot_for_disk(dom: libvirt.virDomain, disk:str):
    printNoNL(" Block committing " + disk + ".")
    dom.blockCommit(disk, None, None, flags=libvirt.VIR_DOMAIN_BLOCK_COMMIT_SHALLOW | libvirt.VIR_DOMAIN_BLOCK_COMMIT_ACTIVE | libvirt.VIR_DOMAIN_BLOCK_COMMIT_DELETE)
    while True:
        info = dom.blockJobInfo(disk)
        cur = info["cur"]
        end = info["end"]
        if cur >= end:
            break
        message = ('\r Block committing ' + disk + ': {:.2%}' + SPACE_PADDING).format(cur/end)
        printNoNL(message)
    printNoNL("\r Block committing " + disk + ": Finishing." + SPACE_PADDING)
    dom.blockJobAbort(disk, flags=libvirt.VIR_DOMAIN_BLOCK_JOB_ABORT_PIVOT | libvirt.VIR_DOMAIN_BLOCK_JOB_ABORT_ASYNC)
    print("\r Block committing " + disk + ". Done." + SPACE_PADDING)

def revert_snapshot_for_domain(dom: libvirt.virDomain, diskNames: list):
    print("Starting to revert temporary snapshot.")
    for disk in diskNames:
        revert_snapshot_for_disk(dom, disk)
    print("Done reverting temporary snapshot.")

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

try:

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

    try:
        backup_vm_def(dom, tar)

        if len(diskNames) > 0:
            tmpDir = tempfile.mkdtemp(prefix="backup_tmp_")
            dom_disks = getDomainDisks(conn, dom)
            os.chmod(tmpDir, 0o777)
            snapshot_domain(dom, tmpDir, dom_disks, diskNames)
            try:
                for name in diskNames:
                    backup_disk(dom_disks[name], tar, os.path.join(backup_name, "root"))
            finally:        
                revert_snapshot_for_domain(dom, diskNames)

                printNoNL("Cleaning up. ")
                shutil.rmtree(tmpDir)
                print("Done.")
    finally:
        tar.close()
finally:
    dom.__del__()
    conn.__del__()