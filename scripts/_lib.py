"""Shared helpers for the repo scripts: loading meta.yaml files and label tables."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = ("coding", "system-design", "behavioral")
LANGS = ("en", "zh")
README = {"en": "README.md", "zh": "README.zh.md"}

FREQUENCY_ORDER = ["very-high", "high", "medium", "low", "rare"]
DIFFICULTIES = ["easy", "medium", "hard"]
ROLES = ["RS", "RE", "MLE", "SWE", "Infra Eng", "EM", "All"]

REQUIRED_KEYS = ("title", "title_zh", "summary", "summary_zh", "category",
                 "roles", "topics", "frequency", "order")
STAGES = ["phone-screen", "tech-screen", "recruiter-screen", "onsite"]

# how often a question comes up, shown as a five-star priority
STARS = {f: "★" * (5 - i) + "☆" * i for i, f in enumerate(FREQUENCY_ORDER)}

LABELS = {
    "en": {
        "category": {"coding": "Coding", "system-design": "System design", "behavioral": "Behavioral & other"},
        "frequency": STARS,
        "difficulty": {"easy": "Easy", "medium": "Medium", "hard": "Hard", None: "—"},
        "role": {},
        "stage": {"phone-screen": "Phone screen", "tech-screen": "Technical screen",
                  "recruiter-screen": "Recruiter screen", "onsite": "Onsite"},
        "cols": {"problem": "Problem", "frequency": "Priority", "difficulty": "Difficulty",
                 "roles": "Roles", "topics": "Topics", "format": "Format",
                 "stage": "Round", "summary": "In one line", "kind": "Type"},
    },
    "zh": {
        "category": {"coding": "编程", "system-design": "系统设计", "behavioral": "行为面与其他"},
        "frequency": STARS,
        "difficulty": {"easy": "简单", "medium": "中等", "hard": "困难", None: "—"},
        "role": {"All": "全部"},
        "stage": {"phone-screen": "电话面", "tech-screen": "技术初筛",
                  "recruiter-screen": "HR 初筛", "onsite": "现场面"},
        "cols": {"problem": "题目", "frequency": "优先级", "difficulty": "难度",
                 "roles": "岗位", "topics": "考点", "format": "形式",
                 "stage": "轮次", "summary": "一句话", "kind": "题型"},
    },
}


@dataclass
class Problem:
    path: Path          # absolute folder
    meta: dict

    @property
    def rel(self) -> str:                       # e.g. "coding/infection-spread"
        return self.path.relative_to(ROOT).as_posix()

    def title(self, lang: str) -> str:
        return self.meta["title_zh"] if lang == "zh" else self.meta["title"]

    def summary(self, lang: str) -> str:
        return self.meta["summary_zh"] if lang == "zh" else self.meta["summary"]

    def sort_key(self):
        return (FREQUENCY_ORDER.index(self.meta["frequency"]), self.meta["order"])


def load_problems() -> list[Problem]:
    problems = []
    for cat in CATEGORIES:
        for meta_file in sorted((ROOT / cat).glob("*/meta.yaml")):
            meta = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
            problems.append(Problem(meta_file.parent, meta))
    return problems


def replace_block(text: str, name: str, new_body: str) -> str:
    """Replace what sits between <!-- name:begin --> and <!-- name:end -->."""
    begin, end = f"<!-- {name}:begin -->", f"<!-- {name}:end -->"
    if begin not in text or end not in text:
        raise ValueError(f"markers for block '{name}' not found")
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{begin}\n{new_body.strip()}\n{end}{tail}"


def meta_table(p: Problem, lang: str) -> str:
    L = LABELS[lang]
    m = p.meta
    cols = ["frequency", "difficulty", "roles", "topics"]
    vals = [L["frequency"][m["frequency"]], L["difficulty"][m.get("difficulty")],
            roles_label(m, lang), ", ".join(m["topics"])]
    kind = m.get("kind_zh") if lang == "zh" else m.get("kind")
    if kind:                                   # what sort of question: coding, derivation, debugging, spoken...
        cols.insert(0, "kind")
        vals.insert(0, kind)
    if m.get("format"):
        cols.append("format")
        vals.append(format_label(m, lang))
    if m.get("stage"):
        cols.append("stage")
        vals.append(" · ".join(L["stage"][s] for s in m["stage"]))
    header = "| " + " | ".join(L["cols"][c] for c in cols) + " |"
    rule = "|" + " --- |" * len(cols)
    return "\n".join([header, rule, "| " + " | ".join(vals) + " |"])


def format_label(m: dict, lang: str) -> str:
    """`format` is written in English ("3 parts", "4 parts / 60 min"); the Chinese page gets a translation
    unless meta.yaml gives `format_zh` explicitly."""
    s = str(m["format"])
    if lang != "zh":
        return s
    if m.get("format_zh"):
        return str(m["format_zh"])
    for pat, rep in ((r"(\d+) oral parts?", r"\1 个口述部分"), (r"(\d+) parts?", r"\1 个部分"),
                     (r"(\d+) bugs?", r"\1 个 bug"), (r"(\d+) follow-ups?", r"\1 个追问"),
                     (r"(\d+) min\b", r"\1 分钟"), (r"\bbonus\b", "附加题")):
        s = re.sub(pat, rep, s)
    return s


def roles_label(m: dict, lang: str) -> str:
    return " · ".join(LABELS[lang]["role"].get(r, r) for r in m["roles"])
