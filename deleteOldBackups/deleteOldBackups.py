#!/usr/bin/env python3 
import sys
import json
import os
import time
import re

from operator import attrgetter

DAY_SECONDS = 24 * 3600
WEEK_SECONDS = 7 * 24 * 3600 
MONTH_SECONDS = 30 * 24 * 3600

class FileToRemove:
    def __init__(self, mtime:int, path:str):
        self.mtime = mtime
        self.path = path
    def __str__(self):
        return self.path
    def __repr__(self):
        return self.path

def fail(message: str, code: int):
    print(message)
    exit(code)

def which_to_remove(files: list, curr_time: int, interval: int):
    files_sorted = sorted(files, key=attrgetter('mtime'), reverse=True)
    to_remove = []
    last = None
    last_unit = -1
    for f in files_sorted:
        unit = int((curr_time - f.mtime) / interval)
        if(last_unit == unit):
            to_remove.append(last)
        last = f
        last_unit = unit
    return to_remove


if len(sys.argv) < 2:
    fail("To few arguments.", 101)

config = []
backup_config = {}

with open(sys.argv[1]) as json_data:
    config = json.load(json_data)

backup_conf_file = config['backupConfig']

with open(backup_conf_file) as conf:
    lines = conf.readlines()
    lines.pop(0)
    for line in lines:
        parts = line.split(' ')
        domName = parts[1]
        backupDir = parts[2]
        backup_config[domName] = backupDir


domains = list(backup_config.keys())
ignore_pattern = config['ignorePattern']
all_for = config['keepAllFor'] #seconds from seconds
daily_for = DAY_SECONDS * config['keepDailyFor'] #seconds from days
weekly_for = WEEK_SECONDS * config['keepWeeklyFor'] #seconds from weeks
monthly_for = MONTH_SECONDS * config['keepMonthlyFor'] #seconds from months

ignore = re.compile(ignore_pattern)
curr_time = time.time()

files_to_remove = []

for domain in domains:
    files = []
    for (dirpath, dirnames, filenames) in os.walk(backup_config[domain]):
        for name in filenames:
            path = os.path.join(dirpath, name)
            mtime = os.path.getmtime(path)
            if (mtime + all_for) > curr_time:
                continue
            if ignore.match(path):
                continue
            if not name.startswith("backup_" + domain + "_"):
                continue
            files.append(FileToRemove(mtime, path))
    day_pool = []
    week_pool = []
    month_pool = []
    for f in files:
        if f.mtime + daily_for > curr_time:
            day_pool.append(f)
        elif f.mtime + weekly_for > curr_time:
            week_pool.append(f)
        elif f.mtime + monthly_for > curr_time:
            month_pool.append(f)
        else:
            files_to_remove.append(f)
    files_to_remove.extend(which_to_remove(day_pool, curr_time, DAY_SECONDS))
    files_to_remove.extend(which_to_remove(week_pool, curr_time, WEEK_SECONDS))
    files_to_remove.extend(which_to_remove(month_pool, curr_time, MONTH_SECONDS))

    keep = [item for item in files if item not in files_to_remove]

for f in files_to_remove:
    os.unlink(f.path)

