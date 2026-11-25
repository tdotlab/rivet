#!/usr/bin/env python3
"""Slice-4 generator: carve curated regions with the recursive-descent
disassembler (tools/gb_rd.py), not mgbdis' linear sweep.

Why a new generator: mgbdis misaligns after embedded data / rst $08
tables (bank 2's sweep is off before $45a9; slice 2/3 hit the same
after $3477). gb_rd.py decodes one instruction at a time from the ROM
bytes and walks control flow from seed addresses, so every emitted
instruction starts at a true boundary. The byte-match check (`make`)
still arbitrates everything.

What slice 4 carves (see PROGRESS.md):
  * bank 5 $4000-$40d3: the 106-entry stage pointer table (dw). The
    stage data itself ($4200+ in bank 5, banks 6/18 for stages 45+/80+)
    is compressed level data, not code -- it stays INCBIN.
  * bank 2: timer-callback stub $4003-$4008, stream command engine
    $4010-$43af (shared byte-for-byte with bank 3; bank 2's own
    dispatch never targets $4142-$415b, so that sub-range is aligned
    from bank 3's walk -- bytes verified identical), stream tick
    $45a9-$47fb, timer tail $6212-$6491.
  * bank 3: entry stubs $4000-$400b, stream command engine
    $4010-$43af, sound timer tick $45a9-$48f0, sound init + tick
    $76eb-$78af.
  * bank 7: $7168 (1-byte ret stub) + $7169-$71b9 stage-RAM clear.
  * bank 7 (extension): $4794-$480d + $6ea9-$6ed1 + $6f2e-$6f61 (one
    routine, three spans; clears [$ff92] bit 0, loads a pointer from
    [$c215]; no call site in curated code, role unverified) and
    $77a9-$7aba (stream/stage index setup, two entries $77a9/$78ba
    called from bank-0 $3323/$3331). $6f62 is NOT carved: its walk
    hits rst $08 at $6f74 and gb_rd has no rst-$08 table handling
    yet -- slice 5.
  * DATA fixups (spliced into the slice-3 files, not regenerated):
    bank 1 $48cb-$48f3 as db (41 bytes; the task's $48d0-$48ff range
    was wrong at the tail -- $48f4+ is live code, proven by the
    `call $48fd` at bank-0 $0a8d with bank 1 mapped, and the
    recursive-descent walk from $48f4 aligns with the existing
    decode; see PROGRESS.md), bank 12 $4e55-$52d4 as db (the
    331-entry state-16 queue table $4f97-$522c as (C,B) pairs, plus
    the flanking dead-data regions $4e55-$4f96 and $522d-$52d4 --
    the whole span is walk-verified unreachable, and the phantom
    jr instructions mgbdis decoded in $4e55-$4f96 target labels
    inside the table, so the table cannot be converted alone
    without moving those labels and breaking byte-match).

Emission rules (mirroring gen_slice3.py's output style):
  * One SECTION per carve; instructions carry a `; $addr` comment.
  * Named LABELS get `Name::`; jr targets inside the carve get
    `jr_BBB_AAAA:` labels (mgbdis style); call/jp targets stay
    numeric $xxxx, as in slice 3.
  * Bytes inside a carve range that no reachable instruction covers
    are emitted as `db` (honest data markers, 8 per line).
  * rst $08 inside a carve is an error (none expected in slice 4).

Regenerate with: python3 tools/generators/gen_slice4.py
Outputs: src/banks/bank2.asm src/banks/bank3.asm src/banks/bank5.asm src/banks/bank7.asm
         (rewrites src/banks/bank1.asm, src/banks/bank12.asm in place for the
         two DATA fixups, and regenerates src/banks.asm via
         tools/generators/gen_banks.py after updating its CARVED map).
The outputs are CHECKED IN; rerun after changing the config.
"""
import re
import subprocess
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, decode, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile, seeds, align_bank)
# align_bank: the bank whose control-flow walk supplies instruction
# boundaries for this carve. Usually the bank itself; bank 2's engine
# carve aligns on bank 3 (identical bytes -- asserted -- because bank
# 2's dispatch never targets $4142-$415b).
CARVES = [
    (2, 0x4003, 0x4008, "Bank 2 timer callback stub",
     "src/banks/bank2.asm", [0x4003], 2),
    (2, 0x4010, 0x43AF, "Bank 2 stream command engine (shared with bank 3)",
     "src/banks/bank2.asm", [0x4003], 3),
    (2, 0x45A9, 0x47FB, "Bank 2 stream timer tick",
     "src/banks/bank2.asm", [0x4003], 2),
    (2, 0x6212, 0x6491, "Bank 2 stream restart + state init",
     "src/banks/bank2.asm", [0x4003], 2),
    (3, 0x4000, 0x400B, "Bank 3 entry stubs",
     "src/banks/bank3.asm", [0x4000, 0x4003], 3),
    (3, 0x4010, 0x43AF, "Bank 3 stream command engine (shared with bank 2)",
     "src/banks/bank3.asm", [0x4000, 0x4003], 3),
    (3, 0x45A9, 0x48F0, "Bank 3 sound timer tick",
     "src/banks/bank3.asm", [0x4000, 0x4003], 3),
    (3, 0x76EB, 0x78AF, "Bank 3 sound init + tick",
     "src/banks/bank3.asm", [0x4000, 0x4003], 3),
    (7, 0x7168, 0x71B9, "Bank 7 stage-RAM clear",
     "src/banks/bank7.asm", [0x7168, 0x7169], 7),
    (7, 0x4794, 0x480D, "Bank 7 $4794 routine",
     "src/banks/bank7.asm", [0x4794], 7),
    (7, 0x6EA9, 0x6ED1, "Bank 7 $4794 continuation",
     "src/banks/bank7.asm", [0x4794], 7),
    (7, 0x6F2E, 0x6F61, "Bank 7 $4794 tail",
     "src/banks/bank7.asm", [0x4794], 7),
    (7, 0x77A9, 0x7ABA, "Bank 7 stream index setup ($77a9/$78ba)",
     "src/banks/bank7.asm", [0x77A9, 0x78BA], 7),
]

# Meaningful entry labels: (bank, addr) -> name. Roles are from the
# code (call sites in bank 0 / the instructions themselves); a name
# followed by "?" would mean inferred, none here are.
LABELS = {
    (2, 0x4003): "Bank2_TimerCallback",   # from TimerHandler (main.asm)
    (2, 0x4010): "Bank2_StreamOp_LoadPtr",      # dispatch target; loads a
                                          # pointer pair from the stream
    (2, 0x4022): "Bank2_StreamOp_4022",
    (2, 0x4062): "Bank2_StreamOp_4062",
    (2, 0x4074): "Bank2_StreamOp_4074",
    (2, 0x4098): "Bank2_StreamOp_4098",
    (2, 0x4131): "Bank2_StreamOp_4131",
    (2, 0x415C): "Bank2_StreamOp_415C",
    (2, 0x41D5): "Bank2_StreamOp_41D5",
    (2, 0x41E3): "Bank2_StreamOp_41E3",
    (2, 0x41F7): "Bank2_StreamOp_41F7",
    (2, 0x4209): "Bank2_StreamOp_4209",
    (2, 0x4229): "Bank2_StreamOp_4229",
    (2, 0x423F): "Bank2_StreamOp_423F",
    (2, 0x4250): "Bank2_StreamOp_4250",
    (2, 0x425F): "Bank2_StreamOp_425F",
    (2, 0x4268): "Bank2_StreamOp_4268",
    (2, 0x432C): "Bank2_StreamOp_432C",
    (2, 0x45A9): "Bank2_StreamTick",      # timer tick: runs one stream op
    (2, 0x4629): "Bank2_StreamTickLoop",
    (2, 0x4677): "Bank2_StreamTickAlt",
    (2, 0x4683): "Bank2_StreamTickCont",
    (2, 0x4744): "StreamDispatch",        # jp z chain over the op type
    (2, 0x6212): "Bank2_StreamRestart",   # [$c836]/[$c837] gate, restart
    (2, 0x6421): "Bank2_StreamStateInit",  # zeroes/sets $dfxx stream state
    (3, 0x4000): "Bank3_SoundInitEntry",  # from ClearRAMAndInit (main.asm)
    (3, 0x4003): "Bank3_TimerCallback",   # from TimerHandler (main.asm)
    (3, 0x4010): "Bank3_StreamOp_LoadPtr",
    (3, 0x4022): "Bank3_StreamOp_4022",
    (3, 0x4062): "Bank3_StreamOp_4062",
    (3, 0x4074): "Bank3_StreamOp_4074",
    (3, 0x4098): "Bank3_StreamOp_4098",
    (3, 0x4131): "Bank3_StreamOp_4131",
    (3, 0x415C): "Bank3_StreamOp_415C",
    (3, 0x41D5): "Bank3_StreamOp_41D5",
    (3, 0x41E3): "Bank3_StreamOp_41E3",
    (3, 0x41F7): "Bank3_StreamOp_41F7",
    (3, 0x4209): "Bank3_StreamOp_4209",
    (3, 0x4229): "Bank3_StreamOp_4229",
    (3, 0x423F): "Bank3_StreamOp_423F",
    (3, 0x4250): "Bank3_StreamOp_4250",
    (3, 0x425F): "Bank3_StreamOp_425F",
    (3, 0x4268): "Bank3_StreamOp_4268",
    (3, 0x432C): "Bank3_StreamOp_432C",
    (3, 0x45A9): "Bank3_StreamRestart",   # same shape as bank 2 $6212
    (3, 0x4632): "Bank3_StreamRestartCont",
    (3, 0x481E): "Bank3_TimerTail",       # rTIMA-gated tail of the callback
    (3, 0x76EB): "SoundInit",             # NR52/NR50/NR51/NR30/NR32 setup
    (3, 0x7739): "SoundTick",             # called from the timer callback
    (7, 0x7168): "Bank7_Noop",            # 1-byte ret; TransitionStep0 tail
    (7, 0x7169): "Bank7_ClearStageRAM",   # clears $dd17/$c117/$ff91, copies
                                          # init data from $7394/$74ee
    (7, 0x4794): "Bank7_4794",            # clears [$ff92] bit 0, loads ptr
                                          # from [$c215]; no call site in
                                          # curated code, role unverified
    (7, 0x77A9): "Bank7_77A9",            # stream index setup; from
                                          # bank-0 $3331
    (7, 0x78BA): "Bank7_78BA",            # stream index setup; from
                                          # bank-0 $3323
}

# C-op meanings in the bank-12 queue table ($4f97), from the C-dispatch
# table at bank-0 $0d8c (slice 3): 1 = load stage B, 2 = state 20,
# 3 = state 4-or-20 walk, 4 = no-op, $14 (20) = state 30.
QUEUE_C_MEANING = {1: "load stage", 2: "state 20", 3: "state 4-or-20",
                   4: "no-op", 0x14: "state 30"}


def jr_targets_in(instrs, lo, hi):
    """Addresses in [lo, hi] targeted by a jr inside the carve."""
    out = set()
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
            out.add(tgt)
    return out


def emit_carve(rom, bank, lo, hi, title, instrs):
    out = [f"; Slice 4: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice4.py from the ROM bytes via",
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
    addr = lo
    while addr <= hi:
        if addr in instrs:
            ln, text, kind, tgt = instrs[addr]
            if kind == "rst08":
                print(f"ERROR: rst $08 at bank {bank} ${addr:04x} "
                      f"inside carve -- table handling not implemented",
                      file=sys.stderr)
                sys.exit(1)
            if (bank, addr) in LABELS:
                out.append(f"{LABELS[(bank, addr)]}::")
            elif addr in jr_targets:
                out.append(f"jr_{bank:03x}_{addr:04x}:")
            # jr targets inside the carve use a label: the named label
            # if the target has one, else the jr_ label; targets
            # outside stay numeric (RGBDS accepts a numeric jr target).
            if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
                if (bank, tgt) in LABELS:
                    tgt_label = LABELS[(bank, tgt)]
                else:
                    tgt_label = f"jr_{bank:03x}_{tgt:04x}"
                text = re.sub(r"\$[0-9a-f]{4}$", tgt_label, text)
            out.append(f"    {text:<48} ; ${addr:04x}")
            addr += ln
        else:
            # Uncovered bytes inside the carve: honest data.
            run = []
            while addr <= hi and addr not in instrs:
                run.append(rom[file_off(bank, addr)])
                addr += 1
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def emit_stage_table(rom):
    """Bank 5 $4000-$40d3: 106-entry stage pointer table (dw).

    $24e7 (LoadStage) reads entry [$c829] and SwitchBankByE ($2611)
    picks the bank by index: 0-44 -> bank 5, 45-79 -> bank 6,
    80-105 -> bank 18. Entry values are window addresses in that bank.
    The stage data itself stays INCBIN (compressed level data).
    """
    out = ["; Slice 4: stage pointer table -- bank 5 $4000-$40d3.",
           "; Read by LoadStage ($24e7, bank 0) at $4000 + [$c829]*2;",
           "; SwitchBankByE ($2611) maps the index to a bank: 0-44 bank 5,",
           "; 45-79 bank 6, 80-105 bank 18. The stage data the entries",
           "; point at stays INCBIN in src/banks.asm (compressed data).",
           'SECTION "Bank 5 stage pointer table", ROMX[$4000], BANK[5]']
    for i in range(106):
        off = 5 * 0x4000 + 2 * i
        tgt = rom[off] | (rom[off + 1] << 8)
        assert 0x4000 <= tgt <= 0x7FFF, f"stage {i} target ${tgt:04x}"
        bank = 5 if i < 45 else (6 if i < 80 else 18)
        out.append(f"    dw ${tgt:04x}  ; stage {i} -> bank {bank}")
    return "\n".join(out) + "\n"


ADDR_RE = re.compile(r"; \$(0[0-9a-f]{3}|[0-9a-f]{4})\s*$")


def splice_db(path, lo, hi, new_lines, what):
    """Replace the lines covering addresses lo..hi in `path` (identified
    by their trailing `; $addr` comments) with `new_lines`.

    Safety: any label defined by a removed line must not be referenced
    by a kept line -- a moved label would change a jr offset byte and
    break byte-match. Abort loudly if that happens (it means the span
    boundary is wrong and a phantom reference needs dealing with).
    """
    lines = open(path).read().split("\n")
    addrs = []
    for i, line in enumerate(lines):
        m = ADDR_RE.search(line)
        addrs.append(int(m.group(1), 16) if m else None)
    try:
        start = addrs.index(lo)
        end = addrs.index(hi)
    except ValueError:
        print(f"ERROR: {what}: address range ${lo:04x}-${hi:04x} not "
              f"found in {path}", file=sys.stderr)
        sys.exit(1)
    # The replaced span must be exactly the address range, in order.
    span = [a for a in addrs[start:end + 1] if a is not None]
    assert span[0] == lo and span[-1] == hi, \
        f"{what}: span ${span[0]:04x}-${span[-1]:04x} != ${lo:04x}-${hi:04x}"
    removed = lines[start:end + 1]
    kept = lines[:start] + lines[end + 1:]
    label_re = re.compile(r"^([A-Za-z_][\w]*):\s*$")
    for line in removed:
        m = label_re.match(line.strip())
        if m:
            lab = m.group(1)
            refs = [l for l in kept if lab in l]
            if refs:
                print(f"ERROR: {what}: label {lab} defined in the "
                      f"removed span is still referenced by kept code "
                      f"(e.g. {refs[0].strip()}) -- refusing to move it",
                      file=sys.stderr)
                sys.exit(1)
    lines[start:end + 1] = new_lines
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"spliced {what} into {path} "
          f"(replaced {end - start + 1} lines with {len(new_lines)})")


def fixup_bank1(rom):
    """Bank 1 $48cb-$48f3 as db. Five 4-byte records ($48cb/$48cf/$48d3/
    $48d7/$48db, loaded as data pointers at $44b9/$4586/$4807/$4812/
    $4538) + the counting sequence $30-$43 ($48df-$48f2) + $9d ($48f3).
    $48f4+ is CODE (call $48fd at bank-0 $0a8d, bank 1 mapped) and stays.
    Idempotent: skips if the slice-4 marker is already present.
    """
    if "Slice 4: data, not code" in open("src/banks/bank1.asm").read():
        print("bank-1 fixup already applied, skipping")
        return
    lines = ["    ; Slice 4: data, not code (was mgbdis' linear-sweep",
             "    ; decode). Five 4-byte records + the $30-$43 counting",
             "    ; sequence + $9d. $48f4+ is live code (call $48fd) and",
             "    ; is NOT part of this blob."]
    blob = rom[1 * 0x4000 + 0x8CB:1 * 0x4000 + 0x8F4]
    assert len(blob) == 0x29, len(blob)
    for j in range(0, len(blob), 8):
        chunk = blob[j:j + 8]
        addr = 0x48CB + j
        comment = ""
        if addr == 0x48DF:
            comment = "  ; counting sequence $30-$43 starts here"
        out = "    db " + ", ".join(f"${b:02x}" for b in chunk) + comment
        lines.append(out)
    splice_db("src/banks/bank1.asm", 0x48CB, 0x48F3, lines,
              "bank-1 $48cb-$48f3 data")


def fixup_bank12(rom):
    """Bank 12 $4e55-$52d4 as db. The whole span is provably dead data:
    a recursive-descent walk from every known bank-12 entry (slice-3
    labels + all bank-0 call targets into bank 12, no jp (hl) anywhere
    in the reached set) reaches $4e15-$4e54 (ends `jp $33fb`) and
    $52d5+ (called from bank-0 $3309) but nothing between. Inside:
      * $4e55-$4f96: unknown table (records with $01/$02/$03 prefixes)
      * $4f97-$522c: the 331-entry state-16 queue table as (C,B) pairs
      * $522d-$52d4: a second table (repeating (02 xx 01 xx 04 xx)
        records)
    The queue table is the named slice-4 item; the flanking regions
    are converted too because the table conversion forces it -- the
    phantom jr instructions mgbdis decoded inside $4e55-$4f96
    (e.g. at $4f78/$4f7e) target labels inside the table span, and
    moving those labels would change jr offset bytes and break the
    byte-match. Converting the whole dead span removes them cleanly.
    Read by QueueFetchBC ($0dda, bank 0) at $4f97 + index*2.
    Idempotent: skips if the slice-4 marker is already present.
    """
    if "Slice 4: dead data, not code" in open("src/banks/bank12.asm").read():
        print("bank-12 fixup already applied, skipping")
        return
    lines = ["    ; Slice 4: dead data, not code (was mgbdis' linear-sweep",
             "    ; decode). Walk-verified: no reachable instruction in",
             "    ; $4e55-$52d4 from any known bank-12 entry. Code ends",
             "    ; at $4e54 (`jp $33fb`); code resumes at $52d5.",
             "    ; --- $4e55-$4f96: unknown table ---"]
    for lo, hi, pairs in ((0x4E55, 0x4F96, False),
                          (0x4F97, 0x522C, True),
                          (0x522D, 0x52D4, False)):
        if lo == 0x4F97:
            lines += ["    ; --- $4f97-$522c: the state-16 queue table,",
                      "    ; (C,B) pairs. C is the C-dispatch op, B the",
                      "    ; stage/param. ---"]
        if lo == 0x522D:
            lines += ["    ; --- $522d-$52d4: second table ---"]
        if pairs:
            for i in range(331):
                off = 12 * 0x4000 + 0xF97 + 2 * i
                c, b = rom[off], rom[off + 1]
                assert c in QUEUE_C_MEANING, f"queue entry {i} C=${c:02x}"
                lines.append(f"    db ${c:02x}, ${b:02x}  ; entry {i}: "
                             f"C={QUEUE_C_MEANING[c]}, B=${b:02x}")
        else:
            blob = rom[12 * 0x4000 + lo - 0x4000:12 * 0x4000 + hi - 0x4000 + 1]
            for j in range(0, len(blob), 8):
                chunk = blob[j:j + 8]
                lines.append("    db " + ", ".join(f"${b:02x}"
                                                   for b in chunk))
    splice_db("src/banks/bank12.asm", 0x4E55, 0x52D4, lines,
              "bank-12 $4e55-$52d4 dead data + queue table")


def main():
    rom = open(ROM, "rb").read()
    # One walk per (align_bank, seeds); reuse across carves.
    walks = {}
    for bank, lo, hi, _t, _o, seeds, align in CARVES:
        key = (align, tuple(seeds))
        if key not in walks:
            reached, rst08, notes = walk(align, seeds)
            if rst08:
                print(f"ERROR: rst $08 in bank {align} walk: "
                      f"{sorted(rst08)}", file=sys.stderr)
                sys.exit(1)
            for n in notes:
                if "outside window" not in n:
                    print(f"NOTE: {n}")
            walks[key] = reached
    outputs = {}
    for bank, lo, hi, title, outfile, seeds, align in CARVES:
        instrs = walks[(align, tuple(seeds))]
        # Bytes must match when aligning on another bank's walk.
        if align != bank:
            for a in range(lo, hi + 1):
                assert rom[file_off(bank, a)] == rom[file_off(align, a)], \
                    f"bank {bank} ${a:04x} != bank {align} (align mismatch)"
        # Every byte of the carve must be covered by a reached
        # instruction (gaps are emitted as db, but for slice 4 the
        # carves were chosen to be fully covered -- report otherwise).
        uncovered = [a for a in range(lo, hi + 1)
                     if not any(s <= a < s + v[0]
                                for s, v in instrs.items())]
        if uncovered:
            print(f"NOTE: bank {bank} ${lo:04x}-${hi:04x}: "
                  f"{len(uncovered)} uncovered bytes "
                  f"(emitted as db), first ${uncovered[0]:04x}")
        text = emit_carve(rom, bank, lo, hi, title, instrs)
        outputs.setdefault(outfile, []).append(text)
        print(f"carve bank {bank} ${lo:04x}-${hi:04x} -> {outfile}")
    header = ("; DO NOT HAND-EDIT the code bodies in this file -- regenerate with\n"
              ";   python3 tools/generators/gen_slice4.py\n"
              "; after changing the generator config. Entry labels and comments\n"
              "; may be added by hand above a generated block, not inside it.\n\n")
    for outfile, chunks in outputs.items():
        with open(outfile, "w") as f:
            f.write(header + "\n".join(chunks))
        print(f"wrote {outfile}")
    with open("src/banks/bank5.asm", "w") as f:
        f.write(header + emit_stage_table(rom))
    print("wrote src/banks/bank5.asm (106-entry stage table)")
    fixup_bank1(rom)
    fixup_bank12(rom)


if __name__ == "__main__":
    main()
