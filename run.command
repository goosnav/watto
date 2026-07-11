#!/bin/bash
# Double-click me to start Watto.
cd "$(dirname "$0")"
exec python3 server.py --open
