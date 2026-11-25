#!/usr/bin/env python3
"""Slice-15 generator: carve the $2a0a per-frame dispatch system.

  * Decimal bank 10 ($0a, new file src/banks/bank0a.asm -- NOT src/banks/bank10.asm,
    which is hex bank $10 = decimal 16, the death-path bank):
    $7730-$7814 (the record state-machine pre-dispatch, incl. $77d4 /
    $77f2 continuations), $7815 (lone 1-byte ret), $7816-$787c (the
    spawn routine, reached via the bank-0 $2b30 trampoline), the two
    20-byte spawn templates $787d / $788b (one $787d-$789e section --
    the two overlap on $788b-$7890),
    $7c57-$7caf (the $c0c7-list insert/remove), $7e50-$7ead (the 94-byte
    $7730 transition table, db), $7eae-$7f43 (25 6-byte transition
    records, db), $759a-$75af (the [$dd18] writer tail), and the three
    remaining decimal-bank-10 [$dd18] spans $4ff2-$4ffe, $5021-$5084,
    $5c4f-$5cf7 (the last holds the $5c97/$5c4f timer-13 routine and
    its $5cd8 $2b48-entry-53 handler, plus the $5cf8 8-entry dw table).
  * Bank 8 (new file src/banks/bank8slice15.asm): the $2a0a dispatch's
    bank-8 destinations -- $5e37-$5efd (the record linker, via the
    bank-0 $2b0e trampoline) + $5efe-$5f5b (its 94-byte B table, db),
    $5f5c-$5f6a, $609d-$60e8, $6110-$611e, $6274-$6282, $63b5-$63ef,
    $6443-$6466 + $6467-$646c (6-entry dw table) + $6473-$6667 (incl.
    $65fc) + $6668 (1-byte ret), $67bd-$67cb, $68b8-$68ee, $69af-$69bd,
    $6a25-$6a33, $6abb-$6ac9, $6d8a-$6da9 + $6daa-$6db5 (6-entry dw
    table) + $6db6-$6f64 (incl. $6ecd / $6f26, the timer-13 setter,
    and $6f56) + $6f65-$6f7a (11-entry dw table) + $6f7b-$7291,
    $7310-$74f3 (bare ret + the $7311 sprite-frame routine),
    $7526-$7587 (the $2a0a per-frame tail) + $77da-$7819 (32-entry dw
    table), $7602-$7629 + $7685-$76b5 (shared subroutines, jp'd to
    from $5ff6/$651f/$72d1 and $7600), $76e3-$7740 (94-byte table, db)
    + $7741-$7746 (3-entry dw table) + $7747-$77d9 (sprite triple
    tables, db).
  * Bank 0: splice the $2b48-$2c61 $2a0a dispatch table (94 entries x
    3 bytes: bank, lo, hi) into src/banks/bank0slice3.asm, replacing the
    mis-decoded garbage lines (the table is currently emitted as
    `ld a,[bc]` / `ld [$5f5c],sp` etc.). The splice is idempotent:
    if the $2b48 line is already a db line, it is skipped.

Why this carve (see PROGRESS.md slice 15): $2a0a runs every frame in
state 16 and dispatches each $c200 record either to bank 10 $7730
([$c103] bit 3 clear) or via the bank-0 $2b48 table (bit 3 set).
$7730 is a pre-dispatch that can rewrite [$c105] (the $2b48 index)
via the $7e50/$7eae tables before the real handler runs. The bank-8
$6d8a handler (entry 34) and the bank-10 $5cd8 handler (entry 53)
are the two timer-13 setters: both gate on [$c109] bit 3 and both end
in the [$dd2b]=$09, [$dd2c]=$0b, timer=13 tail. No [$c105]=34/53
record exists in 1-1 (live values {0,1,2,3,6,7,32,45,72}), so timer
13 is unreachable in 1-1; and timer 13's body $0968 runs bank-16
$5a11, which sets only timers 1/12 -- timer 13 resolves to resume
or death, never to the clear chain (23/26/33/42).

Regenerate with: python3 tools/generators/gen_slice15.py
Outputs: src/banks/bank0a.asm, src/banks/bank8slice15.asm (new files), and the
$2b48 splice in src/banks/bank0slice3.asm (in place).
Also update tools/generators/gen_banks.py CARVED (bank 8 ranges, new key 10)
and regenerate src/banks.asm; add INCLUDEs to src/main.asm.
The outputs are CHECKED IN; rerun after changing the config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
BANK0_SLICE3 = "src/banks/bank0slice3.asm"

# (bank, lo, hi, section title, outfile, seeds) -- hi inclusive.
CARVES = [
    # ---- decimal bank 10 ($0a) ----
    (10, 0x4FF2, 0x4FFE, "Bank 10 $4ff2-$4ffe [$dd18] site",
     "src/banks/bank0a.asm", [0x4FF2]),
    (10, 0x5021, 0x5084, "Bank 10 $5021-$5084 [$dd18] site",
     "src/banks/bank0a.asm", [0x5021]),
    (10, 0x5C4F, 0x5CF7, "Bank 10 $5c4f-$5cf7 timer-13 routine + "
     "$5cd8 entry-53 handler", "src/banks/bank0a.asm", [0x5C4F, 0x5C97, 0x5CD8]),
    (10, 0x759A, 0x75AF, "Bank 10 $759a-$75af [$dd18] writer tail",
     "src/banks/bank0a.asm", [0x759A]),
    (10, 0x7730, 0x7814, "Bank 10 $7730-$7814 record pre-dispatch "
     "($77d4/$77f2 continuations)", "src/banks/bank0a.asm",
     [0x7730, 0x77D4, 0x77F2]),
    (10, 0x7816, 0x787C, "Bank 10 $7816-$787c spawn routine",
     "src/banks/bank0a.asm", [0x7816]),
    (10, 0x7C57, 0x7CAF, "Bank 10 $7c57-$7caf $c0c7-list insert/remove",
     "src/banks/bank0a.asm", [0x7C57, 0x7C88]),
    # ---- bank 8 ----
    (8, 0x5E37, 0x5EFD, "Bank 8 $5e37-$5efd record linker",
     "src/banks/bank8slice15.asm", [0x5E37]),
    (8, 0x5F5C, 0x5F6A, "Bank 8 $5f5c-$5f6a $2b48-entry-1 handler",
     "src/banks/bank8slice15.asm", [0x5F5C]),
    (8, 0x609D, 0x60E8, "Bank 8 $609d-$60e8 $6467-entry-2 routine",
     "src/banks/bank8slice15.asm", [0x609D]),
    (8, 0x6110, 0x611E, "Bank 8 $6110-$611e",
     "src/banks/bank8slice15.asm", [0x6110]),
    (8, 0x6274, 0x6282, "Bank 8 $6274-$6282",
     "src/banks/bank8slice15.asm", [0x6274]),
    (8, 0x63B5, 0x63EF, "Bank 8 $63b5-$63ef $6467-entry-4 routine",
     "src/banks/bank8slice15.asm", [0x63B5]),
    (8, 0x6443, 0x6466, "Bank 8 $6443-$6466 $2b48-entry-6 handler",
     "src/banks/bank8slice15.asm", [0x6443]),
    (8, 0x6473, 0x6667, "Bank 8 $6473-$6667 $6467-entry-0 routine "
     "(incl. $65fc)", "src/banks/bank8slice15.asm", [0x6473, 0x65FC]),
    (8, 0x67BD, 0x67CB, "Bank 8 $67bd-$67cb",
     "src/banks/bank8slice15.asm", [0x67BD]),
    (8, 0x68B8, 0x68EE, "Bank 8 $68b8-$68ee proximity trigger",
     "src/banks/bank8slice15.asm", [0x68B8]),
    (8, 0x69AF, 0x69BD, "Bank 8 $69af-$69bd",
     "src/banks/bank8slice15.asm", [0x69AF]),
    (8, 0x6A25, 0x6A33, "Bank 8 $6a25-$6a33",
     "src/banks/bank8slice15.asm", [0x6A25]),
    (8, 0x6ABB, 0x6AC9, "Bank 8 $6abb-$6ac9",
     "src/banks/bank8slice15.asm", [0x6ABB]),
    (8, 0x6D8A, 0x6DA9, "Bank 8 $6d8a-$6da9 $2b48-entry-34 handler",
     "src/banks/bank8slice15.asm", [0x6D8A]),
    (8, 0x6DB6, 0x6F64, "Bank 8 $6db6-$6f64 $6daa routines + $6ecd "
     "timer-13 setter + $6f56 handler", "src/banks/bank8slice15.asm",
     [0x6DB6, 0x6ECD, 0x6F26, 0x6F56]),
    (8, 0x6F7B, 0x7291, "Bank 8 $6f7b-$7291 $6f65-table routines",
     "src/banks/bank8slice15.asm", [0x6F7B]),
    (8, 0x7310, 0x74F3, "Bank 8 $7310-$74f3 bare ret + $7311 "
     "sprite-frame routine", "src/banks/bank8slice15.asm", [0x7310, 0x7311]),
    (8, 0x7526, 0x7587, "Bank 8 $7526-$7587 $2a0a per-frame tail",
     "src/banks/bank8slice15.asm", [0x7526]),
    (8, 0x7602, 0x7629, "Bank 8 $7602-$7629 shared subroutine",
     "src/banks/bank8slice15.asm", [0x7602]),
    (8, 0x7685, 0x76B5, "Bank 8 $7685-$76b5 shared subroutine",
     "src/banks/bank8slice15.asm", [0x7685]),
]

# Meaningful entry labels: (bank, addr) -> name.
LABELS = {
    (10, 0x4FF2): "Bank0A_4FF2",
    (10, 0x5021): "Bank0A_5021",
    (10, 0x5C4F): "Bank0A_5C4F",
    (10, 0x5C97): "Bank0A_5C97",
    (10, 0x5CD8): "Bank0A_5CD8",
    (10, 0x5CF8): "Bank0A_5CF8",
    (10, 0x759A): "Bank0A_759A",
    (10, 0x7730): "Bank0A_7730",
    (10, 0x77D4): "Bank0A_77D4",
    (10, 0x77F2): "Bank0A_77F2",
    (10, 0x7815): "Bank0A_7815",
    (10, 0x7816): "Bank0A_7816",
    (10, 0x787D): "Bank0A_787D",
    (10, 0x788B): "Bank0A_788B",
    (10, 0x7C57): "Bank0A_7C57",
    (10, 0x7C88): "Bank0A_7C88",
    (10, 0x7E50): "Bank0A_7E50",
    (10, 0x7EAE): "Bank0A_7EAE",
    (8, 0x5E37): "Bank8_5E37",
    (8, 0x5EFE): "Bank8_5EFE",
    (8, 0x5F5C): "Bank8_5F5C",
    (8, 0x609D): "Bank8_609D",
    (8, 0x6110): "Bank8_6110",
    (8, 0x6274): "Bank8_6274",
    (8, 0x63B5): "Bank8_63B5",
    (8, 0x6443): "Bank8_6443",
    (8, 0x6467): "Bank8_6467",
    (8, 0x6473): "Bank8_6473",
    (8, 0x65FC): "Bank8_65FC",
    (8, 0x6668): "Bank8_6668",
    (8, 0x67BD): "Bank8_67BD",
    (8, 0x68B8): "Bank8_68B8",
    (8, 0x69AF): "Bank8_69AF",
    (8, 0x6A25): "Bank8_6A25",
    (8, 0x6ABB): "Bank8_6ABB",
    (8, 0x6D8A): "Bank8_6D8A",
    (8, 0x6DAA): "Bank8_6DAA",
    (8, 0x6DB6): "Bank8_6DB6",
    (8, 0x6ECD): "Bank8_6ECD",
    (8, 0x6F26): "Bank8_6F26",
    (8, 0x6F56): "Bank8_6F56",
    (8, 0x6F65): "Bank8_6F65",
    (8, 0x6F7B): "Bank8_6F7B",
    (8, 0x7310): "Bank8_7310",
    (8, 0x7311): "Bank8_7311",
    (8, 0x7526): "Bank8_7526",
    (8, 0x7602): "Bank8_7602",
    (8, 0x7685): "Bank8_7685",
    (8, 0x76E3): "Bank8_76E3",
    (8, 0x7741): "Bank8_7741",
    (8, 0x7747): "Bank8_7747",
    (8, 0x77DA): "Bank8_77DA",
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
    out = [f"; Slice 15: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice15.py from the ROM bytes via",
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


def emit_db(rom, bank, lo, hi, title, note=None):
    """A raw-byte range, 8 bytes per db line, with a section header."""
    label = LABELS.get((bank, lo))
    out = [f"; Slice 15: {title} -- bank {bank} ${lo:04x}-${hi:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/generators/gen_slice15.py; bytes read straight "
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


def emit_dw_table(rom, bank, lo, entries, title, expected=None, note=None):
    """A dw table: `entries` (addr, comment) pairs, verified against
    the ROM bytes when `expected` (list of values) is given."""
    label = LABELS.get((bank, lo))
    out = [f"; Slice 15: {title} -- bank {bank} ${lo:04x}-"
           f"${lo + 2 * len(entries) - 1:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/generators/gen_slice15.py; values read straight "
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


def splice_bank0_table(rom):
    """Replace the mis-decoded $2b48-$2c61 garbage lines in
    src/banks/bank0slice3.asm with the real 94x3-byte $2b48 dispatch table.
    Idempotent: if the $2b48 line is already a db line, skip."""
    with open(BANK0_SLICE3) as f:
        lines = f.read().splitlines(keepends=True)
    i48 = next(i for i, ln in enumerate(lines) if "; $2b48" in ln)
    i62 = next(i for i, ln in enumerate(lines) if "; $2c62" in ln)
    if lines[i48].strip().startswith("db "):
        print("bank0 $2b48 splice: already done, skipping")
        return
    assert "ld a, [bc]" in lines[i48], \
        f"unexpected $2b48 line: {lines[i48]!r}"
    assert i62 - i48 == 237, \
        f"splice range is {i62 - i48} lines, expected 237"
    assert lines[i62 - 1].strip().endswith("; $2c60"), \
        f"last garbage line: {lines[i62 - 1]!r}"
    entries = []
    for i in range(94):
        a = 0x2B48 + 3 * i
        b0 = rom[file_off(0, a)]
        blo = rom[file_off(0, a + 1)]
        bhi = rom[file_off(0, a + 2)]
        entries.append((b0, blo | (bhi << 8)))
    # Spot-checks against the hand-walked table (slice 15 notes).
    checks = {0: (0x0A, 0x47A3), 1: (0x08, 0x5F5C), 3: (0x08, 0x7310),
              6: (0x08, 0x6443), 34: (0x08, 0x6D8A), 37: (0x08, 0x6F56),
              53: (0x0A, 0x5CD8), 63: (0x0A, 0x705F), 64: (0x0A, 0x4000),
              65: (0x0A, 0x41C2), 66: (0x0A, 0x33E3), 67: (0x0A, 0x33EF),
              93: (0x1F, 0x7BF6)}
    for idx, want in checks.items():
        assert entries[idx] == want, \
            f"$2b48 entry {idx}: {entries[idx]} != {want}"
    assert rom[file_off(0, 0x2C62)] == 0xF0, "byte after table is not $f0"
    new = ["; Slice 15: the $2a0a $2b48 dispatch table -- 94 entries x "
           "3 bytes (bank, lo, hi). Was mis-decoded as code\n",
           "; (ld a,[bc] / ld [$5f5c],sp ...) in bank0slice3.asm; "
           "carved as data here. Total 282 bytes, $2b48-$2c61.\n"]
    for i, (bank, addr) in enumerate(entries):
        new.append(f"    db ${bank:02x}, ${addr & 0xff:02x}, "
                   f"${addr >> 8:02x}  ; $2b48 entry {i} -> "
                   f"bank ${bank:02x} ${addr:04x}\n")
    lines[i48:i62] = new
    with open(BANK0_SLICE3, "w") as f:
        f.writelines(lines)
    print(f"bank0 $2b48 splice: replaced {i62 - i48} garbage lines "
          f"with {len(new)} table lines")


def main():
    rom = open(ROM, "rb").read()
    seeds8 = [0x5E37, 0x5F5C, 0x609D, 0x6110, 0x6274, 0x63B5, 0x6443,
              0x6473, 0x6495, 0x6646, 0x67BD, 0x68B8, 0x69AF, 0x6A25,
              0x6ABB, 0x6D8A, 0x6DB6, 0x6E4D, 0x6E6A, 0x6EA1, 0x6EC4,
              0x6ECC, 0x6F56, 0x6F7B, 0x6FE1, 0x707A, 0x7081, 0x70A6,
              0x70FF, 0x7198, 0x71AC, 0x71CB, 0x7201, 0x7215, 0x7310,
              0x7311, 0x7526, 0x7602, 0x7685]
    seeds10 = [0x4FF2, 0x5021, 0x5C4F, 0x5C97, 0x5CD8, 0x759A, 0x7730,
               0x77D4, 0x77F2, 0x7816, 0x7C57, 0x7C88]
    reached8, rst08_8, notes8 = walk(8, seeds8)
    reached10, rst08_10, notes10 = walk(10, seeds10)
    for n in notes8 + notes10:
        print("note:", n, file=sys.stderr)
    print(f"walk bank 8: {len(reached8)} instrs; "
          f"bank 10: {len(reached10)} instrs", file=sys.stderr)
    assert not rst08_8 and not rst08_10, "unexpected rst $08 in walk"
    by_file = {}
    for bank, lo, hi, title, outfile, _seeds in CARVES:
        reached = reached8 if bank == 8 else reached10
        instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
        covered = set()
        for a, (ln, *_r) in instrs.items():
            covered.update(range(a, a + ln))
        assert covered == set(range(lo, hi + 1)), \
            f"bank {bank} ${lo:04x}-${hi:04x}: uncovered bytes " \
            f"{sorted(set(range(lo, hi + 1)) - covered)[:8]}"
        by_file.setdefault(outfile, []).append(
            (bank, lo, hi, title, instrs, {}))

    # ---- bank 10 data carves (tables / templates / gap bytes) ----
    b10_data = []
    # $7815: a lone 1-byte ret ($c9) between the $77f2 routine (which
    # ends with jp $2a59 at $7812-$7814) and the $7816 spawn routine.
    # The walk does not reach it; it is emitted as a manual ret like
    # bank 8's $6668 below. (An earlier read of $7813-$7815 as gap
    # bytes `59 2a c9` was wrong: $7813/$7814 are the jp's operands.)
    assert rom[file_off(10, 0x7815)] == 0xC9, "bank 10 $7815 is not $c9"
    b10_data.append(
        "; Slice 15: Bank 10 $7815 1-byte ret -- between the $77f2\n"
        "; routine (jp $2a59 at $7812-$7814) and the $7816 spawn\n"
        "; routine. Verified byte $c9; no control flow reaches it.\n"
        'SECTION "Bank 10 $7815 lone ret", ROMX[$7815], BANK[10]\n'
        "Bank0A_7815::\n"
        "    ret                                              ; $7815\n")
    # The two spawn templates OVERLAP: template A starts $787d and
    # template B starts $788b, only 14 bytes later, but each is 20
    # bytes long -- so bytes $788b-$7890 are shared (B's head is A's
    # tail). They cannot be two RGBDS sections (fixed-address sections
    # may not overlap), so emit one $787d-$789e section with both
    # entry labels.
    out = ["; Slice 15: Bank 10 $787d-$789e spawn templates -- bank 10 "
           "$787d-$789e.",
           "; Template A at $787d, template B at $788b, 20 bytes each, "
           "chosen by [$ff94] bit 5; $7816 copies the chosen one to "
           "$c1ab via $106e. Bytes $788b-$7890 are shared.",
           "; Generated by tools/generators/gen_slice15.py; bytes read straight "
           "from the ROM.",
           'SECTION "Bank 10 $787d-$789e spawn templates", '
           'ROMX[$787d], BANK[10]',
           "Bank0A_787D::"]
    addr = 0x787D
    while addr <= 0x789E:
        if addr == 0x788B:
            out.append("Bank0A_788B::")
        chunk = [rom[file_off(10, a)] for a in
                 range(addr, min(addr + 8, 0x789F))]
        out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
        addr += len(chunk)
    b10_data.append("\n".join(out) + "\n")
    # $5cf8: the $5cd8 handler's [$c10a] table. 8 entries; 4/5 are
    # $0000 (dead slots -- [$c10a] is never 4/5 for this handler);
    # 0-3/6-7 point into the uncarved $5d08-$5e97 region.
    b10_data.append(emit_dw_table(
        rom, 10, 0x5CF8,
        [(0x5CF8 + 2 * i, f"[$c10a]={i}") for i in range(8)],
        "Bank 10 $5cf8-$5d07 [$c10a] table (entry-53 handler)",
        expected=[0x5D08, 0x5D48, 0x5D86, 0x5D9F, 0x0000, 0x0000,
                  0x5E88, 0x5E97],
        note="Entries 0-3/6-7 point into uncarved $5d08-$5e97; "
             "entries 4-5 are $0000 dead slots."))
    # $7e50: the $7730 transition table, 94 bytes, values 0-24 (a
    # $7eae record index; 0 is the common default). No $ff sentinel
    # in this table -- the $ff "don't change" markers live inside
    # the $7eae records themselves.
    t7e50 = [rom[file_off(10, a)] for a in range(0x7E50, 0x7EAE)]
    assert len(t7e50) == 94 and max(t7e50) <= 24, \
        f"$7e50 table shape wrong: max={max(t7e50)}"
    b10_data.append(emit_db(rom, 10, 0x7E50, 0x7EAD,
                            "Bank 10 $7e50-$7ead $7730 transition table",
                            "94 bytes: [$c105] -> $7eae record index "
                            "(0-24; 0 is the common default)."))
    # $7eae: 25 records x 6 bytes [new $c0f9|$ff][new $c116|$ff]
    # [new $c105][new $c10a][handler lo][handler hi].
    recs = []
    for i in range(25):
        base = 0x7EAE + 6 * i
        recs.append([rom[file_off(10, base + j)] for j in range(6)])
    assert recs[0] == [0xFF, 0xFF, 0x3F, 0x05, 0xD4, 0x77], recs[0]
    assert recs[11] == [0xFF, 0xFF, 0x36, 0x09, 0xF2, 0x77], recs[11]
    assert recs[24] == [0xFF, 0xB0, 0x3F, 0x05, 0xD4, 0x77], recs[24]
    out = ["; Slice 15: Bank 10 $7eae-$7f43 $7730 transition records -- "
           "bank 10 $7eae-$7f43.",
           "; 25 records x 6 bytes: [new $c0f9|$ff][new $c116|$ff] "
           "[new $c105][new $c10a][handler lo][handler hi].",
           "; Record 0 -> [$c105]=$3f, [$c10a]=5, jp $77d4; record 11 "
           "-> [$c105]=$36, [$c10a]=9, jp $77f2 (record-KILL path).",
           "; Generated by tools/generators/gen_slice15.py; bytes read straight "
           "from the ROM.",
           'SECTION "Bank 10 $7eae-$7f43 transition records", '
           'ROMX[$7eae], BANK[10]',
           "Bank0A_7EAE::"]
    for i, r in enumerate(recs):
        out.append(f"    db ${r[0]:02x}, ${r[1]:02x}, ${r[2]:02x}, "
                   f"${r[3]:02x}, ${r[4]:02x}, ${r[5]:02x}  ; record {i}")
    b10_data.append("\n".join(out) + "\n")

    # ---- bank 8 data carves ----
    b8_data = []
    # $5efe: the $7730 B table, 94 bytes; values in {0,1,2,3,$83}.
    # Only bit 1 is tested by $7730 (it gates the $5e37 linker call).
    t5efe = [rom[file_off(8, a)] for a in range(0x5EFE, 0x5F5C)]
    assert len(t5efe) == 94 and set(t5efe) <= {0, 1, 2, 3, 0x83}, \
        f"$5efe table values: {sorted(set(t5efe))}"
    b8_data.append(emit_db(rom, 8, 0x5EFE, 0x5F5B,
                           "Bank 8 $5efe-$5f5b $7730 B table",
                           "94 bytes: [$c105] -> B for bank-10 $7730; "
                           "bit 1 gates the $5e37 linker call."))
    b8_data.append(emit_dw_table(
        rom, 8, 0x6467,
        [(0x6467 + 2 * i, f"[$c10a]={i}") for i in range(6)],
        "Bank 8 $6467-$646c [$c10a] table (entry-6 handler)",
        expected=[0x6473, 0x6495, 0x609D, 0x7310, 0x63B5, 0x6646]))
    b8_data.append(emit_dw_table(
        rom, 8, 0x6DAA,
        [(0x6DAA + 2 * i, f"[$c10a]={i}") for i in range(6)],
        "Bank 8 $6daa-$6db5 [$c10a] table (entry-34 handler)",
        expected=[0x6DB6, 0x6E4D, 0x6E6A, 0x6EA1, 0x6EC4, 0x6ECC]))
    b8_data.append(emit_dw_table(
        rom, 8, 0x6F65,
        [(0x6F65 + 2 * i, f"[$c10a]={i}") for i in range(11)],
        "Bank 8 $6f65-$6f7a [$c10a] table ($6f56 handler)",
        expected=[0x6F7B, 0x6FE1, 0x707A, 0x7081, 0x70A6, 0x70FF,
                  0x7198, 0x71AC, 0x71CB, 0x7201, 0x7215]))
    # $76e3: 94 bytes, values 0/1/2 -> the $7741 triple-table index.
    t76e3 = [rom[file_off(8, a)] for a in range(0x76E3, 0x7741)]
    assert len(t76e3) == 94 and max(t76e3) <= 2, \
        f"$76e3 table: max={max(t76e3)}"
    b8_data.append(emit_db(rom, 8, 0x76E3, 0x7740,
                           "Bank 8 $76e3-$7740 $7311 triple-table index",
                           "94 bytes: [$c105] (or [$c104]&$7f when "
                           "[$c105]==$3f) -> 0/1/2, selecting a $7741 "
                           "entry."))
    b8_data.append(emit_dw_table(
        rom, 8, 0x7741,
        [(0x7741, "index 0"), (0x7743, "index 1"), (0x7745, "index 2")],
        "Bank 8 $7741-$7746 sprite triple-table pointers",
        expected=[0x7747, 0x7777, 0x778C]))
    b8_data.append(emit_db(rom, 8, 0x7747, 0x77D9,
                           "Bank 8 $7747-$77d9 sprite triple tables",
                           "147 bytes: $7747-$7776 (index 0), "
                           "$7777-$778b (index 1), $778c-$77d9 (index 2); "
                           "3-byte triples the $7311 routine reads."))
    # $77da: 32 dw, all plausible bank-8 addresses; 31 of them fall
    # in $7896-$7944, one (entry 13) is $79ae.
    t77da = [rom[file_off(8, 0x77DA + 2 * i)] |
             (rom[file_off(8, 0x77DA + 2 * i + 1)] << 8)
             for i in range(32)]
    assert all(0x4000 <= v <= 0x7FFF for v in t77da), \
        f"$77da table out of range: {[hex(v) for v in t77da]}"
    b8_data.append(emit_dw_table(
        rom, 8, 0x77DA,
        [(0x77DA + 2 * i, f"entry {i}") for i in range(32)],
        "Bank 8 $77da-$7819 $7526 nested-table pointers",
        note="32 dw, all plausible bank-8 addresses; 31 in "
             "$7896-$7944, entry 13 is $79ae (uncarved region)."))

    # The 1-byte ret at $6668 ($2b48 entry-8 handler): the walk does
    # not reach it (no control flow into it); verified byte $c9.
    assert rom[file_off(8, 0x6668)] == 0xC9, "bank 8 $6668 is not $c9"
    ret6668 = ("; Slice 15: Bank 8 $6668 1-byte ret -- the $2b48 entry-8 "
               "handler (no-op). Verified byte $c9; no control flow "
               "reaches it, so it is not part of the walk.\n"
               'SECTION "Bank 8 $6668 entry-8 ret", ROMX[$6668], BANK[8]\n'
               "Bank8_6668::\n"
               "    ret                                              ; $6668\n")
    by_file.setdefault("src/banks/bank8slice15.asm", []).append(ret6668)
    by_file.setdefault("src/banks/bank0a.asm", []).extend(b10_data)
    by_file.setdefault("src/banks/bank8slice15.asm", []).extend(b8_data)

    for outfile, parts in by_file.items():
        # Code carves are (bank, lo, hi, title, instrs, rst08) tuples;
        # data carves are already-rendered strings.
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

    splice_bank0_table(rom)


if __name__ == "__main__":
    main()
