#!/usr/bin/env python3
"""Slice-24 survey: bank 27 ($1b) sprite table + data.

Reproduces the numbers in tools/generators/gen_slice24.py's header (bank 27
section, if carved). Run: python3 tools/surveys/survey24_bank27.py
"""
import sys
from collections import Counter

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


def main():
    rom = open(ROM, "rb").read()
    b = bank_bytes(27)
    ln, lv = last_non_ff(b)
    print(f"bank 27 ($1b): $ff={b.count(0xff)}, $00={b.count(0)}, "
          f"last non-$ff ${ln:04x} (${lv:02x})")
    for base in range(0, 0x4000, 0x1000):
        ch = b[base:base + 0x1000]
        print(f"  ${0x4000 + base:04x}: ret(c9)={ch.count(0xc9)} "
              f"call(cd)={ch.count(0xcd)} jp(c3)={ch.count(0xc3)} "
              f"rst10(d7)={ch.count(0xd7)} rst08(cf)={ch.count(0xcf)} "
              f"jp(hl)(e9)={ch.count(0xe9)}")
    reached, rst08, notes = walk(27, [0x4000])
    print(f"  gb_rd walk from $4000: {len(reached)} instrs, "
          f"{len(rst08)} rst $08, notes={notes[:3]}")

    def rdw(a):
        return b[a - 0x4000] | (b[a - 0x4000 + 1] << 8)

    # $7918 dw table (BuildSpriteEntries $1dfd: $7918 + A*2 -> ptr
    # -> [count][count x 6-byte items]). Each item is 6 bytes:
    # [index][b0][b1][b2][b3][b4] -- the index byte selects the
    # $c200 + index*32 slot, the other 5 bytes fill the 12-byte
    # record (bytes 0-3, byte 7). The first probe used 5-byte
    # items and showed phantom gaps; 6-byte items tile exactly.
    # Extent: entries while the ptr is plausible AND the list
    # parses (count 1..32, list inside the bank).
    print("\n$7918 dw table:")
    entries = []
    i = 0
    while True:
        p = rdw(0x7918 + 2 * i)
        if not (0x4000 <= p < 0x8000):
            print(f"  entry {i} @${0x7918 + 2 * i:04x}: ${p:04x} "
                  f"(implausible -- table ends)")
            break
        cnt = b[p - 0x4000]
        if not (1 <= cnt <= 32 and p + 1 + 6 * cnt <= 0x8000):
            print(f"  entry {i} @${0x7918 + 2 * i:04x}: ptr ${p:04x} "
                  f"count {cnt} (implausible -- table ends)")
            break
        entries.append(p)
        i += 1
        if i > 200:
            print("  ...runaway, stopping")
            break
    print(f"  {len(entries)} entries, table ${0x7918:04x}-"
          f"${0x7918 + 2 * len(entries) - 1:04x}")
    lists = {}
    for p in sorted(set(entries)):
        cnt = b[p - 0x4000]
        items = []
        for k in range(cnt):
            a = p + 1 + 6 * k
            items.append(tuple(b[a + j - 0x4000] for j in range(6)))
        lists[p] = (cnt, items)
    print(f"  distinct lists: {len(lists)}, total items: "
          f"{sum(cnt for cnt, _items in lists.values())}")
    spans = sorted((p, p + 1 + 6 * c) for p, (c, _i) in lists.items())
    print(f"  list spans: first ${spans[0][0]:04x}, last end "
          f"${spans[-1][1]:04x}")
    # Do the lists tile contiguously from the first list start?
    cur = spans[0][0]
    gaps = []
    for a, bb in spans:
        if a > cur:
            gaps.append((cur, a))
        cur = max(cur, bb)
    print(f"  gaps in list coverage: {[(hex(a), hex(bb)) for a, bb in gaps]}")
    print(f"  table end ${0x7918 + 2 * len(entries):04x} vs first "
          f"list ${spans[0][0]:04x}; last list end ${cur:04x} vs "
          f"last non-$ff ${ln:04x}")
    # 6-byte item byte histograms (what do the fields look like?).
    for j in range(6):
        vals = [it[j] for _c, items in lists.values() for it in items]
        print(f"  item byte{j}: distinct {len(set(vals))}, "
              f"min ${min(vals):02x} max ${max(vals):02x}")
    # TransferTable1E items sourcing bank $1b (from the $74e5 table).
    b30 = bank_bytes(30)

    def rdw30(a):
        return b30[a - 0x4000] | (b30[a - 0x4000 + 1] << 8)

    t1e = [rdw30(0x74E5 + 2 * i) for i in range(49)]
    srcs = []
    for p in sorted(set(t1e)):
        cnt = b30[p - 0x4000]
        for k in range(cnt):
            a = p + 1 + 7 * k
            if b30[a - 0x4000] == 0x1B:
                srcs.append(rdw30(a + 1))
    print(f"\nTransferTable1E items from bank $1b: {len(srcs)}, "
          f"src min ${min(srcs):04x} max ${max(srcs):04x}")
    print(f"  distinct srcs: {len(set(srcs))}")


if __name__ == "__main__":
    main()
