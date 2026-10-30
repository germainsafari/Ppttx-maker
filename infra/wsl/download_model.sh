#!/usr/bin/env bash
# Usage: download_model.sh <hf-repo-id>   (runs detached, logs to ~/dl_<repo>.log)
set -euo pipefail
REPO="$1"
LOG=~/dl_$(echo "$REPO" | tr / _).log
setsid nohup ~/vllm-env/bin/hf download "$REPO" > "$LOG" 2>&1 < /dev/null &
echo "downloading $REPO -> $LOG"
