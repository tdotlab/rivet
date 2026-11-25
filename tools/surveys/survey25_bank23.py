#!/usr/bin/env python3
"""Slice-25 survey: bank 23 ($17) $4000 attract-demo table + $7e12 tables.

Reproduces the numbers in tools/generators/gen_slice25.py's header (bank 23).
Run: python3 tools/surveys/survey25_bank23.py
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def main():
    rom = open(ROM, "rb").read()

    def byte(a):
        return rom[23 * 0x4000 + (a - 0x4000)]

    def rdw(a):
        return byte(a) | (byte(a + 1) << 8)

    # $4000 table: dw entries while plausible + strictly increasing.
    entries = [rdw(0x4000 + 2 * i) for i in range(27)]
    print(f"$4000 table entries 0-26: "
          f"{[f'${t:04x}' for t in entries]}")
    print(f"  strictly increasing: "
          f"{all(entries[i + 1] > entries[i] for i in range(26))}")
    print(f"  entry 27 would read ${rdw(0x4036):04x} "
          f"(first block bytes $04 $00 -- partition break)")
    # Blocks: [count][count x 3-byte items], slot byte sequential.
    total = 0
    for i, t in enumerate(entries):
        cnt = byte(t)
        ln = 1 + 3 * cnt
        items = [(byte(t + 1 + 3 * k), byte(t + 2 + 3 * k),
                  byte(t + 3 + 3 * k)) for k in range(cnt)]
        slots_ok = [it[0] for it in items] == list(range(cnt))
        nxt = entries[i + 1] if i + 1 < 27 else t + ln
        assert t + ln == nxt, f"block {i} does not tile"
        assert slots_ok, f"block {i} slots not sequential"
        total += cnt
    print(f"  27 blocks tile $4036-${entries[-1] + 1 + 3 * byte(entries[-1]):04x} "
          f"with zero gaps, {total} items, all slots sequential")
    # [$ca66] range: C==20 queue B values from the bank-12 queue table.
    pairs = [(rom[12 * 0x4000 + (0x4f97 - 0x4000) + 2 * i],
              rom[12 * 0x4000 + (0x4f97 - 0x4000) + 2 * i + 1])
             for i in range(331)]
    b20 = sorted(set(bv for c, bv in pairs if c == 20))
    print(f"  C==20 queue B values ([$ca66] source): {b20} (max {max(b20)})")
    # $7e12-$7e31: two 6-byte MemcpyC blocks + two byte tables.
    print(f"  $7e12 6 bytes: {' '.join(f'{byte(a):02x}' for a in range(0x7e12, 0x7e18))}")
    print(f"  $7e18 6 bytes: {' '.join(f'{byte(a):02x}' for a in range(0x7e18, 0x7e1e))}")
    print(f"  $7e1e 10 bytes: {' '.join(f'{byte(a):02x}' for a in range(0x7e1e, 0x7e28))}")
    print(f"  $7e28 10 bytes: {' '.join(f'{byte(a):02x}' for a in range(0x7e28, 0x7e32))}")
    # Low region walks derail; carved code never targets it.
    for s in (0x4000, 0x5000, 0x6000, 0x7000):
        reached, rst08, notes = walk(23, [s])
        print(f"  gb_rd walk from ${s:04x}: {len(reached)} instrs, "
              f"notes={notes[:1]}")


if __name__ == "__main__":
    main()
