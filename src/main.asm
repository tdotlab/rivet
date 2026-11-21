; Donkey Kong '94 (Game Boy) -- fresh disassembly, slice 1.
; Target ROM: Donkey Kong (World) (Rev 1) (SGB Enhanced).gb
;   SHA-1 397ad2ff25627b83e02c71b54c72bb4deb39e0c0, 512 KiB, MBC1+RAM+BATTERY.
; Built with RGBDS 1.0.4. See README.md / PROGRESS.md for scope and method.
; Curated code is hand-labelled and hand-checked against the ROM bytes.
; Everything not yet curated is pulled in as INCBIN (see src/banks.asm and
; the "Raw" sections below), so the build is byte-identical from day one
; and curated regions shrink the raw regions slice by slice.

INCLUDE "hardware.inc"
INCLUDE "constants.asm"

; =====================================================================
; $0000-$003f -- RST vectors and interrupt vectors.
; RST $00/$18/$20/$28/$30/$38 are just `ret` (unused); RST $08 is the
; jump-table dispatch (see DispatchViaRST8) and RST $10 is the bank
; switch (see SwitchBank). The three real interrupt vectors jump to the
; handlers in interrupts.asm; Serial and Joypad just `reti`.
; =====================================================================
SECTION "RST and vectors", ROM0[$0000]

RST00::
    ret                     ; $0000
    ds 7, $ff               ; $0001-$0007: unused, $ff-filled

RST08::
    jp DispatchViaRST8      ; $0008
    ds 5, $ff               ; $000b-$000f: unused, $ff-filled

RST10::
    ldh [hCurrentBank], a   ; $0010: remember the bank we are switching to
    ld [$2000], a           ; $0012: MBC1 ROM bank register ($4000-$7fff window)
    ret                     ; $0015
    ds 2, $ff               ; $0016-$0017: unused, $ff-filled

RST18::
    ret                     ; $0018
    ds 7, $ff
RST20::
    ret                     ; $0020
    ds 7, $ff
RST28::
    ret                     ; $0028
    ds 7, $ff
RST30::
    ret                     ; $0030
    ds 7, $ff
RST38::
    ret                     ; $0038
    ds 7, $ff

SECTION "Interrupt vectors", ROM0[$0040]
    jp VBlankHandler        ; $0040 VBlank
    ds 5, $ff
    jp STATHandler          ; $0048 STAT (LYC)
    ds 5, $ff
    jp TimerHandler         ; $0050 Timer
    ds 5, $ff
    reti                    ; $0058 Serial: no handler, return immediately
    ds 7, $ff
    reti                    ; $0060 Joypad: no handler, return immediately
    ds 7, $ff

    ds $98, $ff             ; $0068-$00ff: $ff padding (verified all $ff)

; =====================================================================
; $0100-$014f -- cartridge header. Bytes are literal, copied from the ROM;
; rgbfix -v in the Makefile re-validates logo and both checksums.
; Entry is nop + jp EntryPoint, as in every Game Boy ROM.
; =====================================================================
SECTION "Header", ROM0[$0100]
    nop                     ; $0100
    jp EntryPoint           ; $0101

HeaderLogo::
    db $ce, $ed, $66, $66, $cc, $0d, $00, $0b, $03, $73, $00, $83, $00, $0c, $00, $0d
    db $00, $08, $11, $1f, $88, $89, $00, $0e, $dc, $cc, $6e, $e6, $dd, $dd, $d9, $99
    db $bb, $bb, $67, $63, $6e, $0e, $ec, $cc, $dd, $dc, $99, $9f, $bb, $b9, $33, $3e

HeaderTitle::
    db "DONKEY KONG", $00, $00, $00, $00, $00  ; $0134, "DONKEY KONG"
    db $30, $31             ; $0144: new licensee code "01" (Nintendo)
    db $03                  ; $0146: SGB flag (03 = SGB enhanced)
    db $03                  ; $0147: cart type 03 = MBC1+RAM+BATTERY
    db $04                  ; $0148: ROM size 04 = 512 KiB, 32 banks
    db $02                  ; $0149: RAM size 02 = 8 KiB
    db $00                  ; $014a: destination 00 = Japan
    db $33                  ; $014b: old licensee $33 = new code in use
    db $01                  ; $014c: mask ROM version 01 = Rev 1
    db $2d                  ; $014d: header checksum (verified)
    db $4f, $8c             ; $014e: global checksum (verified)

; =====================================================================
; $0150-$0192 -- EntryPoint.
; Flow: interrupts off, stack at $fffe, bank 1, send SGB packet $5d
; (a no-op on non-SGB: SendSGBPacket returns early when the SGB flag
; in wSGBFlag is clear -- at this point it is, RAM was just powered on,
; so this first send does nothing; it is kept because the code says so),
; clear RAM, copy the OAM DMA routine to HRAM, load palette 3,
; detect the Super Game Boy, set up timer/STAT, enable VBlank
; interrupts only, then fall into the main loop.
; =====================================================================
SECTION "Entry", ROM0[$0150]
EntryPoint::
    di                      ; $0150: no interrupts until setup is done
    ld sp, $fffe            ; $0151: stack at top of HRAM
    ld a, $01
    rst $10                 ; $0154-$0156: switch to ROM bank 1
    ld a, $5d
    call SendSGBPacket      ; $0157-$0159: SGB packet $5d (see sgb.asm)
    call ClearRAMAndInit    ; $015c: clear WRAM/HRAM, set up pointers
    call CopyDMARoutine     ; $015f: copy OAM DMA routine to HRAM $ff80
    ld a, $03
    call LoadPalette        ; $0162-$0164: palette set 3 (BGP/OBP0/OBP1)
    call DetectSGB          ; $0167: probe for Super Game Boy, load border if present
    call SetupTimerAndSTAT  ; $016a
    ld a, $07
    ld [wIEShadow], a       ; $016d-$016f: remember IE = VBlank+STAT+Timer
    ldh [rIE], a            ; $0172: enable those three interrupts
    ei                      ; $0174

; --- Main loop -------------------------------------------------------
; Each pass: read the joypad, check the soft-reset combo, run one step
; of the current game state, then wait for the next VBlank. The halt
; waits for VBlankHandler to set bit 0 of wVBlankFlag; hFrameCount
; ticks once per loop.
MainLoop::
    call ReadJoypad         ; $0175
    call CheckSoftReset     ; $0178
    call DispatchState      ; $017b: rst $08 jump table on hGameState
MainLoop_WaitVBlank:
    ld hl, wUnknownC72F     ; $017e
    res 0, [hl]             ; $0181: clear flag bit 0 (role TODO)
    ld hl, wVBlankFlag      ; $0183
    halt                    ; $0186: sleep until an interrupt fires
MainLoop_WaitFlag:
    bit 0, [hl]             ; $0187: VBlank happened yet?
    jr z, MainLoop_WaitFlag ; $0189: no -- keep waiting
    res 0, [hl]             ; $018b: clear the flag for next frame
    ld hl, hFrameCount      ; $018d
    inc [hl]                ; $0190
    jr MainLoop             ; $0191

; =====================================================================
; $0193-$01a8 -- SetupTimerAndSTAT.
; STAT interrupt on LY compare ($40 = LYC=LY), timer off, TMA=$ba,
; then timer on at 4096 Hz ($04 = 4096 Hz clock, timer enabled).
; =====================================================================
SECTION "SetupTimerAndSTAT", ROM0[$0193]
SetupTimerAndSTAT::
    ld a, $40
    ldh [rSTAT], a          ; $0193-$0195: STAT interrupt when LY == LYC
    xor a
    ld [$defb], a           ; $0197-$0198: clear WRAM byte $defb (purpose TODO)
    ldh [rTIMA], a          ; $019b: timer counter 0
    ld a, $ba
    ldh [rTMA], a           ; $019d-$019f: timer reload $ba
    xor a
    ldh [rTAC], a           ; $01a1-$01a2: timer stopped
    ld a, $04
    ldh [rTAC], a           ; $01a4-$01a6: timer on, 4096 Hz
    ret                     ; $01a8

; =====================================================================
; $01a9-$01eb -- DispatchState.
; Loads hGameState into A and uses RST $08, which jumps through the
; table below (table entry = 16-bit address, index = A * 2). Most
; states just call AdvanceState ($1d22): increment hGameState and
; clear hStateTimer. States with real work have their own handlers
; elsewhere in bank 0; those are NOT curated yet (see PROGRESS.md).
; Two entries are flagged, not named:
;   entry 12 -> $c1fe (WRAM -- no code is ever copied there that we
;     have found; state 12 is never written in bank 0, so this entry
;     may be dead; DO NOT assume it is a real handler)
;   entry 24 -> $4000 (start of the banked window; the handler lives
;     in whatever bank is mapped at dispatch time)
; =====================================================================
SECTION "DispatchState", ROM0[$01a9]
DispatchState::
    ldh a, [hGameState]     ; $01a9
    rst $08                 ; $01ab: jump through StateJumpTable[hGameState]
StateJumpTable::
    dw AdvanceState         ; $01ac:  0
    dw AdvanceState         ; $01ae:  1
    dw $340e                ; $01b0:  2 (TODO: name)
    dw $359a                ; $01b2:  3 (TODO: name)
    dw $28a8                ; $01b4:  4 (TODO: name)
    dw AdvanceState         ; $01b6:  5
    dw AdvanceState         ; $01b8:  6
    dw AdvanceState         ; $01ba:  7
    dw $3657                ; $01bc:  8 (TODO: name)
    dw AdvanceState         ; $01be:  9
    dw AdvanceState         ; $01c0: 10
    dw AdvanceState         ; $01c2: 11
    dw $c1fe                ; $01c4: 12 -- UNVERIFIED, see note above
    dw AdvanceState         ; $01c6: 13
    dw AdvanceState         ; $01c8: 14
    dw AdvanceState         ; $01ca: 15
    dw $06bd                ; $01cc: 16 (TODO: name)
    dw $34df                ; $01ce: 17 (TODO: name)
    dw $0692                ; $01d0: 18 (TODO: name)
    dw AdvanceState         ; $01d2: 19
    dw $266c                ; $01d4: 20 (TODO: name)
    dw $3582                ; $01d6: 21 (TODO: name)
    dw $3663                ; $01d8: 22 (TODO: name)
    dw AdvanceState         ; $01da: 23
    dw $4000                ; $01dc: 24 -- banked entry, see note above
    dw AdvanceState         ; $01de: 25
    dw $3679                ; $01e0: 26 (TODO: name)
    dw AdvanceState         ; $01e2: 27
    dw $3471                ; $01e4: 28 (TODO: name)
    dw AdvanceState         ; $01e6: 29
    dw $290a                ; $01e8: 30 (TODO: name)
    dw AdvanceState         ; $01ea: 31

; =====================================================================
; $01ec-$0225 -- CheckSoftReset.
; If A+B+Select+Start are all held at once (hJoypad low nibble == $0f),
; and the game is past state 2, and the state is not $1a (26), reset:
; send SGB packet $5f, turn the LCD off safely, reload palette 3,
; clear the tilemaps, re-enable interrupts, clear RAM, set state 2,
; and restore interrupts/LCDC. The $1a exception and the state>=3
; guard are in the code; why state $1a is exempt is not yet known.
; =====================================================================
SECTION "CheckSoftReset", ROM0[$01ec]
CheckSoftReset::
    ldh a, [hJoypad]        ; $01ec
    and $0f                 ; $01ee: buttons nibble only
    cp $0f                  ; $01f0: all four buttons pressed?
    ret nz                  ; $01f2: no -- nothing to do
    ldh a, [hGameState]     ; $01f3
    cp $03                  ; $01f5: state < 3?
    ret c                   ; $01f7: too early, ignore
    cp $1a                  ; $01f8: state == $1a?
    ret z                   ; $01fa: exempt, ignore
    ld a, $5f
    call SendSGBPacketIfSGB ; $01fb-$01fd: SGB packet $5f (gated: only on SGB)
    call DisableVBlankAndLCDOff ; $0200
    ld a, $03
    call LoadPalette        ; $0203-$0205: palette set 3
    call ClearTilemaps      ; $0208
    ldh a, [rIE]
    and $fa                 ; $020b-$020d: clear IE bits 0 (VBlank) and 2 (Timer)
    ldh [rIE], a            ; $020f
    ei                      ; $0211
    call ClearRAMAndInit    ; $0212
    ld a, $07
    ld [wIEShadow], a       ; $0215-$0217
    ldh [rIE], a            ; $021a
    xor a
    ldh [hStateTimer], a    ; $021c-$021d: reset per-state counter
    ld a, $02
    ldh [hGameState], a     ; $021f-$0221: back to state 2
    jp RestoreInterruptsAndLCDC ; $0223

; =====================================================================
; $0226-$0274 -- ClearRAMAndInit.
; Saves [$c82b] and [$da40], clears WRAM $c000-$def6 (BC=$1ef7) and
; $df00-$dfff (BC=$0100) to zero, clears HRAM $ff8a-$ffa9 (C=$20) to
; zero, restores the two saved bytes, masks [$c82b] with $cd, switches
; to bank 3 and calls $4000 (bank 3's entry point), calls
; InitStatePtrs, then sets wLCDCShadow=$e7, wUnknownC851=1,
; wUnknownDA43=4, and writes two bytes at wUnknownC859.
; =====================================================================
SECTION "ClearRAMAndInit", ROM0[$0226]
ClearRAMAndInit::
    ld a, [wSGBFlag]        ; $0226: save flags
    push af                 ; $0229
    ld a, [$da40]           ; $022a: save SGB mode byte
    push af                 ; $022d
    ld hl, wClearTarget     ; $022e: $c000
    ld bc, $1ef7            ; $0231: $c000-$def6
    xor a
    call MemsetBC           ; $0235: fill with 0
    ld hl, wClearTarget2    ; $0238: $df00
    ld bc, $0100            ; $023b
    xor a
    call MemsetBC           ; $023f: fill with 0
    ld hl, hJoypad          ; $0242: $ff8a
    ld c, $20               ; $0245: $ff8a-$ffa9
    xor a
    call MemsetC            ; $0248: fill with 0
    pop af                  ; $024b: restore SGB mode byte
    ld [$da40], a           ; $024c
    pop af                  ; $024f: restore flags
    and $cd                 ; $0250: keep bits 0,2,3,6,7
    ld [wSGBFlag], a        ; $0252
    ld a, $03
    rst $10                 ; $0255-$0257: switch to bank 3
    call $4000              ; $0258: bank 3 entry point (TODO: name)
    call InitStatePtrs      ; $025b
    ld a, $e7
    ld [wLCDCShadow], a     ; $025e-$0260: LCDC shadow = $e7 (LCD on, BG+OBJ on)
    ld a, $01
    ld [wUnknownC851], a    ; $0263-$0265
    ld a, $04
    ld [wUnknownDA43], a    ; $0268-$026a
    ld hl, wUnknownC859     ; $026d
    xor a                   ; $0270
    ld [hl-], a             ; $0271: [$c859] = 0
    dec a                   ; $0272: A = $ff
    ld [hl], a              ; $0273: [$c858] = $ff
    ret                     ; $0274

; =====================================================================
; $0275-$02af -- VBlankHandler.
; Masks the timer interrupt while running, calls the per-frame update
; at $16f9 (not curated yet), runs the HRAM OAM DMA routine if
; wOAMDMATrigger is non-zero, restores the current ROM bank, and --
; unless the LCD is in mode 2 -- copies the SCY/SCX shadow pair.
; Ends by restoring IE and setting bit 0 of wVBlankFlag, which is what
; MainLoop's halt is waiting on.
; =====================================================================
SECTION "VBlankHandler", ROM0[$0275]
VBlankHandler::
    push af                 ; $0275
    push bc                 ; $0276
    push de                 ; $0277
    push hl                 ; $0278
    ldh a, [rIE]            ; $0279
    and $fb                 ; $027b: mask out Timer (bit 2)
    ldh [rIE], a            ; $027d
    ei                      ; $027f
    call $16f9              ; $0280: per-frame update (TODO: name)
    ld a, [wOAMDMATrigger]  ; $0283
    or a                    ; $0286
    call z, hDMARoutine     ; $0287: copy OAM to VRAM if triggered
    ldh a, [hCurrentBank]   ; $028a
    ld [$2000], a           ; $028c: restore ROM bank (DMA may have changed it)
    ldh a, [rSTAT]          ; $028f
    and $02                 ; $0291: LCD mode bit 0
    jr nz, VBlankHandler_Done ; $0293: in mode 2, skip scroll update
    call $1663              ; $0295: (TODO: name)
    ld hl, wScrollShadow    ; $0298
    ld a, [hl+]             ; $029b
    ldh [rSCY], a           ; $029c
    ld a, [hl]              ; $029e
    ldh [rSCX], a           ; $029f
VBlankHandler_Done:
    ld a, [wIEShadow]       ; $02a1
    ldh [rIE], a            ; $02a4
    ld hl, wVBlankFlag      ; $02a6
    set 0, [hl]             ; $02a9: tell MainLoop a frame is done
    pop hl                  ; $02ab
    pop de                  ; $02ac
    pop bc                  ; $02ad
    pop af                  ; $02ae
    reti                    ; $02af

; =====================================================================
; $02b0-$02c6 -- STATHandler. Masks VBlank+Timer, calls the STAT
; dispatch at $02ec, restores IE, returns.
; $02c7-$02eb -- TimerHandler. Masks Timer, switches to bank 2 and
; calls $4003, then bank 3 and calls $4003 (banked timer callbacks),
; restores the bank, restores IE, returns.
; =====================================================================
SECTION "STATHandler", ROM0[$02b0]
STATHandler::
    push af                 ; $02b0
    push bc                 ; $02b1
    push de                 ; $02b2
    push hl                 ; $02b3
    ldh a, [rIE]            ; $02b4
    push af                 ; $02b6
    and $f9                 ; $02b7: mask out VBlank (bit 0) and Timer (bit 2)
    ldh [rIE], a            ; $02b9
    ei                      ; $02bb
    call STATDispatch       ; $02bc
    pop af                  ; $02bf
    ldh [rIE], a            ; $02c0
    pop hl                  ; $02c2
    pop de                  ; $02c3
    pop bc                  ; $02c4
    pop af                  ; $02c5
    reti                    ; $02c6

SECTION "TimerHandler", ROM0[$02c7]
TimerHandler::
    push af                 ; $02c7
    push bc                 ; $02c8
    push de                 ; $02c9
    push hl                 ; $02ca
    ldh a, [rIE]            ; $02cb
    push af                 ; $02cd
    and $fb                 ; $02ce: mask out Timer (bit 2)
    ldh [rIE], a            ; $02d0
    ei                      ; $02d2
    ldh a, [hCurrentBank]   ; $02d3: save current bank
    push af                 ; $02d5
    ld a, $02
    rst $10                 ; $02d6-$02d8: switch to bank 2
    call $4003              ; $02d9: bank 2 timer callback (TODO: name)
    ld a, $03
    rst $10                 ; $02dc-$02de: switch to bank 3
    call $4003              ; $02df: bank 3 timer callback (TODO: name)
    pop af                  ; $02e2: restore bank
    rst $10                 ; $02e3
    pop af                  ; $02e4
    ldh [rIE], a            ; $02e5
    pop hl                  ; $02e7
    pop de                  ; $02e8
    pop bc                  ; $02e9
    pop af                  ; $02ea
    reti                    ; $02eb

; =====================================================================
; $02ec-$030e -- STATDispatch.
; Same RST $08 jump-table trick as DispatchState, indexed by
; hSTATState. All 16 entries point into bank 0 code ($0367-$0447);
; the targets are NOT curated yet, so they are listed as raw
; addresses here, not named labels. Do not invent names for them.
; =====================================================================
SECTION "STATDispatch", ROM0[$02ec]
STATDispatch::
    ldh a, [hSTATState]     ; $02ec
    rst $08                 ; $02ee
STATJumpTable::
    dw $037d                ; $02ef:  0
    dw $0367                ; $02f1:  1
    dw $037e                ; $02f3:  2
    dw $0367                ; $02f5:  3
    dw $03b9                ; $02f7:  4
    dw $03cb                ; $02f9:  5
    dw $03db                ; $02fb:  6
    dw $042f                ; $02fd:  7
    dw $0435                ; $02ff:  8
    dw $0440                ; $0301:  9
    dw $0447                ; $0303: 10
    dw $03ec                ; $0305: 11
    dw $040e                ; $0307: 12
    dw $0440                ; $0309: 13
    dw $0423                ; $030b: 14
    dw $03ec                ; $030d: 15

; Raw (not yet curated) bank 0, $030f-$0fc0.
SECTION "Raw bank 0 A", ROM0[$030f]
    INCBIN "roms/Donkey_Kong_World_Rev1_SGB.gb", $030f, $cb2

; =====================================================================
; $0fc1-$0fce -- CopyDMARoutine. Copies the 10-byte OAM DMA routine
; at $0fcf into HRAM at $ff80, where VBlankHandler can call it
; (code cannot run from ROM during OAM DMA).
; $0fcf-$0fd8 -- DMARoutine itself: start DMA from $c000 (OAM copy
; source in WRAM), then burn $28 iterations as a delay.
; =====================================================================
SECTION "CopyDMARoutine", ROM0[$0fc1]
CopyDMARoutine::
    ld c, $80               ; $0fc1: HRAM $ff80
    ld b, $0a               ; $0fc3: 10 bytes
    ld hl, DMARoutine       ; $0fc5
CopyDMARoutine_Loop:
    ld a, [hl+]             ; $0fc8
    ldh [c], a              ; $0fc9
    inc c                   ; $0fca
    dec b                   ; $0fcb
    jr nz, CopyDMARoutine_Loop ; $0fcc
    ret                     ; $0fce

DMARoutine::
    ld a, $c0               ; $0fcf: DMA source $c000
    ldh [rDMA], a           ; $0fd1: start OAM DMA
    ld a, $28               ; $0fd3: delay counter
DMARoutine_Delay:
    dec a                   ; $0fd5
    jr nz, DMARoutine_Delay ; $0fd6
    ret                     ; $0fd8

; =====================================================================
; $0fd9-$0fe4 -- DispatchViaRST8 (RST $08 handler).
; The byte after the `rst $08` is NOT code: it is a table of 16-bit
; addresses. HL is popped from the stack (the return address, i.e.
; the table start), A is the index, HL += A*2, and the code jumps to
; the address stored there. This is how DispatchState and
; STATDispatch work, and why the bytes after an `rst $08` must never
; be disassembled as code -- mgbdis gets this wrong, see PROGRESS.md.
; $0fe5-$0fea -- a second copy of the bank-switch sequence
; (ldh [hCurrentBank],a; ld [$2000],a; ret). No caller has been
; found in bank 0 yet; it may be called from banked code. Kept
; literal; do not merge it with RST10.
; =====================================================================
SECTION "RST8 dispatch", ROM0[$0fd9]
DispatchViaRST8::
    pop hl                  ; $0fd9: HL = address just after `rst $08`
    push de                 ; $0fda
    ld e, a                 ; $0fdb: index
    ld d, $00               ; $0fdc
    add hl, de              ; $0fde: HL += index
    add hl, de              ; $0fdf: HL += index (x2: 16-bit entries)
    pop de                  ; $0fe0
    ld a, [hl+]             ; $0fe1: low byte of target
    ld h, [hl]              ; $0fe2: high byte
    ld l, a                 ; $0fe3
    jp hl                   ; $0fe4: jump to the table entry

; $0fe5-$0fea: bank-switch tail (entry is RST10 at $0010; this copy
; is reached by the code at $0010 falling through? No -- $0010's
; handler is complete in itself. This address is a second copy of
; the same two instructions, used as a subroutine tail by other
; code paths. Kept literal; do not merge with RST10.)
SwitchBankTail::
    ldh [hCurrentBank], a   ; $0fe5
    ld [$2000], a           ; $0fe7
    ret                     ; $0fea

; =====================================================================
; $0feb-$1021 -- LCD-off helpers and restore.
; $0feb sends SGB packet 7 (gated: no-op when not SGB), $0ff0 turns
; the LCD off safely (disable VBlank interrupt, wait for LY=$91,
; clear LCDC bit 7), $0ffd restores IE and LCDC from the shadows,
; $1008 restores then sends SGB packet $0b, $1010 waits for VBlank
; and turns the LCD off.
; =====================================================================
SECTION "LCD helpers", ROM0[$0feb]
SendSGBPacket7AndLCDOff::
    ld a, $07               ; $0feb
    call SendSGBPacketIfSGB ; $0fed: SGB packet 7, gated on SGB
DisableVBlankAndLCDOff::
    di                      ; $0ff0
    ldh a, [rIE]            ; $0ff1
    ld [wIEShadow], a       ; $0ff3: save IE
    and $fe                 ; $0ff6: clear VBlank bit
    ldh [rIE], a            ; $0ff8
    ei                      ; $0ffa
    jr WaitForVBlankAndLCDOff ; $0ffb
RestoreInterruptsAndLCDC::
    ld a, [wIEShadow]       ; $0ffd
    ldh [rIE], a            ; $1000
    ld a, [wLCDCShadow]     ; $1002
    ldh [rLCDC], a          ; $1005
    ret                     ; $1007
RestoreAndSendSGBPacket0B::
    call RestoreInterruptsAndLCDC ; $1008
    ld a, $0b               ; $100b
    jp SendSGBPacketIfSGB   ; $100d: tail call, gated on SGB
WaitForVBlankAndLCDOff::
    ldh a, [rLY]            ; $1010
    cp $91                  ; $1012: wait for VBlank (LY 144)
    jr c, WaitForVBlankAndLCDOff ; $1014
    ldh a, [rLCDC]          ; $1016
    and $7f                 ; $1018: clear LCD-on bit
    ldh [rLCDC], a          ; $101a
    ld a, [wIEShadow]       ; $101c
    ldh [rIE], a            ; $101f
    ret                     ; $1021 (verified: byte at $1021 is $c9)

; =====================================================================
; $1022-$1056 -- ReadJoypad.
; Selects the d-pad ($20), reads it twice, complements and keeps the
; low nibble, swaps it into the high nibble; then selects the buttons
; ($10), reads six times, complements, keeps the low nibble, and ORs
; the two nibbles into C. hJoypadNew = (old ^ new) & new (buttons
; pressed this frame only); hJoypad = new. Ends by deselecting ($30).
; =====================================================================
SECTION "ReadJoypad", ROM0[$1022]
ReadJoypad::
    ld a, $20               ; $1022: select d-pad
    ldh [rP1], a            ; $1024
    ldh a, [rP1]            ; $1026
    ldh a, [rP1]            ; $1028: read twice (hardware settle)
    cpl                     ; $102a: pressed bits become 1
    and $0f                 ; $102b
    swap a                  ; $102d: d-pad into high nibble
    ld b, a                 ; $102f
    ld a, $30               ; $1030: deselect
    ldh [rP1], a            ; $1032
    ld a, $10               ; $1034: select buttons
    ldh [rP1], a            ; $1036
    ldh a, [rP1]            ; $1038
    ldh a, [rP1]            ; $103a
    ldh a, [rP1]            ; $103c
    ldh a, [rP1]            ; $103e
    ldh a, [rP1]            ; $1040
    ldh a, [rP1]            ; $1042: read six times
    cpl                     ; $1044
    and $0f                 ; $1045
    or b                    ; $1047: merge d-pad + buttons
    ld c, a                 ; $1048
    ldh a, [hJoypad]        ; $1049: previous state
    xor c                   ; $104b: changed bits
    and c                   ; $104c: newly pressed bits
    ldh [hJoypadNew], a     ; $104d
    ld a, c                 ; $104f
    ldh [hJoypad], a        ; $1050
    ld a, $30               ; $1052: deselect
    ldh [rP1], a            ; $1054
    ret                     ; $1056

; =====================================================================
; $1057-$1074 -- memory helpers.
; MemsetBC: fill [HL..HL+BC) with A. MemsetC: fill [HL..HL+C) with A.
; MemcpyBC: copy BC bytes HL -> DE. MemcpyC: copy C bytes HL -> DE.
; =====================================================================
SECTION "Memory helpers", ROM0[$1057]
MemsetBC::
    ld [hl+], a             ; $1057
    ld d, a                 ; $1058: save A (BC countdown clobbers it)
    dec bc                  ; $1059
    ld a, b                 ; $105a
    or c                    ; $105b
    ld a, d                 ; $105c: restore A
    jr nz, MemsetBC         ; $105d
    ret                     ; $105f
MemsetC::
    ld [hl+], a             ; $1060
    dec c                   ; $1061
    jr nz, MemsetC          ; $1062
    ret                     ; $1064
MemcpyBC::
    ld a, [hl+]             ; $1065
    ld [de], a              ; $1066
    inc de                  ; $1067
    dec bc                  ; $1068
    ld a, b                 ; $1069
    or c                    ; $106a
    jr nz, MemcpyBC         ; $106b
    ret                     ; $106d
MemcpyC::
    ld a, [hl+]             ; $106e
    ld [de], a              ; $106f
    inc de                  ; $1070
    dec c                   ; $1071
    jr nz, MemcpyC          ; $1072
    ret                     ; $1074

; Raw (not yet curated) bank 0, $1075-$10aa.
SECTION "Raw bank 0 B1", ROM0[$1075]
    INCBIN "roms/Donkey_Kong_World_Rev1_SGB.gb", $1075, $36

; =====================================================================
; $10ab-$10c1 -- ClearTilemaps.
; Three entry points, one body: fill a tilemap with zeros via
; MemsetBC. $10ab clears $9800 for $800 bytes (the whole BG map),
; $10b3 clears $9800 for $400, $10b8 clears $9c00 for $400.
; =====================================================================
SECTION "ClearTilemaps", ROM0[$10ab]
ClearTilemaps::
    ld hl, $9800            ; $10ab
    ld bc, $0800            ; $10ae
    jr ClearTilemaps_Fill   ; $10b1
ClearTilemap9800_400::
    ld hl, $9800            ; $10b3
    jr ClearTilemaps_Set400 ; $10b6
ClearTilemap9C00_400::
    ld hl, $9c00            ; $10b8
ClearTilemaps_Set400:
    ld bc, $0400            ; $10bb
ClearTilemaps_Fill:
    xor a                   ; $10be
    jp MemsetBC             ; $10bf: tail call

; Raw (not yet curated) bank 0, $10c2-$1d06.
SECTION "Raw bank 0 B", ROM0[$10c2]
    INCBIN "roms/Donkey_Kong_World_Rev1_SGB.gb", $10c2, $c45

; =====================================================================
; $1d07-$1d2e -- InitStatePtrs and the state helpers.
; InitStatePtrs sets wStatePtrLo = wStatePtr ($da61) and
; wStatePtr2 = wStatePtr (twice: $da71 and $da73 both = $da61).
; AdvanceState: hGameState++, hStateTimer = 0. IncStateTimer: hStateTimer++.
; =====================================================================
SECTION "State helpers", ROM0[$1d07]
InitStatePtrLo::
    ld hl, wStatePtrLo      ; $1d07: $da5f
    ld de, wStatePtr        ; $1d0a: $da61
    ld a, e                 ; $1d0d
    ld [hl+], a             ; $1d0e
    ld [hl], d              ; $1d0f
    ret                     ; $1d10
InitStatePtrs::
    call InitStatePtrLo     ; $1d11
    ld hl, wStatePtr2       ; $1d14: $da71
    ld de, wStatePtr        ; $1d17: $da61
    ld a, e                 ; $1d1a
    ld [hl+], a             ; $1d1b
    ld a, d                 ; $1d1c
    ld [hl+], a             ; $1d1d
    ld a, e                 ; $1d1e
    ld [hl+], a             ; $1d1f
    ld [hl], d              ; $1d20
    ret                     ; $1d21
AdvanceState::
    ld hl, hGameState       ; $1d22
    inc [hl]                ; $1d25: next state
    xor a                   ; $1d26
    ldh [hStateTimer], a    ; $1d27: reset per-state counter
    ret                     ; $1d29
IncStateTimer::
    ld hl, hStateTimer      ; $1d2a
    inc [hl]                ; $1d2d
    ret                     ; $1d2e

; Raw (not yet curated) bank 0, $1d2f-$1e4e.
SECTION "Raw bank 0 C", ROM0[$1d2f]
    INCBIN "roms/Donkey_Kong_World_Rev1_SGB.gb", $1d2f, $120

; =====================================================================
; $1e4f-$1e6a -- LoadPalette.
; A = palette index (0-?). HL = table at $1e86 + A*3; the three bytes
; are BGP, OBP0, OBP1, written to the hardware registers and to the
; shadow copy at wPaletteShadow ($da3d-$da3f). The table itself is
; in the raw region below, not curated yet.
; =====================================================================
SECTION "LoadPalette", ROM0[$1e4f]
LoadPalette::
    ld b, a                 ; $1e4f
    add a                   ; $1e50: A *= 2
    add b                   ; $1e51: A *= 3
    ld b, $00               ; $1e52
    ld c, a                 ; $1e54
    ld hl, $1e86            ; $1e55: palette table (raw data)
    add hl, bc              ; $1e58
    ld bc, wPaletteShadow   ; $1e59: $da3d
    ld a, [hl+]             ; $1e5c
    ldh [rBGP], a           ; $1e5d
    ld [bc], a              ; $1e5f
    inc bc                  ; $1e60
    ld a, [hl+]             ; $1e61
    ldh [rOBP0], a          ; $1e62
    ld [bc], a              ; $1e64
    inc bc                  ; $1e65
    ld a, [hl]              ; $1e66
    ldh [rOBP1], a          ; $1e67
    ld [bc], a              ; $1e69
    ret                     ; $1e6a

; Raw (not yet curated) bank 0, $1e6b-$3736 (includes the palette table at $1e86).
SECTION "Raw bank 0 D", ROM0[$1e6b]
    INCBIN "roms/Donkey_Kong_World_Rev1_SGB.gb", $1e6b, $18cc

INCLUDE "sgb.asm"
INCLUDE "banks.asm"
