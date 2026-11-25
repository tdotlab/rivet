import glob, os

d = 'build/nacre-test/slice13/maps'
rows = []
for wf in sorted(glob.glob(d + '/wram_*.bin')):
    frame = int(wf.split('_')[-1].split('.')[0])
    w = open(wf, 'rb').read()
    hf = wf.replace('wram_', 'hram_')
    h = open(hf, 'rb').read() if os.path.exists(hf) else b''
    state = h[0x0e] if len(h) > 0x0e else None
    timer = h[0x10] if len(h) > 0x10 else None
    qidx = w[0x85c] | (w[0x85d] << 8)
    c829 = w[0x829]
    world = w[0x860]
    stage = w[0x861]
    c858 = w[0x858]
    # scan $c86d-$d86d (offsets 0x86d..0xd86d), 32 rows x 32 cols x 4 bytes
    hits1 = []  # first pair ($82,$37)
    hits2 = []  # second pair ($82,$37)
    n82 = 0
    for r in range(32):
        for c in range(32):
            o = 0x86d + r*128 + c*4
            b0, b1, b2, b3 = w[o], w[o+1], w[o+2], w[o+3]
            if b0 == 0x82:
                n82 += 1
                if b1 == 0x37:
                    hits1.append((r, c, b2, b3))
            if b2 == 0x82 and b3 == 0x37:
                hits2.append((r, c, b0, b1))
    rows.append((frame, state, timer, qidx, c829, world, stage, c858, n82, hits1, hits2))

print('frame state timer qidx c829 world stage c858 n$82 hits1 hits2')
seen_stages = {}
for (frame, state, timer, qidx, c829, world, stage, c858, n82, h1, h2) in rows:
    print(f'{frame:6d} {state:5} {timer:5} {qidx:4} {c829:4} {world:5} {stage:5} {c858:4} {n82:4} {h1} {h2}')
    if state in (16, 20):
        seen_stages.setdefault(c829, []).append(frame)
print()
print('stages (c829) seen in state 16/20 dumps:', sorted(seen_stages))
print('count:', len(seen_stages))
print()
print('ANY first-pair ($82,$37) hits:', [r for r in rows if r[9]])
print('ANY second-pair ($82,$37) hits:', [r for r in rows if r[10]])
