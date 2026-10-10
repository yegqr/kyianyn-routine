#!/usr/bin/env bash
# Telegram backfill queue (docs/PARSING.md 0.1): one lane = channels fetched one after another.
# Usage: scripts/bronze/tg_backfill.sh A|B|C   Log: data/bronze/telegram/logs/<lane>.log ("done <ch>" or "FAIL <ch>")
# Safe to rerun: tg_fetch.py appends only new posts and finishes an interrupted backfill.
set -u
cd "$(dirname "$0")/../.."
case "${1:-}" in
  A) set -- A VA_Kyiv vitaliy_klitschko OP_UA V_Zelenskiy_official truexakyiv war_monitor AerisRimor ;;  # alerts, label, calendar
  B) set -- B kyiv_airdef kyiv_nebo StrategicaviationT ;;                               # strike label, signals
  C) set -- C mod_russia GeneralStaffZSU mos_sobyanin favt_info kpszsu monitorwarr vanek_nikolaev ;;  # strikes on RF, signals
  *) echo "usage: $0 A|B|C" >&2; exit 2 ;;
esac
lane=$1; shift
log=data/bronze/telegram/logs/$lane.log
mkdir -p data/bronze/telegram/logs
for ch in "$@"; do
  echo "$(date -u +%FT%TZ) start $ch" >> "$log"
  if python3 -I scripts/bronze/tg_fetch.py "$ch" "data/bronze/telegram/$ch.jsonl" >> "$log" 2>&1; then
    echo "$(date -u +%FT%TZ) done $ch" >> "$log"
  else
    echo "$(date -u +%FT%TZ) FAIL $ch" >> "$log"
  fi
done
