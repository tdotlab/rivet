import glob, os

base = 'build/nacre-test/slice13'
all_hits1, all_hits2 = [], []
subtype_hist = {}
stages_seen = {}
for n in range(25):
    d = f'{base}/prog{n}'
    for wf in sorted(glob.glob(d + '/wram_*.bin')):
        frame = int(wf.split('_')[-1].split('.')[0])
        w = open(wf, 'rb').read()
        hf = wf.replace('wram_', 'hram_')
        h = open(hf, 'rb').read() if os.path.exists(hf) else b''
        state = h[0x0e] if len(h) > 0x0e else None
        timer = h[0x10] if len(h) > 0x10 else None
        qidx = w[0x85c] | (w[0x85d] << 8)
        c829 = w[0x829]
        world, stage = w[0x860], w[0x861]
        n82 = 0
        h1, h2 = [], []
        for r in range(32):
            for c in range(32):
                o = 0x86d + r*128 + c*4
                b0, b1, b2, b3 = w[o], w[o+1], w[o+2], w[o+3]
                if b0 == 0x82:
                    n82 += 1
                    subtype_hist[b1] = subtype_hist.get(b1, 0) + 1
                    if b1 == 0x37:
                        h1.append((r, c))
                if b2 == 0x82 and b3 == 0x37:
                    h2.append((r, c))
        # only count dumps where a stage map is actually loaded (state 16/18/20 with map present)
        tag = f'prog{n} f{frame} st{state} t{timer} q{qidx} data{c829} w{world}-{stage} n82={n82}'
        if state in (16, 18) and n82 > 0:
            stages_seen.setdefault(c829, []).append(tag)
        if h1:
            all_hits1.append(tag + f' FIRST-PAIR HITS {h1}')
        if h2:
            all_hits2.append(tag + f' SECOND-PAIR HITS {h2}')
        print(tag + (f'  *** HITS1 {h1}' if h1 else '') + (f'  *** HITS2 {h2}' if h2 else ''))

print()
print('stages (data index c829) with a loaded map in state 16/18:', sorted(stages_seen))
print('count:', len(stages_seen))
for k in sorted(stages_seen):
    print(f'  data {k}: {stages_seen[k][0]}')
print()
print('$82 first-pair subtype histogram across all surveyed maps:', dict(sorted(subtype_hist.items())))
print()
print('FIRST-PAIR ($82,$37) hits:', all_hits1 if all_hits1 else 'NONE')
print('SECOND-PAIR ($82,$37) hits:', all_hits2 if all_hits2 else 'NONE')
