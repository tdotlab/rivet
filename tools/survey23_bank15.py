#!/usr/bin/env python3
"""Slice-23 survey: bank 15 ($0f, ROM $3c000-$3ffff).

Reproduces the numbers in tools/gen_slice23.py's header.
Run: python3 tools/survey23_bank15.py
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
BANK = 15


def main():
    rom = open(ROM, "rb").read()
    b = rom[0x3C000:0x40000]
    print(f"bank 15: {len(b)} bytes, $ff={b.count(0xff)}, $00={b.count(0)}")
    i = len(b) - 1
    while b[i] == 0xFF:
        i -= 1
    print(f"last non-$ff window addr ${0x4000 + i:04x} (byte ${b[i]:02x}); "
          f"${0x4000 + i + 1:04x}-$7fff all $ff: {set(b[i + 1:]) == {0xff}}")
    for base in range(0, 0x4000, 0x1000):
        ch = b[base:base + 0x1000]
        print(f"  ${0x4000 + base:04x}: ret(c9)={ch.count(0xc9)} "
              f"call(cd)={ch.count(0xcd)} jp(c3)={ch.count(0xc3)} "
              f"rst10(d7)={ch.count(0xd7)} rst08(cf)={ch.count(0xcf)} "
              f"jp(hl)(e9)={ch.count(0xe9)}")
    # Whole-ROM callers of TransferTable0F ($1d82): cd 82 1d, and the
    # ld a,imm immediately before each (the table index) where present.
    print("call $1d82 sites (bank, addr, preceding ld a,imm if any):")
    for off in range(len(rom) - 2):
        if rom[off:off + 3] == bytes([0xCD, 0x82, 0x1D]):
            bank = off // 0x4000
            addr = (off % 0x4000) + (0x4000 if bank > 0 else 0)
            pre = ""
            if off >= 2 and rom[off - 2] == 0x3E:
                pre = f"ld a,${rom[off - 1]:02x}"
            print(f"  bank {bank} ${addr:04x} {pre}")
    # ld a,$0f; rst $10 sites (bank-15 selections) in whole ROM.
    sites = []
    for off in range(len(rom) - 2):
        if rom[off] == 0x3E and rom[off + 1] == 0x0F and rom[off + 2] == 0xD7:
            bank = off // 0x4000
            addr = (off % 0x4000) + (0x4000 if bank > 0 else 0)
            sites.append((bank, addr))
    print(f"`ld a,$0f; rst $10` sites: {sites}")
    # The $4000 table: entries are dw pointers; each points at a block
    # whose first byte is a count, then count dw pointers (copy specs
    # consumed by $16c2). Walk entries until a pointer leaves the bank.
    def rdw(a):
        return rom[file_off(BANK, a)] | (rom[file_off(BANK, a + 1)] << 8)
    n = 0
    while True:
        p = rdw(0x4000 + 2 * n)
        if not (0x4000 <= p <= 0x7FFF):
            break
        n += 1
        if n > 512:
            break
    print(f"$4000 table: {n} entries (first non-pointer at index {n}: "
          f"${rdw(0x4000 + 2 * n):04x})")
    total = 0
    for idx in range(n):
        p = rdw(0x4000 + 2 * idx)
        cnt = rom[file_off(BANK, p)]
        subs = [rdw(p + 1 + 2 * k) for k in range(cnt)]
        ok = all(0x4000 <= s <= 0x7FFF for s in subs)
        print(f"  entry {idx}: block ${p:04x} count {cnt} subs "
              f"{[f'${s:04x}' for s in subs]} plausible={ok}")
        total += 1 + 2 * cnt
    print(f"table blocks span bytes: {total} (incl. table itself "
          f"{2 * n})")
    # gb_rd walks from each table-target block start and from sub-targets.
    seeds = []
    for idx in range(n):
        p = rdw(0x4000 + 2 * idx)
        cnt = rom[file_off(BANK, p)]
        for k in range(cnt):
            seeds.append(rdw(p + 1 + 2 * k))
    print(f"walk seeds (sub-targets): {len(seeds)}")
    reached, rst08, notes = walk(BANK, seeds)
    print(f"walk from sub-targets: {len(reached)} instrs, "
          f"{len(rst08)} rst $08 sites, notes={notes[:5]}")
    # Also walk from $4000 itself (linear) to see how fast it derails.
    reached, rst08, notes = walk(BANK, [0x4000])
    print(f"walk from $4000: {len(reached)} instrs, notes={notes[:3]}")


if __name__ == "__main__":
    main()
