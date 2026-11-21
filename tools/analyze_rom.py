#!/usr/bin/env python3
"""Analyse the DK94 ROM header, banks and entry code from the bytes.
No guessing: every claim below is computed from roms/*.gb.
Usage: python3 tools/analyze_rom.py [rom_path]"""
import hashlib, struct, sys
from pathlib import Path

ROM = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "roms" / "Donkey_Kong_World_Rev1_SGB.gb"
d = ROM.read_bytes()
print(f"file: {ROM}  size={len(d)} (0x{len(d):x})")
print(f"sha1={hashlib.sha1(d).hexdigest()}")
print(f"md5 ={hashlib.md5(d).hexdigest()}")

# Nintendo logo (0x104-0x133) - bytes copied from Nacre's src/gb/gb_cart.c,
# which is the same table the boot ROM checks. (An earlier draft of this
# script had a wrong logo table from memory; Nacre's is authoritative here.)
LOGO = bytes([
    0xCE, 0xED, 0x66, 0x66, 0xCC, 0x0D, 0x00, 0x0B, 0x03, 0x73, 0x00, 0x83, 0x00, 0x0C, 0x00, 0x0D,
    0x00, 0x08, 0x11, 0x1F, 0x88, 0x89, 0x00, 0x0E, 0xDC, 0xCC, 0x6E, 0xE6, 0xDD, 0xDD, 0xD9, 0x99,
    0xBB, 0xBB, 0x67, 0x63, 0x6E, 0x0E, 0xEC, 0xCC, 0xDD, 0xDC, 0x99, 0x9F, 0xBB, 0xB9, 0x33, 0x3E])
print(f"nintendo logo 0x104-0x133 ok: {d[0x104:0x134] == LOGO}")

def hdr(off, ln=1):
    return d[off:off+ln]
print(f"entry 0x100: {d[0x100:0x104].hex(' ')}  (jp ${struct.unpack('<H', d[0x101:0x103])[0]:04x} if nop+jp)")
print(f"title 0x134: {d[0x134:0x144]!r}")
print(f"CGB flag 0x143: 0x{d[0x143]:02x}  SGB flag 0x146: 0x{d[0x146]:02x}")
print(f"cart type 0x147: 0x{d[0x147]:02x}  ROM size 0x148: 0x{d[0x148]:02x} -> {32 << d[0x148]} KiB, {32 << d[0x148] >> 4} banks x 16 KiB")
print(f"RAM size 0x149: 0x{d[0x149]:02x}  dest 0x14a: 0x{d[0x14a]:02x}  old licensee 0x14b: 0x{d[0x14b]:02x}")
print(f"version 0x14c: 0x{d[0x14c]:02x} (Rev {d[0x14c]})")
hc = (0 - sum(d[0x134:0x14d]) - 25) & 0xff
print(f"header checksum 0x14d: stored 0x{d[0x14d]:02x} calc 0x{hc:02x} ok={hc == d[0x14d]}")
gc_stored = struct.unpack('>H', d[0x14e:0x150])[0]
gc_calc = (sum(d[:0x14e]) + sum(d[0x150:])) & 0xffff
print(f"global checksum 0x14e: stored 0x{gc_stored:04x} calc 0x{gc_calc:04x} ok={gc_stored == gc_calc}")

# Interrupt vectors: each is 8 bytes at 0x40,0x48,0x50,0x58,0x60
names = {0x40: "VBlank", 0x48: "STAT", 0x50: "Timer", 0x58: "Serial", 0x60: "Joypad"}
for a, n in names.items():
    print(f"vector 0x{a:02x} {n:7s}: {d[a:a+8].hex(' ')}")
print(f"RST 0x00 @0x0000: {d[0:8].hex(' ')}  RST 0x08: {d[8:16].hex(' ')}  RST 0x10: {d[0x10:0x18].hex(' ')}")
print(f"RST 0x18: {d[0x18:0x20].hex(' ')}  RST 0x20: {d[0x20:0x28].hex(' ')}  RST 0x28: {d[0x28:0x30].hex(' ')}")
print(f"RST 0x30: {d[0x30:0x38].hex(' ')}  RST 0x38: {d[0x38:0x40].hex(' ')}")
print(f"bytes 0x68-0xff (padding?): nonzero={sum(1 for x in d[0x68:0x100] if x)} first16={d[0x68:0x78].hex(' ')}")

print("\nbank map (16 KiB banks, file offset = bank*0x4000):")
for b in range(len(d) // 0x4000):
    chunk = d[b*0x4000:(b+1)*0x4000]
    nz = sum(1 for x in chunk if x)
    # crude: count 0x00 runs / distinct
    print(f"  bank {b:2d} 0x{b*0x4000:05x}-0x{(b+1)*0x4000-1:05x} nonzero {nz:5d}/16384 ({100*nz/16384:4.1f}%) first16 {chunk[:16].hex(' ')}")

# Entry code disassembly is done by hand in src/; here just dump raw bytes 0x100-0x200
print("\nentry region 0x100-0x180 raw:")
for off in range(0x100, 0x180, 16):
    print(f"  {off:04x}: {d[off:off+16].hex(' ')}")
