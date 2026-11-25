# Rivet

A byte-matching Game Boy disassembly of **Donkey Kong (World) (Rev 1) (SGB Enhanced)**, written in RGBDS assembly. This is not a copy of an existing disassembly.

Rivet is a study of how the game works: its code, tables, game data, and the systems that tie them together. It includes research notes and tools used to investigate the original, along with a test harness built around [Nacre](https://github.com/tdotlab/nacre), a Game Boy emulator.

## Status

All 32 ROM banks are represented in the assembly source, with no `INCBIN` directives. The original 512 KiB image is represented as instructions, data, tables, and padding; coverage does **not** mean every routine or data structure is understood. The project has rebuilt a ROM matching the original's SHA-1. The door/level-clear path and exact replay behavior remain areas of investigation. See [PROGRESS.md](PROGRESS.md) for findings, corrections, and test records.

This is a disassembly, not a C or Rust reimplementation. A byte match confirms the rebuilt bytes; it does not by itself confirm that every label or explanation is correct.

## Build

The build requires [RGBDS 1.0.4](https://github.com/gbdev/rgbds/releases/tag/v1.0.4), `make`, and a local copy of the target ROM. The ROM is not included in the repository. Do not commit or distribute ROMs, rebuilt ROMs, or saves.

Target revision:

- **Donkey Kong (World) (Rev 1) (SGB Enhanced)**
- Size: 524,288 bytes (512 KiB)
- SHA-1: `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`
- MD5: `4859ec2b18c4fabf489eb570c1d7d326`

Place your own dump at `roms/Donkey_Kong_World_Rev1_SGB.gb`. The build currently requires that file even though the assembly no longer includes bytes from it; the checksum check compares the rebuilt ROM against the expected SHA-1.

```sh
make RGBDS=/path/to/rgbds-1.0.4
make clean
```

`RGBDS` is the directory containing `rgbasm`, `rgblink`, and `rgbfix`. Without an override, the Makefile looks in `~/workspace/tools/rgbds-1.0.4`. The output is `build/game.gb`; a successful `make` checks its SHA-1. The local ROM and build directory are ignored by Git.

## Repository layout

```text
src/
  main.asm           Entry point, vectors, and assembly includes
  constants.asm      RAM variables and constants
  hardware.inc       Hardware register definitions
  banks.asm          Generated bank padding
  core/              State, frame, transfer, decompression, and SGB code
  banks/             Bank-specific code and data, including slice files
tools/
  gb_rd.py           Recursive-descent disassembler
  generators/        Slice and bank source generators
  surveys/           Research scripts and experiments
  harnesses/         Nacre-based runners and memory watchers (C source)
  tests/             Nacre regression scripts
  analyze_rom.py     ROM header and bank analysis
  count_curated.py   Historical INCBIN coverage counter
tests/               Repository layout checks
docs/BANKMAP.md      ROM and bank-map notes
PROGRESS.md          Dated research log and verification records
```

Run `python3 -m unittest discover -s tests -v` for the layout checks. The tools generally assume they are run from the repository root. Research scripts and generators are kept as part of the investigation; many require the original ROM, Nacre, additional tools, or prior files in `build/`. The recursive-descent disassembler uses mgbdis's `instruction_set.py`: put mgbdis at `~/workspace/tools/mgbdis` or set `MGBDIS_DIR` to its directory. The paths in dated progress entries reflect the layout at the time.

**The slice generators are historical research tools, not a clean rebuild pipeline.** Rerunning an older one can overwrite later corrections; some can modify files before failing. Read them first and use a disposable checkout if you experiment. See [the generator notes](tools/generators/README.md).

The Nacre harnesses are separate from the RGBDS build and need Nacre's Game Boy core to compile. The regression scripts in `tools/tests/` additionally expect their corresponding harness binaries and, for some cases, saved test fixtures; see the scripts before running them. Their recorded results are in [PROGRESS.md](PROGRESS.md).

## References

- [RGBDS](https://github.com/gbdev/rgbds) — Game Boy assembler, linker, and tools.
- [mgbdis](https://github.com/mattcurrie/mgbdis) — used as an initial disassembly scaffold and cross-check.
- [CelestialAmber/DKGBDisasm](https://github.com/CelestialAmber/DKGBDisasm) — an earlier disassembly of a different ROM revision, consulted as a reference.
- [gnome41/DK94-SGB](https://github.com/gnome41/DK94-SGB) — a recompilation of the same ROM revision, consulted as a cross-check.

Donkey Kong and Game Boy are trademarks of Nintendo. Rivet is an independent research project and is not affiliated with Nintendo.
