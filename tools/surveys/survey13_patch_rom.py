#!/usr/bin/env python3
"""Patch the $5e99 progress->queue table (bank 1) in a ROM copy (slice 13).

The table is 25 16-bit LE entries at bank 1 $5e99 (file offset 0x5e99).
Used by the full stage survey to point each progress value at an
arbitrary queue index, so any (1,B) stage can be loaded live.
TEST ROMS ONLY - never used for byte-match.

Usage: survey13_patch_rom.py <in.gb> <out.gb> <Q0,Q1,...,Q24>
"""
import sys

src, dst = sys.argv[1], sys.argv[2]
qs = [int(x) for x in sys.argv[3].split(',')]
assert len(qs) == 25, f'need 25 queue indices, got {len(qs)}'
d = bytearray(open(src, 'rb').read())
for e, q in enumerate(qs):
    off = 0x5e99 + e * 2
    d[off] = q & 0xFF
    d[off + 1] = (q >> 8) & 0xFF
open(dst, 'wb').write(d)
print(f'wrote {dst}: $5e99 = {qs}')
