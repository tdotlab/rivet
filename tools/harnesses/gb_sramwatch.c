/* SRAM-write watcher for the DK94 decomp (slice 6).
 * Runs a ROM and reports the first frame each byte in a chosen SRAM
 * range changes, with the CPU state at that moment (PC, bank, game
 * state, timer) -- so a mystery SRAM writer can be identified by
 * when/where it fires, without a debugger watchpoint.
 * Usage: gb_sramwatch <rom.gb> <frames> [press_spec] [lo_hex] [hi_hex]
 *   press_spec: same "btn:start:end,..." windows as gb_headless.
 *   lo_hex/hi_hex: SRAM addresses ($a000-$bfff) to watch, default
 *   b4ca-b927 (the mystery region from slice 5). Prints one line per
 *   first-changed byte (coalesced: consecutive bytes changed in the
 *   same frame print as one range line) plus a per-frame summary.
 * Build (from the decomp project root):
 *   cc -I ~/workspace/nacre/repo/include -I ~/workspace/nacre/repo/src/gb -O2 \
 *      -o tools/harnesses/gb_sramwatch tools/harnesses/gb_sramwatch.c \
 *      ~/workspace/nacre/repo/src/gb/gb.c ~/workspace/nacre/repo/src/gb/gb_cpu.c \
 *      ~/workspace/nacre/repo/src/gb/gb_ppu.c ~/workspace/nacre/repo/src/gb/gb_cart.c \
 *      ~/workspace/nacre/repo/src/gb/gb_apu.c
 */
#include "gb.h"
#include "gb_internal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: %s <rom.gb> <frames> [press_spec] [lo_hex] [hi_hex]\n", argv[0]); return 2; }
    const char *rom_path = argv[1];
    int frames = atoi(argv[2]);
    typedef struct { GbButton btn; int start, end; } Press;
    Press presses[16]; int npress = 0;
    if (argc >= 4 && argv[3][0]) {
        char spec[512];
        snprintf(spec, sizeof spec, "%s", argv[3]);
        for (char *tok = strtok(spec, ","); tok && npress < 16; tok = strtok(NULL, ",")) {
            char name[16]; int s, e;
            if (sscanf(tok, "%15[^:]:%d:%d", name, &s, &e) != 3) continue;
            static const char *names[GB_BUTTON_COUNT] = {
                "right", "left", "up", "down", "a", "b", "select", "start" };
            for (int b = 0; b < GB_BUTTON_COUNT; b++)
                if (!strcmp(name, names[b])) { presses[npress].btn = (GbButton)b; presses[npress].start = s; presses[npress].end = e; npress++; }
        }
    }
    unsigned lo = 0xb4ca, hi = 0xb927;
    if (argc >= 5) sscanf(argv[4], "%x", &lo);
    if (argc >= 6) sscanf(argv[5], "%x", &hi);
    if (lo < 0xa000) lo = 0xa000;
    if (hi > 0xbfff) hi = 0xbfff;
    FILE *f = fopen(rom_path, "rb");
    if (!f) { perror("open rom"); return 1; }
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *rom = malloc(len);
    if (fread(rom, 1, len, f) != (size_t)len) { fprintf(stderr, "short read\n"); return 1; }
    fclose(f);
    Gb *gb = gb_create();
    char err[256] = {0};
    if (!gb_load_rom(gb, rom, (size_t)len, err, sizeof err)) {
        fprintf(stderr, "gb_load_rom failed: %s\n", err); return 1;
    }
    size_t ssize = gb_save_size(gb);
    uint8_t *prev = malloc(ssize), *cur = malloc(ssize);
    gb_save_write(gb, prev, ssize);
    uint8_t *seen = calloc(hi - lo + 1, 1);
    printf("# watching SRAM $%04x-$%04x over %d frames\n", lo, hi, frames);
    for (int i = 0; i < frames; i++) {
        for (int b = 0; b < GB_BUTTON_COUNT; b++) gb_set_button(gb, (GbButton)b, 0);
        for (int p = 0; p < npress; p++)
            if (i >= presses[p].start && i < presses[p].end)
                gb_set_button(gb, presses[p].btn, 1);
        if (!gb_run_cycles(gb, GB_CYCLES_PER_FRAME, err, sizeof err)) {
            fprintf(stderr, "cpu lockup at frame %d: %s\n", i, err); return 1;
        }
        gb_save_write(gb, cur, ssize);
        int state = gb->hram[0x0e], timer = gb->hram[0x10], bank = gb->hram[0x0c];
        /* coalesce consecutive first-changes in this frame into ranges */
        unsigned a = lo;
        while (a <= hi) {
            size_t off = a - 0xa000;
            if (!seen[a - lo] && cur[off] != prev[off]) {
                unsigned b = a;
                while (b + 1 <= hi && !seen[b + 1 - lo] && cur[b + 1 - 0xa000] != prev[b + 1 - 0xa000]) b++;
                printf("frame %d pc %04x bank %d state %d timer %d: $%04x-$%04x first write (was %02x -> %02x%s)\n",
                       i, gb->pc, bank, state, timer, a, b, prev[a - 0xa000], cur[a - 0xa000],
                       b > a ? ", ..." : "");
                for (unsigned k = a; k <= b; k++) seen[k - lo] = 1;
                a = b + 1;
            } else a++;
        }
        memcpy(prev, cur, ssize);
    }
    int n = 0; for (unsigned a = lo; a <= hi; a++) if (seen[a - lo]) n++;
    printf("# %d/%u watched bytes changed at least once; save_dirty=%d\n",
           n, hi - lo + 1, gb_save_dirty(gb));
    return 0;
}
