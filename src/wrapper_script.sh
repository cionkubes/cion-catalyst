#!/bin/sh

python catalyst.py &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start catalyst: $status"
  exit $status
fi

# Start the second process
/usr/bin/caddy --conf /etc/Caddyfile &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start caddy: $status"
  exit $status
fi

while sleep 60; do
  ps aux |grep catalyst |grep -q -v grep
  PROCESS_1_STATUS=$?
  ps aux |grep caddy |grep -q -v grep
  PROCESS_2_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ $PROCESS_1_STATUS -ne 0 -o $PROCESS_2_STATUS -ne 0 ]; then
    echo "One of the processes has already exited."
    exit 1
  fi
done