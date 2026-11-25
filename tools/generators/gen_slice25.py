#!/usr/bin/env python3
"""Slice-25 generator: banks 5 + 18 (stage data), 24 (stream data),
23 (attract-demo table + data), 12 (credits tail data), and bank 1
code $5a00-$5a80.

Surveys: tools/surveys/survey25_bank5.py (banks 5/18/24/23/12/1 extents),
tools/surveys/survey25_bank14records.py (bank-14 record targets),
tools/surveys/survey25_bank23.py (bank-23 $4000 table + blocks),
tools/surveys/survey25_bank1.py (bank-1 code walk).

Bank 5 ($05) run-0 stage data $40d4-$7c56 (15,235 bytes):
  * $40d4-$41ff: 300 bytes of repeating `b2 61` (150 pairs) between
    the stage table ($4000-$40d3, slice 4) and stage 0 ($4200).
    No structure claimed; emitted as plain db.
  * Stages 0-44 from the bank-5 pointer table (slice 4): starts
    tile contiguously $4200-$7c56 (sizes 127-640 bytes); stage 44
    ($7b64) runs 243 bytes to the last non-$ff byte at $7c56
    ($00); $7c57-$7fff is all $ff padding (stays INCBIN).
  * The ONLY `ld a,$05; rst $10` site in the whole ROM is bank-0
    $24e7 (LoadStage) -- bank 5 is reached only via LoadStage
    ($24e7) -> SwitchBankByE ($2611), as decompressor input; no
    bank-5 byte can ever execute. gb_rd from $4000 derails in 119
    instructions; dw values pointing in-bank are 1,797/16,383
    (~11%, below the ~25% random rate), so no embedded pointer
    table. Header value sets across the 45 stages: byte0 {0..4},
    byte1 {5..27}, byte2 {0,3,5,10,12,13,14,16,19,21,22,28,30,32},
    byte3 {100,150,200,250} ($64,$96,$c8,$fa), byte4 all $00.
    The 5-byte header's WRAM destinations are VERIFIED from
    LoadStage $2516-$2527 ([$c705],[$da45],[$da4b],[$c711],[$c712]);
    header roles are unverified, bodies are compressed level data
    (plain db, no per-stream boundaries claimed).

Bank 18 ($12) run-2 stage data $4000-$6206 (stages 80-105):
  * Stages 80-105 from the bank-5 table tile $4000-$6206 (sizes
    85-622 bytes); stage 105 ($61b2) runs 85 bytes to the last
    non-$ff byte at $6206 ($00); $6207-$7fff is all $ff (INCBIN).
  * The $4934-$4c84 span is ALREADY carved as 106 8-byte records
    in src/banks/bank18.asm (slice 7's decimal/hex slip -- those bytes
    are stage 87's body + stage 88's header byte 0, not a stage
    table). The stage carve therefore skips $4934-$4c84: section
    1 covers $4000-$4933 (stages 80-86 + stage 87's head), section
    2 covers $4c84-$6206 (stage 88 from its 2nd byte + stages
    89-105). Bytes are identical either way (both db).
  * The ONLY `ld a,$12; rst $10` site is bank-0 $261c
    (inside SwitchBankByE, E >= $50 -> bank $12).
    Bank 18 is reached only via LoadStage -> SwitchBankByE, as
    decompressor input; no bank-18 byte can execute. gb_rd from
    $4000 derails in 17 instructions. Header value sets: byte0
    {0..4}, byte1 {5..28}, byte2 {3,4,6,8,9,15,20,24,26,33},
    byte3 {100,150,200,250}, byte4 all $00.

Bank 24 ($18) stream data $4000-$4933 + $4c84-$6f41:
  * $4000-$4933: 23 bank-14 $7e00 records point here (indices
    117-139), ptrs $4000-$4832 in 96-byte steps (last $4832, 14
    short of the stride); read by bank-0 $2470 (H >= $7e branch)
    as Decompress $257f / MemcpyC $106e input. The bank is mapped
    only by bank-0 $26f6/$2773/$289e, all followed by ROM0 calls
    or data reads -- no call/jp into bank 24 exists. gb_rd from
    $4000 walks 1,684 instructions through data bytes (spurious;
    opcode density in $4000-$4fff is ret 0 / call 0).
  * $4c84-$6f41: plain db, NO reader pinned (honest gap -- the
    $2470 records stop at $4832 and the $4934 stage table is the
    only other structure; what reads $4c84-$6f41 is unknown).
    gb_rd walks from $4c84/$5000/$6000/$6f00 derail in 10-16
    instructions. $6f42-$7fff is all $ff (stays INCBIN).
  * No per-stream boundaries are claimed for either span.

Bank 23 ($17) attract-demo data $4000-$731e + $7e12-$7e31:
  * $4000-$4035: 27-entry dw table read by bank-23 $7387
    ($4000 + [$ca66]*2; [$ca66] is the queue B byte, written by
    C-dispatch entry 20 $0d6f). Entries 0-26 strictly increasing
    ($4036-$41d6); entry 27 would read $0004 (the first block's
    bytes $04 $00) -- the partition break. C==20 queue B values
    (enumerated from the bank-12 queue table $4f97, 331 pairs)
    are {0..24, 26} (max 26), so every queue index lands inside
    the 27-entry table; B=25 has no queue entry.
  * $4036-$41e5: 27 blocks [count][count x 3-byte items: slot,
    b0, b1], 135 items total; every block's slot bytes run
    0..count-1 sequentially; blocks tile with zero gaps (each
    block is 1+3*count bytes, ending exactly at the next target).
    The reader ($7395-$73ae) stores each item's 2 data bytes to
    $c20c + slot*32.
  * $41e6-$731e: plain db, no reader pinned (honest gap).
    gb_rd walks from $4000/$5000/$6000/$7000 derail in 7-193
    instructions; no carved bank-23 code targets this span
    (own-file control-flow check: NONE).
  * $7e12-$7e31: $7e12/$7e18 are 6-byte blocks copied by MemcpyC
    $106e to $d76d/$d77d ($7586/$7591); $7e1e/$7e28 are 10-byte
    tables (even/odd counting sequences $30..$42 / $31..$43)
    indexed by a byte ($75f1 / $749e, A = [$c80b]). Index ranges
    are unverified. $7e32-$7fff is all $ff (stays INCBIN).
  * Bank 23 is mapped by state 30 ($290a, dispatches into the
    carved $731f+ code), by $293a (map-then-return, called from
    bank-23 $7325), and by LoadStagePtrWrapper $1c8a (called from
    bank-23 $76dc). None of those paths jumps into $4000-$731e.

Bank 12 ($0c) $5dbc-$7001 (4,582 bytes): plain db. Opens with
credits-pattern text (spaces + "defgh" / "jklmnof" at $5dbc,
continuing the $5917-$5dbb credits carve), then binary data to
the last non-$ff byte at $7001 ($04); $7002-$7fff is all $ff
(stays INCBIN). No reader pinned (honest gap); no carved bank-12
code targets this span (own-file check: NONE); gb_rd walks from
$5dbc/$6000/$6c00 derail in 4-254 instructions.

Bank 1 ($01) code $5a00-$5a80 (129 bytes): the carved bank-1 code
ends at $59ff; its last routine ($59c4 loop) falls through at
$59fd into $5a00, and calls $5a45/$5a76 from $59d6/$59dd -- the
only two control-flow targets into $5a00-$79ff in src/banks/bank1.asm.
gb_rd walk from $5a00/$5a45/$5a76 covers $5a00-$5a80 with zero
gaps (116 instructions, no rst $08): $5a00-$5a20 loop body (jr
$59c4 back into the carved routine), $5a3b helper (called 3x
from $5a32/$5a35/$5a38), $5a45 (called from $59d6), $5a76 (called
from $59dd/$5a11) + $5a7c (called from $5a0e/$5a76/$5a79). The
$5a07/$5a26/$5a70 `call $201d` sites are bank-0 routines. $5a81+
is NOT carved here: no walk reaches it and the only ld-pointers
past it ($5d48+ tables, $7308 count) are data reads.

Door / clear chain: none of this slice's carves contains code
that writes hStateTimer ($ff90) or [$c105] (banks 5/18/24/23/12
are data; the bank-1 $5a00-$5a80 code touches only $c809-$c80c
and WRAM $c81c/$c81d via the $201d helper path). No new door
lead, no completion attempt (same NO-GO as slices 15-24).

Regenerate with: python3 tools/generators/gen_slice25.py [db|bank1|all]
  db    -- the five data banks (default)
  bank1 -- the bank-1 code carve only
  all   -- both
Outputs: src/banks/bank5slice25.asm, src/banks/bank18slice25.asm,
src/banks/bank24slice25.asm, src/banks/bank23slice25.asm,
src/banks/bank12slice25.asm, src/banks/bank1slice25.asm (new files).
Also update tools/generators/gen_banks.py CARVED (banks 1, 5, 12, 18, 23, 24)
and regenerate src/banks.asm; add INCLUDEs to src/main.asm.
The outputs are CHECKED IN; rerun after changing the config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

STAGE5 = [0x4200, 0x42c8, 0x43a1, 0x4453, 0x44d2, 0x45c1, 0x4726, 0x4809,
          0x491b, 0x49f0, 0x4abd, 0x4bb9, 0x4c76, 0x4e1d, 0x4f61, 0x5076,
          0x515d, 0x52bc, 0x5447, 0x5630, 0x5753, 0x583d, 0x59be, 0x5b46,
          0x5c14, 0x5da4, 0x5f3b, 0x60a1, 0x624b, 0x63c7, 0x64ad, 0x6613,
          0x6773, 0x6919, 0x6a4a, 0x6bda, 0x6d29, 0x6eab, 0x70a6, 0x72b0,
          0x73ab, 0x75ad, 0x782d, 0x7a56, 0x7b64]
STAGE18 = [0x4000, 0x4188, 0x43a1, 0x4575, 0x4694, 0x4862, 0x49b7, 0x4b18,
           0x4c83, 0x4e21, 0x508f, 0x5294, 0x53b6, 0x5506, 0x566f, 0x585a,
           0x598a, 0x5aca, 0x5c5a, 0x5d84, 0x5e32, 0x5ed6, 0x5f7d, 0x602c,
           0x60df, 0x61b2]
HDR_DST = ["$c705", "$da45", "$da4b", "$c711", "$c712"]


def emit_db_lines(out, rom, bank, lo, hi):
    """Plain db lines, 16 bytes each, for [lo, hi). Returns byte count."""
    n = 0
    a = lo
    while a < hi:
        chunk = min(16, hi - a)
        vals = [rom[file_off(bank, a + k)] for k in range(chunk)]
        out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
        n += chunk
        a += chunk
    return n


def emit_stages(rom, bank, stages, first_no, lo, hi, skip, title):
    """Stage carve over [lo, hi) skipping `skip` [(lo,hi)] ranges.
    One label per stage; stages starting inside a skipped range get
    their label at the resume point with a note. Returns (lines, bytes)."""
    out = [f"; Slice 25: {title}.",
           "; Stages from the bank-5 pointer table (slice 4); reached",
           "; only via LoadStage ($24e7) -> SwitchBankByE ($2611), as",
           "; decompressor input. Each stage starts with a 5-byte",
           "; header (verified from LoadStage $2516-$2527): bytes ->",
           "; [$c705], [$da45], [$da4b], [$c711], [$c712]. Header roles",
           "; are unverified; bodies are compressed level data,",
           "; emitted as plain db. Generated by tools/generators/gen_slice25.py",
           "; from the ROM bytes. Byte-match (`make`) arbitrates.",
           ""]
    # Build the emitted windows: [lo, hi) minus skip ranges.
    wins = []
    cur = lo
    for slo, shi in sorted(skip):
        if slo > cur:
            wins.append((cur, slo))
        cur = max(cur, shi)
    if cur < hi:
        wins.append((cur, hi))

    def in_wins(a):
        return any(wlo <= a < whi for wlo, whi in wins)

    emitted = 0
    for i, s in enumerate(stages):
        n = first_no + i
        end = stages[i + 1] if i + 1 < len(stages) else hi
        hdr = [rom[file_off(bank, s + k)] for k in range(5)] \
            if in_wins(s) else None
        a = s
        started = False
        while a < end:
            if not in_wins(a):
                if not started and a == s:
                    # The stage starts inside a skipped (already
                    # carved) span; note where its head bytes live.
                    resume = min([wlo for wlo, _whi in wins if wlo > a]
                                 + [end])
                    out.append(f"; Stage {n} ${s:04x}-${end - 1:04x}: "
                               f"bytes ${s:04x}-${resume - 1:04x} live in "
                               f"an earlier carve (see the file header).")
                a = min([wlo for wlo, _whi in wins if wlo > a] + [end])
                continue
            wlo, whi = next(w for w in wins if w[0] <= a < w[1])
            seg_end = min(end, whi)
            if a == s and not started:
                if a == wlo:
                    out.append(f'SECTION "Bank {bank} stage {n} '
                               f"${s:04x}-${end - 1:04x}\", "
                               f"ROMX[${s:04x}], BANK[{bank}]")
                out.append(f"Bank{bank}_Stage{n}::  ; stage {n} "
                           f"${s:04x}-${end - 1:04x} ({end - s} bytes)")
                dst = ", ".join(f"{HDR_DST[k]}=${hdr[k]:02x}"
                                for k in range(5))
                out.append("    db " + ", ".join(f"${x:02x}" for x in hdr)
                           + f"  ; header: {dst}")
                emitted += 5
                a = s + 5
                started = True
                continue
            if a == wlo:
                out.append(f'SECTION "Bank {bank} stage {n} '
                           f"(continued) ${a:04x}-${end - 1:04x}\", "
                           f"ROMX[${a:04x}], BANK[{bank}]")
                out.append(f"Bank{bank}_Stage{n}Cont::  ; stage {n} "
                           f"continued ${a:04x}-${end - 1:04x} "
                           f"(header byte 0 at ${s:04x} lives in the "
                           f"earlier carve)")
                started = True
            chunk = min(16, seg_end - a)
            vals = [rom[file_off(bank, a + k)] for k in range(chunk)]
            out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
            emitted += chunk
            a += chunk
        out.append("")
    return out, emitted


def emit_bank5(rom):
    bank = 5
    lo, hi = 0x40D4, 0x7C57  # HI exclusive; last non-$ff byte $7c56.
    # $40d4-$41ff: 300 bytes of repeating b2 61.
    for i in range(0x40D4, 0x4200):
        assert rom[file_off(bank, i)] == (0xB2 if (i - 0x40D4) % 2 == 0
                                          else 0x61), f"gap byte ${i:04x}"
    assert set(rom[file_off(bank, a)] for a in range(hi, 0x8000)) == {0xFF}
    out = ["; Slice 25: bank 5 ($05) run-0 stage data $40d4-$7c56.",
           "; $40d4-$41ff: 300 bytes of repeating `b2 61` between the",
           "; stage table ($4000-$40d3, slice 4) and stage 0 ($4200).",
           "; No structure claimed. Stages 0-44 tile $4200-$7c56;",
           "; stage 44 ($7b64) ends at the last non-$ff byte $7c56;",
           "; $7c57-$7fff is all $ff padding (stays INCBIN). The only",
           "; `ld a,$05; rst $10` site in the ROM is bank-0 $24e7",
           "; (LoadStage): bank 5 is decompressor input only, no",
           "; bank-5 byte can ever execute. Generated by",
           "; tools/generators/gen_slice25.py from the ROM bytes.",
           "; Byte-match (`make`) arbitrates.",
           "",
           'SECTION "Bank 5 gap $40d4-$41ff", ROMX[$40D4], BANK[5]']
    emitted = emit_db_lines(out, rom, bank, 0x40D4, 0x4200)
    out.append("")
    lines, n = emit_stages(rom, bank, STAGE5, 0, 0x4200, hi, [],
                           "Bank 5 stage data $4200-$7c56")
    # emit_stages re-emits its own header comment; drop the duplicate
    # title block (first 10 lines: 9 comment lines + 1 blank line)
    # and keep the sections.
    out.extend(lines[10:])
    emitted += n
    assert emitted == hi - lo, f"emitted {emitted} != {hi - lo}"
    with open("src/banks/bank5slice25.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank5slice25.asm: {len(out)} lines, {emitted} bytes "
          f"${lo:04x}-${hi - 1:04x}, {len(STAGE5)} stages")


def emit_bank18(rom):
    bank = 18
    lo, hi = 0x4000, 0x6207  # HI exclusive; last non-$ff byte $6206.
    assert set(rom[file_off(bank, a)] for a in range(hi, 0x8000)) == {0xFF}
    # The $4934-$4c84 span is already carved in src/banks/bank18.asm.
    out = ["; Slice 25: bank 18 ($12) run-2 stage data $4000-$6206.",
           "; Stages 80-105 tile $4000-$6206; stage 105 ($61b2) ends",
           "; at the last non-$ff byte $6206; $6207-$7fff is all $ff",
           "; padding (stays INCBIN). The $4934-$4c84 span is already",
           "; carved as 106 8-byte records in src/banks/bank18.asm (slice",
           "; 7's decimal/hex slip -- those bytes are stage 87's body",
           "; + stage 88's header byte 0, not a stage table), so this",
           "; carve skips $4934-$4c84 and resumes at $4c84. The only",
           "; `ld a,$12; rst $10` site in the ROM is bank-0 $2615",
           "; (SwitchBankByE, E >= $50 -> bank $12): bank 18 is",
           "; decompressor input only, no bank-18 byte can execute.",
           "; Generated by tools/generators/gen_slice25.py from the ROM bytes.",
           "; Byte-match (`make`) arbitrates.",
           ""]
    lines, n = emit_stages(rom, bank, STAGE18, 80, lo, hi,
                           [(0x4934, 0x4C84)],
                           "Bank 18 stage data $4000-$6206")
    out.extend(lines[10:])
    # Bytes actually emitted here exclude the skipped span.
    assert n == (hi - lo) - (0x4C84 - 0x4934), \
        f"emitted {n} != {(hi - lo) - (0x4C84 - 0x4934)}"
    with open("src/banks/bank18slice25.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank18slice25.asm: {len(out)} lines, {n} bytes "
          f"${lo:04x}-${hi - 1:04x} minus $4934-$4c83, "
          f"{len(STAGE18)} stages")


def emit_bank24(rom):
    bank = 24
    # $4000-$4933: 23 bank-14 records (indices 117-139), ptrs $4000-$4832.
    recs = []
    for i in range(117, 140):
        a = 14 * 0x4000 + 0x3E00 + 3 * i
        recs.append((rom[a], rom[a + 1] | (rom[a + 2] << 8)))
    assert all(bk == 0x18 for bk, _p in recs)
    ptrs = [p for _bk, p in recs]
    assert ptrs[0] == 0x4000 and ptrs[-1] == 0x4832
    assert set(rom[file_off(bank, a)] for a in range(0x6F42, 0x8000)) == {0xFF}
    out = ["; Slice 25: bank 24 ($18) stream data $4000-$4933 + $4c84-$6f41.",
           "; $4000-$4933: 23 bank-14 $7e00 records (indices 117-139)",
           "; point here, ptrs $4000-$4832 in 96-byte steps (last",
           "; $4832); read by bank-0 $2470 as Decompress $257f /",
           "; MemcpyC $106e input. The bank is mapped only by bank-0",
           "; $26f6/$2773/$289e, all followed by ROM0 calls or data",
           "; reads -- no call/jp into bank 24 exists. $4c84-$6f41:",
           "; plain db, NO reader pinned (honest gap -- the $2470",
           "; records stop at $4832; what reads $4c84-$6f41 is",
           "; unknown). gb_rd walks from $4c84/$5000/$6000/$6f00",
           "; derail in 10-16 instructions. No per-stream boundaries",
           "; are claimed. $6f42-$7fff is all $ff (stays INCBIN).",
           "; Generated by tools/generators/gen_slice25.py from the ROM bytes.",
           "; Byte-match (`make`) arbitrates.",
           "",
           'SECTION "Bank 24 stream data $4000-$4933", '
           "ROMX[$4000], BANK[24]"]
    emitted = emit_db_lines(out, rom, bank, 0x4000, 0x4934)
    out.append("")
    out.append('SECTION "Bank 24 stream data $4c84-$6f41", '
               "ROMX[$4C84], BANK[24]")
    emitted += emit_db_lines(out, rom, bank, 0x4C84, 0x6F42)
    assert emitted == (0x4934 - 0x4000) + (0x6F42 - 0x4C84)
    with open("src/banks/bank24slice25.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank24slice25.asm: {len(out)} lines, {emitted} bytes, "
          f"{len(recs)} bank-14 records")


def emit_bank23(rom):
    bank = 23

    def byte(a):
        return rom[file_off(bank, a)]

    def rdw(a):
        return byte(a) | (byte(a + 1) << 8)

    entries = [rdw(0x4000 + 2 * i) for i in range(27)]
    assert all(entries[i + 1] > entries[i] for i in range(26))
    assert rdw(0x4036) == 0x0004  # entry 27 partition break
    blocks = []
    for i, t in enumerate(entries):
        cnt = byte(t)
        assert 1 <= cnt <= 32
        items = [(byte(t + 1 + 3 * k), byte(t + 2 + 3 * k),
                  byte(t + 3 + 3 * k)) for k in range(cnt)]
        assert [it[0] for it in items] == list(range(cnt))
        nxt = entries[i + 1] if i + 1 < 27 else t + 1 + 3 * cnt
        assert t + 1 + 3 * cnt == nxt, f"block {i} does not tile"
        blocks.append((t, cnt, items))
    assert blocks[-1][0] + 1 + 3 * blocks[-1][1] == 0x41E6
    assert set(byte(a) for a in range(0x7E32, 0x8000)) == {0xFF}
    out = ["; Slice 25: bank 23 ($17) attract-demo data $4000-$731e",
           "; + $7e12-$7e31.",
           "; $4000-$4035: 27-entry dw table read by bank-23 $7387",
           "; ($4000 + [$ca66]*2; [$ca66] is the queue B byte, written",
           "; by C-dispatch entry 20 $0d6f). Entry 27 would read $0004",
           "; (the first block's bytes) -- the partition break. C==20",
           "; queue B values are {0..24, 26} (max 26), so every queue",
           "; index lands inside the table; B=25 has no queue entry.",
           "; $4036-$41e5: 27 blocks [count][count x 3-byte items:",
           "; slot, b0, b1], 135 items; slot bytes run 0..count-1 in",
           "; every block; blocks tile with zero gaps. The reader",
           "; ($7395-$73ae) stores each item's 2 data bytes to",
           "; $c20c + slot*32. $41e6-$731e: plain db, no reader pinned",
           "; (honest gap). $7e12/$7e18: 6-byte blocks copied by",
           "; MemcpyC $106e to $d76d/$d77d ($7586/$7591); $7e1e/$7e28:",
           "; 10-byte tables indexed by a byte ($75f1 / $749e).",
           "; Generated by tools/generators/gen_slice25.py from the ROM bytes.",
           "; Byte-match (`make`) arbitrates.",
           "",
           'SECTION "Bank 23 attract table $4000-$4035", '
           "ROMX[$4000], BANK[23]",
           "Bank23_AttractTable::"]
    emitted = 0
    for i, p in enumerate(entries):
        out.append(f"    dw Bank23_AttractBlock_{p:04X}"
                   f"  ; entry {i} -> block ${p:04x}")
        emitted += 2
    out.append("")
    out.append('SECTION "Bank 23 attract blocks $4036-$41e5", '
               "ROMX[$4036], BANK[23]")
    for i, (t, cnt, items) in enumerate(blocks):
        out.append(f"Bank23_AttractBlock_{t:04X}::  ; block {i} "
                   f"${t:04x}, {cnt} item(s)")
        out.append(f"    db ${cnt:02x}")
        emitted += 1
        for (slot, b0, b1) in items:
            out.append(f"    db ${slot:02x}, ${b0:02x}, ${b1:02x}"
                       f"  ; slot {slot}")
            emitted += 3
    out.append("")
    out.append('SECTION "Bank 23 data $41e6-$731e", '
               "ROMX[$41E6], BANK[23]")
    emitted += emit_db_lines(out, rom, bank, 0x41E6, 0x731F)
    out.append("")
    out.append('SECTION "Bank 23 tables $7e12-$7e31", '
               "ROMX[$7E12], BANK[23]")
    out.append("Bank23_Table7E12::  ; 6 bytes, copied to $d76d ($7586)")
    out.append("    db " + ", ".join(f"${byte(a):02x}"
                                     for a in range(0x7E12, 0x7E18)))
    emitted += 6
    out.append("Bank23_Table7E18::  ; 6 bytes, copied to $d77d ($7591)")
    out.append("    db " + ", ".join(f"${byte(a):02x}"
                                     for a in range(0x7E18, 0x7E1E)))
    emitted += 6
    out.append("Bank23_Table7E1E::  ; 10 bytes, indexed by a byte ($75f1)")
    out.append("    db " + ", ".join(f"${byte(a):02x}"
                                     for a in range(0x7E1E, 0x7E28)))
    emitted += 10
    out.append("Bank23_Table7E28::  ; 10 bytes, indexed by [$c80b] ($749e)")
    out.append("    db " + ", ".join(f"${byte(a):02x}"
                                     for a in range(0x7E28, 0x7E32)))
    emitted += 10
    assert emitted == (0x4036 - 0x4000) + (0x41E6 - 0x4036) \
        + (0x731F - 0x41E6) + (0x7E32 - 0x7E12), \
        f"emitted {emitted}"
    with open("src/banks/bank23slice25.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank23slice25.asm: {len(out)} lines, {emitted} bytes, "
          f"27 blocks, {sum(c for _t, c, _i in blocks)} items")


def emit_bank12(rom):
    bank = 12
    assert set(rom[file_off(bank, a)] for a in range(0x7002, 0x8000)) == {0xFF}
    out = ["; Slice 25: bank 12 ($0c) data $5dbc-$7001.",
           "; Opens with credits-pattern text (spaces + \"defgh\" /",
           "; \"jklmnof\" at $5dbc, continuing the $5917-$5dbb credits",
           "; carve), then binary data to the last non-$ff byte at",
           "; $7001 ($04); $7002-$7fff is all $ff (stays INCBIN). No",
           "; reader pinned (honest gap); no carved bank-12 code",
           "; targets this span; gb_rd walks derail in 4-254 instrs.",
           "; Generated by tools/generators/gen_slice25.py from the ROM bytes.",
           "; Byte-match (`make`) arbitrates.",
           "",
           'SECTION "Bank 12 data $5dbc-$7001", ROMX[$5DBC], BANK[12]']
    emitted = emit_db_lines(out, rom, bank, 0x5DBC, 0x7002)
    assert emitted == 0x7002 - 0x5DBC
    with open("src/banks/bank12slice25.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank12slice25.asm: {len(out)} lines, {emitted} bytes "
          f"$5dbc-$7001")


# --- bank-1 code carve ($5a00-$5a80) -------------------------------------

BANK1_LABELS = {(1, 0x5A00): "Bank1_5A00", (1, 0x5A3B): "Bank1_5A3B",
                (1, 0x5A45): "Bank1_5A45", (1, 0x5A76): "Bank1_5A76",
                (1, 0x5A7C): "Bank1_5A7C"}
# jr targets outside the carve that already have a label in bank1.asm.
BANK1_EXT = {(1, 0x59C4): "jr_001_59c4"}


def emit_bank1(rom):
    bank = 1
    lo, hi = 0x5A00, 0x5A80  # HI inclusive.
    reached, _rst08, _notes = walk(bank, [0x5A00, 0x5A45, 0x5A76])
    instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
    # Full coverage, no gaps, no rst $08 in the carve.
    covered = set()
    for a, (ln, _t, _k, _tg) in instrs.items():
        covered.update(range(a, a + ln))
    assert covered == set(range(lo, hi + 1)), \
        f"bank-1 carve has gaps: {sorted(set(range(lo, hi + 1)) - covered)}"
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                and lo <= tgt <= hi and tgt not in instrs:
            raise SystemExit(f"bank 1 ${addr:04x} {text} targets "
                             f"${tgt:04x}, not a decoded instruction")
    jr_targets = {tgt for _a, (_ln, _t, kind, tgt) in instrs.items()
                  if kind == "jr" and isinstance(tgt, int)
                  and lo <= tgt <= hi}
    out = ["; Slice 25: bank 1 ($01) code $5a00-$5a80.",
           "; The carved bank-1 code ends at $59ff; its last routine",
           "; ($59c4 loop) falls through at $59fd into $5a00, and calls",
           "; $5a45/$5a76 from $59d6/$59dd -- the only two control-flow",
           "; targets into $5a00-$79ff in src/banks/bank1.asm. $5a00-$5a20",
           "; is the loop body (jr $59c4 back into the carved routine);",
           "; $5a3b is called 3x from $5a32/$5a35/$5a38; $5a45 is called",
           "; from $59d6; $5a76 (called from $59dd/$5a11) + $5a7c",
           "; (called from $5a0e/$5a76/$5a79) are the byte-copy pair.",
           "; `call $201d` sites are bank-0 routines. Generated by",
           "; tools/generators/gen_slice25.py from the ROM bytes via tools/gb_rd.py",
           "; (recursive descent, not mgbdis' linear sweep).",
           "; Byte-match (`make`) arbitrates.",
           "",
           'SECTION "Bank 1 code $5a00-$5a80", ROMX[$5A00], BANK[1]']
    addr = lo
    while addr <= hi:
        ln, text, kind, tgt = instrs[addr]
        label = None
        if (bank, addr) in BANK1_LABELS:
            label = f"{BANK1_LABELS[(bank, addr)]}::"
        elif addr in jr_targets:
            label = f"jr_{bank:03x}_{addr:04x}:"
        if kind == "jr" and isinstance(tgt, int):
            if lo <= tgt <= hi:
                tgt_label = BANK1_LABELS.get((bank, tgt),
                                             f"jr_{bank:03x}_{tgt:04x}")
            else:
                tgt_label = BANK1_EXT[(bank, tgt)]
            text = re.sub(r"\$[0-9a-f]{4}$", tgt_label, text)
        line = f"    {text:<48} ; ${addr:04x}"
        out.append((label + "\n" + line) if label else line)
        addr += ln
    with open("src/banks/bank1slice25.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank1slice25.asm: {len(out)} lines, "
          f"{len(instrs)} instructions ${lo:04x}-${hi:04x}")


def main():
    rom = open(ROM, "rb").read()
    # Stage starts tile contiguously; last stages end at last non-$ff.
    for i in range(len(STAGE5) - 1):
        assert STAGE5[i] < STAGE5[i + 1]
    for i in range(len(STAGE18) - 1):
        assert STAGE18[i] < STAGE18[i + 1]
    which = sys.argv[1] if len(sys.argv) > 1 else "db"
    if which in ("db", "all"):
        emit_bank5(rom)
        emit_bank18(rom)
        emit_bank24(rom)
        emit_bank23(rom)
        emit_bank12(rom)
    if which in ("bank1", "all"):
        emit_bank1(rom)


if __name__ == "__main__":
    main()
