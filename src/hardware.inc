; Minimal hardware register equates used by slice 1.
; Addresses are the standard Game Boy IO map (Pan Docs); only registers
; actually referenced by the curated code are listed here.
; The full gbdev hardware.inc is NOT copied in; add registers as slices need them.

DEF rP1 EQU $ff00 ; joypad
DEF rSTAT EQU $ff41 ; LCD status
DEF rSCY EQU $ff42 ; scroll Y
DEF rSCX EQU $ff43 ; scroll X
DEF rLY EQU $ff44 ; LCD Y coordinate
DEF rDMA EQU $ff46 ; OAM DMA start
DEF rBGP EQU $ff47 ; background palette
DEF rOBP0 EQU $ff48 ; object palette 0
DEF rOBP1 EQU $ff49 ; object palette 1
DEF rTIMA EQU $ff05 ; timer counter
DEF rTMA EQU $ff06 ; timer modulo
DEF rTAC EQU $ff07 ; timer control
DEF rLCDC EQU $ff40 ; LCD control
DEF rIE EQU $ffff ; interrupt enable
