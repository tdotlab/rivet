; Donkey Kong '94 -- slice 2: per-frame routines ($1643-$17ea).
; FrameCopy16f9 ($16f9) is the VBlank per-frame update: HL = wStatePtrLo
; ($da5f), DE = [HL] (a destination pointer), then an unrolled block copies
; bytes [HL] -> [DE]. Frame1663 ($1663) runs from VBlankHandler when the LCD
; is not in mode 2. The rest are transcribed from mgbdis and byte-verified;
; their exact roles are TODO for a later slice.

SECTION "Per-frame routines", ROM0[$1643]
Frame1643::
    ld hl, $c72e                                     ; $1643
    ld c, $c3                                        ; $1646
    xor a                                            ; $1648
    jp MemsetC                                       ; $1649
    ld hl, $c72f                                     ; $164c
    ld a, $01                                        ; $164f
    ld [hl-], a                                      ; $1651
    ld a, [hl]                                       ; $1652
    ld c, a                                          ; $1653
    inc a                                            ; $1654
    and $1f                                          ; $1655
    ld [hl+], a                                      ; $1657
    ld a, c                                          ; $1658
    add a                                            ; $1659
    ld b, $00                                        ; $165a
    ld c, a                                          ; $165c
    add hl, bc                                       ; $165d
    add hl, bc                                       ; $165e
    add hl, bc                                       ; $165f
    inc hl                                           ; $1660
    inc hl                                           ; $1661
    ret                                              ; $1662
Frame1663::
    ldh a, [rSTAT]                                   ; $1663
    bit 1, a                                         ; $1665
    ret nz                                           ; $1667
    ld hl, $c72f                                     ; $1668
    ld a, [hl+]                                      ; $166b
    or a                                             ; $166c
    ret nz                                           ; $166d
    ld a, [hl+]                                      ; $166e
    add a                                            ; $166f
    ld d, $00                                        ; $1670
    ld e, a                                          ; $1672
    add hl, de                                       ; $1673
    add hl, de                                       ; $1674
    add hl, de                                       ; $1675
    inc hl                                           ; $1676
    ld d, h                                          ; $1677
    ld e, l                                          ; $1678
    ld a, [hl-]                                      ; $1679
    or a                                             ; $167a
    ret z                                            ; $167b
    inc de                                           ; $167c
    ld a, [de]                                       ; $167d
    or a                                             ; $167e
    jr z, FrameRetStub                               ; $167f
    inc de                                           ; $1681
    ld a, [de]                                       ; $1682
    or a                                             ; $1683
    jr z, FrameRetStub                               ; $1684
    push hl                                          ; $1686
    call FrameCopy16c2                               ; $1687
    ld hl, $c730                                     ; $168a
    ld a, [hl]                                       ; $168d
    inc a                                            ; $168e
    and $1f                                          ; $168f
    ld [hl], a                                       ; $1691
    pop hl                                           ; $1692
    xor a                                            ; $1693
    ld [hl+], a                                      ; $1694
    ld [hl+], a                                      ; $1695
    ld [hl+], a                                      ; $1696
    ld [hl+], a                                      ; $1697
    ld [hl+], a                                      ; $1698
    ld [hl], a                                       ; $1699
    ret                                              ; $169a
FrameRetStub::
    ret                                              ; $169b
    ld hl, $c72f                                     ; $169c
    ld a, $01                                        ; $169f
    ld [hl-], a                                      ; $16a1
    ld a, [hl]                                       ; $16a2
    ld c, a                                          ; $16a3
    inc a                                            ; $16a4
    and $1f                                          ; $16a5
    ld [hl+], a                                      ; $16a7
    ld a, c                                          ; $16a8
    add a                                            ; $16a9
    ld b, $00                                        ; $16aa
    ld c, a                                          ; $16ac
    add hl, bc                                       ; $16ad
    add hl, bc                                       ; $16ae
    add hl, bc                                       ; $16af
    ld bc, $0007                                     ; $16b0
    add hl, bc                                       ; $16b3
    inc de                                           ; $16b4
    inc de                                           ; $16b5
    inc de                                           ; $16b6
    inc de                                           ; $16b7
    inc de                                           ; $16b8
    ld b, $06                                        ; $16b9
L_16bb::
    ld a, [de]                                       ; $16bb
    dec de                                           ; $16bc
    ld [hl-], a                                      ; $16bd
    dec b                                            ; $16be
    jr nz, L_16bb                                    ; $16bf
    ret                                              ; $16c1
FrameCopy16c2::
    ld a, [hl+]                                      ; $16c2
    ld e, a                                          ; $16c3
    ld a, [hl+]                                      ; $16c4
    ld d, a                                          ; $16c5
    push de                                          ; $16c6
    ld a, [hl+]                                      ; $16c7
    ld b, a                                          ; $16c8
    ld a, [hl+]                                      ; $16c9
    ld c, a                                          ; $16ca
    ld a, [hl+]                                      ; $16cb
    ld e, a                                          ; $16cc
    ld a, [hl]                                       ; $16cd
    ld d, a                                          ; $16ce
    pop hl                                           ; $16cf
    ld a, d                                          ; $16d0
    or a                                             ; $16d1
    jr z, L_16e7                                     ; $16d2
L_16d4::
    push bc                                          ; $16d4
    push hl                                          ; $16d5
L_16d6::
    ld a, [de]                                       ; $16d6
    inc de                                           ; $16d7
    ld [hl+], a                                      ; $16d8
    dec c                                            ; $16d9
    jr nz, L_16d6                                    ; $16da
    pop hl                                           ; $16dc
    ld b, $00                                        ; $16dd
    ld c, $20                                        ; $16df
    add hl, bc                                       ; $16e1
    pop bc                                           ; $16e2
    dec b                                            ; $16e3
    jr nz, L_16d4                                    ; $16e4
    ret                                              ; $16e6
L_16e7::
    ld a, e                                          ; $16e7
L_16e8::
    push bc                                          ; $16e8
    push hl                                          ; $16e9
L_16ea::
    ld [hl+], a                                      ; $16ea
    inc a                                            ; $16eb
    dec c                                            ; $16ec
    jr nz, L_16ea                                    ; $16ed
    pop hl                                           ; $16ef
    ld bc, $0020                                     ; $16f0
    add hl, bc                                       ; $16f3
    pop bc                                           ; $16f4
    dec b                                            ; $16f5
    jr nz, L_16e8                                    ; $16f6
    ret                                              ; $16f8
FrameCopy16f9::
    ld hl, $da5f                                     ; $16f9
    ld a, [hl+]                                      ; $16fc
    ld e, a                                          ; $16fd
    ld a, [hl+]                                      ; $16fe
    ld d, a                                          ; $16ff
    ld a, [hl+]                                      ; $1700
    ld [de], a                                       ; $1701
    inc de                                           ; $1702
    ld a, [hl+]                                      ; $1703
    ld [de], a                                       ; $1704
    inc de                                           ; $1705
    ld a, [hl+]                                      ; $1706
    ld [de], a                                       ; $1707
    inc de                                           ; $1708
    ld a, [hl+]                                      ; $1709
    ld [de], a                                       ; $170a
    inc de                                           ; $170b
    ld a, [hl+]                                      ; $170c
    ld [de], a                                       ; $170d
    inc de                                           ; $170e
    ld a, [hl+]                                      ; $170f
    ld [de], a                                       ; $1710
    inc de                                           ; $1711
    ld a, [hl+]                                      ; $1712
    ld [de], a                                       ; $1713
    inc de                                           ; $1714
    ld a, [hl+]                                      ; $1715
    ld [de], a                                       ; $1716
    inc de                                           ; $1717
    ld a, [hl+]                                      ; $1718
    ld [de], a                                       ; $1719
    inc de                                           ; $171a
    ld a, [hl+]                                      ; $171b
    ld [de], a                                       ; $171c
    inc de                                           ; $171d
    ld a, [hl+]                                      ; $171e
    ld [de], a                                       ; $171f
    inc de                                           ; $1720
    ld a, [hl+]                                      ; $1721
    ld [de], a                                       ; $1722
    inc de                                           ; $1723
    ld a, [hl+]                                      ; $1724
    ld [de], a                                       ; $1725
    inc de                                           ; $1726
    ld a, [hl+]                                      ; $1727
    ld [de], a                                       ; $1728
    inc de                                           ; $1729
    ld a, [hl+]                                      ; $172a
    ld [de], a                                       ; $172b
    inc de                                           ; $172c
    ld a, [hl+]                                      ; $172d
    ld [de], a                                       ; $172e
    ld a, $04                                        ; $172f
    ld [$2000], a                                    ; $1731
    ld a, [hl+]                                      ; $1734
    ld e, a                                          ; $1735
    ld a, [hl+]                                      ; $1736
    ld d, a                                          ; $1737
    ld a, [hl+]                                      ; $1738
    ld h, [hl]                                       ; $1739
    ld l, a                                          ; $173a
    ld a, [hl+]                                      ; $173b
    ld [de], a                                       ; $173c
    inc de                                           ; $173d
    ld a, [hl+]                                      ; $173e
    ld [de], a                                       ; $173f
    inc de                                           ; $1740
    ld a, [hl+]                                      ; $1741
    ld [de], a                                       ; $1742
    inc de                                           ; $1743
    ld a, [hl+]                                      ; $1744
    ld [de], a                                       ; $1745
    inc de                                           ; $1746
    ld a, [hl+]                                      ; $1747
    ld [de], a                                       ; $1748
    inc de                                           ; $1749
    ld a, [hl+]                                      ; $174a
    ld [de], a                                       ; $174b
    inc de                                           ; $174c
    ld a, [hl+]                                      ; $174d
    ld [de], a                                       ; $174e
    inc de                                           ; $174f
    ld a, [hl+]                                      ; $1750
    ld [de], a                                       ; $1751
    inc de                                           ; $1752
    ld a, [hl+]                                      ; $1753
    ld [de], a                                       ; $1754
    inc de                                           ; $1755
    ld a, [hl+]                                      ; $1756
    ld [de], a                                       ; $1757
    inc de                                           ; $1758
    ld a, [hl+]                                      ; $1759
    ld [de], a                                       ; $175a
    inc de                                           ; $175b
    ld a, [hl+]                                      ; $175c
    ld [de], a                                       ; $175d
    inc de                                           ; $175e
    ld a, [hl+]                                      ; $175f
    ld [de], a                                       ; $1760
    inc de                                           ; $1761
    ld a, [hl+]                                      ; $1762
    ld [de], a                                       ; $1763
    inc de                                           ; $1764
    ld a, [hl+]                                      ; $1765
    ld [de], a                                       ; $1766
    inc de                                           ; $1767
    ld a, [hl]                                       ; $1768
    ld [de], a                                       ; $1769
    ret                                              ; $176a
    ld hl, $ddb4                                     ; $176b
    ld a, [hl]                                       ; $176e
    inc [hl]                                         ; $176f
    cp $04                                           ; $1770
    jr c, L_1791                                     ; $1772
    cp $30                                           ; $1774
    jr c, L_17bd                                     ; $1776
    ld hl, $da71                                     ; $1778
    ld a, $00                                        ; $177b
    ld [hl+], a                                      ; $177d
    ld a, $83                                        ; $177e
    ld [hl+], a                                      ; $1780
    ld a, $00                                        ; $1781
    ld [hl+], a                                      ; $1783
    ld [hl], $83                                     ; $1784
    xor a                                            ; $1786
    ld [$ddb4], a                                    ; $1787
    dec a                                            ; $178a
    ld [$ddb3], a                                    ; $178b
    jp IncStateTimer                                 ; $178e
L_1791::
    add a                                            ; $1791
    ld h, $00                                        ; $1792
    ld l, a                                          ; $1794
    add hl, hl                                       ; $1795
    add hl, hl                                       ; $1796
    add hl, hl                                       ; $1797
    push hl                                          ; $1798
    ld de, $82c0                                     ; $1799
    add hl, de                                       ; $179c
    ld a, l                                          ; $179d
    ld [$da71], a                                    ; $179e
    ld a, h                                          ; $17a1
    ld [$da72], a                                    ; $17a2
    pop hl                                           ; $17a5
    ld de, $46f0                                     ; $17a6
    ld a, [$dd17]                                    ; $17a9
    bit 7, a                                         ; $17ac
    jr nz, L_17b3                                    ; $17ae
    ld de, $67b0                                     ; $17b0
L_17b3::
    add hl, de                                       ; $17b3
    ld a, l                                          ; $17b4
    ld [$da73], a                                    ; $17b5
    ld a, h                                          ; $17b8
    ld [$da74], a                                    ; $17b9
    ret                                              ; $17bc
L_17bd::
    sub $04                                          ; $17bd
    add a                                            ; $17bf
    ld h, $00                                        ; $17c0
    ld l, a                                          ; $17c2
    add hl, hl                                       ; $17c3
    add hl, hl                                       ; $17c4
    add hl, hl                                       ; $17c5
    push hl                                          ; $17c6
    ld de, $8000                                     ; $17c7
    add hl, de                                       ; $17ca
    ld a, l                                          ; $17cb
    ld [$da71], a                                    ; $17cc
    ld a, h                                          ; $17cf
    ld [$da72], a                                    ; $17d0
    pop hl                                           ; $17d3
    ld de, $46f0                                     ; $17d4
    ld a, [$dd17]                                    ; $17d7
    bit 7, a                                         ; $17da
    jr z, L_17e1                                     ; $17dc
    ld de, $67b0                                     ; $17de
L_17e1::
    add hl, de                                       ; $17e1
    ld a, l                                          ; $17e2
    ld [$da73], a                                    ; $17e3
    ld a, h                                          ; $17e6
    ld [$da74], a                                    ; $17e7
    ret                                              ; $17ea
