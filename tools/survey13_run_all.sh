#!/bin/bash
# Slice 13: survey stages 0,4,8,...,96 (progress 0..24) for ($82,$37) map cells.
# Each progress-N save starts at queue 13N; the (2,B) map visit -> (3,1) -> (1,4N) load.
cd ~/workspace/mike-monorepo/donkey-kong-decomp
for n in $(seq 0 24); do
  if [ ! -f build/nacre-test/slice13/save-prog$n.sav ]; then
    python3 tools/make_progress_save.py build/nacre-test/slice6/save-prog1.sav build/nacre-test/slice13/save-prog$n.sav $n > /dev/null 2>&1 || echo "save $n FAILED"
  fi
  mkdir -p build/nacre-test/slice13/prog$n
  timeout 300 ./tools/gb_wramdump roms/Donkey_Kong_World_Rev1_SGB.gb 5000 "start:620:632,a:1000:1012,a:2000:2012" build/nacre-test/slice13/save-prog$n.sav build/nacre-test/slice13/prog$n 400 2800 3600 > /dev/null 2>&1
done
echo done
