#!/usr/bin/env python3
"""Slice 18: scan slice-13 WRAM dumps for $c200 record types.

$c200 holds 32 records x 32 bytes. Byte 14 (offset $0e) is the $2b48
index, copied to [$c105] by $2a0a; byte 13 is [$c104]; byte 18 bit 3
is the [$c109] arming flag (set by entry 91 state 4 $6c60/$6ca9,
disarmed by entry 46 $4aee). Byte 0 is the sprite index into the
bank-11 $4000 table (via $112c), byte 1 the second index.

Scans build/nacre-test/slice13/prog{0..24}/ and full/B{1..100}/
wram_*.bin dumps (frames 2800-3600 of a 5000f run that loads the
stage via the $5e99 progress->queue table). Reports, per stage-data
B, the set of live byte-14 values, any 34/46/53/92/91 records, any
record with byte-18 bit 3 set, any byte-13 in {$46,$c6} (the only
values that could make bank-10 $7378 write [$c105]=46), and the
max byte-0 / byte-1 seen (bank-11 table extent evidence).

Usage: python3 tools/surveys/survey18_records.py
"""
import glob
import os

TARGETS = (34, 46, 53, 92, 91)


def scan_dump(wf):
    w = open(wf, 'rb').read()
    hf = wf.replace('wram_', 'hram_')
    h = open(hf, 'rb').read() if os.path.exists(hf) else b''
    state = h[0x0e] if len(h) > 0x0e else None
    timer = h[0x10] if len(h) > 0x10 else None
    c829 = w[0x829]  # stage-data index being loaded
    recs = []
    for r in range(32):
        base = 0x200 + r * 32
        rec = w[base:base + 32]
        if len(rec) < 32:
            continue
        recs.append(rec)
    return state, timer, c829, recs


def main():
    per_stage = {}
    all_b0 = set()
    all_b1 = set()

    def add(d, b, state, timer, recs, src):
        s = per_stage.setdefault(b, dict(types=set(), armed=[],
                                         b13_46=[], b0=set(), b1=set(),
                                         dumps=0, states=set()))
        s['dumps'] += 1
        s['states'].add((state, timer))
        for r, rec in enumerate(recs):
            b0, b1 = rec[0], rec[1]
            s['b0'].add(b0)
            s['b1'].add(b1)
            all_b0.add(b0)
            all_b1.add(b1)
            if rec[0] == 0 and all(x == 0 for x in rec[1:]):
                continue
            t = rec[14]
            s['types'].add(t)
            if t in TARGETS:
                s.setdefault('targets', []).append((src, r, t, rec[18]))
            if rec[18] & 0x08:
                s['armed'].append((src, r, t))
            if rec[13] in (0x46, 0xC6):
                s['b13_46'].append((src, r, t, rec[13]))

    for d in sorted(glob.glob('build/nacre-test/slice13/prog*')):
        # progN loads data 4N
        n = int(d.split('prog')[-1])
        b = 4 * n
        for wf in sorted(glob.glob(d + '/wram_*.bin')):
            state, timer, c829, recs = scan_dump(wf)
            if c829 != b:
                continue
            add(d, b, state, timer, recs, os.path.basename(wf))
    for d in sorted(glob.glob('build/nacre-test/slice13/full/B*')):
        b = int(d.split('B')[-1])
        for wf in sorted(glob.glob(d + '/wram_*.bin')):
            state, timer, c829, recs = scan_dump(wf)
            if c829 != b:
                continue
            add(d, b, state, timer, recs, os.path.basename(wf))

    print(f"stages with dumps (c829 match): {sorted(per_stage)}")
    print(f"count: {len(per_stage)}")
    print()
    print("byte-14 values seen per stage (live $2b48 indices):")
    for b in sorted(per_stage):
        s = per_stage[b]
        print(f"  B{b:3d}: dumps={s['dumps']} types={sorted(s['types'])}"
              f" states={sorted(s['states'])}")
    print()
    print("TARGET records (34/46/53/92/91):")
    found = False
    for b in sorted(per_stage):
        s = per_stage[b]
        for t in s.get('targets', []):
            print(f"  B{b}: {t}")
            found = True
    if not found:
        print("  NONE in any surveyed stage dump")
    print()
    print("ARMED records (byte18 bit 3 set):")
    found = False
    for b in sorted(per_stage):
        s = per_stage[b]
        for t in s['armed']:
            print(f"  B{b}: {t}")
            found = True
    if not found:
        print("  NONE in any surveyed stage dump")
    print()
    print("byte13 in {$46,$c6} (could feed bank-10 $7378 -> [$c105]=46):")
    found = False
    for b in sorted(per_stage):
        s = per_stage[b]
        for t in s['b13_46']:
            print(f"  B{b}: {t}")
            found = True
    if not found:
        print("  NONE in any surveyed stage dump")
    print()
    print(f"record byte0 (bank-11 table index) values seen: {sorted(all_b0)}")
    print(f"  max byte0 = {max(all_b0)}")
    print(f"record byte1 values seen: {sorted(all_b1)}")
    print(f"  max byte1 = {max(all_b1)}")


if __name__ == '__main__':
    main()
