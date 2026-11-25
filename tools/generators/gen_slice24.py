#!/usr/bin/env python3
"""Slice-24 generator: bank 6 ($06) run-1 stage data $4000-$7364.

Survey (see tools/surveys/survey24_bank6.py for the reproducible numbers):
  * Bank 6 holds stages 45-79 (run 1 of the bank-5 stage pointer
    table, slice 4). The 35 starts tile the bank contiguously:
    every stage ends exactly where the next begins (sizes 213-555
    bytes); stage 79 ($71a1) runs 451 bytes to the last non-$ff
    byte at $7364 ($00); $7365-$7fff is all $ff padding (stays
    INCBIN). Union $4000-$7364 = 13,157 bytes, zero gaps.
  * The ONLY `ld a,$06; rst $10` site in the whole ROM is bank-0
    $2615, inside SwitchBankByE ($2611: E < $2d -> ret, else bank
    6; E >= $50 -> bank $12). Bank 6 is reached only via LoadStage
    ($24e7) -> SwitchBankByE, as decompressor input; no bank-6
    byte can ever execute. gb_rd walk from $4000 derails in 101
    instructions (targets outside the window); opcode counts are
    data-level (ret 6 / call 161 / jp 3 across the bank, unevenly
    spread, cf. bank 15 in slice 23).
  * The 5-byte stage header is VERIFIED from LoadStage itself:
    after mapping the stage bank it reads 5 bytes from the stage
    start into [$c705], [$da45], [$da4b], [$c711], [$c712] in
    order ($2516-$2527), and only then is the rest of the stream
    decompressed ($257f family). Header value sets across the 35
    bank-6 stages: byte0 {0,1,2,3}, byte1 {7..35}, byte2
    {1,2,4,6,7,9,11,17,18,22,26,31}, byte3
    {0x96,0xc8,0xfa,0x2c,0x64}, byte4 mostly $00 (a few $01).
    What each header byte MEANS is unverified (no reader of
    $c705/$da45/$da4b/$c711/$c712 has been traced in this slice),
    so the header is labelled with its WRAM destinations only.
  * No embedded pointer table: dw values pointing in-bank are
    1,304/16,383 (~8%, below the ~25% random rate), and the stage
    spans already cover every byte, leaving no room for one.
    The stage bodies are compressed level data (RLE + LZ + patch
    list per slice 4); no per-stream boundaries are established,
    so bodies are plain db -- no stream starts claimed.

So the carve emits $4000-$7364 as structured db: one label per
stage (Bank6_Stage45 .. Bank6_Stage79), the 5 header bytes as one
db line with the WRAM destinations in a comment, then the body as
plain db lines, 16 bytes each. No code is claimed anywhere.

Door / clear chain: bank 6 has no code, so it writes no timer
($ff90) and no [$c105]; no new door lead, no completion attempt
(same NO-GO as slices 15-23).

Regenerate with: python3 tools/generators/gen_slice24.py
Outputs: src/banks/bank6.asm, src/banks/bank17.asm (new files).
Also update tools/generators/gen_banks.py CARVED (banks 6, 17) and regenerate
src/banks.asm; add INCLUDEs to src/main.asm.
The outputs are CHECKED IN; rerun after changing the config.

Bank 17 (fill -- $11, $4000-$69ef, 10,736 bytes):
surveyed by tools/surveys/survey24_bank17.py. Three `ld a,$11; rst $10`
sites, all in bank-0 $3202-$32fc (state-16 tile-load routines):
  * $4000: 8-entry dw table, read by $3202 ($4000+B*2, B = queue
    B from QueueFetchBC $0dda, gated on C==3). Entries
    $4070,$4070,$4530,$4870,$4d30,$4070,$4070,$4070; the $3202
    copy is $04c0 bytes to VRAM $8040 (MemcpyBC $1065). Entry 8
    would read $4010 = $0001, an invalid pointer -- the partition
    test, same pattern as slice 23's bank-15 table. C==3 queue
    B values are {0,1,2,4} (enumerated from the bank-12 queue
    table $4f97, 331 pairs), all inside the 8-entry table.
  * $4010-$406f: 24 4-byte records [flag][00][dw block ptr] in 3
    groups of 8 ($4010/$4030/$4050), one group per reader entry:
    $4010 by $323d, $4030 by $3291 (sets [$c809]=$4030), $4050
    by $32fc (`ld de,$4050; jr $3294`, the only such site in the
    ROM). Each reader does base+B*4, tests the flag byte (0 =
    skip via $1778), and copies 16 bytes (MemcpyC $106e) from
    ptr+counter*8 ($323d, slots at $8040) or ptr+counter*16
    ($3291/$32fc, slots at $8500) to $c809. All 24 records are
    plausible (flag in {0,1}, b1 $00, dw in {$5110,$55d0,$5970,
    $5e30,$6530}); flags repeat per group as [1,1,1,1,1,1,0,0];
    groups 1 and 2 have identical dw sequences. Record 24
    ($4070) breaks the pattern (dw $0000) -- the partition test.
    Whether queue B ever exceeds 7 in the record phases is NOT
    verified live (the queue as a whole has B up to 203); the
    8-per-group extent rests on the three reader bases + the
    pattern break at $4070, and is stated as such.
  * $4070-$69ef: data blocks, emitted as plain db with labels at
    the 9 starts the tables reference ($4070/$4530/$4870/$4d30
    from the $4000 table; $5110/$55d0/$5970/$5e30/$6530 from the
    records). Block sizes are NOT claimed (only the $04c0 copy
    length for $4000-table targets and the 16-byte record copies
    are verified); $4070 and $4870 open with identical bytes
    (`00 00 00 00 40 00 70 00 3c 10 7f 0c 0c 03 03 00`), the rest
    open with zeros except $55d0 and $5e30. No code anywhere in
    the bank: gb_rd from $4000 derails in 42 instructions, and
    the only bank-17 mappings are the three data readers above.

Banks 19-22, 25, 26, 30 (fill -- see the emit_* docstrings):
banks 19-22 are $2470 stream data (bank-14 record targets);
banks 25/26 are TransferTable1E sources (bank-30 $74e5 items);
bank 30 is SGB packets ($40e0-$470f, zero-gap) + the $64e5
10-page table + the $74e5 TransferTable1E table/lists, with
$4710-$64e4 / $6de5-$74e4 as plain db (no reader pinned).
Surveys: tools/surveys/survey24_banks1922.py, survey24_banks2530.py.
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
BANK = 6
LO, HI = 0x4000, 0x7365  # HI exclusive; last non-$ff byte at $7364

# Run-1 stage starts from the bank-5 table (src/banks/bank5.asm).
STAGE6 = [0x4000, 0x4181, 0x43ac, 0x44ac, 0x4589, 0x4741, 0x48c5, 0x4a19,
          0x4c25, 0x4d54, 0x4ec8, 0x4fce, 0x50d9, 0x5235, 0x53e5, 0x5504,
          0x565f, 0x579b, 0x59b7, 0x5a8c, 0x5c42, 0x5d9a, 0x5f33, 0x60ad,
          0x61fc, 0x638d, 0x6555, 0x66d8, 0x68c8, 0x6a4e, 0x6bda, 0x6cbf,
          0x6e78, 0x6ffb, 0x71a1]

HDR_DST = ["$c705", "$da45", "$da4b", "$c711", "$c712"]


def main():
    rom = open(ROM, "rb").read()

    def byte(a):
        return rom[file_off(BANK, a)]

    # Stage spans tile contiguously and end at the last non-$ff byte.
    for i in range(len(STAGE6) - 1):
        assert STAGE6[i] < STAGE6[i + 1]
    assert STAGE6[-1] < HI

    out = []
    out.append("; Slice 24: bank 6 ($06) run-1 stage data $4000-$7364.")
    out.append("; Stages 45-79 from the bank-5 pointer table (slice 4);")
    out.append("; reached only via LoadStage ($24e7) -> SwitchBankByE")
    out.append("; ($2611), as decompressor input. No code anywhere:")
    out.append("; the only `ld a,$06; rst $10` site in the ROM is")
    out.append("; inside SwitchBankByE itself. Each stage starts with")
    out.append("; a 5-byte header (verified from LoadStage $2516-$2527):")
    out.append("; bytes -> [$c705], [$da45], [$da4b], [$c711], [$c712].")
    out.append("; Header roles are unverified; bodies are compressed")
    out.append("; level data, emitted as plain db. Generated by")
    out.append("; tools/generators/gen_slice24.py from the ROM bytes.")
    out.append("; Byte-match (`make`) arbitrates.")
    out.append("")
    out.append('SECTION "Bank 6 stage data $4000-$7364", '
               "ROMX[$4000], BANK[6]")

    emitted = 0
    for i, s in enumerate(STAGE6):
        n = 45 + i
        end = STAGE6[i + 1] if i + 1 < len(STAGE6) else HI
        hdr = [byte(s + k) for k in range(5)]
        dst = ", ".join(f"{HDR_DST[k]}=${hdr[k]:02x}" for k in range(5))
        out.append(f"Bank6_Stage{n}::  ; stage {n} ${s:04x}-${end - 1:04x} "
                   f"({end - s} bytes)")
        out.append("    db " + ", ".join(f"${x:02x}" for x in hdr)
                   + f"  ; header: {dst}")
        emitted += 5
        a = s + 5
        while a < end:
            chunk = min(16, end - a)
            vals = [byte(a + k) for k in range(chunk)]
            out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
            emitted += chunk
            a += chunk
        out.append("")
    assert emitted == HI - LO, f"emitted {emitted} != {HI - LO}"
    with open("src/banks/bank6.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank6.asm: {len(out)} lines, {emitted} bytes "
          f"${LO:04x}-${HI - 1:04x}, {len(STAGE6)} stages")
    emit_bank17(rom)
    emit_stream_banks(rom)
    emit_banks2526(rom)
    emit_bank30(rom)
    emit_bank27(rom)
    emit_bank28(rom)


def emit_bank17(rom):
    """Bank 17 ($11): $4000 8-entry dw table, $4010 24 4-byte records
    in 3 groups of 8, $4070-$69ef data blocks as plain db with
    labels at the 9 starts the tables reference."""
    bank = 17
    lo, hi = 0x4000, 0x69F0  # HI exclusive; last non-$ff byte $69ef

    def byte(a):
        return rom[file_off(bank, a)]

    def rdw(a):
        return byte(a) | (byte(a + 1) << 8)

    # $4000 table: 8 dw entries, partition-tested ($4010 = $0001).
    entries = [rdw(0x4000 + 2 * i) for i in range(8)]
    assert rdw(0x4010) == 0x0001
    for p in entries:
        assert 0x4070 <= p <= 0x69EF, f"table entry ${p:04x}"
    # Records: 24 x [flag][00][dw]; pattern breaks at k=24 ($4070).
    records = []
    for k in range(24):
        a = 0x4010 + 4 * k
        fl, b1, dw = byte(a), byte(a + 1), rdw(a + 2)
        assert fl in (0, 1) and b1 == 0 and 0x4070 <= dw <= 0x69EF, \
            f"record {k} ${a:04x}: flag={fl:02x} b1={b1:02x} dw=${dw:04x}"
        records.append((fl, dw))
    assert rdw(0x4072) == 0x0000  # k=24 breaks: $4070 is block data

    out = []
    out.append("; Slice 24: bank 17 ($11) tile data $4000-$69ef.")
    out.append("; $4000: 8-entry dw table read by bank-0 $3202")
    out.append("; ($4000+B*2, queue B, C==3 gate); each entry is a")
    out.append("; $04c0-byte block copied to VRAM $8040. $4010-$406f:")
    out.append("; 24 4-byte records [flag][00][dw ptr] in 3 groups")
    out.append("; of 8 ($4010 by $323d, $4030 by $3291, $4050 by")
    out.append("; $32fc); flag 0 skips, else 16 bytes copied from")
    out.append("; ptr+counter*8/16 to $c809. $4070-$69ef: data blocks")
    out.append("; as plain db, labelled at the 9 referenced starts.")
    out.append("; No code anywhere in the bank. Generated by")
    out.append("; tools/generators/gen_slice24.py from the ROM bytes.")
    out.append("; Byte-match (`make`) arbitrates.")
    out.append("")
    out.append('SECTION "Bank 17 block table $4000-$400f", '
               "ROMX[$4000], BANK[17]")
    out.append("Bank17_BlockTable::")
    for i, p in enumerate(entries):
        out.append(f"    dw Bank17_Block_{p:04X}"
                   f"  ; entry {i} -> block ${p:04x}")
    out.append("")
    out.append('SECTION "Bank 17 record table $4010-$406f", '
               "ROMX[$4010], BANK[17]")
    for g in range(3):
        base = 0x4010 + 32 * g
        reader = ("$323d", "$3291", "$32fc")[g]
        out.append(f"Bank17_Records{g}::  ; group {g} ${base:04x}, "
                   f"read by bank-0 {reader}")
        for k in range(8):
            fl, dw = records[8 * g + k]
            out.append(f"    db ${fl:02x}, $00"
                       f"  ; record {8 * g + k} flag={fl}")
            out.append(f"    dw Bank17_Block_{dw:04X}")
    out.append("")
    out.append('SECTION "Bank 17 data $4070-$69ef", '
               "ROMX[$4070], BANK[17]")
    blocks = sorted(set(entries) |
                    set(dw for _fl, dw in records))
    a = 0x4070
    emitted = 16 + 96  # table + records
    while a < hi:
        if a in blocks:
            out.append(f"Bank17_Block_{a:04X}::  ; referenced block "
                       f"start ${a:04x}")
        chunk = min(16, hi - a)
        # Don't let a db line cross a block-start label.
        for s in blocks:
            if a < s < a + chunk:
                chunk = s - a
        vals = [byte(a + k) for k in range(chunk)]
        out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
        emitted += chunk
        a += chunk
    assert emitted == hi - lo, f"emitted {emitted} != {hi - lo}"
    assert a == hi
    with open("src/banks/bank17.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank17.asm: {len(out)} lines, {emitted} bytes "
          f"${lo:04x}-${hi - 1:04x}, {len(blocks)} referenced blocks")


def emit_stream_banks(rom):
    """Banks 19-22 ($13-$16): stream data as plain db, slice-23
    bank-13 pattern. Surveyed by tools/surveys/survey24_banks1922.py:
    no `ld a,$xx; rst $10` site for any of them anywhere in the
    ROM; the only mapping is bank-0 $2470's H >= $7e branch,
    which reads a bank-14 record [bank][ptr], maps the record
    bank, and follows ptr+DE as a Decompress $257f / MemcpyC
    $106e source (bank-12 $4a3e beforehand only reads a $4eeb
    table byte into E, never jumps into the record bank). Record
    counts / ptr ranges: bank 19: 25 records $4000-$7ade; bank
    20: 36 records $4000-$79a8; bank 21: 28 records $4000-$77c6;
    bank 22: 28 records $4000-$7c7c. gb_rd walks from $4000
    derail in 75 / 24 / 43 / 192 instructions; the code-like
    opcode counts (bank 19 $5000: ret 21 / rst $08 87; bank 22
    $6000: jp 45) are data bytes, as in slice 23's bank 15 --
    no call/jp/jr/table target into any of these banks exists.
    No per-stream boundaries are established, so the carve is
    plain db $4000 to the last non-$ff byte; $ff tails stay
    INCBIN. No code is claimed anywhere in these banks."""
    for bank, last in ((19, 0x7B7F), (20, 0x7BB9),
                       (21, 0x7990), (22, 0x7F0B)):
        hi = last + 1
        out = [f"; Slice 24: bank {bank} (${bank:02x}) stream data "
               f"$4000-${last:04x}.",
               "; Read via bank-0 $2470 as Decompress $257f / MemcpyC",
               "; $106e input (bank-14 record [bank][ptr]); no code",
               "; anywhere in the bank. Generated by",
               "; tools/generators/gen_slice24.py from the ROM bytes.",
               "; Byte-match (`make`) arbitrates.",
               "",
               f'SECTION "Bank {bank} stream data $4000-${last:04x}", '
               f"ROMX[$4000], BANK[{bank}]"]
        a = 0x4000
        while a < hi:
            chunk = min(16, hi - a)
            vals = [rom[file_off(bank, a + k)] for k in range(chunk)]
            out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
            a += chunk
        fname = f"src/banks/bank{bank}.asm"
        with open(fname, "w") as f:
            f.write("\n".join(out) + "\n")
        print(f"{fname}: {len(out)} lines, {hi - 0x4000} bytes "
              f"$4000-${last:04x}")


def emit_banks2526(rom):
    """Banks 25/26 ($19/$1a): transfer data as plain db.
    Surveyed by tools/surveys/survey24_banks2530.py: no `ld a,$xx;
    rst $10` site for either bank anywhere in the ROM; the only
    mapping is bank-0 $1da7 TransferTable1E, whose 7-byte items
    name the source bank (bank-30 $74e5 table: 3 items from bank
    $19, src $6103/$642c/$65cc, all decompress, len $0000; 14
    items from bank $1a, src $4000-$698a). gb_rd walks from
    $4000 derail in 27 / 32 instructions; no call/jp/jr/table
    target into either bank exists. No per-stream boundaries
    are established, so the carve is plain db $4000 to the last
    non-$ff byte; $ff tails stay INCBIN. No code is claimed."""
    for bank, last in ((25, 0x67E1), (26, 0x705C)):
        hi = last + 1
        out = [f"; Slice 24: bank {bank} (${bank:02x}) transfer data "
               f"$4000-${last:04x}.",
               "; Read via bank-0 $1da7 TransferTable1E (bank-30",
               "; $74e5 table items name the source bank); no code",
               "; anywhere in the bank. Generated by",
               "; tools/generators/gen_slice24.py from the ROM bytes.",
               "; Byte-match (`make`) arbitrates.",
               "",
               f'SECTION "Bank {bank} transfer data $4000-${last:04x}", '
               f"ROMX[$4000], BANK[{bank}]"]
        a = 0x4000
        while a < hi:
            chunk = min(16, hi - a)
            vals = [rom[file_off(bank, a + k)] for k in range(chunk)]
            out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
            a += chunk
        fname = f"src/banks/bank{bank}.asm"
        with open(fname, "w") as f:
            f.write("\n".join(out) + "\n")
        print(f"{fname}: {len(out)} lines, {hi - 0x4000} bytes "
              f"$4000-${last:04x}")


def emit_bank30(rom):
    """Bank 30 ($1e): SGB packets + $64e5 page table + $74e5
    TransferTable1E table + lists. Surveyed by
    tools/surveys/survey24_banks2530.py:
      * $40e0-$470f: SGB packets. The slice-3 $4000 table has
        112 entries / 98 distinct ptrs; each packet is 16*n
        bytes (n = first byte & 7; 97 x n=1, 1 x n=2 at $4590,
        spanning 32 bytes to $45b0). Spans tile $40e0-$4710
        with zero gaps. Emitted as db with a label per distinct
        packet start.
      * $4710-$64e4 and $6de5-$74e4: plain db -- no reader pinned
        in this slice (honest gap, cf. slice 23's bank-14 low
        region). The only non-SGB bank-30 reader found is
        LoadStagePtr ($1c91), which reads the $64e5 table.
      * $64e5-$6de4: 10 pages x 256 bytes, read by LoadStagePtr
        ($1c91/$1cd9: HL=$64e5+DE, DE=(D<<8)|E, D in 0..9 from
        the $1c9c/$1cca branch logic, E a byte from the caller's
        table; 16 bytes copied to $da61). D's 0..9 bound is
        inferred from the branch logic, not verified live.
      * $74e5-$7546: 49-entry dw table (TransferTable1E index,
        A = entry; (0x7547-0x74e5)/2 = 49 exactly).
      * $7547-$7cf9: 39 distinct lists [count][count x 7-byte
        items: bank, src dw, dst dw, len lo, len hi+flags]
        (bit 7 of the last byte selects Decompress $257f, len
        $0000 means DecompressPrefixed). 276 items total; lists
        tile $7547-$7cfa with zero gaps; source banks
        {$04,$0d,$0e,$11,$13,$14,$16,$18,$19,$1a,$1b,$1c}.
        Counts run 1..17 (the $7987 list has 17 -- the <=16
        cap in the first probe was wrong; all 17 items parse
        cleanly). $7cfa-$7fff is $ff padding (stays INCBIN).
        No code is claimed anywhere in the bank."""
    bank = 30

    def byte(a):
        return rom[file_off(bank, a)]

    def rdw(a):
        return byte(a) | (byte(a + 1) << 8)

    # Packets: 98 distinct starts, 16*n spans, $40e0-$4710.
    pkt_entries = [rdw(0x4000 + 2 * i) for i in range(112)]
    pkt_starts = sorted(set(pkt_entries))
    for p in pkt_starts:
        n = byte(p) & 7
        assert 1 <= n <= 7
    spans = [(p, p + 16 * (byte(p) & 7)) for p in pkt_starts]
    cur = 0x40E0
    for a, b in spans:
        assert a == cur, f"packet gap/overlap at ${a:04x} (cur ${cur:04x})"
        cur = b
    assert cur == 0x4710
    # $74e5 table: 49 entries -> 39 distinct lists, $7547-$7cfa.
    entries = [rdw(0x74E5 + 2 * i) for i in range(49)]
    lists = {}
    for p in sorted(set(entries)):
        cnt = byte(p)
        assert 1 <= cnt <= 32, f"list ${p:04x} count {cnt}"
        items = []
        for k in range(cnt):
            a = p + 1 + 7 * k
            bk = byte(a)
            src, dst = rdw(a + 1), rdw(a + 3)
            lo, hi = byte(a + 5), byte(a + 6)
            assert bk <= 0x1F and 0x4000 <= src <= 0x7FFF
            assert 0x8000 <= dst <= 0x9FFF
            items.append((bk, src, dst, lo, hi))
        lists[p] = (cnt, items)
    lspans = sorted((p, p + 1 + 7 * c) for p, (c, _i) in lists.items())
    cur = 0x7547
    for a, b in lspans:
        assert a == cur, f"list gap/overlap at ${a:04x}"
        cur = b
    assert cur == 0x7CFA

    def emit_db(out, lo, hi, labels=()):
        """Plain db lines for [lo, hi), with optional address labels."""
        lab = dict(labels)
        a = lo
        n = 0
        while a < hi:
            if a in lab:
                out.append(f"{lab[a]}::")
            chunk = min(16, hi - a)
            for s in sorted(lab):
                if a < s < a + chunk:
                    chunk = s - a
            vals = [byte(a + k) for k in range(chunk)]
            out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
            n += chunk
            a += chunk
        return n

    out = []
    out.append("; Slice 24: bank 30 ($1e) SGB packets + tables.")
    out.append("; $40e0-$470f: SGB packets (16 bytes per unit, n =")
    out.append("; first byte & 7; 98 distinct starts, zero-gap")
    out.append("; coverage). $4710-$64e4 / $6de5-$74e4: plain db,")
    out.append("; no reader pinned (honest gap). $64e5-$6de4: 10")
    out.append("; pages x 256 bytes read by LoadStagePtr ($1c91).")
    out.append("; $74e5-$7546: 49-entry TransferTable1E dw table.")
    out.append("; $7547-$7cf9: 39 lists of 7-byte transfer items")
    out.append("; (276 items). No code anywhere in the bank.")
    out.append("; Generated by tools/generators/gen_slice24.py from the ROM")
    out.append("; bytes. Byte-match (`make`) arbitrates.")
    out.append("")
    out.append('SECTION "Bank 30 SGB packets $40e0-$470f", '
               "ROMX[$40e0], BANK[30]")
    emitted = emit_db(out, 0x40E0, 0x4710,
                      [(p, f"Bank30_Packet_{p:04X}") for p in pkt_starts])
    out.append("")
    out.append('SECTION "Bank 30 data $4710-$64e4", '
               "ROMX[$4710], BANK[30]")
    emitted += emit_db(out, 0x4710, 0x64E5)
    out.append("")
    out.append('SECTION "Bank 30 page table $64e5-$6de4", '
               "ROMX[$64e5], BANK[30]")
    pages = [(0x64E5 + 256 * k, f"Bank30_Page{k}") for k in range(10)]
    emitted += emit_db(out, 0x64E5, 0x6DE5, pages)
    out.append("")
    out.append('SECTION "Bank 30 data $6de5-$74e4", '
               "ROMX[$6de5], BANK[30]")
    emitted += emit_db(out, 0x6DE5, 0x74E5)
    out.append("")
    out.append('SECTION "Bank 30 TransferTable1E $74e5-$7546", '
               "ROMX[$74e5], BANK[30]")
    out.append("Bank30_T1ETable::")
    for i, p in enumerate(entries):
        out.append(f"    dw Bank30_T1EList_{p:04X}"
                   f"  ; entry {i} -> list ${p:04x}")
        emitted += 2
    out.append("")
    out.append('SECTION "Bank 30 TransferTable1E lists $7547-$7cf9", '
               "ROMX[$7547], BANK[30]")
    for p in sorted(lists):
        cnt, items = lists[p]
        out.append(f"Bank30_T1EList_{p:04X}::  ; list ${p:04x}, "
                   f"{cnt} item(s)")
        out.append(f"    db ${cnt:02x}")
        emitted += 1
        for (bk, src, dst, lo, hi) in items:
            ln = lo | ((hi & 0x7F) << 8)
            dec = "decompress" if hi & 0x80 else "memcpy"
            out.append(f"    db ${bk:02x}  ; src bank ${bk:02x}")
            out.append(f"    dw ${src:04x}  ; src")
            out.append(f"    dw ${dst:04x}  ; dst, len ${ln:04x} {dec}")
            out.append(f"    db ${lo:02x}, ${hi:02x}")
            emitted += 7
    assert emitted == 0x7CFA - 0x40E0, \
        f"emitted {emitted} != {0x7CFA - 0x40E0}"
    with open("src/banks/bank30.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank30.asm: {len(out)} lines, {emitted} bytes "
          f"$40e0-$7cf9, {len(pkt_starts)} packets, "
          f"{len(lists)} lists, {sum(c for c, _ in lists.values())} items")


def emit_bank27(rom):
    """Bank 27 ($1b): sprite data + $7918 sprite table + lists.
    Surveyed by tools/surveys/survey24_bank27.py:
      * $4000-$7917: plain db (tile/sprite data). Read via
        bank-0 $1da7 TransferTable1E (91 items from bank $1b,
        43 distinct srcs $4000-$732b) and via the $7918 table
        lists below. No per-block boundaries are established.
      * $7918-$7971: 45-entry dw table, read by BuildSpriteEntries
        ($1dfd: $7918 + A*2 -> list ptr). Entry 45 would read
        $7972 = $0009 (the first list's count byte) -- the
        partition test, table is 45 entries.
      * $7972-$7ea8: 45 lists [count][count x 6-byte items]:
        [index][b0][b1][b2][b3][b4]; the index byte selects the
        $c200 + index*32 slot, the other 5 bytes fill the
        12-byte record (bytes 0-3, byte 7). 215 items total;
        lists tile $7972-$7ea9 with zero gaps (the first probe
        used 5-byte items and showed phantom gaps; the reader
        consumes 1 index + 5 data bytes = 6 per item). Index
        byte values are 0-14 (15 distinct). $7ea9-$7fff is $ff
        padding (stays INCBIN). No code is claimed anywhere in
        the bank: gb_rd from $4000 derails in 1 instruction."""
    bank = 27

    def byte(a):
        return rom[file_off(bank, a)]

    def rdw(a):
        return byte(a) | (byte(a + 1) << 8)

    entries = [rdw(0x7918 + 2 * i) for i in range(45)]
    assert rdw(0x7972) == 0x0009  # entry 45 would read the count byte
    lists = {}
    for p in sorted(set(entries)):
        cnt = byte(p)
        assert 1 <= cnt <= 32, f"list ${p:04x} count {cnt}"
        items = []
        for k in range(cnt):
            a = p + 1 + 6 * k
            items.append(tuple(byte(a + j) for j in range(6)))
        lists[p] = (cnt, items)
    spans = sorted((p, p + 1 + 6 * c) for p, (c, _i) in lists.items())
    cur = 0x7972
    for a, b in spans:
        assert a == cur, f"list gap/overlap at ${a:04x}"
        cur = b
    assert cur == 0x7EA9

    out = []
    out.append("; Slice 24: bank 27 ($1b) sprite data + table.")
    out.append("; $4000-$7917: sprite/tile data as plain db (read")
    out.append("; via TransferTable1E). $7918-$7971: 45-entry dw")
    out.append("; table read by BuildSpriteEntries ($1dfd).")
    out.append("; $7972-$7ea8: 45 lists of 6-byte sprite items")
    out.append("; [index][5 data bytes], 215 items, zero-gap.")
    out.append("; No code anywhere in the bank. Generated by")
    out.append("; tools/generators/gen_slice24.py from the ROM bytes.")
    out.append("; Byte-match (`make`) arbitrates.")
    out.append("")
    out.append('SECTION "Bank 27 sprite data $4000-$7917", '
               "ROMX[$4000], BANK[27]")
    emitted = 0
    a = 0x4000
    while a < 0x7918:
        chunk = min(16, 0x7918 - a)
        vals = [byte(a + k) for k in range(chunk)]
        out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
        emitted += chunk
        a += chunk
    out.append("")
    out.append('SECTION "Bank 27 sprite table $7918-$7971", '
               "ROMX[$7918], BANK[27]")
    out.append("Bank27_SpriteTable::")
    for i, p in enumerate(entries):
        out.append(f"    dw Bank27_SpriteList_{p:04X}"
                   f"  ; entry {i} -> list ${p:04x}")
        emitted += 2
    out.append("")
    out.append('SECTION "Bank 27 sprite lists $7972-$7ea8", '
               "ROMX[$7972], BANK[27]")
    for p in sorted(lists):
        cnt, items = lists[p]
        out.append(f"Bank27_SpriteList_{p:04X}::  ; list ${p:04x}, "
                   f"{cnt} item(s)")
        out.append(f"    db ${cnt:02x}")
        emitted += 1
        for it in items:
            out.append("    db " + ", ".join(f"${x:02x}" for x in it)
                       + f"  ; slot {it[0]}")
            emitted += 6
    assert emitted == 0x7EA9 - 0x4000, \
        f"emitted {emitted} != {0x7EA9 - 0x4000}"
    with open("src/banks/bank27.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank27.asm: {len(out)} lines, {emitted} bytes "
          f"$4000-$7ea8, {len(lists)} lists, "
          f"{sum(c for c, _ in lists.values())} items")


def emit_bank28(rom):
    """Bank 28 ($1c): stream-record table + pool.
    Surveyed by tools/surveys/survey24_bank28.py:
      * $4000-$409b: 78-entry dw table, read by bank-0 $143e
        StreamDispatchRecordD ($4000 + C*2 -> stream base, C =
        record byte0 & $7f; +B, B = record byte1*2). Entry 78
        (@$409c) would read $f100 -- implausible -- so the
        table is 78 entries; min plausible target is $409e.
        Entries 0-77: 56 distinct targets, all in
        [$409e, $43b2]. The pool head $409c-$409d is `00 f1`,
        a marker pair -- confirming the $409c bytes are pool,
        not table.
      * $409c-$6c46: stream pool as plain db, labelled at the
        56 distinct table targets. The $143e loop walks 2-byte
        values with $f0/$f1 high-byte markers ($f0 x71, $f1
        x85 in the pool) and never jumps/calls into the pool.
        Per-stream boundaries beyond the table targets are NOT
        claimed (targets overlap into a shared pool; +B offsets
        reach further in). Second mapping: bank-0 $2470 B >=
        $af branch (Decompress $257f input). $6c47-$7fff is $ff
        padding (stays INCBIN). No code is claimed anywhere in
        the bank: gb_rd from $4000 derails in 11 instructions."""
    bank = 28

    def byte(a):
        return rom[file_off(bank, a)]

    def rdw(a):
        return byte(a) | (byte(a + 1) << 8)

    entries = [rdw(0x4000 + 2 * i) for i in range(78)]
    assert rdw(0x409C) == 0xF100  # entry 78 is implausible
    for t in entries:
        assert 0x409E <= t <= 0x6C46, f"table target ${t:04x}"
    targets = sorted(set(entries))

    out = []
    out.append("; Slice 24: bank 28 ($1c) stream table + pool.")
    out.append("; $4000-$409b: 78-entry dw table read by bank-0")
    out.append("; $143e StreamDispatchRecordD ($4000+C*2 -> base).")
    out.append("; $409c-$6c46: stream pool as plain db, labelled")
    out.append("; at the 56 distinct table targets; $f0/$f1 are")
    out.append("; stream markers, not code. No code anywhere in")
    out.append("; the bank. Generated by tools/generators/gen_slice24.py")
    out.append("; from the ROM bytes. Byte-match (`make`) arbitrates.")
    out.append("")
    out.append('SECTION "Bank 28 stream table $4000-$409b", '
               "ROMX[$4000], BANK[28]")
    out.append("Bank28_StreamTable::")
    emitted = 0
    for i, t in enumerate(entries):
        out.append(f"    dw Bank28_Stream_{t:04X}"
                   f"  ; entry {i} -> stream ${t:04x}")
        emitted += 2
    out.append("")
    out.append('SECTION "Bank 28 stream pool $409c-$6c46", '
               "ROMX[$409c], BANK[28]")
    a = 0x409C
    hi = 0x6C47
    while a < hi:
        if a in targets:
            out.append(f"Bank28_Stream_{a:04X}::  ; stream ${a:04x}")
        chunk = min(16, hi - a)
        for s in targets:
            if a < s < a + chunk:
                chunk = s - a
        vals = [byte(a + k) for k in range(chunk)]
        out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
        emitted += chunk
        a += chunk
    assert emitted == hi - 0x4000, \
        f"emitted {emitted} != {hi - 0x4000}"
    with open("src/banks/bank28.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/banks/bank28.asm: {len(out)} lines, {emitted} bytes "
          f"$4000-$6c46, {len(targets)} distinct stream targets")


if __name__ == "__main__":
    main()
