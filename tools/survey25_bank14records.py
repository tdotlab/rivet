#!/usr/bin/env python3
"""Slice-25 survey: bank-14 $7e00 record table enumeration.

The bank-14 record table (slice 23/24) is 140 3-byte records
[bank][ptr lo][ptr hi] at bank 14 $7e00-$7fa3, read by bank-0
$2470 (H >= $7e branch). This enumerates, per target bank, how
many records point at it and the ptr range -- pinning the readers
of the bank-23 low region and the bank-24 stream region (and
checking banks 5/18/12/1/2/3/16 for any record targets).
Run: python3 tools/survey25_bank14records.py
"""
ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def main():
    rom = open(ROM, "rb").read()
    recs = {}
    for i in range(140):
        a = 14 * 0x4000 + 0x3E00 + 3 * i
        bk = rom[a]
        ptr = rom[a + 1] | (rom[a + 2] << 8)
        recs.setdefault(bk, []).append((i, ptr))
    total = 0
    for bk in sorted(recs):
        ps = recs[bk]
        total += len(ps)
        print(f"bank ${bk:02x} (dec {bk}): {len(ps)} records, "
              f"ptr min ${min(p for _i, p in ps):04x} "
              f"max ${max(p for _i, p in ps):04x}")
    print(f"total records: {total}")
    for bk in (23, 24):
        print(f"bank {bk} records (index, ptr): {recs.get(bk, [])}")


if __name__ == "__main__":
    main()
