; Donkey Kong '94 -- slice 2: main state handlers (DispatchState table $01ac).
; Every handler here is a `rst $08` sub-dispatch on hStateTimer, exactly like
; DispatchState itself: the bytes after the `rst $08` are a table of 16-bit
; addresses (bank 0 or banked $4000-$7fff), NOT code. Banked sub-step bodies
; (banks 1, 12, 23) are NOT curated yet -- they stay INCBIN in banks.asm.
; State flow, verified by Nacre trace (slice 2, tools/gb_headless trace):
;   boot 0 -> 2 TitleScreen -> (Start) 3 PostStart -> (A) 16 Transition
;     -> 4 IntroSequence -> 16 -> 20 Gameplay -> 16 -> 15 -> 16 -> 20 ...
;   idle on title: 2 -> 16 -> 30 AttractDemo (~4300 frames) -> 2 (loops).
; State 8's bank-1 sub-steps are NOT curated yet (only the table is); see
; the State 8 section below for what they do.
;   State 12 ($c1fe) was never visited in any trace; see PROGRESS.md.

; --- State 18: file-select input loop ($0692-$06bc). -------------------------
; $0692 reads hJoypad; if a button is held it jumps to $06a5 (joypad branch);
; otherwise it calls bank-12 $4d05, saves hJoypadNew/hJoypad, and loops on
; [$c711]. Timer cycles 3-10 in the trace: the per-frame file-select handler
; (role INFERRED -- never single-stepped, only traced).
SECTION "State 18 handler", ROM0[$0692]
FileSelectLoop::
    ldh a, [$ff8a]                                   ; $0692
    or a                                             ; $0694
    jr nz, FileSelectLoop_Joypad                     ; $0695
    ld a, $0c                                        ; $0697
    rst $10                                          ; $0699
    call $4d05                                       ; $069a
    ldh [$ff8b], a                                   ; $069d
    ldh [$ff8a], a                                   ; $069f
    cp $ff                                           ; $06a1
    jr nz, $06bd                                     ; $06a3
FileSelectLoop_Joypad::
    ld hl, $defb                                     ; $06a5
    inc [hl]                                         ; $06a8
    ld a, [hl]                                       ; $06a9
    cp $05                                           ; $06aa
    jr nz, L_06af                                    ; $06ac
    xor a                                            ; $06ae
L_06af::
    ld [hl-], a                                      ; $06af
    xor a                                            ; $06b0
    ld [hl-], a                                      ; $06b1
    ld [hl-], a                                      ; $06b2
    ld [hl-], a                                      ; $06b3
    ld [hl], a                                       ; $06b4
    ld hl, $c82b                                     ; $06b5
    res 5, [hl]                                      ; $06b8
    jp $01fb                                         ; $06ba

; --- State 16: transition / router ($06bd-$071b, timer-0 step $071c-$0736). --
; No bank switch in the prologue: it dispatches on hStateTimer directly.
; 46-entry table ($06c0-$071b). Timer 0 ($071c) calls $09f0 (which sets state
; 21/22 when a save exists: [$c858]==0 and [$c860]!=0), then $0cec, then
; InitStatePtrs, then IncStateTimer and a bank-7 call; it FALLS THROUGH into
; timer 1's code at $0737 (not curated yet).
SECTION "State 16 handler", ROM0[$06bd]
State16_Transition::
    ldh a, [hStateTimer]    ; $06bd
    rst $08                 ; $06bf: jump through State16Table[hStateTimer]
State16Table::
    dw $071c, $0737, $07e7, $083e, $0847, $083e, $0859, $083e
    dw $0847, $083e, $0853, $0996, $08f7, $0968, $0996, $0996
    dw $08cc, $08de, $08e5, $08e8, $0a0c, $0a49, $098c, $0997
    dw $09b9, $09c6, $09d5, $0a8a, $0a98, $0ab5, $0abc, $0a95
    dw $0ac4, $0ad7, $0ade, $0af0, $0afd, $0b02, $0b15, $0b1c
    dw $0b21, $0b28, $0b45, $0b6a, $0b95, $0bde

SECTION "State 16 step 0", ROM0[$071c]
TransitionStep0::
    call $09f0                                       ; $071c
    call $0cec                                       ; $071f
    call InitStatePtrs                               ; $0722
    ld hl, $c853                                     ; $0725
    xor a                                            ; $0728
    ld [hl+], a                                      ; $0729
    ld [hl], a                                       ; $072a
    call IncStateTimer                               ; $072b
    ld a, $07                                        ; $072e
    rst $10                                          ; $0730
    call $7168                                       ; $0731
    ld a, $01                                        ; $0734
    rst $10                                          ; $0736
; NOTE: TransitionStep0 falls through into $0737 (timer-1 code, raw for now).

; --- State 20: gameplay entry ($266c-$26b4). --------------------------------
; $266c: if wSGBFlag bit 5 is set and any joypad button is held, jump to
; $06a5 (FileSelectLoop_Joypad); otherwise bank 1, sub-dispatch on
; hStateTimer, 27-entry table (repeats: $26b5/$43f9/$4748/$4757/$476c/
; $47ad/$47d5/$4807/$483a recur -- per-stage setup steps, inferred).
SECTION "State 20 handler", ROM0[$266c]
State20_Gameplay::
    ld a, [wSGBFlag]        ; $266c
    bit 5, a                ; $266f
    jr z, State20_Dispatch  ; $2671
    ldh a, [hJoypad]        ; $2673
    or a                    ; $2675
    jp nz, FileSelectLoop_Joypad ; $2676
State20_Dispatch:
    ld a, $01               ; $2679
    rst $10                 ; $267b: bank 1
    ldh a, [hStateTimer]    ; $267c
    rst $08                 ; $267e: jump through State20Table[hStateTimer]
State20Table::
    dw $26b5, $43f9, $4586, $45bb, $4748, $4757, $476c, $47ad
    dw $47d5, $464c, $4673, $46a2, $26b5, $46f5, $470e, $4807
    dw $483a, $43f9, $448e, $4748, $4757, $476c, $47ad, $47d5
    dw $4807, $483a, $43f9

; --- State 4: intro sequence ($28a8-$2909). ---------------------------------
; 4-entry table; steps 1 and 2 both point at $2900. Trace: state 4 runs
; ~900 frames after PostStart, then -> 16 -> 20.
SECTION "State 4 handler", ROM0[$28a8]
State04_Intro::
    ld a, $01               ; $28a8
    rst $10                 ; $28aa: bank 1
    ldh a, [hStateTimer]    ; $28ab
    rst $08                 ; $28ad: jump through State04Table[hStateTimer]
State04Table::
    dw $28b6, $2900, $2900, $58e9

SECTION "State 4 steps", ROM0[$28b6]
State04Step0::
    call InitStatePtrs                               ; $28b6
    call SendSGBPacket7AndLCDOff                     ; $28b9
    call $1643                                       ; $28bc
    xor a                                            ; $28bf
    call LoadPalette                                 ; $28c0
    ld a, $03                                        ; $28c3
    call TransferTable1E                             ; $28c5
    ld hl, $9800                                     ; $28c8
    ld bc, $0800                                     ; $28cb
    ld a, $80                                        ; $28ce
    call MemsetBC                                    ; $28d0
    ld a, $0c                                        ; $28d3
    call TransferTable0F                             ; $28d5
    ld a, $13                                        ; $28d8
    ldh [$ff8f], a                                   ; $28da
    ld a, $08                                        ; $28dc
    call LoadSpriteTable                             ; $28de
    ld a, $10                                        ; $28e1
    rst $10                                          ; $28e3
    xor a                                            ; $28e4
    call $61b2                                       ; $28e5
    ld a, $01                                        ; $28e8
    rst $10                                          ; $28ea
    call $20c9                                       ; $28eb
    xor a                                            ; $28ee
    ld [$ce1c], a                                    ; $28ef
    call ResetWindowPos                              ; $28f2
    call IncStateTimer                               ; $28f5
    call RestoreInterruptsAndLCDC                    ; $28f8
    ld a, $2f                                        ; $28fb
    call SendSGBPacketIfSGB                          ; $28fd
State04Step1::
    ld a, $10                                        ; $2900
    rst $10                                          ; $2902
    xor a                                            ; $2903
    call $6b32                                       ; $2904
    jp $10d5                                         ; $2907

; --- State 30: attract demo ($290a-$291f). -----------------------------------
; Bank $17 (23). Trace: entered from Transition on title timeout, runs
; ~4300 frames of demo play, then back to TitleScreen.
SECTION "State 30 handler", ROM0[$290a]
State30_AttractDemo::
    ld a, $17               ; $290a
    rst $10                 ; $290c: bank 23
    ldh a, [hStateTimer]    ; $290d
    rst $08                 ; $290f: jump through State30Table[hStateTimer]
State30Table::
    dw $731f, $76b4, $06a5, $7563, $759c, $7650, $765f, $76a6

; --- State 2: title screen ($340e-$344a + helpers). --------------------------
; Trace: timer steps 0-7; step 0 ($342a) sets up, steps 1-6 (bank 1) run the
; logo/title animation (~11 s), step 7 waits for Start -> state 3.
; No Start within ~1000 frames -> Transition -> AttractDemo.
SECTION "State 2 handler", ROM0[$340e]
TitleScreen::
    ld a, $01               ; $340e
    rst $10                 ; $3410: bank 1
    ldh a, [hStateTimer]    ; $3411
    rst $08                 ; $3413: jump through TitleTable[hStateTimer]
TitleTable::
    dw $342a, $4998, $49bf, $49ef, $4a2e, $4a75, $4aa4, $4b14
    dw $4b21, $4a7f, $4b2a

SECTION "Title step 0", ROM0[$342a]
TitleStep0::
    call $0ff0                                       ; $342a
    call ResetWindowPos                              ; $342d
    call $344b                                       ; $3430
    call RestoreInterruptsAndLCDC                    ; $3433
    ld a, [$c82b]                                    ; $3436
    bit 7, a                                         ; $3439
    ret z                                            ; $343b
    ld a, $5c                                        ; $343c
    call SendSGBPacketIfSGB                          ; $343e
    ld a, $04                                        ; $3441
    call SendSGBPacketIfSGB                          ; $3443
    ld a, $21                                        ; $3446
    jp SendSGBPacketIfSGB                            ; $3448

SECTION "Title screen setup", ROM0[$344b]
TitleScreenSetup::
    call $1643                                       ; $344b
    ld a, $0b                                        ; $344e
    call TransferTable1E                             ; $3450
    ld a, $0d                                        ; $3453
    call LoadSpriteTable                             ; $3455
    ld a, $10                                        ; $3458
    call LoadPalette                                 ; $345a
    ld a, $23                                        ; $345d
    call TransferTable0F                             ; $345f
    xor a                                            ; $3462
    ld hl, $defe                                     ; $3463
    ld a, [hl]                                       ; $3466
    and $0f                                          ; $3467
    ld [hl+], a                                      ; $3469
    ld [hl], $00                                     ; $346a
    ldh [$ff95], a                                   ; $346c
    jp IncStateTimer                                 ; $346e

SECTION "Save scroll shadow", ROM0[$34cf]
SaveAndClearScroll::
    ld hl, $c707                                     ; $34cf
    ld de, $c80d                                     ; $34d2
    ld a, [hl]                                       ; $34d5
    ld [de], a                                       ; $34d6
    xor a                                            ; $34d7
    ld [hl+], a                                      ; $34d8
    inc de                                           ; $34d9
    ld a, [hl]                                       ; $34da
    ld [de], a                                       ; $34db
    xor a                                            ; $34dc
    ld [hl], a                                       ; $34dd
    ret                                              ; $34de

SECTION "Setup next screen", ROM0[$34b9]
SetupNextScreen::
    call SendSGBPacket7AndLCDOff                     ; $34b9
    call InitStatePtrs                               ; $34bc
    call $1643                                       ; $34bf
    xor a                                            ; $34c2
    ldh [$ff8f], a                                   ; $34c3
    call ResetWindowPos                              ; $34c5
    call IncStateTimer                               ; $34c8
    ld a, $01                                        ; $34cb
    rst $10                                          ; $34cd
    ret                                              ; $34ce

; --- State 28 ($3471-$34b6). --------------------------------------------------
; 6-entry table; entry 5 = $01fb (the soft-reset body inside CheckSoftReset
; -- flagged, same as state 17 entry 5; whether the timer ever reaches 5
; here is unverified). Role unknown; not visited in traces.
SECTION "State 28 handler", ROM0[$3471]
State28::
    ld a, $01               ; $3471
    rst $10                 ; $3473: bank 1
    ldh a, [hStateTimer]    ; $3474
    rst $08                 ; $3476: jump through State28Table[hStateTimer]
State28Table::
    dw $3483, $4c1b, $4ca2, $4cb6, $4ca2, $01fb

SECTION "State 28 step 0", ROM0[$3483]
; NOTE: mgbdis mis-disassembles this routine (its linear sweep drifts by
; one byte after the $3477 table, reading $3483 as part of `ld bc,$b9cd`);
; the code below is hand-decoded from the ROM bytes and byte-verified.
State28Step0::
    call SetupNextScreen                             ; $3483
    call SaveAndClearScroll                          ; $3486
    ld a, $0a                                        ; $3489
    call LoadPalette                                 ; $348b
    ld a, $08                                        ; $348e
    call TransferTable1E                             ; $3490
    ld a, $09                                        ; $3493
    call LoadSpriteTable                             ; $3495
    call $20c9                                       ; $3498
    xor a                                            ; $349b
    ldh [rSCY], a                                    ; $349c
    ldh [rSCX], a                                    ; $349e
    ld a, $09                                        ; $34a0
    call TransferTable0F                             ; $34a2
    ld a, $3a                                        ; $34a5
    ld [$c836], a                                    ; $34a7
    xor a                                            ; $34aa
    ld [wDecompOutLen], a                                    ; $34ab
    call $10dd                                       ; $34ae
    call RestoreInterruptsAndLCDC                    ; $34b1
    ld a, $08                                        ; $34b4
    jp SendSGBPacketIfSGB                            ; $34b6

; --- State 17: file select ($34df-$3581). --------------------------------------
; Reads save slots [$c860]/[$c861], draws the file info at $9c8d/$9c8f via
; PutNumberTiles ($3556: table $3723). Entry 5 of the table = $01fb (the
; soft-reset body); the timer reaching 5 would jump into CheckSoftReset's
; body and reset to state 2 -- unverified whether that ever happens.
SECTION "State 17 handler", ROM0[$34df]
FileSelect::
    ld a, $01               ; $34df
    rst $10                 ; $34e1: bank 1
    ldh a, [hStateTimer]    ; $34e2
    rst $08                 ; $34e4: jump through FileSelectTable[hStateTimer]
FileSelectTable::
    dw $34f5, $4d66, $4e6d, $4e06, $4e7c, $01fb, $34fb, $4e77

SECTION "File select setup", ROM0[$34f5]
FileSelectSetup::
    call $4e87                                       ; $34f5
    call SaveAndClearScroll                          ; $34f8
    call SetupNextScreen                             ; $34fb
    ld a, $2b                                        ; $34fe
    ldh [$ff8f], a                                   ; $3500
    ld a, $09                                        ; $3502
    call LoadPalette                                 ; $3504
    ld a, $0d                                        ; $3507
    call TransferTable1E                             ; $3509
    ld a, $0a                                        ; $350c
    call TransferTable0F                             ; $350e
    ld a, [$c860]                                    ; $3511
    ld h, $00                                        ; $3514
    ld l, a                                          ; $3516
    call $201d                                       ; $3517
    ld de, $9c8d                                     ; $351a
    ld a, [$c81f]                                    ; $351d
    call PutNumberTiles                              ; $3520
    ld a, [$c861]                                    ; $3523
    ld h, $00                                        ; $3526
    ld l, a                                          ; $3528
    call $201d                                       ; $3529
    ld de, $9c8f                                     ; $352c
    ld a, [$c81e]                                    ; $352f
    or a                                             ; $3532
    jr z, L_3539                                     ; $3533
    call PutNumberTiles                              ; $3535
    inc de                                           ; $3538
L_3539::
    ld a, [$c81f]                                    ; $3539
    call PutNumberTiles                              ; $353c
    ld a, $05                                        ; $353f
    call BuildSpriteEntries                          ; $3541
    xor a                                            ; $3544
    ld [wDecompOutLen], a                                    ; $3545
    call $0ecd                                       ; $3548
    call $10dd                                       ; $354b
    call RestoreInterruptsAndLCDC                    ; $354e
    ld a, $06                                        ; $3551
    jp SendSGBPacketIfSGB                            ; $3553

SECTION "Put number tiles", ROM0[$3556]
PutNumberTiles::
    push de                                          ; $3556
    ld hl, $3723                                     ; $3557
    ld b, $00                                        ; $355a
    ld c, a                                          ; $355c
    add hl, bc                                       ; $355d
    ld a, [hl]                                       ; $355e
    ld [de], a                                       ; $355f
    ld a, e                                          ; $3560
    add $20                                          ; $3561
    ld e, a                                          ; $3563
    ld a, d                                          ; $3564
    adc $00                                          ; $3565
    ld d, a                                          ; $3567
    ld c, $0a                                        ; $3568
    add hl, bc                                       ; $356a
    ld a, [hl]                                       ; $356b
    ld [de], a                                       ; $356c
    pop de                                           ; $356d
    ret                                              ; $356e

SECTION "Load tiles from bank 4", ROM0[$356f]
LoadTilesFromBank4::
    ld a, $04                                        ; $356f
    rst $10                                          ; $3571
    ld hl, $67b0                                     ; $3572
    ld de, $8000                                     ; $3575
    ld bc, $0300                                     ; $3578
    call MemcpyBC                                    ; $357b
    ld a, $01                                        ; $357e
    rst $10                                          ; $3580
    ret                                              ; $3581

; --- State 21 ($3582-$3599). ---------------------------------------------------
; 9-entry table, all bank-1 targets ($4f31-$5051). Role unknown; not visited.
SECTION "State 21 handler", ROM0[$3582]
State21::
    ld a, $01               ; $3582
    rst $10                 ; $3584: bank 1
    ldh a, [hStateTimer]    ; $3585
    rst $08                 ; $3587: jump through State21Table[hStateTimer]
State21Table::
    dw $4f31, $4fbd, $4fcf, $4fd2, $5004, $5018, $501d, $5048
    dw $5051

; --- State 3: post-Start screen ($359a-$35e9). ----------------------------------
; 37-entry table (bank-1 targets $5131-$56f1, one bank-0 $362a at index 29);
; entries repeat ($5131/$52cc/$531c/$53e7 recur) -- a looping animation.
; Trace: entered from TitleScreen on Start; timer 1 ($5131) waits for A,
; then -> 16 -> 4.
SECTION "State 3 handler", ROM0[$359a]
PostStart::
    ld a, $01               ; $359a
    rst $10                 ; $359c: bank 1
    ldh a, [hStateTimer]    ; $359d
    rst $08                 ; $359f: jump through PostStartTable[hStateTimer]
PostStartTable::
    dw $35ea, $5131, $52cc, $531c, $5369, $536c, $5391, $53a7
    dw $53e7, $5131, $52cc, $531c, $53e7, $53ea, $536c, $5391
    dw $53e7, $5413, $541f, $5558, $55b7, $5687, $5619, $55b7
    dw $5687, $5694, $56d7, $56f1, $53e7, $362a, $5695, $56cc
    dw $5695, $56c3, $5247, $5269, $5273

; --- State 3 step 0 ($35ea) and step 29 ($362a, table index 29). --------------
; Step 0 validates the save file (ValidateSave $1ed2) and loads the
; file-select data (TransferTable1E 10, LoadSpriteTable 7, TransferTable0F
; $0b, bank-1 $5762). Step 29 re-runs the sprite/table load with [$c202]
; shifted by -$25 (a scroll/offset tweak, inferred).
SECTION "PostStart step 0", ROM0[$35ea]
PostStartStep0::
    call InitStatePtrs                               ; $35ea
    call SendSGBPacket7AndLCDOff                     ; $35ed
    call $1643                                       ; $35f0
    call ValidateSave                                ; $35f3
    call $1ff6                                       ; $35f6
    ld a, $0a                                        ; $35f9
    call TransferTable1E                             ; $35fb
    ld a, $07                                        ; $35fe
    call LoadSpriteTable                             ; $3600
    ld a, $0b                                        ; $3603
    call TransferTable0F                             ; $3605
    call $5762                                       ; $3608
    ld hl, $c817                                     ; $360b
    xor a                                            ; $360e
    ld [hl+], a                                      ; $360f
    ld [hl], a                                       ; $3610
    ldh [rWY], a                                     ; $3611
    ld a, $a7                                        ; $3613
    ldh [rWX], a                                     ; $3615
    ld a, $2b                                        ; $3617
    ld [$c836], a                                    ; $3619
    call IncStateTimer                               ; $361c
    call $10dd                                       ; $361f
    call RestoreInterruptsAndLCDC                    ; $3622
    ld a, $0c                                        ; $3625
    jp SendSGBPacketIfSGB                            ; $3627

SECTION "PostStart step 29", ROM0[$362a]
PostStartStep29::
    call SendSGBPacket7AndLCDOff                     ; $362a
    ld a, [$c202]                                    ; $362d
    push af                                          ; $3630
    ld a, [$c207]                                    ; $3631
    push af                                          ; $3634
    ld a, $07                                        ; $3635
    call LoadSpriteTable                             ; $3637
    ld a, $0b                                        ; $363a
    call TransferTable0F                             ; $363c
    call $5743                                       ; $363f
    pop af                                           ; $3642
    ld [$c207], a                                    ; $3643
    pop af                                           ; $3646
    sub $25                                          ; $3647
    ld [$c202], a                                    ; $3649
    call $10dd                                       ; $364c
    call RestoreInterruptsAndLCDC                    ; $364f
    ld a, $0c                                        ; $3652
    jp SendSGBPacketIfSGB                            ; $3654

; --- State 8 ($3657-$3662). ------------------------------------------------------
; 3-entry table, bank-1 targets (CORRECTED: the prologue switches to bank 1,
; not 12 -- slice-2 draft had this wrong, caught by the byte-match check).
; Step 0 ($58f3, bank 1): InitStatePtrs, SGB packet 1, LCD off, $1643,
; TransferTable1E $0e, ClearTilemap9C00, TransferTable0F $1e, then $5986.
; Step 1 ($593c): reads hJoypadNew, waits for input (ret z), sets
; [$c82f]/[$c835] = 5 or $30, then IncStateTimer. Step 2 ($5977): loads the
; next (timer, state) pair from WRAM $c80f/$c810 and jumps there -- a generic
; state-transition step, and how state 8 exits. Role unknown; never visited
; in traces. (The credits text at bank-12 $59a0 belongs to states 22/26's
; bank, not this one.)
SECTION "State 8 handler", ROM0[$3657]
State08::
    ld a, $01               ; $3657
    rst $10                 ; $3659: bank 1
    ldh a, [hStateTimer]    ; $365a
    rst $08                 ; $365c: jump through State08Table[hStateTimer]
State08Table::
    dw $58f3, $593c, $5977

; --- State 22 ($3663-$3678). -------------------------------------------------------
; 8-entry table, all bank-12 targets ($553d-$5680). Role unknown; not visited.
SECTION "State 22 handler", ROM0[$3663]
State22::
    ld a, $0c               ; $3663
    rst $10                 ; $3665: bank 12
    ldh a, [hStateTimer]    ; $3666
    rst $08                 ; $3668: jump through State22Table[hStateTimer]
State22Table::
    dw $553d, $561c, $5651, $5651, $5651, $569b, $562c, $5680

; --- State 26 ($3679-$3688). -------------------------------------------------------
; 5-entry table; entries 5+ would be data ($3689+ is a data stream, not
; code). Role unknown; not visited.
SECTION "State 26 handler", ROM0[$3679]
State26::
    ld a, $0c               ; $3679
    rst $10                 ; $367b: bank 12
    ldh a, [hStateTimer]    ; $367c
    rst $08                 ; $367e: jump through State26Table[hStateTimer]
State26Table::
    dw $57ca, $5827, $5862, $58ed, $5430
