/* gb_watch: write-watchpoint probe for the DK94 decomp (slice 8).
 * Nacre has no debugger watchpoints, so this emulates one in two passes:
 *   pass 1: frame-step the run, recording every frame where a watched
 *     byte changes (or matches an addr=value filter), with state/timer/
 *     bank at that frame.
 *   pass 2: re-run from scratch, frame-step to a chosen frame, then
 *     cycle-step that single frame (1 cycle per gb_run_cycles call),
 *     logging the exact instruction (PC before the step) that wrote the
 *     watched byte, plus a ring of the last executed instructions so
 *     the call path is visible.
 * Usage: gb_watch <rom.gb> <frames> <press_spec> <save_in|-> <watch_spec>
 *   [refine_frame]
 *   press_spec: same "btn:start:end,..." windows as gb_headless ("-" = none).
 *   save_in: path to a .sav to preload, or "-" for fresh SRAM.
 *   watch_spec: comma list of hex addresses in $c000-$dfff (WRAM) or
 *     $ff80-$fffe (HRAM), optionally addr=value (log only when the byte
 *     BECOMES value), e.g. "c860,c861" or "ff90=12".
 *   refine_frame: frame to cycle-step (-1 or omitted = first pass-1 hit).
 * Examples:
 *   gb_watch rom.gb 1500 "start:620:632,a:1000:1012,a:2000:2012" save.sav c860,c861
 *     -- find the instruction that writes world/stage during the map visit.
 *   gb_watch rom.gb 3000 "start:620:632,a:1000:1012,a:2000:2012,right:2500:3000,a:2600:2612,a:2900:2912" save.sav ff90=12
 *     -- find the instruction that sets hStateTimer=12 on a death.
 * Build (from the decomp project root):
 *   cc -I ~/workspace/nacre/repo/include -I ~/workspace/nacre/repo/src/gb -O2 \
 *      -o tools/gb_watch tools/gb_watch.c \
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

typedef struct { GbButton btn; int start, end; } Press;
static Press presses[32]; static int npress = 0;

static void parse_press(const char *spec) {
    if (!spec || !spec[0] || !strcmp(spec, "-")) return;
    char buf[1024];
    snprintf(buf, sizeof buf, "%s", spec);
    for (char *tok = strtok(buf, ","); tok && npress < 32; tok = strtok(NULL, ",")) {
        char name[16]; int s, e;
        if (sscanf(tok, "%15[^:]:%d:%d", name, &s, &e) != 3) continue;
        static const char *names[GB_BUTTON_COUNT] = {
            "right", "left", "up", "down", "a", "b", "select", "start" };
        for (int b = 0; b < GB_BUTTON_COUNT; b++)
            if (!strcmp(name, names[b])) { presses[npress].btn = (GbButton)b; presses[npress].start = s; presses[npress].end = e; npress++; }
    }
}

static void apply_buttons(Gb *gb, int frame) {
    for (int b = 0; b < GB_BUTTON_COUNT; b++) gb_set_button(gb, (GbButton)b, 0);
    for (int p = 0; p < npress; p++)
        if (frame >= presses[p].start && frame < presses[p].end)
            gb_set_button(gb, presses[p].btn, 1);
}

typedef struct { int addr; int has_value; int value; } Watch;
static Watch watches[16]; static int nwatch = 0;

static uint8_t read_addr(Gb *gb, int addr) {
    if (addr >= 0xc000 && addr <= 0xdfff) return gb->wram[addr - 0xc000];
    if (addr >= 0xff80 && addr <= 0xfffe) return gb->hram[addr - 0xff80];
    return 0;
}

static Gb *load_rom(const char *rom_path, const char *save_path) {
    FILE *f = fopen(rom_path, "rb");
    if (!f) { perror("open rom"); return NULL; }
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *rom = malloc(len);
    if (fread(rom, 1, len, f) != (size_t)len) { fprintf(stderr, "short read\n"); return NULL; }
    fclose(f);
    Gb *gb = gb_create();
    char err[256] = {0};
    if (!gb_load_rom(gb, rom, (size_t)len, err, sizeof err)) {
        fprintf(stderr, "gb_load_rom failed: %s\n", err); return NULL;
    }
    free(rom);
    if (save_path && strcmp(save_path, "-")) {
        FILE *sf = fopen(save_path, "rb");
        if (sf) {
            fseek(sf, 0, SEEK_END); long slen = ftell(sf); fseek(sf, 0, SEEK_SET);
            uint8_t *sdata = malloc(slen);
            if (fread(sdata, 1, slen, sf) == (size_t)slen && gb_save_load(gb, sdata, (size_t)slen))
                printf("save-in: %s (%ld bytes)\n", save_path, slen);
            else
                printf("save-in: %s FAILED\n", save_path);
            free(sdata); fclose(sf);
        } else printf("save-in: %s not found, fresh SRAM\n", save_path);
    }
    return gb;
}

/* ring of recently executed instructions (pc, bank), deduped on pc */
#define RINGN 128
static uint16_t ring_pc[RINGN]; static uint8_t ring_bank[RINGN];
static int ring_head = 0, ring_count = 0;
static void ring_push(uint16_t pc, uint8_t bank) {
    if (ring_count && ring_pc[(ring_head + RINGN - 1) % RINGN] == pc) return;
    ring_pc[ring_head] = pc; ring_bank[ring_head] = bank;
    ring_head = (ring_head + 1) % RINGN;
    if (ring_count < RINGN) ring_count++;
}
static void ring_dump(int n) {
    int start = ring_count < n ? 0 : ring_count - n;
    printf("  last %d executed instrs (pc/bank):\n", ring_count - start);
    for (int i = start; i < ring_count; i++) {
        int idx = (ring_head - ring_count + i + RINGN) % RINGN;
        printf("    %04x/%02x", ring_pc[idx], ring_bank[idx]);
        if ((i - start) % 6 == 5) printf("\n");
    }
    if ((ring_count - start) % 6) printf("\n");
}

int main(int argc, char **argv) {
    if (argc < 6) {
        fprintf(stderr, "usage: %s <rom.gb> <frames> <press_spec> <save_in|-> <watch_spec> [refine_frame]\n", argv[0]);
        return 2;
    }
    const char *rom_path = argv[1];
    int frames = atoi(argv[2]);
    parse_press(argv[3]);
    const char *save_path = argv[4];
    /* watch spec: addr or addr=value, comma-separated */
    {
        char buf[512];
        snprintf(buf, sizeof buf, "%s", argv[5]);
        for (char *tok = strtok(buf, ","); tok && nwatch < 16; tok = strtok(NULL, ",")) {
            unsigned a = 0, v = 0; int has = 0;
            if (sscanf(tok, "%x=%x", &a, &v) == 2) has = 1;
            else if (sscanf(tok, "%x", &a) != 1) continue;
            if (!((a >= 0xc000 && a <= 0xdfff) || (a >= 0xff80 && a <= 0xfffe))) {
                fprintf(stderr, "watch addr %04x out of range (need $c000-$dfff or $ff80-$fffe)\n", a);
                return 2;
            }
            watches[nwatch].addr = (int)a; watches[nwatch].has_value = has; watches[nwatch].value = (int)v;
            nwatch++;
        }
    }
    int refine = -1;
    if (argc >= 7) refine = atoi(argv[6]);

    char err[256] = {0};
    /* ---- pass 1: frame-step, find hit frames ---- */
    Gb *gb = load_rom(rom_path, save_path);
    if (!gb) return 1;
    uint8_t prev[16];
    for (int w = 0; w < nwatch; w++) prev[w] = read_addr(gb, watches[w].addr);
    int first_hit = -1, nhits = 0;
    printf("# pass 1: frame-step %d frames, watching", frames);
    for (int w = 0; w < nwatch; w++)
        printf(" %04x%s", watches[w].addr, watches[w].has_value ? "(=val)" : "");
    printf("\n");
    for (int i = 0; i < frames; i++) {
        apply_buttons(gb, i);
        if (!gb_run_cycles(gb, GB_CYCLES_PER_FRAME, err, sizeof err)) {
            fprintf(stderr, "cpu lockup at frame %d: %s\n", i, err); return 1;
        }
        int state = gb->hram[0x0e], timer = gb->hram[0x10], bank = gb->hram[0x0c];
        for (int w = 0; w < nwatch; w++) {
            uint8_t cur = read_addr(gb, watches[w].addr);
            int hit = 0;
            if (watches[w].has_value)
                hit = (cur == watches[w].value && prev[w] != watches[w].value);
            else
                hit = (cur != prev[w]);
            if (hit) {
                printf("HIT frame %d addr $%04x %02x->%02x state=%d timer=%d bank=%d pc=%04x\n",
                       i, watches[w].addr, prev[w], cur, state, timer, bank, gb->pc);
                if (first_hit < 0) first_hit = i;
                nhits++;
            }
            prev[w] = cur;
        }
    }
    printf("# pass 1 done: %d hits, first at frame %d\n", nhits, first_hit);
    gb_destroy(gb);
    if (nhits == 0) return 0;
    int target = (refine >= 0) ? refine : first_hit;
    if (target >= frames) { fprintf(stderr, "refine frame %d beyond run\n", target); return 1; }

    /* ---- pass 2: re-run, cycle-step the target frame ---- */
    printf("# pass 2: cycle-stepping frame %d\n", target);
    gb = load_rom(rom_path, save_path);
    if (!gb) return 1;
    for (int w = 0; w < nwatch; w++) prev[w] = read_addr(gb, watches[w].addr);
    for (int i = 0; i < target; i++) {
        apply_buttons(gb, i);
        if (!gb_run_cycles(gb, GB_CYCLES_PER_FRAME, err, sizeof err)) {
            fprintf(stderr, "cpu lockup at frame %d: %s\n", i, err); return 1;
        }
        for (int w = 0; w < nwatch; w++) prev[w] = read_addr(gb, watches[w].addr);
    }
    apply_buttons(gb, target);
    ring_head = 0; ring_count = 0;
    int logged = 0;
    for (uint32_t c = 0; c < GB_CYCLES_PER_FRAME; c++) {
        uint16_t pc_before = gb->pc;
        uint8_t bank_before = gb->hram[0x0c];
        ring_push(pc_before, bank_before);
        if (!gb_run_cycles(gb, 1, err, sizeof err)) {
            fprintf(stderr, "cpu lockup at frame %d cycle %u: %s\n", target, c, err); return 1;
        }
        for (int w = 0; w < nwatch; w++) {
            uint8_t cur = read_addr(gb, watches[w].addr);
            int hit = 0;
            if (watches[w].has_value)
                hit = (cur == watches[w].value && prev[w] != watches[w].value);
            else
                hit = (cur != prev[w]);
            if (hit) {
                int state = gb->hram[0x0e], timer = gb->hram[0x10];
                printf("WRITE frame %d cycle %u addr $%04x %02x->%02x by instr at pc=%04x bank=%02x (pc now %04x) state=%d timer=%d\n",
                       target, c, watches[w].addr, prev[w], cur, pc_before, bank_before, gb->pc, state, timer);
                printf("  regs at write: A=%02x B=%02x C=%02x D=%02x E=%02x H=%02x L=%02x HL=%04x rom_bank=%d\n",
                       gb->a, gb->b, gb->c, gb->d, gb->e, gb->h, gb->l,
                       (unsigned)(gb->h << 8 | gb->l), gb->cart.rom_bank);
                ring_dump(128);
                logged++;
            }
            prev[w] = cur;
        }
    }
    printf("# pass 2 done: %d writes logged in frame %d\n", logged, target);
    gb_destroy(gb);
    return 0;
}
