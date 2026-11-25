# Donkey Kong '94 disassembly -- build the ROM from src/ with RGBDS.
# RGBDS lives at ~/workspace/tools/rgbds-1.0.4 (portable install, v1.0.4).
# Override with: make RGBDS=/path/to/rgbds
RGBDS ?= $(HOME)/workspace/tools/rgbds-1.0.4
RGBASM := $(RGBDS)/rgbasm
RGBLINK := $(RGBDS)/rgblink
RGBFIX := $(RGBDS)/rgbfix

ROM := roms/Donkey_Kong_World_Rev1_SGB.gb
OUT := build/game.gb
EXPECTED_SHA1 := 397ad2ff25627b83e02c71b54c72bb4deb39e0c0

all: $(OUT) check

SOURCES := $(wildcard src/*.asm src/*.inc) $(wildcard src/banks/*.asm) $(wildcard src/core/*.asm)

$(OUT): $(SOURCES) $(ROM)
	@mkdir -p build
	$(RGBASM) -I src -o build/game.o src/main.asm
	$(RGBLINK) -n build/game.sym -m build/game.map -o $@ build/game.o
	$(RGBFIX) -v -p 0xff $@

# Byte-match check: the rebuilt ROM must be identical to the original.
check: $(OUT)
	@echo "rebuilt: $$(sha1sum $(OUT) | cut -d' ' -f1)"
	@echo "expected: $(EXPECTED_SHA1)"
	@printf '%s  %s\n' '$(EXPECTED_SHA1)' '$(OUT)' | sha1sum -c - && echo "BYTE-MATCH: rebuilt ROM == original ROM"

clean:
	rm -f build/game.o build/game.gb build/game.sym build/game.map

.PHONY: all check clean
