; Donkey Kong '94 -- slice 2: bitstream decompressor ($257b-$266b) + helpers.
; Called from TransferTable1E ($1ddf/$1de4) and from the SGB border code
; ($24bd/$255b/$379e/$37b8/$37d2/$37ec/$3806). Entry points:
;   DecompressPrefixed $257b -- BC (output length) is read from the stream.
;   Decompress $257f -- BC = output length, DE = destination, HL = source.
; State at wDecompOutLen-wDecompDst + 1: output length (lo/hi), destination (lo/hi).

SECTION "Decompressor", ROM0[$257b]
DecompressPrefixed::
    ld a, [hl+]                                      ; $257b
    ld c, a                                          ; $257c
    ld a, [hl+]                                      ; $257d
    ld b, a                                          ; $257e
Decompress::
    push hl                                          ; $257f
    ld hl, wDecompOutLen                                     ; $2580
    ld a, c                                          ; $2583
    ld [hl+], a                                      ; $2584
    ld a, b                                          ; $2585
    ld [hl+], a                                      ; $2586
    ld a, e                                          ; $2587
    ld [hl+], a                                      ; $2588
    ld [hl], d                                       ; $2589
    ld de, $0000                                     ; $258a
    pop hl                                           ; $258d
L_258e::
    ld a, [hl+]                                      ; $258e
    ld b, a                                          ; $258f
    ld c, $08                                        ; $2590
L_2592::
    push bc                                          ; $2592
    bit 0, b                                         ; $2593
    jr z, L_25a9                                     ; $2595
    ld a, [hl+]                                      ; $2597
    call DecompWriteByte                             ; $2598
    ld a, [wDecompOutLen]                                    ; $259b
    cp e                                             ; $259e
    jr nz, L_25dd                                    ; $259f
    ld a, [wDecompOutLen + 1]                                    ; $25a1
    cp d                                             ; $25a4
    jr nz, L_25dd                                    ; $25a5
    jr L_25e5                                        ; $25a7
L_25a9::
    ld a, [hl+]                                      ; $25a9
    ld c, a                                          ; $25aa
    ld a, [hl+]                                      ; $25ab
    push hl                                          ; $25ac
    ld b, a                                          ; $25ad
    and $f0                                          ; $25ae
    swap a                                           ; $25b0
    ld h, a                                          ; $25b2
    ld a, e                                          ; $25b3
    sub c                                            ; $25b4
    ld l, a                                          ; $25b5
    ld a, d                                          ; $25b6
    sbc h                                            ; $25b7
    ld h, a                                          ; $25b8
    ld a, b                                          ; $25b9
    and $0f                                          ; $25ba
    add $03                                          ; $25bc
    ld c, a                                          ; $25be
    ld a, [wDecompDst]                                    ; $25bf
    add l                                            ; $25c2
    ld l, a                                          ; $25c3
    ld a, [wDecompDst + 1]                                    ; $25c4
    adc h                                            ; $25c7
    ld h, a                                          ; $25c8
L_25c9::
    ld a, [hl+]                                      ; $25c9
    call DecompWriteByte                             ; $25ca
    dec c                                            ; $25cd
    jr nz, L_25c9                                    ; $25ce
    pop hl                                           ; $25d0
    ld a, [wDecompOutLen]                                    ; $25d1
    cp e                                             ; $25d4
    jr nz, L_25dd                                    ; $25d5
    ld a, [wDecompOutLen + 1]                                    ; $25d7
    cp d                                             ; $25da
    jr z, L_25e5                                     ; $25db
L_25dd::
    pop bc                                           ; $25dd
    srl b                                            ; $25de
    dec c                                            ; $25e0
    jr nz, L_2592                                    ; $25e1
    jr L_258e                                        ; $25e3
L_25e5::
    pop bc                                           ; $25e5
    ret                                              ; $25e6
DecompWriteByte::
    ld b, a                                          ; $25e7
    push hl                                          ; $25e8
    ld hl, wDecompDst                                     ; $25e9
    ld a, [hl+]                                      ; $25ec
    ld h, [hl]                                       ; $25ed
    ld l, a                                          ; $25ee
    add hl, de                                       ; $25ef
    ld [hl], b                                       ; $25f0
    inc de                                           ; $25f1
    pop hl                                           ; $25f2
    ret                                              ; $25f3
ExpandRLE::
    ld a, b                                          ; $25f4
    or a                                             ; $25f5
    ret z                                            ; $25f6
    ld a, [hl+]                                      ; $25f7
    push af                                          ; $25f8
    and $7f                                          ; $25f9
    ld c, a                                          ; $25fb
    ld a, b                                          ; $25fc
    sub c                                            ; $25fd
    ld b, a                                          ; $25fe
    pop af                                           ; $25ff
    bit 7, a                                         ; $2600
    jr z, L_2609                                     ; $2602
    call $106e                                       ; $2604
    jr ExpandRLE                                     ; $2607
L_2609::
    xor a                                            ; $2609
    ld [de], a                                       ; $260a
    inc de                                           ; $260b
    dec c                                            ; $260c
    jr nz, L_2609                                    ; $260d
    jr ExpandRLE                                     ; $260f
SwitchBankByE::
    ld a, e                                          ; $2611
    cp $2d                                           ; $2612
    ret c                                            ; $2614
    ld a, $06                                        ; $2615
    rst $10                                          ; $2617
    ld a, e                                          ; $2618
    cp $50                                           ; $2619
    ret c                                            ; $261b
    ld a, $12                                        ; $261c
    rst $10                                          ; $261e
    ret                                              ; $261f
LookupStreamEntry::
    ld hl, $c5e3                                     ; $2620
    ld de, $ffe0                                     ; $2623
    ld c, $20                                        ; $2626
L_2628::
    ld a, [wDecompOutLen]                                    ; $2628
    cp [hl]                                          ; $262b
    jr nz, L_2639                                    ; $262c
    push hl                                          ; $262e
    inc hl                                           ; $262f
    inc hl                                           ; $2630
    inc hl                                           ; $2631
    inc hl                                           ; $2632
    ld a, [wDecompOutLen + 1]                                    ; $2633
    cp [hl]                                          ; $2636
    pop hl                                           ; $2637
    ret z                                            ; $2638
L_2639::
    add hl, de                                       ; $2639
    dec c                                            ; $263a
    jr nz, L_2628                                    ; $263b
    ret                                              ; $263d
CallBank9Dispatch::
    ldh a, [$ff8c]                                   ; $263e
    push af                                          ; $2640
    ld a, $09                                        ; $2641
    rst $10                                          ; $2643
    call DispatchLevel                               ; $2644
    pop af                                           ; $2647
    rst $10                                          ; $2648
    ret                                              ; $2649
DispatchLevel::
    ld a, [$c725]                                    ; $264a
    cp $07                                           ; $264d
    jp z, $62cd                                      ; $264f
    cp $18                                           ; $2652
    jp z, $6308                                      ; $2654
    cp $27                                           ; $2657
    jp z, $636f                                      ; $2659
    cp $00                                           ; $265c
    jp z, $6182                                      ; $265e
    cp $0c                                           ; $2661
    jp z, $61f4                                      ; $2663
    cp $23                                           ; $2666
    jp z, $6266                                      ; $2668
    ret                                              ; $266b
