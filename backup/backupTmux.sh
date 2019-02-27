#!/usr/bin/env bash
SESSION=backup
tmux="tmux -2"

dir="$(dirname "$(realpath "$0")")"

# if the session is already running, just attach to it.
$tmux has-session -t $SESSION
if [ $? -eq 0 ]; then
       echo "Session $SESSION already exists. Asuming backup in progress. Not starting backup! Attaching to session."
       logger "Backup warning: Session already existing." 
       sleep 1
       $tmux attach -t $SESSION
       exit 0;
fi

# create a new session, named $SESSION, and detach from it
$tmux new-session -d -s $SESSION
$tmux send-keys $dir/backup.sh Space $1 Enter
$tmux attach -t $SESSION:0