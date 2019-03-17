#!/usr/bin/env bash

LOG_TMP_PATH="/var/log/current-backup/"
#Argument to date
LOG_PREFIX="[%Y/%m/%d (%a) %H:%M:%S] "

function fail {
    echo $1
    exit $2
}

logForMail=""

function logLow {
    logger -t "c-hack-backup" "$1"
    logForMail="$logForMail"$'\n'"$1"
}

function log {
    out="$(date "+$LOG_PREFIX")$1"
    echo "$out"
    logLow "$out"
}

if [ $# -ne 1 ] ;then
  fail "Need the path to the config file." 11
fi

dir="$(dirname "$(realpath "$0")")"

mailOn="notSet"
mailRecp=""
mailSubj=""

backups=()
exitCodes=()

while IFS= read -r line
do
  if [[ "$line" == "#"* ]] ;then
    #Ignore
    :
  elif [[ "$line" == "mail"* ]] ;then
    if [ "$mailOn" == "notSet" ] ;then
      remainingLine=${line#* }
      mailOn=${remainingLine%% *}
      if ! ( [ "$mailOn" == "on" ] || [ "$mailOn" == "off" ] ) ;then
        fail "Config error! mail should be followed by either on or off." 21
      fi
      if [ "$mailOn" == "on" ] ;then
        remainingLine=${remainingLine#* }
        mailRecp=${remainingLine%% *}
        remainingLine=${remainingLine#* }
        mailSubj=$remainingLine
      fi
    else
      fail "Config error! mail can only occur once!" 22
    fi
  elif [[ "$line" == "backup"* ]] ;then
    backups["${#backups[@]}"]=${line#* }
  else
    fail "Config error! Unknown option: $line" 23
  fi
done < "$1"

if [ "$mailOn" == "notSet" ] ;then
  fail "Config error! No mail line!" 24
fi

backupCount=${#backups[@]}

log "Starting backup of $backupCount domains."

for (( i=0; i<$backupCount; i++ )); do 
  backupArgs=${backups[$i]}
  vmName=${backupArgs%% *}
  logName=$LOG_TMP_PATH"backup_"$(date "+%Y-%m-%d-%H-%m")"_"$vmName".log"
  log "------------------"
  log "Domain: $vmName"
  log "------------------"
  "$dir/backup.py" $backupArgs | "$dir/logOutput.py" $logName ; exit=${PIPESTATUS[0]}
  sync
  sleep 1
  logLow "$(cat $logName)"
  log "------------------"
  log "Exit Code: $exit"
  if [ $exit -eq 111 ] ;then
    log "!!! Seems the backup was interrupted. Stopping here!!!"
  elif [ $exit -ne 0 ] ;then 
    log "!!! This is not good !!!" 
  fi
  log "------------------"
  log ""
  exitCodes[$i]=$exit
  if [ $exit -eq 111 ] ;then
    break
  fi
done

find "$LOG_TMP_PATH" -type f -delete

if [ "$mailOn" == "off" ] ;then
  exit 0
fi

exitSum=0

for (( i=0; i<${#exitCodes[@]}; i++ )) ;do 
  exitC=${exitCodes[$i]}
  let exitSum=exitSum+exitC
done

mailSubj="$mailSubj"" Backup "

if [ $exitSum -eq 0 ] ;then
  mailSubj="$mailSubj""successfull."
else
  mailSubj="$mailSubj""failed."
fi

log "Sending mail"

echo "$logForMail" | mail -s "$mailSubj" $mailRecp

log "End of backup"
log ""
