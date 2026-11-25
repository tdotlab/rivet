#!/bin/bash
# Slice-5 Nacre regression: original vs rebuilt ROM, framebuffer hash +
# state trace, for every prior slice's cases. Fails loudly on any diff.
# Usage: bash tools/tests/run_slice5_regression.sh   (from the project root)
set -u
cd "$(dirname "$0")/../.."
ORIG=roms/Donkey_Kong_World_Rev1_SGB.gb
REB=build/game.gb
OUT=build/nacre-test/slice5
mkdir -p "$OUT"
HB=tools/harnesses/gb_headless
fail=0

run_case() {  # name frames press_spec [save_in]
    local name="$1" frames="$2" spec="$3" savein="${4:-}"
    local o_ppm="$OUT/${name}-orig.ppm" r_ppm="$OUT/${name}-reb.ppm"
    local o_tr="$OUT/trace-${name}-orig.txt" r_tr="$OUT/trace-${name}-reb.txt"
    local o_log="$OUT/log-${name}-orig.txt" r_log="$OUT/log-${name}-reb.txt"
    if [ -n "$savein" ]; then
        "$HB" "$ORIG" "$frames" "$o_ppm" "$spec" "$o_tr" "$savein" "$OUT/save-${name}-orig.sav" > "$o_log" 2>&1
        "$HB" "$REB"  "$frames" "$r_ppm" "$spec" "$r_tr" "$savein" "$OUT/save-${name}-reb.sav"  > "$r_log" 2>&1
    elif [ -n "$spec" ]; then
        "$HB" "$ORIG" "$frames" "$o_ppm" "$spec" "$o_tr" > "$o_log" 2>&1
        "$HB" "$REB"  "$frames" "$r_ppm" "$spec" "$r_tr" > "$r_log" 2>&1
    else
        "$HB" "$ORIG" "$frames" "$o_ppm" > "$o_log" 2>&1
        "$HB" "$REB"  "$frames" "$r_ppm" > "$r_log" 2>&1
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

run_case 600 600 ""
run_case 900 900 "start:620:632"
run_case 3600 3600 "start:620:632,a:1000:1012"
run_case 12000 12000 "start:620:632,a:1000:1012,start:2500:2512"
# slice-4 gameplay cases (save files from slice 4, in the slice4 dir)
S4=build/nacre-test/slice4
run_case s8 7000 "start:620:632,a:1000:1012,start:2500:2512,down:5700:5712,down:5800:5812,a:5900:5912,a:6100:6112"
run_case f0 7000 "start:620:632,a:1000:1012,start:2500:2512,a:5700:5712"
run_case f1 7000 "start:620:632,a:1000:1012,start:2500:2512,down:5700:5712,a:5800:5812" 
[ $fail -eq 0 ] && echo "ALL REGRESSION CASES IDENTICAL" || { echo "REGRESSION FAILURES ABOVE"; exit 1; }
