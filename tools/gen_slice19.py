#!/usr/bin/env python3
"""Slice-19 generator: bank-29 sprite table + blocks, the $7378
routine's entry (bank 10 $7073 table), and the bank-31 $70df-$723d
remainder (plus the $6a98-table entry-9 routine it belongs with).

Bank 29 -- the second $112c sprite-pointer table. The selector is
STATIC, per call site, and is now pinned, not inferred:
  * $10d5 (bank 0) selects bank $1d (29) then jumps into the
    $10e3 iterator loop body, skipping the bank-$0b select at
    $10e0. It is the ONLY `ld a,$1d; rst $10` in the whole ROM
    (whole-ROM pattern scan: exactly 1 hit, at bank-0 $10d8).
  * $10dd (bank 0) selects bank $0b (11) at $10e0, then runs the
    same $10e3 loop. Its callers are everywhere (bank 1, state 20
    $285a, ...); $10d5's callers are ONLY state-16 transition steps
    (bank-0 $09d2, $0ab2, $0ae1, $0b12, $0b95, $0bde) plus state-20
    step 0 ($2907). So: state-16 transition rendering uses bank 29's
    sprite set; everything else uses bank 11's.
  * Bank 29's table: 256 dw at $4000, 121 distinct targets in
    $4200-$7d02, partitioning the range exactly (consecutive-target
    gaps sum to the span); last block $7d02 runs to $7e94 (bank 29's
    last non-$ff byte is at $7e93; $7e94-$7fff is $ff padding, stays
    INCBIN). Its $4200 default block is byte-identical to bank 11's.
    Same emitter shape as gen_slice18's bank-11 blocks.

Bank 10 $7378 -- ENTRY MECHANISM RESOLVED. $7378 is not a routine
head at all: the head is $7369 (`dec [$c10c]; ret nz; res 3,[$c103];
ld a,[$c104]; and $7f; ld [$c105],a`, then the $7dde/$7e3c dw
dispatch ending `jp hl`). $7369 is [$c10a]=4 of the 7-entry dw table
at $7073 ($7081, $7815, $70a6, $7297, $7369, $738f, $7400), read by
the $2b48-entry-63 handler $705f (carved slice 16: `ld a,[$c10a];
add a; ld hl,$7073; ...; jp hl`, gated on [$ff93] bit 5 clear).
So $7378 runs whenever a $c200 record with [$c105]=63 is dispatched
-- the same jp-hl-table entry pattern as bank 31's $6a98 table.
The whole $7073-$7599 span is carved here: table + entry routines
$7081/$70a6/$7297/$7369/$738f/$7400 (entry 1 $7815 was already
carved, a 1-byte ret), with data blobs $7290-$7296 (7 bytes, indexed
by [$c705]) and $74aa-$74b9 (16 bytes, two 8-byte records loaded via
DE by the $748f/$74ba routines). Note $7300 is NOT a routine head:
it is the $07 immediate byte of `cp $07` at $72ff (slice 18's
"~$7300" was approximate; the real head is $7297, table entry 3).

Bank 31 $70df-$723d -- ENTRY MECHANISM RESOLVED, same pattern.
Slice 17 truncated the $6a98 [$c10a] table at 9 entries ($6a98-$6aa9);
it is actually 19 entries ($6a98-$6abd): entries 9-18 are $6ed6,
$6ffa, $704b, $708f, $70d0, $70df, $7161, $71bd, $7222, $722c --
all increasing, all decoded instruction starts (slice 19 verifies).
Entries 10-13 ($6ffa/$704b/$708f/$70d0) were carved in slice 18
without noting they are table entries; entries 14-18 are carved
here ($70df-$7144 code, $7161-$7211 code, $7222-$722b and $722c-$723d
countdown tails), plus entry 9 ($6ed6-$6f88, which shares the $6e22
tail with entry 7) and the memcpy data blobs $6eba-$6ed5 (28 bytes,
`ld hl,$6eba` at $6e9a), $7145-$7160 (28 bytes, `ld hl,$7145` at
$70e9) and $7212-$7221 (16 bytes, "bodyfkhmncpejgkli", 4x4 table
indexed by [$c113]&3 at $71f2). gen_slice17.py's TABLES31 entry 91
is extended 9 -> 19 in this slice; re-running it regenerates the
$6a98 dw block (verify with git diff that ONLY that block changes).
The $79b5 `c2 09 72` byte triple is NOT a `jp nz,$7209`: it is the
tail of `ld bc,$c213` ($79b3) + `add hl,bc` ($79b6) in carved code.

Regenerate with: python3 tools/gen_slice19.py
Outputs: src/bank29.asm, src/bank29slice19.asm,
src/bank10slice19.asm, src/bank31slice19.asm. Also update
tools/gen_banks.py CARVED (bank 29, bank 10 $7073-$7599, bank 31
$6a98-$6abe + $6eba-$6f89 + $70df-$723e) and regenerate
src/banks.asm; add the three INCLUDEs to src/main.asm.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def file_off(bank, addr):
    return bank * 0x4000 + (addr - 0x4000)


# ------------------------------------------------------------------
# Shared emit helpers (gen_slice17/18 pattern).
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


def emit_carve(rom, bank, lo, hi, title, instrs, labels, slice_tag="Slice 19"):
    section = "ROM0" if bank == 0 else "ROMX"
    bankarg = f", BANK[{bank}]" if bank != 0 else ""
    out = [f"; {slice_tag}: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/gen_slice19.py from the ROM bytes via",
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
    out = [f"; Slice 19: {title} -- bank {bank} ${lo:04x}-"
           f"${lo + 2 * len(entries) - 1:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/gen_slice19.py; values read straight "
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
    out = [f"; Slice 19: {title} -- bank {bank} ${lo:04x}-${hi:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/gen_slice19.py; bytes read straight "
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


# ------------------------------------------------------------------
# Bank 29 sprite table + blocks.
# ------------------------------------------------------------------

def emit_bank29(rom):
    base = file_off(29, 0x4000)
    entries = [rom[base + 2 * i] | (rom[base + 2 * i + 1] << 8)
               for i in range(256)]
    assert all(0x4200 <= w < 0x8000 for w in entries), \
        "implausible table word"
    assert not any(0x4100 <= w < 0x4200 for w in entries), \
        "entry points into the table region"
    targets = sorted(set(entries))
    assert targets[0] == 0x4200
    assert rom[file_off(29, 0x7E93)] != 0xFF
    assert all(b == 0xFF for b in
               rom[file_off(29, 0x7E94):file_off(29, 0x8000)]), \
        "trailing padding is not all $ff"
    # $4200 default block byte-identical to bank 11's.
    assert rom[file_off(29, 0x4200):file_off(29, targets[1])] == \
        rom[file_off(11, 0x4200):file_off(11, targets[1])], \
        "$4200 block differs from bank 11"
    owners = {}
    for i, w in enumerate(entries):
        owners.setdefault(w, []).append(i)

    out = ["; DO NOT HAND-EDIT this file -- regenerate with",
           ";   python3 tools/gen_slice19.py",
           "; after changing the generator config.",
           "",
           "; Slice 19: Bank 29 $4000 sprite-pointer table -- 256 dw.",
           "; The second $112c table (bank $1d): selected by the $10d5",
           "; entry (state-16 transition steps), where bank $0b (11) is",
           "; selected by $10dd everywhere else. Indexed by 2*record[0],",
           "; then +2*record[1], same as bank 11. 99 entries are $4200",
           "; (the empty/default block, byte-identical to bank 11's).",
           "; Generated by tools/gen_slice19.py from the ROM bytes.",
           'SECTION "Bank 29 $4000 sprite table", ROMX[$4000], BANK[29]']
    for i, w in enumerate(entries):
        out.append(f"    {'dw $%04x' % w:<48} ; entry {i}")
    with open("src/bank29.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote src/bank29.asm (256 dw, {len(targets)} distinct targets)")

    header = ("; DO NOT HAND-EDIT this file -- regenerate with\n"
              ";   python3 tools/gen_slice19.py\n"
              "; after changing the generator config.\n\n"
              "; Slice 19: Bank 29 sprite blocks -- the 121 distinct blocks\n"
              "; the $4000 table (256 dw, src/bank29.asm) points at.\n"
              "; Each block runs from its target to the next distinct target;\n"
              "; the last block ($7d02) runs to $7e94 (last non-$ff byte in\n"
              "; the bank; $7e94-$7fff is $ff padding, stays INCBIN).\n"
              "; Same block format as bank 11 (from $112c): a sprite group;\n"
              "; 2*record[1] selects a sub-entry inside the block. Internal\n"
              "; structure not decoded here -- plain db. Generated from the\n"
              "; ROM bytes.\n\n")
    out = [header]
    for j, tgt in enumerate(targets):
        end = targets[j + 1] if j + 1 < len(targets) else 0x7E94
        ents = owners[tgt]
        out.append(f"; Block ${tgt:04x}-${end:04x} ({end - tgt} bytes) -- "
                   f"table entries {ents}")
        out.append(f'SECTION "Bank 29 sprite block ${tgt:04x}", '
                   f'ROMX[${tgt:04x}], BANK[29]')
        out.append(f"Bank29_SpriteBlock_{tgt:04X}::")
        o = file_off(29, tgt)
        data = rom[o:o + (end - tgt)]
        assert len(data) == end - tgt
        for k in range(0, len(data), 16):
            chunk = data[k:k + 16]
            out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
        out.append("")
    with open("src/bank29slice19.asm", "w") as f:
        f.write("\n".join(out))
    print(f"wrote src/bank29slice19.asm ({len(targets)} blocks, "
          f"$4200-$7e94)")


# ------------------------------------------------------------------
# Bank 10 $7073 table + $7081-$7599 routines.
# ------------------------------------------------------------------

BANK10_TABLE = [0x7081, 0x7815, 0x70A6, 0x7297, 0x7369, 0x738F, 0x7400]
BANK10_SEEDS = [0x7081, 0x70A6, 0x7297, 0x7369, 0x738F, 0x7400]
BANK10_LABELS = {a: f"Bank10_{a:04X}" for a in BANK10_SEEDS}
BANK10_LABELS[(10, 0x7073)] = "Bank10_7073"


def emit_bank10(rom):
    reached, rst08, notes = walk(10, BANK10_SEEDS)
    for n in notes:
        print("note:", n, file=sys.stderr)
    print(f"bank 10 walk: {len(reached)} instrs, rst08={rst08}",
          file=sys.stderr)
    assert not rst08, f"unexpected rst $08: {rst08}"
    # Coverage: code spans, excluding the two data blobs.
    assert_coverage(10, 0x7081, 0x728F,
                    {a: v for a, v in reached.items()
                     if 0x7081 <= a <= 0x728F})
    assert_coverage(10, 0x7297, 0x74A9,
                    {a: v for a, v in reached.items()
                     if 0x7297 <= a <= 0x74A9})
    assert_coverage(10, 0x74BA, 0x7599,
                    {a: v for a, v in reached.items()
                     if 0x74BA <= a <= 0x7599})
    parts = []
    parts.append(emit_dw_table(
        rom, 10, 0x7073,
        [(0x7073 + 2 * i, f"[$c10a]={i} -> ${v:04x}")
         for i, v in enumerate(BANK10_TABLE)],
        "Bank 10 $7073 dw table (7 entries, $2b48 entry 63)",
        expected=BANK10_TABLE,
        note="Read by the $705f handler (slice 16): ld a,[$c10a]; add a; "
             "ld hl,$7073; ...; jp hl. Entry 4 ($7369) is the $7378 "
             "routine's head; entry 1 ($7815) is the carved 1-byte ret."))
    parts.append(emit_carve(
        rom, 10, 0x7081, 0x728F,
        "Bank 10 $7081-$728f $7073-table entries 0+2 routines",
        {a: v for a, v in reached.items() if 0x7081 <= a <= 0x728F},
        {(10, a): l for a, l in
         ((a, f"Bank10_{a:04X}") for a in BANK10_SEEDS)}))
    parts.append(emit_db(
        rom, 10, 0x7290, 0x7296,
        "Bank 10 $7290-$7296 7-byte data table",
        note="Indexed by [$c705] (ld hl,$7290 at $708c/$72ab); bytes "
             "a0 f0 f0 a0 a0 f0 a0."))
    parts.append(emit_carve(
        rom, 10, 0x7297, 0x74A9,
        "Bank 10 $7297-$74a9 $7073-table entries 3-6 routines",
        {a: v for a, v in reached.items() if 0x7297 <= a <= 0x74A9},
        {(10, a): l for a, l in
         ((a, f"Bank10_{a:04X}") for a in BANK10_SEEDS)}))
    parts.append(emit_db(
        rom, 10, 0x74AA, 0x74B9,
        "Bank 10 $74aa-$74b9 16-byte data (two 8-byte records)",
        note="Loaded via DE by the $748f routine ($74aa for type $37, "
             "$74b2 otherwise); copied 4 bytes at a time to $c1f3 by "
             "the $74ba routine."))
    parts.append(emit_carve(
        rom, 10, 0x74BA, 0x7599,
        "Bank 10 $74ba-$7599 $748f-routine continuation",
        {a: v for a, v in reached.items() if 0x74BA <= a <= 0x7599},
        {(10, a): l for a, l in
         ((a, f"Bank10_{a:04X}") for a in BANK10_SEEDS)}))
    with open("src/bank10slice19.asm", "w") as f:
        f.write("\n".join(parts))
    print("wrote src/bank10slice19.asm "
          "(table + 3 code carves + 2 data blobs)")


# ------------------------------------------------------------------
# Bank 31 $6a98-table entry 9 + $70df-$723d remainder.
# ------------------------------------------------------------------

BANK31_SEEDS = [0x6ED6, 0x70DF, 0x7161, 0x71BD, 0x7222, 0x722C]
BANK31_LABELS = {(31, a): f"Bank31_{a:04X}" for a in BANK31_SEEDS}


def emit_bank31(rom):
    reached, rst08, notes = walk(31, BANK31_SEEDS)
    for n in notes:
        print("note:", n, file=sys.stderr)
    print(f"bank 31 walk: {len(reached)} instrs, rst08={rst08}",
          file=sys.stderr)
    assert not rst08, f"unexpected rst $08: {rst08}"
    assert_coverage(31, 0x6ED6, 0x6F88,
                    {a: v for a, v in reached.items()
                     if 0x6ED6 <= a <= 0x6F88})
    assert_coverage(31, 0x70DF, 0x7144,
                    {a: v for a, v in reached.items()
                     if 0x70DF <= a <= 0x7144})
    assert_coverage(31, 0x7161, 0x7211,
                    {a: v for a, v in reached.items()
                     if 0x7161 <= a <= 0x7211})
    assert_coverage(31, 0x7222, 0x722B,
                    {a: v for a, v in reached.items()
                     if 0x7222 <= a <= 0x722B})
    assert_coverage(31, 0x722C, 0x723D,
                    {a: v for a, v in reached.items()
                     if 0x722C <= a <= 0x723D})
    parts = []
    parts.append(emit_db(
        rom, 31, 0x6EBA, 0x6ED5,
        "Bank 31 $6eba-$6ed5 28-byte data table",
        note="Copied to $c1c4 by the $6e95 routine (ld hl,$6eba at "
             "$6e9a; ld c,$1c; call $106e) -- same shape as the $6fde "
             "and $7145 tables."))
    parts.append(emit_carve(
        rom, 31, 0x6ED6, 0x6F88,
        "Bank 31 $6ed6-$6f88 $6a98-table entry-9 routine",
        {a: v for a, v in reached.items() if 0x6ED6 <= a <= 0x6F88},
        BANK31_LABELS))
    parts.append(emit_carve(
        rom, 31, 0x70DF, 0x7144,
        "Bank 31 $70df-$7144 $6a98-table entry-14 routine",
        {a: v for a, v in reached.items() if 0x70DF <= a <= 0x7144},
        BANK31_LABELS))
    parts.append(emit_db(
        rom, 31, 0x7145, 0x7160,
        "Bank 31 $7145-$7160 28-byte data table",
        note="Copied to $c1c4 by the $70df routine (ld hl,$7145 at "
             "$70e9; ld c,$1c; call $106e)."))
    parts.append(emit_carve(
        rom, 31, 0x7161, 0x7211,
        "Bank 31 $7161-$7211 $6a98-table entries 15-16 routines",
        {a: v for a, v in reached.items() if 0x7161 <= a <= 0x7211},
        BANK31_LABELS))
    parts.append(emit_db(
        rom, 31, 0x7212, 0x7221,
        "Bank 31 $7212-$7221 16-byte data table (4x4)",
        note="4 entries x 4 bytes (ASCII 'body','fkhm','ncpe','jgkl'); "
             "indexed by [$c113]&3, copied 4 bytes to $c1c4 by the "
             "$71e5 routine (ld hl,$7212 at $71f2; ld c,$04; call "
             "$106e)."))
    parts.append(emit_carve(
        rom, 31, 0x7222, 0x722B,
        "Bank 31 $7222-$722b $6a98-table entry-17 countdown tail",
        {a: v for a, v in reached.items() if 0x7222 <= a <= 0x722B},
        BANK31_LABELS))
    parts.append(emit_carve(
        rom, 31, 0x722C, 0x723D,
        "Bank 31 $722c-$723d $6a98-table entry-18 countdown tail",
        {a: v for a, v in reached.items() if 0x722C <= a <= 0x723D},
        BANK31_LABELS))
    with open("src/bank31slice19.asm", "w") as f:
        f.write("\n".join(parts))
    print("wrote src/bank31slice19.asm "
          "(entry-9 routine + $70df-$723d remainder)")


def main():
    rom = open(ROM, "rb").read()
    emit_bank29(rom)
    emit_bank10(rom)
    emit_bank31(rom)


if __name__ == "__main__":
    main()
