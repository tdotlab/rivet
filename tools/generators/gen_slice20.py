#!/usr/bin/env python3
"""Slice-20 generator: close out bank 31 (all 26 remaining gaps, 978
bytes) and carve bank 10 (decimal, $0a) whole -- every one of its 34
gaps, $480a-$705e plus $75b0-$7730, $789f-$7951, $79ea-$7ab8,
$7b12-$7b3f, $7b6c-$7c24, $7cb0-$7e50 and $7f44-$8000.

Bank 31 -- every gap was classified from the carved code that reads
it (ld hl bases in src/banks/bank31slice17.asm / slice18 / slice19, jp-hl
dispatch tables, call/jp/jr targets). Summary:
  * dw tables: $467f (5 WRAM ptrs), $4fd3 (3, + routines $4fd9-$503b),
    $6188 (3, + routines $618e-$61a4), $67f8 (4, + routines $680e-$68db).
  * 14-byte record tables (memcpy'd with ld c,$14; call $106e):
    $48c7 (2), $4c9c (4), $4d8a (2), $6152 (2), $6b53 (2).
  * Other data: $4f9b (30B blob: 20B memcpy src + 4x4B indexed at
    $4fa9), $5407 (7B, indexed by [$c705]), $5445 (6B, 3x2B),
    $57a1 (32B, 16x2B pairs), $6da2 (8B, no reference found in carved
    code), $6df6 (4x5B records), $6e84 (12B memcpy template + 5B byte
    table at $6e90), $7306 (4x4B records), $7371/$73d1/$7434/$74d5
    (3B each), $775f (11x2B pairs; $7765 is also a 16B memcpy src),
    $792e (two 3B tables).
  * Code: $7db9-$7de3 (call $7db9 at $6426, call $7dcc at $6463),
    $7e44-$7e7d ($7e44 called from bank-0 $2aaa; $7e61 jp'd to from
    $71ba), $7f5f (1-byte ret; entry unverified -- could equally be
    the first byte of the $7f60 table) + $7f60-$7fff 160B 00/01 table
    indexed by [$dd18].

Bank 10 (decimal) -- the gaps are dw dispatch tables (read by the
$2b48-entry handlers carved in slices 15/16: ld a,[$c10a]; add a;
ld hl,$TABLE; ...; jp hl) plus their routines, with 14-byte data
records interleaved (each verified by an ld hl/ld de reference from
the walked routines). Table entry counts were fixed by the
partition test: first entry == table base + 2*N, and the walk from
all entries covers [first entry, next carved range) exactly, apart
from the noted data records. Tables: $480a (16), $4e56 (8), $51a1
(2), $524b (5), $534b (4), $5421 (5), $56b1 (4), $56fb (3), $5894
(4), $5918 (6), $5eca (15), $6414 (6), $65a2 (7), $67ac (7), $69de
(7), $6b08 (7), $6d9a (7), $6f66 (16), $7d0e (4, read by the $7cb0
routine's jp hl), $7e3c (10, entries are the $763a-$76ee routines;
reader unidentified), $7fb6 (8 signed offsets, read at $4e0b).
Other code: $4ae3 (jr nz,$4ae3 at $4adb), $4d5e, $4db7 (jp'd to from
many $480a-table routines; calls $7a8a), $4fff (entry unverified,
coherent routine chain to $5020), $5212 (entry unverified), $612e
(jr nc,$612e at $60e0), $75b0-$772f ($75c2/$75f7 are computed-jp-hl
targets -- the $759a routine ends jp hl with HL from stage data;
entry mechanism noted, not proven), $789f (fall-through from the
$787d routine), $79ea/$7a20 (calls at $6d19/$6aa5)/$7a8a (call at
$4db7), $7b12 (entry unverified), $7b6c/$7bdf ($7d0e-table entry
0)/$7bfc (jp'd to from five routines), $7cb0 (reads the $7d0e dw
table and scans the $7d16 4-byte records by [$c80d]).
Data: $5085-$5096 (3 groups, 4/6/8B, copied to $dd81), $5097-$50a6
(16B memcpy src), $5d5e (40B; ld de $5d5e/$5d6d, jp $7951),
$5e0a (126B; $5e0a/$5e1c are 18B records passed to $799d, $5e80/
$5e83 are byte tables indexed by [$c10b]), $7f44-$7fb5 (mostly $00
padding with scattered bytes; no code entry found).

Regenerate with: python3 tools/generators/gen_slice20.py
Outputs: src/banks/bank31slice20.asm, src/banks/bank10slice20.asm. Also update
tools/generators/gen_banks.py CARVED (bank 31: all 26 gaps; bank 10: all 34
gaps) and regenerate src/banks.asm; add the two INCLUDEs to
src/main.asm.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def file_off(bank, addr):
    return bank * 0x4000 + (addr - 0x4000)


# ------------------------------------------------------------------
# Shared emit helpers (gen_slice17/18/19 pattern).
# ------------------------------------------------------------------

def jr_targets_in(instrs, lo, hi):
    out = set()
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
            out.add(tgt)
    return out


def fmt_instr(bank, addr, text, kind, tgt, lo, hi, jr_targets, labels):
    if (bank, addr) in labels:
        label = f"{labels[(bank, addr)]}::"
    elif addr in jr_targets:
        label = f"jr_{bank:03x}_{addr:04x}:"
    else:
        label = None
    if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
        if (bank, tgt) in labels:
            tgt_label = labels[(bank, tgt)]
        else:
            tgt_label = f"jr_{bank:03x}_{tgt:04x}"
        text = re.sub(r"\$[0-9a-f]{4}$", tgt_label, text)
    line = f"    {text:<48} ; ${addr:04x}"
    return (label + "\n" + line) if label else line


def emit_carve(rom, bank, lo, hi, title, instrs, labels, slice_tag="Slice 20"):
    section = "ROM0" if bank == 0 else "ROMX"
    bankarg = f", BANK[{bank}]" if bank != 0 else ""
    out = [f"; {slice_tag}: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice20.py from the ROM bytes via",
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
                                 lo, hi, jr_targets, labels))
            addr += ln
        else:
            run = []
            while addr <= hi and addr not in instrs:
                run.append(rom[file_off(bank, addr)])
                addr += 1
            label = labels.get((bank, addr - len(run)))
            if label:
                out.append(f"{label}::")
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def emit_dw_table(rom, bank, lo, entries, title, expected=None, note=None):
    out = [f"; Slice 20: {title} -- bank {bank} ${lo:04x}-"
           f"${lo + 2 * len(entries) - 1:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/generators/gen_slice20.py; values read straight "
               "from the ROM.")
    out.append(f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]')
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
    out = [f"; Slice 20: {title} -- bank {bank} ${lo:04x}-${hi:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/generators/gen_slice20.py; bytes read straight "
               "from the ROM.")
    out.append(f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]')
    addr = lo
    while addr <= hi:
        chunk = [rom[file_off(bank, a)] for a in
                 range(addr, min(addr + 8, hi + 1))]
        out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
        addr += len(chunk)
    return "\n".join(out) + "\n"


def assert_coverage(bank, lo, hi, instrs):
    covered = set()
    for a, (ln, *_r) in instrs.items():
        covered.update(range(a, a + ln))
    missing = sorted(set(range(lo, hi + 1)) - covered)
    assert not missing, \
        f"bank {bank} ${lo:04x}-${hi:04x}: uncovered bytes " \
        f"{[hex(m) for m in missing[:8]]}"


def carve(rom, bank, lo, hi, title, seeds, labels):
    reached, rst08, notes = walk(bank, seeds)
    for n in notes:
        print("note:", n, file=sys.stderr)
    print(f"bank {bank} ${lo:04x}-${hi:04x} walk: {len(reached)} instrs, "
          f"rst08={rst08}", file=sys.stderr)
    assert not rst08, f"unexpected rst $08: {rst08}"
    sub = {a: v for a, v in reached.items() if lo <= a <= hi}
    assert_coverage(bank, lo, hi, sub)
    for a, (ln, *_r) in sub.items():
        assert a + ln - 1 <= hi, \
            f"bank {bank}: instruction at ${a:04x} straddles ${hi:04x}"
    return emit_carve(rom, bank, lo, hi, title, sub, labels)


# ------------------------------------------------------------------
# Bank 31 -- all 26 remaining gaps.
# ------------------------------------------------------------------

B31_LABELS = lambda addrs: {(31, a): f"Bank31_{a:04X}" for a in addrs}


def emit_bank31(rom):
    parts = []
    parts.append(emit_dw_table(
        rom, 31, 0x467F,
        [(0x467F + 2 * i, f"entry {i} -> ${v:04x}")
         for i, v in enumerate([0xDCD8, 0xDCE8, 0xDCC8, 0xDCF8, 0xDCB8])],
        "Bank 31 $467f dw table (5 WRAM pointers)",
        expected=[0xDCD8, 0xDCE8, 0xDCC8, 0xDCF8, 0xDCB8],
        note="Indexed by 2*[$c0a4] (or 2*([$c0a4]-1)) at $464c/$4667; "
             "the pointed-to WRAM byte is set to $01."))
    parts.append(emit_db(
        rom, 31, 0x48C7, 0x48E2,
        "Bank 31 $48c7-$48e2 2x14-byte records",
        note="ld hl,$48c7/$48d5 at $4869/$4872; memcpy'd 14 bytes to "
             "$c1ab (ld c,$14; call $106e)."))
    parts.append(emit_db(
        rom, 31, 0x4C9C, 0x4CD3,
        "Bank 31 $4c9c-$4cd3 4x14-byte records",
        note="ld hl,$4c9c/$4caa/$4cb8/$4cc6 at $4bee/$4c1a/$4c46/$4c76; "
             "memcpy'd 14 bytes to $c1ab."))
    parts.append(emit_db(
        rom, 31, 0x4D8A, 0x4DA5,
        "Bank 31 $4d8a-$4da5 2x14-byte records",
        note="ld hl,$4d8a/$4d98 at $4d29/$4d4a; memcpy'd 14 bytes to "
             "$c1ab."))
    parts.append(emit_db(
        rom, 31, 0x4F9B, 0x4FB8,
        "Bank 31 $4f9b-$4fb8 30-byte data blob",
        note="20 bytes memcpy'd to $c1ab (ld hl,$4f9b; ld c,$14; call "
             "$106e at $4f3b); $4fa9 is also indexed by 2*[$c10d] at "
             "$4f6f (4 bytes read). One blob, two uses."))
    parts.append(emit_dw_table(
        rom, 31, 0x4FD3,
        [(0x4FD3 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate([0x4FD9, 0x500A, 0x503B])],
        "Bank 31 $4fd3 dw table (3 entries, $2b48-entry-76)",
        expected=[0x4FD9, 0x500A, 0x503B],
        note="Read by the $4fb9 handler (ld hl,$4fd3 at $4fcb; "
             "jp hl)."))
    parts.append(carve(
        rom, 31, 0x4FD9, 0x503B,
        "Bank 31 $4fd9-$503b $4fd3-table routines",
        [0x4FD9, 0x500A, 0x503B],
        B31_LABELS([0x4FD9, 0x500A, 0x503B])))
    parts.append(emit_db(
        rom, 31, 0x5407, 0x540D,
        "Bank 31 $5407-$540d 7-byte table",
        note="Indexed by [$c705] (ld hl,$5407 at $53eb); values become "
             "[$c10d]."))
    parts.append(emit_db(
        rom, 31, 0x5445, 0x544A,
        "Bank 31 $5445-$544a 6-byte data (3x2B)",
        note="Indexed by the SeedMul result (ld hl,$5445 at $541c); "
             "2 bytes copied to $c100."))
    parts.append(emit_db(
        rom, 31, 0x57A1, 0x57C0,
        "Bank 31 $57a1-$57c0 16x2-byte pairs",
        note="Indexed by 2*[$c10d] (ld hl,$57a1 at $5747; [$c10d] < 15); "
             "first byte -> [$c10c], second -> [$c0a6+[$c108]-$40]."))
    parts.append(emit_db(
        rom, 31, 0x6152, 0x616D,
        "Bank 31 $6152-$616d 2x14-byte records",
        note="ld hl,$6152/$6160 at $611b/$6124 (choice by [$c0f8] bit "
             "0); memcpy'd 14 bytes to $c1ab."))
    parts.append(emit_dw_table(
        rom, 31, 0x6188,
        [(0x6188 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate([0x618E, 0x6196, 0x61A4])],
        "Bank 31 $6188 dw table (3 entries, $2b48-entry-79)",
        expected=[0x618E, 0x6196, 0x61A4],
        note="Read by the $616e handler (ld hl,$6188 at $6180; "
             "jp hl)."))
    parts.append(carve(
        rom, 31, 0x618E, 0x61A4,
        "Bank 31 $618e-$61a4 $6188-table routines",
        [0x618E, 0x6196, 0x61A4],
        B31_LABELS([0x618E, 0x6196, 0x61A4])))
    parts.append(emit_dw_table(
        rom, 31, 0x67F8,
        [(0x67F8 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate([0x680E, 0x6876, 0x68DA, 0x68DB])],
        "Bank 31 $67f8 dw table (4 entries)",
        expected=[0x680E, 0x6876, 0x68DA, 0x68DB],
        note="Read at $67f0 (ld hl,$67f8; jp hl) by the routine ending "
             "at $67e8."))
    parts.append(emit_db(
        rom, 31, 0x6800, 0x680D,
        "Bank 31 $6800-$680d 14-byte record",
        note="Caught by the byte-match check: sits between the $67f8 "
             "table and the $680e routine. Same 98 a0 e8 f0 repeating "
             "record shape as the other 14-byte records in this bank; "
             "ld hl,$6800 at $446f and $67ca (slice 17)."))
    parts.append(carve(
        rom, 31, 0x680E, 0x68DB,
        "Bank 31 $680e-$68db $67f8-table routines",
        [0x680E, 0x6876, 0x68DA, 0x68DB],
        B31_LABELS([0x680E, 0x6876, 0x68DA, 0x68DB])))
    parts.append(emit_db(
        rom, 31, 0x6B53, 0x6B6E,
        "Bank 31 $6b53-$6b6e 2x14-byte records",
        note="ld hl,$6b53/$6b61 at $6b03/$6b2b; memcpy'd 14 bytes to "
             "$c1ab."))
    parts.append(emit_db(
        rom, 31, 0x6DA2, 0x6DA9,
        "Bank 31 $6da2-$6da9 8-byte data",
        note="No ld hl/call/jp reference found in carved code; plain "
             "db. Sits between the $6d8e 20-byte template and the "
             "$6daa routine."))
    parts.append(emit_db(
        rom, 31, 0x6DF6, 0x6E09,
        "Bank 31 $6df6-$6e09 4x5-byte records",
        note="Indexed by 5*[$c113] (ld hl,$6df6 at $6dba); first byte "
             "-> [$c10c], next 4 memcpy'd to $c1c4."))
    parts.append(emit_db(
        rom, 31, 0x6E84, 0x6E94,
        "Bank 31 $6e84-$6e94 12-byte template + 5-byte table",
        note="$6e84-$6e8f memcpy'd 12 bytes to $c1c4 (ld hl,$6e84; ld "
             "c,$0c; call $106e at $6e2c); $6e90-$6e94 is a byte table "
             "indexed by [$c114] (ld hl,$6e90 at $6d83)."))
    parts.append(emit_db(
        rom, 31, 0x7306, 0x7315,
        "Bank 31 $7306-$7315 4x4-byte records",
        note="ld hl,$7306/$730a/$730e at $727f/$725e/$72a9; memcpy'd 4 "
             "bytes to $c1c4. The $7312 record has no ld hl reference "
             "in carved code."))
    parts.append(emit_db(
        rom, 31, 0x7371, 0x7373,
        "Bank 31 $7371-$7373 3-byte table",
        note="Indexed by the SeedMul result (ld hl,$7371 at $735a); "
             "value -> [$c10d]."))
    parts.append(emit_db(
        rom, 31, 0x73D1, 0x73D3,
        "Bank 31 $73d1-$73d3 3-byte table",
        note="Indexed by the SeedMul result (ld hl,$73d1 at $737c); "
             "value -> [$c10d]."))
    parts.append(emit_db(
        rom, 31, 0x7434, 0x7436,
        "Bank 31 $7434-$7436 3-byte table",
        note="Indexed by the SeedMul result (ld hl,$7434 at $7411); "
             "value -> [$c10d]."))
    parts.append(emit_db(
        rom, 31, 0x74D5, 0x74D7,
        "Bank 31 $74d5-$74d7 3-byte table",
        note="Indexed by the SeedMul result (ld hl,$74d5 at $748e); "
             "value -> [$c10d]."))
    parts.append(emit_db(
        rom, 31, 0x775F, 0x7774,
        "Bank 31 $775f-$7774 11x2-byte pairs",
        note="Indexed by 2*(record byte) (ld hl,$775f at $7752); first "
             "byte -> [$c10a], second -> [$c10c]. $7765 is also a 16B "
             "memcpy source to $dd59 (ld hl,$7765 at $772d)."))
    parts.append(emit_db(
        rom, 31, 0x792E, 0x7933,
        "Bank 31 $792e-$7933 two 3-byte tables",
        note="ld hl,$792e or $7931 at $78f8/$7904 (choice by [$c0f8] "
             "bit 0); indexed by [$c10f], value -> [$c10d]."))
    parts.append(carve(
        rom, 31, 0x7DB9, 0x7DE3,
        "Bank 31 $7db9-$7de3 shared routines",
        [0x7DB9, 0x7DCC],
        B31_LABELS([0x7DB9, 0x7DCC])))
    parts.append(carve(
        rom, 31, 0x7E44, 0x7E7D,
        "Bank 31 $7e44-$7e7d shared routines",
        [0x7E44, 0x7E61],
        B31_LABELS([0x7E44, 0x7E61])))
    parts.append(
        "; Slice 20: Bank 31 $7f5f 1-byte ret + $7f60 00/01 table.\n"
        "; $7f5f entry unverified -- it could equally be the first\n"
        "; byte of the table. The table is indexed by [$dd18]\n"
        "; (ld hl,$7f60 at $4729/$476c/$5621/$54c8); values are 0/1.\n"
        "; Generated by tools/generators/gen_slice20.py.\n"
        'SECTION "Bank 31 $7f5f ret", ROMX[$7f5f], BANK[31]\n'
        "Bank31_7F5F::\n"
        "    ret                                              ; $7f5f\n")
    parts.append(emit_db(
        rom, 31, 0x7F60, 0x7FFF,
        "Bank 31 $7f60-$7fff 00/01 table (160 bytes)",
        note="Indexed by [$dd18]; values are 0/1 throughout."))
    with open("src/banks/bank31slice20.asm", "w") as f:
        f.write("\n".join(parts))
    print("wrote src/banks/bank31slice20.asm (26 gaps)")


# ------------------------------------------------------------------
# Bank 10 (decimal) -- all 34 gaps.
# ------------------------------------------------------------------

B10_LABELS = lambda addrs: {(10, a): f"Bank0A_{a:04X}" for a in addrs}

# dw tables: (base, entries)
B10_TABLES = {
    0x480A: [0x482A, 0x4977, 0x4A16, 0x4AC6, 0x4B3B, 0x4BB6, 0x4C49,
             0x7815, 0x4C4E, 0x4C73, 0x4D00, 0x4D11, 0x4D17, 0x7815,
             0x6367, 0x4D41],
    0x4E56: [0x4E66, 0x4EAA, 0x4ED6, 0x4EF8, 0x4F19, 0x50A7, 0x50C9,
             0x5191],
    0x51A1: [0x51A5, 0x51D9],
    0x524B: [0x5255, 0x5283, 0x52A6, 0x52BF, 0x6581],
    0x534B: [0x535B, 0x536F, 0x538B, 0x53A4],
    0x5421: [0x542B, 0x54D7, 0x5543, 0x5644, 0x5673],
    0x56B1: [0x56C1, 0x5D48, 0x5D86, 0x5D9F],
    0x56FB: [0x5701, 0x5734, 0x57BA],
    0x5894: [0x7815, 0x589C, 0x717A, 0x7297],
    0x5918: [0x5924, 0x5944, 0x5A7C, 0x5ABF, 0x5B39, 0x5C27],
    0x5ECA: [0x5EE8, 0x5F3E, 0x5FCB, 0x7815, 0x6044, 0x60C0, 0x617B,
             0x7815, 0x619C, 0x61BD, 0x6208, 0x7815, 0x7815, 0x628C,
             0x6367],
    0x6414: [0x6420, 0x6453, 0x6479, 0x649A, 0x64D0, 0x6581],
    0x65A2: [0x65B0, 0x6601, 0x6630, 0x6655, 0x66C3, 0x6716, 0x678B],
    0x67AC: [0x67BA, 0x67EF, 0x6825, 0x684A, 0x68A7, 0x6900, 0x69BD],
    0x69DE: [0x69EC, 0x69FC, 0x6A26, 0x6A38, 0x6A7B, 0x6A90, 0x678B],
    0x6B08: [0x6B16, 0x6B71, 0x6BBC, 0x6C15, 0x6C6A, 0x6C99, 0x6D6F],
    0x6D9A: [0x6DA8, 0x7815, 0x7815, 0x6DEC, 0x7815, 0x6C99, 0x6E3A],
    0x6E62: [0x6E70, 0x6601, 0x6630, 0x6E95, 0x6EDB, 0x6F0C, 0x678B],
    0x6F66: [0x6F86, 0x7043, 0x7059, 0x7815, 0x4B3B, 0x4BB6, 0x4C49,
             0x7815, 0x4C4E, 0x6F86, 0x4D00, 0x4D11, 0x4D17, 0x7815,
             0x6367, 0x4D41],
}


def emit_bank10(rom):
    parts = []
    # --- $480a table + routines ---
    parts.append(emit_dw_table(
        rom, 10, 0x480A,
        [(0x480A + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x480A])],
        "Bank 10 $480a dw table (16 entries)",
        expected=B10_TABLES[0x480A],
        note="Read at $4802 (ld hl,$480a; jp hl). Entries $7815 (ret) "
             "and $6367 (in the $612e carve) are shared routines."))
    parts.append(carve(
        rom, 10, 0x482A, 0x4ADC,
        "Bank 10 $482a-$4adc $480a-table routines (part 1)",
        B10_TABLES[0x480A],
        B10_LABELS([0x482A, 0x4977, 0x4A16, 0x4AC6, 0x4B3B, 0x4BB6,
                    0x4C49, 0x4C4E, 0x4C73])))
    parts.append(carve(
        rom, 10, 0x4AE3, 0x4B3A,
        "Bank 10 $4ae3-$4b3a routine",
        [0x4AE3],
        B10_LABELS([0x4AE3])))
    parts.append(carve(
        rom, 10, 0x4B3B, 0x4D57,
        "Bank 10 $4b3b-$4d57 $480a-table routines (part 2)",
        B10_TABLES[0x480A],
        B10_LABELS([0x4B3B, 0x4BB6, 0x4C49, 0x4C4E, 0x4C73, 0x4D00,
                    0x4D11, 0x4D17, 0x4D41])))
    parts.append(carve(
        rom, 10, 0x4D5E, 0x4DB6,
        "Bank 10 $4d5e-$4db6 routine",
        [0x4D5E],
        B10_LABELS([0x4D5E])))
    parts.append(carve(
        rom, 10, 0x4DB7, 0x4DBD,
        "Bank 10 $4db7-$4dbd shared tail (call $7a8a)",
        [0x4DB7],
        B10_LABELS([0x4DB7])))
    # --- $4e56 table + routines ---
    parts.append(emit_dw_table(
        rom, 10, 0x4E56,
        [(0x4E56 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x4E56])],
        "Bank 10 $4e56 dw table (8 entries)",
        expected=B10_TABLES[0x4E56],
        note="Read at $4e4e (ld hl,$4e56; jp hl). Entries $50a7/$50c9/"
             "$5191 live in the $5085 carve below."))
    parts.append(carve(
        rom, 10, 0x4E66, 0x4FF1,
        "Bank 10 $4e66-$4ff1 $4e56-table routines",
        B10_TABLES[0x4E56],
        B10_LABELS([0x4E66, 0x4EAA, 0x4ED6, 0x4EF8, 0x4F19])))
    parts.append(carve(
        rom, 10, 0x4FFF, 0x5020,
        "Bank 10 $4fff-$5020 routine",
        [0x4FFF],
        B10_LABELS([0x4FFF, 0x503B])))
    # --- $5085 data + routines ---
    parts.append(emit_db(
        rom, 10, 0x5085, 0x5096,
        "Bank 10 $5085-$5096 data (4/6/8-byte groups)",
        note="Copied to $dd81 (ld hl,$5085/$5089/$508f at $5053/$505e/"
             "$5069; B=4/6/8 by [$c705] bit 0 and [$c10e])."))
    parts.append(emit_db(
        rom, 10, 0x5097, 0x50A6,
        "Bank 10 $5097-$50a6 16-byte data",
        note="Mempcy'd to $dd59 (ld hl,$5097; ld c,$10; call $106e at "
             "$5040)."))
    parts.append(carve(
        rom, 10, 0x50A7, 0x50C8,
        "Bank 10 $50a7-$50c8 $4e56-table entry-5 routine",
        [0x50A7],
        B10_LABELS([0x50A7])))
    parts.append(carve(
        rom, 10, 0x50C9, 0x5166,
        "Bank 10 $50c9-$5166 $4e56-table entry-6 routine",
        [0x50C9],
        B10_LABELS([0x50C9])))
    parts.append(emit_db(
        rom, 10, 0x5167, 0x5190,
        "Bank 10 $5167-$5190 3x14-byte records",
        note="Same 14-byte record shape as the other tables in this "
             "bank; no ld hl reference found in carved code."))
    parts.append(carve(
        rom, 10, 0x5191, 0x5191,
        "Bank 10 $5191 ret ($4e56-table entry 7)",
        [0x5191],
        B10_LABELS([0x5191])))
    # --- $51a1 table + routines ---
    parts.append(emit_dw_table(
        rom, 10, 0x51A1,
        [(0x51A1 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x51A1])],
        "Bank 10 $51a1 dw table (2 entries, $2b48-entry-11)",
        expected=B10_TABLES[0x51A1],
        note="Read at $5199 (ld hl,$51a1; jp hl)."))
    parts.append(carve(
        rom, 10, 0x51A5, 0x51DF,
        "Bank 10 $51a5-$51df $51a1-table routines",
        B10_TABLES[0x51A1],
        B10_LABELS([0x51A5, 0x51D9])))
    parts.append(carve(
        rom, 10, 0x5212, 0x522A,
        "Bank 10 $5212-$522a routine",
        [0x5212],
        B10_LABELS([0x5212])))
    # --- $524b table + routines + data ---
    parts.append(emit_dw_table(
        rom, 10, 0x524B,
        [(0x524B + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x524B])],
        "Bank 10 $524b dw table (5 entries, $2b48-entry-13)",
        expected=B10_TABLES[0x524B],
        note="Read at $5243 (ld hl,$524b; jp hl). Entry $6581 is the "
             "1-byte ret in the $6414 carve."))
    parts.append(carve(
        rom, 10, 0x5255, 0x531A,
        "Bank 10 $5255-$531a $524b-table routines",
        B10_TABLES[0x524B],
        B10_LABELS([0x5255, 0x5283, 0x52A6, 0x52BF])))
    parts.append(emit_db(
        rom, 10, 0x531B, 0x532A,
        "Bank 10 $531b-$532a 16-byte data",
        note="ld hl,$531b at $52cc."))
    # --- $534b table + routines + data ---
    parts.append(emit_dw_table(
        rom, 10, 0x534B,
        [(0x534B + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x534B])],
        "Bank 10 $534b dw table (4 entries, $2b48-entry-14)",
        expected=B10_TABLES[0x534B],
        note="Read at $5343 (ld hl,$534b; jp hl)."))
    parts.append(emit_db(
        rom, 10, 0x5353, 0x535A,
        "Bank 10 $5353-$535a 8-byte data",
        note="Caught by the byte-match check: sits between the $534b "
             "table and the $535b routine. 00 00 00 00 88 5e 97 5e; no "
             "ld hl/call/jp reference found in carved code."))
    parts.append(carve(
        rom, 10, 0x535B, 0x537B,
        "Bank 10 $535b-$537b $534b-table routines (part 1)",
        B10_TABLES[0x534B],
        B10_LABELS([0x535B, 0x536F])))
    parts.append(emit_db(
        rom, 10, 0x537C, 0x538A,
        "Bank 10 $537c-$538a 15-byte data",
        note="ld de,$537c at $5374 (inside the $536f routine)."))
    parts.append(carve(
        rom, 10, 0x538B, 0x53D5,
        "Bank 10 $538b-$53d5 $534b-table routines (part 2)",
        B10_TABLES[0x534B],
        B10_LABELS([0x538B, 0x53A4])))
    parts.append(emit_db(
        rom, 10, 0x53D6, 0x5411,
        "Bank 10 $53d6-$5411 60-byte data",
        note="ld hl,$53d6 at $53a9 (inside the $538b routine)."))
    # --- $5421 table + routines ---
    parts.append(emit_dw_table(
        rom, 10, 0x5421,
        [(0x5421 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x5421])],
        "Bank 10 $5421 dw table (5 entries, $2b48-entry-16)",
        expected=B10_TABLES[0x5421],
        note="Read at $5419 (ld hl,$5421; jp hl)."))
    parts.append(carve(
        rom, 10, 0x542B, 0x568B,
        "Bank 10 $542b-$568b $5421-table routines",
        B10_TABLES[0x5421],
        B10_LABELS([0x542B, 0x54D7, 0x5543, 0x5644, 0x5673])))
    # --- $56b1 table + routine ---
    parts.append(emit_dw_table(
        rom, 10, 0x56B1,
        [(0x56B1 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x56B1])],
        "Bank 10 $56b1 dw table (4 entries, $2b48-entry-17)",
        expected=B10_TABLES[0x56B1],
        note="Read at $56a9 (ld hl,$56b1; jp hl). Entries 1-3 "
             "($5d48/$5d86/$5d9f) are already carved (slice 16)."))
    parts.append(emit_db(
        rom, 10, 0x56B9, 0x56C0,
        "Bank 10 $56b9-$56c0 8-byte data",
        note="Caught by the byte-match check: sits between the $56b1 "
             "table and the $56c1 routine. 00 00 00 00 88 5e 97 5e "
             "(identical bytes to $5353-$535a); no ld hl/call/jp "
             "reference found in carved code."))
    parts.append(carve(
        rom, 10, 0x56C1, 0x56DA,
        "Bank 10 $56c1-$56da $56b1-table entry-0 routine",
        [0x56C1],
        B10_LABELS([0x56C1])))
    # --- $56fb table + routines + data ---
    parts.append(emit_dw_table(
        rom, 10, 0x56FB,
        [(0x56FB + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x56FB])],
        "Bank 10 $56fb dw table (3 entries, $2b48-entry-31)",
        expected=B10_TABLES[0x56FB],
        note="Read at $56f3 (ld hl,$56fb; jp hl)."))
    parts.append(carve(
        rom, 10, 0x5701, 0x57AB,
        "Bank 10 $5701-$57ab $56fb-table routines",
        B10_TABLES[0x56FB],
        B10_LABELS([0x5701, 0x5734])))
    parts.append(emit_db(
        rom, 10, 0x57AC, 0x57B9,
        "Bank 10 $57ac-$57b9 14-byte record",
        note="ld hl,$57ac in the $5701 walk (see generator notes)."))
    parts.append(carve(
        rom, 10, 0x57BA, 0x57BA,
        "Bank 10 $57ba ret ($56fb-table entry 2)",
        [0x57BA],
        B10_LABELS([0x57BA])))
    # --- $5894 table + routine ---
    parts.append(emit_dw_table(
        rom, 10, 0x5894,
        [(0x5894 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x5894])],
        "Bank 10 $5894 dw table (4 entries)",
        expected=B10_TABLES[0x5894],
        note="Read at $588c (ld hl,$5894; jp hl) by the $57bb handler. "
             "Entries $717a/$7297 are carved routines in $7073-$7599."))
    parts.append(carve(
        rom, 10, 0x589C, 0x5908,
        "Bank 10 $589c-$5908 $5894-table entry-1 routine",
        [0x589C],
        B10_LABELS([0x589C])))
    # --- $5918 table + routines ---
    parts.append(emit_dw_table(
        rom, 10, 0x5918,
        [(0x5918 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x5918])],
        "Bank 10 $5918 dw table (6 entries)",
        expected=B10_TABLES[0x5918],
        note="Read at $5910 (ld hl,$5918; jp hl)."))
    parts.append(carve(
        rom, 10, 0x5924, 0x5C4E,
        "Bank 10 $5924-$5c4e $5918-table routines",
        B10_TABLES[0x5918],
        B10_LABELS([0x5924, 0x5944, 0x5A7C, 0x5ABF, 0x5B39, 0x5C27])))
    # --- $5d5e / $5e0a data ---
    parts.append(emit_db(
        rom, 10, 0x5D5E, 0x5D85,
        "Bank 10 $5d5e-$5d85 40-byte data",
        note="ld de,$5d5e or $5d6d at $5d4d/$5d56 (choice by [$c110]); "
             "jp $7951 with A=$07."))
    parts.append(emit_db(
        rom, 10, 0x5E0A, 0x5E87,
        "Bank 10 $5e0a-$5e87 data (126 bytes)",
        note="$5e0a/$5e1c are 18-byte records passed to $799d (ld "
             "hl,$5e0a/$5e1c at $5da4/$5dad; call $799d at $5db0); "
             "$5e2e-$5e73 are five 14-byte records; $5e80/$5e83 are "
             "byte tables indexed by [$c10b] (ld hl,$5e80/$5e83 at "
             "$5db4/$5dbd)."))
    # --- $5eca table + routines ---
    parts.append(emit_dw_table(
        rom, 10, 0x5ECA,
        [(0x5ECA + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x5ECA])],
        "Bank 10 $5eca dw table (15 entries)",
        expected=B10_TABLES[0x5ECA],
        note="Read at $5ec2 (ld hl,$5eca; jp hl). Entries $617b/$619c/"
             "$61bd/$6208/$628c/$6367 live in the $612e carve."))
    parts.append(carve(
        rom, 10, 0x5EE8, 0x60F2,
        "Bank 10 $5ee8-$60f2 $5eca-table routines (part 1)",
        B10_TABLES[0x5ECA],
        B10_LABELS([0x5EE8, 0x5F3E, 0x5FCB, 0x6044, 0x60C0])))
    # --- $612e big routine ---
    parts.append(carve(
        rom, 10, 0x612E, 0x63A2,
        "Bank 10 $612e-$63a2 routines ($5eca/$480a/$6f66-table entries)",
        [0x612E, 0x617B, 0x619C, 0x61BD, 0x6208, 0x628C, 0x6367],
        B10_LABELS([0x612E, 0x617B, 0x619C, 0x61BD, 0x6208, 0x628C,
                    0x6367])))
    emit_bank10_rest(rom, parts)
    with open("src/banks/bank10slice20.asm", "w") as f:
        f.write("\n".join(parts))
    print("wrote src/banks/bank10slice20.asm")


def emit_bank10_rest(rom, parts):
    # --- $6414 table + routines + ret ---
    parts.append(emit_dw_table(
        rom, 10, 0x6414,
        [(0x6414 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x6414])],
        "Bank 10 $6414 dw table (6 entries)",
        expected=B10_TABLES[0x6414],
        note="Read at $640c (ld hl,$6414; jp hl). Entry $6581 is the "
             "1-byte ret below."))
    parts.append(carve(
        rom, 10, 0x6420, 0x6580,
        "Bank 10 $6420-$6580 $6414-table routines",
        B10_TABLES[0x6414],
        B10_LABELS([0x6420, 0x6453, 0x6479, 0x649A, 0x64D0])))
    parts.append(carve(
        rom, 10, 0x6581, 0x6581,
        "Bank 10 $6581 ret ($6414-table entry 5)",
        [0x6581],
        B10_LABELS([0x6581])))
    # --- $65a2 table + routines + data ---
    parts.append(emit_dw_table(
        rom, 10, 0x65A2,
        [(0x65A2 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x65A2])],
        "Bank 10 $65a2 dw table (7 entries)",
        expected=B10_TABLES[0x65A2],
        note="Read at $659a (ld hl,$65a2; jp hl). Entry $678b is the "
             "1-byte ret below."))
    parts.append(carve(
        rom, 10, 0x65B0, 0x66B4,
        "Bank 10 $65b0-$66b4 $65a2-table routines (part 1)",
        B10_TABLES[0x65A2],
        B10_LABELS([0x65B0, 0x6601, 0x6630, 0x6655])))
    parts.append(emit_db(
        rom, 10, 0x66B5, 0x66C2,
        "Bank 10 $66b5-$66c2 14-byte record",
        note="ld hl,$66b5 at $666c."))
    parts.append(carve(
        rom, 10, 0x66C3, 0x6707,
        "Bank 10 $66c3-$6707 $65a2-table entry-4 routine",
        [0x66C3],
        B10_LABELS([0x66C3])))
    parts.append(emit_db(
        rom, 10, 0x6708, 0x6715,
        "Bank 10 $6708-$6715 14-byte record",
        note="ld hl,$6708 at $66d1."))
    parts.append(carve(
        rom, 10, 0x6716, 0x677C,
        "Bank 10 $6716-$677c $65a2-table entry-5 routine",
        [0x6716],
        B10_LABELS([0x6716])))
    parts.append(emit_db(
        rom, 10, 0x677D, 0x678A,
        "Bank 10 $677d-$678a 14-byte record",
        note="ld hl,$677d at $6724."))
    parts.append(carve(
        rom, 10, 0x678B, 0x678B,
        "Bank 10 $678b ret ($65a2-table entry 6)",
        [0x678B],
        B10_LABELS([0x678B])))
    # --- $67ac table + routines ---
    parts.append(emit_dw_table(
        rom, 10, 0x67AC,
        [(0x67AC + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x67AC])],
        "Bank 10 $67ac dw table (7 entries)",
        expected=B10_TABLES[0x67AC],
        note="Read at $67a4 (ld hl,$67ac; jp hl)."))
    parts.append(carve(
        rom, 10, 0x67BA, 0x69BD,
        "Bank 10 $67ba-$69bd $67ac-table routines",
        B10_TABLES[0x67AC],
        B10_LABELS([0x67BA, 0x67EF, 0x6825, 0x684A, 0x68A7, 0x6900,
                    0x69BD])))
    # --- $69de table + routines + data ---
    parts.append(emit_dw_table(
        rom, 10, 0x69DE,
        [(0x69DE + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x69DE])],
        "Bank 10 $69de dw table (7 entries)",
        expected=B10_TABLES[0x69DE],
        note="Read at $69d6 (ld hl,$69de; jp hl). Entry $678b is the "
             "1-byte ret carved above."))
    parts.append(carve(
        rom, 10, 0x69EC, 0x6A6C,
        "Bank 10 $69ec-$6a6c $69de-table routines (part 1)",
        B10_TABLES[0x69DE],
        B10_LABELS([0x69EC, 0x69FC, 0x6A26, 0x6A38])))
    parts.append(emit_db(
        rom, 10, 0x6A6D, 0x6A7A,
        "Bank 10 $6a6d-$6a7a 14-byte record",
        note="ld hl,$6a6d at $6a6d's walk callers ($69ec walk: $6a6d "
             "loaded at three sites)."))
    parts.append(carve(
        rom, 10, 0x6A7B, 0x6AF8,
        "Bank 10 $6a7b-$6af8 $69de-table routines (part 2)",
        B10_TABLES[0x69DE],
        B10_LABELS([0x6A7B, 0x6A90])))
    # --- $6b08 table + routines + data ---
    parts.append(emit_dw_table(
        rom, 10, 0x6B08,
        [(0x6B08 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x6B08])],
        "Bank 10 $6b08 dw table (7 entries)",
        expected=B10_TABLES[0x6B08],
        note="Read at $6b00 (ld hl,$6b08; jp hl)."))
    parts.append(carve(
        rom, 10, 0x6B16, 0x6B62,
        "Bank 10 $6b16-$6b62 $6b08-table entry-0 routine",
        [0x6B16],
        B10_LABELS([0x6B16])))
    parts.append(emit_db(
        rom, 10, 0x6B63, 0x6B70,
        "Bank 10 $6b63-$6b70 14-byte record",
        note="ld hl,$6b63 at $6b71-walk site."))
    parts.append(carve(
        rom, 10, 0x6B71, 0x6D62,
        "Bank 10 $6b71-$6d62 $6b08-table routines (part 2)",
        B10_TABLES[0x6B08],
        B10_LABELS([0x6B71, 0x6BBC, 0x6C15, 0x6C6A, 0x6C99])))
    parts.append(emit_db(
        rom, 10, 0x6D63, 0x6D6E,
        "Bank 10 $6d63-$6d6e 12-byte data",
        note="ld hl,$6d63 at $6cf5."))
    parts.append(carve(
        rom, 10, 0x6D6F, 0x6D76,
        "Bank 10 $6d6f-$6d76 $6b08-table entry-6 routine",
        [0x6D6F],
        B10_LABELS([0x6D6F])))
    # --- $6d9a table + routines ---
    parts.append(emit_dw_table(
        rom, 10, 0x6D9A,
        [(0x6D9A + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x6D9A])],
        "Bank 10 $6d9a dw table (7 entries)",
        expected=B10_TABLES[0x6D9A],
        note="Read at $6d92 (ld hl,$6d9a; jp hl). Entry $6c99 is a "
             "$6b08-table routine carved above."))
    parts.append(carve(
        rom, 10, 0x6DA8, 0x6E41,
        "Bank 10 $6da8-$6e41 $6d9a-table routines",
        B10_TABLES[0x6D9A],
        B10_LABELS([0x6DA8, 0x6DEC, 0x6E3A])))
    # --- $6e62 table + routines + data ---
    parts.append(emit_dw_table(
        rom, 10, 0x6E62,
        [(0x6E62 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x6E62])],
        "Bank 10 $6e62 dw table (7 entries)",
        expected=B10_TABLES[0x6E62],
        note="Read at $6e5a (ld hl,$6e62; jp hl). Entries $6601/$6630/"
             "$678b are $65a2-table routines carved above."))
    parts.append(carve(
        rom, 10, 0x6E70, 0x6ECC,
        "Bank 10 $6e70-$6ecc $6e62-table entry-0/3 routines",
        [0x6E70, 0x6E95],
        B10_LABELS([0x6E70, 0x6E95])))
    parts.append(emit_db(
        rom, 10, 0x6ECD, 0x6EDA,
        "Bank 10 $6ecd-$6eda 14-byte record",
        note="ld hl,$6ecd at $6eac."))
    parts.append(carve(
        rom, 10, 0x6EDB, 0x6EFD,
        "Bank 10 $6edb-$6efd $6e62-table entry-4 routine",
        [0x6EDB],
        B10_LABELS([0x6EDB])))
    parts.append(emit_db(
        rom, 10, 0x6EFE, 0x6F0B,
        "Bank 10 $6efe-$6f0b 14-byte record",
        note="ld hl,$6efe at $6ee9."))
    parts.append(carve(
        rom, 10, 0x6F0C, 0x6F2E,
        "Bank 10 $6f0c-$6f2e $6e62-table entry-5 routine",
        [0x6F0C],
        B10_LABELS([0x6F0C])))
    parts.append(emit_db(
        rom, 10, 0x6F2F, 0x6F3C,
        "Bank 10 $6f2f-$6f3c 14-byte record",
        note="ld hl,$6f2f at $6f1a."))
    # --- $6f66 table + routines + data ---
    parts.append(emit_dw_table(
        rom, 10, 0x6F66,
        [(0x6F66 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(B10_TABLES[0x6F66])],
        "Bank 10 $6f66 dw table (16 entries)",
        expected=B10_TABLES[0x6F66],
        note="Read at $6f5e (ld hl,$6f66; jp hl). Shares most entries "
             "with the $480a table ($4b3b/$4bb6/$4c49/$4c4e/$4d00/$4d11/"
             "$4d17/$6367/$4d41); only entries 0-3 ($6f86/$7043/$7059/"
             "$7815) and entry 9 ($6f86) are new here."))
    parts.append(carve(
        rom, 10, 0x6F86, 0x703C,
        "Bank 10 $6f86-$703c $6f66-table entry-0 routine",
        [0x6F86],
        B10_LABELS([0x6F86])))
    parts.append(emit_db(
        rom, 10, 0x703D, 0x7042,
        "Bank 10 $703d-$7042 6-byte data (3x 00 80)",
        note="No ld hl/call/jp reference found in carved code; plain "
             "db."))
    parts.append(carve(
        rom, 10, 0x7043, 0x705E,
        "Bank 10 $7043-$705e $6f66-table entry-1/2 routines",
        [0x7043, 0x7059],
        B10_LABELS([0x7043, 0x7059])))
    # --- $75b0-$772f record routines ---
    parts.append(carve(
        rom, 10, 0x75B0, 0x772F,
        "Bank 10 $75b0-$772f record routines",
        [0x75B0, 0x75C2, 0x75F7, 0x7706, 0x76EF, 0x763A, 0x763F,
         0x7645, 0x764B, 0x7675, 0x7651, 0x769A, 0x76B3, 0x76DE],
        B10_LABELS([0x75B0, 0x75C2, 0x75F7, 0x7706, 0x76EF, 0x763A,
                    0x763F, 0x7645, 0x764B, 0x7675, 0x7651, 0x769A,
                    0x76B3, 0x76DE])))
    # --- $789f-$7951 routine ---
    parts.append(carve(
        rom, 10, 0x789F, 0x7950,
        "Bank 10 $789f-$7950 routine (fall-through from $787d)",
        [0x789F],
        B10_LABELS([0x789F])))
    # --- $79ea-$7ab8 routines + data ---
    parts.append(carve(
        rom, 10, 0x79EA, 0x7AA9,
        "Bank 10 $79ea-$7aa9 routines",
        [0x79EA, 0x7A20, 0x7A8A],
        B10_LABELS([0x79EA, 0x7A20, 0x7A8A])))
    parts.append(emit_db(
        rom, 10, 0x7AAA, 0x7AB7,
        "Bank 10 $7aaa-$7ab7 14-byte record",
        note="Same repeating record shape as the $67f8-region records "
             "in bank 31; no ld hl reference found in carved code."))
    # --- $7b12 routine ---
    parts.append(carve(
        rom, 10, 0x7B12, 0x7B3E,
        "Bank 10 $7b12-$7b3e routine",
        [0x7B12],
        B10_LABELS([0x7B12])))
    # --- $7b6c routines ---
    parts.append(carve(
        rom, 10, 0x7B6C, 0x7C23,
        "Bank 10 $7b6c-$7c23 routines",
        [0x7B6C, 0x7BDF, 0x7BFC],
        B10_LABELS([0x7B6C, 0x7BDF, 0x7BFC])))
    # --- $7cb0 routine + tables ---
    parts.append(carve(
        rom, 10, 0x7CB0, 0x7D0D,
        "Bank 10 $7cb0-$7d0d routine (reads $7d0e/$7d16 tables)",
        [0x7CB0],
        B10_LABELS([0x7CB0])))
    parts.append(emit_dw_table(
        rom, 10, 0x7D0E,
        [(0x7D0E + 2 * i, f"([$c814]&3)={i} -> ${v:04x}")
         for i, v in enumerate([0x7BDF, 0x7C57, 0x7C24, 0x7BFC])],
        "Bank 10 $7d0e dw table (4 entries)",
        expected=[0x7BDF, 0x7C57, 0x7C24, 0x7BFC],
        note="Read by the $7cb0 routine (ld hl,$7d0e at $7d05; jp hl; "
             "index 2*([$c814]&3))."))
    parts.append(emit_db(
        rom, 10, 0x7D16, 0x7E3B,
        "Bank 10 $7d16-$7e3b 72x4-byte records",
        note="Scanned by the $7cb0 routine (ld hl,$7d16 at $7ccb; "
             "stride 4; match record[0] against [$c80d]); record[1..3] "
             "are consumed at $7cd8-$7ce7."))
    parts.append(emit_dw_table(
        rom, 10, 0x7E3C,
        [(0x7E3C + 2 * i, f"entry {i} -> ${v:04x}")
         for i, v in enumerate([0x7815, 0x763A, 0x763F, 0x7645, 0x764B,
                                0x7675, 0x7651, 0x769A, 0x76B3, 0x76DE])],
        "Bank 10 $7e3c dw table (10 entries)",
        expected=[0x7815, 0x763A, 0x763F, 0x7645, 0x764B, 0x7675,
                  0x7651, 0x769A, 0x76B3, 0x76DE],
        note="Entries are the $763a-$76ee routines (carved in the "
             "$75b0 section); the $763a/$763f/$7645/$764b routines set "
             "[$c10a] to 0/1/4/7, i.e. indices into this table. The "
             "table's own reader was not found in carved code."))
    # --- $7f44 tail: padding + offset table + byte table ---
    parts.append(emit_db(
        rom, 10, 0x7F44, 0x7FB5,
        "Bank 10 $7f44-$7fb5 data (mostly $00 padding)",
        note="Mostly $00 with scattered bytes ($02 $02 at $7f7a, dw "
             "$76ef/$7706 at $7f9e/$7fa2); no code entry found."))
    parts.append(emit_dw_table(
        rom, 10, 0x7FB6,
        [(0x7FB6 + 2 * i, f"entry {i} -> ${v:04x}")
         for i, v in enumerate([0x0000, 0xFFFC, 0xFF80, 0xFF7C, 0x7FC6,
                                0x7FCC, 0x7FD2, 0x7FDA])],
        "Bank 10 $7fb6 dw table (8 signed offsets)",
        expected=[0x0000, 0xFFFC, 0xFF80, 0xFF7C, 0x7FC6, 0x7FCC,
                  0x7FD2, 0x7FDA],
        note="Read at $4e0b (ld hl,$7fb6; add hl,bc); the entry is "
             "added as a signed 16-bit offset to DE."))
    parts.append(emit_db(
        rom, 10, 0x7FC6, 0x7FE3,
        "Bank 10 $7fc6-$7fe3 30-byte data",
        note="Byte table (values $48/$68/$88/$90/$98/$b8/$d8/$e8 and "
             "small ints); readers unidentified."))
    parts.append(emit_db(
        rom, 10, 0x7FE4, 0x7FFF,
        "Bank 10 $7fe4-$7fff tail data",
        note="10 bytes ($17 $02 $07 $04 $1d $03 $08 $05 $23 $04), then "
             "$ff padding to $7ffb, then dw $43a3/$43a7 at $7ffc (no "
             "reader identified)."))


def main():
    rom = open(ROM, "rb").read()
    emit_bank31(rom)
    emit_bank10(rom)


if __name__ == "__main__":
    main()
