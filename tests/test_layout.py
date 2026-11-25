import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class LayoutTests(unittest.TestCase):
    def test_assembler_includes_exist(self):
        main = (ROOT / 'src/main.asm').read_text()
        includes = re.findall(r'^\s*INCLUDE\s+"([^"]+)"', main, re.M)
        self.assertGreater(len(includes), 50)
        for name in includes:
            with self.subTest(include=name):
                self.assertTrue((ROOT / 'src' / name).is_file(), name)

    def test_makefile_tracks_all_source_files(self):
        makefile = (ROOT / 'Makefile').read_text()
        self.assertIn('$(wildcard src/banks/*.asm)', makefile)
        self.assertIn('$(wildcard src/core/*.asm)', makefile)

    def test_disassembler_can_use_configured_mgbdis(self):
        with tempfile.TemporaryDirectory() as temp:
            (pathlib.Path(temp) / 'instruction_set.py').write_text(
                'instructions = {}\ncb_instructions = {}\n'
            )
            env = {**os.environ, 'MGBDIS_DIR': temp, 'PYTHONPATH': ''}
            result = subprocess.run(
                [sys.executable, 'tools/gb_rd.py'], cwd=ROOT, env=env,
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rom_header_analyzer_decodes_entry_address(self):
        with tempfile.TemporaryDirectory() as temp:
            rom = bytearray(0x80000)
            rom[0x100:0x104] = bytes.fromhex('00 c3 50 01')
            path = pathlib.Path(temp) / 'fixture.gb'
            path.write_bytes(rom)
            result = subprocess.run(
                [sys.executable, 'tools/analyze_rom.py', str(path)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('jp $0150', result.stdout)

    def test_banks_and_tools_are_grouped(self):
        self.assertTrue((ROOT / 'src/banks/bank1.asm').is_file())
        self.assertTrue((ROOT / 'src/core/states.asm').is_file())
        self.assertTrue((ROOT / 'tools/generators/gen_slice29.py').is_file())
        self.assertTrue((ROOT / 'tools/surveys/survey29_map.py').is_file())
        self.assertTrue((ROOT / 'tools/harnesses/gb_headless.c').is_file())
        self.assertTrue((ROOT / 'tools/tests/run_slice5_regression.sh').is_file())


if __name__ == '__main__':
    unittest.main()
