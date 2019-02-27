# Backup Script
Can backup domains.

## Requirements
 * `python3-libvirt`
 * optional: `tmux`

## Overview
 * `backup.py` does the heavy lifting and uses `tarfileProg.py`(a variation of the official tarfile.py). It can backup any amount of disks from one VM.
 * `backup.sh` does backups of multiple VMs and manages logging and mailing and so on. It needs a config file. The format is described below.
 * `backupTmux.sh` runs `backup.sh` in a tmux session. Needs `tmux` to be installed.
## Config
This is the syntax of the conf:

    mail (off|on <recipient> <subject prefix>)
    backup <vm name> <backup dir> [<disk> [<second disk> ...]]
    backup <vm name> <backup dir> [<disk> [<second disk> ...]]
    ...

Where `recipient` is a mail address, `vm name` is a vm name as in `virsh list` and `disk` is a disk name as the target in `virsh domblklist`.
Lines starting with `#` are ignored.