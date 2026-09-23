#!/usr/bin/env python3
"""Consistency checks for the bilingual notes. Exits non-zero when something is off.

    python scripts/check_i18n.py                         # whole repository
    python scripts/check_i18n.py coding/gpu-credits       # only these problem folders (no link check)

For every problem folder:
  * meta.yaml has the required keys and legal values
  * README.md and README.zh.md both exist, carry the language switch and the meta markers,
    and start with "# <title>" / "# <title_zh>" from meta.yaml
  * both files have the same number of ## and ### headings
  * every ```python (runnable) and ```py (illustrative) block is byte-identical in the two languages
  * no template placeholder comments are left
  * warning (does not fail the check): sentences that talk about where the material comes from instead
    of the problem, e.g. "reports say", "candidates", "面经", "候选人" (CONTRIBUTING, writing rules), and
    Chinese prose written with ASCII quotes or ASCII commas
Across the repo:
  * every relative Markdown link points at something that exists, including the #heading anchor
"""
from __future__ import annotations

import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

from _lib import (CATEGORIES, DIFFICULTIES, FREQUENCY_ORDER, README, REQUIRED_KEYS, ROLES, ROOT, STAGES,
                  load_problems)

FENCE_RE = re.compile(r"^```(\w*)\n(.*?)^```", re.S | re.M)
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
SWITCH = "[English](README.md) · [中文](README.zh.md)"
SOURCE_TALK = {
    # phrases that talk about where the material comes from; bare "report" / "candidate" are ordinary
    # technical words (an annotator reports a label, a candidate user) and are not flagged
    "en": re.compile(r"\b(reports? (say|says|stress|put|describe|mention|agree|differ|give)|known reports?|"
                     r"(is|are|was|were) reported|reportedly|according to (the )?reports?|"
                     r"candidates? (report|say|describe|mention)s?|interview(er)?s? hand out|not public)\b", re.I),
    "zh": re.compile(r"面经|原始资料|据报告|候选人(反馈|报告|提到|表示|说)|并不公开|为练习而写"),
}
# Chinese prose should use full-width quotes “ ”; code spans and maths are masked first
ASCII_QUOTE = re.compile(r'[\u4e00-\u9fff][^"\n]{0,30}"|"[^"\n]{0,30}[\u4e00-\u9fff]')
# Chinese prose takes full-width punctuation; an ASCII comma or semicolon touching a Chinese character is a slip
# ("Lock, RLock" between two ASCII words and "1,000" inside a number are fine)
HALF_WIDTH = re.compile(r"[\u4e00-\u9fff][,;]|[,;][\u4e00-\u9fff]")
# behavioral pages only: frequency claims about how interviewers or recruiters behave
PROCESS_TALK = {
    "en": re.compile(r"\b(often|usually|typically|tend to)\b", re.I),
    "zh": re.compile(r"往往|通常|一般会"),
}


def strip_code(text: str) -> str:
    return FENCE_RE.sub("", text)


def github_slug(heading: str) -> str:
    """The anchor GitHub gives a heading: lower-case, punctuation and symbols dropped, spaces to hyphens."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)          # [text](url) -> text
    text = re.sub(r"[`*]", "", text).strip().lower()
    kept = "".join(c for c in text if unicodedata.category(c)[0] in "LMN" or c in "_- ")
    return kept.replace(" ", "-")


@lru_cache(maxsize=None)
def anchors(md: Path) -> frozenset[str]:
    seen: dict[str, int] = {}
    out = set()
    for line in strip_code(md.read_text(encoding="utf-8")).splitlines():
        m = re.match(r"^#{1,6} (.*?)\s*$", line)
        if not m:
            continue
        s = github_slug(m.group(1))
        n = seen.get(s, 0)
        seen[s] = n + 1
        out.add(s if n == 0 else f"{s}-{n}")
    return frozenset(out)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    only = {a.strip("/") for a in sys.argv[1:]}
    problems = [p for p in load_problems() if not only or p.rel in only]
    if not problems:
        errors.append("no problems found")

    for p in problems:
        m, where = p.meta, p.rel
        for key in REQUIRED_KEYS:
            if m.get(key) in (None, "", []):
                errors.append(f"{where}/meta.yaml: missing '{key}'")
        if m.get("category") != where.split("/")[0]:
            errors.append(f"{where}/meta.yaml: category does not match its folder")
        if m.get("frequency") not in FREQUENCY_ORDER:
            errors.append(f"{where}/meta.yaml: bad frequency {m.get('frequency')!r}")
        for stage in m.get("stage") or []:
            if stage not in STAGES:
                errors.append(f"{where}/meta.yaml: unknown stage {stage!r}")
        if m.get("difficulty") not in DIFFICULTIES + [None]:
            errors.append(f"{where}/meta.yaml: bad difficulty {m.get('difficulty')!r}")
        for role in m.get("roles") or []:
            if role not in ROLES:
                errors.append(f"{where}/meta.yaml: unknown role {role!r}")

        texts = {}
        for lang, name in README.items():
            f = p.path / name
            if not f.exists():
                errors.append(f"{where}: {name} is missing")
                continue
            t = texts[lang] = f.read_text(encoding="utf-8")
            if SWITCH not in t:
                errors.append(f"{where}/{name}: language switch line missing")
            if "<!-- meta:begin -->" not in t or "<!-- meta:end -->" not in t:
                errors.append(f"{where}/{name}: meta markers missing")
            if t.split("\n", 1)[0] != f"# {p.title(lang)}":
                errors.append(f"{where}/{name}: first line should be '# {p.title(lang)}' (the title in meta.yaml)")
            body = re.sub(r"<!-- meta:begin -->.*?<!-- meta:end -->", "", strip_code(t), flags=re.S)
            for line in body.splitlines():
                if SOURCE_TALK[lang].search(line):
                    warnings.append(f"{where}/{name}: talks about the source? -> {line.strip()[:90]}")
                elif lang == "zh" and ASCII_QUOTE.search(re.sub(r"`[^`\n]*`|\$[^$\n]*\$|<[^>]+>", "", line)):
                    warnings.append(f"{where}/{name}: ASCII quotes in Chinese prose, use “ ” -> {line.strip()[:90]}")
                elif lang == "zh" and HALF_WIDTH.search(re.sub(r"`[^`\n]*`|\$[^$\n]*\$|<[^>]+>", "", line)):
                    warnings.append(f"{where}/{name}: half-width punctuation in Chinese prose, use ，； -> "
                                    f"{line.strip()[:90]}")
                elif m.get("category") == "behavioral" and PROCESS_TALK[lang].search(line):
                    warnings.append(f"{where}/{name}: claim about how the process usually goes? -> "
                                    f"{line.strip()[:90]}")
            if re.search(r"<!--(?! meta:)(?!\s*i18n)", t):
                errors.append(f"{where}/{name}: template placeholder comment left")
        if len(texts) < 2:
            continue

        for level in ("## ", "### "):
            n = {lang: sum(1 for line in strip_code(t).splitlines() if line.startswith(level))
                 for lang, t in texts.items()}
            if n["en"] != n["zh"]:
                errors.append(f"{where}: {level.strip()} heading count differs (en {n['en']}, zh {n['zh']})")
        code = {lang: [(kind, body) for kind, body in FENCE_RE.findall(t) if kind in ("python", "py")]
                for lang, t in texts.items()}
        if code["en"] != code["zh"]:
            k = next((i for i, (a, b) in enumerate(zip(code["en"], code["zh"])) if a != b),
                     min(len(code["en"]), len(code["zh"])))
            errors.append(f"{where}: code block #{k + 1} differs between languages "
                          f"(en has {len(code['en'])} blocks, zh has {len(code['zh'])})")

    skip = {"_dev", "_raw", ".git"}
    for md in ([] if only else ROOT.rglob("*.md")):
        if skip & set(md.relative_to(ROOT).parts):
            continue
        for target in LINK_RE.findall(strip_code(md.read_text(encoding="utf-8"))):
            if re.match(r"^(https?:|mailto:)", target):
                continue
            file_part, _, anchor = target.partition("#")
            path = (md.parent / file_part).resolve() if file_part else md
            if not path.exists():
                errors.append(f"{md.relative_to(ROOT)}: broken link -> {target}")
            elif anchor and path.suffix == ".md" and anchor not in anchors(path):
                errors.append(f"{md.relative_to(ROOT)}: no heading for anchor -> {target}")

    for cat in ([] if only else CATEGORIES):
        for folder in (ROOT / cat).iterdir():
            if folder.is_dir() and not (folder / "meta.yaml").exists():
                errors.append(f"{folder.relative_to(ROOT)}: folder without meta.yaml")

    if warnings:
        print("\n".join(f"⚠ {w}" for w in warnings))
    if errors:
        print("\n".join(f"✗ {e}" for e in errors))
        print(f"\n{len(errors)} problem(s) found")
        return 1
    print(f"✓ {len(problems)} problems, both languages consistent, all links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
