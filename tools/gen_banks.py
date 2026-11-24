#!/usr/bin/env python3
"""Generate src/banks.asm: INCBIN lines for bank 0's tail and banks 1-31.
These are the parts of the ROM not yet curated. As a bank (or part of
one) gets curated, add its range to CARVED below and move the code into
src/ -- this script then emits INCBIN only for the remaining gaps.
Regenerate with: python3 tools/gen_banks.py > src/banks.asm
The ROM itself is never copied into the repo -- INCBIN reads it at
build time from roms/, which is git-ignored (see README.md)."""
ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# Curated ranges, keyed by bank: [(lo, hi), ...] in $4000-$7fff space,
# hi exclusive. Slice 3 carved bank 1 $4000-$59ff, bank 12 $4000-$5916,
# bank 23 $731f-$7716, bank $1e (30) $4000-$40df (SGB packet table).
# Slice 4 carved bank 2 $4003-$4008 + $4010-$43af + $45a9-$47fb +
# $6212-$6491, bank 3 $4000-$400b + $4010-$43af + $45a9-$48f0 +
# $76eb-$78af, bank 5 $4000-$40d3 (stage table), bank 7 $7168-$71b9.
# Slice 5 carved bank 7 $4016-$41dc + $480e-$4826 + $6572-$6580 +
# $68ad-$68c3 + $6b0a-$6b54 + $6f62-$7000 + $7edd-$7f0c, bank 23
# $7717-$7e11 (the $7722 rst-$08 dispatch + handlers).
# Slice 7 carved bank 11 $4000-$40ff (sprite-pointer table) and
# bank 18 DECIMAL ($12) $4934-$4c83 (106 8-byte records -- slice 7
# called it the stage table, but that was a decimal/hex slip; the
# real stage table is bank $18 HEX = decimal 24, see slice 8).
# Slice 8 carved bank 24 ($18) $4934-$4c83 (stage table, 106 records)
# and bank 16 ($10) $4031-$4044 + $51c8-$52e7 + $52e7-$5428 +
# $5428-$59f1 (the death path: $51c8 per-frame update, $52e0/$5405
# rst-$08 tables, $5349 death handler setting hStateTimer=12).
# Slice 9 carved bank 9 $4000-$4020 (rst-$08 dispatch, 16 entries) +
# $418b-$4690 (object handlers) + $63f3-$6401 (record-pointer helper)
# + $6480-$6484 (dec [$da4a]).
# Slice 9 also carved bank 12 $5917-$5dbb (data + credits text).
# Slice 10 carved bank 7 $63c4-$63f3 (shared $63c4 setup) + $6b09
# (no-op handler) + $6b55-$6e8b ($75ea interaction handlers) +
# $6e8c-$6ea8 + $6f06-$6f2d (handler-18 continuation) + $750a-$760f
# ($750a byte map + $75ea pointer table) + $7d5e-$7d95 + $7e07-$7e17
# (handler-6 chain).
# Slice 11 carved bank 8 $4000-$4aec (map-record builders) + the
# $4aed-$4b62 pointer tables + $5409-$5808 (256 4-byte class
# records); bank 7 $41dd-$4793 (the $42xx per-frame interaction
# routines, entered via the $41dd [$dd1a] table) + $7d96-$7e06
# (handler-7/17 chains); bank 16 ($10) $4af0-$4e88 (per-frame
# $c117-record scanner).
# Slice 12 carved bank 2 $47fc-$48e9 (119-entry sound table), bank 3
# $48f1-$4942 (41-entry song table), bank 7 $4827-$4840 ([$dd18]
# table) + $627b-$63c3 + $63f4-$643e + $643f-$644c (template, 14 bytes
# here; last 6 bytes $644d-$6452 are entry 11's dispatch head, slice
# 13) + $664e-$66c9 + $714c-$7167 (the $6331 scan home), bank 8
# $4b63-$5408 (class byte tables).
# Slice 13 carved bank 7 $4841-$4ed6 + $4ed7-$4edb (table) +
# $4edb-$5082 + $50a0-$521e + $521f-$5229 (table) + $5229-$5681 +
# $5682-$5694 (table) + $5694-$58ee + $58ef-$58f5 (table) +
# $58f5-$5a19 + $5a1a-$5a20 (table) + $5a20-$5d49 + $5d4a-$5d6e (data)
# + $5d6e-$5f32 + $5f33-$5f45 (table) + $5f45-$627a + $644d-$645b
# (entry 11 dispatch) + $645c-$6464 (table) + $6464-$64e9 (incl.
# entry 12 $64db) + $64ea-$64f0 (table) + $64f0-$6571 + $66ca-$67a1 +
# $695b-$6b08 (the $4827 entries' routines and their jp-hl tables).
# NOT carved in slice 13: $5083-$50a0 (real code, no found entry --
# left INCBIN), $6581-$664e, $67a1-$695b, $7001-$714c, $71ba-$750a,
# $7610-$77a9.
CARVED = {
    1: [(0x4000, 0x5A00)],
    2: [(0x4003, 0x4009), (0x4010, 0x43B0), (0x45A9, 0x47FC),
        (0x47FC, 0x48EA), (0x6212, 0x6492)],
    3: [(0x4000, 0x400C), (0x4010, 0x43B0), (0x45A9, 0x48F1),
        (0x48F1, 0x4943), (0x76EB, 0x78B0)],
    5: [(0x4000, 0x40D4)],
    7: [(0x4000, 0x4016), (0x4016, 0x41DD), (0x41DD, 0x4794), (0x4794, 0x480E), (0x480E, 0x4827),
        (0x4827, 0x4841), (0x4841, 0x4ED7), (0x4ED7, 0x4EDB),
        (0x4EDB, 0x5083), (0x5083, 0x50A0), (0x50A0, 0x521F), (0x521F, 0x5229),
        (0x5229, 0x5682), (0x5682, 0x5694), (0x5694, 0x58EF),
        (0x58EF, 0x58F5), (0x58F5, 0x5A1A), (0x5A1A, 0x5A20),
        (0x5A20, 0x5D4A), (0x5D4A, 0x5D6E), (0x5D6E, 0x5F33),
        (0x5F33, 0x5F45), (0x5F45, 0x627B),
        (0x63C4, 0x63F4), (0x627B, 0x63C4), (0x63F4, 0x643F),
        (0x643F, 0x644D), (0x644D, 0x645C), (0x645C, 0x6464),
        (0x6464, 0x64EA), (0x64EA, 0x64F0), (0x64F0, 0x6572),
        (0x6572, 0x6581), (0x664E, 0x66CA), (0x66CA, 0x67A1),
        (0x68AD, 0x68C4), (0x695B, 0x6B09),
        (0x6B09, 0x6B0A), (0x6B0A, 0x6B55), (0x6B55, 0x6E8C),
        (0x6E8C, 0x6EA9), (0x6EA9, 0x6ED2), (0x6F06, 0x6F2E),
        (0x6F2E, 0x7001), (0x714C, 0x7168), (0x7168, 0x71BA), (0x750A, 0x7610),
        (0x77A9, 0x7ABB), (0x7D5E, 0x7D96), (0x7D96, 0x7E07), (0x7E07, 0x7E18),
        (0x7EDD, 0x7F0D)],
    8: [(0x4000, 0x4AED), (0x4AED, 0x4B63), (0x4B63, 0x5409), (0x5409, 0x5809)],
    9: [(0x4000, 0x4021), (0x418B, 0x4691),
        (0x63F3, 0x6402), (0x6480, 0x6485)],
    11: [(0x4000, 0x4100)],
    12: [(0x4000, 0x5DBC)],
    16: [(0x4031, 0x4044), (0x4AF0, 0x4E89), (0x51C8, 0x52E7), (0x52E7, 0x5428),
         (0x5428, 0x59F1)],
    18: [(0x4934, 0x4C84)],
    23: [(0x731F, 0x7717), (0x7717, 0x7E12)],
    24: [(0x4934, 0x4C84)],
    30: [(0x4000, 0x40E0)],
}


def gaps(bank):
    """Uncarved intervals of bank `bank` as (lo, hi) in $4000-$7fff."""
    carved = sorted(CARVED.get(bank, []))
    out, cur = [], 0x4000
    for lo, hi in carved:
        if lo > cur:
            out.append((cur, lo))
        cur = max(cur, hi)
    if cur < 0x8000:
        out.append((cur, 0x8000))
    return out


print("; GENERATED by tools/gen_banks.py -- do not hand-edit.")
print("; Raw bank data, pulled in as INCBIN from the local ROM at build time.")
print("; Curated ranges live in src/ (see CARVED in tools/gen_banks.py).")
print()
print('; Bank 0 tail, $3947-$3fff (everything after the SGB code).')
print('SECTION "Bank 0 tail", ROM0[$3947]')
print(f'    INCBIN "{ROM}", $3947, $6b9')  # $4000-$3947, NOT $b9 (fixed 2026-11-21)
print()
for bank in range(1, 32):
    for lo, hi in gaps(bank):
        off = bank * 0x4000 + (lo - 0x4000)
        print(f'SECTION "Bank {bank:02d} ${lo:04x}-${hi - 1:04x}", '
              f'ROMX[${lo:04x}], BANK[{bank}]')
        print(f'    INCBIN "{ROM}", ${off:05x}, ${hi - lo:04x}')
        print()
