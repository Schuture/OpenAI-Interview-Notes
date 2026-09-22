# 数据标注任务调度

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★★☆ | 中等 | SWE · RE · MLE | scheduling, greedy, fairness | 3 个部分 |
<!-- meta:end -->

## 题目

共有 $t$ 个任务，编号 $0, 1, \dots, t-1$；$m$ 个模型，编号 $0, \dots, m-1$；$h$ 个人类标注员，编号
$0, \dots, h-1$。给一个任务打标签，就是把某个模型在这个任务上的输出展示给一个标注员，请他打分。
一个*分配*（assignment）是一个三元组 $(\mathrm{task}, \mathrm{model}, \mathrm{human})$，记录一次这样的评审。
*调度*（schedule）是一个有序列表 $S = (a_0, a_1, \dots, a_{L-1})$，其中每个分配 $a_j = (\mathrm{task}_j,
\mathrm{model}_j, \mathrm{human}_j)$，顺序就是平台把这些评审派发出去的先后次序。顺序是有意义的：下面每一条规则
都是针对 $S$ 的每个*前缀*陈述的——对 $0 \le p \le L$，长度为 $p$ 的前缀是 $S[:p] = (a_0, \dots, a_{p-1})$。

另给定一个整数 $k \ge 0$。下面每个 Part 都共享两条基本规则：

- **覆盖（coverage）。** 对每个标注员 $u$，$S$ 中满足 $\mathrm{human}_j = u$ 的分配至少有 $k$ 个。
- **唯一（uniqueness）。** 任意两个分配不能同时任务相同且标注员相同：对 $i \ne j$，
  $(\mathrm{task}_i, \mathrm{human}_i) \ne (\mathrm{task}_j, \mathrm{human}_j)$。

每个 Part 都还要求调度的分配数量尽可能少。

### Part 1 —— 覆盖与唯一

实现 `build_basic_schedule`。这一问不限制模型的选取。

```py
from typing import List, Optional, Tuple
Assignment = Tuple[int, int, int]  # (task, model, human)

def build_basic_schedule(t: int, m: int, h: int, k: int) -> Optional[List[Assignment]]:
    """Returns None if t <= 0, m <= 0, or h <= 0 (invalid dimensions, regardless of k). Otherwise
    returns [] if k == 0, or None if k > t (infeasible). Otherwise
    returns a schedule of exactly h * k assignments satisfying coverage and uniqueness."""
```

例子，取 $t = 2$、$m = 2$、$h = 3$、$k = 2$：一个合法的调度是

```text
(0, 0, 0), (1, 0, 1), (0, 0, 2), (1, 0, 0), (0, 0, 1), (1, 0, 2)
```

每个标注员恰好出现两次，两个任务各做一次；模型始终是 0，这一问是允许的。

### Part 2 —— 按任务均衡

对前缀 $S[:p]$、任务 $x$ 和模型 $i$，记

$$c_p(x, i) = \sum_{j=0}^{p-1} [\mathrm{task}_j = x \text{ 且 } \mathrm{model}_j = i]$$

为这个前缀里模型 $i$ 在任务 $x$ 上被使用过的次数。如果对每个前缀 $p$ 和每个任务 $x$ 都有

$$\max_i c_p(x, i) - \min_i c_p(x, i) \le 1 ,$$

（最大值和最小值取遍全部 $m$ 个模型），就称这个调度*按任务均衡*。实现 `build_balanced_schedule`，
返回一个同时满足覆盖、唯一、按任务均衡的调度。

```py
def build_balanced_schedule(t: int, m: int, h: int, k: int) -> Optional[List[Assignment]]:
    """Same feasibility contract as build_basic_schedule. The returned schedule is also balanced
    by task at every prefix, with exactly h * k assignments."""
```

例子，$t, m, h, k$ 与 Part 1 相同：一个最短的均衡调度是

```text
(0, 0, 0), (1, 0, 1), (0, 1, 2), (1, 1, 0), (0, 0, 1), (1, 0, 2)
```

任务 0 出现在位置 0、2、4，它的各模型计数依次是 $(1, 0) \to (1, 1) \to (2, 1)$，差值从未超过 1；
任务 1 的情况完全一样。

### Part 3 —— 在标注员维度上也均衡

对标注员 $u$，按与上面 $c_p(x, i)$ 完全相同的方式定义 $c_p(u, i)$，只是统计对象换成满足
$\mathrm{human}_j = u$ 且 $\mathrm{model}_j = i$ 的分配。如果对每个前缀 $p$ 和每个标注员 $u$ 都有
$\max_i c_p(u, i) - \min_i c_p(u, i) \le 1$，就称这个调度*按标注员均衡*。

实现 `build_doubly_balanced_schedule`：必须与 Part 2 一样保持覆盖、唯一、按任务均衡，此外还要尝试用一条
自选的贪心规则同时做到按标注员均衡——每一步都根据当前的计数为下一个分配选取模型。然后判断你选的规则是否
真的能让按标注员均衡在任意 $t, m, h, k$ 下的任意前缀都成立：给出证明，或者找出你能找到的最小反例——参数，
以及它失败的那个前缀。

```py
def build_doubly_balanced_schedule(t: int, m: int, h: int, k: int) -> Optional[List[Assignment]]:
    """Same feasibility contract and minimal length h * k as build_balanced_schedule, and always
    balanced by task. Attempts, via a greedy rule, to also be balanced by human."""
```

例子，取 $t = 2$、$m = 3$、$h = 4$、$k = 2$：下面这个调度同时按任务均衡、按标注员均衡：

```text
(0, 0, 0), (1, 0, 1), (0, 1, 2), (1, 1, 3), (1, 2, 0), (0, 2, 1), (1, 0, 2), (0, 0, 3)
```

任务 0 一共出现四次，在位置 0、2、5、7，依次用模型 0、1、2、0；每个标注员自己的两个模型也都互不相同。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前有两点值得向面试官确认：均衡条件是要求在任意前缀都成立，还是只要求在调度结束时成立（下文用的是更强的、
按前缀的版本，Part 2 的论证正是因为这一点才不平凡）；以及重复标注是按 (task, human) 这一对禁止（下文的假设），
还是按完整的 (task, model, human) 三元组禁止——后者会允许同一个标注员在不同模型下再看一次同一个任务。

### Part 1

唯一性不允许两个分配同时任务相同、标注员相同，所以单个标注员最多只能出现在 $t$ 个分配里，每个任务至多一次。
覆盖条件因此要求 $k \le t$；这个条件也是充分的。当维度合法（$t, m, h > 0$）时，`build_basic_schedule` 在
$k = 0$ 时返回 `[]`，在 $k > t$ 时返回 `None`；只要有一个维度不合法（$t \le 0$、$m \le 0$ 或 $h \le 0$），
不论 $k$ 取什么值都返回 `None`。

每个分配都恰好让某一个标注员的计数加 1，所以要让全部 $h$ 个标注员都达到覆盖要求，至少需要 $h \cdot k$ 个分配；
让每个标注员都恰好拿到 $k$ 个、不多不少的调度，因此就是最短的。第 $r = 0, \dots, k-1$ 轮给标注员 $u$
分配任务 $(u + r) \bmod t$：因为 $r$ 取遍 $k \le t$ 个连续的剩余类，同一个标注员拿到的 $k$ 个任务两两不同，
唯一性成立；而经过这 $k$ 轮，每个标注员也恰好拿到了 $k$ 个任务。

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

固定一个任务 $x$，只看它自己在调度中出现的那些位置——这正是下面代码里 `task_seen[x]` 计数器在追踪的东西。
给它的第 $c$ 次出现（$c = 0, 1, 2, \dots$）分配模型 $c \bmod m$，就是一个轮转：把 $c$ 写成 $c = qm + s$、
$0 \le s < m$，模型 $0, \dots, s-1$ 各被用过 $q + 1$ 次，模型 $s, \dots, m-1$ 各被用过 $q$ 次，
所以计数之差不超过 1——对每一个 $c$ 都成立，也就是在每个前缀都成立，不只是 $c$ 是 $m$ 的倍数的时候。

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

**引理。** 有 $m$ 个计数器，初始都是 0；如果每次增量总是加到当前值最小的那个计数器上（并列时任意打破），
那么在这个过程的任意前缀之后，计数器之间的差值都不超过 1。

*证明。* 对增量次数做归纳。一开始所有计数器都是 0。假设在某次增量之前，每个计数器的值都是 $L$ 或 $L + 1$，
其中 $L$ 是当前的最小值（初始情形 $L = 0$）。被选中做增量的那个计数器的值是 $L$，因为它是一个最小值；
增量之后它变成 $L + 1$，其余计数器都不变，值仍然是 $L$ 或 $L + 1$。所以增量之后，每个计数器的值仍然是
$L$ 或 $L + 1$，差值维持在 1 以内。

沿用 Part 2 的轮次顺序——第 $r$ 轮给标注员 $u$ 分配任务 $(u + r) \bmod t$——但用引理来选模型：对标注员 $u$
在任务 $x$ 上的这次分配，选择让 $x$ 自己当前计数最小的模型，并列时先看 $u$ 自己当前的计数，再看模型下标。
把引理分别应用到每个任务自己的计数器上——它们只在这个任务被调度时才变化，而且每次变化都是把自己当前的某个
最小值加 1——就说明按任务均衡在任意前缀都成立，而且对任何并列时的打破方式都成立，不像 Part 2 那样依赖
某一种固定的轮转顺序。

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

按标注员均衡并不成立，而且不只是打破并列的方式不好。取 $t = 2$、$m = 3$、$h = 6$、$k = 2$，标注员 4 的
两次分配都落在模型 2 上。第一次是任务 0，当时的计数是 $(1, 1, 0)$，最小值唯一地在模型 2；第二次是一轮之后
的任务 1，当时的计数是 $(2, 2, 1)$，最小值又唯一地在模型 2。这两步都没有并列可打破，所以无论用什么样的
打破并列的规则，都没法让标注员 4 在这两次分配里换一个模型；它最终的计数是 $(0, 0, 2)$，差值为 2。
失败的是这条贪心规则，而不是题目本身：对同一组参数，同时按任务、按标注员均衡的调度是存在的（验证代码里检查了一个）。

### 追问

- 把优先级换过来（先看标注员自己的计数，再看任务的计数）是对称的：这样能保证按标注员均衡，
  代价是在任务这个维度上可能出现同样类型的失败。
- 如果任务是逐天到来的，而不是一次性给出，就把 `task_count`、`human_count` 和每个标注员的累计次数
  跨天保留下来，不必重新构建；再加一条规则，要求每个标注员每天至多做一个任务，叠加在同样的均衡要求之上。
- Part 1、Part 2 的时间是 $O(hk)$；Part 3 每一步要在 $m$ 个模型上取最小值，时间变成 $O(hkm)$，
  用一个按任务、按标注员各建一个的最小堆可以降到 $O(hk \log m)$。

<details>
<summary>验证代码（可运行）</summary>

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
