rom = open('roms/Donkey_Kong_World_Rev1_SGB.gb','rb').read()
# bank 12 queue table at $4f97, 331 (C,B) pairs
base = 12*0x4000 + (0x4f97-0x4000)
entries = [(rom[base+2*i], rom[base+2*i+1]) for i in range(331)]
from collections import Counter
print('C histogram:', dict(Counter(c for c,_ in entries)))
print('C==4 indices:', [i for i,(c,_) in enumerate(entries) if c==4])
print()
print('C==4 entries with predecessor and successor:')
for i,(c,b) in enumerate(entries):
    if c==4:
        prev = entries[i-1] if i>0 else None
        nxt = entries[i+1] if i<331 else None
        print(f'  idx {i}: (4,{b}) prev={prev} next={nxt}')
print()
print('entries 13..45:')
for i in range(13,46):
    print(f'  {i}: {entries[i]}')
