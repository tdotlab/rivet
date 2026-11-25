#!/usr/bin/env python3
"""Slice-18 generator: bank-11 sprite blocks + 256-entry table extension.

Bank 11 $4000 is the $112c sprite-pointer table. Slice 7 carved 128
entries and called the extent inferred. Slice 18 VERIFIES 256 entries:
  * $112c indexes it by the FULL record byte 0 (C = byte0, HL = $4000
    + 2*C, no masking), so the table must cover all 256 byte values.
  * Live record byte-0 values across all 101 surveyed stages reach 229
    (tools/surveys/survey18_records.py) -- past 127, so a 128-entry table cannot
    be right.
  * All 256 words ($4000-$4200) are plausible pointers ($4200-$7xxx),
    none points into $4100-$41ff, and 35 of them are $4200 (the
    empty/default block) -- the same signature as entries 0-127.
  * Only banks 11 and 29 carry this table (whole-ROM survey: 256/256
    plausible words); bank 29's table differs in 220/256 entries, so
    this slice carves bank 11 only. Bank 29 is a next-slice target.

The blocks: the 256 entries point at 176 distinct targets in
$4200-$7948. They partition the range exactly (consecutive-target gaps
sum to the span, no gaps, no overlaps), so each block is emitted as db
from its target to the next distinct target. The last block ($7948)
runs to $7e3d (bank 11's last non-$ff byte is at $7e3c; $7e3d-$7fff is
$ff padding and stays INCBIN). Block format (from $112c): a sprite
group; within a block, 2*record[1] selects a sub-entry whose first
byte is a count and whose second byte is $f0/$f1 for the flip
variants -- the internal structure is NOT decoded here, plain db.

Regenerate with: python3 tools/generators/gen_slice18.py
Outputs: src/banks/bank11.asm (table extended 128 -> 256 dw, via the
gen_slice7.py emitter -- see note below) and src/banks/bank11slice18.asm
(new file, 176 db blocks). Also update tools/generators/gen_banks.py CARVED
(bank 11: (0x4000,0x4200) + (0x4200,0x7E3D)) and regenerate
src/banks.asm; add INCLUDE \"bank11slice18.asm\" to src/main.asm
after bank11.asm.

NOTE: the table itself is emitted by patching tools/generators/gen_slice7.py's
emit_bank11 (128 -> 256) and re-running it, NOT by this script --
gen_slice7.py owns src/banks/bank11.asm. This script only emits the blocks.

Gap carves (task 3, also emitted by this script, into
src/banks/bank9slice18.asm and src/banks/bank31slice18.asm):
  * Bank 9 $684f-$6907: three map-sample dispatch routines
    ($684f, $6893, $68d7), same shape as the $664a-table routines
    (slice 17): HL = DE + a signed offset, sample [HL] & $c0,
    jump to the carved $6ae7/$6b8d/$6bbc/$6bf2/$6c34/$6c7e/$6cb7
    routines. $68d7 also writes $c112-$c116 ($10,$10,0,0,$a0),
    sets bit 2 of [$c103], clears [$c102], then dispatches on
    [$c10e] bit 0 (jp nc,$6ad5). Entry mechanism for all three
    heads is UNVERIFIED (no call/jp ref anywhere in the ROM; the
    preceding spans end in jp, no fall-through). Alignment traps
    avoided: $6891-$6892 are the jp $6ae7 operand bytes, NOT code
    (a walk seeded there misaligns by 2).
  * Bank 31 $4499-$4566: a 3-entry dw table ($449f,$44dc,$4540)
    read by the carved $4205-$4498 span's jp-hl dispatch
    (`ld a,[$c10a]; add a; ld hl,$4499; ...; jp hl` at $4491),
    plus the three table routines. $449f sets [$c103] bit 2 and
    [$c109] bit 0, inc [$c10a], calls $1d2f, writes [$c0f9]=$2a
    and [$c116]=$51.
  * Bank 31 $506c-$5200: a 7-entry dw table ($507a,$50e0,$510f,
    $5175,$519b,$51ce,$51e3) read by the entry-51 handler's
    `ld hl,$506c ... jp hl` at $5064, plus the seven routines.
  * Bank 31 $6244-$64ed: an 11-entry dw table read by the
    entry-80 handler's `ld hl,$6244 ... jp hl` at $623c, plus
    the eleven routines.
  * Bank 31 $6fde-$704f: a 28-byte data table ($6fde-$6ff9 --
    exactly $1c bytes, matching the `ld c,$1c` below), a
    countdown/state routine $6ffa-$704a (dec [$c867], [$c0fa]+=4,
    dec [$c10c] with $1e reload, [$c10a]=1 or $0c, [$c114]=1 on
    the [$c0a4]==2 path, then memcpy $6fde->$c1c4 via $106e and
    jp $6f89), and a 5-byte countdown wrapper $704b-$704f
    (`dec [$c10c]; ret nz`) falling through into the carved
    $7050 shared routine. The $6ffa routine's entry is
    unverified; $704b's fall-through into $7050 is structural.
  * Bank 31 $708f-$723d: only the head is code -- $708f-$70cd
    (`dec [$c10c]; jp nz,$723e`, position math on [$c213]
    records, [$c10a]=4, [$c114]=2, jp $723e) plus the tiny
    state-setter $70d0-$70de ([$c10a]=1, [$c10c]=$0f, [$c114]=0).
    Remainder $70df-$723d stays INCBIN (mixed data; the
    $70ce seed is the jp $723e operand byte, NOT code -- same
    trap as $6891). Entry for $708f unverified.
  * Bank 31 $7a12-$7bf5: a 6-entry dw table read by the
    $7934-$7a11 span's `ld hl,$7a12 ... jp hl` at $7a0a, plus
    the six routines.
Table lengths are the increasing-dw-run rule (verified against
the ROM bytes); every table entry is asserted to be a decoded
instruction start. The $70df-$723d remainder and the post-table
bytes stay INCBIN.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
OUT = "src/banks/bank11slice18.asm"
BANK = 11
TABLE_LO, TABLE_HI = 0x4000, 0x4200  # 256 dw entries
BLOCKS_LO = 0x4200
BLOCKS_HI = 0x7E3D  # last non-$ff byte in bank 11 is at $7e3c


def file_off(bank, addr):
    return bank * 0x4000 + (addr - 0x4000)


def main():
    rom = open(ROM, "rb").read()
    emit_bank11_blocks(rom)
    emit_gap_carves(rom)


# ------------------------------------------------------------------
# Gap carves (task 3). Same emit helpers as gen_slice17.py.
# ------------------------------------------------------------------

# (bank, lo, hi, section title, outfile) -- hi inclusive.
GAP_CARVES = [
    (9, 0x684F, 0x6907, "Bank 9 $684f-$6907 map-sample dispatch routines",
     "src/banks/bank9slice18.asm"),
    (31, 0x449F, 0x4566, "Bank 31 $449f-$4566 $4499-table routines",
     "src/banks/bank31slice18.asm"),
    (31, 0x507A, 0x5200, "Bank 31 $507a-$5200 $506c-table routines",
     "src/banks/bank31slice18.asm"),
    (31, 0x625A, 0x64ED, "Bank 31 $625a-$64ed $6244-table routines",
     "src/banks/bank31slice18.asm"),
    (31, 0x6FFA, 0x704A, "Bank 31 $6ffa-$704a countdown/state routine",
     "src/banks/bank31slice18.asm"),
    (31, 0x704B, 0x704F, "Bank 31 $704b-$704f countdown wrapper for $7050",
     "src/banks/bank31slice18.asm"),
    (31, 0x708F, 0x70DE, "Bank 31 $708f-$70de countdown routine + "
     "state-setter", "src/banks/bank31slice18.asm"),
    (31, 0x7A1E, 0x7BF5, "Bank 31 $7a1e-$7bf5 $7a12-table routines",
     "src/banks/bank31slice18.asm"),
]

# [$c10a] jp-hl tables: (base, [entries]).
GAP_TABLES = {
    0x4499: [0x449F, 0x44DC, 0x4540],
    0x506C: [0x507A, 0x50E0, 0x510F, 0x5175, 0x519B, 0x51CE, 0x51E3],
    0x6244: [0x625A, 0x62B0, 0x6345, 0x6356, 0x6369, 0x637C, 0x63A5,
             0x63FD, 0x6434, 0x6497, 0x649F],
    0x7A12: [0x7A1E, 0x7A57, 0x7ADD, 0x7AFE, 0x7BCA, 0x7BEB],
}

GAP_SEEDS9 = [0x684F, 0x6893, 0x68D7]
GAP_SEEDS31 = [0x449F, 0x44DC, 0x4540, 0x507A, 0x50E0, 0x510F, 0x5175,
               0x519B, 0x51CE, 0x51E3, 0x625A, 0x62B0, 0x6345, 0x6356,
               0x6369, 0x637C, 0x63A5, 0x63FD, 0x6434, 0x6497, 0x649F,
               0x6FFA, 0x704B, 0x708F, 0x70D0, 0x7A1E, 0x7A57, 0x7ADD,
               0x7AFE, 0x7BCA, 0x7BEB]

LABELS = {}
for _a in (0x684F, 0x6893, 0x68D7):
    LABELS[(9, _a)] = f"Bank9_{_a:04X}"
for _b, _ents in GAP_TABLES.items():
    LABELS[(31, _b)] = f"Bank31_{_b:04X}"
    for _v in _ents:
        LABELS.setdefault((31, _v), f"Bank31_{_v:04X}")
for _a in (0x6FDE, 0x6FFA, 0x704B, 0x708F, 0x70D0):
    LABELS.setdefault((31, _a), f"Bank31_{_a:04X}")


def jr_targets_in(instrs, lo, hi):
    out = set()
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
            out.add(tgt)
    return out


def fmt_instr(bank, addr, text, kind, tgt, lo, hi, jr_targets):
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
    out = [f"; Slice 18: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice18.py from the ROM bytes via",
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
    label = LABELS.get((bank, lo))
    out = [f"; Slice 18: {title} -- bank {bank} ${lo:04x}-"
           f"${lo + 2 * len(entries) - 1:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/generators/gen_slice18.py; values read straight "
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
    label = LABELS.get((bank, lo))
    out = [f"; Slice 18: {title} -- bank {bank} ${lo:04x}-${hi:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/generators/gen_slice18.py; bytes read straight "
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


def emit_gap_carves(rom):
    reached9, rst08_9, notes9 = walk(9, GAP_SEEDS9)
    reached31, rst08_31, notes31 = walk(31, GAP_SEEDS31)
    for n in notes9 + notes31:
        print("note:", n, file=sys.stderr)
    print(f"gap walk bank 9: {len(reached9)} instrs; "
          f"bank 31: {len(reached31)} instrs", file=sys.stderr)
    assert not rst08_9 and not rst08_31, \
        f"unexpected rst $08: {rst08_9} {rst08_31}"
    for _base, _ents in GAP_TABLES.items():
        for _v in _ents:
            assert _v in reached31, f"bank 31 table entry ${_v:04x} " \
                "not decoded"
    by_file = {}
    for bank, lo, hi, title, outfile in GAP_CARVES:
        reached = {9: reached9, 31: reached31}[bank]
        instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
        covered = set()
        for a, (ln, *_r) in instrs.items():
            covered.update(range(a, a + ln))
        assert covered == set(range(lo, hi + 1)), \
            f"bank {bank} ${lo:04x}-${hi:04x}: uncovered bytes " \
            f"{sorted(set(range(lo, hi + 1)) - covered)[:8]}"
        by_file.setdefault(outfile, []).append(
            (bank, lo, hi, title, instrs))
    # Bank 31 data: the four jp-hl tables + the $6fde 28-byte table.
    b31_data = []
    for base, ents in GAP_TABLES.items():
        b31_data.append(emit_dw_table(
            rom, 31, base,
            [(base + 2 * i, f"entry {i} -> ${ents[i]:04x}")
             for i in range(len(ents))],
            f"Bank 31 ${base:04x} dw table ({len(ents)} entries)",
            expected=ents))
    b31_data.append(emit_db(
        rom, 31, 0x6FDE, 0x6FF9,
        "Bank 31 $6fde-$6ff9 28-byte data table",
        note="Copied to $c1c4 by the $6ffa routine (ld c,$1c; call "
             "$106e); exactly $1c bytes, matching the copy length."))
    b31 = b31_data + [emit_carve(rom, bank, lo, hi, title, instrs)
                      for bank, lo, hi, title, instrs
                      in by_file.get("src/banks/bank31slice18.asm", [])]
    with open("src/banks/bank31slice18.asm", "w") as f:
        f.write("\n".join(b31))
    print(f"wrote src/banks/bank31slice18.asm "
          f"({len(b31_data)} data + "
          f"{len(by_file.get('src/banks/bank31slice18.asm', []))} code carves)")
    b9 = [emit_carve(rom, bank, lo, hi, title, instrs)
          for bank, lo, hi, title, instrs
          in by_file.get("src/banks/bank9slice18.asm", [])]
    with open("src/banks/bank9slice18.asm", "w") as f:
        f.write("\n".join(b9))
    print(f"wrote src/banks/bank9slice18.asm ({len(b9)} code carve)")


def emit_bank11_blocks(rom):
    base = file_off(BANK, TABLE_LO)
    entries = [rom[base + 2 * i] | (rom[base + 2 * i + 1] << 8)
               for i in range(256)]
    # Verify the table assumptions before emitting anything.
    assert all(0x4200 <= w < 0x8000 for w in entries), "implausible table word"
    assert not any(0x4100 <= w < 0x4200 for w in entries), \
        "entry points into the table region"
    targets = sorted(set(entries))
    assert targets[0] == BLOCKS_LO
    assert rom[file_off(BANK, 0x7E3C)] != 0xFF
    assert all(b == 0xFF for b in rom[file_off(BANK, 0x7E3D):file_off(BANK, 0x8000)]), \
        "trailing padding is not all $ff"
    owners = {}
    for i, w in enumerate(entries):
        owners.setdefault(w, []).append(i)

    header = ("; DO NOT HAND-EDIT this file -- regenerate with\n"
              ";   python3 tools/generators/gen_slice18.py\n"
              "; after changing the generator config.\n\n"
              "; Slice 18: Bank 11 sprite blocks -- the 176 distinct blocks\n"
              "; the $4000 table (256 dw, src/banks/bank11.asm) points at.\n"
              "; Each block runs from its target to the next distinct target;\n"
              "; the last block ($7948) runs to $7e3d (last non-$ff byte in\n"
              "; the bank; $7e3d-$7fff is $ff padding, stays INCBIN).\n"
              "; Block format (from $112c): a sprite group; 2*record[1]\n"
              "; selects a sub-entry inside the block. Internal structure\n"
              "; not decoded here -- plain db. Generated from the ROM bytes.\n\n")
    out = [header]
    for j, tgt in enumerate(targets):
        end = targets[j + 1] if j + 1 < len(targets) else BLOCKS_HI
        ents = owners[tgt]
        out.append(f"; Block ${tgt:04x}-${end:04x} ({end - tgt} bytes) -- "
                   f"table entries {ents}")
        out.append(f'SECTION "Bank 11 sprite block ${tgt:04x}", '
                   f'ROMX[${tgt:04x}], BANK[11]')
        out.append(f"Bank11_SpriteBlock_{tgt:04X}::")
        o = file_off(BANK, tgt)
        data = rom[o:o + (end - tgt)]
        assert len(data) == end - tgt
        for k in range(0, len(data), 16):
            chunk = data[k:k + 16]
            out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
        out.append("")
    with open(OUT, "w") as f:
        f.write("\n".join(out))
    print(f"wrote {OUT} ({len(targets)} blocks, "
          f"${BLOCKS_LO:04x}-${BLOCKS_HI:04x})")


if __name__ == "__main__":
    main()
