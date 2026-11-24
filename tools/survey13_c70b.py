import re
rom = open('roms/Donkey_Kong_World_Rev1_SGB.gb','rb').read()

def loc(off):
    bank = off//0x4000
    o = off%0x4000
    addr = o if bank == 0 else 0x4000+o
    return f'file {off:#x} bank {bank} addr ${addr:04x}'

print('== ld [$c70b],a  (ea 0b c7) ==')
for m in re.finditer(rb'\xea\x0b\xc7', rom):
    print(' ', loc(m.start()))
print('== ld hl,$c70b  (21 0b c7) ==')
for m in re.finditer(rb'\x21\x0b\xc7', rom):
    print(' ', loc(m.start()))
print('== ld a,[$c70b]  (fa 0b c7) ==')
for m in re.finditer(rb'\xfa\x0b\xc7', rom):
    print(' ', loc(m.start()))
print('== ld hl,$ff90  (21 90 ff) ==')
for m in re.finditer(rb'\x21\x90\xff', rom):
    print(' ', loc(m.start()))
print('== ldh [hStateTimer],a variants: e0 90 already done; ld [$ff90],a (ea 90 ff) ==')
for m in re.finditer(rb'\xea\x90\xff', rom):
    print(' ', loc(m.start()))
print('== dec [hl] / inc [hl] near $ff90 handled by hand ==')
# find all 'ld a,$xx' immediately before 'ld [hl],a' where hl was $ff90 is too fuzzy; instead list
# every occurrence of bytes 34/35 (inc/dec [hl]) and print context for manual triage is too noisy.
# Instead: search for the two-byte sequence 21 90 ff then dump following 8 bytes.
print('== $ff90 hl-load contexts ==')
for m in re.finditer(rb'\x21\x90\xff', rom):
    ctx = rom[m.start():m.start()+10].hex(' ')
    print(f'  {loc(m.start())}: {ctx}')
