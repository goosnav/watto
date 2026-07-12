#!/bin/bash
# Double-click me to start Watto (Terminal version — shows the log).
cd "$(dirname "$0")"
python3 server.py --open
status=$?
if [ $status -ne 0 ]; then
  echo
  read -n1 -s -r -p "Watto stopped with an error (see above). Press any key to close..."
fi
