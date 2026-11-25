#!/bin/bash
# Slice 13: full stage survey - load every (1,B) stage B=0..100 not covered
# by the progress survey (which only reached B=0,4,...,92) and scan its
# WRAM map for ($82,$37) cells and $5b $0b trigger cells.
# Uses TEST ROMs with a patched $5e99 progress->queue table (bank 1) so
# each progress value E points at the queue entry that leads to (1,B).
# Test ROMs live in build/ only; never used for byte-match.
cd "$(dirname "$0")/../.."
mkdir -p build/nacre-test/slice13/full

# batch format: "B0:Q0 B1:Q1 ..." (E = position in batch)
run_batch() {
  local bi="$1"; shift
  local rom="build/nacre-test/slice13/full/testrom_batch${bi}.gb"
  local qs=""
  local bs=()
  for pair in "$@"; do
    bs+=("${pair%%:*}")
    qs+="${pair##*:},"
  done
  qs="${qs%,}"
  # pad to 25 entries (unused progress values repeat the last Q)
  local nq=$(echo "$qs" | tr ',' '\n' | wc -l)
  local lastq="${qs##*,}"
  while [ "$nq" -lt 25 ]; do qs="$qs,$lastq"; nq=$((nq+1)); done
  python3 tools/surveys/survey13_patch_rom.py roms/Donkey_Kong_World_Rev1_SGB.gb "$rom" "$qs" > /dev/null || { echo "batch $bi ROM patch FAILED"; return; }
  local e=0
  for b in "${bs[@]}"; do
    local sav="build/nacre-test/slice13/full/save-batch${bi}-e${e}.sav"
    local out="build/nacre-test/slice13/full/B${b}"
    mkdir -p "$out"
    if [ ! -f "$sav" ]; then
      python3 tools/make_progress_save.py build/nacre-test/slice6/save-prog1.sav "$sav" $e > /dev/null 2>&1 || echo "save batch $bi e$e (B$b) FAILED"
    fi
    timeout 300 ./tools/harnesses/gb_wramdump "$rom" 5000 "start:620:632,a:1000:1012,a:2000:2012" "$sav" "$out" 400 2800 3600 > /dev/null 2>&1
    echo "batch $bi B$b done"
    e=$((e+1))
  done
}

run_batch 0 1:4 2:7 3:10 5:18 6:21 7:23 9:31 10:34 11:36 13:44 14:47 15:49 17:57 18:60 19:62 21:70 22:73 23:75 25:83 26:86 27:88 29:96 30:99 31:101 33:109
run_batch 1 34:112 35:114 37:122 38:125 39:127 41:135 42:138 43:140 45:148 46:151 47:153 49:161 50:164 51:166 53:174 54:177 55:179 57:187 58:190 59:192 61:200 62:203 63:205 65:213 66:216
run_batch 2 67:218 69:226 70:229 71:231 73:239 74:242 75:244 77:252 78:255 79:257 81:265 82:268 83:270 85:278 86:281 87:283 89:291 90:294 91:296 93:303 94:306 95:309 96:313 97:316 98:319
run_batch 3 99:322 100:327
echo done
