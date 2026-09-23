# 感染扩散（网格元胞自动机）

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★★★ | 中等 | SWE · MLE · RE · RS · EM | bfs, simulation, grid | 5 个部分 / 60 分钟 |
<!-- meta:end -->

## 题目

`grid` 是一个由 $R$ 行组成的列表，每一行是含 $C$ 个整数的列表。`grid[r][c]` 是第 $r$ 行、第 $c$ 列那个格子的状态：
`0` 表示*健康*（healthy），`1` 表示*已感染*（infected）。一个格子的*邻居*是紧挨着它的上、下、左、右四个格子中位于网格内的那些，
对角线方向的格子不算邻居。

时间以天为单位推进，第 0 天就是输入的网格。第 $t + 1$ 天的网格，是把规则同时作用在第 $t$ 天网格的所有格子上得到的
（*同步更新，synchronous update*）。因此，在第 $t + 1$ 天才被感染的格子，要到从第 $t + 1$ 天到第 $t + 2$ 天的那一步才开始感染邻居。

本题共五个 Part，每个 Part 在前一个的基础上增加一条规则。

### Part 1 —— 扩散

如果一个健康格在第 $t$ 天至少有一个邻居是已感染的，它就在第 $t + 1$ 天变为已感染。已感染的格子保持已感染。
返回最小的 $t$，使得第 $t$ 天没有健康格；如果不存在这样的一天，返回 `-1`。如果第 0 天就没有健康格（包括空网格），返回 `0`。

```py
def days_until_all_infected(grid: list[list[int]]) -> int:
    """grid[r][c] is 0 (healthy) or 1 (infected); from Part 2 on also 2 (immune). Returns the day, or -1."""
```

例子：第 0 天有两个格子已感染，第 2 天所有格子都已感染，答案是 `2`。

```text
day 0        day 1        day 2
1 0 0 0      1 1 0 0      1 1 1 1
0 0 0 0      1 0 0 1      1 1 1 1
0 0 0 1      0 0 1 1      1 1 1 1
```

### Part 2 —— 免疫格

网格里还可以出现 `2`，表示*免疫*（immune）。免疫格的状态永不改变，也不算作已感染的邻居，所以感染无法穿过它。
任务与 Part 1 相同。如果某个健康格永远不可能被感染，返回 `-1`。

左边的网格里，感染必须绕过免疫格，第 6 天才到达右上角的格子。右边的网格里，最右一列被隔开了，答案是 `-1`。

```text
1 2 0                     1 2 0
0 2 0      -> 6           2 2 0      -> -1
0 0 0
```

### Part 3 —— D 天后康复

给定整数 $D \ge 1$。一个格子被感染满 $D$ 天后康复：变为免疫，不再感染别人。对每个已感染格，记 $t_0$ 为它被感染的那一天；
输入里一开始就已感染的格子取 $t_0 = 0$。从第 $t - 1$ 天到第 $t$ 天的这一步依次分为两个阶段：

1. 康复：所有满足 $t - t_0 \ge D$ 的已感染格变为免疫。
2. 传播：在第 1 阶段之后，凡是至少有一个邻居仍为已感染的健康格，都变为已感染，并记 $t_0 = t$。

返回最小的 $t$，使得第 $t$ 天没有已感染格（如果第 0 天就没有已感染格，返回 `0`）。健康格可以一直留在网格里。

```py
def days_until_outbreak_ends(grid: list[list[int]], D: int) -> int:
    """grid holds 0, 1 or 2, and D >= 1. Returns the first day on which no cell is infected."""
```

例子：只有一行的网格 `1 0 0`，$D = 2$，格子从左到右编号为 0、1、2，答案是 `4`。
如果 $D = 1$，格子 0 在第 1 天还没感染任何人就康复了，答案是 `1`。

```text
day 0:  1 0 0
day 1:  1 1 0    格子 0：1 - 0 < 2，不康复；它感染了格子 1（t0 = 1）
day 2:  2 1 1    格子 0：2 - 0 >= 2，康复；格子 1 感染了格子 2（t0 = 2）
day 3:  2 2 1    格子 1：3 - 1 >= 2，康复；格子 2 没有健康的邻居
day 4:  2 2 2    格子 2：4 - 2 >= 2，康复；没有已感染格了
```

### Part 4 —— 阈值与死亡

这一问有三个版本。

**版本 A：传播阈值。** 给定整数 $K \ge 1$。在第 2 阶段，一个健康格只有在至少 $K$ 个邻居已感染时才会被感染。$K = 1$ 就是 Part 3。
返回值与 Part 3 相同。取 $K = 2$、$D = 2$ 的例子：疫情在第 4 天结束，有三个格子始终没有被感染，因为它们从未在同一天拥有两个已感染的邻居。

```text
day 0      day 1      day 2      day 3      day 4
1 0 1      1 1 1      2 1 2      2 2 2      2 2 2
0 0 0      1 0 0      1 1 0      2 1 0      2 2 0
1 0 0      1 0 0      2 0 0      2 0 0      2 0 0
```

**版本 B：死亡。** 新增状态 `3`，表示*死亡*（dead）。死亡格的状态永不改变，也不感染别人。健康格按 Part 3 的规则被感染；
如果它在被感染的那一刻至少有 $K$ 个已感染的邻居，那么它在 $D$ 天期满时死亡，而不是变为免疫。
这里的 $K$ 是独立的阈值，不必与版本 A 的那个一致。这个计数只在被感染的那一天做一次：已感染格不会被重新检查，
之后新增的已感染邻居既不会让它转为死亡，也不会重置它的 $D$ 天倒计时。返回疫情结束的那一天和死亡格的数量。

**版本 C。** 免疫格、康复、传播阈值和死亡合并在同一个模拟里。

```py
def simulate(grid: list[list[int]], recover_after: int, spread_threshold: int = 1,
             death_threshold: int | None = None) -> tuple[int, int]:
    """recover_after is D. spread_threshold is the K of version A. death_threshold is the K of
    version B, or None when nobody dies. Returns (day on which the outbreak ends, number of dead cells)."""
```

### Part 5 —— 干预

第 0 天在第一步开始之前，你可以烧掉一整行、一整列，或者什么都不烧。被烧的那条线上的每个格子都变为死亡，
无论它原来是什么状态：它不会再被感染，也不会感染别人，并且计入死亡数。之后按 Part 4 版本 C 的规则一直模拟到结束。
返回所能达到的最小死亡总数。

```py
def min_deaths(grid: list[list[int]], recover_after: int, death_threshold: int,
               spread_threshold: int = 1) -> int:
    """Returns the smallest number of dead cells over the R + C + 1 choices."""
```

取 $D = 2$、两个阈值都为 1 的例子，列从左到右编号为 0 到 3：什么都不烧要死 9 个格子，烧掉第 3 列要死 11 个，
烧掉第 2 列要死 4 个，答案是 `4`。

```text
0 0 0 1
0 0 0 1
0 0 1 0
```

其余的规则由你自行设定并说明：烧的时机是否可以推迟到后面某一天、是否允许烧不止一条线、是否允许只烧一条线的一部分。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前先向面试官确认：四邻域还是八邻域；格子如何编码（整数还是字符，免疫是 `2` 还是 `-1`）；Part 3 里同一天内康复是否先于传播，
比较用 $\ge$ 还是 $>$；Part 4 里的 $K$ 是感染的阈值、死亡的阈值，还是两者都是。
五个 Part 共 60 分钟，Part 1 和 Part 2 要写得快、写得简单。

### Part 1–2：多源 BFS

从所有已感染格同时开始做广度优先搜索，也就是把它们全部以距离 0 放进队列。这样一个格子的 BFS 距离就是它到最近的已感染格的距离，
恰好等于它被感染的那一天。BFS 的一层就是一天，答案是最后一层的层号。同时维护尚未到达的健康格数量：减到 0 就停止；
如果队列先空了，返回 `-1`。免疫格永远不会被进入，这就是 Part 2 的全部改动。每个格子最多进队一次，所以时间和空间都是 $O(R \cdot C)$。
每天把整张网格重算一遍更容易写，但最坏情况是 $O((R \cdot C)^2)$，因为免疫格围成的走廊可以让感染持续 $R \cdot C$ 量级的天数。

```python
from collections import Counter, deque

HEALTHY, INFECTED, IMMUNE, DEAD = 0, 1, 2, 3
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))      # NOTE: add the four diagonals for the 8-neighbour variant


def days_until_all_infected(grid):
    if not grid or not grid[0]:
        return 0
    rows, cols = len(grid), len(grid[0])
    reached = [[cell != HEALTHY for cell in row] for row in grid]      # NOTE: the input grid is not modified
    frontier = deque((r, c) for r in range(rows) for c in range(cols) if grid[r][c] == INFECTED)
    healthy = sum(cell == HEALTHY for row in grid for cell in row)

    days = 0
    while frontier and healthy:
        days += 1
        for _ in range(len(frontier)):          # NOTE: exactly one BFS level per day
            r, c = frontier.popleft()
            for dr, dc in STEPS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and not reached[nr][nc]:
                    reached[nr][nc] = True      # immune cells start as reached, so they are never entered
                    healthy -= 1
                    frontier.append((nr, nc))
    return days if healthy == 0 else -1         # NOTE: healthy cells left over are walled off -> -1
```

### Part 3–4：逐天模拟

有了计时器之后，BFS 的层就不够用了。给每个已感染格保存 $t_0$，按题目里的两个阶段逐天模拟。每个格子最多感染 $D$ 天，
每天只需要常数的工作量，所以模拟的代价是 $O(R \cdot C \cdot D)$。Part 4 用的是同一个循环，只是多了两个阈值参数。

单看 Part 3 有一个闭式解。当阈值为 1 且 $D \ge 2$ 时，一个格子在被感染的第二天就会感染它所有健康的邻居，所以感染的推进方式与 Part 2 完全相同。
设 $d_{\max}$ 是被感染到的格子中最大的 BFS 距离，那么最后一个格子在第 $d_{\max}$ 天被感染，在第 $d_{\max} + D$ 天康复，这就是答案。
$D = 1$ 时答案是 1，因为初始的已感染格还没传播就康复了。阈值 $K > 1$ 时闭式解不成立，因为一个格子可能要分几天才凑齐 $K$ 个已感染的邻居。

```python
def simulate(grid, recover_after, spread_threshold=1, death_threshold=None):
    """Returns (day on which the outbreak ends, number of dead cells)."""
    if not grid or not grid[0]:
        return 0, 0
    rows, cols = len(grid), len(grid[0])
    state = [row[:] for row in grid]
    # NOTE: the cells infected in the input carry a timer too, with t0 = 0; they recover on day D
    infected_on = {(r, c): 0 for r in range(rows) for c in range(cols) if state[r][c] == INFECTED}
    doomed = set()
    day = deaths = 0

    while infected_on:
        day += 1
        # Phase 1: recovery.  NOTE: it comes BEFORE the spread of the same day, and the test is >=, not >
        for cell in [cell for cell, since in infected_on.items() if day - since >= recover_after]:
            del infected_on[cell]
            r, c = cell
            state[r][c] = DEAD if cell in doomed else IMMUNE
            deaths += cell in doomed

        # Phase 2: spread.  NOTE: count first, apply afterwards. Writing into `state` while counting
        # would let a cell infected today infect its neighbours today.
        pressure = Counter()                    # healthy cell -> number of infected neighbours
        for r, c in infected_on:                # NOTE: only infected cells count; immune and dead ones do not
            for dr, dc in STEPS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and state[nr][nc] == HEALTHY:
                    pressure[(nr, nc)] += 1
        for (r, c), count in pressure.items():
            if count >= spread_threshold:
                state[r][c] = INFECTED
                infected_on[(r, c)] = day
                if death_threshold is not None and count >= death_threshold:
                    doomed.add((r, c))          # decided now, carried out when the D days are over
    return day, deaths


def days_until_outbreak_ends(grid, D):          # Part 3 is the engine with threshold 1 and no deaths
    return simulate(grid, D)[0]
```

### Part 5

干预只做一次，所以整个决策空间就是 $R + C + 1$ 种选择：什么都不烧，或者烧掉 $R$ 行、$C$ 列中的某一条。
每一种选择就是把网格复制一份、把那条线整条置为 `3`，再跑一遍 Part 4 的模拟；模拟本身不用改，
因为死亡格既不是健康格也不是已感染格，本来就不参与任何事。因此在这些选择里取最小值是精确的，代价为
$O((R + C) \cdot R \cdot C \cdot D)$。烧一条线在烧下去的那一刻就要付出它整条的长度，
所以只有当它能把感染封在网格的一小块里时才划算。按“已感染格最多的那条线”去烧是错的规则：
它把这点长度花在感染已经所在的地方，而不是感染将要去的地方；在题面的那个网格上这条线是第 3 列，
结果比什么都不烧还差。如果烧的时机可以推迟、或者可以烧多次，选择数每天再乘一次 $R + C + 1$，
穷举就要缩减成每天只考虑少数几条候选线。

```python
def min_deaths(grid, recover_after, death_threshold, spread_threshold=1):
    """Part 5: the best of burning nothing and burning one whole row or column on day 0."""
    if not grid or not grid[0]:
        return 0
    rows, cols = len(grid), len(grid[0])
    lines = [[(r, c) for c in range(cols)] for r in range(rows)]
    lines += [[(r, c) for r in range(rows)] for c in range(cols)]
    best = simulate(grid, recover_after, spread_threshold, death_threshold)[1]   # burning nothing
    for line in lines:
        burnt = [row[:] for row in grid]
        for r, c in line:
            burnt[r][c] = DEAD                  # NOTE: a burnt cell counts as a death whatever it was
        rest = simulate(burnt, recover_after, spread_threshold, death_threshold)[1]
        best = min(best, len(line) + rest)      # NOTE: the line itself already costs len(line) deaths
    return best
```

### 追问

- 版本 B 的两个阈值互相独立。死亡阈值不超过传播阈值时，第 0 天之后被感染的格子全部死亡；
  死亡阈值大于 4 时没有格子会死，因为一个格子最多只有四个邻居。
- 用字符而不是整数（`.`、`X`、`I`）：在输入处转换，核心逻辑保持数值化。
- 超大或稀疏的网格：只保存已感染格的集合和前沿；或者把网格切成块，每天结束后交换各块的边界。
- 同时为所有格子统计已感染邻居数，等价于用十字形卷积核做一次二维卷积。

<details>
<summary>验证代码（可运行）</summary>

```python
a = [[1, 0, 0, 0],
     [0, 0, 0, 0],
     [0, 0, 0, 1]]
b = [[1, 2, 0],
     [0, 2, 0],
     [0, 0, 0]]
d = [[1, 0, 1],
     [0, 0, 0],
     [1, 0, 0]]
e = [[0, 0, 0, 1],
     [0, 0, 0, 1],
     [0, 0, 1, 0]]

# Parts 1-2: the examples of the statement and the edge cases
assert days_until_all_infected(a) == 2
assert days_until_all_infected(b) == 6
assert days_until_all_infected([[1, 2, 0], [2, 2, 0]]) == -1
assert days_until_all_infected([[1]]) == 0 and days_until_all_infected([[0]]) == -1
assert days_until_all_infected([]) == 0 and days_until_all_infected([[2, 2]]) == 0

# Part 3
assert days_until_outbreak_ends([[1, 0, 0]], 2) == 4
assert days_until_outbreak_ends([[1, 0, 0]], 1) == 1
assert days_until_outbreak_ends([[0, 0, 0]], 2) == 0
assert days_until_outbreak_ends(a, 3) == 2 + 3          # d_max + D

# Part 4: variant A (the traced example) and variant B
assert simulate(d, 2, spread_threshold=2) == (4, 0)
assert simulate(d, 2, death_threshold=2) == (4, 4)
# a death threshold at or below the spread threshold, then one that no cell can ever reach
assert simulate(d, 2, spread_threshold=2, death_threshold=1)[1] == 3    # all three cells infected later die
assert simulate(d, 2, death_threshold=5)[1] == 0                        # nobody has five neighbours


def burn(grid, line, index):
    return [[DEAD if (r if line == "row" else c) == index else v for c, v in enumerate(row)]
            for r, row in enumerate(grid)]


# Part 5: the example of the statement, and why "burn the most infected line" is the wrong rule
assert simulate(e, 2, death_threshold=1)[1] == 9                        # burning nothing
assert 3 + simulate(burn(e, "col", 3), 2, death_threshold=1)[1] == 11   # the column with two infected cells
assert 3 + simulate(burn(e, "col", 2), 2, death_threshold=1)[1] == 4    # the column that seals the rest off
assert min_deaths(e, 2, 1) == 4
assert min_deaths([[0, 0], [0, 0]], 2, 1) == 0 and min_deaths([], 2, 1) == 0


def naive_min_deaths(grid, D, k_death, k_spread=1):
    """Straight from the statement: a whole-grid rewrite per day, sharing nothing with simulate()."""
    rows, cols = len(grid), len(grid[0])
    options = [[]] + [[(r, c) for c in range(cols)] for r in range(rows)] \
                   + [[(r, c) for r in range(rows)] for c in range(cols)]
    totals = []
    for line in options:
        state = [row[:] for row in grid]
        for r, c in line:
            state[r][c] = DEAD
        age = {(r, c): 0 for r in range(rows) for c in range(cols) if state[r][c] == INFECTED}
        fatal, deaths = set(), len(line)
        while age:
            for cell in list(age):
                age[cell] += 1
                if age[cell] >= D:
                    del age[cell]
                    state[cell[0]][cell[1]] = DEAD if cell in fatal else IMMUNE
                    deaths += cell in fatal
            before = [row[:] for row in state]
            for r in range(rows):
                for c in range(cols):
                    if before[r][c] != HEALTHY:
                        continue
                    n = sum(before[r + dr][c + dc] == INFECTED for dr, dc in STEPS
                            if 0 <= r + dr < rows and 0 <= c + dc < cols)
                    if n >= k_spread:
                        state[r][c], age[(r, c)] = INFECTED, 0
                        if n >= k_death:
                            fatal.add((r, c))
        totals.append(deaths)
    return min(totals)


# every 3x4 grid with two infected cells, against the naive version
cases = 0
for i in range(12):
    for j in range(i + 1, 12):
        g = [[HEALTHY] * 4 for _ in range(3)]
        g[i // 4][i % 4] = g[j // 4][j % 4] = INFECTED
        for days in (1, 2, 3):
            for threshold in (1, 2):
                assert min_deaths(g, days, threshold) == naive_min_deaths(g, days, threshold)
                cases += 1
assert cases == 396
```

</details>

</details>
