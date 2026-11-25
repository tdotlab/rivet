#!/usr/bin/env python3
"""Slice-24 survey: banks 25/26 ($19/$1a) and bank 30 ($1e).

Reproduces the numbers in tools/gen_slice24.py's header (banks
25/26/30 section). Run: python3 tools/survey24_banks2530.py
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


def ld_sites(rom, val):
    sites = []
    for off in range(len(rom) - 2):
        if rom[off] == 0x3E and rom[off + 1] == val and rom[off + 2] == 0xD7:
            bk = off // 0x4000
            addr = (off % 0x4000) + (0x4000 if bk > 0 else 0)
            sites.append((bk, addr))
    return sites


def survey_plain(bank):
    b = bank_bytes(bank)
    ln, lv = last_non_ff(b)
    print(f"bank {bank} (${bank:02x}): "
          f"`ld a,${bank:02x}; rst $10` sites: {ld_sites(open(ROM, 'rb').read(), bank)}")
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


def t1e_items():
    """Parse bank 30's $74e5 TransferTable1E table -> (entries, lists)."""
    b30 = bank_bytes(30)

    def rdw(a):
        return b30[a - 0x4000] | (b30[a - 0x4000 + 1] << 8)

    entries = [rdw(0x74E5 + 2 * i) for i in range(49)]
    lists = {}
    for p in sorted(set(entries)):
        cnt = b30[p - 0x4000]
        assert 1 <= cnt <= 32, (hex(p), cnt)
        items = []
        for k in range(cnt):
            a = p + 1 + 7 * k
            bk = b30[a - 0x4000]
            src = rdw(a + 1)
            dst = rdw(a + 3)
            ln = b30[a + 5 - 0x4000] | ((b30[a + 6 - 0x4000] & 0x7F) << 8)
            dec = bool(b30[a + 6 - 0x4000] & 0x80)
            assert bk <= 0x1F and 0x4000 <= src <= 0x7FFF
            assert 0x8000 <= dst <= 0x9FFF
            items.append((bk, src, dst, ln, dec))
        lists[p] = (cnt, items)
    return entries, lists


def main():
    rom = open(ROM, "rb").read()
    for bank in (25, 26):
        survey_plain(bank)
    entries, lists = t1e_items()
    print(f"\nTransferTable1E ($74e5): {len(entries)} entries, "
          f"{len(lists)} distinct lists, "
          f"{sum(c for c, _ in lists.values())} items")
    banks = Counter()
    for _cnt, items in lists.values():
        for bk, _s, _d, _l, _dc in items:
            banks[bk] += 1
    print("source-bank histogram: "
          f"{{{', '.join(f'${k:02x}:{v}' for k, v in sorted(banks.items()))}}}")
    for bank in (0x19, 0x1A):
        its = [(s, d, ln, dc) for _c, items in lists.values()
               for (bk, s, d, ln, dc) in items if bk == bank]
        print(f"  bank ${bank:02x} items ({len(its)}): "
              + "; ".join(f"src ${s:04x} dst ${d:04x} len ${ln:04x}"
                          f"{' dec' if dc else ''}" for s, d, ln, dc in its))
    spans = sorted((p, p + 1 + 7 * c) for p, (c, _i) in lists.items())
    cur = 0x7547
    gaps = []
    for a, b in spans:
        if a > cur:
            gaps.append((cur, a))
        cur = max(cur, b)
    print(f"  list coverage $7547-$7cfa: gaps "
          f"{[(hex(a), hex(b)) for a, b in gaps]}, end ${cur:04x}")

    # Bank 30 SGB packets $40e0-$4710.
    b30 = bank_bytes(30)

    def rdw30(a):
        return b30[a - 0x4000] | (b30[a - 0x4000 + 1] << 8)

    pkt_entries = [rdw30(0x4000 + 2 * i) for i in range(112)]
    uniq = sorted(set(pkt_entries))
    spans = [(p, p + 16 * (b30[p - 0x4000] & 7)) for p in uniq]
    cur = 0x40E0
    gaps = []
    for a, b in spans:
        if a > cur:
            gaps.append((cur, a))
        cur = max(cur, b)
    print(f"\nbank 30 SGB packets: {len(pkt_entries)} entries, "
          f"{len(uniq)} distinct, first-byte &7 histogram "
          f"{dict(Counter(b30[p - 0x4000] & 7 for p in uniq))}")
    print(f"  packet coverage $40e0: gaps "
          f"{[(hex(a), hex(b)) for a, b in gaps]}, end ${cur:04x}")
    ln, lv = last_non_ff(b30)
    print(f"  bank 30 last non-$ff ${ln:04x} (${lv:02x})")
    print("  $64e5 table (LoadStagePtr $1c91/$1cd9): 10 pages x 256 "
          "bytes = $64e5-$6de4 (D in 0..9 selects the page, E the "
          "offset; 16 bytes copied to $da61). Flanking $4710-$64e4 "
          "and $6de5-$74e4 have no reader pinned in this slice.")


if __name__ == "__main__":
    main()
