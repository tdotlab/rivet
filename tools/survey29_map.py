#!/usr/bin/env python3
"""Slice-29 survey: find every 1-1 map cell whose subtype lands in the
timer-22 $75ea handler ranges.

The $750a byte map (bank 7) sends a $c117-record byte 1 (the map-cell
SUBTYPE) to a $75ea handler index. Timer-22 handlers are entries
02/04/08/09 ($6c7a/$6c8f/$6ca4/$6cb9), selected by byte-1 values
{16-19, 24-27, 38-41, 42-45} decimal. This script reads a WRAM dump
($c86d-$d86d, 32 rows x 32 cols x 4 bytes: two (type,subtype) pairs
per cell) and lists every cell with a subtype in those ranges, with
its map (row,col) and OAM coords (screen tile (col-1,row-1) + (8,16)).

Usage: python3 tools/survey29_map.py <wram.bin>
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
    base = 0xC86D - 0xC000  # WRAM offset of the map
    hits = []
    all_subtypes = {}
    for row in range(32):
        for col in range(32):
            off = base + row * 128 + col * 4
            b0, b1, b2, b3 = wram[off:off + 4]
            for pair, (t, s) in enumerate(((b0, b1), (b2, b3))):
                all_subtypes.setdefault(s, 0)
                all_subtypes[s] += 1
                r = in_range(s)
                if r is not None:
                    # OAM coords of the cell's top-left: x = col*8, y = row*8+8
                    hits.append((row, col, pair, t, s, HANDLER[r], col * 8, row * 8 + 8))
    print(f"cells surveyed: {32*32}, distinct subtypes present: {len(all_subtypes)}")
    print("subtype histogram (decimal: count):")
    print("  " + ", ".join(f"{s}:{c}" for s, c in sorted(all_subtypes.items())))
    print(f"\ntimer-22-range subtype hits: {len(hits)}")
    for row, col, pair, t, s, h, ox, oy in hits:
        print(f"  row {row:2d} col {col:2d} pair {pair} type ${t:02x} "
              f"subtype {s} (${s:02x}) -> $75ea entry {h:02d} "
              f"OAM ({ox},{oy})")
    if not hits:
        print("  NONE -- no 1-1 map cell carries a timer-22 subtype.")


if __name__ == "__main__":
    main()
