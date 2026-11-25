#!/usr/bin/env python3
"""Slice-26 generator (part 4): bank 1 ($01) $5a81-$79dd -> src/bank1slice26.asm.

Survey: tools/survey26_bank1.py.
  * $5a81-$5d47 (711 B) CODE, one continuous gb_rd span from seeds
    [$5a81, $5b71, $5ceb, $5d21], zero unreached, no rst $08.
    Entries (all verified, ROM-wide byte search + carved callers):
      - $5a81: `call $5a81` at bank-0 $0b3a (State16Table[41] $0b28:
        maps bank 1, calls $5a81 when [$c860]!=0 and [$c858]!=$ff).
      - $5b71: `call $5b71` at bank-0 $0b3f (same $0b28, else-branch).
        $5a81/$5b71 are parallel [$c809] dispatches ($11/$12 vs
        $0b/$0c thresholds; MemcpyC sources $5fd3 vs $5f69).
      - $5ceb: `call $5ceb` at bank-0 $22b3 (stream area; bank-1
        mapping at that point unpinned -- honest gap).
      - $5d21: `jp $5d21` at bank-0 $1c7a (BuildAttrMap tail;
        TransitionStep1 maps bank 1 before calling BuildAttrMap).
    Cross-refs: bank-0 $106e/$1060 (MemcpyC/MemsetC), $293e, $1ec0/
    $1ebf/$1ec9 (save), $3891, $169c, $33c3, $201d; carved bank-1
    $5a45/$5a76/$5a7c (Bank1_5A45/5A76/5A7C, slice 25).
  * $5d48-$79dd (7,318 B) DATA, plain db with a label at each
    ld-pointer target read by carved bank-1 code ($5d48, $5d5e,
    $5d74, $5d8a, $5d9e, $5dae, $5db4, $5e80, $5e92, $5e96, $5e99,
    $5ecb, $5f0d, $5f21, $609d, $60c5, $60fd, $610d, $6114, $7308)
    plus the two MemcpyC sources $5f69 ($5bdd) and $5fd3 ($5a97).
    The $5d48 walk (219 instrs) is spurious: the $5d48 bytes are
    digit-like table data read by ld, and the walk jumps back into
    $5d10 only through data-decoding. The $6000/$7000/$7800 walks
    are spurious too: no call/jp/ld entry to $7000/$7800/$5e54
    anywhere in the ROM (byte search), and $7000-$704d / $7800-
    $7903 contain ZERO ret ($c9) bytes. $7904+ is counting data.
    Last non-$ff at $79dd; $79de-$7fff all $ff stays INCBIN.
Door / clear chain: ONE hStateTimer ($ff90) write, at $5bd1:
  `ld a,[$c70b]; ldh [$ff90],a` -- a RESTORE of the timer saved
  in [$c70b], not a literal 33/42 write. The $5bd1 restore sits
  in the $5b84 tail of the $5a81/$5b71 sequence (State16Table[41]
  $0b28, bank 1 mapped). The [$c70b] mechanism (all 6 writers /
  4 readers now known): a routine saves the current hStateTimer
  into [$c70b], switches to a sub-sequence timer, and a later
  routine restores it. Writers: $08bd/$08c6 (bank-0 $0859,
  State16Table[6]: save timer, set timer 41 $29 -- the save that
  launches the $5a81 sequence), $6d2a/$405a (bank 7: save, set
  $11), $66b5 (bank 7: save, set $10), $55b6 (bank 31: save, set
  $10). Readers: $0a2c (bank-0), $4e0f (bank 1), $6fc4 (bank 7),
  $5bd1 (bank 1, this slice). The normal restored value is 6
  (saved by $08bd when timer 6 launches the sequence). LIVE
  (gb_pcwatch, 15000f retry flow, progress-1 save): $5a81@1 0,
  $5b71@1 0, $5bd1@1 0, $08bd 0, $0b28 0 -- the sequence NEVER
  fires in this flow. $0859 fires 2262x but in STATE 18 timer 6
  (the routine is shared between states 16 and 18), and its
  $08bd save branch is never taken: the gate ([$ff8b]&$0c,
  [$da4b]!=$21, $c712/$c711 check) fails throughout. So the
  $5a81 sequence is gated on a flow this run never takes (which
  flow -- map entry with input? -- is an OPEN QUESTION for a
  later slice), and the restored value at $5bd1 is unresolved
  live; statically it is the $08bd save, i.e. normally 6.
  VERIFIED LIVE in the same run: $5d21@1 23x and $5ceb@1 6x,
  both state 18 timer 1 -- the BuildAttrMap tail-jump and the
  $22b3 stream call run on every stage load.
  No hGameState ($ff8e) writes, no [$c105] writes in this carve.
  $5c55/$5cbf READ hGameState and compare with $1e (30 = attract
  demo): the $5c61/$5ce6 writes are skipped during the demo.
  $5ceb writes [$c80d]=$54/$01. No literal timer-33/42 lead.
Run: python3 tools/gen_slice26_bank1.py
"""
import re
import sys

sys.path.insert(0, "tools")
import gen_slice26  # noqa: E402
from gb_rd import file_off, walk  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
BANK = 1
OUT = "src/bank1slice26.asm"

LABELS1 = {
    0x5A81: "Bank1_5A81", 0x5B71: "Bank1_5B71", 0x5B5A: "Bank1_5B5A",
    0x5B67: "Bank1_5B67", 0x5B84: "Bank1_5B84", 0x5C67: "Bank1_5C67",
    0x5C73: "Bank1_5C73", 0x5C8B: "Bank1_5C8B", 0x5CB5: "Bank1_5CB5",
    0x5CC5: "Bank1_5CC5", 0x5CD9: "Bank1_5CD9", 0x5CEB: "Bank1_5CEB",
    0x5D21: "Bank1_5D21",
}


def jr_targets_in(instrs, lo, hi):
    out = set()
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
            out.add(tgt)
    return out


def fmt_instr(addr, text, kind, tgt, lo, hi, jr_targets):
    if addr in LABELS1:
        label = f"{LABELS1[addr]}::"
    elif addr in jr_targets:
        label = f"jr_{BANK:03x}_{addr:04x}:"
    else:
        label = None
    if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
        tgt_label = LABELS1.get(tgt, f"jr_{BANK:03x}_{tgt:04x}")
        text = re.sub(r"\$[0-9a-f]{4}$", tgt_label, text)
    line = f"    {text:<48} ; ${addr:04x}"
    return (label + "\n" + line) if label else line


def emit_carve(rom, lo, hi, title, instrs):
    out = [f"; Slice 26: {title} -- bank {BANK} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/gen_slice26_bank1.py from the ROM bytes via",
           "; tools/gb_rd.py (recursive descent, not mgbdis' linear",
           "; sweep). Byte-match (`make`) arbitrates.",
           f'SECTION "{title}", ROMX[${lo:04x}], BANK[{BANK}]']
    jr_targets = jr_targets_in(instrs, lo, hi)
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                and lo <= tgt <= hi and tgt not in instrs:
            print(f"ERROR: bank {BANK} ${addr:04x} {text} targets "
                  f"${tgt:04x}, not a decoded instruction", file=sys.stderr)
            sys.exit(1)
    addr = lo
    while addr <= hi:
        if addr in instrs:
            ln, text, kind, tgt = instrs[addr]
            out.append(fmt_instr(addr, text, kind, tgt, lo, hi, jr_targets))
            addr += ln
        else:
            run = []
            while addr <= hi and addr not in instrs:
                run.append(rom[file_off(BANK, addr)])
                addr += 1
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def main():
    rom = open(ROM, "rb").read()
    out = ["; Slice 26: Bank 1 $5a81-$5d47 (code) + $5d48-$79dd (data).",
           "; Generated by tools/gen_slice26_bank1.py (survey:",
           "; tools/survey26_bank1.py). Byte-match (`make`) arbitrates."]
    total = 0
    # --- code $5a81-$5d47 ---
    reached, rst08, notes = walk(BANK, [0x5A81, 0x5B71, 0x5CEB, 0x5D21])
    assert not rst08, f"unexpected rst $08: {rst08}"
    covered = set()
    for a, (ln, _, _, _) in reached.items():
        covered.update(range(a, a + ln))
    assert all(a in covered for a in range(0x5A81, 0x5D48)), \
        "gap in $5a81-$5d47 coverage"
    txt = emit_carve(rom, 0x5A81, 0x5D47,
                     "Bank 1 $5a81-$5d47 [$c809] dispatch + $5ceb + $5d21",
                     reached)
    assert "    db " not in txt, "db fallback inside code section"
    out.append("")
    out.append(txt.rstrip("\n"))
    total += 0x5D48 - 0x5A81
    print(f"  carve $5a81-$5d47: {len(reached)} instrs walked")
    # --- data $5d48-$79dd ---
    labels = {
        0x5D48: "Bank1_5D48", 0x5D5E: "Bank1_5D5E", 0x5D74: "Bank1_5D74",
        0x5D8A: "Bank1_5D8A", 0x5D9E: "Bank1_5D9E", 0x5DAE: "Bank1_5DAE",
        0x5DB4: "Bank1_5DB4", 0x5E80: "Bank1_5E80", 0x5E92: "Bank1_5E92",
        0x5E96: "Bank1_5E96", 0x5E99: "Bank1_5E99", 0x5ECB: "Bank1_5ECB",
        0x5F0D: "Bank1_5F0D", 0x5F21: "Bank1_5F21", 0x5F69: "Bank1_5F69",
        0x5FD3: "Bank1_5FD3", 0x609D: "Bank1_609D", 0x60C5: "Bank1_60C5",
        0x60FD: "Bank1_60FD", 0x610D: "Bank1_610D", 0x6114: "Bank1_6114",
        0x7308: "Bank1_7308",
    }
    out.append("")
    out.append("; Slice 26: Bank 1 $5d48-$79dd data (tables read by carved")
    out.append("; bank-1 code + MemcpyC sources $5f69/$5fd3; $6000/$7000/$7800")
    out.append("; walks are spurious -- no entries, zero ret bytes).")
    out.append('SECTION "Bank 1 $5d48-$79dd data", ROMX[$5d48], BANK[1]')
    lines = []
    n = gen_slice26.emit_db(lines, rom, BANK, 0x5D48, 0x79DE, labels)
    assert n == 0x79DE - 0x5D48, f"db $5d48 emitted {n}"
    out.extend(lines)
    total += n
    assert total == 8029, f"total {total} != 8029"
    print(f"bank 1 slice 26: {total} bytes")
    with open(OUT, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
