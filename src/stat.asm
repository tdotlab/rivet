; Donkey Kong '94 -- slice 2: STAT (LYC) scanline effects.
; The STAT dispatch table has 58 entries (hSTATState 0-57), not 16 as slice 1
; assumed: entry 0's code sets hSTATState=$39, and the table runs $02ef-$0366.
; Targets $0367-$0673 are short WX/LYC/BGP/LCDC setters, chained by the shared
; tails STAT_Next (hSTATState++, ret) and STAT_SetState (hSTATState=A, ret).
; The two blocks $03a2/$03ad have no call/jp/jr reference found anywhere in the
; ROM -- they are kept literal, not deleted, in case a later slice finds a caller.

SECTION "STAT targets", ROM0[$0367]
STAT_0367::
    ld a, $07                                        ; $0367
    ldh [rWX], a                                     ; $0369
    ld hl, $ff40                                     ; $036b
    res 1, [hl]                                      ; $036e
    ld a, [$da40]                                    ; $0370
    ldh [rBGP], a                                    ; $0373
    ld a, $07                                        ; $0375
    ldh [rLYC], a                                    ; $0377
STAT_Next::
    ld hl, $ff8f                                     ; $0379
    inc [hl]                                         ; $037c
STAT_037d::
    ret                                              ; $037d
STAT_037e::
    ld hl, $ff40                                     ; $037e
    set 1, [hl]                                      ; $0381
    ld a, $a7                                        ; $0383
    ldh [rWX], a                                     ; $0385
    ld a, $4f                                        ; $0387
    ldh [rLYC], a                                    ; $0389
    call RestorePaletteFromShadow                                       ; $038b
    ld a, $39                                        ; $038e
    jr STAT_SetState                                 ; $0390
STAT_Prev::
    ld hl, $ff8f                                     ; $0392
    dec [hl]                                         ; $0395
    ret                                              ; $0396
STAT_0397::
    ld a, $a7                                        ; $0397
    ldh [rWX], a                                     ; $0399
    ld a, $67                                        ; $039b
    ldh [rLYC], a                                    ; $039d
    jp STAT_Next                                     ; $039f
STAT_03a2::
    ld a, $a7                                        ; $03a2
    ldh [rWX], a                                     ; $03a4
    ld a, $8f                                        ; $03a6
    ldh [rLYC], a                                    ; $03a8
    jp STAT_Next                                     ; $03aa
STAT_03ad::
    ld a, $07                                        ; $03ad
    ldh [rWX], a                                     ; $03af
    xor a                                            ; $03b1
    ldh [rLYC], a                                    ; $03b2
    ld a, $01                                        ; $03b4
    jp STAT_SetState                                 ; $03b6
STAT_03b9::
    ld hl, $ff40                                     ; $03b9
    set 1, [hl]                                      ; $03bc
    ld a, $a7                                        ; $03be
    ldh [rWX], a                                     ; $03c0
    call RestorePaletteFromShadow                                       ; $03c2
    ld a, $4f                                        ; $03c5
    ldh [rLYC], a                                    ; $03c7
    jr STAT_Next                                     ; $03c9
STAT_03cb::
    ld hl, $ff40                                     ; $03cb
    res 1, [hl]                                      ; $03ce
    ld a, $07                                        ; $03d0
    ldh [rWX], a                                     ; $03d2
    ld a, $57                                        ; $03d4
    ldh [rLYC], a                                    ; $03d6
    jp STAT_Next                                     ; $03d8
STAT_03db::
    ld hl, $ff40                                     ; $03db
    set 1, [hl]                                      ; $03de
    ld a, $a7                                        ; $03e0
    ldh [rWX], a                                     ; $03e2
    xor a                                            ; $03e4
    ldh [rLYC], a                                    ; $03e5
    ld a, $03                                        ; $03e7
STAT_SetState::
    ldh [$ff8f], a                                   ; $03e9
    ret                                              ; $03eb
STAT_03ec::
    xor a                                            ; $03ec
    ldh [rWY], a                                     ; $03ed
    ld a, $07                                        ; $03ef
    ldh [rWX], a                                     ; $03f1
    ld hl, $c813                                     ; $03f3
    inc [hl]                                         ; $03f6
    ld a, [hl]                                       ; $03f7
    and $03                                          ; $03f8
    ld [hl+], a                                      ; $03fa
    jr nz, L_0404                                    ; $03fb
    ld a, [hl]                                       ; $03fd
    and $03                                          ; $03fe
    inc a                                            ; $0400
    or $e4                                           ; $0401
    ld [hl], a                                       ; $0403
L_0404::
    ld a, [hl]                                       ; $0404
    ldh [rBGP], a                                    ; $0405
L_0407::
    ld a, $17                                        ; $0407
    ldh [rLYC], a                                    ; $0409
    jp STAT_Next                                     ; $040b
STAT_040e::
    ld a, $57                                        ; $040e
    ldh [rLYC], a                                    ; $0410
L_0412::
    ld a, $a7                                        ; $0412
    ldh [rWX], a                                     ; $0414
    ld a, $e4                                        ; $0416
    ldh [rBGP], a                                    ; $0418
    jp STAT_Next                                     ; $041a
STAT_041d::
    ld a, $57                                        ; $041d
    ldh [rLYC], a                                    ; $041f
    jr L_0412                                        ; $0421
STAT_0423::
    call STAT_0459                                   ; $0423
    jr STAT_0447                                     ; $0426
STAT_0428::
    call STAT_0452                                   ; $0428
    ld a, $0f                                        ; $042b
    jr STAT_SetState                                 ; $042d
STAT_042f::
    ld a, $e4                                        ; $042f
    ldh [rBGP], a                                    ; $0431
    jr L_0407                                        ; $0433
STAT_0435::
    ld a, $e4                                        ; $0435
    ldh [rBGP], a                                    ; $0437
    ld a, $57                                        ; $0439
    ldh [rLYC], a                                    ; $043b
    jp STAT_Next                                     ; $043d
STAT_0440::
    ld a, $80                                        ; $0440
    ldh [rLYC], a                                    ; $0442
    jp STAT_Next                                     ; $0444
STAT_0447::
    xor a                                            ; $0447
    ldh [rLYC], a                                    ; $0448
    ld hl, $ff8f                                     ; $044a
    ld a, [hl]                                       ; $044d
    sub $03                                          ; $044e
    ld [hl], a                                       ; $0450
    ret                                              ; $0451
STAT_0452::
    xor a                                            ; $0452
    ldh [rLYC], a                                    ; $0453
    ld a, $a7                                        ; $0455
    ldh [rWX], a                                     ; $0457
STAT_0459::
    ld hl, $c812                                     ; $0459
    inc [hl]                                         ; $045c
    dec hl                                           ; $045d
    ld a, [hl+]                                      ; $045e
    or a                                             ; $045f
    jr z, L_046d                                     ; $0460
    ld a, $e0                                        ; $0462
    ldh [rSCX], a                                    ; $0464
    ld a, [hl]                                       ; $0466
    and $07                                          ; $0467
    ld [hl-], a                                      ; $0469
    ret nz                                           ; $046a
    dec [hl]                                         ; $046b
    ret                                              ; $046c
L_046d::
    ld a, [hl]                                       ; $046d
    and $0f                                          ; $046e
    ld [hl-], a                                      ; $0470
    ret nz                                           ; $0471
    inc [hl]                                         ; $0472
    ret                                              ; $0473
STAT_0474::
    ld a, $07                                        ; $0474
    ldh [rWX], a                                     ; $0476
    ld a, $80                                        ; $0478
    ldh [rLYC], a                                    ; $047a
    jp STAT_Next                                     ; $047c
STAT_047f::
    ld a, $07                                        ; $047f
    ldh [rWX], a                                     ; $0481
    ld hl, $068d                                     ; $0483
    ld a, [$ce1c]                                    ; $0486
    ld d, $00                                        ; $0489
    ld e, a                                          ; $048b
    add hl, de                                       ; $048c
    ld a, [hl]                                       ; $048d
    ldh [rLYC], a                                    ; $048e
    jp STAT_Next                                     ; $0490
STAT_0493::
    ld a, $a7                                        ; $0493
    ldh [rWX], a                                     ; $0495
    xor a                                            ; $0497
    ldh [rLYC], a                                    ; $0498
    jp STAT_Prev                                     ; $049a
STAT_049d::
    ld hl, $ff40                                     ; $049d
    set 1, [hl]                                      ; $04a0
    ld a, $a7                                        ; $04a2
    ldh [rWX], a                                     ; $04a4
    call RestorePaletteFromShadow                                       ; $04a6
    ld a, $67                                        ; $04a9
    ldh [rLYC], a                                    ; $04ab
    jp STAT_Next                                     ; $04ad
STAT_04b0::
    ld a, $07                                        ; $04b0
    ldh [rWX], a                                     ; $04b2
    ld hl, $ff40                                     ; $04b4
    res 1, [hl]                                      ; $04b7
    call L_04c3                                      ; $04b9
    ld a, $8f                                        ; $04bc
    ldh [rLYC], a                                    ; $04be
    jp STAT_Next                                     ; $04c0
L_04c3::
    ld a, [$da40]                                    ; $04c3
    ld hl, $c82b                                     ; $04c6
    bit 7, [hl]                                      ; $04c9
    jr nz, L_04cf                                    ; $04cb
    res 7, a                                         ; $04cd
L_04cf::
    ldh [rBGP], a                                    ; $04cf
    ret                                              ; $04d1
STAT_04d2::
    xor a                                            ; $04d2
    ldh [rLYC], a                                    ; $04d3
    ld a, $15                                        ; $04d5
    jp STAT_SetState                                 ; $04d7
STAT_04da::
    ld hl, $ff40                                     ; $04da
    res 1, [hl]                                      ; $04dd
    ldh a, [$ff95]                                   ; $04df
    and $08                                          ; $04e1
    jr z, L_04e7                                     ; $04e3
    ld a, $90                                        ; $04e5
L_04e7::
    ldh [rSCY], a                                    ; $04e7
    call L_04c3                                      ; $04e9
    ld a, [$def5]                                    ; $04ec
    ldh [rLYC], a                                    ; $04ef
    jp STAT_Next                                     ; $04f1
STAT_04f4::
    ld hl, $ff40                                     ; $04f4
    set 1, [hl]                                      ; $04f7
    xor a                                            ; $04f9
    ldh [rSCY], a                                    ; $04fa
    call $067b                                       ; $04fc
    ld a, [$def6]                                    ; $04ff
    ldh [rLYC], a                                    ; $0502
    jp STAT_Next                                     ; $0504
STAT_0507::
    ld hl, $ff40                                     ; $0507
    res 1, [hl]                                      ; $050a
    call L_04c3                                      ; $050c
    xor a                                            ; $050f
    ldh [rLYC], a                                    ; $0510
    ld a, $19                                        ; $0512
    jp STAT_SetState                                 ; $0514
STAT_0517::
    ld a, $07                                        ; $0517
    ldh [rWX], a                                     ; $0519
    ld a, $48                                        ; $051b
    ldh [rLYC], a                                    ; $051d
    jp STAT_Next                                     ; $051f
STAT_0522::
    ld a, $50                                        ; $0522
    ldh [rSCY], a                                    ; $0524
    ld a, $97                                        ; $0526
    ldh [rWX], a                                     ; $0528
    ld a, $68                                        ; $052a
    ldh [rLYC], a                                    ; $052c
    jp STAT_Next                                     ; $052e
STAT_0531::
    ld a, $07                                        ; $0531
    ldh [rWX], a                                     ; $0533
    xor a                                            ; $0535
    ldh [rLYC], a                                    ; $0536
    ld a, $1f                                        ; $0538
    jp STAT_SetState                                 ; $053a
STAT_053d::
    ld a, $a7                                        ; $053d
    ldh [rWX], a                                     ; $053f
    ld a, [$c817]                                    ; $0541
    or a                                             ; $0544
    jr nz, L_054d                                    ; $0545
    xor a                                            ; $0547
    ldh [rLYC], a                                    ; $0548
    jp STAT_Prev                                     ; $054a
L_054d::
    ld a, $28                                        ; $054d
L_054f::
    ldh [rLYC], a                                    ; $054f
    jp STAT_Next                                     ; $0551
STAT_0554::
    ld a, $68                                        ; $0554
    ldh [rSCY], a                                    ; $0556
    ld a, $5a                                        ; $0558
    jr L_054f                                        ; $055a
STAT_055c::
    xor a                                            ; $055c
    ldh [rSCY], a                                    ; $055d
    ldh [rLYC], a                                    ; $055f
    ld a, $22                                        ; $0561
    jp STAT_SetState                                 ; $0563
STAT_0566::
    ld hl, $ff40                                     ; $0566
    res 1, [hl]                                      ; $0569
    xor a                                            ; $056b
    ldh [rSCY], a                                    ; $056c
    ld a, $a7                                        ; $056e
    ldh [rWX], a                                     ; $0570
    ld a, $20                                        ; $0572
    ldh [rLYC], a                                    ; $0574
    jp STAT_Next                                     ; $0576
STAT_0579::
    ld hl, $ff40                                     ; $0579
    set 1, [hl]                                      ; $057c
    ld a, $3f                                        ; $057e
    ldh [rLYC], a                                    ; $0580
    ld a, [$c817]                                    ; $0582
    or a                                             ; $0585
    jr z, L_058c                                     ; $0586
    ld a, $70                                        ; $0588
    ldh [rSCY], a                                    ; $058a
L_058c::
    jp STAT_Next                                     ; $058c
STAT_058f::
    ld hl, $ff40                                     ; $058f
    res 1, [hl]                                      ; $0592
    ld a, $58                                        ; $0594
    ldh [rLYC], a                                    ; $0596
    xor a                                            ; $0598
    ldh [rSCY], a                                    ; $0599
    jp STAT_Next                                     ; $059b
STAT_059e::
    ld hl, $ff40                                     ; $059e
    set 1, [hl]                                      ; $05a1
    xor a                                            ; $05a3
    ldh [rLYC], a                                    ; $05a4
    ld a, [$c818]                                    ; $05a6
    or a                                             ; $05a9
    jr z, L_05b0                                     ; $05aa
    ld a, $58                                        ; $05ac
    ldh [rSCY], a                                    ; $05ae
L_05b0::
    ld a, $26                                        ; $05b0
    jp STAT_SetState                                 ; $05b2
STAT_05b5::
    ld a, $07                                        ; $05b5
    ldh [rWX], a                                     ; $05b7
    ldh [rLYC], a                                    ; $05b9
    jp STAT_Next                                     ; $05bb
STAT_05be::
    ld a, $0f                                        ; $05be
    ldh [rBGP], a                                    ; $05c0
    ld a, $07                                        ; $05c2
    ldh [rLYC], a                                    ; $05c4
    jp STAT_Next                                     ; $05c6
STAT_05c9::
    ld a, $9c                                        ; $05c9
    ldh [rBGP], a                                    ; $05cb
    xor a                                            ; $05cd
    ldh [rLYC], a                                    ; $05ce
    jp STAT_Prev                                     ; $05d0
STAT_05d3::
    ld hl, $ff40                                     ; $05d3
    res 0, [hl]                                      ; $05d6
    res 1, [hl]                                      ; $05d8
    ld a, $07                                        ; $05da
    ldh [rWX], a                                     ; $05dc
    ld a, [$c811]                                    ; $05de
    ldh [rLYC], a                                    ; $05e1
    jp STAT_Next                                     ; $05e3
STAT_05e6::
    ld a, [$c816]                                    ; $05e6
    ldh [rOBP0], a                                   ; $05e9
    ldh [rOBP1], a                                   ; $05eb
    ld hl, $ff40                                     ; $05ed
    set 0, [hl]                                      ; $05f0
    set 1, [hl]                                      ; $05f2
    ld a, [$c813]                                    ; $05f4
    ldh [rWX], a                                     ; $05f7
    ld a, [$c812]                                    ; $05f9
    ldh [rLYC], a                                    ; $05fc
    jp STAT_Next                                     ; $05fe
STAT_0601::
    ld hl, $ff40                                     ; $0601
    res 0, [hl]                                      ; $0604
    res 1, [hl]                                      ; $0606
    ld a, $07                                        ; $0608
    ldh [rWX], a                                     ; $060a
    xor a                                            ; $060c
    ldh [rLYC], a                                    ; $060d
    ld a, $2d                                        ; $060f
    jp STAT_SetState                                 ; $0611
STAT_0614::
    ld a, [$c811]                                    ; $0614
    ldh [rWX], a                                     ; $0617
    ld a, $0f                                        ; $0619
    ldh [rLYC], a                                    ; $061b
    jp STAT_Next                                     ; $061d
STAT_0620::
    ld a, $a0                                        ; $0620
    ldh [rWX], a                                     ; $0622
    xor a                                            ; $0624
    ldh [rLYC], a                                    ; $0625
    jp STAT_Prev                                     ; $0627
STAT_062a::
    ld hl, $ff40                                     ; $062a
    set 1, [hl]                                      ; $062d
    ld a, $a7                                        ; $062f
    ldh [rWX], a                                     ; $0631
    ld a, $4f                                        ; $0633
    ldh [rLYC], a                                    ; $0635
    jp STAT_Next                                     ; $0637
STAT_063a::
    ld hl, $c867                                     ; $063a
    ld a, [hl+]                                      ; $063d
    ldh [rSCY], a                                    ; $063e
    ld a, [hl+]                                      ; $0640
    ldh [rSCX], a                                    ; $0641
    ld a, $7f                                        ; $0643
    add [hl]                                         ; $0645
    ldh [rLYC], a                                    ; $0646
    jp STAT_Next                                     ; $0648
STAT_064b::
    ld hl, $ff40                                     ; $064b
    res 1, [hl]                                      ; $064e
    xor a                                            ; $0650
    ldh [rLYC], a                                    ; $0651
    ldh [rSCY], a                                    ; $0653
    ldh [rSCX], a                                    ; $0655
    ld a, $07                                        ; $0657
    ldh [rWX], a                                     ; $0659
    ld a, $32                                        ; $065b
    jp STAT_SetState                                 ; $065d
STAT_0660::
    ld hl, $ff40                                     ; $0660
    set 1, [hl]                                      ; $0663
    ld a, $a7                                        ; $0665
    ldh [rWX], a                                     ; $0667
    call RestorePaletteFromShadow                                       ; $0669
    ld a, $4f                                        ; $066c
    ldh [rLYC], a                                    ; $066e
    jp STAT_Next                                     ; $0670
STAT_0673::
    xor a                                            ; $0673

; $0680-$068c -- reload BGP/OBP0/OBP1 from the shadow copy at $da3d.
; Called from STAT targets $038b/$03c2 (mid-frame palette restore).
SECTION "RestorePaletteFromShadow", ROM0[$0680]
RestorePaletteFromShadow::
    ld hl, $da3d                                     ; $0680
    ld a, [hl+]                                      ; $0683
    ldh [rBGP], a                                    ; $0684
    ld a, [hl+]                                      ; $0686
    ldh [rOBP0], a                                   ; $0687
    ld a, [hl]                                       ; $0689
    ldh [rOBP1], a                                   ; $068a
    ret                                              ; $068c

; $068d-$0691 -- 5 unidentified bytes between RestorePaletteFromShadow and
; the state-18 handler at $0692. Kept literal; not code (no reference found).
SECTION "Unknown 068d", ROM0[$068d]
    db $10, $49, $64, $82, $8f  ; $068d-$0691
