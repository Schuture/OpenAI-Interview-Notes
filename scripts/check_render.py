#!/usr/bin/env python3
"""Find emphasis markers that GitHub will print literally instead of rendering.

    python scripts/check_render.py                      # every page, plus the top-level README, ROADMAP, CONTRIBUTING
    python scripts/check_render.py coding/gpu-credits    # only these folders

CommonMark closes `*...*` only if the closing star is "right-flanking". A star that follows punctuation and is
followed by a letter is not, so `*原地（in-place）*操作` shows its stars. Write `*原地*（in-place）操作` instead.
The page is parsed with markdown-it (CommonMark rules, as GitHub uses); maths is masked first. Needs markdown-it-py.

Also checks the collapsed sections: GitHub renders <details>/<summary>, but only parses the Markdown inside when
<details> starts a block, </summary> is followed by a blank line and </details> is preceded by one; tags must balance.

Also checks maths. GitHub runs Markdown escapes and emphasis inside `$...$` and `$$...$$` before MathJax sees them
(`\\{` `\\,` `\\%` `\\\\` lose their backslash, `}_..._` turns into italics), and only opens inline maths after
whitespace or `(`, so `取值，$n$` and `top-$k$` print their dollars. Write display maths as a ```math block and any
inline maths that trips a rule below as $`...`$, which GitHub passes to MathJax untouched.
GitHub also refuses some macros outright ("The following macros are not allowed: operatorname"); use \\mathrm{...}.
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


PUNCT = r"""!"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~"""
MATH_TOKEN = re.compile(r"\$(`+)[\s\S]*?\1\$|(`+)[\s\S]*?\2|\\\$|\$\$([\s\S]+?)\$\$|\$(?=[^\s$])((?:\\.|[^$\\])*?)(?<=\S)\$")


BLOCKED_MACROS = ("operatorname",)  # GitHub shows "The following macros are not allowed: ..." for these


def math_problems(text: str) -> list[str]:
    """Maths GitHub would print literally or hand to MathJax mangled; each should be a ```math block or $`...`$."""
    out, fence = [], None
    for i, line in enumerate(text.split("\n"), 1):
        opener = re.match(r"\s*(```+)\s*(\w*)", line)
        if fence is None and opener:
            fence = opener.group(2)
        elif fence is not None and opener and not opener.group(2):
            fence = None
        elif fence in (None, "math"):
            out += [f"line {i}: GitHub does not allow \\{m}, use \\mathrm{{...}}"
                    for m in re.findall(r"\\(" + "|".join(BLOCKED_MACROS) + r")\b", line)]
    text = re.sub(r"^\s*```.*?^\s*```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S | re.M)
    for m in MATH_TOKEN.finditer(text):
        lineno = text.count("\n", 0, m.start()) + 1
        if m.group(3) is not None:
            out.append(f"line {lineno}: write display maths as a ```math block -> {m.group(0)[:50]!r}")
            continue
        c = m.group(4)
        if c is None:
            continue
        st, en = m.start(), m.end()
        prev, nxt = text[st - 1] if st else "\n", text[en] if en < len(text) else "\n"
        line = text[text.rfind("\n", 0, st) + 1:text.find("\n", en) if "\n" in text[en:] else len(text)]
        para = text[text.rfind("\n\n", 0, st) + 1:st]
        para = re.sub(r"(`+)[\s\S]*?\1|\$[^$]*\$|\\\*|\*\*+|^\s*\* ", "", para, flags=re.M)
        why = [w for w, bad in [
            ("not after a space or '('", not (prev.isspace() or prev == "(")),
            ("followed by a letter or digit", re.match(r"[A-Za-z0-9_]", nxt)),
            ("Markdown escape, * or _ inside", re.search(r"\\[" + PUNCT + r"]|\*|(?<![A-Za-z0-9\\])_", c)),
            ("inside *emphasis*", para.count("*") % 2),
            ("'(...)' right before ')'", nxt == ")" and ")" in c),
            ("\\$ on the same line", "\\$" in line),
            ("symbol only", not re.search(r"[A-Za-z0-9]", c)),
        ] if bad]
        if why:
            out.append(f"line {lineno}: use $`...`$ ({'; '.join(why)}) -> ${c[:50]}$")
    return out


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
            for msg in details_problems(text) + math_problems(text):
                print(f"✗ {rel}: {msg}")
                bad += 1
    print(f"{bad} rendering problem(s)" if bad else "✓ emphasis markers, maths and collapsed sections will render")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
