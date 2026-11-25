#!/usr/bin/env python3
"""Count curated bytes: 524288 minus SUM of INCBIN lengths (2nd arg)
across BOTH src/banks.asm AND src/main.asm. (Slice-25 correction:
banks.asm alone misses main.asm's INCBIN bytes.)"""
import re

tot = 0
for f in ("src/banks.asm", "src/main.asm"):
    txt = open(f).read()
    for m in re.finditer(r'INCBIN\s+"[^"]+"\s*,\s*\$[0-9a-fA-F]+\s*,\s*\$([0-9a-fA-F]+)', txt):
        tot += int(m.group(1), 16)
print(f"INCBIN total (banks+main): {tot}")
print(f"curated = {524288 - tot} / 524288 ({(524288 - tot) / 524288 * 100:.1f}%)")
print(f"remaining = {tot}")
