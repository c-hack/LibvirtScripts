#!/usr/bin/env bash

BUFFSIZE=64

function write {
  echo "[$(date)] $1" | sed -e 's/[ \t]*$//' >> "$2"
}

function readPipeAndWork {
  cr=$'\r' # Carriage return
  nl=$'\n' # New line
  currentLine=""
  while read -N $BUFFSIZE -r str || ! [ "$str" == "" ] ;do
    newStr="$str"
    if [[ "$str" == *"$nl"* ]] ;then
      write "$currentLine${str%%$nl*}" "$2"
      newStr="${str##*$nl}"
    fi
    if [[ "$newStr" == *"$cr"* ]] ;then
      currentLine="${newStr##*$cr}"
    else 
      currentLine="$currentLine$newStr"
    fi
    str=""
  done < "$1"
  if ! [ "$currentLine" == "" ] ;then
    write "$currentLine" "$2"
  fi 
}

echo -n "" > $1

pipe="$(mktemp)"
rm "$pipe"
mkfifo "$pipe"

readPipeAndWork "$pipe" "$1" &

tee "$pipe"

rm $pipe