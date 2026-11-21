; Addresses of RAM variables referenced by slice 1.
; These are EQUates, not allocations: the game itself owns the layout.
; Sizes and neighbours are TODO until the surrounding WRAM is mapped.
; Names are ours, chosen from how the code uses each byte; a name followed
; by "?" means the role is inferred, not yet proven by a second use site.

; --- HRAM ($ff80-$fffe) ---
DEF hDMARoutine EQU $ff80 ; 10 bytes: OAM DMA routine, copied here by CopyDMARoutine
DEF hJoypad EQU $ff8a ; current buttons, 1 = pressed (high nibble d-pad, low A/B/Select/Start)
DEF hJoypadNew EQU $ff8b ; buttons newly pressed this frame
DEF hCurrentBank EQU $ff8c ; ROM bank currently mapped at $4000-$7fff (mirror of $2000 write)
DEF hGameState EQU $ff8e ; main state-machine index (dispatched by DispatchState)
DEF hSTATState EQU $ff8f ; STAT-handler dispatch index (dispatched by STATHandler)
DEF hStateTimer EQU $ff90 ; per-state frame counter, cleared on state change
DEF hFrameCount EQU $ff95 ; increments once per main-loop iteration

; --- WRAM ($c000-$dfff) ---
DEF wVBlankFlag EQU $c0a0 ; bit 0 set by VBlankHandler, cleared by MainLoop after halt
DEF wLCDCShadow EQU $c0a2 ; LCDC value restored by RestoreInterruptsAndLCDC
DEF wIEShadow EQU $c0a3 ; IE value saved/restored around LCD-off sequences
DEF wSGBFlag EQU $c82b ; bit 7 set = Super Game Boy detected; low bits also used elsewhere (TODO)
DEF wOAMDMATrigger EQU $c701 ; if non-zero, VBlankHandler runs the HRAM DMA routine (name inferred)
DEF wDecompOutLen EQU $c809 ; 2 bytes: decompressor output length (lo/hi), saved by Decompress
DEF wDecompDst EQU $c80b ; 2 bytes: decompressor destination pointer (lo/hi), saved by Decompress
DEF wScrollShadow EQU $c707 ; SCY/SCX shadow pair written by VBlankHandler
DEF wUnknownC711 EQU $c711 ; TODO: role unknown, read by state $15 setup
DEF wUnknownC72F EQU $c72f ; bit 0 cleared by MainLoop each frame; set elsewhere (TODO)
DEF wUnknownC851 EQU $c851 ; set to 1 by ClearRAMAndInit (TODO)
DEF wUnknownC859 EQU $c859 ; two bytes written by ClearRAMAndInit (TODO)
DEF wPaletteShadow EQU $da3d ; 3 bytes: BGP/OBP0/OBP1 shadows written by LoadPalette
DEF wSGBMode EQU $da40 ; $9c = SGB detected, $cc = not SGB (set by DetectSGB)
DEF wUnknownDA43 EQU $da43 ; set to 4 by ClearRAMAndInit (TODO)
DEF wStatePtrLo EQU $da5f ; 2-byte pointer, set by InitStatePtrs (TODO: target)
DEF wStatePtr EQU $da61 ; 2-byte pointer, set by InitStatePtrs (TODO: target)
DEF wStatePtr2 EQU $da71 ; 2-byte pointer, set by InitStatePtrs (TODO: target)
DEF wUnknownC82B EQU $c82b ; alias, see wSGBFlag
DEF wClearTarget EQU $c000 ; start of the WRAM region cleared by ClearRAMAndInit
DEF wClearTarget2 EQU $df00 ; start of the second region cleared by ClearRAMAndInit
