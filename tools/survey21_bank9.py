#!/usr/bin/env python3
"""Slice-21 survey: bank 9 gaps + every entry point into bank 9.

Finds, ROM-wide:
  * `ld a,$09; rst $10` sites (3e 09 d7) and the call/jp that follows
  * `call $xxxx` / `jp $xxxx` in already-carved code whose target is a
    bank-9 gap address (only call/jp/jr seed a walk -- slice 17 lesson)
  * what a gb_rd walk from all known bank-9 seeds reaches, vs CARVED
"""
import sys
sys.path.insert(0, "tools")
from gb_rd import walk, file_off, decode

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()

# 1. ROM-wide `ld a,$09; rst $10` (bank-9 select) sites.
print("=== ld a,$09 ; rst $10 sites ===")
for bank in range(32):
    base = bank * 0x4000
    for off in range(base, base + 0x4000 - 3):
        if rom[off] == 0x3E and rom[off + 1] == 0x09 and rom[off + 2] == 0xD7:
            addr = off - base + (0x4000 if bank else 0)
            # next instruction after rst $10
            nxt = off + 3
            ln, text, kind, tgt = decode(rom, nxt, addr + 3)
            print(f"  bank {bank:2d} ${addr:04x}: next: {text} "
                  f"(kind {kind}, tgt "
                  f"${tgt:04x})" if isinstance(tgt, int) else
                  f"  bank {bank:2d} ${addr:04x}: next: {text} "
                  f"(kind {kind})")

# 2. Walk bank 9 from every known seed; report spans vs CARVED gaps.
import ast, re
src = open("tools/gen_banks.py").read()
m = re.search(r'CARVED\s*=\s*(\{.*?\n\})', src, re.S)
carved = ast.literal_eval(m.group(1))[9]
carved_set = set()
for lo, hi in carved:
    carved_set.update(range(lo, hi))

seeds = [0x418B, 0x41F2, 0x4259, 0x4292, 0x4657, 0x42CB, 0x46A4,
         0x432B, 0x439C, 0x440D, 0x444D,  # $4000 dispatch entries
         0x6574, 0x6CCE, 0x6D8B,          # $2b48 entries 26/56/89
         0x63F3, 0x6480, 0x684F, 0x6893, 0x68D7]
reached, rst08, notes = walk(9, seeds)
print(f"\n=== walk from {len(seeds)} known seeds: {len(reached)} instrs ===")
for n in notes:
    print("  NOTE:", n)
# reached-but-uncarved addresses
uncarved = sorted(a for a in reached if a not in carved_set)
print(f"  reached instrs outside CARVED: {len(uncarved)}")
# group into spans
def spans(addrs):
    out = []
    for a in addrs:
        if out and a == out[-1][1] + 1:
            out[-1][1] = a
        else:
            out.append([a, a])
    return out
for lo, hi in spans(uncarved):
    print(f"    reached-uncarved ${lo:04x}-${hi:04x}")
# gaps and their first bytes
print("\n=== bank 9 gaps (CARVED complement in $4000-$8000) ===")
gaps = []
a = 0x4000
while a < 0x8000:
    if a not in carved_set:
        lo = a
        while a < 0x8000 and a not in carved_set:
            a += 1
        gaps.append((lo, a))
    else:
        a += 1
for lo, hi in gaps:
    b = rom[file_off(9, lo):file_off(9, lo) + 16]
    print(f"  ${lo:04x}-${hi:04x} ({hi-lo} bytes) first bytes: "
          + " ".join(f"{x:02x}" for x in b))
print(f"  total gap bytes: {sum(hi-lo for lo,hi in gaps)}")
