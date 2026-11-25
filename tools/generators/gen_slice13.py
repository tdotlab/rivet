#!/usr/bin/env python3
"""Slice-13 generator: carve the $4827 [$dd18] dispatch table's
remaining entries (bank 7) -- the per-frame interaction routines
that were not yet carved.

Why this carve (see PROGRESS.md slice 13):
  * The $4827 table (slice 12) dispatches on [$dd18] (13 entries).
    Entries 7 ($6b09, no-op) and 10 ($627b, post-$5b-trigger scan)
    were carved in slices 10/12. This slice carves entries 0-6,
    8, 9, 11, 12 and their `jp hl` subtables, plus the $66ca/$6732
    and $695b ($69ab) shared subroutines they call.
  * Entry 11 ($644d) OVERLAPS the $643f record template (slice 12):
    the template is 20 bytes ($643f-$6452) and entry 11's dispatch
    head ($644d-$6452: ld a,[$c213]; add a; ld c,a; ld b,$00) is
    its last 6 bytes. So the template is shortened to 14 bytes
    ($643f-$644c) in src/banks/bank7slice12.asm (and in gen_slice12.py),
    and entry 11 is emitted here as full code ($644d-$645b). The
    20-byte copy to $c1ab ($6370-$6378) still reads the same 20
    bytes; byte-match arbitrates.
  * Entry 12 ($64db) sits inside the $6464-$64ea span (it is one
    of the $645c table's targets); it is emitted as an interior
    label of that span, not a separate section.
  * $5083-$50a0 is real code (ld hl,$c11b; pointer check; cp
    $08/$0e; jp $4ea8) with NO found entry (no call/jp/dw to it
    anywhere in the ROM) -- left INCBIN, noted in PROGRESS.md.
  * $5d4a-$5d6e (36 bytes) decodes as garbage ($fd/$fc bytes,
    self-referential jr) -- emitted as db data.
  * [$dd18] values written by this code are 0-9, $0e, $16 -- never
    $0a. The only $0a setter in the ROM is the $6bf2 tail (handler
    0, the $5b trigger). So [$dd18]==$0a happens only via the $5b
    trigger cell, which exists only in 1-1's map among the 24
    stages surveyed live (see tools/surveys/survey13_progmaps.py).

Regenerate with: python3 tools/generators/gen_slice13.py
Outputs: src/banks/bank7slice13.asm (new file). Regenerates
src/banks.asm via tools/generators/gen_banks.py after updating its CARVED
map. The outputs are CHECKED IN; rerun after changing the config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile, seeds)
# hi is inclusive; code spans end just before their jp-hl dw table.
CARVES = [
    (7, 0x4841, 0x4ED6, "Bank 7 $4841-$4ed6 [$dd18] entry 0",
     "src/banks/bank7slice13.asm", [0x4841]),
    (7, 0x4EDB, 0x5082, "Bank 7 $4edb-$5082 [$dd18] entry 1 "
     "routines ($4ed7 table)", "src/banks/bank7slice13.asm", [0x4EDB]),
    (7, 0x50A0, 0x521E, "Bank 7 $50a0-$521e [$dd18] entry 2",
     "src/banks/bank7slice13.asm", [0x50A0]),
    (7, 0x5229, 0x5681, "Bank 7 $5229-$5681 [$dd18] entry 3/6 "
     "routines ($521f table)", "src/banks/bank7slice13.asm", [0x5229]),
    (7, 0x5694, 0x58EE, "Bank 7 $5694-$58ee [$dd18] entry 4 "
     "routines ($5682 table)", "src/banks/bank7slice13.asm", [0x5694]),
    (7, 0x58F5, 0x5A19, "Bank 7 $58f5-$5a19 [$dd18] entry 5 "
     "routines ($58ef table)", "src/banks/bank7slice13.asm", [0x58F5]),
    (7, 0x5A20, 0x5D49, "Bank 7 $5a20-$5d49 [$dd18] entry 8 "
     "routines ($5a1a table)", "src/banks/bank7slice13.asm", [0x5A20]),
    (7, 0x5D6E, 0x5F32, "Bank 7 $5d6e-$5f32 [$dd18] entry 8/9",
     "src/banks/bank7slice13.asm", [0x5D6E]),
    (7, 0x5F45, 0x627A, "Bank 7 $5f45-$627a [$dd18] entry 9 "
     "routines ($5f33 table)", "src/banks/bank7slice13.asm", [0x5F45]),
    (7, 0x644D, 0x645B, "Bank 7 $644d-$645b [$dd18] entry 11 "
     "dispatch (head is the $643f template tail)",
     "src/banks/bank7slice13.asm", [0x644D]),
    (7, 0x6464, 0x64E9, "Bank 7 $6464-$64e9 [$dd18] entry 11/12 "
     "routines ($645c table; entry 12 $64db inside)",
     "src/banks/bank7slice13.asm", [0x6464]),
    (7, 0x64F0, 0x6571, "Bank 7 $64f0-$6571 [$dd18] entry 12 "
     "routines ($64ea table)", "src/banks/bank7slice13.asm", [0x64F0]),
    (7, 0x66CA, 0x67A0, "Bank 7 $66ca-$67a0 shared subroutine "
     "($66ca called from $4861/$57bf; $6732 inside)",
     "src/banks/bank7slice13.asm", [0x66CA]),
    (7, 0x695B, 0x6B08, "Bank 7 $695b-$6b08 shared subroutine "
     "($69ab inside; called from $4ec0/$5bd2/$5dbe/$64ab)",
     "src/banks/bank7slice13.asm", [0x695B]),
]

# In-carve tables: (bank, addr) -> ("dw", [values]) or ("db", [bytes]).
TABLES = {
    (7, 0x4ED7): ("dw", [0x4EDB, 0x50B6]),
    (7, 0x521F): ("dw", [0x5229, 0x5409, 0x5520, 0x55BF, 0x5633]),
    (7, 0x5682): ("dw", [0x5694, 0x56C9, 0x56E5, 0x5736, 0x5761,
                         0x57BF, 0x5863, 0x5874, 0x58BE]),
    (7, 0x58EF): ("dw", [0x58F5, 0x5946, 0x59BD]),
    (7, 0x5A1A): ("dw", [0x5A20, 0x5C04, 0x5C54]),
    (7, 0x5D4A): ("db", None),  # 36 bytes, read from ROM in main()
    (7, 0x5F33): ("dw", [0x5F45, 0x5F77, 0x5FEC, 0x602D, 0x605F,
                         0x6088, 0x60AE, 0x615B, 0x616E]),
    (7, 0x645C): ("dw", [0x6464, 0x6486, 0x64AE, 0x64AF]),
    (7, 0x64EA): ("dw", [0x64F0, 0x6524, 0x654C]),
}

# Meaningful entry labels: (bank, addr) -> name.
LABELS = {
    (7, 0x4841): "Bank7_4841",  # [$dd18]==0
    (7, 0x4E8B): "Bank7_4E8B",  # [$dd18]==1
    (7, 0x517C): "Bank7_517C",  # [$dd18]==2
    (7, 0x5673): "Bank7_5673",  # [$dd18]==3
    (7, 0x58DA): "Bank7_58DA",  # [$dd18]==4
    (7, 0x59FF): "Bank7_59FF",  # [$dd18]==5
    (7, 0x5669): "Bank7_5669",  # [$dd18]==6
    (7, 0x5D6E): "Bank7_5D6E",  # [$dd18]==8
    (7, 0x5EA1): "Bank7_5EA1",  # [$dd18]==9
    (7, 0x644D): "Bank7_644D",  # [$dd18]==11 (head is template tail)
    (7, 0x64DB): "Bank7_64DB",  # [$dd18]==12 (inside $6464 span)
    (7, 0x66CA): "Bank7_66CA",  # shared sub, called from $4861/$57bf
    (7, 0x6732): "Bank7_6732",  # shared sub, called from
                                # $4fe2/$522c/$540c
    (7, 0x695B): "Bank7_695B",  # shared sub ($69ab inside)
    (7, 0x4ED7): "Bank7_4ED7",  # jp-hl table for entry 0
    (7, 0x521F): "Bank7_521F",  # jp-hl table for entry 2
    (7, 0x5682): "Bank7_5682",  # jp-hl table for entry 3/6
    (7, 0x58EF): "Bank7_58EF",  # jp-hl table for entry 5
    (7, 0x5A1A): "Bank7_5A1A",  # jp-hl table for entry 8
    (7, 0x5F33): "Bank7_5F33",  # jp-hl table for entry 9
    (7, 0x645C): "Bank7_645C",  # jp-hl table for entry 11
    (7, 0x64EA): "Bank7_64EA",  # jp-hl table for entry 12
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
    out = [f"; Slice 13: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice13.py from the ROM bytes via",
           "; tools/gb_rd.py (recursive descent, not mgbdis' linear",
           "; sweep). Byte-match (`make`) arbitrates.",
           f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]']
    jr_targets = jr_targets_in(instrs, lo, hi)
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                and lo <= tgt <= hi and tgt not in instrs:
            print(f"ERROR: bank {bank} ${addr:04x} {text} targets "
                  f"${tgt:04x}, not a decoded instruction",
                  file=sys.stderr)
            sys.exit(1)
    for site, tbl in rst08.items():
        if not (lo <= site <= hi):
            continue
        for i, w in enumerate(tbl):
            if 0x4000 <= w <= 0x7FFF and lo <= w <= hi and w not in instrs:
                print(f"ERROR: bank {bank} rst $08 at ${site:04x} entry "
                      f"{i} -> ${w:04x}, not decoded", file=sys.stderr)
                sys.exit(1)
    addr = lo
    while addr <= hi:
        if (bank, addr) in TABLES:
            kind, vals = TABLES[(bank, addr)]
            nbytes = 2 * len(vals) if kind == "dw" else len(vals)
            label = LABELS.get((bank, addr))
            if label:
                out.append(f"{label}::")
            if kind == "dw":
                for i, w in enumerate(vals):
                    out.append(f"    {'dw $%04x' % w:<48} ; "
                               f"${addr + 2 * i:04x}")
            else:
                for j in range(0, len(vals), 8):
                    chunk = vals[j:j + 8]
                    out.append("    db " + ", ".join(f"${b:02x}"
                                                     for b in chunk))
            addr += nbytes
            continue
        if addr in instrs:
            ln, text, kind, tgt = instrs[addr]
            if kind == "rst08":
                tbl = rst08[addr]
                out.append(f"    {'rst $08':<48} ; ${addr:04x}")
                for i, w in enumerate(tbl):
                    out.append(f"    {'dw $%04x' % w:<48} ; entry {i}")
                addr += 1 + 2 * len(tbl)
                continue
            out.append(fmt_instr(bank, addr, text, kind, tgt,
                                 lo, hi, jr_targets))
            addr += ln
        else:
            # Uncovered bytes inside the carve: honest data.
            run = []
            while addr <= hi and addr not in instrs \
                    and (bank, addr) not in TABLES \
                    and not any(s < addr < s + 1 + 2 * len(t)
                                for s, t in rst08.items()):
                run.append(rom[file_off(bank, addr)])
                addr += 1
            if not run:
                print(f"ERROR: bank {bank} ${addr:04x}: fell into an "
                      f"rst-$08 table outside the rst08 branch",
                      file=sys.stderr)
                sys.exit(1)
            label = LABELS.get((bank, addr - len(run)))
            if label:
                out.append(f"{label}::")
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def main():
    rom = open(ROM, "rb").read()
    # The $5d4a-$5d6e data block (36 bytes) is read from the ROM.
    TABLES[(7, 0x5D4A)] = ("db", list(rom[file_off(7, 0x5D4A):
                                          file_off(7, 0x5D4A) + 36]))
    # Verify the hand-listed dw tables against the ROM bytes.
    for (bank, addr), (kind, vals) in TABLES.items():
        base = file_off(bank, addr)
        if kind == "dw":
            got = [rom[base + 2 * i] | (rom[base + 2 * i + 1] << 8)
                   for i in range(len(vals))]
        else:
            got = list(rom[base:base + len(vals)])
        assert got == vals, \
            f"bank {bank} table at ${addr:04x} mismatch: {got} != {vals}"
    # Walk bank 7 from all entry points + table-entry routines +
    # shared subroutines. The $4827 entries 11/12 are the dispatch
    # heads; the $645c/$64ea tables' targets are the seeds.
    seeds = [0x4841, 0x4E8B, 0x517C, 0x5673, 0x58DA, 0x59FF, 0x5669,
             0x5D6E, 0x5EA1, 0x644D, 0x64DB,
             0x4EDB, 0x50B6,
             0x5229, 0x5409, 0x5520, 0x55BF, 0x5633,
             0x5694, 0x56C9, 0x56E5, 0x5736, 0x5761, 0x57BF, 0x5863,
             0x5874, 0x58BE,
             0x58F5, 0x5946, 0x59BD,
             0x5A20, 0x5C04, 0x5C54,
             0x5F45, 0x5F77, 0x5FEC, 0x602D, 0x605F, 0x6088, 0x60AE,
             0x615B, 0x616E,
             0x6464, 0x6486, 0x64AE, 0x64AF,
             0x64F0, 0x6524, 0x654C,
             0x66CA, 0x695B]
    reached, rst08, notes = walk(7, seeds)
    for n in notes:
        print("note:", n, file=sys.stderr)
    print(f"walk: {len(reached)} instrs, {len(rst08)} rst08 sites",
          file=sys.stderr)
    assert not rst08, "unexpected rst $08 in bank-7 slice-13 walk"
    # The walk also reaches already-carved spans ($6f06-$6f40,
    # $714c-$7168, $77a9-$7abb, $627b-$63c3, $63f4-$643e, $6572-$6580,
    # $664e-$66c9, $6b09-$6b54); those are NOT re-emitted here.
    by_file = {}
    for bank, lo, hi, title, outfile, _seeds in CARVES:
        instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
        covered = set()
        for a, (ln, *_r) in instrs.items():
            covered.update(range(a, a + ln))
        assert covered == set(range(lo, hi + 1)), \
            f"bank 7 ${lo:04x}-${hi:04x}: uncovered bytes " \
            f"{sorted(set(range(lo, hi + 1)) - covered)[:8]}"
        by_file.setdefault(outfile, []).append(
            (bank, lo, hi, title, instrs, rst08))
    # Emit the dw tables as their own sections, in address order,
    # interleaved with the code sections. TABLES keys are the table
    # addresses; emit each as a section between the code carves.
    # Build the full ordered list of (lo, hi, kind) pieces.
    pieces = []
    for bank, lo, hi, title, outfile, _s in CARVES:
        pieces.append((lo, hi, "code", title, outfile))
    for (bank, addr), (kind, vals) in TABLES.items():
        nbytes = 2 * len(vals) if kind == "dw" else len(vals)
        pieces.append((addr, addr + nbytes - 1, kind, None, None))
    pieces.sort()
    # Sanity: pieces must not overlap and must tile $4841-$6b09
    # except the known INCBIN gaps ($5083-$50a0, $627b-$644d,
    # $6572-$66ca, $67a1-$695b) and the already-carved $6b09.
    for i in range(len(pieces) - 1):
        assert pieces[i][1] < pieces[i + 1][0], \
            f"overlapping pieces: {pieces[i]} vs {pieces[i+1]}"
    for outfile, carves in by_file.items():
        parts = []
        for bank, lo, hi, title, instrs, rst08 in carves:
            parts.append(emit_carve(rom, bank, lo, hi, title, instrs,
                                    rst08))
        # Append the dw/db tables as sections after the code.
        for (bank, addr), (kind, vals) in sorted(TABLES.items()):
            nbytes = 2 * len(vals) if kind == "dw" else len(vals)
            label = LABELS.get((bank, addr))
            hdr = [f"; Slice 13: Bank 7 ${addr:04x}-${addr + nbytes - 1:04x} "
                   f"{'jp-hl dw table' if kind == 'dw' else 'data block'} "
                   f"-- bank {bank} ${addr:04x}-${addr + nbytes - 1:04x}.",
                   "; Generated by tools/generators/gen_slice13.py from the ROM bytes.",
                   f'SECTION "Bank 7 ${addr:04x} table", ROMX[${addr:04x}], '
                   f'BANK[{bank}]']
            if label:
                hdr.append(f"{label}::")
            if kind == "dw":
                for j, w in enumerate(vals):
                    hdr.append(f"    {'dw $%04x' % w:<48} ; "
                               f"${addr + 2 * j:04x}")
            else:
                for j in range(0, len(vals), 8):
                    chunk = vals[j:j + 8]
                    hdr.append("    db " + ", ".join(f"${b:02x}"
                                                     for b in chunk))
            parts.append("\n".join(hdr) + "\n")
        with open(outfile, "w") as f:
            f.write("\n".join(parts))
        print(f"wrote {outfile} ({sum(len(p) for p in parts)} bytes)")


if __name__ == "__main__":
    main()
