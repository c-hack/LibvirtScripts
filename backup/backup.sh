#!/usr/bin/env bash

LOG_PATH="/var/log/backup/"
LOG_PREFIX="backup"

function fail {
    echo $1
    exit $2
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

fullLog=""

for (( i=0; i<${#backups[@]}; i++ )); do 
  backupArgs=${backups[$i]}
  vmName=${backupArgs%% *}
  logName=$LOG_PATH$LOG_PREFIX"_"$(date "+%Y-%m-%d-%H-%m")"_"$vmName".log"
  "$dir/backup.py" $backupArgs | "$dir/logOutput.sh" $logName ; exit=${PIPESTATUS[0]}
  echo "------------------" >> "$logName" 
  echo "Exit Code: $exit" >> "$logName" 
  echo "------------------" 
  
  fullLog="$fullLog$(cat "$logName")"
  
  echo "Exit Code: $exit"
  echo ""
  echo ""
  
  if [ $exit -ne 0 ] ;then
    logger "Backup failed for VM $vmName with code $exit"
  fi
  exitCodes[$i]=$exit
done

if [ "$mailOn" == "off" ] ;then
  exit 0
fi

exitSum=0

for (( i=0; i<${#exitCodes[@]}; i++ )) ;do 
  exitC=${exitCodes[$i]}
  let exitSum=exitSum+exitC
done

mailSubj="$mailSubj""Backup "

if [ $exitSum -eq 0 ] ;then
  mailSubj="$mailSubj""successfull."
else
  mailSubj="$mailSubj""failed."
fi

echo "$fullLog" | mail -s "$mailSubj" $mailRecp