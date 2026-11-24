#!/usr/bin/env python3
"""Slice-12 generator: carve the $6331 post-key scan and its home
routine (bank 7 $627b-$63c3 + $63f4-$643e, the $4827 [$dd18] table,
$664e + $714c callees, $643f record template), the bank-8
$4b63-$5408 class byte tables, and the two timer-tick song/sound
tables (bank 2 $47fc, bank 3 $48f1).

Why this carve (see PROGRESS.md slice 12):
  * Bank 7 $480e (slice 5) dispatches on [$dd18] via the $4827
    table (13 dw, indices 0-12); entry $0a -> $627b. $627b is the
    post-$5b-trigger per-frame routine: it counts [$dd3c] down and
    at 0 jumps to $63f4 (clears [$dd18], [$c82e]/[$c835]=3); every
    6 frames (via [$c210]) it toggles [$c21c]; when [$ff94] bit 5
    is set and [$c21c] is set, it counts [$c20d] down, and at 0
    calls bank-0 $2b24 (bank 8 $4a04) to find an ($82,$37) cell
    near Mario. On a hit ($6334-$63a3) it clears the cell, calls
    $714c (map pointer -> tile coords in BC), copies the 20-byte
    $643f template to $c1ab, calls $2b1a (bank $0a $7b6c) and
    $6f06, sets [$c20d]=3, [$c830]/[$c835]=$5f, and scores +1 via
    $0e29. No ($82,$37) cell exists in 1-1's map, so the path is
    inert there. $664e (called from $62c2 when rec8's byte is
    $22/$23) scores +3, writes a $c20e record, saves hStateTimer
    to [$c70b], sets hStateTimer=$10 (16), and jp $6f40.
  * Bank 8 $4b63-$5408: the class byte tables the $4aed/$4b23
    pointer tables (slice 11) point at. A table maps a map-cell
    subtype byte -> class index; the class record is at
    $5409 + class*4. Runs are delimited by the next table base
    from those pointer tables (distinct bases $4b5d..$531f);
    the $4b63-$4bf0 run is the tail of the $4b5d table (its
    head $4b5d-$4b62 is already emitted as the $4b23 dw tail).
  * Bank 2 $47fc: 119-entry sound-definition table. The bank-2
    tick ($45a9) reads [$c835]; nonzero -> drain the 8-slot
    request queue $c82d-$c834 via $4677. A slot value V indexes
    this table at (V-1); the entry points at an 8-byte record
    of four (lo,hi) channel-data pairs ($df0e-$df11 channels).
    $44 (all pickups) -> entry 67 -> $5480; $5f -> entry 94 ->
    $4feb; $19 -> entry 24 -> $5fa7; $03 -> entry 2 -> $59c1.
    All 119 entries verified: targets in $4904-$6196, every
    record pair hi-byte $00 or $40-$7f.
  * Bank 3 $48f1: 41-entry song table (song index < $29).
    The bank-3 tick ($45a9) reads [$c838] ($80 = stop),
    [$c836]/[$c837] (song request/current); song V indexes
    this table at (V-1) and the song data goes to $df07/$df12.
    All 41 entries verified: targets in $454b-$764f.

Regenerate with: python3 tools/gen_slice12.py
Outputs: src/bank7slice12.asm, src/bank2slice12.asm,
src/bank3slice12.asm (new files); appends the bank-8 class
tables to src/bank8.asm. Regenerates src/banks.asm via
tools/gen_banks.py after updating its CARVED map. The
outputs are CHECKED IN; rerun after changing the config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile, seeds)
CARVES = [
    (7, 0x4827, 0x4840, "Bank 7 $4827 [$dd18] dispatch table",
     "src/bank7slice12.asm", []),
    (7, 0x627B, 0x63C3, "Bank 7 $627b-$63c3 post-trigger routine "
     "($6331 scan home)", "src/bank7slice12.asm", [0x627B]),
    (7, 0x63F4, 0x643E, "Bank 7 $63f4-$643e post-trigger expiry",
     "src/bank7slice12.asm", [0x627B]),
    (7, 0x643F, 0x644C, "Bank 7 $643f record template (14 bytes here)",
     "src/bank7slice12.asm", []),
    (7, 0x664E, 0x66C9, "Bank 7 $664e-$66c9 rec8 $22/$23 handler",
     "src/bank7slice12.asm", [0x627B]),
    (7, 0x714C, 0x7167, "Bank 7 $714c-$7167 map-pointer to tile coords",
     "src/bank7slice12.asm", [0x627B]),
    (2, 0x47FC, 0x48E9, "Bank 2 $47fc sound-definition table (119)",
     "src/bank2slice12.asm", []),
    (3, 0x48F1, 0x4942, "Bank 3 $48f1 song table (41)",
     "src/bank3slice12.asm", []),
]

# In-carve tables: (bank, addr) -> ("dw", [values]) or ("db", [bytes]).
# Values read from the ROM in main() and asserted against it.
TABLES = {
    (7, 0x4827): ("dw", [0x4841, 0x4E8B, 0x517C, 0x5673, 0x58DA, 0x59FF,
                         0x5669, 0x6B09, 0x5D6E, 0x5EA1, 0x627B, 0x644D,
                         0x64DB]),
}

# Meaningful entry labels: (bank, addr) -> name.
LABELS = {
    (7, 0x4827): "Bank7_DD18Table",  # $480e dispatches on [$dd18] here
    (7, 0x627B): "Bank7_627B",       # [$dd18]==$0a: post-$5b-trigger
                                     # per-frame routine; $6331 calls
                                     # $2b24 (bank 8 $4a04 ($82,$37)
                                     # scan) when [$c20d] hits 0
    (7, 0x63F4): "Bank7_63F4",       # [$dd3c]==0 expiry: clears
                                     # [$dd18], [$c82e]/[$c835]=3
    (7, 0x643F): "Bank7_643F",       # 20-byte record template (14
                                     # bytes emitted here; last 6 are
                                     # entry 11's dispatch head, slice 13)
    (7, 0x664E): "Bank7_664E",       # rec8 byte $22/$23: score +3,
                                     # $c20e record write, timer 16
    (7, 0x714C): "Bank7_714C",       # map pointer (DE) -> tile
                                     # coords in BC
    (2, 0x47FC): "Bank2_SoundTable",  # sound defs, indexed by (V-1)
    (3, 0x48F1): "Bank3_SongTable",   # song ptrs, indexed by (V-1)
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
    out = [f"; Slice 12: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/gen_slice12.py from the ROM bytes via",
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


def emit_bank8_class_tables(rom):
    """Bank 8 $4b63-$5408 class byte tables, as db runs delimited by
    the next table base from the $4aed/$4b23 pointer tables."""
    # Read both pointer tables fresh from the ROM.
    bases = set()
    for tbl_base in (0x4AED, 0x4B23):
        off = file_off(8, tbl_base)
        for i in range(32):
            w = rom[off + 2 * i] | (rom[off + 2 * i + 1] << 8)
            if 0x4B63 <= w < 0x5409:
                bases.add(w)
    bases = sorted(bases)
    # $4b5d is below the carve start ($4b63); its table's tail is
    # the first run. The first in-range base is $4bf1.
    assert bases[0] == 0x4BF1 and bases[-1] == 0x531F, bases
    # Runs: the $4b63-$4bf0 run is the tail of the $4b5d table;
    # each later run starts at its base and ends at the next base.
    runs = [(0x4B63, bases[0])] + [(bases[i], bases[i + 1])
                                   for i in range(len(bases) - 1)]
    runs.append((0x531F, 0x5409))
    assert runs[0][0] == 0x4B63 and runs[-1][1] == 0x5409
    assert all(runs[i][1] == runs[i + 1][0]
               for i in range(len(runs) - 1)), runs
    out = ["; Slice 12: Bank 8 $4b63-$5408 class byte tables.",
           "; Generated by tools/gen_slice12.py from the ROM bytes.",
           "; Each run is one subtype->class table from the $4aed/$4b23",
           "; pointer tables (slice 11): the byte at (base + subtype)",
           "; is the class index, and the class record is at",
           "; $5409 + class*4. Runs are delimited by the next table",
           "; base. The $4b63-$4bf0 run is the tail of the $4b5d",
           "; table (its head $4b5d-$4b62 is the $4b23 dw tail,",
           "; already emitted as dw in this file). Byte-match",
           "; (`make`) arbitrates.",
           'SECTION "Bank 8 $4b63-$5408 class tables", ROMX[$4b63], '
           'BANK[8]']
    for lo, hi in runs:
        base = lo if lo != 0x4B63 else 0x4B5D
        out.append(f"Bank8_ClassTable_{base:04X}::")
        for j in range(lo, hi, 8):
            chunk = rom[file_off(8, j):file_off(8, min(j + 8, hi))]
            out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def read_dw_table(rom, bank, addr, count):
    off = file_off(bank, addr)
    return [rom[off + 2 * i] | (rom[off + 2 * i + 1] << 8)
            for i in range(count)]


def main():
    rom = open(ROM, "rb").read()
    # Verify the hand-listed tables against the ROM bytes.
    for (bank, addr), (kind, vals) in TABLES.items():
        base = file_off(bank, addr)
        if kind == "dw":
            got = [rom[base + 2 * i] | (rom[base + 2 * i + 1] << 8)
                   for i in range(len(vals))]
        else:
            got = list(rom[base:base + len(vals)])
        assert got == vals, \
            f"bank {bank} table at ${addr:04x} mismatch: {got} != {vals}"
    # Verify the bank-2 sound table: 119 entries, targets in-window,
    # every record an 8-byte set of 4 (lo,hi) pairs with hi $00 or
    # $40-$7f. The first word after the table ($48ea) is $0801 --
    # not a pointer, so the table ends at 119 entries.
    snd = read_dw_table(rom, 2, 0x47FC, 119)
    assert all(0x4000 <= t <= 0x7FF7 for t in snd), "sound table target"
    for i, t in enumerate(snd):
        rec = rom[file_off(2, t):file_off(2, t) + 8]
        for p in range(4):
            hi = rec[2 * p + 1]
            assert hi == 0 or 0x40 <= hi < 0x80, \
                f"sound table entry {i} -> ${t:04x} pair {p} hi ${hi:02x}"
    assert read_dw_table(rom, 2, 0x48EA, 1)[0] == 0x0801
    TABLES[(2, 0x47FC)] = ("dw", snd)
    # Verify the bank-3 song table: 41 entries (song < $29), all
    # targets in-window.
    song = read_dw_table(rom, 3, 0x48F1, 41)
    assert all(0x4000 <= t <= 0x7FFF for t in song), "song table target"
    TABLES[(3, 0x48F1)] = ("dw", song)
    # The $643f template is emitted as data (14 bytes here; the
    # record is 20 bytes, copied to $c1ab by the $6334 scan-hit path,
    # but its last 6 bytes ($644d-$6452) are the head of [$dd18]
    # entry 11's dispatch routine, emitted as code in slice 13 --
    # see tools/gen_slice13.py. The 20-byte copy still reads the
    # same 20 bytes.)
    TABLES[(7, 0x643F)] = ("db", list(rom[file_off(7, 0x643F):
                                          file_off(7, 0x643F) + 14]))
    # Walk bank 7 once from $627b; keep only instructions inside
    # each code span, and require each span to be fully covered
    # (no db gaps inside code).
    reached, rst08, notes = walk(7, [0x627B])
    for n in notes:
        print("note:", n, file=sys.stderr)
    by_file = {}
    for bank, lo, hi, title, outfile, seeds in CARVES:
        if bank == 7 and seeds:
            instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
            covered = set()
            for a, (ln, *_r) in instrs.items():
                covered.update(range(a, a + ln))
            assert covered == set(range(lo, hi + 1)), \
                f"bank 7 ${lo:04x}-${hi:04x}: uncovered bytes " \
                f"{sorted(set(range(lo, hi + 1)) - covered)[:8]}"
            assert not rst08, "unexpected rst $08 in bank-7 $627b walk"
        else:
            instrs = {}
        by_file.setdefault(outfile, []).append(
            (bank, lo, hi, title, instrs, rst08))
    for outfile, carves in by_file.items():
        parts = []
        for bank, lo, hi, title, instrs, rst08 in carves:
            parts.append(emit_carve(rom, bank, lo, hi, title, instrs,
                                    rst08))
        with open(outfile, "w") as f:
            f.write("\n".join(parts))
        print(f"wrote {outfile} ({sum(len(p) for p in parts)} bytes)")
    # Append the bank-8 class tables (do not overwrite slice 11).
    with open("src/bank8.asm") as f:
        cur = f.read()
    marker = 'SECTION "Bank 8 $4b63-$5408 class tables"'
    assert marker not in cur, "bank8 class tables already present"
    with open("src/bank8.asm", "a") as f:
        f.write("\n" + emit_bank8_class_tables(rom))
    print("appended bank-8 class tables to src/bank8.asm")


if __name__ == "__main__":
    main()
