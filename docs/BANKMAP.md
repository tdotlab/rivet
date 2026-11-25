file: roms/Donkey_Kong_World_Rev1_SGB.gb  size=524288 (0x80000)
sha1=397ad2ff25627b83e02c71b54c72bb4deb39e0c0
md5 =4859ec2b18c4fabf489eb570c1d7d326
nintendo logo 0x104-0x133 ok: True
entry 0x100: 00 c3 50 01  (jp $0150 if nop+jp)
title 0x134: b'DONKEY KONG\x00\x00\x00\x00\x00'
CGB flag 0x143: 0x00  SGB flag 0x146: 0x03
cart type 0x147: 0x03  ROM size 0x148: 0x04 -> 512 KiB, 32 banks x 16 KiB
RAM size 0x149: 0x02  dest 0x14a: 0x00  old licensee 0x14b: 0x33
version 0x14c: 0x01 (Rev 1)
header checksum 0x14d: stored 0x2d calc 0x2d ok=True
global checksum 0x14e: stored 0x4f8c calc 0x4f8c ok=True
vector 0x40 VBlank : c3 75 02 ff ff ff ff ff
vector 0x48 STAT   : c3 b0 02 ff ff ff ff ff
vector 0x50 Timer  : c3 c7 02 ff ff ff ff ff
vector 0x58 Serial : d9 ff ff ff ff ff ff ff
vector 0x60 Joypad : d9 ff ff ff ff ff ff ff
RST 0x00 @0x0000: c9 ff ff ff ff ff ff ff  RST 0x08: c3 d9 0f ff ff ff ff ff  RST 0x10: e0 8c ea 00 20 c9 ff ff
RST 0x18: c9 ff ff ff ff ff ff ff  RST 0x20: c9 ff ff ff ff ff ff ff  RST 0x28: c9 ff ff ff ff ff ff ff
RST 0x30: c9 ff ff ff ff ff ff ff  RST 0x38: c9 ff ff ff ff ff ff ff
bytes 0x68-0xff (padding?): nonzero=152 first16=ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff

bank map (16 KiB banks, file offset = bank*0x4000):
  bank  0 0x00000-0x03fff nonzero 16056/16384 (98.0%) first16 c9 ff ff ff ff ff ff ff c3 d9 0f ff ff ff ff ff
  bank  1 0x04000-0x07fff nonzero 13686/16384 (83.5%) first16 f0 90 cf 0d 40 6c 40 cf 41 1b 41 42 41 cd c0 1e
  bank  2 0x08000-0x0bfff nonzero 15189/16384 (92.7%) first16 ff ff ff cd a9 45 c3 12 62 ff ff ff ff ff ff ff
  bank  3 0x0c000-0x0ffff nonzero 16029/16384 (97.8%) first16 c3 eb 76 cd a9 45 cd 39 77 c3 1e 48 ff ff ff ff
  bank  4 0x10000-0x13fff nonzero 10724/16384 (65.5%) first16 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  bank  5 0x14000-0x17fff nonzero 15307/16384 (93.4%) first16 00 42 c8 42 a1 43 53 44 d2 44 c1 45 26 47 09 48
  bank  6 0x18000-0x1bfff nonzero 15398/16384 (94.0%) first16 03 0b 16 96 00 00 00 7f ff ff ff 56 56 56 ff 01
  bank  7 0x1c000-0x1ffff nonzero 15686/16384 (95.7%) first16 cd a1 67 f0 91 17 da c9 41 f0 8a e6 30 ca c9 41
  bank  8 0x20000-0x23fff nonzero 15600/16384 (95.2%) first16 21 0a c2 11 08 c2 01 54 dd 1a 86 02 2b 1b 0b 1a
  bank  9 0x24000-0x27fff nonzero 16068/16384 (98.1%) first16 cf 8b 41 f2 41 59 42 92 42 57 46 cb 42 29 1d a4
  bank 10 0x28000-0x2bfff nonzero 15598/16384 (95.2%) first16 fa 02 c1 fe 10 30 32 fe 08 c0 fa 0a c1 21 e7 46
  bank 11 0x2c000-0x2ffff nonzero 12608/16384 (77.0%) first16 a3 43 a7 43 69 42 85 42 a1 42 b4 42 c7 42 ea 42
  bank 12 0x30000-0x33fff nonzero 15654/16384 (95.5%) first16 cd 09 40 21 f7 c7 c3 c2 16 01 f7 c7 7d 02 03 7c
  bank 13 0x34000-0x37fff nonzero 15586/16384 (95.1%) first16 81 81 42 42 24 24 18 18 18 18 24 24 42 42 81 81
  bank 14 0x38000-0x3bfff nonzero 15212/16384 (92.8%) first16 81 81 42 42 24 24 18 18 18 18 24 24 42 42 81 81
  bank 15 0x3c000-0x3ffff nonzero 15600/16384 (95.2%) first16 ad 40 c8 40 c8 40 c8 40 c8 40 c8 40 c8 40 c8 40
  bank 16 0x40000-0x43fff nonzero 15197/16384 (92.8%) first16 c3 44 40 cd d7 43 cd e5 45 cd a8 46 cd c4 48 cd
  bank 17 0x44000-0x47fff nonzero 12649/16384 (77.2%) first16 70 40 70 40 30 45 70 48 30 4d 70 40 70 40 70 40
  bank 18 0x48000-0x4bfff nonzero 15798/16384 (96.4%) first16 02 17 04 c8 00 00 84 98 97 dc 02 3c cd 27 01 0f
  bank 19 0x4c000-0x4ffff nonzero 14382/16384 (87.8%) first16 20 00 30 00 40 00 50 00 60 00 70 00 80 00 90 00
  bank 20 0x50000-0x53fff nonzero 13660/16384 (83.4%) first16 20 00 7f 00 17 01 a4 01 41 02 d6 02 73 03 ff 03
  bank 21 0x54000-0x57fff nonzero 10997/16384 (67.1%) first16 42 00 52 00 62 00 72 00 82 00 92 00 a2 00 b2 00
  bank 22 0x58000-0x5bfff nonzero 12385/16384 (75.6%) first16 40 00 50 00 60 00 70 00 80 00 90 00 a0 00 b0 00
  bank 23 0x5c000-0x5ffff nonzero 15109/16384 (92.2%) first16 36 40 43 40 68 40 87 40 94 40 aa 40 b4 40 be 40
  bank 24 0x60000-0x63fff nonzero 14862/16384 (90.7%) first16 20 00 20 00 20 00 20 00 20 00 20 00 20 00 20 00
  bank 25 0x64000-0x67fff nonzero 15751/16384 (96.1%) first16 d0 09 ef 00 ff 00 ff 03 00 00 1f e0 bc 0a 01 02
  bank 26 0x68000-0x6bfff nonzero 15670/16384 (95.6%) first16 c0 0a 35 ff 01 02 e7 01 02 ff ff 0e 09 12 09 f2
  bank 27 0x6c000-0x6ffff nonzero 14935/16384 (91.2%) first16 e0 07 fd 00 01 02 1c 00 24 18 48 30 ff 4c 30 8a
  bank 28 0x70000-0x73fff nonzero 14104/16384 (86.1%) first16 a0 40 ac 40 b8 40 9e 40 d2 40 d8 40 e8 40 10 41
  bank 29 0x74000-0x77fff nonzero 12556/16384 (76.6%) first16 2a 43 2e 43 69 42 85 42 00 42 00 42 00 42 3c 70
  bank 30 0x78000-0x7bfff nonzero 13914/16384 (84.9%) first16 e0 40 f0 40 00 41 10 41 20 41 30 41 40 41 50 41
  bank 31 0x7c000-0x7ffff nonzero 15865/16384 (96.8%) first16 21 03 c1 cb 66 28 3d cb a6 21 fc c0 3e ff 22 3e

entry region 0x100-0x180 raw:
  0100: 00 c3 50 01 ce ed 66 66 cc 0d 00 0b 03 73 00 83
  0110: 00 0c 00 0d 00 08 11 1f 88 89 00 0e dc cc 6e e6
  0120: dd dd d9 99 bb bb 67 63 6e 0e ec cc dd dc 99 9f
  0130: bb b9 33 3e 44 4f 4e 4b 45 59 20 4b 4f 4e 47 00
  0140: 00 00 00 00 30 31 03 03 04 02 00 33 01 2d 4f 8c
  0150: f3 31 fe ff 3e 01 d7 3e 5d cd 8e 38 cd 26 02 cd
  0160: c1 0f 3e 03 cd 4f 1e cd 37 37 cd 93 01 3e 07 ea
  0170: a3 c0 e0 ff fb cd 22 10 cd ec 01 cd a9 01 21 2f
