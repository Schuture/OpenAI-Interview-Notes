# Data Labeling Task Scheduler

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★★☆ | Medium | SWE · RE · MLE | scheduling, greedy, fairness | 3 parts |
<!-- meta:end -->

## Problem

There are $t$ tasks, indexed $0, 1, \dots, t-1$; $m$ models, indexed $0, \dots, m-1$; and $h$ human
labelers, indexed $0, \dots, h-1$. Labeling a task means showing a human labeler one model's output on
that task and asking for a rating. An *assignment* is a triple $(\mathrm{task}, \mathrm{model},
\mathrm{human})$ recording one such review. A *schedule* is an ordered list $S = (a_0, a_1, \dots,
a_{L-1})$ of assignments, $a_j = (\mathrm{task}_j, \mathrm{model}_j, \mathrm{human}_j)$, in the order the
platform hands them out. The order matters: every rule below is stated for each *prefix* of $S$ — for
$0 \le p \le L$, the prefix of length $p$ is $S[:p] = (a_0, \dots, a_{p-1})$.

An integer $k \ge 0$ is also given. Every part below shares two base rules:

- **Coverage.** For every human $u$, at least $k$ assignments of $S$ have $\mathrm{human}_j = u$.
- **Uniqueness.** No two assignments share both the same task and the same human: for $i \ne j$,
  $(\mathrm{task}_i, \mathrm{human}_i) \ne (\mathrm{task}_j, \mathrm{human}_j)$.

Every part also asks for a schedule with the fewest possible assignments.

### Part 1 — Coverage and uniqueness

Implement `build_basic_schedule`. Model choice is unconstrained in this part.

```py
from typing import List, Optional, Tuple
Assignment = Tuple[int, int, int]  # (task, model, human)

def build_basic_schedule(t: int, m: int, h: int, k: int) -> Optional[List[Assignment]]:
    """Returns None if t <= 0, m <= 0, or h <= 0 (invalid dimensions, regardless of k). Otherwise
    returns [] if k == 0, or None if k > t (infeasible). Otherwise
    returns a schedule of exactly h * k assignments satisfying coverage and uniqueness."""
```

Example, with $t = 2$, $m = 2$, $h = 3$, $k = 2$: one valid schedule is

```text
(0, 0, 0), (1, 0, 1), (0, 0, 2), (1, 0, 0), (0, 0, 1), (1, 0, 2)
```

Each human appears exactly twice, once on each task; the model is always 0, which this part allows.

### Part 2 — Balanced by task

For a prefix $S[:p]$, a task $x$, and a model $i$, let

$$c_p(x, i) = \sum_{j=0}^{p-1} [\mathrm{task}_j = x \text{ and } \mathrm{model}_j = i]$$

count how many times model $i$ has been used on task $x$ within that prefix. A schedule is *balanced by
task* if for every prefix $p$ and every task $x$,

$$\max_i c_p(x, i) - \min_i c_p(x, i) \le 1 ,$$

the maximum and minimum ranging over all $m$ models. Implement `build_balanced_schedule`, returning a
schedule with coverage, uniqueness, and balance by task.

```py
def build_balanced_schedule(t: int, m: int, h: int, k: int) -> Optional[List[Assignment]]:
    """Same feasibility contract as build_basic_schedule. The returned schedule is also balanced
    by task at every prefix, with exactly h * k assignments."""
```

Example, same $t, m, h, k$ as Part 1: one minimal balanced schedule is

```text
(0, 0, 0), (1, 0, 1), (0, 1, 2), (1, 1, 0), (0, 0, 1), (1, 0, 2)
```

Task 0 appears at positions 0, 2 and 4; its per-model counts evolve $(1, 0) \to (1, 1) \to (2, 1)$, so
the difference never exceeds 1. Task 1 behaves identically.

### Part 3 — Also balanced by human

Define $c_p(u, i)$ for a human $u$ the same way as $c_p(x, i)$ above, counting assignments with
$\mathrm{human}_j = u$ and $\mathrm{model}_j = i$ instead. A schedule is *balanced by human* if
$\max_i c_p(u, i) - \min_i c_p(u, i) \le 1$ for every prefix $p$ and every human $u$.

Implement `build_doubly_balanced_schedule`, which must keep coverage, uniqueness, and balance by task
exactly as in Part 2, and additionally tries to also achieve balance by human, using a greedy rule of
your choice: at each step, pick the model for the next assignment from the running counts. Then decide
whether your rule actually guarantees balance by human at every prefix, for every valid $t, m, h, k$ —
prove it, or find the smallest counterexample you can: parameters, and the prefix at which it fails.

```py
def build_doubly_balanced_schedule(t: int, m: int, h: int, k: int) -> Optional[List[Assignment]]:
    """Same feasibility contract and minimal length h * k as build_balanced_schedule, and always
    balanced by task. Attempts, via a greedy rule, to also be balanced by human."""
```

Example, with $t = 2$, $m = 3$, $h = 4$, $k = 2$: one schedule that is balanced both by task and by
human is

```text
(0, 0, 0), (1, 0, 1), (0, 1, 2), (1, 1, 3), (1, 2, 0), (0, 2, 1), (1, 0, 2), (0, 0, 3)
```

Task 0 appears four times, at positions 0, 2, 5 and 7, using models 0, 1, 2, 0 in turn; every human's
two models differ from each other.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two points worth confirming before coding: whether the balance conditions must hold at every prefix or
only at the end (the stronger per-prefix version below is what makes Part 2 non-trivial, and what every
construction here targets), and whether repeated labeling is forbidden per (task, human) pair, as assumed
below, or per full (task, model, human) triple, which would let a human see the same task again under a
different model.

### Part 1

Uniqueness forbids two assignments with the same (task, human) pair, so a single human can appear in at
most $t$ assignments, one per task. Coverage then forces $k \le t$; this bound is also sufficient. Given
valid dimensions ($t, m, h > 0$), `build_basic_schedule` returns `[]` when $k = 0$ and `None` when $k > t$;
with an invalid dimension ($t \le 0$, $m \le 0$, or $h \le 0$) it returns `None` regardless of $k$.

Every assignment raises exactly one human's total by 1, so meeting coverage for all $h$ humans needs at
least $h \cdot k$ assignments; a schedule that gives every human exactly $k$, no more, is therefore
minimal. Round $r = 0, \dots, k-1$ gives human $u$ the task $(u + r) \bmod t$: since $r$ ranges over
$k \le t$ consecutive residues, the $k$ tasks assigned to one human are pairwise distinct, so uniqueness
holds, and every human ends up with exactly $k$ tasks over the $k$ rounds.

```python
def build_basic_schedule(t, m, h, k):
    if t <= 0 or m <= 0 or h <= 0:
        return None
    if k == 0:
        return []
    if k > t:
        return None
    schedule = []
    for r in range(k):
        for u in range(h):
            schedule.append(((u + r) % t, 0, u))   # NOTE: model is unconstrained in Part 1; 0 is simplest
    return schedule
```

### Part 2

Fix a task $x$ and look only at its own occurrences, in schedule order — this is what the `task_seen[x]`
counter below tracks. Giving its $c$-th occurrence ($c = 0, 1, 2, \dots$) the model $c \bmod m$ is a
round-robin: writing $c = qm + s$ with $0 \le s < m$, models $0, \dots, s-1$ have each been used $q + 1$
times and models $s, \dots, m-1$ have each been used $q$ times, so the counts differ by at most 1 — for
every $c$, i.e. at every prefix, not only when $c$ is a multiple of $m$.

```python
def build_balanced_schedule(t, m, h, k):
    if t <= 0 or m <= 0 or h <= 0:
        return None
    if k == 0:
        return []
    if k > t:
        return None
    task_seen = [0] * t
    schedule = []
    for r in range(k):
        for u in range(h):
            task = (u + r) % t
            model = task_seen[task] % m          # NOTE: task_seen[task] is x's occurrence count so far
            task_seen[task] += 1
            schedule.append((task, model, u))
    return schedule
```

### Part 3

**Lemma.** If a sequence of increments always adds 1 to whichever of $m$ counters, all starting at 0,
currently has the smallest value (ties broken any way), then after every prefix of the sequence the
counters differ by at most 1.

*Proof.* By induction on the number of increments. Initially every counter is 0. Suppose that before some
increment, every counter's value is either $L$ or $L + 1$, where $L$ is the current minimum (the base
case has $L = 0$). The counter chosen for the increment has value $L$, since it is a minimum; after the
increment it becomes $L + 1$, and every other counter is unchanged, so its value is still $L$ or $L + 1$.
Hence every counter's value is $L$ or $L + 1$ afterward too, and the difference stays at most 1.

Keep Part 2's round order — task $(u + r) \bmod t$ for human $u$ in round $r$ — but choose the model with
the lemma: for the assignment on task $x$ by human $u$, pick the model minimizing $x$'s own current
count, breaking ties by $u$'s own current count and then by model index. Applying the lemma to each
task's counters, which change only when that task is scheduled and always by incrementing one of their
own minimums, shows balance by task holds at every prefix — for any tie-break rule, unlike Part 2's one
specific cyclic order.

```python
def build_doubly_balanced_schedule(t, m, h, k):
    if t <= 0 or m <= 0 or h <= 0:
        return None
    if k == 0:
        return []
    if k > t:
        return None
    task_count = [[0] * m for _ in range(t)]
    human_count = [[0] * m for _ in range(h)]
    schedule = []
    for r in range(k):
        for u in range(h):
            task = (u + r) % t
            # NOTE: argmin over the task's own counts first; the human's counts only break ties,
            # so they can lose every tie and the human axis stays unprotected (see the text above).
            model = min(range(m), key=lambda i: (task_count[task][i], human_count[u][i], i))
            task_count[task][model] += 1
            human_count[u][model] += 1
            schedule.append((task, model, u))
    return schedule
```

Balance by human is not guaranteed, and not only because of a bad tie-break. With $t = 2$, $m = 3$,
$h = 6$, $k = 2$, human 4's two assignments both land on model 2. The first is on task 0, whose counts
are $(1, 1, 0)$ at that point, so the argmin is uniquely model 2; the second, a round later, is on task
1, whose counts are then $(2, 2, 1)$, so the argmin is again uniquely model 2. Neither step has a tie to
break, so no tie-break rule could have sent human 4 to a different model either time; its final counts
are $(0, 0, 2)$, a difference of 2. The failure belongs to this greedy rule, not to the task: for the same
parameters a schedule that is balanced by task and by human does exist (it is checked in the code below).

### Follow-ups

- Swapping the priority (a human's own counts first, a task's counts second) is symmetric: it certifies
  balance by human instead, at the cost of the same kind of failure on the task axis.
- If tasks stream in day by day instead of arriving all at once, keep `task_count`, `human_count` and
  each human's running total across days instead of rebuilding them, and cap every human to one
  assignment per day as an extra rule layered on the same balance requirements.
- Parts 1 and 2 run in $O(h k)$ time; Part 3's per-step argmin over $m$ models makes it $O(h k m)$, or
  $O(h k \log m)$ with a per-task and per-human min-heap.

<details>
<summary>Checks (runnable)</summary>

```python
from collections import Counter
from itertools import product


def verify_schedule(schedule, t, m, h, k, task_balance=False, human_balance=False):
    """Checks every prefix of `schedule`, not only the final counts."""
    seen_pairs = set()
    task_model = [Counter() for _ in range(t)]
    human_model = [Counter() for _ in range(h)]
    human_total = Counter()
    for step, (task, model, human) in enumerate(schedule):
        assert 0 <= task < t and 0 <= model < m and 0 <= human < h
        pair = (task, human)
        assert pair not in seen_pairs, f"duplicate {pair} at step {step}"
        seen_pairs.add(pair)
        task_model[task][model] += 1
        human_model[human][model] += 1
        human_total[human] += 1
        if task_balance:
            counts = [task_model[task][i] for i in range(m)]
            assert max(counts) - min(counts) <= 1, (task, counts, step)
        if human_balance:
            counts = [human_model[human][i] for i in range(m)]
            assert max(counts) - min(counts) <= 1, (human, counts, step)
    assert all(human_total[u] >= k for u in range(h))
    return True


# Exhaustive sweep over small (t, m, h, k): the None / [] / list contract, the minimal length h * k,
# and every prefix of the schedule returned by each of the three builders.
for t, m, h, k in product(range(0, 5), range(0, 4), range(0, 4), range(0, 6)):
    infeasible = t <= 0 or m <= 0 or h <= 0 or (k > 0 and k > t)
    for build, kwargs in (
        (build_basic_schedule, {}),
        (build_balanced_schedule, {"task_balance": True}),
        (build_doubly_balanced_schedule, {"task_balance": True}),   # human_balance not claimed here
    ):
        result = build(t, m, h, k)
        if infeasible:
            assert result is None
            continue
        if k == 0:
            assert result == []
            continue
        assert len(result) == h * k
        verify_schedule(result, t, m, h, k, **kwargs)


def brute_force_feasible(t, h, k):
    """Ignores models (Part 1 never constrains them) and searches every subset of the (task, human)
    grid for one where each human's subset-degree is >= k, independently of the round construction."""
    cells = [(x, u) for x in range(t) for u in range(h)]
    for mask in range(1 << len(cells)):
        counts = Counter(u for i, (_, u) in enumerate(cells) if mask & (1 << i))
        if all(counts[u] >= k for u in range(h)):
            return True
    return False


for t, h, k in product(range(1, 5), range(1, 4), range(0, 6)):
    assert brute_force_feasible(t, h, k) == (k <= t)

# Part 3's greedy is certified balanced by task (the lemma) but not by human: a concrete counterexample.
bad = build_doubly_balanced_schedule(2, 3, 6, 2)
failed = False
try:
    verify_schedule(bad, 2, 3, 6, 2, task_balance=True, human_balance=True)
except AssertionError:
    failed = True
assert failed
verify_schedule(bad, 2, 3, 6, 2, task_balance=True)  # task balance alone still holds throughout

human4_steps = [(i, a) for i, a in enumerate(bad) if a[2] == 4]
assert human4_steps == [(4, (0, 2, 4)), (10, (1, 2, 4))]
assert [mm for _, (_, mm, _) in human4_steps] == [2, 2]

# Replay the same computation to confirm neither of human 4's two steps had a tie to break.
task_count = [[0, 0, 0] for _ in range(2)]
for step, (task, model, human) in enumerate(bad):
    counts = task_count[task]
    if step in (4, 10):
        best = min(counts)
        assert counts.count(best) == 1 and counts.index(best) == model
    task_count[task][model] += 1

# For the same parameters a schedule balanced by task AND by human exists: shift each task's models by one per round.
both = [((u + r) % 2, (u // 2 + r) % 3, u) for r in range(2) for u in range(6)]
verify_schedule(both, 2, 3, 6, 2, task_balance=True, human_balance=True)
```

</details>

</details>
