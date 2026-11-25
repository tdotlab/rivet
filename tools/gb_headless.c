/* Headless Game Boy test harness for the DK94 disassembly.
 * Links Nacre's GB core (~/workspace/nacre/repo/src/gb/, include/gb.h)
 * -- it does NOT modify Nacre. Runs a ROM for N frames, writes the
 * 160x144 framebuffer as a PPM, and prints a SHA-256 of the raw
 * shade bytes plus the frame count, so an original ROM and a rebuilt
 * ROM can be compared exactly.
 * Usage: gb_headless <rom.gb> <frames> <out.ppm>
 *   [press_spec] [trace_file] [save_in.sav] [save_out.sav]
 * The optional press spec is a comma-separated list of BTN:START:END
 * windows, e.g. "start:620:632,a:1000:1012" (buttons: start, a, b, select,
 * up, down, left, right; each held for frames [START, END)). The optional
 * trace file logs one line per frame where hGameState, hStateTimer,
 * hCurrentBank or hSTATState changes, plus a heartbeat every 60 frames,
 * so the real state flow can be checked against the disassembly.
 * The optional save files exercise the battery SRAM: save_in is loaded
 * into cartridge RAM before frame 0 (missing file = fresh SRAM, all
 * $ff); save_out is written after the last frame, and the run prints
 * whether the game wrote SRAM at all (gb_save_dirty). Used for the
 * save-RAM tests (state 28 file 1 + A writes a save, $09f0 then
 * routes a later boot to states 21/22).
 * Env GB_WATCH (slice 5): comma-separated hex WRAM addresses in
 * $c000-$dfff, e.g. GB_WATCH=c858,c860,da4b,c711,c712 -- their values
 * are appended to every trace line, so a state transition can be read
 * against the flags that caused it. Unset = trace format unchanged.
 * Build (from the decomp project root):
 *   cc -I ~/workspace/nacre/repo/include -I ~/workspace/nacre/repo/src/gb -O2 \
 *      -o tools/gb_headless tools/gb_headless.c \
 *      ~/workspace/nacre/repo/src/gb/gb.c ~/workspace/nacre/repo/src/gb/gb_cpu.c \
 *      ~/workspace/nacre/repo/src/gb/gb_ppu.c ~/workspace/nacre/repo/src/gb/gb_cart.c \
 *      ~/workspace/nacre/repo/src/gb/gb_apu.c
 * (gb_internal.h is included only to read HRAM/PC for the trace; Nacre
 * itself is not modified.)
 * Nacre starts from the post-boot-ROM state (no Nintendo logo scroll);
 * no buttons are pressed, so this tests boot -> title screen only.
 */
#include "gb.h"
#include "gb_internal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* Minimal SHA-256 (public-domain style, written for this harness). */
typedef struct { uint32_t h[8]; uint64_t len; uint8_t buf[64]; size_t n; } Sha256;
static const uint32_t K256[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2 };
static uint32_t rotr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
static void sha_block(Sha256 *s, const uint8_t *p) {
    uint32_t w[64];
    for (int i = 0; i < 16; i++) w[i] = (uint32_t)p[i*4]<<24 | (uint32_t)p[i*4+1]<<16 | (uint32_t)p[i*4+2]<<8 | p[i*4+3];
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = rotr(w[i-15],7) ^ rotr(w[i-15],18) ^ (w[i-15]>>3);
        uint32_t s1 = rotr(w[i-2],17) ^ rotr(w[i-2],19) ^ (w[i-2]>>10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    uint32_t a=s->h[0],b=s->h[1],c=s->h[2],d=s->h[3],e=s->h[4],f=s->h[5],g=s->h[6],h=s->h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t S1 = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25), ch = (e & f) ^ (~e & g);
        uint32_t t1 = h + S1 + ch + K256[i] + w[i];
        uint32_t S0 = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22), mj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2 = S0 + mj;
        h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    s->h[0]+=a; s->h[1]+=b; s->h[2]+=c; s->h[3]+=d; s->h[4]+=e; s->h[5]+=f; s->h[6]+=g; s->h[7]+=h;
}
static void sha_init(Sha256 *s) {
    static const uint32_t H0[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    memcpy(s->h, H0, sizeof H0); s->len = 0; s->n = 0;
}
static void sha_update(Sha256 *s, const uint8_t *p, size_t n) {
    s->len += n;
    while (n) {
        size_t take = 64 - s->n; if (take > n) take = n;
        memcpy(s->buf + s->n, p, take); s->n += take; p += take; n -= take;
        if (s->n == 64) { sha_block(s, s->buf); s->n = 0; }
    }
}
static void sha_final(Sha256 *s, char out[65]) {
    uint64_t bits = s->len * 8;
    uint8_t pad = 0x80; sha_update(s, &pad, 1);
    uint8_t zero = 0; while (s->n != 56) sha_update(s, &zero, 1);
    uint8_t lb[8]; for (int i = 0; i < 8; i++) lb[i] = (uint8_t)(bits >> (56 - 8*i));
    /* feed length without counting it: */
    s->len -= 8; /* not used further */
    memcpy(s->buf + s->n, lb, 8); s->n += 8; sha_block(s, s->buf);
    for (int i = 0; i < 8; i++) sprintf(out + i*8, "%08x", s->h[i]);
    out[64] = 0;
}

int main(int argc, char **argv) {
    if (argc < 4 || argc > 8) { fprintf(stderr, "usage: %s <rom.gb> <frames> <out.ppm> [press_spec] [trace_file] [save_in.sav] [save_out.sav]\n", argv[0]); return 2; }
    const char *rom_path = argv[1];
    int frames = atoi(argv[2]);
    const char *ppm_path = argv[3];
    const char *trace_path = NULL;
    /* press windows: up to 512 (button, start, end) triples.
     * Slice 29: raised from 16 -- gb_play schedules run to ~250
     * merged windows, and the old cap silently dropped the rest,
     * which is the likely source of the slice-8 schedule-replay
     * divergence (the replayed Mario was not the autopilot's Mario).
     * Short specs are unaffected: windows are still OR'd per frame. */
    typedef struct { GbButton btn; int start, end; } Press;
    Press presses[512]; int npress = 0;
    if (argc >= 5) {
        if (strchr(argv[4], ':')) {
            /* press spec "btn:start:end,..." */
            char spec[8192];
            snprintf(spec, sizeof spec, "%s", argv[4]);
            for (char *tok = strtok(spec, ","); tok && npress < 512; tok = strtok(NULL, ",")) {
                char name[16]; int s, e;
                if (sscanf(tok, "%15[^:]:%d:%d", name, &s, &e) != 3) continue;
                static const char *names[GB_BUTTON_COUNT] = {
                    "right", "left", "up", "down", "a", "b", "select", "start" };
                for (int b = 0; b < GB_BUTTON_COUNT; b++)
                    if (!strcmp(name, names[b])) { presses[npress].btn = (GbButton)b; presses[npress].start = s; presses[npress].end = e; npress++; }
            }
        } else trace_path = argv[4];
        if (argc >= 6) trace_path = argv[5];
    }
    FILE *trace = NULL;
    /* Slice 5: optional WRAM watch. GB_WATCH="c858,c860,da4b,c711,c712"
     * (hex addresses in $c000-$dfff, comma-separated, up to 8) appends
     * those bytes to every trace line, so a state transition can be
     * read against the flags that caused it (e.g. the $09f0
     * [$c858]/[$c860] check, the $0868 [$da4b]/[$c711]/[$c712]
     * guards). Unset = trace format unchanged. */
    int watch[8], nwatch = 0;
    const char *wenv = getenv("GB_WATCH");
    if (wenv && wenv[0]) {
        char wbuf[256];
        snprintf(wbuf, sizeof wbuf, "%s", wenv);
        for (char *tok = strtok(wbuf, ","); tok && nwatch < 8;
             tok = strtok(NULL, ",")) {
            unsigned a = 0;
            if (sscanf(tok, "%x", &a) == 1 && a >= 0xc000 && a <= 0xdfff)
                watch[nwatch++] = (int)a;
        }
    }
    if (trace_path && trace_path[0]) {
        trace = fopen(trace_path, "w");
        if (!trace) { perror("open trace"); return 1; }
        fprintf(trace, "# frame pc state timer bank statstate");
        for (int w = 0; w < nwatch; w++) fprintf(trace, " w%04x", watch[w]);
        fprintf(trace, "\n");
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
    printf("title: %s\n", gb_title(gb));
    /* Optional battery-SRAM load (argv[6]): a previous run's save. */
    if (argc >= 7 && argv[6][0]) {
        FILE *sf = fopen(argv[6], "rb");
        if (sf) {
            fseek(sf, 0, SEEK_END); long slen = ftell(sf); fseek(sf, 0, SEEK_SET);
            uint8_t *sdata = malloc(slen);
            if (fread(sdata, 1, slen, sf) == (size_t)slen && gb_save_load(gb, sdata, (size_t)slen))
                printf("save-in: %s (%ld bytes)\n", argv[6], slen);
            else
                printf("save-in: %s FAILED (size %ld, save size %zu)\n", argv[6], slen, gb_save_size(gb));
            free(sdata); fclose(sf);
        } else printf("save-in: %s not found, fresh SRAM\n", argv[6]);
    }
    int prev_state = -1, prev_timer = -1, prev_bank = -1, prev_stat = -1;
    for (int i = 0; i < frames; i++) {
        /* NOTE (slice 3): two windows for the same button used to clobber
         * each other -- the later entry overwrote the earlier one each
         * frame, so "start:620:632,...,start:2500:2512" silently dropped
         * the first press (the game idled instead). Windows now OR: all
         * buttons are cleared, then every active window sets its button.
         * Single-window specs are unaffected (verified: slice-2 hashes
         * unchanged after this fix). */
        for (int b = 0; b < GB_BUTTON_COUNT; b++) gb_set_button(gb, (GbButton)b, 0);
        for (int p = 0; p < npress; p++)
            if (i >= presses[p].start && i < presses[p].end)
                gb_set_button(gb, presses[p].btn, 1);
        if (!gb_run_cycles(gb, GB_CYCLES_PER_FRAME, err, sizeof err)) {
            fprintf(stderr, "cpu lockup at frame %d: %s\n", i, err); return 1;
        }
        if (trace) {
            /* HRAM $ff80..: hCurrentBank=$ff8c, hGameState=$ff8e,
             * hSTATState=$ff8f, hStateTimer=$ff90. */
            int state = gb->hram[0x0e], timer = gb->hram[0x10];
            int bank = gb->hram[0x0c], stat = gb->hram[0x0f];
            if (state != prev_state || timer != prev_timer || bank != prev_bank ||
                stat != prev_stat || i % 60 == 0) {
                fprintf(trace, "%d %04x %d %d %d %d", i, gb->pc, state, timer, bank, stat);
                for (int w = 0; w < nwatch; w++)
                    fprintf(trace, " %02x", gb->wram[watch[w] - 0xc000]);
                fprintf(trace, "\n");
                prev_state = state; prev_timer = timer; prev_bank = bank; prev_stat = stat;
            }
        }
    }
    if (trace) fclose(trace);
    const uint8_t *fb = gb_framebuffer(gb);
    size_t pixels = (size_t)GB_SCREEN_WIDTH * GB_SCREEN_HEIGHT;
    int nonzero = 0; for (size_t i = 0; i < pixels; i++) if (fb[i]) nonzero++;
    Sha256 s; sha_init(&s); sha_update(&s, fb, pixels);
    char hex[65]; sha_final(&s, hex);
    printf("frames_run: %d  gb_frames: %u  nonzero_pixels: %d/%zu  fb_sha256: %s\n",
           frames, gb_frame_count(gb), nonzero, pixels, hex);
    /* Optional battery-SRAM dump (argv[7]) + dirty report. */
    printf("save_dirty: %d  save_size: %zu\n", gb_save_dirty(gb), gb_save_size(gb));
    if (argc >= 8 && argv[7][0]) {
        size_t ssize = gb_save_size(gb);
        uint8_t *sdata = malloc(ssize ? ssize : 1);
        size_t written = gb_save_write(gb, sdata, ssize);
        FILE *sf = fopen(argv[7], "wb");
        if (sf && written) { fwrite(sdata, 1, written, sf); fclose(sf); }
        else if (sf) fclose(sf);
        printf("save-out: %s (%zu bytes)\n", argv[7], written);
        free(sdata);
    }
    FILE *o = fopen(ppm_path, "wb");
    if (!o) { perror("open ppm"); return 1; }
    static const uint8_t grey[4] = { 235, 175, 110, 40 };
    fprintf(o, "P6\n%d %d\n255\n", GB_SCREEN_WIDTH, GB_SCREEN_HEIGHT);
    for (size_t i = 0; i < pixels; i++) {
        uint8_t g = grey[fb[i] & 3];
        fputc(g, o); fputc(g, o); fputc(g, o);
    }
    fclose(o);
    gb_destroy(gb);
    free(rom);
    return 0;
}
