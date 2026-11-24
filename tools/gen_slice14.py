#!/usr/bin/env python3
"""Slice-14 generator: carve the $5083-$50a0 orphaned code (bank 7),
the bank-7 $4000-$4015 second entry into the $4016 system, and the
bank-0 $0f09-$0f73 trampoline / SRAM-record / queue helpers.

Why this carve (see PROGRESS.md slice 14):
  * $5083-$50a0 was left INCBIN in slice 13: real code (ld hl,$c11b;
    pointer check; cp $08/$0e; jp $4ea8) with NO found entry. Slice 14
    re-searched (call/jp/dw/ld-hl to $5083/$5095, whole ROM): the only
    $5083/$5095 bytes are bank-11 sprite-data coincidences. It is
    orphaned/dead code, plausibly a duplicate helper left by the build.
    It is NOT the stage-clear mechanism: it never writes hStateTimer,
    [$c70b], or the queue -- it only returns or jumps to the $4ea8
    interaction-end cleanup. Carved here so it stops being INCBIN.
  * Bank 7 $4000-$4015 is the second entry into the $4016 per-frame
    system, reached ONLY via the bank-0 $0f09 trampoline (call $4000),
    which is called only from $0871 inside $0868 (state-16 timers
    3-10). $4000 calls $67a1 (still uncarved), then goes to $41c9
    unless [$ff91] bit 7 is clear AND [$ff8a] bits 4-5 are clear,
    in which case it falls to $4085 (inside the carved $4016 span).
    $4013 (jp $41c9) is dead code: unreachable fall-through after
    the unconditional jp $4085 at $4010. This carve is the evidence
    for slice 14's timer-23 verdict: the $4016 system is entered
    only from state-16 timers 3-10 (via $0f09) and 18/19 (via $6f62),
    never from state 20 -- so no [$c70b] writer can run in state 20.
  * Bank 0 $0f09-$0f14 is that trampoline (bank 7 call $4000, then
    bank 16 jp $4000 -- the second half selects bank 16 and jumps to
    ITS $4000, the state-24 dispatch; state 24 always runs bank 1
    here because its sole writer selects bank 1 first).
  * Bank 0 $0f15-$0f38 is the SRAM stage-record writer, called only
    from the timer-23/26 bodies ($09a6/$09de): it counts the C==2 /
    C==$15 queue entries before qidx (via $0f39), enables SRAM
    ($1ec0), writes 4 nibble-split bytes from [$c711] to SRAM
    $a190+4*count, disables SRAM ($1ec9). It is what the game does
    WHEN a stage clears -- but the chain that calls it (timer 23/26)
    is itself unreachable via known paths (slice 14 verdict).
  * Bank 0 $0f39-$0f60 counts C==2/C==$15 queue entries before qidx
    (bank 12 $4f97 table), returns count-1 in A. Called only from
    $0f15. (The $29c0/$29ee forward/backward scans do the same count
    over the same table; all three have no other callers.)
  * Bank 0 $0f61-$0f73 peeks the NEXT queue entry: qidx++, call
    bank-1 $4cbe, qidx--. Called only from $4783 (state-20 timer
    6/20 body $476c, when [$c207]==$50).

Regenerate with: python3 tools/gen_slice14.py
Outputs: src/bank0slice14.asm, src/bank7slice14.asm (new files).
Also update tools/gen_banks.py CARVED (bank 7: (0x4000, 0x4016),
(0x5083, 0x50A0)) and regenerate src/banks.asm; split the raw bank-0
A2 INCBIN in src/main.asm ($0df4-$0f09 and $0f74-$0fc0) and INCLUDE
the new files. The outputs are CHECKED IN; rerun after changing the
config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile, seeds)
# hi is inclusive.
CARVES = [
    (0, 0x0F09, 0x0F14, "Bank 0 $0f09-$0f14 $4016-system trampoline",
     "src/bank0slice14.asm", [0x0F09]),
    (0, 0x0F15, 0x0F38, "Bank 0 $0f15-$0f38 SRAM stage-record writer",
     "src/bank0slice14.asm", [0x0F15]),
    (0, 0x0F39, 0x0F60, "Bank 0 $0f39-$0f60 queue C==2/$15 counter",
     "src/bank0slice14.asm", [0x0F15]),
    (0, 0x0F61, 0x0F73, "Bank 0 $0f61-$0f73 peek-next-queue-entry",
     "src/bank0slice14.asm", [0x0F61]),
    (7, 0x4000, 0x4015, "Bank 7 $4000-$4015 $4016-system entry ($0f09)",
     "src/bank7slice14.asm", [0x4000, 0x4013]),
    (7, 0x5083, 0x509F, "Bank 7 $5083-$509f orphaned rec0 check "
     "(no entry; NOT the stage-clear mechanism)",
     "src/bank7slice14.asm", [0x5083, 0x5095]),
]

# Meaningful entry labels: (bank, addr) -> name.
LABELS = {
    (0, 0x0F09): "Bank0_0F09",
    (0, 0x0F15): "Bank0_0F15",
    (0, 0x0F39): "Bank0_0F39",
    (0, 0x0F61): "Bank0_0F61",
    (7, 0x4000): "Bank7_4000",
    (7, 0x5083): "Bank7_5083",
    (7, 0x5095): "Bank7_5095",
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
    out = [f"; Slice 14: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/gen_slice14.py from the ROM bytes via",
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


def main():
    rom = open(ROM, "rb").read()
    seeds0 = [0x0F09, 0x0F15, 0x0F61]
    reached0, rst08_0, notes0 = walk(0, seeds0)
    seeds7 = [0x4000, 0x4013, 0x5083, 0x5095]
    reached7, rst08_7, notes7 = walk(7, seeds7)
    for n in notes0 + notes7:
        print("note:", n, file=sys.stderr)
    print(f"walk bank 0: {len(reached0)} instrs; "
          f"bank 7: {len(reached7)} instrs", file=sys.stderr)
    assert not rst08_0 and not rst08_7, "unexpected rst $08 in walk"
    by_file = {}
    for bank, lo, hi, title, outfile, _seeds in CARVES:
        reached = reached0 if bank == 0 else reached7
        instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
        covered = set()
        for a, (ln, *_r) in instrs.items():
            covered.update(range(a, a + ln))
        assert covered == set(range(lo, hi + 1)), \
            f"bank {bank} ${lo:04x}-${hi:04x}: uncovered bytes " \
            f"{sorted(set(range(lo, hi + 1)) - covered)[:8]}"
        by_file.setdefault(outfile, []).append(
            (bank, lo, hi, title, instrs, {}))
    for outfile, carves in by_file.items():
        parts = []
        for bank, lo, hi, title, instrs, rst08 in carves:
            parts.append(emit_carve(rom, bank, lo, hi, title, instrs,
                                    rst08))
        with open(outfile, "w") as f:
            f.write("\n".join(parts))
        print(f"wrote {outfile} ({sum(len(p) for p in parts)} bytes)")


if __name__ == "__main__":
    main()
