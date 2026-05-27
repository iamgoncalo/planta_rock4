#!/bin/bash
set -e
DIRS="app/static app/routers/sections.py app/routers/state.py app/routers/clusters.py app/routers/tv.py"
TERMS="CO2|temperature|temperatura|humidity|humidade|Deucalion|MAC address|#FF0000|#EF4444|red-500|red-600|bg-red|text-red"
found=0
for dir in $DIRS; do
  if [ -e "$dir" ]; then
    matches=$(grep -rn -E "$TERMS" "$dir" 2>/dev/null || true)
    if [ -n "$matches" ]; then
      echo "FORBIDDEN TERM FOUND:"
      echo "$matches"
      found=1
    fi
  fi
done
exit $found
