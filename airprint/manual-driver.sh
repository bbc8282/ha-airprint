#!/usr/bin/env bash
set -uo pipefail
DEVICE=$1
OPTIONS=${AIRPRINT_OPTIONS:-/data/options.json}
MODEL=$(jq -r --arg d "$DEVICE" '
  def uri: gsub("^\\s+|\\s+$"; "") |
    if . == "" or contains("://") then .
    elif contains("/printers/") then "ipp://" + . else "socket://" + . end;
  [(.driver_overrides // [])[] | select((.device | uri) == ($d | uri)) | .model][0] // ""
' "$OPTIONS")
[ -n "$MODEL" ] || exit 0
# Read the entire listing to avoid lpinfo SIGPIPE with pipefail enabled.
LIST=$(lpinfo -m 2>/dev/null) || exit 0
MATCH=$(printf '%s\n' "$LIST" | awk -v model="$MODEL" '
  { description=$0; sub(/^[^[:space:]]+[[:space:]]+/, "", description) }
  index(tolower(description),tolower(model)) {
    if (tolower($1) ~ /splix/) {splix[++ns]=$1} else {other[++no]=$1}
  }
  END {if (ns == 1) print splix[1]; else if (ns == 0 && no == 1) print other[1]}
')
if [ -n "$MATCH" ]; then
  printf '%s' "$MATCH"
else
  echo "[airprint] manual driver model '$MODEL' is missing or ambiguous; inspect lpinfo -m" >&2
fi
