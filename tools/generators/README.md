# Historical slice generators

These scripts document how parts of the disassembly were produced. They are **not** a pipeline to run from first slice to last, and they are not needed to build the project.

They can overwrite current source, including corrections made in later slices. Some write several files and may stop after only some have been changed. For example, the slice-3 generator overwrites files later corrected in slice 4, and the slice-12 generator can write files before encountering an existing-data guard.

Read the script and its progress-log entry before running it. Experiment in a disposable checkout, not your working tree. Many scripts require the target ROM and mgbdis; see the project README for setup.

`gen_banks.py` is different: it writes generated padding to standard output. Its output can be compared with `src/banks.asm` without modifying the source:

```sh
python3 tools/generators/gen_banks.py | diff -u src/banks.asm -
```
