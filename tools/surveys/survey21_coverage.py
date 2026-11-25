#!/usr/bin/env python3
"""Slice-21 coverage check: walk bank 9 from all slice-21 seeds and
verify every planned carve span is fully covered (code) or identified
as data. Prints any span with uncovered bytes."""
import sys
sys.path.insert(0, "tools")
from gb_rd import walk, file_off

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()

# 50 non-noop targets of the $4001 dispatch table (197 entries).
targets = set()
for a in range(0x4001, 0x418B, 2):
    w = rom[file_off(9, a)] | (rom[file_off(9, a + 1)] << 8)
    if w != 0x1D29:
        targets.add(w)
# $264a (bank 0) jp targets -- the $6182 pocket.
pocket = [0x6182, 0x61F4, 0x6266, 0x62CD, 0x6308, 0x636F]
# helpers / small routines / tails, incl. entry-UNVERIFIED hand seeds.
extra = [0x6402, 0x6412, 0x644B, 0x6485, 0x648B, 0x6D6D, 0x6E94,
         0x6ED9, 0x6F0C, 0x6F65, 0x6574, 0x6CCE, 0x6D8B]
seeds = sorted(targets | set(pocket) | set(extra))
reached, rst08, notes = walk(9, seeds)
print(f"seeds: {len(seeds)}, instrs: {len(reached)}, rst08: {len(rst08)}")
for n in notes:
    if "outside window" not in n:
        print("  NOTE:", n)

CODE_SPANS = [
    (0x4691, 0x48DF), (0x492E, 0x49A0), (0x49D7, 0x4B4D),
    (0x4B52, 0x5A02), (0x5A04, 0x63F2),
    (0x6402, 0x6411), (0x6412, 0x644A), (0x644B, 0x647F),
    (0x6485, 0x648A), (0x648B, 0x648F),
    (0x6962, 0x696A), (0x699A, 0x69AB), (0x6A08, 0x6A10),
    (0x6A40, 0x6A52), (0x6A7D, 0x6A9B), (0x6AC8, 0x6AE6),
    (0x6B43, 0x6B4B), (0x6B7B, 0x6B8C), (0x6BE9, 0x6BF1),
    (0x6C21, 0x6C33), (0x6C5F, 0x6C7D), (0x6CAA, 0x6CB6),
    (0x6D6D, 0x6D8A), (0x6E94, 0x6EB0), (0x6ED9, 0x6F0B),
    (0x6F0C, 0x6F33), (0x6F65, 0x6F9A),
]
cov = set()
for a, (ln, *_r) in reached.items():
    cov.update(range(a, a + ln))
bad = 0
for lo, hi in CODE_SPANS:
    missing = [a for a in range(lo, hi + 1) if a not in cov]
    if missing:
        bad += 1
        print(f"SPAN ${lo:04x}-${hi:04x}: UNCOVERED {missing[:10]}"
              f"{'...' if len(missing) > 10 else ''} "
              f"({len(missing)} bytes)")
    else:
        print(f"SPAN ${lo:04x}-${hi:04x}: fully covered")
print("BAD SPANS:", bad)
# timer writes in the new carve (door/clear-chain check)
print("\nldh [$ff90],a (timer) writes in reached code:")
for a, (ln, text, kind, tgt) in sorted(reached.items()):
    if "ff90" in text:
        print(f"  ${a:04x}: {text}")
print("\n[$c105] writes in reached code:")
for a, (ln, text, kind, tgt) in sorted(reached.items()):
    if "c105" in text and ("ld [" in text or "ldh [" in text):
        print(f"  ${a:04x}: {text}")
