#!/usr/bin/env python3
"""Slice-24 survey: banks 19-22 ($13-$16) stream data.

Reproduces the numbers in tools/gen_slice24.py's header (banks
19-22 section). Run: python3 tools/survey24_banks1922.py
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def bank_bytes(bank):
    return open(ROM, "rb").read()[bank * 0x4000:(bank + 1) * 0x4000]


def last_non_ff(b):
    i = len(b) - 1
    while b[i] == 0xFF:
        i -= 1
    return 0x4000 + i, b[i]


def ld_sites(rom, val):
    sites = []
    for off in range(len(rom) - 2):
        if rom[off] == 0x3E and rom[off + 1] == val and rom[off + 2] == 0xD7:
            bk = off // 0x4000
            addr = (off % 0x4000) + (0x4000 if bk > 0 else 0)
            sites.append((bk, addr))
    return sites


def main():
    rom = open(ROM, "rb").read()
    # Bank-14 record table: per-bank record counts / ptr ranges.
    recs = {}
    for i in range(140):
        a = 14 * 0x4000 + 0x3E00 + 3 * i
        bk = rom[a]
        ptr = rom[a + 1] | (rom[a + 2] << 8)
        recs.setdefault(bk, []).append(ptr)
    for bank in (19, 20, 21, 22):
        b = bank_bytes(bank)
        ln, lv = last_non_ff(b)
        print(f"bank {bank} (${bank:02x}): "
              f"`ld a,${bank:02x}; rst $10` sites: "
              f"{ld_sites(rom, bank)}")
        print(f"  $ff={b.count(0xff)}, $00={b.count(0)}, "
              f"last non-$ff ${ln:04x} (${lv:02x}), "
              f"tail all $ff: {set(b[ln - 0x3fff:]) == {0xff}}")
        for base in range(0, 0x4000, 0x1000):
            ch = b[base:base + 0x1000]
            print(f"  ${0x4000 + base:04x}: ret(c9)={ch.count(0xc9)} "
                  f"call(cd)={ch.count(0xcd)} jp(c3)={ch.count(0xc3)} "
                  f"rst10(d7)={ch.count(0xd7)} "
                  f"rst08(cf)={ch.count(0xcf)} "
                  f"jp(hl)(e9)={ch.count(0xe9)}")
        reached, rst08, notes = walk(bank, [0x4000])
        print(f"  gb_rd walk from $4000: {len(reached)} instrs, "
              f"{len(rst08)} rst $08, notes={notes[:3]}")
        ps = recs.get(bank, [])
        print(f"  bank-14 records -> this bank: {len(ps)}, "
              f"ptr min ${min(ps):04x} max ${max(ps):04x}")
    print("reader: bank-0 $2470 (H >= $7e branch reads a bank-14 "
          "record [bank][ptr], maps the record bank, follows "
          "ptr+DE as a Decompress $257f / MemcpyC $106e source; "
          "bank-12 $4a3e beforehand only reads a $4eeb table byte "
          "into E, never jumps into the record bank).")


if __name__ == "__main__":
    main()
