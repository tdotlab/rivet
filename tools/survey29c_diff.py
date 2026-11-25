#!/usr/bin/env python3
"""Slice-29 survey (c): diff the WRAM map ($c86d-$d86d) between two dumps,
cell by cell. Also prints a few control bytes ($c560, $dd18, $dd3c, $c858).

Usage: python3 tools/survey29c_diff.py <before.bin> <after.bin>
"""
import sys

BASE = 0xC86D - 0xC000


def cells(wram):
    out = {}
    for row in range(32):
        for col in range(32):
            off = BASE + row * 128 + col * 4
            out[(row, col)] = tuple(wram[off:off + 4])
    return out


def main():
    a = open(sys.argv[1], "rb").read()
    b = open(sys.argv[2], "rb").read()
    assert len(a) == 8192 and len(b) == 8192
    ca, cb = cells(a), cells(b)
    diffs = [(k, ca[k], cb[k]) for k in ca if ca[k] != cb[k]]
    print(f"map cells changed: {len(diffs)}")
    for (row, col), old, new in sorted(diffs):
        print(f"  row {row:2d} col {col:2d} OAM ({col*8},{row*8+8}): "
              f"{old[0]:02x}{old[1]:02x}{old[2]:02x}{old[3]:02x} -> "
              f"{new[0]:02x}{new[1]:02x}{new[2]:02x}{new[3]:02x}")
    for name, addr in (("$c560", 0x560), ("$dd18", 0x1D18), ("$c858", 0x858),
                       ("$dd3c", 0x1D3C)):
        print(f"  {name}: ${a[addr]:02x} -> ${b[addr]:02x}")
    # $dd3c is 16-bit little-endian at $dd3c
    print(f"  $dd3c (16-bit): ${a[0x1D3C] | (a[0x1D3D] << 8):04x} -> "
          f"${b[0x1D3C] | (b[0x1D3D] << 8):04x}")


if __name__ == "__main__":
    main()
