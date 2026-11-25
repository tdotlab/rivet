#!/usr/bin/env python3
"""Slice-24 survey: bank 6 ($06) run-1 stage data, plus fill candidates.

Reproduces the numbers in tools/generators/gen_slice24.py's header.
Run: python3 tools/surveys/survey24_bank6.py
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# Bank-5 stage table, run 1 (stages 45-79 -> bank 6), from src/banks/bank5.asm.
STAGE6 = [0x4000, 0x4181, 0x43ac, 0x44ac, 0x4589, 0x4741, 0x48c5, 0x4a19,
          0x4c25, 0x4d54, 0x4ec8, 0x4fce, 0x50d9, 0x5235, 0x53e5, 0x5504,
          0x565f, 0x579b, 0x59b7, 0x5a8c, 0x5c42, 0x5d9a, 0x5f33, 0x60ad,
          0x61fc, 0x638d, 0x6555, 0x66d8, 0x68c8, 0x6a4e, 0x6bda, 0x6cbf,
          0x6e78, 0x6ffb, 0x71a1]


def bank_bytes(bank):
    return open(ROM, "rb").read()[bank * 0x4000:(bank + 1) * 0x4000]


def last_non_ff(b):
    i = len(b) - 1
    while b[i] == 0xFF:
        i -= 1
    return 0x4000 + i, b[i]


def survey_bank(bank):
    b = bank_bytes(bank)
    ln, lv = last_non_ff(b)
    print(f"bank {bank}: $ff={b.count(0xff)}, $00={b.count(0)}, "
          f"last non-$ff ${ln:04x} (${lv:02x}), "
          f"tail all $ff: {set(b[ln - 0x3fff:]) == {0xff}}")
    for base in range(0, 0x4000, 0x1000):
        ch = b[base:base + 0x1000]
        print(f"  ${0x4000 + base:04x}: ret(c9)={ch.count(0xc9)} "
              f"call(cd)={ch.count(0xcd)} jp(c3)={ch.count(0xc3)} "
              f"rst10(d7)={ch.count(0xd7)} rst08(cf)={ch.count(0xcf)} "
              f"jp(hl)(e9)={ch.count(0xe9)}")
    reached, rst08, notes = walk(bank, [0x4000])
    print(f"  gb_rd walk from $4000: {len(reached)} instrs, "
          f"{len(rst08)} rst $08, notes={notes[:3]}")


def main():
    rom = open(ROM, "rb").read()
    # `ld a,$06; rst $10` sites in the whole ROM.
    sites = []
    for off in range(len(rom) - 2):
        if rom[off] == 0x3E and rom[off + 1] == 0x06 and rom[off + 2] == 0xD7:
            bk = off // 0x4000
            addr = (off % 0x4000) + (0x4000 if bk > 0 else 0)
            sites.append((bk, addr))
    print(f"`ld a,$06; rst $10` sites: {sites}")
    survey_bank(6)

    # Stage starts: headers, contiguity, sizes.
    b = bank_bytes(6)
    print("stage starts (bank 6):")
    for i, s in enumerate(STAGE6):
        hdr = " ".join(f"{b[s - 0x4000 + k]:02x}" for k in range(8))
        nxt = STAGE6[i + 1] if i + 1 < len(STAGE6) else None
        print(f"  stage {45 + i} ${s:04x} size "
              f"{(nxt - s) if nxt else '?'} hdr: {hdr}")
    print(f"  stage 79 ${STAGE6[-1]:04x} -> last non-$ff "
          f"${last_non_ff(b)[0]:04x}: "
          f"{last_non_ff(b)[0] - STAGE6[-1]} bytes")
    # Gap check: are stage spans contiguous (next start == prev end)?
    contig = all(STAGE6[i + 1] > STAGE6[i] for i in range(len(STAGE6) - 1))
    print(f"  starts strictly increasing: {contig}")
    # Header byte patterns: byte0 / byte1 distributions across stages.
    print(f"  hdr byte0 values: {sorted(set(b[s - 0x4000] for s in STAGE6))}")
    print(f"  hdr byte1 values: {sorted(set(b[s - 0x4000 + 1] for s in STAGE6))}")
    print(f"  hdr byte2 values: {sorted(set(b[s - 0x4000 + 2] for s in STAGE6))}")
    # Embedded dw pointers in-bank: count dw values in $4000-$7fff
    # pointing at $4000-$7fff (a pointer table would show a dense run).
    ptrs = 0
    for a in range(0x4000, 0x7fff):
        w = b[a - 0x4000] | (b[a - 0x4000 + 1] << 8)
        if 0x4000 <= w <= 0x7fff:
            ptrs += 1
    print(f"  dw values pointing in-bank (any alignment): {ptrs} / 16383")
    # Bytes after last stage start up to last non-$ff.
    ln, _ = last_non_ff(b)
    print(f"  bytes ${STAGE6[-1]:04x}-${ln:04x} first 16: "
          + " ".join(f"{x:02x}" for x in b[STAGE6[-1] - 0x4000:STAGE6[-1] - 0x4000 + 16]))

    print("\nfill candidates (extent + opcode density only):")
    for bank in (17, 19, 20, 21, 22, 25, 26, 27, 28, 30):
        survey_bank(bank)


if __name__ == "__main__":
    main()
