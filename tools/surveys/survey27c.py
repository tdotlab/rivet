#!/usr/bin/env python3
"""Slice-27 survey phase 3: for each bank-0 cf site targeting $59xx-$7exx,
find the bank mapped just before it (scan back for `ld a,$xx; rst $10`
= 3e xx d7, or a `call $xxxx` into a mapper). Also compare bank 9 vs
bank 8 bytes at $6182-$6376 (the $264a pocket) and check bank-10 $7b6c.
Run: python3 tools/surveys/survey27c.py
"""
import re
import sys

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()

SITES = [
    0x026C, 0x08FD, 0x0974, 0x09CC, 0x0928, 0x0937, 0x09AD, 0x09E5,
    0x095A, 0x0AAF, 0x0B0F, 0x1C6E, 0x22BD, 0x234A, 0x265E, 0x2663,
    0x2668, 0x28E5, 0x2904, 0x2AAA, 0x2B21, 0x321F, 0x3323, 0x3331,
    0x3315, 0x3401, 0x3404, 0x35BA,
]


def backscan(site):
    """Scan back up to 64 bytes from site for 3e xx d7 (ld a,xx; rst $10).
    Return list of (offset_back, bank)."""
    out = []
    for i in range(site - 1, max(0, site - 64), -1):
        if rom[i] == 0x3E and rom[i + 2] == 0xD7:
            out.append((site - i, rom[i + 1]))
    return out


def main():
    for s in SITES:
        op = rom[s]
        tgt = rom[s + 1] | (rom[s + 2] << 8) if op in (0xC3, 0xCD, 0xC2,
                                                      0xCA, 0xD2, 0xDA,
                                                      0xEA, 0xFA) else None
        tstr = f"${tgt:04x}" if tgt is not None else "?"
        print(f"  bank0 ${s:04x} op ${op:02x} tgt {tstr}  backscan: "
              f"{[(f'-{d}', f'bank ${b:02x}') for d, b in backscan(s)]}")
    # bank 9 vs bank 8 at the $264a pocket
    for lo, hi in ((0x6182, 0x6273), (0x62CD, 0x6376)):
        a = rom[9 * 0x4000 + lo - 0x4000:9 * 0x4000 + hi - 0x4000]
        b = rom[8 * 0x4000 + lo - 0x4000:8 * 0x4000 + hi - 0x4000]
        d = sum(1 for p, q in zip(a, b) if p != q)
        print(f"  bank9 vs bank8 ${lo:04x}-${hi:04x}: {d}/{hi-lo} differ")
    # bank 10 $7b6c: carved?
    print(f"  bank10 $7b6c bytes: {rom[10*0x4000+0x3b6c:10*0x4000+0x3b6c+24].hex()}")
    print(f"  bank7  $7b6c bytes: {rom[7*0x4000+0x3b6c:7*0x4000+0x3b6c+24].hex()}")
    print(f"  bank8  $7b6c bytes: {rom[8*0x4000+0x3b6c:8*0x4000+0x3b6c+24].hex()}")
    # bank 7 vs bank 10 at $7ae5/$7c57/$7c88/$7cb0
    for lo, hi in ((0x7AE5, 0x7B14), (0x7C57, 0x7CA0), (0x7CB0, 0x7D01)):
        a = rom[7 * 0x4000 + lo - 0x4000:7 * 0x4000 + hi - 0x4000]
        b = rom[10 * 0x4000 + lo - 0x4000:10 * 0x4000 + hi - 0x4000]
        d = sum(1 for p, q in zip(a, b) if p != q)
        print(f"  bank7 vs bank10 ${lo:04x}-${hi:04x}: {d}/{hi-lo} differ")


if __name__ == "__main__":
    main()
