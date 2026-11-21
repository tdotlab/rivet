#!/usr/bin/env python3
"""Craft a DK94 SRAM save with a chosen progress level (slice 6).

Reads a known-good save (slice-4 f1 save), patches the file-0 slot's
progress byte in BOTH copies (primary $bfbe.. and backup $bfdc..) and
fixes both nibble-sum checksums, so ValidateSave ($1ed2) still passes.

Save layout (from src/transfer.asm ValidateSave + $4d21):
  $bfbe: file index (selected file, 0)
  $bfbf: validity (01)
  $bfc0: lives BCD low  ([$da43] = (([$bfc1]&$0f)<<4)|([$bfc0]&$0f))
  $bfc1: lives BCD high
  $bfc2: progress BCD low  (E = (([$bfc3]&$0f)<<4)|([$bfc2]&$0f))
  $bfc3: progress BCD high
  $bfc0..$bfd9 (26 bytes): low nibbles sum (mod 256) == byte at $bfda/$bfdb
  $bfdc..$bff9: backup copy of the same record (progress at $bfe0/$bfe1,
  checksum at $bff8/$bff9)
  $5e99 table (bank 1): progress E -> queue start (E=0->0, 1->14, 2->27,
  3->40, ... step 13). $4d21 loads [$c85c]/[$c85d] from it.

Usage: make_progress_save.py <in.sav> <out.sav> <progress 0-24>
"""
import sys

def nib_sum(data):
    return sum(b & 0x0F for b in data) & 0xFF

def main():
    src, dst, prog = sys.argv[1], sys.argv[2], int(sys.argv[3])
    assert 0 <= prog <= 24, "progress 0-24 (table has 25 entries)"
    d = bytearray(open(src, 'rb').read())
    assert len(d) == 8192
    # sanity: known f1-save markers
    assert d[0x1ffa:0x2000] == bytes([0x09, 0x04, 0x00, 0x02, 0x00, 0x08]), "bad sig"
    assert d[0x1fd8:0x1fda] == bytes([0x02, 0x07]), "bad $bfd8 marker"
    # primary copy: progress at $bfc2/$bfc3 (file offsets 0x1fc2/0x1fc3)
    d[0x1fc2] = prog & 0x0F
    d[0x1fc3] = (prog >> 4) & 0x0F
    s = nib_sum(d[0x1fc0:0x1fc0 + 26])
    d[0x1fda] = s & 0x0F                     # low nibble only; high nibble was 0
    d[0x1fdb] = (d[0x1fdb] & 0xF0) | ((s >> 4) & 0x0F)
    # backup copy: progress at $bfe0/$bfe1 (offsets 0x1fe0/0x1fe1)
    d[0x1fe0] = prog & 0x0F
    d[0x1fe1] = (prog >> 4) & 0x0F
    s2 = nib_sum(d[0x1fde:0x1fde + 26])
    d[0x1ff8] = s2 & 0x0F
    d[0x1ff9] = d[0x1ff9] & 0xF0 | ((s2 >> 4) & 0x0F)
    assert s == s2, (s, s2)
    # Slice 6 correction: the game's own $4cbe save-write never writes
    # $be2a/$be2b (the $a000 checksum) -- only bank-23 $74a9 does, in the
    # attract-demo flow. So a hand-crafted save from the f1 base fails
    # ValidateSave ($1ed2) on the $a000 checksum (E vs stored $ff) and
    # the backup $be2c checksum, and $1f9a wipes the file records (this
    # is what expH saw). Fix both checksum pairs, nibble-encoded, high
    # nibbles preserved (same encoding as the $bfda/$bfdb pair above).
    def write_cksum(off, e):
        d[off] = (d[off] & 0xF0) | (e & 0x0F)
        d[off + 1] = (d[off + 1] & 0xF0) | ((e >> 4) & 0x0F)
    e_a000 = nib_sum(d[0x0000:0x0190])            # $a000, 0x190 bytes
    e_be2c = nib_sum(d[0x1e2c:0x1e2c + 0x190])    # $be2c backup, 0x190 bytes
    write_cksum(0x1e2a, e_a000)                   # $be2a/$be2b
    write_cksum(0x1fbc, e_be2c)                   # $bfbc/$bfbd
    open(dst, 'wb').write(d)
    print(f"wrote {dst}: progress={prog} queue={[0,14,27,40,53,66,79,92,105,118,131,144,157,170,183,196,209,222,235,248,261,274,287,300,313][prog]} "
          f"primary_sum=${s:02x} backup_sum=${s2:02x} "
          f"a000_cksum=${e_a000:02x} be2c_cksum=${e_be2c:02x}")

if __name__ == '__main__':
    main()
