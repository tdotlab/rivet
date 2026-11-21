#!/usr/bin/env python3
"""Survey helper for slice 3: find rst $08 sites, tables, and byte patterns.
Usage: python3 tools/survey3.py [command...]
All output is analysis only; nothing here modifies the repo.
"""
import sys

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

def load():
    with open(ROM, "rb") as f:
        return f.read()

def bank_off(bank, addr):
    """File offset of a banked address $4000-$7fff in `bank`."""
    return bank * 0x4000 + (addr - 0x4000)

def find_bytes(rom, pat, lo=0, hi=None):
    out, i = [], lo
    hi = len(rom) if hi is None else hi
    while True:
        j = rom.find(pat, i, hi)
        if j < 0:
            return out
        out.append(j)
        i = j + 1

def fmt_off(off):
    bank, within = off // 0x4000, off % 0x4000
    addr = within if bank == 0 else within + 0x4000
    return f"bank {bank} ${addr:04x} (file ${off:05x})"

def cmd_rst08(bank, lo, hi):
    """List every $cf (rst $08) byte in bank:lo-hi with following bytes."""
    rom = load()
    base = bank * 0x4000
    for addr in range(lo, hi):
        off = base + (addr - 0x4000 if bank else addr)
        if rom[off] == 0xCF:
            nxt = rom[off + 1:off + 33]
            words = [f"${nxt[i] | (nxt[i+1] << 8):04x}"
                     for i in range(0, min(32, len(nxt) - 1), 2)]
            print(f"${addr:04x}: rst $08 ; table? {' '.join(words[:8])}")

def cmd_findhex(hexpat, bank=None):
    rom = load()
    pat = bytes.fromhex(hexpat)
    lo = 0 if bank is None else bank * 0x4000
    hi = len(rom) if bank is None else (bank + 1) * 0x4000
    for off in find_bytes(rom, pat, lo, hi):
        print(f"{hexpat}: {fmt_off(off)}")

def cmd_dump(bank, addr, length):
    rom = load()
    off = bank_off(bank, addr) if bank else addr
    data = rom[off:off + length]
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        print(f"${addr + i:04x}: {' '.join(f'{b:02x}' for b in chunk)}")

if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "rst08":
        cmd_rst08(int(args[0]), int(args[1], 16), int(args[2], 16))
    elif cmd == "find":
        bank = int(args[1]) if len(args) > 1 else None
        cmd_findhex(args[0], bank)
    elif cmd == "dump":
        cmd_dump(int(args[0]), int(args[1], 16), int(args[2], 0))
    else:
        print("commands: rst08 <bank> <lo> <hi> | find <hex> [bank] | dump <bank> <addr> <len>")
