#!/usr/bin/env python3
"""Find emphasis markers that GitHub will print literally instead of rendering.

    python scripts/check_render.py                      # every page, plus the top-level README, ROADMAP, CONTRIBUTING
    python scripts/check_render.py coding/gpu-credits    # only these folders

CommonMark closes `*...*` only if the closing star is "right-flanking". A star that follows punctuation and is
followed by a letter is not, so `*原地（in-place）*操作` shows its stars. Write `*原地*（in-place）操作` instead.
The page is parsed with markdown-it (CommonMark rules, as GitHub uses); maths is masked first. Needs markdown-it-py.

Also checks the collapsed sections: GitHub renders <details>/<summary>, but only parses the Markdown inside when
<details> starts a block, </summary> is followed by a blank line and </details> is preceded by one; tags must balance.
"""
from __future__ import annotations

import re
import sys

from markdown_it import MarkdownIt

from _lib import README, ROOT, load_problems

MATH = re.compile(r"```math\n.*?\n```|\$\$.*?\$\$|(?<![\\$])\$(?!\s)[^$\n]+?(?<!\s)\$", re.S)


def leftovers(text: str) -> list[str]:
    md = MarkdownIt("commonmark").enable("table")
    found = []
    for tok in md.parse(MATH.sub("MATH", text)):
        if tok.type != "inline":
            continue
        for child in tok.children or []:
            if child.type == "text" and re.search(r"\*|(?<!\w)_(?!\w)", child.content):
                found.append(tok.content.strip().replace("\n", " ")[:110])
                break
    return found


def details_problems(text: str) -> list[str]:
    text = re.sub(r"^```.*?^```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S | re.M)
    lines = re.sub(r"`[^`\n]+`", "CODE", text).split("\n")          # tags quoted in inline code do not count
    out, depth = [], 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s == "<details>":
            depth += 1
            if i and lines[i - 1].strip():
                out.append(f"line {i + 1}: <details> needs a blank line before it")
            if i + 1 >= len(lines) or not lines[i + 1].strip().startswith("<summary>"):
                out.append(f"line {i + 1}: <details> must be followed by its <summary> line")
        elif s.startswith("<summary>"):
            if not s.endswith("</summary>") or i + 1 >= len(lines) or lines[i + 1].strip():
                out.append(f"line {i + 1}: one-line <summary>...</summary>, then a blank line")
        elif s == "</details>":
            depth -= 1
            if lines[i - 1].strip():
                out.append(f"line {i + 1}: </details> needs a blank line before it")
        elif "<details" in s or "</details" in s or "<summary" in s:
            out.append(f"line {i + 1}: keep each details/summary tag on a line of its own")
    if depth:
        out.append("unbalanced <details> tags")
    return out


def main() -> int:
    only = {a.strip("/") for a in sys.argv[1:]}
    files = [p.path / name for p in load_problems() if not only or p.rel in only for name in README.values()]
    if not only:
        files += sorted(ROOT.glob("*.md"))
    bad = 0
    for f in files:
        if f.exists():
            rel = f.relative_to(ROOT).as_posix()
            text = f.read_text(encoding="utf-8")
            for line in leftovers(text):
                print(f"✗ {rel}: literal emphasis marker -> {line}")
                bad += 1
            for msg in details_problems(text):
                print(f"✗ {rel}: {msg}")
                bad += 1
    print(f"{bad} rendering problem(s)" if bad else "✓ emphasis markers and collapsed sections will render")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
