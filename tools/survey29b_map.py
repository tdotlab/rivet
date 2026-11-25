#!/usr/bin/env python3
"""Slice-29 survey (b): which type-$0b cells exist in the live 1-1 map,
and where are the ($82,$37) cells the $6331 post-key scan looks for?

$6b0a (bank 7) only dispatches into $75ea when a $c117-family record's
byte 0 (type) is $0b; byte 1 (subtype) then indexes $750a. So a
timer-22 subtype only matters on a type-$0b cell. Lists every type-$0b
cell (both pairs) with subtype, $75ea entry, and OAM coords, plus every
($82,$37) cell, plus every cell of any type whose subtype is in the
timer-22 ranges {16-19, 24-27, 38-41, 42-45} (for the record).

Usage: python3 tools/survey29b_map.py <wram.bin>
"""
import sys

RANGES = [(16, 19), (24, 27), (38, 41), (42, 45)]
HANDLER = {(16, 19): 2, (24, 27): 4, (38, 41): 8, (42, 45): 9}


def in_range(v):
    for lo, hi in RANGES:
        if lo <= v <= hi:
            return (lo, hi)
    return None


def main():
    wram = open(sys.argv[1], "rb").read()
    assert len(wram) == 8192, len(wram)
    base = 0xC86D - 0xC000
    print("== type-$0b cells (the only ones $6b0a dispatches on) ==")
    n0b = 0
    for row in range(32):
        for col in range(32):
            off = base + row * 128 + col * 4
            b0, b1, b2, b3 = wram[off:off + 4]
            for pair, (t, s) in enumerate(((b0, b1), (b2, b3))):
                if t == 0x0B:
                    n0b += 1
                    r = in_range(s)
                    h = f"-> $75ea entry {HANDLER[r]:02d} (TIMER-22)" if r else ""
                    print(f"  row {row:2d} col {col:2d} pair {pair} subtype {s} "
                          f"(${s:02x}) OAM ({col*8},{row*8+8}) {h}")
    print(f"total type-$0b cells: {n0b}")
    print("\n== ($82,$37) cells (the $6331 post-key scan target) ==")
    n8237 = 0
    for row in range(32):
        for col in range(32):
            off = base + row * 128 + col * 4
            b0, b1, b2, b3 = wram[off:off + 4]
            for pair, (t, s) in enumerate(((b0, b1), (b2, b3))):
                if t == 0x82 and s == 0x37:
                    n8237 += 1
                    print(f"  row {row:2d} col {col:2d} pair {pair} OAM ({col*8},{row*8+8})")
    print(f"total ($82,$37) cells: {n8237}")
    print("\n== any-type cells with a timer-22-range subtype, by type ==")
    bytype = {}
    for row in range(32):
        for col in range(32):
            off = base + row * 128 + col * 4
            b0, b1, b2, b3 = wram[off:off + 4]
            for pair, (t, s) in enumerate(((b0, b1), (b2, b3))):
                if in_range(s):
                    bytype.setdefault(t, []).append((row, col, pair, s))
    for t in sorted(bytype):
        cells = bytype[t]
        print(f"  type ${t:02x}: {len(cells)} cells, subtypes "
              f"{sorted(set(s for _, _, _, s in cells))}")


if __name__ == "__main__":
    main()
