#!/usr/bin/env python3
"""Scan slice-13 full-survey dumps (build/nacre-test/slice13/full/B*)
for ($82,$37) map cells and $5b $0b trigger cells, per stage-data B.

A dump counts if its c829 matches the directory's B and the $c86d
map is present (n$82 > 0). State-20 dumps with a loaded map (stage
ended, retry) are valid stage maps; state-20 map-visit dumps have
n$82 == 0 and are excluded by the n$82 > 0 test.
Also scans the progress-survey dumps (prog0..prog24) for comparison.
"""
import glob
import os

def scan_dump(wf):
    w = open(wf, 'rb').read()
    hf = wf.replace('wram_', 'hram_')
    h = open(hf, 'rb').read() if os.path.exists(hf) else b''
    state = h[0x0e] if len(h) > 0x0e else None
    timer = h[0x10] if len(h) > 0x10 else None
    qidx = w[0x85c] | (w[0x85d] << 8)
    c829 = w[0x829]
    world, stage = w[0x860], w[0x861]
    n82 = 0
    h37, h5b = [], []
    for r in range(32):
        for c in range(32):
            o = 0x86d + r * 128 + c * 4
            b0, b1, b2, b3 = w[o], w[o + 1], w[o + 2], w[o + 3]
            if b0 == 0x82:
                n82 += 1
                if b1 == 0x37:
                    h37.append((r, c))
            if b2 == 0x82 and b3 == 0x37:
                h37.append((r, c, '2nd'))
            for pair in (0, 2):
                if w[o + pair] == 0x0b and w[o + pair + 1] == 0x5b:
                    h5b.append((r, c, pair))
    return dict(state=state, timer=timer, qidx=qidx, c829=c829,
                world=world, stage=stage, n82=n82, h37=h37, h5b=h5b)

results = {}
for d in sorted(glob.glob('build/nacre-test/slice13/full/B*')):
    b = int(d.split('B')[-1])
    hits37, hits5b, nmaps = [], [], 0
    states = set()
    for wf in sorted(glob.glob(d + '/wram_*.bin')):
        s = scan_dump(wf)
        states.add((s['state'], s['timer']))
        if s['c829'] != b or s['n82'] == 0:
            continue
        nmaps += 1
        if s['h37']:
            hits37.append((wf.split('_')[-1], len(s['h37'])))
        if s['h5b']:
            hits5b.append((wf.split('_')[-1], s['h5b']))
    results[b] = dict(nmaps=nmaps, hits37=hits37, hits5b=hits5b,
                      states=sorted(states))
    tag = f'B{b:3d}: maps={nmaps} states={sorted(states)}'
    if hits37:
        tag += f'  ($82,$37) x{hits37[0][1]} in {hits37[0][0]}'
    if hits5b:
        tag += f'  $5b {hits5b[0][1]}'
    print(tag)

print()
print('stages with ($82,$37):', [b for b, r in sorted(results.items())
                                 if r['hits37']])
print('stages with $5b:', [b for b, r in sorted(results.items())
                           if r['hits5b']])
print('stages with NO valid map:', [b for b, r in sorted(results.items())
                                    if r['nmaps'] == 0])
print('stages surveyed (valid map):', len([b for b, r in results.items()
                                           if r['nmaps'] > 0]))
