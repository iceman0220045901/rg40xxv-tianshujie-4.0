#!/usr/bin/env python3
"""Patch the in-game help/guide text files so completed stories can be colored.

Background
----------
The engine colors a guide entry green and appends "（完成）" only when the
line carries an event marker of the form 'N' (N = 1-based story index):

    TSGL(filename, id):
        local i1, j1 = string.find(str[k], "'%x+'", 1)
        if JY.GLTS[id - 1][tsnum] == 1 then   -- mark as done
            color[k] = RGB(120, 208, 88)
            str[k] = string.gsub(str[k], "'%x+'", "（完成）", 1)
        else
            color[k] = C_WHITE
            str[k] = string.gsub(str[k], "'%x+'", "", 1)

The marker itself is only a display hook: the engine rewrites it at draw time,
so the file on disk keeps it.  The Xiangao Jianghu (book 8) guide shipped in
4.0 has no markers at all, therefore it can never turn green even after the
story has been completed and recorded in the save (JY.GLTS[7][1] = 1).

What this script does
--------------------
For each guide file it walks the numbered story lines ("1.", "2.", ...) and
appends the matching 'N' marker.  Only a strictly increasing run counts as
story lines, so repeated numbers used by branch notes ("6.分支二（选“是”）")
are left untouched.  Files that already carry the marker are skipped, so the
script is idempotent.  A backup of every touched file is kept in Help_bak/.

Usage
-----
    python3 patch_helpmark.py                # dry run, books 1..16
    python3 patch_helpmark.py --apply        # write the files
    python3 patch_helpmark.py --apply 8 4    # only books 8 and 4
    python3 patch_helpmark.py --help-dir /roms/ports/jysdlbh/data/Help
"""

import os
import re
import shutil
import sys

DEFAULT_HELP = "/roms/ports/jysdlbh/data/Help"
DEFAULT_BAK = "/roms/ports/jysdlbh/data/Help_bak"


def patch_file(path, bak_dir, apply):
    data = open(path, "rb").read()
    lines = data.split(b"\r\n")

    expect = 1
    changed = 0
    seq = []
    out = []

    for line in lines:
        m = re.match(rb"^(\d+)\.", line)
        new = line
        if m:
            num = int(m.group(1))
            if num == expect:
                seq.append(num)
                mark = b"'" + m.group(1) + b"'"
                if mark not in line:
                    new = line + mark
                    changed += 1
                expect += 1
        out.append(new)

    newdata = b"\r\n".join(out)
    name = os.path.basename(path)
    print("%-8s stories=%-3d marked=%-3d size %d -> %d" %
          (name, len(seq), changed, len(data), len(newdata)))

    if apply and newdata != data:
        os.makedirs(bak_dir, exist_ok=True)
        bak = os.path.join(bak_dir, name)
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        with open(path, "wb") as f:
            f.write(newdata)
    return changed


def main(argv):
    apply = "--apply" in argv
    help_dir = DEFAULT_HELP
    bak_dir = DEFAULT_BAK
    if "--help-dir" in argv:
        help_dir = argv[argv.index("--help-dir") + 1]
        bak_dir = os.path.join(os.path.dirname(help_dir.rstrip("/")), "Help_bak")

    books = []
    for a in argv:
        if a.isdigit():
            books.append(int(a))
    if not books:
        books = list(range(1, 17))

    print("mode:", "APPLY" if apply else "DRY-RUN", "dir:", help_dir)
    total = 0
    for n in books:
        p = os.path.join(help_dir, "%d.txt" % n)
        if not os.path.exists(p):
            print("  missing:", p)
            continue
        total += patch_file(p, bak_dir, apply)
    print("total markers added:", total)
    print("DONE")


if __name__ == "__main__":
    main(sys.argv[1:])
