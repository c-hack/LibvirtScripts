#!/usr/bin/env bash
function readPipeAndWork {
  sep=$(echo -e '\r') # \015 is carriage return in octal
  pattern="*$sep"
  while IFS='' read -r line || [[ -n "$line" ]]; do
    echo "[$(date)] ${line##$pattern}" >> "$2" 
  done < "$1"
}

echo -n "" > $1

pipe="$(mktemp)"
rm "$pipe"
mkfifo "$pipe"

readPipeAndWork "$pipe" "$1" &

tee "$pipe"

rm $pipe