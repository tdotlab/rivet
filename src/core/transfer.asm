; Donkey Kong '94 -- slice 2: data-transfer routines, palette table, SRAM save.
; $1d2f SeedMul: seed at $defe/$deff advanced by *15625-1 (mod 65536), returns
;   A * new-seed in HL. The *15625 (5^6) LCG shape reads like the game's RNG
;   step (INFERRED -- the arithmetic is verified, the RNG role is not); it has
;   89 call sites, almost all in banked gameplay code (banks 1,7-10,12,16,31).
; $1d82 TransferTable0F: bank $0f table at $4000, A*2 -> pointer -> count,
;   each entry calls $16c2 (a copy routine). $1da7 TransferTable1E: bank $1e
;   table at $74e5, A = index; entries are 7 bytes:
;   [bank][src lo][src hi][dst lo][dst hi][len lo][len hi+flags] -- bit 7 of
;   the last byte selects the $257f decompressor (len = BC), else MemcpyBC.
; $1df8/$1dfd: build 12-byte sprite-table entries at $c200 + A*12 from the
;   bank $1b table at $7918. $1e3e/$1e46: window position (show / hide).
; Palette table $1e86: 17 entries (indices 0-16 -- 16 is the largest index
;   loaded directly by any `call LoadPalette` in the ROM).

SECTION "Transfer routines", ROM0[$1d2f]
SeedMul::
    ld h, $00                                        ; $1d2f
    ld l, a                                          ; $1d31
    push bc                                          ; $1d32
    push de                                          ; $1d33
    ld d, h                                          ; $1d34
    ld e, l                                          ; $1d35
    ld a, [$defe]                                    ; $1d36
    ld c, a                                          ; $1d39
    ld l, a                                          ; $1d3a
    ld a, [$deff]                                    ; $1d3b
    ld b, a                                          ; $1d3e
    ld h, a                                          ; $1d3f
    add hl, hl                                       ; $1d40
    add hl, bc                                       ; $1d41
    add hl, hl                                       ; $1d42
    add hl, bc                                       ; $1d43
    add hl, hl                                       ; $1d44
    add hl, bc                                       ; $1d45
    add hl, hl                                       ; $1d46
    add hl, hl                                       ; $1d47
    add hl, bc                                       ; $1d48
    add hl, hl                                       ; $1d49
    add hl, hl                                       ; $1d4a
    add hl, hl                                       ; $1d4b
    add hl, hl                                       ; $1d4c
    add hl, hl                                       ; $1d4d
    add hl, bc                                       ; $1d4e
    add hl, hl                                       ; $1d4f
    add hl, hl                                       ; $1d50
    add hl, hl                                       ; $1d51
    add hl, bc                                       ; $1d52
    ld a, l                                          ; $1d53
    sub $01                                          ; $1d54
    ld l, a                                          ; $1d56
    ld a, h                                          ; $1d57
    sbc $00                                          ; $1d58
    ld h, a                                          ; $1d5a
    ld a, l                                          ; $1d5b
    ld [$defe], a                                    ; $1d5c
    ld a, h                                          ; $1d5f
    ld [$deff], a                                    ; $1d60
    ld b, h                                          ; $1d63
    ld c, l                                          ; $1d64
    ld hl, $0000                                     ; $1d65
    ld a, $10                                        ; $1d68
L_1d6a::
    push af                                          ; $1d6a
    add hl, hl                                       ; $1d6b
    ld a, e                                          ; $1d6c
    adc a                                            ; $1d6d
    ld e, a                                          ; $1d6e
    ld a, d                                          ; $1d6f
    adc a                                            ; $1d70
    ld d, a                                          ; $1d71
    jr nc, L_1d78                                    ; $1d72
    add hl, bc                                       ; $1d74
    jr nc, L_1d78                                    ; $1d75
    inc de                                           ; $1d77
L_1d78::
    pop af                                           ; $1d78
    dec a                                            ; $1d79
    jr nz, L_1d6a                                    ; $1d7a
    ld h, d                                          ; $1d7c
    ld l, e                                          ; $1d7d
    ld a, e                                          ; $1d7e
    pop de                                           ; $1d7f
    pop bc                                           ; $1d80
    ret                                              ; $1d81
TransferTable0F::
    ld hl, $4000                                     ; $1d82
    ld d, $00                                        ; $1d85
    add a                                            ; $1d87
    ld e, a                                          ; $1d88
    add hl, de                                       ; $1d89
    ldh a, [$ff8c]                                   ; $1d8a
    push af                                          ; $1d8c
    ld a, $0f                                        ; $1d8d
    rst $10                                          ; $1d8f
    ld a, [hl+]                                      ; $1d90
    ld h, [hl]                                       ; $1d91
    ld l, a                                          ; $1d92
    ld a, [hl+]                                      ; $1d93
    ld c, a                                          ; $1d94
L_1d95::
    push hl                                          ; $1d95
    ld a, [hl+]                                      ; $1d96
    ld h, [hl]                                       ; $1d97
    ld l, a                                          ; $1d98
    push bc                                          ; $1d99
    call $16c2                                       ; $1d9a
    pop bc                                           ; $1d9d
    pop hl                                           ; $1d9e
    inc hl                                           ; $1d9f
    inc hl                                           ; $1da0
    dec c                                            ; $1da1
    jr nz, L_1d95                                    ; $1da2
    pop af                                           ; $1da4
    rst $10                                          ; $1da5
    ret                                              ; $1da6
TransferTable1E::
    ld b, a                                          ; $1da7
    ldh a, [$ff8c]                                   ; $1da8
    push af                                          ; $1daa
    ld a, $1e                                        ; $1dab
    rst $10                                          ; $1dad
    ld h, $00                                        ; $1dae
    ld l, b                                          ; $1db0
    add hl, hl                                       ; $1db1
    ld de, $74e5                                     ; $1db2
    add hl, de                                       ; $1db5
    ld a, [hl+]                                      ; $1db6
    ld h, [hl]                                       ; $1db7
    ld l, a                                          ; $1db8
    ld a, [hl+]                                      ; $1db9
    ld c, a                                          ; $1dba
L_1dbb::
    push bc                                          ; $1dbb
    ld a, $1e                                        ; $1dbc
    rst $10                                          ; $1dbe
    push hl                                          ; $1dbf
    ld a, [hl+]                                      ; $1dc0
    ld b, a                                          ; $1dc1
    ld a, [hl+]                                      ; $1dc2
    ld e, a                                          ; $1dc3
    ld a, [hl+]                                      ; $1dc4
    ld d, a                                          ; $1dc5
    push de                                          ; $1dc6
    ld a, [hl+]                                      ; $1dc7
    ld e, a                                          ; $1dc8
    ld a, [hl+]                                      ; $1dc9
    ld d, a                                          ; $1dca
    ld a, [hl+]                                      ; $1dcb
    ld c, a                                          ; $1dcc
    ld a, [hl+]                                      ; $1dcd
    push af                                          ; $1dce
    ld a, b                                          ; $1dcf
    rst $10                                          ; $1dd0
    pop af                                           ; $1dd1
    ld b, a                                          ; $1dd2
    pop hl                                           ; $1dd3
    bit 7, b                                         ; $1dd4
    jr z, L_1de9                                     ; $1dd6
    ld a, b                                          ; $1dd8
    and $7f                                          ; $1dd9
    ld b, a                                          ; $1ddb
    or c                                             ; $1ddc
    jr z, L_1de4                                     ; $1ddd
    call Decompress                                       ; $1ddf
    jr L_1dec                                        ; $1de2
L_1de4::
    call DecompressPrefixed                                       ; $1de4
    jr L_1dec                                        ; $1de7
L_1de9::
    call $1065                                       ; $1de9
L_1dec::
    pop hl                                           ; $1dec
    ld de, $0007                                     ; $1ded
    add hl, de                                       ; $1df0
    pop bc                                           ; $1df1
    dec c                                            ; $1df2
    jr nz, L_1dbb                                    ; $1df3
    pop af                                           ; $1df5
    rst $10                                          ; $1df6
    ret                                              ; $1df7
LoadSpriteTable::
    push af                                          ; $1df8
    call $10c2                                       ; $1df9
    pop af                                           ; $1dfc
BuildSpriteEntries::
    ld hl, $7918                                     ; $1dfd
    ld d, $00                                        ; $1e00
    add a                                            ; $1e02
    ld e, a                                          ; $1e03
    add hl, de                                       ; $1e04
    ldh a, [$ff8c]                                   ; $1e05
    push af                                          ; $1e07
    ld a, $1b                                        ; $1e08
    rst $10                                          ; $1e0a
    ld a, [hl+]                                      ; $1e0b
    ld h, [hl]                                       ; $1e0c
    ld l, a                                          ; $1e0d
    ld a, [hl+]                                      ; $1e0e
    ld c, a                                          ; $1e0f
L_1e10::
    ld a, [hl+]                                      ; $1e10
    push hl                                          ; $1e11
    ld h, $00                                        ; $1e12
    add a                                            ; $1e14
    add a                                            ; $1e15
    add a                                            ; $1e16
    ld l, a                                          ; $1e17
    add hl, hl                                       ; $1e18
    add hl, hl                                       ; $1e19
    ld de, $c200                                     ; $1e1a
    add hl, de                                       ; $1e1d
    pop de                                           ; $1e1e
    ld a, [de]                                       ; $1e1f
    inc de                                           ; $1e20
    ld [hl+], a                                      ; $1e21
    ld a, [de]                                       ; $1e22
    inc de                                           ; $1e23
    ld [hl+], a                                      ; $1e24
    ld a, [de]                                       ; $1e25
    inc de                                           ; $1e26
    ld [hl+], a                                      ; $1e27
    ld a, [de]                                       ; $1e28
    inc de                                           ; $1e29
    ld [hl+], a                                      ; $1e2a
    xor a                                            ; $1e2b
    ld [hl+], a                                      ; $1e2c
    ld [hl+], a                                      ; $1e2d
    ld [hl+], a                                      ; $1e2e
    ld a, [de]                                       ; $1e2f
    inc de                                           ; $1e30
    ld [hl+], a                                      ; $1e31
    xor a                                            ; $1e32
    ld [hl+], a                                      ; $1e33
    ld [hl+], a                                      ; $1e34
    ld [hl], a                                       ; $1e35
    ld l, e                                          ; $1e36
    ld h, d                                          ; $1e37
    dec c                                            ; $1e38
    jr nz, L_1e10                                    ; $1e39
    pop af                                           ; $1e3b
    rst $10                                          ; $1e3c
    ret                                              ; $1e3d
ResetWindowPos::
    xor a                                            ; $1e3e
    ldh [rWY], a                                     ; $1e3f
    ld a, $07                                        ; $1e41
    ldh [rWX], a                                     ; $1e43
    ret                                              ; $1e45

; $1e46-$1e4e -- move the window off-screen (WY=$90, WX=$a6), then return.
SECTION "HideWindow", ROM0[$1e46]
HideWindow::
    ld a, $90                                        ; $1e46
    ldh [rWY], a                                     ; $1e48
    ld a, $a6                                        ; $1e4a
    ldh [rWX], a                                     ; $1e4c
    ret                                              ; $1e4e

; $1e86-$1eb8 -- palette table: 17 entries x 3 bytes (BGP, OBP0, OBP1).
SECTION "Palette table", ROM0[$1e86]
PaletteTable::
    db $9c, $1e, $9c  ; palette 0 (BGP, OBP0, OBP1)
    db $9c, $1e, $9c  ; palette 1 (BGP, OBP0, OBP1)
    db $63, $e1, $63  ; palette 2 (BGP, OBP0, OBP1)
    db $ff, $ff, $ff  ; palette 3 (BGP, OBP0, OBP1)
    db $9c, $36, $9c  ; palette 4 (BGP, OBP0, OBP1)
    db $e4, $1e, $9c  ; palette 5 (BGP, OBP0, OBP1)
    db $00, $00, $00  ; palette 6 (BGP, OBP0, OBP1)
    db $e4, $e4, $e4  ; palette 7 (BGP, OBP0, OBP1)
    db $e4, $ff, $ff  ; palette 8 (BGP, OBP0, OBP1)
    db $9c, $1e, $e4  ; palette 9 (BGP, OBP0, OBP1)
    db $e4, $e4, $e4  ; palette 10 (BGP, OBP0, OBP1)
    db $cc, $cc, $cc  ; palette 11 (BGP, OBP0, OBP1)
    db $93, $e4, $e0  ; palette 12 (BGP, OBP0, OBP1)
    db $9c, $cc, $cc  ; palette 13 (BGP, OBP0, OBP1)
    db $8c, $cc, $cc  ; palette 14 (BGP, OBP0, OBP1)
    db $6c, $1e, $9c  ; palette 15 (BGP, OBP0, OBP1)
    db $e4, $e4, $e4  ; palette 16 (BGP, OBP0, OBP1)

; $1eb9-$1ebd -- 5 unidentified bytes after the palette table. Kept literal.
SECTION "Unknown 1eb9", ROM0[$1eb9]
    db $00, $00, $e4, $ff, $ff  ; $1eb9-$1ebd

; $1ebe-$1f99 -- SRAM save handling. $1ebe is `dec de; ret` (called from
; $1fbe); $1ebf is just `ret` (called from $1ed6 -- a do-nothing call, kept
; literal). $1ec0/$1ec9 enable/disable SRAM via the MBC RAM-enable register
; at $0000 ($0a = enable, $00 = disable). $1ed2 ValidateSave checks the save
; in SRAM ($bffa nibbles vs ROM $2017, $bfd8 == 2,7, $bfc0 via $1f72, $a000
; checksum via $1f8a, $be2a nibbles); $1f9a+ (save-clear/write) is not
; curated yet and stays raw.
SECTION "Save routines", ROM0[$1ebe]
DecDE::
    dec de                                           ; $1ebe
L_1ebf::
    ret                                              ; $1ebf
EnableSRAM::
    ld a, $0a                                        ; $1ec0
    ld [$c86a], a                                    ; $1ec2
    ld [$0000], a                                    ; $1ec5
    ret                                              ; $1ec8
DisableSRAM::
    ld a, $00                                        ; $1ec9
    ld [$c86a], a                                    ; $1ecb
    ld [$0000], a                                    ; $1ece
    ret                                              ; $1ed1
ValidateSave::
    call EnableSRAM                                  ; $1ed2
    xor a                                            ; $1ed5
    call L_1ebf                                      ; $1ed6
    ld hl, $2017                                     ; $1ed9
    ld de, $bffa                                     ; $1edc
    ld c, $06                                        ; $1edf
L_1ee1::
    ld a, [de]                                       ; $1ee1
    and $0f                                          ; $1ee2
    cp [hl]                                          ; $1ee4
    jr nz, L_1f1e                                    ; $1ee5
    inc de                                           ; $1ee7
    inc hl                                           ; $1ee8
    dec c                                            ; $1ee9
    jr nz, L_1ee1                                    ; $1eea
    ld hl, $bfd8                                     ; $1eec
    ld a, [hl+]                                      ; $1eef
    and $0f                                          ; $1ef0
    cp $02                                           ; $1ef2
    jr nz, L_1f1e                                    ; $1ef4
    ld a, [hl]                                       ; $1ef6
    and $0f                                          ; $1ef7
    cp $07                                           ; $1ef9
    jr nz, L_1f1e                                    ; $1efb
    ld hl, $bfc0                                     ; $1efd
    call SaveCmpLoop                                 ; $1f00
    jr nz, L_1f1e                                    ; $1f03
    ld hl, $a000                                     ; $1f05
    call SaveChecksum                                ; $1f08
    ld hl, $be2a                                     ; $1f0b
    ld a, [hl+]                                      ; $1f0e
    and $0f                                          ; $1f0f
    ld d, a                                          ; $1f11
    ld a, [hl]                                       ; $1f12
    and $0f                                          ; $1f13
    swap a                                           ; $1f15
    or d                                             ; $1f17
    cp e                                             ; $1f18
    jr nz, L_1f1e                                    ; $1f19
    jp DisableSRAM                                   ; $1f1b
L_1f1e::
    ld hl, $bff6                                     ; $1f1e
    ld a, [hl+]                                      ; $1f21
    and $0f                                          ; $1f22
    cp $02                                           ; $1f24
    jr nz, L_1f70                                    ; $1f26
    ld a, [hl]                                       ; $1f28
    and $0f                                          ; $1f29
    cp $07                                           ; $1f2b
    jr nz, L_1f70                                    ; $1f2d
    ld hl, $bfde                                     ; $1f2f
    call SaveCmpLoop                                 ; $1f32
    jr nz, L_1f70                                    ; $1f35
    ld hl, $be2c                                     ; $1f37
    call SaveChecksum                                ; $1f3a
    ld a, [hl+]                                      ; $1f3d
    and $0f                                          ; $1f3e
    ld d, a                                          ; $1f40
    ld a, [hl]                                       ; $1f41
    and $0f                                          ; $1f42
    swap a                                           ; $1f44
    or d                                             ; $1f46
    cp e                                             ; $1f47
    jr nz, L_1f70                                    ; $1f48
    ld hl, $bfbe                                     ; $1f4a
    xor a                                            ; $1f4d
    ld [hl+], a                                      ; $1f4e
    ld hl, $bfdd                                     ; $1f4f
    ld de, $bfbf                                     ; $1f52
    ld c, $1d                                        ; $1f55
    call $106e                                       ; $1f57
    ld hl, $be2c                                     ; $1f5a
    ld de, $a000                                     ; $1f5d
    ld bc, $0190                                     ; $1f60
    call $1065                                       ; $1f63
    ld de, $be2a                                     ; $1f66
    ld c, $02                                        ; $1f69
    call $106e                                       ; $1f6b
    jr $1fe4                                         ; $1f6e
L_1f70::
    jr $1f9a                                         ; $1f70
SaveCmpLoop::
    ld bc, $001a                                     ; $1f72
L_1f75::
    ld a, [hl+]                                      ; $1f75
    and $0f                                          ; $1f76
    add b                                            ; $1f78
    ld b, a                                          ; $1f79
    dec c                                            ; $1f7a
    jr nz, L_1f75                                    ; $1f7b
    ld e, b                                          ; $1f7d
    ld a, [hl+]                                      ; $1f7e
    and $0f                                          ; $1f7f
    ld b, a                                          ; $1f81
    ld a, [hl]                                       ; $1f82
    and $0f                                          ; $1f83
    swap a                                           ; $1f85
    or b                                             ; $1f87
    cp e                                             ; $1f88
    ret                                              ; $1f89
SaveChecksum::
    ld bc, $0190                                     ; $1f8a
    ld e, $00                                        ; $1f8d
L_1f8f::
    ld a, [hl+]                                      ; $1f8f
    and $0f                                          ; $1f90
    add e                                            ; $1f92
    ld e, a                                          ; $1f93
    dec bc                                           ; $1f94
    ld a, c                                          ; $1f95
    or b                                             ; $1f96
    jr nz, L_1f8f                                    ; $1f97
    ret                                              ; $1f99
