#!/usr/bin/env python3
"""Slice-17 generator: finish the $2a0a $2b48 dispatch table.

  * Bank 9 (new file src/bank9slice17.asm): entries 26 ($6574),
    56 ($6cce), 89 ($6d8b) with their callees -- the $664a/$6d33
    jp-hl tables (8 entries, identical words), the shared $6660
    return routine, the $6490 sound/record routine called by $6cce,
    the $6d49/$6d5b signed-offset tables, the $6d9a 2-entry table,
    the $6696-$66b6 overlapping byte tables ($6696 [$c10a] remap,
    $66a0 [$c10e]>>1, $66a3 [$c10b]*3 records), the $6f9c [$dd18]
    byte table, and the 1-byte $6f9b ret (table entries 4/5).
  * Bank $1f (decimal 31, new file src/bank31slice17.asm): the
    remaining 35 $2b48 entries in table order -- 5 ($4000), 12
    ($64ee, 1-byte ret), 15 ($414e), 18 ($41ec), 19 ($442f), 20
    ($4567), 28 ($46b1), 30 ($484b), 35 ($4932), 46 ($4a95), 47
    ($4cd5), 48 ($4da6), 50 ($4e31), 51 ($503c), 52 ($79ec), 59
    ($5201), 60 ($53cb), 68 ($5455), 70 ($55c9), 71 ($56b6), 74
    ($5a3c), 75 ($5b42), 76 ($4fb9), 77 ($5e73), 78 ($5f29), 79
    ($616e), 80 ($61a5), 81 ($64ef), 82 ($66a3), 83 ($67bc), 88
    ($68dc), 90 ($68eb), 91 ($6a89), 92 ($7316), 93 ($7bf6) --
    each head plus its [$c10a] jp-hl table and the table routines
    the walk reaches, plus shared callees ($7050, $723e, $7ea6,
    $7de4, $7bf6). Table lengths are (first-routine - base)/2,
    verified against the ROM bytes (see TABLES31); entry 20's
    table is 3 entries, not 4 -- the 4th word ($403e) is routine
    0's first instruction (`ld a,$40`), and $403e is also e5's
    mid-routine `call $7f0a`, a coincidence, not an entry.
  * Bank 0 (new file src/bank0slice17.asm): $0f95-$0fa0, the
    scroll-clamp wrapper called from 8 state-16 timer bodies
    (and from timer-13's body $0968); its callee $152e was
    carved in slice 6. This closes the last unverified callee
    of the timer-13 body.
  * Bank $0a entries 66/67 ($33e3/$33ef): NO new carve -- the
    targets are already curated (bank-0 trampolines in
    src/bank0slice3.asm switching to bank 12, calling $4e15/
    $4e35, carved in src/bank12.asm). See PROGRESS.md slice 17
    for the mechanism proof (real path, not a table quirk).

Findings baked into this carve (see PROGRESS.md):
  * Timer 13 has FOUR $2b48 setters, not two (slice 15's
    "exactly two" was wrong -- the bank-$1f set was uncarved
    then): entry 34 (bank 8 $6d8a), entry 53 (bank $0a $5cd8),
    entry 46 (bank 31 $4aee, gated on [$c109] bit 3 SET, and it
    CLEARS the flag), entry 92 state 15 (bank 31 $780b, gated
    on Mario's position, no bit-3 test). All four share the
    $6ecd/$5c4f tail shape ([$dd18]=$07, [$dd21]=$ff,
    [$ff91]|=$c0, [$dd2b]=$09, [$dd2c]=$0b, timer=13).
  * The [$c109]-bit-3 arming path is entry 91 state 4 ($6c60):
    bit 2 set + bit 3 clear -> fall through to $6ca9
    (`ld hl,$c109; set 3,[hl]`, INLINE fall-through code, not
    a callable routine -- slice 15's "$6ca9 setter" framing
    was wrong). Entry 91's return continuation $5b55
    (`ld hl,$c109; res 3,[hl]; ret`) clears the flag on return.
    The $4add/$4d58 setters still have NO direct caller
    anywhere in the ROM (whole-ROM byte search: $4add zero
    hits at all; $4d58 one hit, bank 29 $54b4 inside data, not
    a call/jp/dw). Whether a 91-armed record ever becomes a
    46 record (no [$c105] rewrite to 46 exists -- the $7730
    transition table only ever writes $3f/$36) is unverified.
  * No carved handler in this slice writes timer 23/26/33/42:
    the only two `ldh [$ff90],a` sites in the whole bank-31
    carve are $4b70 and $7847, both literal $0d (13); bank 9
    has none. Timer 13 still resolves to timer 1 or 12 via
    bank-16 $5a11 (slice 16), never to the clear chain.

Regenerate with: python3 tools/gen_slice17.py
Outputs: src/bank9slice17.asm, src/bank31slice17.asm,
src/bank0slice17.asm (new files).
Also update tools/gen_banks.py CARVED (bank-9 and bank-31
ranges) and regenerate src/banks.asm; add INCLUDEs to
src/main.asm; split raw bank-0 A2b around $0f95.
The outputs are CHECKED IN; rerun after changing the config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile) -- hi inclusive.
CARVES = [
    # ---- bank 9: entries 26/56/89 + callees ----
    (9, 0x6490, 0x64CA, "Bank 9 $6490-$64ca $6cce callee routine",
     "src/bank9slice17.asm"),
    (9, 0x6574, 0x6649, "Bank 9 $6574-$6649 $2b48-entry-26 handler",
     "src/bank9slice17.asm"),
    (9, 0x6660, 0x6695, "Bank 9 $6660-$6695 shared return routine",
     "src/bank9slice17.asm"),
    (9, 0x66B7, 0x684E, "Bank 9 $66b7-$684e $664a-table routines 0-3,6-7",
     "src/bank9slice17.asm"),
    (9, 0x6908, 0x6961, "Bank 9 $6908-$6961 table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x696B, 0x6999, "Bank 9 $696b-$6999 table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x69AC, 0x6A07, "Bank 9 $69ac-$6a07 table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6A11, 0x6A3F, "Bank 9 $6a11-$6a3f table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6A53, 0x6A7C, "Bank 9 $6a53-$6a7c table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6A9C, 0x6AC7, "Bank 9 $6a9c-$6ac7 table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6AE7, 0x6B42, "Bank 9 $6ae7-$6b42 table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6B4C, 0x6B7A, "Bank 9 $6b4c-$6b7a table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6B8D, 0x6BE8, "Bank 9 $6b8d-$6be8 table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6BF2, 0x6C20, "Bank 9 $6bf2-$6c20 table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6C34, 0x6C5E, "Bank 9 $6c34-$6c5e table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6C7E, 0x6CA9, "Bank 9 $6c7e-$6ca9 table-routine callee",
     "src/bank9slice17.asm"),
    (9, 0x6CB7, 0x6D32, "Bank 9 $6cb7-$6d32 $2b48-entry-56 handler",
     "src/bank9slice17.asm"),
    (9, 0x6D8B, 0x6D99, "Bank 9 $6d8b-$6d99 $2b48-entry-89 head",
     "src/bank9slice17.asm"),
    (9, 0x6D9E, 0x6DD3, "Bank 9 $6d9e-$6dd3 $6d9a-entry-0 routine",
     "src/bank9slice17.asm"),
    (9, 0x6DE0, 0x6E62, "Bank 9 $6de0-$6e62 $6d9a-entry-1 routine",
     "src/bank9slice17.asm"),
    (9, 0x6E6A, 0x6E93, "Bank 9 $6e6a-$6e93 $6d9a-entry-0 callee",
     "src/bank9slice17.asm"),
    (9, 0x6EB1, 0x6ED8, "Bank 9 $6eb1-$6ed8 $6d9a-entry-0 callee",
     "src/bank9slice17.asm"),
    (9, 0x6F34, 0x6F64, "Bank 9 $6f34-$6f64 $6d9a-entry-1 callee",
     "src/bank9slice17.asm"),
    # ---- bank 31 ($1f): remaining 35 $2b48 entries ----
    (31, 0x4000, 0x4052, "Bank 31 $4000-$4052 $2b48-entry-5 handler",
     "src/bank31slice17.asm"),
    (31, 0x4059, 0x40E0, "Bank 31 $4059-$40e0 $4053-table routines",
     "src/bank31slice17.asm"),
    (31, 0x414E, 0x4161, "Bank 31 $414e-$4161 $2b48-entry-15 head",
     "src/bank31slice17.asm"),
    (31, 0x416C, 0x41FA, "Bank 31 $416c-$41fa $4162-table routines",
     "src/bank31slice17.asm"),
    (31, 0x4205, 0x4498, "Bank 31 $4205-$4498 $41fb-table routines + "
     "entry-19 handler", "src/bank31slice17.asm"),
    (31, 0x4567, 0x4575, "Bank 31 $4567-$4575 $2b48-entry-20 head",
     "src/bank31slice17.asm"),
    (31, 0x457C, 0x467E, "Bank 31 $457c-$467e $4576-table routines",
     "src/bank31slice17.asm"),
    (31, 0x4689, 0x46BF, "Bank 31 $4689-$46bf $4576-entry-2 routine",
     "src/bank31slice17.asm"),
    (31, 0x46C8, 0x48C6, "Bank 31 $46c8-$48c6 $46c0-table routines + "
     "entry-30 handler", "src/bank31slice17.asm"),
    (31, 0x4932, 0x4940, "Bank 31 $4932-$4940 $2b48-entry-35 head",
     "src/bank31slice17.asm"),
    (31, 0x4945, 0x49AF, "Bank 31 $4945-$49af $4941-table routines",
     "src/bank31slice17.asm"),
    (31, 0x4A95, 0x4AA3, "Bank 31 $4a95-$4aa3 $2b48-entry-46 head",
     "src/bank31slice17.asm"),
    (31, 0x4AAA, 0x4C9B, "Bank 31 $4aaa-$4c9b $4aa4-table routines",
     "src/bank31slice17.asm"),
    (31, 0x4CD4, 0x4CE3, "Bank 31 $4cd4-$4ce3 $2b48-entry-47 head",
     "src/bank31slice17.asm"),
    (31, 0x4CEA, 0x4D89, "Bank 31 $4cea-$4d89 $4ce4-table routines",
     "src/bank31slice17.asm"),
    (31, 0x4DA6, 0x4DB4, "Bank 31 $4da6-$4db4 $2b48-entry-48 head",
     "src/bank31slice17.asm"),
    (31, 0x4DBB, 0x4E3F, "Bank 31 $4dbb-$4e3f $4db5-table routines",
     "src/bank31slice17.asm"),
    (31, 0x4E48, 0x4F9A, "Bank 31 $4e48-$4f9a $4e40-table routines",
     "src/bank31slice17.asm"),
    (31, 0x4FB9, 0x4FD2, "Bank 31 $4fb9-$4fd2 $2b48-entry-76 handler",
     "src/bank31slice17.asm"),
    (31, 0x503C, 0x506B, "Bank 31 $503c-$506b $2b48-entry-51 handler",
     "src/bank31slice17.asm"),
    (31, 0x5201, 0x520F, "Bank 31 $5201-$520f $2b48-entry-59 head",
     "src/bank31slice17.asm"),
    (31, 0x5218, 0x53D9, "Bank 31 $5218-$53d9 $5210-table routines",
     "src/bank31slice17.asm"),
    (31, 0x53E0, 0x5406, "Bank 31 $53e0-$5406 $53da-entry-0 routine",
     "src/bank31slice17.asm"),
    (31, 0x540E, 0x5444, "Bank 31 $540e-$5444 $53da-table routines",
     "src/bank31slice17.asm"),
    (31, 0x544B, 0x5463, "Bank 31 $544b-$5463 $53da-entry-2 routine",
     "src/bank31slice17.asm"),
    (31, 0x5468, 0x55D7, "Bank 31 $5468-$55d7 $5464-table routines",
     "src/bank31slice17.asm"),
    (31, 0x55DE, 0x56C4, "Bank 31 $55de-$56c4 $55d8-table routines",
     "src/bank31slice17.asm"),
    (31, 0x56CF, 0x57A0, "Bank 31 $56cf-$57a0 $56c5-table routines",
     "src/bank31slice17.asm"),
    (31, 0x57C1, 0x589B, "Bank 31 $57c1-$589b $56c5-table routines",
     "src/bank31slice17.asm"),
    (31, 0x5A3C, 0x5A8A, "Bank 31 $5a3c-$5a8a $2b48-entry-74 handler",
     "src/bank31slice17.asm"),
    (31, 0x5A91, 0x5B5A, "Bank 31 $5a91-$5b5a $5a8b-table routines + "
     "$5b55 return", "src/bank31slice17.asm"),
    (31, 0x5B6D, 0x5E81, "Bank 31 $5b6d-$5e81 $5b5b-table routines",
     "src/bank31slice17.asm"),
    (31, 0x5E88, 0x5F37, "Bank 31 $5e88-$5f37 $5e82-table routines",
     "src/bank31slice17.asm"),
    (31, 0x5F4A, 0x6151, "Bank 31 $5f4a-$6151 $5f38-table routines",
     "src/bank31slice17.asm"),
    (31, 0x616E, 0x6187, "Bank 31 $616e-$6187 $2b48-entry-79 handler",
     "src/bank31slice17.asm"),
    (31, 0x61A5, 0x6243, "Bank 31 $61a5-$6243 $2b48-entry-80 handler",
     "src/bank31slice17.asm"),
    (31, 0x64EE, 0x64FD, "Bank 31 $64ee-$64fd entry-12 ret + entry-81 "
     "head", "src/bank31slice17.asm"),
    (31, 0x650C, 0x66B1, "Bank 31 $650c-$66b1 $64fe-table routines",
     "src/bank31slice17.asm"),
    (31, 0x66BC, 0x67F7, "Bank 31 $66bc-$67f7 $66b2-table routines",
     "src/bank31slice17.asm"),
    (31, 0x68DC, 0x68F9, "Bank 31 $68dc-$68f9 $2b48-entry-88 handler",
     "src/bank31slice17.asm"),
    (31, 0x6900, 0x6A97, "Bank 31 $6900-$6a97 $68fa-table routines",
     "src/bank31slice17.asm"),
    (31, 0x6ABE, 0x6B52, "Bank 31 $6abe-$6b52 $6a98-table routines",
     "src/bank31slice17.asm"),
    (31, 0x6B6F, 0x6CC1, "Bank 31 $6b6f-$6cc1 $6a98-table routines",
     "src/bank31slice17.asm"),
    (31, 0x6CC7, 0x6D8D, "Bank 31 $6cc7-$6d8d $6a98-entry-5 routine",
     "src/bank31slice17.asm"),
    (31, 0x6DAA, 0x6DF5, "Bank 31 $6daa-$6df5 $6a98-entry-6 routine",
     "src/bank31slice17.asm"),
    (31, 0x6E0A, 0x6E83, "Bank 31 $6e0a-$6e83 $6a98-entry-7 routine",
     "src/bank31slice17.asm"),
    (31, 0x6E95, 0x6EB9, "Bank 31 $6e95-$6eb9 $6a98-entry-8 routine",
     "src/bank31slice17.asm"),
    (31, 0x6F89, 0x6FDD, "Bank 31 $6f89-$6fdd shared routine",
     "src/bank31slice17.asm"),
    (31, 0x7050, 0x708E, "Bank 31 $7050-$708e shared routine",
     "src/bank31slice17.asm"),
    (31, 0x723E, 0x7305, "Bank 31 $723e-$7305 $6c60 armed branch",
     "src/bank31slice17.asm"),
    (31, 0x7316, 0x7324, "Bank 31 $7316-$7324 $2b48-entry-92 head",
     "src/bank31slice17.asm"),
    (31, 0x7351, 0x7370, "Bank 31 $7351-$7370 $7325-table routines",
     "src/bank31slice17.asm"),
    (31, 0x7374, 0x73D0, "Bank 31 $7374-$73d0 $7325-table routines",
     "src/bank31slice17.asm"),
    (31, 0x73D4, 0x7433, "Bank 31 $73d4-$7433 $7325-table routines",
     "src/bank31slice17.asm"),
    (31, 0x7437, 0x74D4, "Bank 31 $7437-$74d4 $7325-table routines",
     "src/bank31slice17.asm"),
    (31, 0x74D8, 0x775E, "Bank 31 $74d8-$775e $7325-table routines",
     "src/bank31slice17.asm"),
    (31, 0x7775, 0x792D, "Bank 31 $7775-$792d $7325-table routines",
     "src/bank31slice17.asm"),
    (31, 0x7934, 0x7A11, "Bank 31 $7934-$7a11 $7325-table routines",
     "src/bank31slice17.asm"),
    (31, 0x7BF6, 0x7CA0, "Bank 31 $7bf6-$7ca0 $2b48-entry-93 handler",
     "src/bank31slice17.asm"),
    (31, 0x7CE2, 0x7D82, "Bank 31 $7ce2-$7d82 entry-93 callee",
     "src/bank31slice17.asm"),
    (31, 0x7DE4, 0x7E06, "Bank 31 $7de4-$7e06 entry-80 callee",
     "src/bank31slice17.asm"),
    (31, 0x7EA6, 0x7F00, "Bank 31 $7ea6-$7f00 shared routines",
     "src/bank31slice17.asm"),
    # ---- bank 0: timer-13 body callee ----
    (0, 0x0F95, 0x0FA0, "Bank 0 $0f95-$0fa0 scroll-clamp wrapper",
     "src/bank0slice17.asm"),
]

# [$c10a] jp-hl tables: (entry, base, [entries]). Lengths are
# (first-routine - base)/2 from the ROM bytes; the generator
# asserts every value.
TABLES31 = {
    5: (0x4053, [0x4059, 0x40B3, 0x40BF]),
    15: (0x4162, [0x416C, 0x4193, 0x41B4, 0x41C7, 0x41D9]),
    18: (0x41FB, [0x4205, 0x423F, 0x4272, 0x429F, 0x433C]),
    20: (0x4576, [0x457C, 0x4590, 0x4689]),
    28: (0x46C0, [0x46C8, 0x470F, 0x4811, 0x4840]),
    35: (0x4941, [0x4945, 0x4977]),
    46: (0x4AA4, [0x4AAA, 0x4AEE, 0x4CD4]),
    47: (0x4CE4, [0x4CEA, 0x4D06, 0x4D0F]),
    48: (0x4DB5, [0x4DBB, 0x4DE9, 0x4E17]),
    50: (0x4E40, [0x4E48, 0x4E8D, 0x4EFE, 0x4F22]),
    59: (0x5210, [0x5218, 0x527E, 0x5376, 0x53B3]),
    60: (0x53DA, [0x53E0, 0x540E, 0x544B]),
    68: (0x5464, [0x5468, 0x5484]),
    70: (0x55D8, [0x55DE, 0x561B, 0x56A8]),
    71: (0x56C5, [0x56CF, 0x570B, 0x5734, 0x57C1, 0x57EE]),
    74: (0x5A8B, [0x5A91, 0x5AE7, 0x5B2C]),
    75: (0x5B5B, [0x5B6D, 0x5BAB, 0x5C1A, 0x5C9B, 0x5CF6, 0x5CF7,
                 0x5D94, 0x5D9C, 0x5DC0]),
    77: (0x5E82, [0x5E88, 0x5EB8, 0x5F21]),
    78: (0x5F38, [0x5F4A, 0x5F92, 0x604A, 0x6074, 0x60AD, 0x60CA,
                 0x60D1, 0x5F5D, 0x60DE]),
    81: (0x64FE, [0x650C, 0x653D, 0x6628, 0x6632, 0x663C, 0x666B,
                 0x6683]),
    82: (0x66B2, [0x66BC, 0x6707, 0x6750, 0x67B1, 0x672C]),
    90: (0x68FA, [0x6900, 0x694B, 0x6A5A]),
    91: (0x6A98, [0x6ABE, 0x6B6F, 0x6BA6, 0x6BC9, 0x6C60, 0x6CC7,
                 0x6DAA, 0x6E0A, 0x6E95, 0x6ED6, 0x6FFA, 0x704B,
                 0x708F, 0x70D0, 0x70DF, 0x7161, 0x71BD, 0x7222,
                 0x722C]),  # Slice 19 CORRECTS slice 17's 9-entry extent
                 # to 19: entries 9-18 continue the increasing run and
                 # are all decoded instruction starts (slice 18 carved
                 # entries 10-13 without noting the table; slice 19
                 # carves 9 and 14-18).
    92: (0x7325, [0x7351, 0x7352, 0x7374, 0x73D4, 0x7437, 0x74D8,
                 0x74F1, 0x75CE, 0x7615, 0x7643, 0x7775, 0x77A4,
                 0x77B0, 0x77E3, 0x77F2, 0x780B, 0x787B, 0x78C1,
                 0x78E5, 0x7934, 0x7989, 0x79DD]),
}

# Bank 9 tables: (base, [entries]).
# Slice 21 corrects slice 17's 8-entry read: both tables are 10 entries
# ($664a-$665d, $6d33-$6d46). Evidence: the [$c10a] writers in the
# carved bank-9 routines max out at 9 ($6b63 writes 9; the $6696 remap
# outputs max 9), and the words at $665a-$665d / $6d43-$6d46 are
# $684f/$6893 -- the slice-18 map-sample routines, the same family as
# the table routines. The trailing words $665e ($68d7) and $6d47
# ($6d6d) are NOT claimed as entry 10: no [$c10a]=10 writer exists in
# carved code, so $68d7/$6d6d stay entry-UNVERIFIED (emitted below as
# single dw with that note).
TABLES9 = {
    0x664A: [0x66B7, 0x66FB, 0x673F, 0x6783, 0x6F9B, 0x6F9B, 0x67C7,
             0x680B, 0x684F, 0x6893],
    0x6D33: [0x66B7, 0x66FB, 0x673F, 0x6783, 0x6F9B, 0x6F9B, 0x67C7,
             0x680B, 0x684F, 0x6893],
    0x6D9A: [0x6D9E, 0x6DE0],
}
# Bank 9 signed-offset tables (dw values, not code addresses).
OFFSETS9 = {
    0x6D49: [0x0104, 0xFF80, 0x007C, 0x0008, 0x0100, 0xFFFC, 0xFF84,
             0x0088],
    0x6D5B: [0xFF84, 0x0100, 0x0088, 0xFFFC, 0x0008, 0x0104, 0x007C,
             0xFF80],
}

# Meaningful entry labels: (bank, addr) -> name.
LABELS = {}
for _a in (0x6490, 0x6574, 0x664A, 0x6660, 0x6696, 0x66B7, 0x66FB, 0x673F,
           0x6783, 0x67C7, 0x680B, 0x6CCE, 0x6D33, 0x6D49, 0x6D5B, 0x6D8B,
           0x6D9A, 0x6D9E, 0x6DD4, 0x6DE0, 0x6F9B, 0x6F9C):
    LABELS[(9, _a)] = f"Bank9_{_a:04X}"
for _e, (_b, _ents) in TABLES31.items():
    LABELS[(31, _b)] = f"Bank31_{_b:04X}"
    for _v in _ents:
        LABELS.setdefault((31, _v), f"Bank31_{_v:04X}")
for _a in (0x4000, 0x414E, 0x41EC, 0x442F, 0x4567, 0x46B1, 0x484B, 0x4932,
           0x4A95, 0x4CD5, 0x4DA6, 0x4E31, 0x503C, 0x79EC, 0x5201, 0x53CB,
           0x5455, 0x55C9, 0x56B6, 0x5A3C, 0x5B42, 0x4FB9, 0x5E73, 0x5F29,
           0x616E, 0x61A5, 0x64EE, 0x64EF, 0x66A3, 0x67BC, 0x68DC, 0x68EB,
           0x6A89, 0x7316, 0x7BF6, 0x5B55, 0x4AEE, 0x4B70, 0x6C60, 0x6CA9,
           0x780B, 0x7847, 0x6D8E, 0x6CC2, 0x7050, 0x723E, 0x7EA6, 0x7DE4,
           0x7BF6, 0x7CE2):
    LABELS.setdefault((31, _a), f"Bank31_{_a:04X}")
LABELS[(0, 0x0F95)] = "Bank0_0F95"


def jr_targets_in(instrs, lo, hi):
    """Addresses in [lo, hi] targeted by a jr inside the carve."""
    out = set()
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
            out.add(tgt)
    return out


def fmt_instr(bank, addr, text, kind, tgt, lo, hi, jr_targets):
    """One instruction line, with jr targets inside the carve rewritten
    to the named label (or the jr_ label) instead of a raw address."""
    if (bank, addr) in LABELS:
        label = f"{LABELS[(bank, addr)]}::"
    elif addr in jr_targets:
        label = f"jr_{bank:03x}_{addr:04x}:"
    else:
        label = None
    if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
        if (bank, tgt) in LABELS:
            tgt_label = LABELS[(bank, tgt)]
        else:
            tgt_label = f"jr_{bank:03x}_{tgt:04x}"
        text = re.sub(r"\$[0-9a-f]{4}$", tgt_label, text)
    line = f"    {text:<48} ; ${addr:04x}"
    return (label + "\n" + line) if label else line


def emit_carve(rom, bank, lo, hi, title, instrs):
    section = "ROM0" if bank == 0 else "ROMX"
    bankarg = f", BANK[{bank}]" if bank != 0 else ""
    out = [f"; Slice 17: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/gen_slice17.py from the ROM bytes via",
           "; tools/gb_rd.py (recursive descent, not mgbdis' linear",
           "; sweep). Byte-match (`make`) arbitrates.",
           f'SECTION "{title}", {section}[${lo:04x}]{bankarg}']
    jr_targets = jr_targets_in(instrs, lo, hi)
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                and lo <= tgt <= hi and tgt not in instrs:
            print(f"ERROR: bank {bank} ${addr:04x} {text} targets "
                  f"${tgt:04x}, not a decoded instruction",
                  file=sys.stderr)
            sys.exit(1)
    addr = lo
    while addr <= hi:
        if addr in instrs:
            ln, text, kind, tgt = instrs[addr]
            out.append(fmt_instr(bank, addr, text, kind, tgt,
                                 lo, hi, jr_targets))
            addr += ln
        else:
            # Uncovered bytes inside the carve: honest data.
            run = []
            while addr <= hi and addr not in instrs:
                run.append(rom[file_off(bank, addr)])
                addr += 1
            label = LABELS.get((bank, addr - len(run)))
            if label:
                out.append(f"{label}::")
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def emit_dw_table(rom, bank, lo, entries, title, expected=None, note=None):
    """A dw table: `entries` (addr, comment) pairs, verified against
    the ROM bytes when `expected` (list of values) is given."""
    label = LABELS.get((bank, lo))
    out = [f"; Slice 17: {title} -- bank {bank} ${lo:04x}-"
           f"${lo + 2 * len(entries) - 1:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/gen_slice17.py; values read straight "
               "from the ROM.")
    out.append(f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]')
    if label:
        out.append(f"{label}::")
    for i, (addr, comment) in enumerate(entries):
        val = rom[file_off(bank, lo + 2 * i)] | \
            (rom[file_off(bank, lo + 2 * i + 1)] << 8)
        if expected is not None:
            assert val == expected[i], \
                f"bank {bank} ${lo + 2 * i:04x}: dw ${val:04x} != " \
                f"expected ${expected[i]:04x}"
        out.append(f"    dw ${val:04x}  ; {comment}")
    return "\n".join(out) + "\n"


def emit_db(rom, bank, lo, hi, title, note=None):
    """A raw-byte range, 8 bytes per db line, with a section header."""
    label = LABELS.get((bank, lo))
    out = [f"; Slice 17: {title} -- bank {bank} ${lo:04x}-${hi:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/gen_slice17.py; bytes read straight "
               "from the ROM.")
    out.append(f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]')
    if label:
        out.append(f"{label}::")
    addr = lo
    while addr <= hi:
        chunk = [rom[file_off(bank, a)] for a in
                 range(addr, min(addr + 8, hi + 1))]
        out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
        addr += len(chunk)
    return "\n".join(out) + "\n"


def emit_ret1(rom, bank, addr, title, note=None):
    """A 1-byte `ret` ($c9), verified against the ROM."""
    assert rom[file_off(bank, addr)] == 0xC9, \
        f"bank {bank} ${addr:04x} is not $c9"
    label = LABELS.get((bank, addr))
    out = [f"; Slice 17: {title} -- bank {bank} ${addr:04x} 1-byte ret."]
    if note:
        out.append(f"; {note}")
    out.append("; Verified byte $c9.")
    out.append(f'SECTION "{title}", ROMX[${addr:04x}], BANK[{bank}]')
    if label:
        out.append(f"{label}::")
    out.append(f"    ret                                              ; ${addr:04x}")
    return "\n".join(out) + "\n"


def main():
    rom = open(ROM, "rb").read()
    seeds9 = [0x6574, 0x6CCE, 0x6D8B, 0x6660, 0x66B7, 0x66FB, 0x673F,
              0x6783, 0x67C7, 0x680B, 0x6D9E, 0x6DE0, 0x684F, 0x6893]
    seeds31 = [0x4000, 0x64EE, 0x414E, 0x41EC, 0x442F, 0x4567, 0x46B1,
               0x484B, 0x4932, 0x4A95, 0x4CD5, 0x4DA6, 0x4E31, 0x503C,
               0x79EC, 0x5201, 0x53CB, 0x5455, 0x55C9, 0x56B6, 0x5A3C,
               0x5B42, 0x4FB9, 0x5E73, 0x5F29, 0x616E, 0x61A5, 0x64EF,
               0x66A3, 0x67BC, 0x68DC, 0x68EB, 0x6A89, 0x7316, 0x7BF6,
               0x5B55]
    for _base, _ents in TABLES31.values():
        seeds31 += _ents
    seeds0 = [0x0F95]
    reached9, rst08_9, notes9 = walk(9, seeds9)
    reached31, rst08_31, notes31 = walk(31, seeds31)
    reached0, rst08_0, notes0 = walk(0, seeds0)
    for n in notes9 + notes31 + notes0:
        print("note:", n, file=sys.stderr)
    print(f"walk bank 9: {len(reached9)} instrs; "
          f"bank 31: {len(reached31)} instrs; "
          f"bank 0: {len(reached0)} instrs", file=sys.stderr)
    assert not rst08_9 and not rst08_31 and not rst08_0, \
        f"unexpected rst $08: {rst08_9} {rst08_31} {rst08_0}"
    # Every table entry must be a decoded instruction start.
    for _base, _ents in TABLES31.values():
        for _v in _ents:
            assert _v in reached31, f"bank 31 table entry ${_v:04x} " \
                "not decoded"
    for _base, _ents in TABLES9.items():
        for _v in _ents:
            assert _v in reached9 or _v == 0x6F9B, \
                f"bank 9 table entry ${_v:04x} not decoded"
    by_file = {}
    for bank, lo, hi, title, outfile in CARVES:
        reached = {9: reached9, 31: reached31, 0: reached0}[bank]
        instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
        covered = set()
        for a, (ln, *_r) in instrs.items():
            covered.update(range(a, a + ln))
        assert covered == set(range(lo, hi + 1)), \
            f"bank {bank} ${lo:04x}-${hi:04x}: uncovered bytes " \
            f"{sorted(set(range(lo, hi + 1)) - covered)[:8]}"
        by_file.setdefault(outfile, []).append(
            (bank, lo, hi, title, instrs))

    # ---- bank 9 data carves ----
    b9_data = []
    b9_data.append(emit_dw_table(
        rom, 9, 0x664A,
        [(0x664A + 2 * i, f"[$c10a]={i}") for i in range(10)],
        "Bank 9 $664a-$665d [$c10a] table (entries 26/56)",
        expected=TABLES9[0x664A],
        note="Slice 21: 10 entries, not 8 -- [$c10a] reaches 9 (see "
             "TABLES9 note)."))
    b9_data.append(emit_dw_table(
        rom, 9, 0x6D33,
        [(0x6D33 + 2 * i, f"[$c10a]={i}") for i in range(10)],
        "Bank 9 $6d33-$6d46 [$c10a] table (entry 56)",
        expected=TABLES9[0x6D33],
        note="Identical words to the $664a table -- a second copy. "
             "Slice 21: 10 entries, not 8."))
    b9_data.append(emit_dw_table(
        rom, 9, 0x665E,
        [(0x665E, "not a table entry -- see note")],
        "Bank 9 $665e trailing word",
        expected=[0x68D7],
        note="NOT claimed as $664a entry 10: no [$c10a]=10 writer "
             "exists in carved code. The word points at $68d7, a "
             "coherent routine of the same family (slice 18), whose "
             "entry mechanism is unverified."))
    b9_data.append(emit_dw_table(
        rom, 9, 0x6D47,
        [(0x6D47, "not a table entry -- see note")],
        "Bank 9 $6d47 trailing word",
        expected=[0x6D6D],
        note="NOT claimed as $6d33 entry 10: no [$c10a]=10 writer "
             "exists in carved code. The word points at $6d6d, a "
             "coherent routine of the same family (slice 21), whose "
             "entry mechanism is unverified."))
    b9_data.append(emit_dw_table(
        rom, 9, 0x6D49,
        [(0x6D49 + 2 * i, f"[$c10b]={i}") for i in range(8)],
        "Bank 9 $6d49-$6d58 signed-offset table (entry 56)",
        expected=OFFSETS9[0x6D49],
        note="Offsets added to the map pointer DE; selected when "
             "[$c10e] bit 0 is clear."))
    b9_data.append(emit_dw_table(
        rom, 9, 0x6D5B,
        [(0x6D5B + 2 * i, f"[$c10b]={i}") for i in range(8)],
        "Bank 9 $6d5b-$6d6a signed-offset table (entry 56)",
        expected=OFFSETS9[0x6D5B],
        note="Same 8 offsets as $6d49, permuted; selected when "
             "[$c10e] bit 0 is set."))
    b9_data.append(emit_dw_table(
        rom, 9, 0x6D9A,
        [(0x6D9A + 2 * i, f"[$c10a]={i}") for i in range(2)],
        "Bank 9 $6d9a-$6d9d [$c10a] table (entry-89 head)",
        expected=TABLES9[0x6D9A],
        note="Only 2 entries: the word at $6d9e ($0efa) is the first "
             "two bytes of routine 0's `ld a,[$c10e]` (fa 0e c1), "
             "not a 3rd entry."))
    b9_data.append(emit_ret1(
        rom, 9, 0x6F9B, "Bank 9 $6f9b 1-byte ret",
        note="$664a/$6d33 table entries 4 and 5 both point here."))
    b9_data.append(emit_db(
        rom, 9, 0x6DD4, 0x6DDF, "Bank 9 $6dd4-$6ddf 12-byte data blob",
        note="Pointed to by $6da5 (`ld hl,$6dd4`) -- a data pointer, "
             "not a code entry (the earlier $6dd4 seed was spurious: "
             "nothing jumps or calls here, and a linear decode gives "
             "nonsense -- rst $38, ld b,b). Bytes: 00 20 ff e0 00 40 "
             "ff c0 00 80 ff 80. Meaning unresolved."))
    b9_data.append(emit_db(
        rom, 9, 0x6696, 0x66B6, "Bank 9 $6696-$66b6 byte tables",
        note="$6696: [$c10a] remap (8 bytes, 07 06 09 08 04 05 01 "
             "00); $66a0: [$c10e]>>1 table (3 bytes); $66a3: "
             "[$c10b]*3 records (12 bytes, $66a3-$66ae); $66af-$66b6 "
             "unresolved (8 bytes). One blob, overlapping views."))
    b9_data.append(emit_db(
        rom, 9, 0x6F9C, 0x6FAB, "Bank 9 $6f9c-$6fab [$dd18] byte table",
        note="Indexed by [$dd18] (0-12); values 0/1, $ff at "
             "index 12+. Read by entry 26 ($6574) into [$c1f3]."))
    by_file.setdefault("src/bank9slice17.asm", []).extend(b9_data)

    # ---- bank 31 dw tables ----
    b31_data = []
    for entry, (base, vals) in sorted(TABLES31.items()):
        b31_data.append(emit_dw_table(
            rom, 31, base,
            [(base + 2 * i, f"[$c10a]={i}") for i in range(len(vals))],
            f"Bank 31 ${base:04x}-${base + 2 * len(vals) - 1:04x} "
            f"[$c10a] table ($2b48 entry {entry})",
            expected=vals))
    b31_data.append(emit_db(
        rom, 31, 0x6CC2, 0x6CC6, "Bank 31 $6cc2-$6cc6 5-byte template",
        note="Copied to $dd81 by entry-91 $6c60 (5 bytes)."))
    b31_data.append(emit_db(
        rom, 31, 0x6D8E, 0x6DA1, "Bank 31 $6d8e-$6da1 20-byte template",
        note="Copied to $c1ab by entry-91 $6c60 (via $6d12, "
             "$106e), then $1097; byte 14 is $aa, byte 18 is $00 "
             "-- the spawned record is NOT born armed and its "
             "type is not 46, so this is not the 91->46 link."))
    by_file.setdefault("src/bank31slice17.asm", []).extend(b31_data)

    for outfile, parts in by_file.items():
        rendered = []
        for part in parts:
            if isinstance(part, str):
                rendered.append(part)
            else:
                bank, lo, hi, title, instrs = part
                rendered.append(emit_carve(rom, bank, lo, hi, title,
                                           instrs))
        with open(outfile, "w") as f:
            f.write("\n".join(rendered))
        print(f"wrote {outfile} ({sum(len(p) for p in rendered)} bytes)")


if __name__ == "__main__":
    main()
