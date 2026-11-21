; Super Game Boy support (slice 1).
; All of this runs from bank 0 except the packet data, which lives in
; bank $1e at $4000 (a table of pointers, one per packet index).
; The SGB protocol is bit-banged out of the joypad port (rP1): a 0 bit
; is a $10 pulse, a 1 bit is a $20 pulse, $30 is idle. That is what
; SendSGBPacketData does. Packet indices here are indices into bank
; $1e's table, NOT raw SGB command bytes -- do not confuse the two.

; =====================================================================
; $3737-$3854, $391b-$392a -- DetectSGB.
; Enables the VBlank interrupt, sends SGB packet $0a, and reads the
; joypad. On a real Super Game Boy the reply makes P1 read back
; something other than $ff; on a plain Game Boy (or in Nacre, which
; is DMG-only) it stays $ff. If both reads are $ff, this is not an
; SGB: clear bit 7 of wSGBFlag, set wSGBMode=$cc, and return.
; If an SGB answers, set bit 7 of wSGBFlag, set wSGBMode=$9c, and
; transfer the SGB border: fill tilemap $9800, copy/decompress tile
; data from bank $1e into VRAM $8800 in several chunks (each chunk:
; LCD on, send a packet, wait for VBlank, LCD off), then send the
; final packets and jump to SendSGBPackets68To6F.
; The $257f routine used for the transfers is NOT curated yet; it
; lives in the raw region and is most likely the data decompressor
; (the DKGBDisasm reference credits eDKit for the compression code).
; =====================================================================
SECTION "DetectSGB", ROM0[$3737]
DetectSGB::
    ldh a, [rIE]            ; $3737
    set 0, a                ; $3739: enable VBlank interrupt
    ei                      ; $373b
    ld a, $0a
    call SendSGBPacket      ; $373c-$373e: SGB packet $0a
    ldh a, [rP1]            ; $3741
    cp $ff                  ; $3743: $ff = no SGB reply?
    jr nz, DetectSGB_IsSGB ; $3745
    call ReadJoypadRaw      ; $3747
    ldh a, [rP1]            ; $374a
    cp $ff                  ; $374c
    jr nz, DetectSGB_IsSGB ; $374e
    ld a, $09
    call SendSGBPacket      ; $3750-$3752: SGB packet $09
    ld hl, wSGBFlag         ; $3755
    res 7, [hl]             ; $3758: not an SGB
    ld a, $cc
    ld [$da40], a           ; $375a-$375c: wSGBMode = $cc
    di                      ; $375f
    ret                     ; $3760
DetectSGB_IsSGB:
    ld hl, wSGBFlag         ; $3761
    set 7, [hl]             ; $3764: it IS an SGB
    ld a, $9c
    ld [$da40], a           ; $3766-$3768: wSGBMode = $9c
    ld a, $2d
    call SendSGBPacketAndDelay ; $376b-$376d
    ld a, $1f
    call SendSGBPacketAndDelay ; $3770-$3772
    di                      ; $3775
    call SaveIEWaitVBlankLCDOff ; $3776
    ld a, $e4
    ldh [rBGP], a           ; $3779-$377b: palette $e4 (all four shades)
    ld hl, $9800            ; $377d: border tilemap
    ld de, $000c            ; $3780: row stride remainder (32-20)
    ld a, $80               ; $3783: first tile
    ld b, $0d               ; $3785: 13 rows
DetectSGB_FillRow:
    ld c, $14               ; $3787: 20 tiles per row
DetectSGB_FillTile:
    ld [hl+], a             ; $3789
    inc a                   ; $378a
    dec c                   ; $378b
    jr nz, DetectSGB_FillTile ; $378c
    add hl, de              ; $378e: next row
    dec b                   ; $378f
    jr nz, DetectSGB_FillRow ; $3790
    ld a, $1e
    rst $10                 ; $3792-$3794: switch to bank $1e (packet/data bank)
    ld hl, $5212            ; $3795
    ld de, $8800            ; $3798: VRAM tile data
    ld bc, $1000            ; $379b
    call $257f              ; $379e: transfer/decompress (TODO: name)
    ld a, $81
    ldh [rLCDC], a          ; $37a1-$37a3: LCD on, BG on
    ld a, $27
    call SendSGBPacketAndDelay ; $37a5-$37a7
    ei                      ; $37aa
    di                      ; $37ab
    call SaveIEWaitVBlankLCDOff ; $37ac
    ld hl, $5d9c            ; $37af
    ld de, $8800            ; $37b2
    ld bc, $06e0            ; $37b5
    call $257f              ; $37b8
    ld a, $81
    ldh [rLCDC], a          ; $37bb-$37bd
    ld a, $2a
    call SendSGBPacketAndDelay ; $37bf-$37c1
    ei                      ; $37c4
    di                      ; $37c5
    call SaveIEWaitVBlankLCDOff ; $37c6
    ld hl, $6145            ; $37c9
    ld de, $8800            ; $37cc
    ld bc, $0860            ; $37cf
    call $257f              ; $37d2
    ld a, $81
    ldh [rLCDC], a          ; $37d5-$37d7
    ld a, $28
    call SendSGBPacketAndDelay ; $37d9-$37db
    ei                      ; $37de
    di                      ; $37df
    call SaveIEWaitVBlankLCDOff ; $37e0
    ld hl, $4710            ; $37e3
    ld de, $8800            ; $37e6
    ld bc, $1000            ; $37e9
    call $257f              ; $37ec
    ld a, $81
    ldh [rLCDC], a          ; $37ef-$37f1
    ld a, $10
    call SendSGBPacketAndDelay ; $37f3-$37f5
    ei                      ; $37f8
    di                      ; $37f9
    call SaveIEWaitVBlankLCDOff ; $37fa
    ld hl, $4c92            ; $37fd
    ld de, $8800            ; $3800
    ld bc, $0fd2            ; $3803
    call $257f              ; $3806
    ld a, $81
    ldh [rLCDC], a          ; $3809-$380b
    ld a, $11
    call SendSGBPacketAndDelay ; $380d-$380f
    ei                      ; $3812
    di                      ; $3813
    call SaveIEWaitVBlankLCDOff ; $3814
    ld a, $0c
    rst $10                 ; $3817-$3819: switch to bank $0c
    ld hl, $5ddd            ; $381a
    ld de, $8800            ; $381d
    ld bc, $0680            ; $3820
    call MemcpyBC           ; $3823
    ld a, $81
    ldh [rLCDC], a          ; $3826-$3828
    ld a, $20
    call SendSGBPacketAndDelay ; $382a-$382c
    ei                      ; $382f
    di                      ; $3830
    call SaveIEWaitVBlankLCDOff ; $3831
    ld hl, $6438            ; $3834
    ld de, $8800            ; $3837
    ld bc, $0bca            ; $383a
    call MemcpyBC           ; $383d
    ld a, $81
    ldh [rLCDC], a          ; $3840-$3842
    ld a, $20
    call SendSGBPacketAndDelay ; $3844-$3846
    ei                      ; $3849
    ld a, $05
    call SendSGBPacketIfSGB ; $384a-$384c: SGB packet $05
    ld a, $09
    call SendSGBPacketIfSGB ; $384f-$3851: SGB packet $09
    jp SendSGBPackets68To6F ; $3854

; $3857: send SGB packet A (gated on SGB), then a long delay (8x).
; $385e: short delay only (4x). $3860: the delay loop itself,
; B iterations of a $06d6-count nop loop ($3885).
SECTION "SGB delays", ROM0[$3857]
SendSGBPacketAndDelay::
    call SendSGBPacketIfSGB ; $3857
    ld b, $08               ; $385a
    jr SGBDelayLoop         ; $385c
SGBDelayShort::
    ld b, $04               ; $385e
SGBDelayLoop::
    ld de, $06d6            ; $3860
    call DelayDE            ; $3863
    dec b                   ; $3866
    jr nz, SGBDelayLoop     ; $3867
    ret                     ; $3869

; $386a: save IE, mask out VBlank, wait for LY >= $91 (VBlank),
; turn the LCD off (LCDC bit 7 clear), restore IE.
SECTION "SGB vblank wait", ROM0[$386a]
SaveIEWaitVBlankLCDOff::
    ldh a, [rIE]            ; $386a
    ld [wIEShadow], a       ; $386c: save IE
    res 0, a                ; $386f: mask out VBlank
    ldh [rIE], a            ; $3871
SaveIEWaitVBlankLCDOff_Wait:
    ldh a, [rLY]            ; $3873
    cp $91                  ; $3875
    jr c, SaveIEWaitVBlankLCDOff_Wait ; $3877
    ldh a, [rLCDC]          ; $3879
    and $7f                 ; $387b: LCD off
    ldh [rLCDC], a          ; $387d
    ld a, [wIEShadow]       ; $387f
    ldh [rIE], a            ; $3882: restore IE
    ret                     ; $3884

DelayDE::
    nop                     ; $3885
    nop                     ; $3886
    nop                     ; $3887
    dec de                  ; $3888
    ld a, d                 ; $3889
    or e                    ; $388a
    jr nz, DelayDE          ; $388b
    ret                     ; $388d

; =====================================================================
; $388e-$38b2 -- SendSGBPacket / SendSGBPacketIfSGB.
; A = packet index into bank $1e's table at $4000. The table holds
; 16-bit pointers to the packet bytes. The current bank is saved,
; bank $1e is mapped, the pointer is fetched, the packet is sent by
; SendSGBPacketData, a short delay runs, and the bank is restored.
; SendSGBPacketIfSGB returns immediately when wSGBFlag bit 7 is
; clear (not an SGB); SendSGBPacket sends regardless (used during
; detection, when the flag is not set yet).
; =====================================================================
SECTION "SendSGBPacket", ROM0[$388e]
SendSGBPacket::
    ld b, a                 ; $388e: packet index
    jr SendSGBPacket_Send   ; $388f
SendSGBPacketIfSGB::
    ld b, a                 ; $3891: packet index
    ld a, [wSGBFlag]        ; $3892
    bit 7, a                ; $3895: SGB detected?
    ret z                   ; $3897: no -- do nothing
SendSGBPacket_Send:
    ldh a, [hCurrentBank]   ; $3898: save current bank
    push af                 ; $389a
    ld a, $1e
    rst $10                 ; $389b-$389d: switch to bank $1e
    ld hl, $4000            ; $389e: packet pointer table
    ld a, b                 ; $38a1: packet index
    add a                   ; $38a2: x2 (16-bit entries)
    ld d, $00               ; $38a3
    ld e, a                 ; $38a5
    add hl, de              ; $38a6
    ld a, [hl+]             ; $38a7: low byte of packet address
    ld h, [hl]              ; $38a8: high byte
    ld l, a                 ; $38a9
    call SendSGBPacketData  ; $38aa
    call SGBDelayShort      ; $38ad
    pop af                  ; $38b0: restore bank
    rst $10                 ; $38b1
    ret                     ; $38b2

; $38b3: send the packet at HL if SGB, then a short delay.
SendPacketHLIfSGB::
    ld a, [wSGBFlag]        ; $38b3
    bit 7, a                ; $38b6
    ret z                   ; $38b8
    call SendSGBPacketData  ; $38b9
    jp SGBDelayShort        ; $38bc: tail call

; =====================================================================
; $38bf-$38f3 -- SendSGBPacketData.
; HL points at a packet. Its first byte, AND $07, is the packet
; count (each packet is 16 bytes). For each packet, for each of its
; 16 bytes, for each of its 8 bits (LSB first): write $10 to rP1
; for a 0 bit, $20 for a 1 bit, then $30 (idle). After each packet,
; send a stop bit ($20 then $30) and a short delay. This is the
; standard SGB joypad-port protocol.
; =====================================================================
SECTION "SendSGBPacketData", ROM0[$38bf]
SendSGBPacketData::
    ld a, [hl]              ; $38bf: first byte
    and $07                 ; $38c0: packet count
    ld b, a                 ; $38c2
    ld c, $00               ; $38c3: rP1 ($ff00 + C)
    push bc                 ; $38c5
SendSGBPacketData_Packet:
    xor a                   ; $38c6: $00 to P1
    ldh [c], a              ; $38c7
    ld a, $30               ; $38c8: idle
    ldh [c], a              ; $38ca
    ld b, $10               ; $38cb: 16 bytes per packet
SendSGBPacketData_Byte:
    ld e, $08               ; $38cd: 8 bits per byte
    ld a, [hl+]             ; $38cf
    ld d, a                 ; $38d0
SendSGBPacketData_Bit:
    bit 0, d                ; $38d1
    ld a, $10               ; $38d3: 0 bit
    jr nz, SendSGBPacketData_Bit1 ; $38d5
    ld a, $20               ; $38d7: 1 bit
SendSGBPacketData_Bit1:
    ldh [c], a              ; $38d9
    ld a, $30               ; $38da: idle
    ldh [c], a              ; $38dc
    rr d                    ; $38dd: next bit
    dec e                   ; $38df
    jr nz, SendSGBPacketData_Bit ; $38e0
    dec b                   ; $38e2
    jr nz, SendSGBPacketData_Byte ; $38e3
    ld a, $20               ; $38e5: stop bit
    ldh [c], a              ; $38e7
    ld a, $30               ; $38e8: idle
    ldh [c], a              ; $38ea
    pop bc                  ; $38eb
    dec b                   ; $38ec: packets left?
    ret z                   ; $38ed: done
    push bc                 ; $38ee
    call SGBDelayShort      ; $38ef
    jr SendSGBPacketData_Packet ; $38f2

; =====================================================================
; $38f4-$391a -- ReadJoypadRaw.
; Reads the joypad exactly like ReadJoypad (d-pad, then buttons) but
; stores nothing: the merged value is left in B and the caller
; re-reads rP1 itself. Used by DetectSGB, where the point is the
; SGB's reply on the joypad lines, not the button state.
; =====================================================================
SECTION "ReadJoypadRaw", ROM0[$38f4]
ReadJoypadRaw::
    ld a, $20               ; $38f4: select d-pad
    ldh [rP1], a            ; $38f6
    ldh a, [rP1]            ; $38f8
    ldh a, [rP1]            ; $38fa
    cpl                     ; $38fc
    and $0f                 ; $38fd
    swap a                  ; $38ff
    ld b, a                 ; $3901
    ld a, $30               ; $3902: deselect
    ldh [rP1], a            ; $3904
    ld a, $10               ; $3906: select buttons
    ldh [rP1], a            ; $3908
    ldh a, [rP1]            ; $390a
    ldh a, [rP1]            ; $390c
    ldh a, [rP1]            ; $390e
    ldh a, [rP1]            ; $3910
    ldh a, [rP1]            ; $3912
    ldh a, [rP1]            ; $3914
    ld a, $30               ; $3916: deselect
    ldh [rP1], a            ; $3918
    ret                     ; $391a

; $391b-$392a -- SendSGBPackets68To6F: send packets $68-$6f, one
; after another, gated on SGB. Final step of DetectSGB.
SECTION "SGB packets 68-6F", ROM0[$391b]
SendSGBPackets68To6F::
    ld c, $08               ; $391b: 8 packets
    ld a, $68               ; $391d: first packet index
SendSGBPackets68To6F_Loop:
    push af                 ; $391f
    push bc                 ; $3920
    call SendSGBPacketIfSGB ; $3921
    pop bc                  ; $3924
    pop af                  ; $3925
    inc a                   ; $3926: next packet
    dec c                   ; $3927
    jr nz, SendSGBPackets68To6F_Loop ; $3928
    ret                     ; $392a

    ds $1c, $ff             ; $392b-$3946: $ff padding (verified all $ff)
