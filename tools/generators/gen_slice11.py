#!/usr/bin/env python3
"""Slice-11 generator: carve bank 8 $4000-$4aec (the $c117 map-record
builders) + its tables, bank 7 $41dd-$4793 (the $42xx per-frame
interaction routines, entered via the $41dd [$dd1a] table) +
$7d96-$7e06 (the handler-7/17 chains), and bank $10 (16) $4af0-$4e88
(the other per-frame $c117-record scanner, from $0868).

Why this carve (see PROGRESS.md slice 11):
  * Bank 8 $4022 zeroes the nine $c117 records (9 x 7 bytes) and runs
    four corner blocks; each block computes a map pointer and calls
    two sub-builders (even = pair 0, odd = pair 1, DE+2). The map is
    $c86d-$d86d, 32 cols x 32 rows x 4 bytes; each cell is TWO
    (type, subtype) pairs. Even builders sample pair 0, odd builders
    pair 1 (via $4aa0, which reads the dynamic $c0a6 table). The
    $0b cells in 1-1: parasol 2x2 (subtypes $22-$25), top-right 1x2
    (subtypes $20/$21), key 2x2 (subtypes $4a-$4d), and a 1x2
    vertical trigger (second pair, subtype $5b). The $750a map sends
    those subtypes to handlers 7, 6, 17 and 0 respectively -- all
    score pickups (+2, or handler 0's $c200-record deactivation),
    NOT the door. The door is not a $0b cell.
  * Bank 8 $4a04 (reached via bank-0 $2b24, called from bank 7
    $6331) scans the map near Mario for an ($82,$37) cell -- the
    post-key door-sensor path. No ($82,$37) cell exists in the 1-1
    map at frame 2500, so that path is inert in 1-1; the door's cell
    (if it is one) is still unidentified.
  * Bank 7 $41c9 (slice 5) dispatches on ([$dd1a]-1) via the $41dd
    table: 1->$41e9, 2->$4269, 3->$42cc, 4->$44e4, 5->$46bd,
    6->$4769. $44e4 dispatches on [$dd1f] via the $4506 table
    (0->$4510, 1->$45e2, 2->$4612, 3->$466f, 4->$4699), and $4510
    dispatches on [$dd18] via the $452f table. $466f is a SECOND
    hStateTimer=12 writer (besides bank $10 $53c8, slice 8's death
    pin): [$dd1f]==3 and [$ff91] bit 2 set -> timer 12, so it is a
    death path, not a stage-clear path.
  * Bank 7 $7d96/$7dbe are the handler-7 (parasol) and handler-17
    (key) chains: clear the 2x2 block, $33a7, $164c alloc, write a
    $c72f slot, $7e07 (decrement [$c858]; at 0, [$c82f]/[$c835]=$44),
    score +2 via $0e29. $7de6 is the shared 2x2 cell clear.
  * Bank $10 $4af0 scans the $c117 records each frame, clears
    stale ones (byte-3 == $9d checks), and at $4cf8 triggers a
    Mario action ([$dd1a]=3, [$dd24]/[$dd25]=$0080, [$dd26]=$08)
    with [$dd21] chosen by [$dd18]. $4b90 is a $c148/$c14b/$9d
    branch with no direct entry found in bank 16 (possibly a dead
    duplicate of the $4b43 branch); it decodes cleanly and is
    emitted as code with this note.
  * Tables: $41dd (6 dw), $4506 (5 dw), $452f (12 dw), $4aed/$4b23
    (one overlapping dw blob $4aed-$4b62: the $4aed entries are
    byte-table bases for the even builders' class lookup, the
    $4b23 entries for the odd builders; the last $4b23 entries are
    ROM0 bases like $1902), $5409 (256 4-byte class records),
    $4df5 (13 db, indexed by [$dd18]).

Regenerate with: python3 tools/generators/gen_slice11.py
Outputs: src/banks/bank8.asm, src/banks/bank7slice11.asm, src/banks/bank16slice11.asm
(new files). Regenerates src/banks.asm via tools/generators/gen_banks.py
after updating its CARVED map. The outputs are CHECKED IN; rerun
after changing the config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, decode, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile, seeds)
CARVES = [
    (8, 0x4000, 0x4AEC, "Bank 8 $4000-$4aec map-record builders",
     "src/banks/bank8.asm",
     [0x4000, 0x4022, 0x41B8, 0x4A04]),
    (7, 0x41DD, 0x4793, "Bank 7 $41dd-$4793 per-frame interaction routines",
     "src/banks/bank7slice11.asm",
     [0x41E9, 0x4200, 0x420D, 0x4237, 0x4269, 0x42CC, 0x4361, 0x43C6,
      0x43D9, 0x44CB, 0x44E4, 0x45A0, 0x45D9, 0x45E2, 0x4612, 0x4629,
      0x466F, 0x46B6, 0x46BD, 0x470D, 0x4750, 0x4769, 0x4510, 0x4549,
      0x4556, 0x456E, 0x4572, 0x4583, 0x45AB, 0x4699, 0x4779, 0x45C8]),
    (7, 0x7D96, 0x7E06, "Bank 7 $7d96-$7e06 handler-7/17 chains",
     "src/banks/bank7slice11.asm", [0x7D96, 0x7DBE, 0x7DE6]),
    (16, 0x4AF0, 0x4E88, "Bank 16 $4af0-$4e88 per-frame record scanner",
     "src/banks/bank16slice11.asm", [0x4AF0, 0x4B90]),
]

# In-carve tables: (bank, addr) -> ("dw", [values]) or ("db", [bytes]).
# Values verified against the ROM bytes in main().
TABLES = {
    (7, 0x41DD): ("dw", [0x41E9, 0x4269, 0x42CC, 0x44E4, 0x46BD, 0x4769]),
    (7, 0x4506): ("dw", [0x4510, 0x45E2, 0x4612, 0x466F, 0x4699]),
    (7, 0x452F): ("dw", [0x4549, 0x4549, 0x4549, 0x4572, 0x4556, 0x4549,
                          0x4549, 0x4549, 0x456E, 0x4583, 0x45AB, 0x4779]),
    (16, 0x4DF5): ("db", [0x00, 0x01, 0x01, 0x00, 0x01, 0x01, 0x01, 0x00,
                          0x00, 0x00, 0x00, 0x00, 0x00]),
}

# Meaningful entry labels: (bank, addr) -> name. Roles are from the
# code (call sites / the instructions themselves) or from live
# gb_wramdump/gb_watch evidence; none is more than that.
LABELS = {
    # --- bank 8 ---
    (8, 0x4000): "Bank8_4000",    # per-frame entry (called from bank 0
                                  # $087d/$0903 via $2a0a); copies
                                  # $c203-$c20a into $dd51-$dd54, then
                                  # $4022 builds the $c117 records
    (8, 0x4022): "Bank8_4022",    # zeroes $c117-$c155, runs the four
                                  # corner blocks (each: map pointer
                                  # + even builder + odd builder)
    (8, 0x41B8): "Bank8_41B8",    # even builder, corner 1 (rec0)
    (8, 0x42AC): "Bank8_42AC",    # odd builder, corner 1 (rec1)
    (8, 0x4375): "Bank8_4375",    # even builder, corner 2 (rec2)
    (8, 0x446D): "Bank8_446D",    # odd builder, corner 2 (rec3)
    (8, 0x453A): "Bank8_453A",    # even builder, corner 3 (rec4)
    (8, 0x4645): "Bank8_4645",    # odd builder, corner 3 (rec5)
    (8, 0x4733): "Bank8_4733",    # even builder, corner 4 (rec6)
    (8, 0x4843): "Bank8_4843",    # odd builder, corner 4 (rec7)
    (8, 0x4936): "Bank8_4936",    # $fe class check (from $41b8)
    (8, 0x495B): "Bank8_495B",    # rec8 sampler (post-key, [$dd18]==$0a
                                  # or [$ff94] bit 7)
    (8, 0x4A04): "Bank8_4A04",    # ($82,$37) cell finder; called via
                                  # bank-0 $2b24 from bank 7 $6331
                                  # (post-key scan); writes the found
                                  # pointer to $c156-$c159, or 0
    (8, 0x4AA0): "Bank8_4AA0",    # $c1f4/$c1f9 lookup (odd builders)
    # --- bank 7 ---
    (7, 0x41E9): "Bank7_41E9",    # [$dd1a]==1: checks $c117/$c11e bit 7,
                                  # call $6960, [$dd21]=$1e on $1f/$20
    (7, 0x4200): "Bank7_4200",    # fall-through from $41e9: [$dd22]==
                                  # $20 -> [$dd21]=$1e, else jp $4016
    (7, 0x420D): "Bank7_420D",    # 16-bit compares on $dd29/$dd24-$dd28
    (7, 0x4237): "Bank7_4237",    # 16-bit position/velocity math
    (7, 0x4269): "Bank7_4269",    # [$dd1a]==2: checks $c117/$c11e bit 7,
                                  # call $6960, [$c830]/[$c835]=$0d
    (7, 0x42CC): "Bank7_42CC",    # [$dd1a]==3: checks $c125/$c12c bits
                                  # $c0, [$dd2a]/[$dd1a]=4, [$dd47]=9
    (7, 0x4361): "Bank7_4361",    # [$dd18]==9: reload $7394->$dd59,
                                  # set 6 [$ff93]; $7343/$734b table
    (7, 0x43C6): "Bank7_43C6",    # 16-bit position/velocity math
    (7, 0x43D9): "Bank7_43D9",    # [$dd18]==$0a (key) -> [$dd21]=$39,
                                  # call $2b30 (bank $0a $7816),
                                  # [$dd1c]=$83; ==$03 -> $2b3c/$4794
    (7, 0x44CB): "Bank7_44CB",    # [$ff93] bit 5 / [$dd1f] dispatch
                                  # preamble (falls into $44e4)
    (7, 0x44E4): "Bank7_44E4",    # [$dd1a]==4: [$dd1f] dispatcher via
                                  # the $4506 table
    (7, 0x4510): "Bank7_4510",    # [$dd18] dispatcher via the $452f
                                  # table (dec [$dd2a] first)
    (7, 0x4549): "Bank7_4549",    # $452f entries 0,1,2,5,6,7
    (7, 0x4556): "Bank7_4556",    # $452f entry 4
    (7, 0x456E): "Bank7_456E",    # $452f entry 8
    (7, 0x4572): "Bank7_4572",    # $452f entry 3
    (7, 0x4583): "Bank7_4583",    # $452f entry 9
    (7, 0x45A0): "Bank7_45A0",    # [$dd1c] selector ([$ff94] bit 7)
    (7, 0x45AB): "Bank7_45AB",    # $452f entry 10: [$c125]==$52 check
    (7, 0x45C8): "Bank7_45C8",    # [$dd1c] write + [$ff93] bit 5 branch
    (7, 0x45D9): "Bank7_45D9",    # [$ff91] mask ([$dd1c] selector tail)
    (7, 0x45E2): "Bank7_45E2",    # $4506 entry 1: [$ff91] bit 2 branch
    (7, 0x4612): "Bank7_4612",    # $4506 entry 2: [$c21b] counter
    (7, 0x4629): "Bank7_4629",    # [$dd18]==$0b -> call $64ba,
                                  # ==$0c -> call $6551
    (7, 0x466F): "Bank7_466F",    # $4506 entry 3: SECOND hStateTimer=12
                                  # writer ([$dd1f]==3, [$ff91] bit 2)
    (7, 0x46B6): "Bank7_46B6",    # $46bd tail: dec [hl], jp z $4629
    (7, 0x46BD): "Bank7_46BD",    # [$dd1a]==5: checks $c125/$c12c bits
                                  # $c0, [$dd1f]=2, [$dd21]=$18,
                                  # [$c830]/[$c835]=$35
    (7, 0x470D): "Bank7_470D",    # 16-bit position/velocity math
    (7, 0x4750): "Bank7_4750",    # [$dd4b] countdown -> [$dd1a]=5
    (7, 0x4769): "Bank7_4769",    # [$dd1a]==6: dec [$dd4b], [$dd1a]=5,
                                  # res 1 [$ff91]
    (7, 0x4779): "Bank7_4779",    # $452f entry 11: [$c213]=3,
                                  # [$dd21]=$31, res 2/3 [$ff91]/[$ff92]
    (7, 0x7D96): "Bank7_7D96",    # handler-7 (parasol) chain: $7de6,
                                  # $33a7, $164c, $c72f slot, $7e07,
                                  # score +2 via $0e29
    (7, 0x7DBE): "Bank7_7DBE",    # handler-17 (key) chain: same shape
                                  # as $7d96 (slot byte 2, [$d9a2]+4)
    (7, 0x7DE6): "Bank7_7DE6",    # shared 2x2 cell clear (from $7d96
                                  # and $7dbe)
    # --- bank 16 ($10) ---
    (16, 0x4AF0): "Bank16_4AF0",  # per-frame $c117-record scanner
                                  # (from $0868); clears stale records
                                  # and triggers Mario actions
    (16, 0x4B90): "Bank16_4B90",  # $c148/$c14b/$9d branch; no direct
                                  # entry found in bank 16 (possibly a
                                  # dead duplicate of the $4b43 branch)
    (16, 0x4C0B): "Bank16_4C0B",  # record-apply continuation
    (16, 0x4C6D): "Bank16_4C6D",  # record-apply continuation
    (16, 0x4D9B): "Bank16_4D9B",  # record-clear continuation
    (16, 0x4E02): "Bank16_4E02",  # [$dd18]==2 path ([$dd1d] dispatch)
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
    out = [f"; Slice 11: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice11.py from the ROM bytes via",
           "; tools/gb_rd.py (recursive descent, not mgbdis' linear",
           "; sweep). Byte-match (`make`) arbitrates.",
           f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]']
    jr_targets = jr_targets_in(instrs, lo, hi)
    # Every in-carve jump target must be a decoded instruction start;
    # anything else means the walk missed a path -- fail loudly.
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                and lo <= tgt <= hi and tgt not in instrs:
            print(f"ERROR: bank {bank} ${addr:04x} {text} targets "
                  f"${tgt:04x}, not a decoded instruction",
                  file=sys.stderr)
            sys.exit(1)
    # Every rst-$08 table entry inside the carve must be decoded code
    # (WRAM entries, which cannot be decoded, are the only exception).
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
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def emit_bank8_tables(rom):
    """The $4aed/$4b23 pointer tables (one overlapping dw blob) and
    the $5409 4-byte class-record table (256 records)."""
    # $4aed (32 dw) and $4b23 (32 dw) overlap at $4b23-$4b2c; the
    # shared words agree, so emit $4aed-$4b62 as one dw blob.
    base = file_off(8, 0x4AED)
    words = [rom[base + 2 * i] | (rom[base + 2 * i + 1] << 8)
             for i in range((0x4B63 - 0x4AED) // 2)]
    assert words[0] == 0x4B55 and words[27] == 0x4F2C, \
        "bank 8 $4aed/$4b23 tables are not the expected words"
    out = ["; Slice 11: Bank 8 $4aed/$4b23 class-lookup pointer tables.",
           "; $4aed is indexed by (tile & $1f) from the even builders",
           "; ($41b8 family); $4b23 the same from the odd builders",
           "; ($42ac family). The two tables overlap at $4b23-$4b2c",
           "; and the shared words agree, so they are emitted as one",
           "; dw blob. Entries are byte-table bases (some in ROM0,",
           "; e.g. $1902); the byte at (base + subtype) is the class.",
           'SECTION "Bank 8 $4aed/$4b23 tables", ROMX[$4aed], BANK[8]']
    for i, w in enumerate(words):
        out.append(f"    {'dw $%04x' % w:<48} ; ${0x4AED + 2 * i:04x}")
    # $5409: 256 4-byte class records, indexed by class * 4.
    base = file_off(8, 0x5409)
    recs = rom[base:base + 1024]
    assert recs[:4] == bytes([0x06, 0x03, 0x02, 0x04]), \
        "bank 8 $5409 class table does not start with 06 03 02 04"
    out += ["",
            "; Slice 11: Bank 8 $5409 4-byte class records (256 entries).",
            "; Indexed by class * 4 from the $41b8-family builders.",
            "; $ff = skip, $fe = $4936 check, $fd = $57d5/$57e4 remap.",
            "; $57d5/$57e4/$5795 are views into this table (records",
            "; 243, 244 and 227), not separate tables.",
            'SECTION "Bank 8 $5409 class table", ROMX[$5409], BANK[8]']
    for j in range(0, len(recs), 8):
        chunk = recs[j:j + 8]
        out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def main():
    rom = open(ROM, "rb").read()
    # Verify the in-carve tables against the ROM bytes.
    for (bank, addr), (kind, vals) in TABLES.items():
        base = file_off(bank, addr)
        if kind == "dw":
            got = [rom[base + 2 * i] | (rom[base + 2 * i + 1] << 8)
                   for i in range(len(vals))]
        else:
            got = list(rom[base:base + len(vals)])
        assert got == vals, \
            f"bank {bank} table at ${addr:04x} mismatch: {got} != {vals}"
    # Group carves by outfile, in file order.
    by_file = {}
    for bank, lo, hi, title, outfile, seeds in CARVES:
        reached, rst08, notes = walk(bank, seeds)
        # The walk follows calls/jumps outside the carve; keep only
        # instructions inside [lo, hi] for emission.
        instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
        for n in notes:
            print("note:", n, file=sys.stderr)
        by_file.setdefault(outfile, []).append(
            (bank, lo, hi, title, instrs, rst08))
    for outfile, carves in by_file.items():
        parts = []
        for bank, lo, hi, title, instrs, rst08 in carves:
            parts.append(emit_carve(rom, bank, lo, hi, title, instrs,
                                    rst08))
        if outfile == "src/banks/bank8.asm":
            parts.append(emit_bank8_tables(rom))
        with open(outfile, "w") as f:
            f.write("\n".join(parts))
        print(f"wrote {outfile} ({sum(len(p) for p in parts)} bytes)")


if __name__ == "__main__":
    main()
