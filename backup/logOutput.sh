#!/usr/bin/env bash

function write {
  echo "[$(date)] $1" | sed -e 's/[ \t]*$//' >> "$2"
}

function readPipeAndWork {
  cr=$'\r' # Carriage return
  nl=$'\n' # New line
  currentLine=""
  while read -N1 -r char ;do
    if [ "$char" == "$cr" ] ;then
      currentLine=""
    elif [ "$char" == "$nl" ] ;then
      write "$currentLine" "$2"
      currentLine=""
    else 
      currentLine="$currentLine$char"
    fi
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