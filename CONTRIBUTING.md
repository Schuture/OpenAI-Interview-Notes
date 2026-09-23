# Contributing

[English](CONTRIBUTING.md) · [中文](CONTRIBUTING.zh.md)

Thanks for helping. There are three ways to contribute, from least to most effort.

1. **Report a mistake.** [Open an issue](https://github.com/Schuture/OpenAI-Interview-Notes/issues) with a link to the page, the sentence or line of code
   concerned, what is wrong with it and, if you can, what it should say.
2. **Suggest a variant or a new problem.** Open an issue and describe it in your own words: the task, its parts,
   the constraints, the follow-up questions. Leave out anything that identifies an interviewer or a candidate.
3. **Send a pull request** that fixes a page or adds one, following the rules below.

## Content rules

1. **Facts yes, borrowed wording no.** What a round tests, the shape of an API, constraints, known variants and
   time limits are facts and belong here. Prose, structure, example data and code from prep sites, paid material
   or other people's posts do not. Restate everything in your own words and make up fresh examples.
2. **No interview materials.** Never paste starter files or test harnesses handed out in an interview; describe
   the interface instead.
3. **Run what you write.** Solutions are written from scratch and must pass their checks (see below).
4. **Nothing personal.** No names, no precise dates, nothing that identifies a candidate or an interviewer.
5. **Both languages.** The English page is the reference and the Chinese page mirrors it heading for heading.
   Every `python` and `py` block is identical in the two files, with comments in English. If you can only
   write one of the two, open the pull request anyway and say so.

## How a page is written

A page has exactly two sections.

**Problem.** The complete, formal statement, the way a textbook or a competition would put it.

1. Start with the objects of the problem: the input, its shape, the quantity to compute. Do not open with
   remarks about the round or the page.
2. Use standard terminology from textbooks and from the documentation of the library involved. Define a term
   where it is first needed, in one sentence. In the Chinese page, give the standard English term in parentheses
   at first use.
3. One block per part: the rule or task, the function signature, one example. Trace an example step by step
   when the rule is about time or order.
4. No commentary: no sentences that explain the wording, talk about where the problem comes from, or refer to
   the page itself. Anything about the process itself — rounds, timings, tooling — belongs in
   [INTERVIEW-PROCESS.md](INTERVIEW-PROCESS.md), not in a problem page. What type of question it is goes into `kind` in `meta.yaml`, which the page header shows.
5. Do not economise on words that state the task. Do economise on everything else.

**Reference solution.** Everything about the answer, in one section wrapped in a collapsed `<details>` block and
readable in about fifteen minutes.

1. Open with the one or two points worth confirming with the interviewer.
2. Then go part by part: the idea, the derivation if there is one (derive, do not assert), the code.
3. Put technical pitfalls into the code as `# NOTE:` comments on the line they concern, not in a separate list.
4. End with a few one-line follow-ups. No summary, no checklists.
5. Put the checks into a second, nested `<details>` block at the end: asserts on the examples, and a brute force
   written from the statement alone (it must not call the solution's helpers) wherever one is feasible. For a
   system-design page, recompute every estimate the text quotes.

Code fences: a block marked `python` is executed and must run; a block marked `py` is illustrative only
(bare signatures, code that fails on purpose). All `python` blocks of a page run top to bottom in one namespace
and should take well under 30 seconds in total on a laptop CPU.

## Adding a problem

A problem is a folder `<category>/<slug>/` with three files: `meta.yaml`, `README.md` and `README.zh.md`.
Copying a page of the same category is the easiest start. Keep the `<!-- meta:begin -->` and
`<!-- meta:end -->` lines under the language switch; the header table between them is generated.

| `meta.yaml` key | Meaning |
| --- | --- |
| `title`, `title_zh` | page title; the first line of each README must be `# <title>` |
| `summary`, `summary_zh` | one sentence on what the problem asks, shown in the roadmap |
| `category` | `coding`, `system-design` or `behavioral`; must match the folder |
| `kind`, `kind_zh` | type of question shown in the header, e.g. `Coding with derivation · NumPy` |
| `roles` | any of `RS`, `RE`, `MLE`, `SWE`, `Infra Eng`, `EM`, `All` |
| `topics` | short tags such as `heap`, `idempotency` |
| `difficulty` | `easy`, `medium` or `hard` (optional) |
| `frequency` | `very-high`, `high`, `medium`, `low` or `rare`; shown as ★★★★★ to ★☆☆☆☆ |
| `format` | number of parts and, if known, the length of the round, e.g. `4 parts / 60 min` (optional) |
| `stage` | any of `phone-screen`, `tech-screen`, `recruiter-screen`, `onsite` (optional) |
| `order` | position among problems with the same frequency |

To place the problem in a study track, add it to `scripts/roadmap.yaml`.

## Before you open a pull request

```bash
pip install -r requirements.txt
python scripts/build_index.py                              # regenerate page headers, README tables, roadmap
python scripts/check_i18n.py                               # both languages in sync, links and anchors resolve
python scripts/check_render.py                             # emphasis and collapsed sections render on GitHub
python scripts/run_snippets.py coding/<slug>               # run the page's code
python scripts/run_snippets.py --hash-seeds coding/<slug>  # for pages with randomness or sets
```

`--hash-seeds` runs the page under two string-hash seeds: if the result changes, the code depends on the
iteration order of a set somewhere. CI runs all of these checks on every pull request.
