/* gb_wramdump: WRAM snapshot dumper for the DK94 decomp (slice 8).
 * Runs a ROM with a press spec + optional save, and dumps the full 8 KiB
 * WRAM ($c000-$dfff) at selected frames, so two runs (e.g. Mario standing
 * still vs walking right) can be diffed to find object/position variables.
 * Also dumps HRAM ($ff80-$fffe) alongside, for hGameState/hStateTimer.
 * Usage: gb_wramdump <rom.gb> <frames> <press_spec> <save_in|-> <outdir>
 *   <every_N_frames> <frame_lo> <frame_hi>
 *   press_spec: same "btn:start:end,..." windows as gb_headless ("-" = none).
 *   save_in: path to a .sav to preload, or "-" for fresh SRAM.
 * Writes <outdir>/wram_%05d.bin and <outdir>/hram_%05d.bin per dumped frame.
 * Build (from the decomp project root):
 *   cc -I ~/workspace/nacre/repo/include -I ~/workspace/nacre/repo/src/gb -O2 \
 *      -o tools/harnesses/gb_wramdump tools/harnesses/gb_wramdump.c \
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
#include <sys/stat.h>

int main(int argc, char **argv) {
    if (argc < 9) {
        fprintf(stderr, "usage: %s <rom.gb> <frames> <press_spec> <save_in|-> <outdir> <every_N> <frame_lo> <frame_hi>\n", argv[0]);
        return 2;
    }
    const char *rom_path = argv[1];
    int frames = atoi(argv[2]);
    const char *save_path = argv[4];
    const char *outdir = argv[5];
    int every = atoi(argv[6]), lo = atoi(argv[7]), hi = atoi(argv[8]);
    mkdir(outdir, 0755);

    typedef struct { GbButton btn; int start, end; } Press;
    Press presses[32]; int npress = 0;
    if (strcmp(argv[3], "-")) {
        char buf[1024];
        snprintf(buf, sizeof buf, "%s", argv[3]);
        for (char *tok = strtok(buf, ","); tok && npress < 32; tok = strtok(NULL, ",")) {
            char name[16]; int s, e;
            if (sscanf(tok, "%15[^:]:%d:%d", name, &s, &e) != 3) continue;
            static const char *names[GB_BUTTON_COUNT] = {
                "right", "left", "up", "down", "a", "b", "select", "start" };
            for (int b = 0; b < GB_BUTTON_COUNT; b++)
                if (!strcmp(name, names[b])) { presses[npress].btn = (GbButton)b; presses[npress].start = s; presses[npress].end = e; npress++; }
        }
    }

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
    free(rom);
    if (strcmp(save_path, "-")) {
        FILE *sf = fopen(save_path, "rb");
        if (sf) {
            fseek(sf, 0, SEEK_END); long slen = ftell(sf); fseek(sf, 0, SEEK_SET);
            uint8_t *sdata = malloc(slen);
            if (fread(sdata, 1, slen, sf) == (size_t)slen && gb_save_load(gb, sdata, (size_t)slen))
                printf("save-in: %s (%ld bytes)\n", save_path, slen);
            else
                printf("save-in: %s FAILED\n", save_path);
            free(sdata); fclose(sf);
        }
    }
    int dumped = 0;
    for (int i = 0; i < frames; i++) {
        for (int b = 0; b < GB_BUTTON_COUNT; b++) gb_set_button(gb, (GbButton)b, 0);
        for (int p = 0; p < npress; p++)
            if (i >= presses[p].start && i < presses[p].end)
                gb_set_button(gb, presses[p].btn, 1);
        if (!gb_run_cycles(gb, GB_CYCLES_PER_FRAME, err, sizeof err)) {
            fprintf(stderr, "cpu lockup at frame %d: %s\n", i, err); return 1;
        }
        if (i >= lo && i <= hi && ((i - lo) % every == 0)) {
            char path[512];
            snprintf(path, sizeof path, "%s/wram_%05d.bin", outdir, i);
            FILE *o = fopen(path, "wb");
            if (o) { fwrite(gb->wram, 1, 0x2000, o); fclose(o); }
            snprintf(path, sizeof path, "%s/hram_%05d.bin", outdir, i);
            o = fopen(path, "wb");
            if (o) { fwrite(gb->hram, 1, 0x80, o); fclose(o); }
            snprintf(path, sizeof path, "%s/vram_%05d.bin", outdir, i);
            o = fopen(path, "wb");
            if (o) { fwrite(gb->vram, 1, 0x2000, o); fclose(o); }
            dumped++;
        }
    }
    printf("dumped %d frames to %s\n", dumped, outdir);
    gb_destroy(gb);
    return 0;
}
