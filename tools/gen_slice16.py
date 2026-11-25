#!/usr/bin/env python3
"""Slice-16 generator: carve the $2a0a $2b48 handlers actually firing
every frame in stage 1-1.

  * Bank $1f (decimal 31, new file src/bank31.asm -- the bank-31
    sections are BANK[31]; do NOT confuse with src/bank10.asm, which
    is hex bank $10 = decimal 16):
    - Entry 7  $40e1 (jp-hl head via [$c10a]) + the $40f0 table
      (3 dw: $40f6, $411e, $4142) + routines $40f6-$414d.
    - Entry 32 $48e3-$4931 (the only non-dispatch head of the four:
      sets bit 5 of [$c103], clamps the [$c0fc]/[$c0fd] pointer to
      $00c0, sets bit 0 of [$c109], and on [$c109] bit 0 calls $7f32
      + jp $7f0a -- the record-kill / link-remove path).
    - Entry 45 $49b0 (jp-hl head) + the $49bf table (2 dw: $49c3,
      $49fd) + routines $49c3-$4a94.
    - Entry 72 $589c (jp-hl head) + the $58ab table (2 dw: $58af,
      $58dc) + routines $58af-$58e1.
    - Entry 73 $58e2 ([$c109] bit 4 -> [$c0fe]=$ff, else jp-hl head)
      + the $58fe table (8 dw) + routines $590e-$5a3b.
    - Shared callees: $7ca1-$7ce1 (incl. $7cb8), $7d83-$7db8,
      $7e07-$7e43, $7e7e-$7ea5, $7f01-$7f5e (incl. $7f0a/$7f32/$7f39).
  * Bank 8 (new file src/bank8slice16.asm): entry 1's missing pieces
    -- the $5f6b [$c10a] table (8 dw: $6473, $5f7b, $609d, $7310,
    $63b5, $6646, $63f0, $60e9; the head $5f5c-$5f6a was carved in
    slice 15) + the three uncarved table routines $5f7b-$609c,
    $60e9-$610f, $63f0-$6442. The other five targets were already
    carved in slice 15 ($6473, $609d, $7310, $63b5 in their spans;
    $6646 inside $6473-$6667).

CORRECTION to slice 15 sec.8 / the slice-16 task text: $58e2 is
$2b48 entry **73**, not 72. Entry 72 is $589c. The live [$c105]
values seen in 1-1 were {7, 32, 45, 72}, so entry 72 = $589c is
the firing one; entry 73 ($58e2) is carved here too because it
sits adjacent (its head starts the byte after the entry-72
routines end) and shares the [$c10a] dispatch shape.

Why this carve (see PROGRESS.md slice 15 sec.4): in 1-1 the $2a0a
dispatch actually uses $2b48 entries 1, 7, 32, 45, 72 (live
[$c105] byte-14 values {0,1,2,3,6,7,32,45,72} -- the 0/1/2/3/6/7
go through the $7730 pre-dispatch; 32/45/72 are the bank-$1f
handlers here, 1 is bank-8 $5f5c, 7 is bank-$1f $40e1). Bank $1f
was almost entirely uncarved before this slice.

Regenerate with: python3 tools/gen_slice16.py
Outputs: src/bank31.asm, src/bank8slice16.asm, src/bank0aslice16.asm,
src/bank16slice16.asm (new files).
Also update tools/gen_banks.py CARVED (new key 31, bank-8 and
bank-10 ranges) and regenerate src/banks.asm; add INCLUDEs to
src/main.asm.
The outputs are CHECKED IN; rerun after changing the config.

  * Decimal bank 10 ($0a, new file src/bank0aslice16.asm): the
    $2b48-handler set, walked whole from every entry head --
    $4000-$46e2 (14 entry heads), the $46e3-$47a2 byte table (db),
    $47a3-$4809 (entry 0), $4add/$4d58 (the [$c109]-bit-3 setters,
    no direct caller anywhere in the ROM -- see PROGRESS.md),
    $4dbe-$4e55 (entry 10), $5192 (entry 11), $51e0-$5211,
    $522b/$532b (entries 13/14), $5412 (entry 16), $568c
    (entry 17), $56db (entry 31), $57bb (entry 33), $5909
    (entry 36), the $5cf8-table routines $5d08-$5d5d / $5d86-$5e09
    / $5e88-$5ec9 (entries 0-3/6-7; the $5c4f-$5cf7 timer-13
    routine + $5cf8 table were carved in slice 15), $60f3-$612d,
    $63a3 (entry 55), $6582 (entry 58), $678c (entry 62), $69be
    (entry 84), $6af9 (entry 85), $6d77 (entry 49), $6e42
    (entry 86), $6f3d (entry 87), $705f (entry 63), and the shared
    routines $7951-$79e9 / $7ab8-$7b11 / $7b3f-$7b6b / $7c24-$7c56
    ($7c57+ was carved in slice 15).
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile, seeds) -- hi inclusive.
CARVES = [
    # ---- bank 31 ($1f) ----
    (31, 0x40E1, 0x40EF, "Bank 31 $40e1-$40ef $2b48-entry-7 head",
     "src/bank31.asm", [0x40E1]),
    (31, 0x40F6, 0x414D, "Bank 31 $40f6-$414d $40f0-table routines",
     "src/bank31.asm", [0x40F6, 0x411E, 0x4142]),
    (31, 0x48E3, 0x4931, "Bank 31 $48e3-$4931 $2b48-entry-32 handler",
     "src/bank31.asm", [0x48E3]),
    (31, 0x49B0, 0x49BE, "Bank 31 $49b0-$49be $2b48-entry-45 head",
     "src/bank31.asm", [0x49B0]),
    (31, 0x49C3, 0x4A94, "Bank 31 $49c3-$4a94 $49bf-table routines",
     "src/bank31.asm", [0x49C3, 0x49FD]),
    (31, 0x589C, 0x58AA, "Bank 31 $589c-$58aa $2b48-entry-72 head",
     "src/bank31.asm", [0x589C]),
    (31, 0x58AF, 0x58E1, "Bank 31 $58af-$58e1 $58ab-table routines",
     "src/bank31.asm", [0x58AF, 0x58DC]),
    (31, 0x58E2, 0x58FD, "Bank 31 $58e2-$58fd $2b48-entry-73 head",
     "src/bank31.asm", [0x58E2]),
    (31, 0x590E, 0x5A3B, "Bank 31 $590e-$5a3b $58fe-table routines",
     "src/bank31.asm", [0x590E, 0x5934, 0x5968, 0x5990, 0x59B2, 0x59D2,
                        0x59EB, 0x5A1D]),
    (31, 0x7CA1, 0x7CE1, "Bank 31 $7ca1-$7ce1 shared routines",
     "src/bank31.asm", [0x7CA1, 0x7CB8]),
    (31, 0x7D83, 0x7DB8, "Bank 31 $7d83-$7db8 proximity check",
     "src/bank31.asm", [0x7D83]),
    (31, 0x7E07, 0x7E43, "Bank 31 $7e07-$7e43 link-record reader",
     "src/bank31.asm", [0x7E07]),
    (31, 0x7E7E, 0x7EA5, "Bank 31 $7e7e-$7ea5 $c0c7-list insert",
     "src/bank31.asm", [0x7E7E]),
    (31, 0x7F01, 0x7F5E, "Bank 31 $7f01-$7f5e record-kill + "
     "link-remove", "src/bank31.asm", [0x7F01, 0x7F0A, 0x7F32, 0x7F39]),
    # ---- bank 8 (entry-1 table routines) ----
    (8, 0x5F7B, 0x609C, "Bank 8 $5f7b-$609c $5f6b-entry-1 routine",
     "src/bank8slice16.asm", [0x5F7B]),
    (8, 0x60E9, 0x610F, "Bank 8 $60e9-$610f $5f6b-entry-7 routine",
     "src/bank8slice16.asm", [0x60E9]),
    (8, 0x63F0, 0x6442, "Bank 8 $63f0-$6442 $5f6b-entry-6 routine",
     "src/bank8slice16.asm", [0x63F0]),
    # ---- decimal bank 10 ($0a): the $2b48-handler set ----
    # The $4000-$46e2 span holds 14 entry heads (64 $4000, 61 $40dd,
    # 65 $41c2, 21 $41ce, 22 $4203, 23 $422c, 24 $4252, 25 $427b,
    # 39 $42a0, 40 $4345, 41 $43f6, 42 $44c3, 43 $458a, 44 $463e).
    # $46e3-$47a2 is the byte table $4000 reads ($46e3 8-byte records
    # + the $46e7 [$c10a]-indexed pair window) -- db, see below.
    (10, 0x4000, 0x46E2, "Bank 10 $4000-$46e2 $2b48-handler region",
     "src/bank0aslice16.asm",
     [0x4000, 0x40DD, 0x41C2, 0x41CE, 0x4203, 0x422C, 0x4252, 0x427B,
      0x42A0, 0x4345, 0x43F6, 0x44C3, 0x458A, 0x463E]),
    (10, 0x47A3, 0x4809, "Bank 10 $47a3-$4809 $2b48-entry-0 handler",
     "src/bank0aslice16.asm", [0x47A3]),
    (10, 0x4ADD, 0x4AE2, "Bank 10 $4add-$4ae2 [$c109]-bit-3 setter",
     "src/bank0aslice16.asm", [0x4ADD]),
    (10, 0x4D58, 0x4D5D, "Bank 10 $4d58-$4d5d [$c109]-bit-3 setter",
     "src/bank0aslice16.asm", [0x4D58]),
    (10, 0x4DBE, 0x4E55, "Bank 10 $4dbe-$4e55 $2b48-entry-10 region",
     "src/bank0aslice16.asm", [0x4DBE, 0x4E36]),
    (10, 0x5192, 0x51A0, "Bank 10 $5192-$51a0 $2b48-entry-11 handler",
     "src/bank0aslice16.asm", [0x5192]),
    (10, 0x51E0, 0x5211, "Bank 10 $51e0-$5211 shared routine",
     "src/bank0aslice16.asm", [0x51E0]),
    (10, 0x522B, 0x524A, "Bank 10 $522b-$524a $2b48-entry-13 handler",
     "src/bank0aslice16.asm", [0x522B]),
    (10, 0x532B, 0x534A, "Bank 10 $532b-$534a $2b48-entry-14 handler",
     "src/bank0aslice16.asm", [0x532B]),
    (10, 0x5412, 0x5420, "Bank 10 $5412-$5420 $2b48-entry-16 handler",
     "src/bank0aslice16.asm", [0x5412]),
    (10, 0x568C, 0x56B0, "Bank 10 $568c-$56b0 $2b48-entry-17 handler",
     "src/bank0aslice16.asm", [0x568C]),
    (10, 0x56DB, 0x56FA, "Bank 10 $56db-$56fa $2b48-entry-31 handler",
     "src/bank0aslice16.asm", [0x56DB]),
    (10, 0x57BB, 0x5893, "Bank 10 $57bb-$5893 $2b48-entry-33 handler",
     "src/bank0aslice16.asm", [0x57BB]),
    (10, 0x5909, 0x5917, "Bank 10 $5909-$5917 $2b48-entry-36 handler",
     "src/bank0aslice16.asm", [0x5909]),
    (10, 0x5D08, 0x5D5D, "Bank 10 $5d08-$5d5d $5cf8-table entries 0-1",
     "src/bank0aslice16.asm", [0x5D08, 0x5D48]),
    (10, 0x5D86, 0x5E09, "Bank 10 $5d86-$5e09 $5cf8-table entries 2-3",
     "src/bank0aslice16.asm", [0x5D86, 0x5D9F]),
    (10, 0x5E88, 0x5EC9, "Bank 10 $5e88-$5ec9 $5cf8-table entries 6-7",
     "src/bank0aslice16.asm", [0x5E88, 0x5E97]),
    (10, 0x60F3, 0x612D, "Bank 10 $60f3-$612d shared routine",
     "src/bank0aslice16.asm", [0x60F3]),
    (10, 0x63A3, 0x6413, "Bank 10 $63a3-$6413 $2b48-entry-55 handler",
     "src/bank0aslice16.asm", [0x63A3]),
    (10, 0x6582, 0x65A1, "Bank 10 $6582-$65a1 $2b48-entry-58 handler",
     "src/bank0aslice16.asm", [0x6582]),
    (10, 0x678C, 0x67AB, "Bank 10 $678c-$67ab $2b48-entry-62 handler",
     "src/bank0aslice16.asm", [0x678C]),
    (10, 0x69BE, 0x69DD, "Bank 10 $69be-$69dd $2b48-entry-84 handler",
     "src/bank0aslice16.asm", [0x69BE]),
    (10, 0x6AF9, 0x6B07, "Bank 10 $6af9-$6b07 $2b48-entry-85 handler",
     "src/bank0aslice16.asm", [0x6AF9]),
    (10, 0x6D77, 0x6D99, "Bank 10 $6d77-$6d99 $2b48-entry-49 handler",
     "src/bank0aslice16.asm", [0x6D77]),
    (10, 0x6E42, 0x6E61, "Bank 10 $6e42-$6e61 $2b48-entry-86 handler",
     "src/bank0aslice16.asm", [0x6E42]),
    (10, 0x6F3D, 0x6F65, "Bank 10 $6f3d-$6f65 $2b48-entry-87 handler",
     "src/bank0aslice16.asm", [0x6F3D]),
    (10, 0x705F, 0x7072, "Bank 10 $705f-$7072 $2b48-entry-63 handler",
     "src/bank0aslice16.asm", [0x705F]),
    (10, 0x7951, 0x79E9, "Bank 10 $7951-$79e9 shared routine",
     "src/bank0aslice16.asm", [0x7951]),
    (10, 0x7AB8, 0x7B11, "Bank 10 $7ab8-$7b11 shared routine",
     "src/bank0aslice16.asm", [0x7AB8]),
    (10, 0x7B3F, 0x7B6B, "Bank 10 $7b3f-$7b6b shared routine",
     "src/bank0aslice16.asm", [0x7B3F]),
    (10, 0x7C24, 0x7C56, "Bank 10 $7c24-$7c56 $c0c7-list head",
     "src/bank0aslice16.asm", [0x7C24]),
    # ---- bank 16 ($10): the $5a11 timer-13 body / Mario machine ----
    # $5a11 calls $5f6c, then dispatches on [$c213] via the $5a18
    # table (7 entries -- the entries are the nested rst-$08 sites
    # $5a46/$5b3c/$5c02/$5d4e/$5e00/$5f13 + $5a26). $4993/$49c8/$4a18
    # are the shared [$c213]-record routines called from $5a48;
    # $49c4 is their 2-entry dw table ($4a18, $4a61). $4aef is a
    # lone $c9 ret between the $4a18 routine and slice 11's $4af0
    # carve. $4e89 is the position nudge (slice 15's 26-instr walk).
    (16, 0x4993, 0x49C3, "Bank 16 $4993-$49c3 [$c213]-record routine",
     "src/bank16slice16.asm", [0x4993]),
    (16, 0x49C8, 0x4A17, "Bank 16 $49c8-$4a17 [$c213]-record tail",
     "src/bank16slice16.asm", [0x49C8]),
    (16, 0x4A18, 0x4AEE, "Bank 16 $4a18-$4aee $49c4-table routines",
     "src/bank16slice16.asm", [0x4A18, 0x4A61]),
    (16, 0x4E89, 0x4EB1, "Bank 16 $4e89-$4eb1 position nudge",
     "src/bank16slice16.asm", [0x4E89]),
    (16, 0x5A11, 0x5A17, "Bank 16 $5a11-$5a17 timer-13 body head",
     "src/bank16slice16.asm", [0x5A11]),
    (16, 0x5A26, 0x5A4E, "Bank 16 $5a26-$5a4e $5a18-entry-0 routine",
     "src/bank16slice16.asm", [0x5A26, 0x5A46]),
    (16, 0x5A59, 0x5B3F, "Bank 16 $5a59-$5b3f $5a4f-table routines",
     "src/bank16slice16.asm", [0x5A59, 0x5ABF, 0x5AF3, 0x5B0B, 0x5B15]),
    (16, 0x5B46, 0x5C05, "Bank 16 $5b46-$5c05 $5b40-table routines",
     "src/bank16slice16.asm", [0x5B46, 0x5BCF, 0x5BF8]),
    (16, 0x5C16, 0x5D51, "Bank 16 $5c16-$5d51 $5c06-table routines",
     "src/bank16slice16.asm",
     [0x5C16, 0x5C4A, 0x5C71, 0x5C97, 0x5CC3, 0x5CE9, 0x5D29, 0x5D33]),
    (16, 0x5D58, 0x5E03, "Bank 16 $5d58-$5e03 $5d52-table routines",
     "src/bank16slice16.asm", [0x5D58, 0x5D98, 0x5DF6]),
    (16, 0x5E0E, 0x5F16, "Bank 16 $5e0e-$5f16 $5e04-table routines",
     "src/bank16slice16.asm", [0x5E0E, 0x5E6B, 0x5EE7, 0x5F00, 0x5F0E]),
    (16, 0x5F1F, 0x5FD2, "Bank 16 $5f1f-$5fd2 $5f17-table routines",
     "src/bank16slice16.asm", [0x5F1F, 0x5F31, 0x5F49, 0x5F62]),
]

# Meaningful entry labels: (bank, addr) -> name.
LABELS = {
    (31, 0x40E1): "Bank31_40E1",
    (31, 0x40F0): "Bank31_40F0",
    (31, 0x40F6): "Bank31_40F6",
    (31, 0x411E): "Bank31_411E",
    (31, 0x4142): "Bank31_4142",
    (31, 0x48E3): "Bank31_48E3",
    (31, 0x49B0): "Bank31_49B0",
    (31, 0x49BF): "Bank31_49BF",
    (31, 0x49C3): "Bank31_49C3",
    (31, 0x49FD): "Bank31_49FD",
    (31, 0x589C): "Bank31_589C",
    (31, 0x58AB): "Bank31_58AB",
    (31, 0x58AF): "Bank31_58AF",
    (31, 0x58DC): "Bank31_58DC",
    (31, 0x58E2): "Bank31_58E2",
    (31, 0x58FE): "Bank31_58FE",
    (31, 0x590E): "Bank31_590E",
    (31, 0x5934): "Bank31_5934",
    (31, 0x5968): "Bank31_5968",
    (31, 0x5990): "Bank31_5990",
    (31, 0x59B2): "Bank31_59B2",
    (31, 0x59D2): "Bank31_59D2",
    (31, 0x59EB): "Bank31_59EB",
    (31, 0x5A1D): "Bank31_5A1D",
    (31, 0x7CA1): "Bank31_7CA1",
    (31, 0x7CB8): "Bank31_7CB8",
    (31, 0x7D83): "Bank31_7D83",
    (31, 0x7E07): "Bank31_7E07",
    (31, 0x7E7E): "Bank31_7E7E",
    (31, 0x7F01): "Bank31_7F01",
    (31, 0x7F0A): "Bank31_7F0A",
    (31, 0x7F32): "Bank31_7F32",
    (31, 0x7F39): "Bank31_7F39",
    (8, 0x5F6B): "Bank8_5F6B",
    (8, 0x5F7B): "Bank8_5F7B",
    (8, 0x60E9): "Bank8_60E9",
    (8, 0x63F0): "Bank8_63F0",
    (10, 0x4000): "Bank0A_4000",
    (10, 0x40DD): "Bank0A_40DD",
    (10, 0x41C2): "Bank0A_41C2",
    (10, 0x41CE): "Bank0A_41CE",
    (10, 0x4203): "Bank0A_4203",
    (10, 0x422C): "Bank0A_422C",
    (10, 0x4252): "Bank0A_4252",
    (10, 0x427B): "Bank0A_427B",
    (10, 0x42A0): "Bank0A_42A0",
    (10, 0x4345): "Bank0A_4345",
    (10, 0x43F6): "Bank0A_43F6",
    (10, 0x44C3): "Bank0A_44C3",
    (10, 0x458A): "Bank0A_458A",
    (10, 0x463E): "Bank0A_463E",
    (10, 0x46E3): "Bank0A_46E3",
    (10, 0x47A3): "Bank0A_47A3",
    (10, 0x4ADD): "Bank0A_4ADD",
    (10, 0x4DBE): "Bank0A_4DBE",
    (10, 0x4D58): "Bank0A_4D58",
    (10, 0x4E36): "Bank0A_4E36",
    (10, 0x5192): "Bank0A_5192",
    (10, 0x51E0): "Bank0A_51E0",
    (10, 0x522B): "Bank0A_522B",
    (10, 0x532B): "Bank0A_532B",
    (10, 0x5412): "Bank0A_5412",
    (10, 0x568C): "Bank0A_568C",
    (10, 0x56DB): "Bank0A_56DB",
    (10, 0x57BB): "Bank0A_57BB",
    (10, 0x5909): "Bank0A_5909",
    (10, 0x5D08): "Bank0A_5D08",
    (10, 0x5D48): "Bank0A_5D48",
    (10, 0x5D86): "Bank0A_5D86",
    (10, 0x5D9F): "Bank0A_5D9F",
    (10, 0x5E88): "Bank0A_5E88",
    (10, 0x5E97): "Bank0A_5E97",
    (10, 0x60F3): "Bank0A_60F3",
    (10, 0x63A3): "Bank0A_63A3",
    (10, 0x6582): "Bank0A_6582",
    (10, 0x678C): "Bank0A_678C",
    (10, 0x69BE): "Bank0A_69BE",
    (10, 0x6AF9): "Bank0A_6AF9",
    (10, 0x6D77): "Bank0A_6D77",
    (10, 0x6E42): "Bank0A_6E42",
    (10, 0x6F3D): "Bank0A_6F3D",
    (10, 0x705F): "Bank0A_705F",
    (10, 0x7951): "Bank0A_7951",
    (10, 0x7AB8): "Bank0A_7AB8",
    (10, 0x7B3F): "Bank0A_7B3F",
    (10, 0x7C24): "Bank0A_7C24",
    (16, 0x4993): "Bank16_4993",
    (16, 0x49C4): "Bank16_49C4",
    (16, 0x49C8): "Bank16_49C8",
    (16, 0x4A18): "Bank16_4A18",
    (16, 0x4A61): "Bank16_4A61",
    (16, 0x4AEF): "Bank16_4AEF",
    (16, 0x4E89): "Bank16_4E89",
    (16, 0x5A11): "Bank16_5A11",
    (16, 0x5A18): "Bank16_5A18",
    (16, 0x5A26): "Bank16_5A26",
    (16, 0x5A46): "Bank16_5A46",
    (16, 0x5A4F): "Bank16_5A4F",
    (16, 0x5A59): "Bank16_5A59",
    (16, 0x5ABF): "Bank16_5ABF",
    (16, 0x5AF3): "Bank16_5AF3",
    (16, 0x5B0B): "Bank16_5B0B",
    (16, 0x5B15): "Bank16_5B15",
    (16, 0x5B40): "Bank16_5B40",
    (16, 0x5B46): "Bank16_5B46",
    (16, 0x5BCF): "Bank16_5BCF",
    (16, 0x5BF8): "Bank16_5BF8",
    (16, 0x5C06): "Bank16_5C06",
    (16, 0x5C16): "Bank16_5C16",
    (16, 0x5C4A): "Bank16_5C4A",
    (16, 0x5C71): "Bank16_5C71",
    (16, 0x5C97): "Bank16_5C97",
    (16, 0x5CC3): "Bank16_5CC3",
    (16, 0x5CE9): "Bank16_5CE9",
    (16, 0x5D29): "Bank16_5D29",
    (16, 0x5D33): "Bank16_5D33",
    (16, 0x5D52): "Bank16_5D52",
    (16, 0x5D58): "Bank16_5D58",
    (16, 0x5D98): "Bank16_5D98",
    (16, 0x5DF6): "Bank16_5DF6",
    (16, 0x5E04): "Bank16_5E04",
    (16, 0x5E0E): "Bank16_5E0E",
    (16, 0x5E6B): "Bank16_5E6B",
    (16, 0x5EE7): "Bank16_5EE7",
    (16, 0x5F00): "Bank16_5F00",
    (16, 0x5F0E): "Bank16_5F0E",
    (16, 0x5F17): "Bank16_5F17",
    (16, 0x5F1F): "Bank16_5F1F",
    (16, 0x5F31): "Bank16_5F31",
    (16, 0x5F49): "Bank16_5F49",
    (16, 0x5F62): "Bank16_5F62",
}


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


def emit_carve(rom, bank, lo, hi, title, instrs, rst08):
    section = "ROM0" if bank == 0 else "ROMX"
    bankarg = f", BANK[{bank}]" if bank != 0 else ""
    out = [f"; Slice 16: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/gen_slice16.py from the ROM bytes via",
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
    out = [f"; Slice 16: {title} -- bank {bank} ${lo:04x}-"
           f"${lo + 2 * len(entries) - 1:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/gen_slice16.py; values read straight "
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
    out = [f"; Slice 16: {title} -- bank {bank} ${lo:04x}-${hi:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/gen_slice16.py; bytes read straight "
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


def main():
    rom = open(ROM, "rb").read()
    seeds31 = [0x40E1, 0x48E3, 0x49B0, 0x589C, 0x58E2,
               0x40F6, 0x411E, 0x4142, 0x49C3, 0x49FD, 0x58AF, 0x58DC,
               0x590E, 0x5934, 0x5968, 0x5990, 0x59B2, 0x59D2, 0x59EB, 0x5A1D]
    seeds8 = [0x5F7B, 0x60E9, 0x63F0]
    seeds10 = [0x47A3, 0x4E36, 0x5192, 0x522B, 0x532B, 0x5412, 0x568C,
               0x41CE, 0x4203, 0x422C, 0x4252, 0x427B, 0x56DB, 0x57BB,
               0x5909, 0x42A0, 0x4345, 0x43F6, 0x44C3, 0x458A, 0x463E,
               0x6D77, 0x5E98, 0x63A3, 0x63F4, 0x6582, 0x40DD, 0x678C,
               0x705F, 0x4000, 0x41C2, 0x69BE, 0x6AF9, 0x6E42, 0x6F3D,
               0x4ADD, 0x4D58, 0x5D08, 0x5D48, 0x5D86, 0x5D9F, 0x5E88, 0x5E97]
    seeds16 = [0x4993, 0x49C8, 0x4A18, 0x4A61, 0x4E89, 0x5A11,
               0x5A26, 0x5A46, 0x5A59, 0x5ABF, 0x5AF3, 0x5B0B, 0x5B15,
               0x5B46, 0x5BCF, 0x5BF8, 0x5C16, 0x5C4A, 0x5C71, 0x5C97,
               0x5CC3, 0x5CE9, 0x5D29, 0x5D33, 0x5D58, 0x5D98, 0x5DF6,
               0x5E0E, 0x5E6B, 0x5EE7, 0x5F00, 0x5F0E,
               0x5F1F, 0x5F31, 0x5F49, 0x5F62]
    reached31, rst08_31, notes31 = walk(31, seeds31)
    reached8, rst08_8, notes8 = walk(8, seeds8)
    reached10, rst08_10, notes10 = walk(10, seeds10)
    reached16, rst08_16, notes16 = walk(16, seeds16)
    for n in notes31 + notes8 + notes10 + notes16:
        print("note:", n, file=sys.stderr)
    print(f"walk bank 31: {len(reached31)} instrs; "
          f"bank 8: {len(reached8)} instrs; "
          f"bank 10: {len(reached10)} instrs; "
          f"bank 16: {len(reached16)} instrs", file=sys.stderr)
    # Bank 16's walk has 7 rst-$08 sites (the $5a11 dispatch chain);
    # the other three walks must have none. The tables are emitted
    # as dw sections below, verified against the walk's entries.
    assert not rst08_31 and not rst08_8 and not rst08_10, \
        "unexpected rst $08 in walk"
    assert len(rst08_16) == 7, f"bank 16 rst $08 sites: {rst08_16}"
    by_file = {}
    for bank, lo, hi, title, outfile, _seeds in CARVES:
        reached = {31: reached31, 8: reached8, 10: reached10,
                   16: reached16}[bank]
        instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
        covered = set()
        for a, (ln, *_r) in instrs.items():
            covered.update(range(a, a + ln))
        assert covered == set(range(lo, hi + 1)), \
            f"bank {bank} ${lo:04x}-${hi:04x}: uncovered bytes " \
            f"{sorted(set(range(lo, hi + 1)) - covered)[:8]}"
        by_file.setdefault(outfile, []).append(
            (bank, lo, hi, title, instrs, {}))

    # ---- bank 31 dw tables ----
    b31_data = []
    b31_data.append(emit_dw_table(
        rom, 31, 0x40F0,
        [(0x40F0 + 2 * i, f"[$c10a]={i}") for i in range(3)],
        "Bank 31 $40f0-$40f5 [$c10a] table (entry-7 handler)",
        expected=[0x40F6, 0x411E, 0x4142]))
    b31_data.append(emit_dw_table(
        rom, 31, 0x49BF,
        [(0x49BF + 2 * i, f"[$c10a]={i}") for i in range(2)],
        "Bank 31 $49bf-$49c2 [$c10a] table (entry-45 handler)",
        expected=[0x49C3, 0x49FD]))
    b31_data.append(emit_dw_table(
        rom, 31, 0x58AB,
        [(0x58AB + 2 * i, f"[$c10a]={i}") for i in range(2)],
        "Bank 31 $58ab-$58ae [$c10a] table (entry-72 handler)",
        expected=[0x58AF, 0x58DC]))
    b31_data.append(emit_dw_table(
        rom, 31, 0x58FE,
        [(0x58FE + 2 * i, f"[$c10a]={i}") for i in range(8)],
        "Bank 31 $58fe-$590d [$c10a] table (entry-73 handler)",
        expected=[0x590E, 0x5934, 0x5968, 0x5990, 0x59B2, 0x59D2,
                  0x59EB, 0x5A1D]))
    by_file.setdefault("src/bank31.asm", []).extend(b31_data)

    # ---- bank 8 dw table ----
    b8_data = []
    b8_data.append(emit_dw_table(
        rom, 8, 0x5F6B,
        [(0x5F6B + 2 * i, f"[$c10a]={i}") for i in range(8)],
        "Bank 8 $5f6b-$5f7a [$c10a] table (entry-1 handler)",
        expected=[0x6473, 0x5F7B, 0x609D, 0x7310, 0x63B5, 0x6646,
                  0x63F0, 0x60E9],
        note="Entries 0/2/3/4/5 point at routines carved in slice 15 "
             "($6473, $609d, $7310, $63b5, $6646 inside $6473-$6667); "
             "entries 1/6/7 are carved here ($5f7b, $63f0, $60e9)."))
    by_file.setdefault("src/bank8slice16.asm", []).extend(b8_data)

    # ---- bank 10 data carve: the $46e3-$47a2 byte table ----
    # $4000 reads it two ways: $46e3 as 8-byte records (the $4064
    # loop steps 8 and compares [$c10b]-derived bytes), and $46e7
    # as a [$c10a]-indexed 1-byte-stride pair window (the $400d
    # block reads [HL-] then [HL]). The two views overlap in the
    # same 192 bytes, so emit one db blob with no field claims.
    b10_data = []
    b10_data.append(emit_db(rom, 10, 0x46E3, 0x47A2,
                            "Bank 10 $46e3-$47a2 $4000 byte table",
                            "$4000 reads $46e3 as 8-byte records and "
                            "$46e7 as a [$c10a]-indexed pair window; "
                            "one blob, no field claims."))
    by_file.setdefault("src/bank0aslice16.asm", []).extend(b10_data)

    # ---- bank 16 data carves: the rst-$08 tables + lone ret ----
    b16_data = []
    b16_data.append(emit_dw_table(
        rom, 16, 0x49C4,
        [(0x49C4, "[$c213] record byte 0"), (0x49C6, "[$c213] record byte 1")],
        "Bank 16 $49c4-$49c7 [$c213] dw table ($4993)",
        expected=[0x4A18, 0x4A61]))
    rst_tables = [
        (0x5A18, rst08_16[0x5A17], "rst $08 at $5a17 ([$c213] dispatch)"),
        (0x5A4F, rst08_16[0x5A4E], "rst $08 at $5a4e"),
        (0x5B40, rst08_16[0x5B3F], "rst $08 at $5b3f"),
        (0x5C06, rst08_16[0x5C05], "rst $08 at $5c05"),
        (0x5D52, rst08_16[0x5D51], "rst $08 at $5d51"),
        (0x5E04, rst08_16[0x5E03], "rst $08 at $5e03"),
        (0x5F17, rst08_16[0x5F16], "rst $08 at $5f16"),
    ]
    for base, entries, note in rst_tables:
        b16_data.append(emit_dw_table(
            rom, 16, base,
            [(base + 2 * i, f"entry {i}") for i in range(len(entries))],
            f"Bank 16 ${base:04x}-${base + 2 * len(entries) - 1:04x} "
            f"rst-$08 table",
            expected=entries, note=note))
    assert rom[file_off(16, 0x4AEF)] == 0xC9, "bank 16 $4aef is not $c9"
    b16_data.append(
        "; Slice 16: Bank 16 $4aef 1-byte ret -- between the $4a18\n"
        "; routine (ends $4aee ret) and slice 11's $4af0 carve.\n"
        "; Verified byte $c9; no control flow reaches it.\n"
        'SECTION "Bank 16 $4aef lone ret", ROMX[$4aef], BANK[16]\n'
        "Bank16_4AEF::\n"
        "    ret                                              ; $4aef\n")
    by_file.setdefault("src/bank16slice16.asm", []).extend(b16_data)

    for outfile, parts in by_file.items():
        rendered = []
        for part in parts:
            if isinstance(part, str):
                rendered.append(part)
            else:
                bank, lo, hi, title, instrs, rst08 = part
                rendered.append(emit_carve(rom, bank, lo, hi, title,
                                           instrs, rst08))
        with open(outfile, "w") as f:
            f.write("\n".join(rendered))
        print(f"wrote {outfile} ({sum(len(p) for p in rendered)} bytes)")


if __name__ == "__main__":
    main()
