#!/usr/bin/env python3
"""Run the ```python blocks of a page, top to bottom, in one namespace.

    python scripts/run_snippets.py coding/infection-spread
    python scripts/run_snippets.py --all          # every page
    python scripts/run_snippets.py --hash-seeds coding/cluster-count-topology   # run twice, PYTHONHASHSEED=0 and 1
    python scripts/run_snippets.py --all --strict # a missing library is a failure, not a skip (used by CI)

Each page is a script: its solution blocks followed by the checks in the collapsed block at the end,
which assert the solution against the examples and, where one exists, an independent brute force.
Blocks are taken from README.md; check_i18n.py guarantees README.zh.md carries the same code.
Only ```python fences are executed. Use ```py for illustrative snippets that are not meant to run
(bare signatures, code that raises on purpose); GitHub highlights both the same way.

--hash-seeds runs each page in two fresh interpreters with different string-hash seeds. A page whose asserts
pass under one seed and fail under the other iterates over a set (or dict built from one) somewhere its
output depends on the order -- a real bug in a simulation, not flakiness.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import traceback

from _lib import ROOT, load_problems

FENCE_RE = re.compile(r"^```python\n(.*?)^```", re.S | re.M)


STRICT = False


def run(rel: str) -> bool:
    page = ROOT / rel / "README.md"
    blocks = FENCE_RE.findall(page.read_text(encoding="utf-8"))
    blocks = [b for b in blocks if b.strip()]
    if not blocks:
        print(f"– {rel}: no python blocks")
        return True
    namespace: dict = {"__name__": "__snippets__"}
    for i, block in enumerate(blocks, 1):
        try:
            exec(compile(block, f"{rel} block #{i}", "exec"), namespace)
        except ModuleNotFoundError as e:       # optional dependency such as torch: skip unless --strict
            if STRICT:
                print(f"✗ {rel}: block #{i} needs a missing library ({e}); pip install -r requirements.txt")
                return False
            print(f"– {rel}: block #{i} skipped ({e})")
        except Exception:
            print(f"✗ {rel}: block #{i} failed")
            traceback.print_exc()
            return False
    print(f"✓ {rel}: {len(blocks)} block(s) ran")
    return True


def run_hash_seeds(rel: str) -> bool:
    ok = True
    for seed in ("0", "1"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        cmd = [sys.executable, __file__, rel] + (["--strict"] if STRICT else [])
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"✗ {rel}: fails with PYTHONHASHSEED={seed}")
            print(proc.stdout[-3000:] + proc.stderr[-3000:])
            ok = False
    if ok:
        print(f"✓ {rel}: passes with PYTHONHASHSEED=0 and 1")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pages", nargs="*", help="problem folders such as coding/infection-spread")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--hash-seeds", action="store_true", help="run each page under two string-hash seeds")
    ap.add_argument("--strict", action="store_true", help="fail instead of skipping when a library is missing")
    args = ap.parse_args()
    global STRICT
    STRICT = args.strict
    pages = [p.rel for p in load_problems()] if args.all else args.pages
    if not pages:
        ap.error("give at least one page or --all")
    runner = run_hash_seeds if args.hash_seeds else run
    return 0 if all([runner(rel.strip("/")) for rel in pages]) else 1


if __name__ == "__main__":
    sys.exit(main())
