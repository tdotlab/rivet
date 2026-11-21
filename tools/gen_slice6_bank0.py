#!/usr/bin/env python3
"""Slice-6 generator: carve bank 0 $10c2-$1642 (the sprite-stream engine).

Reads the region with tools/gb_rd.py (recursive descent from known entry
points -- the linear sweep misaligns here) and emits RGBDS source for it.
The byte-match check (`make`) is the arbiter: any transcription error
shows up as a SHA-1 mismatch.

Transformations applied to each gb_rd line:
  * jr targets inside the carved range become `jr_000_<tgt>` label refs
    (house style, cf. gen_slice3.py); jr targets outside stay absolute.
  * call/jp targets stay absolute ($xxxx), as in the other generated files.
  * known HRAM/WRAM addresses are spelled with their constants.asm /
    hardware.inc names (hCurrentBank, hFrameCount, wOAMDMATrigger,
    wScrollShadow, rSCY, rSCX, rDIV); $ff95 keeps its hFrameCount name.
  * `ld hl, sp+$06` is emitted as-is (RGBDS accepts it).

Entry points (seeds) and roles -- verified by reading the decoded bodies:
  $10c2 ClearOAMAndStreamRecords: clears OAM buffer $c000 (160 bytes) and
        the stream-record table $c200 (1024 bytes), then switches to bank
        $1d and jumps into the $10dd loop at $10e3 (so the $4000 sprite
        table it dispatches through is bank $1d's, not $0b's).
  $10dd StreamIterate: bank $0b; clears [$c701]; iterates the 32 records
        at $c200 (stride $20), calling $112c per nonzero record[0]; then
        zeroes $c000-$c0a0.
  $112c StreamDispatchRecord: per-record dispatcher (bank-$0b $4000
        table, indexed by 2*record[0]); $f0/$f1 special cases; copies
        sprite bytes from the $c600+record[0] table into the OAM buffer
        at $c000+[$c701].
  $11e8 StreamIterateB: bank $0b; 31 records from $c201; calls $123d.
  $123d StreamDispatchRecordB: same shape as $112c (flip constants
        $2b/$12 instead of $1a/$11).
  $12f9 StreamIterateC: bank $0b; 32 records from $c200; calls $1348;
        then zeroes the OAM tail from $c000+[$c701] to $c0a0.
  $1348 StreamDispatchRecordC: simpler field layout (no 16-bit pointer
        adds); flip constants $36/$13.
  $13e7 StreamIterateDual: bank $1c; alternates between the $c5e0
        records (stride $22) and the $c200 records (stride $20) on bit 0
        of [$ce21]; calls $143e; then zeroes the OAM tail.
  $143e StreamDispatchRecordD: like $112c but with a bit-7 h-flip
        variant (negated Y, tile byte xor $20).
  $1522 Bank12Jump4BCD / $1528 Bank12Jump4BF1: trampolines -- switch to
        bank $0c and jp $4bcd / $4bf1.
  $152e ClampSpriteOffset: dispatches on [$c705] (1 = both axes, 2/5 = X
        only, 3 = Y only, 4 = none); clamps the $c203/$c207 record
        positions against the scroll registers into [$c707]/[$c708].
  $15f8 ClampSpriteOffset2: [$c705] gate; same clamp reading $c223/$c227
        directly (no 16-bit adds). Caller unidentified (no carved call
        site); the bytes decode as a coherent routine with a proper
        prologue/epilogue, so it is carved as code, not data.

Regenerate with: python3 tools/gen_slice6_bank0.py
Output: src/bank0slice6.asm (checked in, not generated at build time).
"""
import re
import sys

sys.path.insert(0, "tools")
import gb_rd  # noqa: E402

LO, HI = 0x10C2, 0x1643

SEEDS = [0x10C2, 0x10D5, 0x10DD, 0x1115, 0x112C, 0x11E8, 0x1226,
         0x12F9, 0x1331, 0x13E7, 0x1522, 0x1528, 0x152E, 0x15F8]

LABELS = {
    0x10C2: "ClearOAMAndStreamRecords",
    0x10DD: "StreamIterate",
    0x112C: "StreamDispatchRecord",
    0x11E8: "StreamIterateB",
    0x123D: "StreamDispatchRecordB",
    0x12F9: "StreamIterateC",
    0x1348: "StreamDispatchRecordC",
    0x13E7: "StreamIterateDual",
    0x143E: "StreamDispatchRecordD",
    0x1522: "Bank12Jump4BCD",
    0x1528: "Bank12Jump4BF1",
    0x152E: "ClampSpriteOffset",
    0x15F8: "ClampSpriteOffset2",
}

# address spellings (constants.asm / hardware.inc names)
NAMES = {
    "$ff8c": "hCurrentBank",
    "$ff95": "hFrameCount",
    "$ff42": "rSCY",
    "$ff43": "rSCX",
    "$c701": "wOAMDMATrigger",
    "$c707": "wScrollShadow",
}


def jr_label(tgt):
    return f"jr_000_{tgt:04x}"


def main():
    reached, _rst08, notes = gb_rd.walk(0, SEEDS)
    # The $1522/$1528 trampolines jp to bank-$0c addresses ($4bcd/$4bf1);
    # the walk rightly stops there -- those targets are outside ROM0.
    notes = [n for n in notes
             if "$4bf1 outside ROM0" not in n
             and "$4bcd outside ROM0" not in n]
    assert not notes, notes
    covered = set()
    for a, (ln, _t, _k, _tg) in reached.items():
        for k in range(a, a + ln):
            covered.add(k)
    missing = [a for a in range(LO, HI) if a not in covered]
    assert not missing, f"uncovered bytes: {[hex(a) for a in missing[:8]]}"
    # The walk follows calls outside the carve (e.g. $1057/$1060, already
    # curated in main.asm); emit only the carved range.
    reached = {a: v for a, v in reached.items() if LO <= a < HI}

    # jr targets inside the range get labels
    jr_targets = set()
    for a, (_ln, txt, _k, _tg) in reached.items():
        for m in re.finditer(r"jr (nz, |z, |nc, |c, )?\$([0-9a-f]{4})", txt):
            t = int(m.group(2), 16)
            if LO <= t < HI:
                jr_targets.add(t)

    def rewrite(txt):
        # jr $xxxx -> jr jr_000_xxxx (in range only)
        def sub_jr(m):
            cond, tgt = m.group(1), int(m.group(2), 16)
            if LO <= tgt < HI:
                return f"jr {cond or ''}{jr_label(tgt)}"
            return m.group(0)
        txt = re.sub(r"jr (nz, |z, |nc, |c, )?\$([0-9a-f]{4})", sub_jr, txt)
        # address spellings: [$ff8c] / $ff8c / [$c701] / $c707
        for raw, name in NAMES.items():
            txt = txt.replace(f"[{raw}]", f"[{name}]")
            txt = re.sub(rf"(?<![0-9a-fA-Za-z_]){re.escape(raw)}(?![0-9a-fA-Za-z_])",
                         name, txt)
        return txt

    out = []
    out.append("; DO NOT HAND-EDIT the code bodies in this file -- regenerate with")
    out.append(";   python3 tools/gen_slice6_bank0.py")
    out.append("; after changing the generator config. Entry labels and comments")
    out.append("; may be added by hand above a generated block, not inside it.")
    out.append("")
    out.append("; Slice 6: Bank 0 sprite-stream engine -- bank 0 $10c2-$1642.")
    out.append("; Generated by tools/gen_slice6_bank0.py from tools/gb_rd.py")
    out.append("; (recursive descent; the linear sweep misaligns in this region).")
    out.append("; Four iterator/dispatcher pairs (A $10dd/$112c, B $11e8/$123d,")
    out.append("; C $12f9/$1348, D $13e7/$143e) walk the 32-entry stream-record")
    out.append("; table at $c200 (stride $20) and copy sprite bytes into the OAM")
    out.append("; buffer at $c000, dispatching through the bank-$0b/$1c $4000")
    out.append("; table; the $152e/$15f8 tail clamps record positions against the")
    out.append("; scroll registers into wScrollShadow ($c707/$c708).")
    out.append('SECTION "Bank 0 stream engine", ROM0[$10c2]')
    for a in sorted(reached):
        ln, txt, _kind, _tgt = reached[a]
        if a in LABELS:
            out.append(f"{LABELS[a]}::")
        if a in jr_targets:
            out.append(f"{jr_label(a)}:")
        out.append(f"    {rewrite(txt):<48} ; ${a:04x}")
    with open("src/bank0slice6.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote src/bank0slice6.asm ({len(reached)} instructions)")


if __name__ == "__main__":
    main()
