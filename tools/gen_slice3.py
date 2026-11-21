#!/usr/bin/env python3
"""Slice-3 generator: carve curated regions out of mgbdis' raw scaffold.

Reads build/raw-mgbdis/bank_*.asm (the linear-sweep disassembly, which
reassembles byte-identically) and emits RGBDS source for the regions
listed in CARVES below. The byte-match check (`make`) is the arbiter:
any transcription error shows up as a SHA-1 mismatch.

Transformations applied to each mgbdis line:
  * `rst RST_08` -> `rst $08` (and RST_10/RST_38 likewise)
  * `Call_xxx_yyyy` / `Jump_xxx_yyyy` -> `call $yyyy` / `jp $yyyy`
    (absolute: the targets stay INCBIN'd or are curated elsewhere)
  * `jr jr_xxx_yyyy` -> kept as a label ref when yyyy is inside the
    carved range, else `jr $yyyy` (RGBDS accepts a numeric jr target)
  * `jr cond, @+/-$off` (mgbdis' unresolvable relative jump) ->
    `jr cond, $target` computed from the instruction's own bytes
  * `Call_xxx_yyyy:` / `Jump_xxx_yyyy:` label definitions are dropped
    (their references are absolute now); `jr_xxx_yyyy:` labels are kept
  * `db $xx` lines are kept verbatim (mgbdis' data bytes)

Hand fixes, configured per carve (TABLES / DATA / LABELS):
  * TABLES: {addr: nentries} -- the bytes after a genuine `rst $08`
    are a jump table, not code. Emitted as `dw` lines from the ROM
    bytes; the mgbdis garbage decode of those bytes is skipped.
  * DATA: {addr: length} -- bytes that are data, not code (e.g. the
    table at bank-0 $21e9). Emitted as `db` lines from the ROM bytes.
  * LABELS: {addr: name} -- meaningful entry-point labels.

Regenerate with: python3 tools/gen_slice3.py
Outputs: src/bank1.asm src/bank12.asm src/bank23.asm src/bank0slice3.asm
         src/sgbpackets.asm
The outputs are CHECKED IN (not generated at build time) so the curated
source is durable; rerun this script after editing the config.
"""
import re
import sys

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
RAW = "build/raw-mgbdis"

# (bank, lo, hi, section_name, outfile, romkind)
# romkind: "ROMX" for banked, "ROM0" for bank 0.
CARVES = [
    (1, 0x4000, 0x59ff, "Bank 1 code", "src/bank1.asm", "ROMX"),
    (12, 0x4000, 0x5916, "Bank 12 code", "src/bank12.asm", "ROMX"),
    (23, 0x731f, 0x7716, "Bank 23 attract demo", "src/bank23.asm", "ROMX"),
    (0, 0x0737, 0x0df3, "Bank 0 state-16 chain + C-dispatch",
     "src/bank0slice3.asm", "ROM0"),
    (0, 0x1f9a, 0x257a, "Bank 0 save + stream code",
     "src/bank0slice3.asm", "ROM0"),
    (0, 0x26b5, 0x28a7, "Bank 0 state-20 step 0",
     "src/bank0slice3.asm", "ROM0"),
    (0, 0x2920, 0x340d, "Bank 0 mid code",
     "src/bank0slice3.asm", "ROM0"),
]

# Genuine rst $08 tables inside the carves: (bank, addr) -> nentries.
TABLES = {
    (1, 0x4003): 5,    # bank-1 $4000 dispatch on hStateTimer: entries
                       # $400d $406c $41cf $411b $4142; code resumes $400d
    (0, 0x0d8c): 23,   # C-dispatch table: 0:$0d07 1:$0d1a 2:$0d23 3:$0d2c
                       # 4:$0d2b 5-18:$0d07/$0d1a alternating 19:$0d6c
                       # 20:$0d6f 21:$0d23 22:$0d81; code resumes $0dba
}

# Data blobs inside the carves: (bank, addr) -> length in bytes.
DATA = {
    (0, 0x21e9): 8,    # table read by $216c (bytes 00 01 00 01 00 01 00 01)
}

# Meaningful entry labels: (bank, addr) -> name.
LABELS = {
    (1, 0x4000): "Bank1_State24Dispatch",  # hStateTimer dispatch; state 24
                                           # lands here when bank 1 is mapped
    (1, 0x400d): "Bank1_Dispatch0",
    (1, 0x406c): "Bank1_Dispatch1",
    (1, 0x41cf): "Bank1_Dispatch2",
    (1, 0x411b): "Bank1_Dispatch3",
    (1, 0x4142): "Bank1_Dispatch4",
    (1, 0x43f9): "State20Step1",
    (1, 0x4586): "State20Step2",
    (1, 0x4998): "TitleStep1",
    (1, 0x4b14): "TitleStep7",
    (1, 0x4b21): "TitleStep8",
    (1, 0x4b2a): "TitleStep10",
    (1, 0x4c1b): "State28Step1",
    (1, 0x4ca2): "State28Step2",  # table entries 2 AND 4 share this body
                                   # (waits for [$ff95]==$2d, then IncStateTimer)
    (1, 0x4cb6): "State28Step3",  # sets state 16, timer 0 (back to transition)
    (1, 0x4e6d): "FileSelectStep2",
    (1, 0x4d66): "FileSelectStep1",
    (1, 0x4e06): "FileSelectStep3",
    (1, 0x4e77): "FileSelectStep7",
    (1, 0x4e7c): "FileSelectStep4",
    (1, 0x4e87): "FileSelectSetupSub",
    (1, 0x4f31): "State21Step0",
    (1, 0x5131): "PostStartStep1",
    (1, 0x5743): "PostStartStep29Sub",
    (1, 0x5762): "PostStartStep0Sub",
    (1, 0x58e9): "State04Step3",
    (1, 0x58f3): "State08Step0",
    (1, 0x593c): "State08Step1",
    (1, 0x5977): "State08Step2",
    (1, 0x5986): "SetLCDCShadowBit1",
    (12, 0x4000): "Bank12_State24Entry",  # state 24 lands here when bank 12
                                          # is mapped (after state 22/23)
    (12, 0x4009): "Bank12_PushHLDEToC7F7",
    (12, 0x4d05): "FileSelectLoopSub",
    (12, 0x5430): "State26Step4",
    (12, 0x553d): "State22Step0",
    (12, 0x57ca): "State26Step0",
    (12, 0x58ed): "State26Step3",
    (23, 0x731f): "AttractStep0",
    (23, 0x7563): "AttractStep3",
    (23, 0x759c): "AttractStep4",
    (23, 0x7650): "AttractStep5",
    (23, 0x765f): "AttractStep6",
    (23, 0x76a6): "AttractStep7",
    (23, 0x76b4): "AttractStep1",
    (0, 0x0737): "TransitionStep1",
    (0, 0x09f0): "CheckSaveForState21",
    (0, 0x0d8a): "CDispatch",       # ld a,c; rst $08 -- the C-dispatch
    (0, 0x0d07): "CDispatch_DecState",
    (0, 0x0d1a): "CDispatch_StoreBDec",
    (0, 0x0d23): "CDispatch_State20",
    (0, 0x0d2c): "CDispatch_State4or20",
    (0, 0x0d6c): "CDispatch_SoftReset",
    (0, 0x0d6f): "CDispatch_State30",
    (0, 0x0d81): "CDispatch_State26",
    (0, 0x0dba): "QueueAdvance",
    (0, 0x0dc7): "QueueRetreat",
    (0, 0x0dda): "QueueFetchBC",
    (0, 0x26b5): "State20Step0",
}

LINE_RE = re.compile(
    r"^(?:(?P<label>[A-Za-z_][\w]*):)?\s*(?P<code>[^;]*?)\s*;"
    r" \$(?P<addr>[0-9a-f]{4}): (?P<bytes>(?:\$[0-9a-f]{2} ?)+)\s*$")
LABEL_ONLY_RE = re.compile(r"^(?P<label>[A-Za-z_][\w]*):\s*$")
CALL_RE = re.compile(r"\b(?:Call|Jump)_[0-9a-f]{3}_([0-9a-f]{4})\b")
RST_RE = re.compile(r"\brst RST_([0-9A-F]{2})\b")
JR_LABEL_RE = re.compile(r"\bjr_([0-9a-f]{3})_([0-9a-f]{4})\b")
AT_RE = re.compile(r"@([+-])\$([0-9a-f]+)")


def parse_raw(bank):
    """Parse build/raw-mgbdis/bank_XXX.asm into {addr: (code, nbytes, label)}."""
    fn = f"{RAW}/bank_{bank:03x}.asm"
    entries, pending_label = {}, None
    for raw in open(fn):
        line = raw.rstrip("\n")
        m = LABEL_ONLY_RE.match(line.strip())
        if m:
            pending_label = m.group("label")
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        addr = int(m.group("addr"), 16)
        nbytes = len(re.findall(r"\$[0-9a-f]{2}", m.group("bytes")))
        code = m.group("code").strip()
        label = m.group("label") or pending_label
        pending_label = None
        entries[addr] = (code, nbytes, label)
    return entries


def s8(b):
    return b - 256 if b >= 128 else b


def convert(code, addr, nbytes, bank, lo, hi):
    """Convert one mgbdis instruction line to RGBDS. Returns (text, warns)."""
    warns = []
    if not code:
        return "", warns
    # rst RST_xx -> rst $xx
    code = RST_RE.sub(lambda m: f"rst ${m.group(1)}", code)
    # Call_/Jump_ labels -> absolute addresses
    code = CALL_RE.sub(lambda m: f"${m.group(1)}", code)
    # mgbdis relative jumps it could not label: jr cond, @+/-$off.
    # NOTE: mgbdis' @ offset is relative to the instruction's own
    # address, not PC-after-fetch: target = addr +/- off. (First
    # draft used addr+2+/-off and mismatched 10 bytes; the byte-match
    # check caught it -- see PROGRESS.md slice 3.)
    def at_fix(m):
        off = int(m.group(2), 16)
        if m.group(1) == "-":
            off = -off
        return f"${addr + off:04x}"
    code = AT_RE.sub(at_fix, code)
    # jr labels: keep if target inside this carve, else numeric
    def jr_fix(m):
        tgt = int(m.group(2), 16)
        if lo <= tgt <= hi:
            return m.group(0)
        warns.append(f"jr target ${tgt:04x} outside carve "
                     f"(bank {bank} ${addr:04x})")
        return f"${tgt:04x}"
    code = JR_LABEL_RE.sub(jr_fix, code)
    if "@" in code:
        warns.append(f"unconverted @ in bank {bank} ${addr:04x}: {code}")
    if re.search(r"\b(?:Call|Jump)_[0-9a-f]", code):
        warns.append(f"leftover label ref bank {bank} ${addr:04x}: {code}")
    return code, warns


def emit_carve(rom, bank, lo, hi, title, entries):
    out = []
    out.append(f"; Slice 3: {title} -- bank {bank} ${lo:04x}-${hi:04x}.")
    out.append("; Generated by tools/gen_slice3.py from build/raw-mgbdis/;")
    out.append("; hand fixes (rst $08 tables, data blobs, entry labels) are")
    out.append("; configured in the generator. Byte-match (`make`) arbitrates.")
    kind = "ROM0" if bank == 0 else "ROMX"
    bankarg = "" if bank == 0 else f", BANK[{bank}]"
    out.append(f'SECTION "{title}", {kind}[${lo:04x}]{bankarg}')
    addr = lo
    all_warns = []
    # Pre-scan: which addresses in this range are jr targets? A named
    # LABELS entry at such an address must also emit the jr_ label,
    # or the jr reference would be undefined.
    jr_targets = set()
    a = lo
    while a <= hi:
        if (bank, a) in TABLES:
            a += 2 * TABLES[(bank, a)]
            continue
        if (bank, a) in DATA:
            a += DATA[(bank, a)]
            continue
        if a not in entries:
            break
        code, nbytes, _label = entries[a]
        for m in JR_LABEL_RE.finditer(code):
            tgt = int(m.group(2), 16)
            if lo <= tgt <= hi:
                jr_targets.add(tgt)
        a += nbytes
    while addr <= hi:
        # rst $08 table override?
        if (bank, addr) in TABLES:
            n = TABLES[(bank, addr)]
            words = []
            for i in range(n):
                off = (bank * 0x4000 + addr - 0x4000) if bank else addr
                w = rom[off + 2 * i] | (rom[off + 2 * i + 1] << 8)
                words.append(f"${w:04x}")
            out.append(f"    ; rst $08 table at ${addr:04x} ({n} entries)")
            for j in range(0, n, 8):
                out.append("    dw " + ", ".join(words[j:j + 8]))
            addr += 2 * n
            continue
        # data blob override?
        if (bank, addr) in DATA:
            n = DATA[(bank, addr)]
            off = (bank * 0x4000 + addr - 0x4000) if bank else addr
            blob = rom[off:off + n]
            out.append(f"    ; data at ${addr:04x} ({n} bytes)")
            out.append("    db " + ", ".join(f"${b:02x}" for b in blob))
            addr += n
            continue
        if addr not in entries:
            print(f"ERROR: bank {bank} ${addr:04x} missing from mgbdis",
                  file=sys.stderr)
            sys.exit(1)
        code, nbytes, label = entries[addr]
        if label and label.startswith(("Call_", "Jump_")):
            label = None  # references are absolute now; drop the def
        if (bank, addr) in LABELS:
            out.append(f"{LABELS[(bank, addr)]}::")
        if label and label.startswith("jr_"):
            out.append(f"{label}:")
        elif addr in jr_targets and (bank, addr) in LABELS:
            # jr target that got a named label: keep the jr_ label too.
            out.append(f"jr_{bank:03x}_{addr:04x}:")
        text, warns = convert(code, addr, nbytes, bank, lo, hi)
        all_warns.extend(warns)
        if text:
            out.append(f"    {text:<48} ; ${addr:04x}")
        addr += nbytes
    print(f"carve bank {bank} ${lo:04x}-${hi:04x} ends at ${addr:04x} "
          f"(next byte)")
    return "\n".join(out) + "\n", all_warns


def write_sgb_table(rom):
    """Bank $1e (30) $4000-$40df: 112-entry SGB packet pointer table.

    SendSGBPacket (src/sgb.asm) indexes it by packet number A:
    HL = $4000 + A*2, packet = [HL]. Packet numbers used go up to $6f
    (SendSGBPackets68To6F), so 112 entries, $4000-$40df; the packet
    bytes themselves start at $40e0 (entry 0 -> $40e0) and stay INCBIN.
    Each entry is validated: target in $40e0-$7fff, and the packet's
    first byte & $07 (packet count) is 1..7.
    """
    out = ["; Slice 3: SGB packet pointer table -- bank $1e (30) $4000-$40df.",
           "; Generated by tools/gen_slice3.py from the ROM bytes.",
           "; A = packet index (see SendSGBPacket in src/sgb.asm).",
           "; The packet bytes at $40e0+ stay INCBIN in src/banks.asm.",
           'SECTION "SGB packet table", ROMX[$4000], BANK[30]']
    for i in range(112):
        off = 30 * 0x4000 + 2 * i
        tgt = rom[off] | (rom[off + 1] << 8)
        assert 0x40E0 <= tgt <= 0x7FFF, f"entry {i} target ${tgt:04x}"
        toff = 30 * 0x4000 + (tgt - 0x4000)
        count = rom[toff] & 0x07
        assert 1 <= count <= 7, f"entry {i} packet count {count}"
        out.append(f"    dw ${tgt:04x}  ; packet ${i:02x} ({count} x 16 bytes)")
    with open("src/sgbpackets.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print("wrote src/sgbpackets.asm (112 entries, all validated)")


def main():
    rom = open(ROM, "rb").read()
    parsed = {}
    outputs = {}
    for bank, lo, hi, title, outfile, _kind in CARVES:
        if bank not in parsed:
            parsed[bank] = parse_raw(bank)
        text, warns = emit_carve(rom, bank, lo, hi, title, parsed[bank])
        outputs.setdefault(outfile, []).append(text)
        for w in warns:
            print(f"WARN: {w}")
    header = ("; DO NOT HAND-EDIT the code bodies in this file -- regenerate with\n"
              ";   python3 tools/gen_slice3.py\n"
              "; after changing the generator config. Entry labels and comments\n"
              "; may be added by hand above a generated block, not inside it.\n\n")
    for outfile, chunks in outputs.items():
        with open(outfile, "w") as f:
            f.write(header + "\n".join(chunks))
        print(f"wrote {outfile} ({sum(len(c) for c in chunks)} bytes)")
    write_sgb_table(rom)


if __name__ == "__main__":
    main()
