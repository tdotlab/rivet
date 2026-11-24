import re
rom = open('roms/Donkey_Kong_World_Rev1_SGB.gb','rb').read()
# literal timer setters: ld a,imm; ldh [hStateTimer],a  -> 3e XX e0 90
for m in re.finditer(rb'\x3e(.)\xe0\x90', rom):
    bank = m.start()//0x4000
    off = m.start()%0x4000
    addr = off if bank == 0 else 0x4000+off
    print(f'timer ${m.group(1)[0]:02x} ({m.group(1)[0]:3d}) at file {m.start():#x} bank {bank} addr ${addr:04x}')
print('---')
# ld a,imm; ld [hl],a with hl=$ff90 pattern is harder; also search ld [$ff90],a (ea 90 ff)
for m in re.finditer(rb'\x3e(.)\xea\x90\xff', rom):
    bank = m.start()//0x4000
    off = m.start()%0x4000
    addr = off if bank == 0 else 0x4000+off
    print(f'ld[$ff90] timer ${m.group(1)[0]:02x} ({m.group(1)[0]:3d}) at file {m.start():#x} bank {bank} addr ${addr:04x}')
print('--- timer 22/23/26 literal setters only ---')
for m in re.finditer(rb'\x3e([\x16\x17\x1a])\xe0\x90', rom):
    bank = m.start()//0x4000
    off = m.start()%0x4000
    addr = off if bank == 0 else 0x4000+off
    print(f'timer ${m.group(1)[0]:02x} at file {m.start():#x} bank {bank} addr ${addr:04x}')
