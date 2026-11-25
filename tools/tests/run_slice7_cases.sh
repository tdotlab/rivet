#!/bin/bash
# Slice-7 Nacre cases: original vs rebuilt ROM, framebuffer hash +
# state trace. Fails loudly on any diff.
# Usage: bash tools/tests/run_slice7_cases.sh   (from the project root)
set -u
cd "$(dirname "$0")/../.."
ORIG=roms/Donkey_Kong_World_Rev1_SGB.gb
REB=build/game.gb
OUT=build/nacre-test/slice7
mkdir -p "$OUT"
HB=tools/harnesses/gb_headless
SAVE6=build/nacre-test/slice6/save-prog1.sav
fail=0
run_case() {  # name frames press_spec [save_in] [watch]
    local name="$1" frames="$2" spec="$3" savein="${4:-}" watch="${5:-}"
    local o_ppm="$OUT/${name}-orig.ppm" r_ppm="$OUT/${name}-reb.ppm"
    local o_tr="$OUT/trace-${name}-orig.txt" r_tr="$OUT/trace-${name}-reb.txt"
    local o_log="$OUT/log-${name}-orig.txt" r_log="$OUT/log-${name}-reb.txt"
    local env_o=() env_r=()
    if [ -n "$watch" ]; then env_o=(GB_WATCH="$watch"); env_r=(GB_WATCH="$watch"); fi
    if [ -n "$savein" ]; then
        env "${env_o[@]}" "$HB" "$ORIG" "$frames" "$o_ppm" "$spec" "$o_tr" "$savein" "$OUT/save-${name}-orig.sav" > "$o_log" 2>&1
        env "${env_r[@]}" "$HB" "$REB"  "$frames" "$r_ppm" "$spec" "$r_tr" "$savein" "$OUT/save-${name}-reb.sav"  > "$r_log" 2>&1
    else
        env "${env_o[@]}" "$HB" "$ORIG" "$frames" "$o_ppm" "$spec" "$o_tr" > "$o_log" 2>&1
        env "${env_r[@]}" "$HB" "$REB"  "$frames" "$r_ppm" "$spec" "$r_tr" > "$r_log" 2>&1
    fi
    local o_fb r_fb
    o_fb=$(grep -o 'fb_sha256: [0-9a-f]*' "$o_log" | cut -d' ' -f2)
    r_fb=$(grep -o 'fb_sha256: [0-9a-f]*' "$r_log" | cut -d' ' -f2)
    local status="OK"
    [ "$o_fb" != "$r_fb" ] && status="FB-DIFF"
    if [ -f "$o_tr" ] && ! cmp -s "$o_tr" "$r_tr"; then status="$status TRACE-DIFF"; fi
    if [ -f "$OUT/save-${name}-orig.sav" ] && ! cmp -s "$OUT/save-${name}-orig.sav" "$OUT/save-${name}-reb.sav"; then status="$status SAVE-DIFF"; fi
    echo "$name ($frames f): fb $o_fb  [$status]"
    [ "$status" != "OK" ] && fail=1
}
# retry: progress-1, timer-12 retry loop, 15000f (slice-7 headline case)
run_case retry 15000 "start:620:632,a:1000:1012,a:2000:2012" "$SAVE6" "c85c,c82b,c860,c861,da43,c70f"
# mid5000: progress-1 flow, idle to 5000f (playable stage 1-1 screenshot)
run_case mid5000 5000 "start:620:632,a:1000:1012,a:2000:2012" "$SAVE6" ""
# play-right: progress-1 + right + A presses (Mario moves, dies, replays)
run_case play-right 5000 "start:620:632,a:1000:1012,a:2000:2012,right:2500:5000,a:2600:2612,a:2900:2912,a:3200:3212,a:3500:3512,a:3800:3812,a:4100:4112,a:4400:4412,a:4700:4712" "$SAVE6" ""
# death: progress-1 + right 2500-3000, A 2600/2900 (first timer-12 at f=2668)
run_case death 3000 "start:620:632,a:1000:1012,a:2000:2012,right:2500:3000,a:2600:2612,a:2900:2912" "$SAVE6" "c711,c712,c82b,c85c,da43"
[ $fail -eq 0 ] && echo "ALL SLICE-7 CASES IDENTICAL" || { echo "SLICE-7 FAILURES ABOVE"; exit 1; }
