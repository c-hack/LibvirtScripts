#!/usr/bin/env -S python3 -u
#The -u is important, so that we have unbuffered streams for stdin and out.

import sys
import time

#Argument to strftime
LOG_PREFIX="[%Y/%m/%d (%a) %H:%M:%S] "

REQUIRED_INTERRUPTS = 3

def fail(message: str, code: int):
    print(message)
    exit(code)

def writeToLog(logfile, line:str):
    prefix = time.strftime(LOG_PREFIX)
    outLine = prefix + line.rstrip(' ') + '\n'
    logfile.write(outLine)
    logfile.flush()

if len(sys.argv) < 2:
    fail("To few arguments.", 101)

line = ""
interruptCount=0

with open(sys.argv[1], "w") as logfile:
    while True:
        try:
            char = sys.stdin.read(1)
            if char == '': 
                break
            sys.stdout.write(char)
            if char == '\n':
                writeToLog(logfile, line)
                line = ""
            elif char == '\r':
                line = ""
            else:
                line += char
        except KeyboardInterrupt:
            interruptCount += 1
            if interruptCount >= REQUIRED_INTERRUPTS:
                break
    if line != "":
         writeToLog(logfile, line)




