# 应届生在线测评（OA）

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 在线测评 | ★☆☆☆☆ | 简单 | SWE | graph, counting, simulation, dp | 4 independent parts |
<!-- meta:end -->

## 题目

四道相互独立的题目，由系统自动评测，隐藏测试用例；各部分之间没有依赖。每部分都按给定签名实现为一个函数。

### Part 1 —— 函数图上游走的终点

一个*有向图*（directed graph）的节点用整数标识（不一定连续，可以为负），*边*（edge）`u -> v` 连接两个不同的节点。
图中每个节点至多有一条出边，所以边用两个等长列表给出：第 `i` 条边从 `from_ids[i]` 指向 `to_ids[i]`，
`from_ids` 中的值两两不同。只出现在 `to_ids` 中、或两个列表都没出现的节点没有出边。

从节点 `start` 出发的*游走*（walk）是节点序列 `w_0 = start, w_1, w_2, ...`，其中 `w_{t+1}` 是离开 `w_t` 的
那条唯一边的终点。游走在第一个满足下列任一条件的 `w_t` 处停止：

- `w_t` 没有出边；
- 离开 `w_t` 的边的终点 `w` 已经出现在 `w_0, ..., w_t` 中。

返回这个最后的节点 `w_t`。第二种情形下，它是游走即将闭合成环之前的那个节点，而不是环的入口。

```py
def walk_end(from_ids: list[int], to_ids: list[int], start: int) -> int:
    """len(from_ids) == len(to_ids) <= 2 * 10**5; from_ids are distinct; from_ids[i] != to_ids[i]."""
```

例子：边为 `7 -> 12`、`12 -> 40`、`40 -> 3`、`3 -> 12`、`90 -> 7`。

```text
walk_end(..., 90) -> 3    游走：90, 7, 12, 40, 3；3 的出边指回已访问过的 12
walk_end(..., 3)  -> 40   游走：3, 12, 40；40 的出边指回 3
walk_end(..., 55) -> 55   节点 55 没有出边
```

### Part 2 —— 覆盖四种类型的四点路径

一个无向简单图（没有自环，没有重边）的节点为 `0, ..., n - 1`，边表 `edges` 由无序点对组成。
节点 `v` 带有一个*类型*（type）`types[v]`，取值于 `{0, 1, 2, 3}`。

*4 点路径*（4-path）是由四个两两不同的节点组成的序列 `(v_1, v_2, v_3, v_4)`，并且对 `i = 1, 2, 3`，
`v_i` 与 `v_{i+1}` 相邻。如果 `types[v_1], ..., types[v_4]` 恰好是 `0, 1, 2, 3` 的一个排列（每个数各出现一次），
就称它*覆盖*（covering）全部类型。序列是有序的：`(v_1, v_2, v_3, v_4)` 与它的反向序列 `(v_4, v_3, v_2, v_1)`
算作两条不同的 4 点路径。返回覆盖全部类型的 4 点路径的条数。

```py
def count_typed_paths(n: int, edges: list[tuple[int, int]], types: list[int]) -> int:
    """1 <= n <= 50, len(edges) <= 250, types[v] in {0, 1, 2, 3}. Returns the number of ordered
    4-node paths whose four nodes have four different types."""
```

例子：`n = 6`，`types = [0, 1, 2, 3, 0, 3]`，`edges = [(0,1), (1,2), (2,3), (3,4), (2,5), (4,1)]`。
答案是 `14`：不计方向共有七条覆盖路径，即 `(0,1,2,3)`、`(0,1,2,5)`、`(4,1,2,3)`、`(4,1,2,5)`、`(1,2,3,4)`、
`(2,1,4,3)`、`(2,3,4,1)`，每条连同它的反向序列各算一次。序列 `(0,1,4,3)` 不覆盖，因为 `4` 与 `0` 类型相同。

### Part 3 —— 直线上的邻居吞食

`families` 是一个字符串，`sizes` 是等长（`m <= 20`）的正整数列表。第 `i` 个生物（从 0 开始，自左向右）属于
家族 `families[i]`，大小为 `sizes[i]`。模拟按*轮*（round）进行；每一轮都基于该轮开始时的队列，大小取该时刻的值。

在一轮中，按 `i = 0, 1, ..., m - 1` 的顺序依次处理各位置。每个生物要么是*空闲*（free）的，要么是*已参与*（used）的；
开始时全部空闲，一个生物在吞食他人或被吞食时变为已参与。处理位置 `i` 时：

1. 若生物 `i` 已参与，什么也不做。
2. 否则，称一个邻居 `j`（`j = i - 1` 或 `j = i + 1`，若存在）是*可吞食的*（edible），当且仅当它空闲、
   与生物 `i` 属于不同家族，并且大小严格小于生物 `i`。
3. 若左邻居可吞食，生物 `i` 吞食它；否则若右邻居可吞食，生物 `i` 吞食右邻居；否则什么也不做。
   `i` 吞食 `j` 后，两者都变为已参与，`j` 将被移除。

一轮结束时，把所有被吞食的生物从队列中移除，每个吞食者的大小增加它所吞食生物的大小。若这一轮至少发生了
一次吞食，就在新队列上开始下一轮；否则模拟结束。以 `"<family> <size>"` 的形式返回最大生物的家族与大小；
若有多个生物并列最大，取最左边的。

```py
def last_standing(families: str, sizes: list[int]) -> str:
    """1 <= len(families) == len(sizes) <= 20, families are letters, sizes are positive integers.
    Returns "<family> <size>" of the largest organism once no eating event can occur."""
```

例子：`families = "ABABBCA"`，`sizes = [4, 2, 5, 3, 1, 6, 2]`。

```text
Round 1   line: A4 B2 A5 B3 B1 C6 A2
  i=0  A4: no left neighbour; right B2 is free, other family, smaller      -> A4 eats B2
  i=1  B2: used
  i=2  A5: left B2 is used; right B3 is free, other family, smaller         -> A5 eats B3
  i=3  B3: used
  i=4  B1: left B3 is used; right C6 is larger                             -> nothing
  i=5  C6: left B1 is free, other family, smaller                          -> C6 eats B1
  i=6  A2: left C6 is used; no right neighbour                             -> nothing
  new line: A6 A8 C7 A2           (A2 was also edible for C6, but the left neighbour has priority)
Round 2   line: A6 A8 C7 A2
  i=0  A6: right A8 is the same family                                     -> nothing
  i=1  A8: left is the same family; right C7 is free, other family, smaller -> A8 eats C7
  i=2  C7: used
  i=3  A2: left C7 is used                                                 -> nothing
  new line: A6 A15 A2
Round 3   no event; stop.
last_standing("ABABBCA", [4, 2, 5, 3, 1, 6, 2]) == "A 15"
```

### Part 4 —— 最便宜的咖啡豆计划

一家咖啡馆计划 `n` 天。每天恰好供应三种咖啡豆之一，编号 `0, 1, 2`；第 `d` 天供应豆 `b` 的成本是 `costs[d][b]`。
连续两天不能供应同一种豆。一个计划的*总成本*是各天成本之和。返回总成本最小的计划，用每天所选豆的编号列表表示。
输入保证总成本最小的计划唯一。

```py
def cheapest_blends(costs: list[list[int]]) -> list[int]:
    """1 <= len(costs) <= 10**5, costs[d] has 3 entries, 1 <= costs[d][b] <= 10**9. Returns the blend
    chosen on each day in a plan of minimum total cost; that plan is unique."""
```

例子：`costs = [[4, 7, 3], [6, 2, 5], [3, 8, 1], [5, 4, 9]]` 的答案是 `[2, 1, 2, 1]`，总成本
`3 + 2 + 1 + 4 = 10`；次优计划 `[2, 1, 2, 0]` 的成本是 11。

## 参考解答

<details>
<summary>展开参考解答</summary>

编码前分部分值得确认的点：Part 1 中游走遇到已访问节点时返回哪个节点（返回当前节点，而不是重复出现的那个），
以及 `start` 本身可能没有出边；Part 2 中一条路径与它的反向序列分别计数；Part 3 中大小在每轮开始时比较、
左邻居优先；Part 4 中最小计划唯一，因此无需额外的并列规则。

### Part 1

用字典按起点索引各条边，模拟游走并记录已访问节点集合。每个节点至多加入一次，所以时间是 O(E)。

```python
def walk_end(from_ids: list[int], to_ids: list[int], start: int) -> int:
    """len(from_ids) == len(to_ids) <= 2 * 10**5; from_ids are distinct; from_ids[i] != to_ids[i]."""
    next_of = dict(zip(from_ids, to_ids))  # warning: ids are arbitrary integers, so a dict, not a list indexed by id
    visited = {start}
    current = start
    while current in next_of:  # no outgoing edge: the walk ends here
        following = next_of[current]
        if following in visited:  # warning: return `current`, the node before the repeat, not `following`
            return current
        visited.add(following)
        current = following
    return current  # warning: also covers a start node that has no outgoing edge
```

### Part 2

固定路径中间的那条边 `(b, c)`，两个方向都要考虑。两个端点必须提供 `b` 和 `c` 所没有的那两种类型，所以只有类型
重要：设 `x`、`y` 是缺少的两种类型。要么第一个节点类型为 `x`、最后一个类型为 `y`，要么相反。记 `nbr_count[v][t]`
为 `v` 的类型为 `t` 的邻居个数，则以 `(b, c)` 为中间边的这类路径条数为

```text
nbr_count[b][x] * nbr_count[c][y] + nbr_count[b][y] * nbr_count[c][x]
```

四种类型互不相同，所以两个端点既不会彼此重合，也不会与 `b`、`c` 重合，无需做减法。对每条边的两个方向求和，
总时间 O(n + E)。对全部 n^4 个四元组暴力枚举在 n = 50 时（约 600 万个四元组）也是可行的；对“已用类型集合”做
动态规划是另一种标准做法，上面的公式最短。

```python
def count_typed_paths(n: int, edges: list[tuple[int, int]], types: list[int]) -> int:
    """1 <= n <= 50, len(edges) <= 250, types[v] in {0, 1, 2, 3}. Returns the number of ordered
    4-node paths whose four nodes have four different types."""
    # we fix the middle edge (b, c); the two end nodes must have the two types x, y that b and c miss
    # so the count is nbr_count[b][x] * nbr_count[c][y] + nbr_count[b][y] * nbr_count[c][x]
    # first count, for every node, its neighbours of each type
    nbr_count = [[0] * 4 for _ in range(n)]  # (n, 4), nbr_count[v][t]: number of neighbours of v whose type is t
    for u, v in edges:
        nbr_count[u][types[v]] += 1
        nbr_count[v][types[u]] += 1

    # then sum over every middle edge
    n_paths = 0
    for u, v in edges:
        # warning: both orientations of the middle edge; reversed paths count separately
        for b, c in ((u, v), (v, u)):
            if types[b] == types[c]:
                continue
            x, y = [t for t in range(4) if t != types[b] and t != types[c]]
            # warning: end nodes need no "distinct from b, c" test: their types differ from types[b] and types[c]
            n_paths += nbr_count[b][x] * nbr_count[c][y] + nbr_count[b][y] * nbr_count[c][x]
    return n_paths
```

例子的计算过程（`types = [0, 1, 2, 3, 0, 3]`）：中间边 `{1, 2}` 的类型是 1 和 2，缺少类型 0 和 3。节点 1 有两个
类型为 0 的邻居（0 和 4），没有类型为 3 的邻居；节点 2 有两个类型为 3 的邻居（3 和 5），没有类型为 0 的邻居，
所以每个方向贡献 `2*2 + 0*0 = 4`，合计 8。中间边 `{2, 3}`、`{1, 4}`、`{3, 4}` 各贡献 2，`{0, 1}`、`{2, 5}` 贡献 0，
总和为 14。

### Part 3

最多 20 个生物，且有吞食事件的每一轮至少移除一个生物，所以至多 19 轮有事件的轮次，每轮 O(m) 工作量：
直接模拟就够了。规则用 `taken` 标记数组逐字实现；由于每个变大的生物都已参与（`taken`），在每轮开始时比较大小
与比较当前大小等价，增长可以在该轮结束时再应用。

```python
def last_standing(families: str, sizes: list[int]) -> str:
    """1 <= len(families) == len(sizes) <= 20, families are letters, sizes are positive integers.
    Returns "<family> <size>" of the largest organism once no eating event can occur."""
    # we simulate round by round: at most 19 eventful rounds of O(n) work
    family, size = list(families), list(sizes)  # we copy the inputs
    while True:
        n_alive = len(family)
        taken = [False] * n_alive  # has taken part in an eating event this round
        gain = [0] * n_alive
        eaten = [False] * n_alive
        any_event = False
        # first find this round's eating events
        for i in range(n_alive):
            if taken[i]:
                continue
            # warning: left neighbour is tried first; `taken` already reflects events earlier in this same round
            for j in (i - 1, i + 1):
                if 0 <= j < n_alive and not taken[j] and family[j] != family[i] and size[j] < size[i]:
                    taken[i] = taken[j] = True
                    gain[i] = size[j]
                    eaten[j] = True
                    any_event = True
                    break
        if not any_event:
            break
        # then apply them
        # warning: sizes change only here, after the round; a grown eater is `taken`, so nobody compared against it
        family, size = (
            [family[i] for i in range(n_alive) if not eaten[i]],
            [size[i] + gain[i] for i in range(n_alive) if not eaten[i]],
        )
    best = max(range(len(family)), key=lambda i: (size[i], -i))  # warning: -i makes the leftmost win a tie
    return f"{family[best]} {size[best]}"
```

### Part 4

设 `best[d][b]` 是前 `d + 1` 天（第 `0..d` 天）在第 `d` 天供应豆 `b` 时的最小成本。则
`best[0][b] = costs[0][b]`，当 `d >= 1` 时

```text
best[d][b] = costs[d][b] + min(best[d-1][q] for q != b)
```

答案的成本是最后一行的最小值。还原计划时，为每个状态保存取得最小值的前驱豆，从最优的最后一天出发向前回溯。
时间与空间都是 O(n)（每天三个值）。

```python
def cheapest_blends(costs: list[list[int]]) -> list[int]:
    """1 <= len(costs) <= 10**5, costs[d] has 3 entries, 1 <= costs[d][b] <= 10**9. Returns the blend
    chosen on each day in a plan of minimum total cost; that plan is unique."""
    # best[d][b] = costs[d][b] + min(best[d-1][q] for q != b)
    # we store the predecessor of each state and walk back from the best final blend
    n_days = len(costs)
    best = [list(costs[0])]  # (n_days, 3), best[d][b]: cheapest cost of days 0..d if day d uses blend b
    came_from = [[-1, -1, -1]]  # (n_days, 3)
    for d in range(1, n_days):
        best_row, back_row = [], []
        for b in range(3):
            prev = min((q for q in range(3) if q != b), key=lambda q: best[d - 1][q])
            best_row.append(costs[d][b] + best[d - 1][prev])
            # warning: store the predecessor; recomputing it later would need the whole table anyway
            back_row.append(prev)
        best.append(best_row)
        came_from.append(back_row)

    b = min(range(3), key=lambda q: best[-1][q])
    plan = [b]
    # warning: iterative walk back; n = 10**5 would overflow Python's recursion limit
    for d in range(n_days - 1, 0, -1):
        b = came_from[d][b]
        plan.append(b)
    plan.reverse()
    return plan
```

### 追问

- Part 1 在同一张图上有很多个起点：沿游走路径做记忆化，每个节点的答案只算一次。
- Part 2 推广到 `k` 种类型、`k` 个节点的路径：对（节点，已用类型集合）做动态规划。
- Part 3 把吞食顺序改成右邻居优先：哪些输入的结果会改变？
- Part 4 有 `m` 种豆，仍是 O(nm)：保留前一天最小的两个值。

<details>
<summary>检查（可运行）</summary>

```python
import random
from itertools import permutations, product

# Examples from the statement
assert walk_end([7, 12, 40, 3, 90], [12, 40, 3, 12, 7], 90) == 3
assert walk_end([7, 12, 40, 3, 90], [12, 40, 3, 12, 7], 7) == 3
assert walk_end([7, 12, 40, 3, 90], [12, 40, 3, 12, 7], 12) == 3
assert walk_end([7, 12, 40, 3, 90], [12, 40, 3, 12, 7], 3) == 40
assert walk_end([7, 12, 40, 3, 90], [12, 40, 3, 12, 7], 55) == 55
assert walk_end([], [], 0) == 0
assert walk_end([5, 8], [8, -2], 5) == -2

ex_types = [0, 1, 2, 3, 0, 3]
ex_edges = [(0, 1), (1, 2), (2, 3), (3, 4), (2, 5), (4, 1)]
assert count_typed_paths(6, ex_edges, ex_types) == 14
assert count_typed_paths(1, [], [0]) == 0

assert last_standing("ABABBCA", [4, 2, 5, 3, 1, 6, 2]) == "A 15"
assert last_standing("XYXY", [3, 3, 3, 3]) == "X 3"
assert last_standing("PQP", [5, 2, 4]) == "P 7"
assert last_standing("Q", [9]) == "Q 9"

ex_costs = [[4, 7, 3], [6, 2, 5], [3, 8, 1], [5, 4, 9]]
assert cheapest_blends(ex_costs) == [2, 1, 2, 1]

random.seed(0)


# Part 1: brute force follows the walk with a list
def walk_brute(from_ids, to_ids, start):
    path = [start]
    while True:
        outs = [t for f, t in zip(from_ids, to_ids) if f == path[-1]]
        if not outs or outs[0] in path:
            return path[-1]
        path.append(outs[0])


for _ in range(2000):
    k = random.randint(1, 8)
    ids = random.sample(range(-20, 20), k + 1)
    sources = ids[:k]
    targets = [random.choice([x for x in ids if x != s]) for s in sources]
    start = random.choice(ids + [100])
    assert walk_end(sources, targets, start) == walk_brute(sources, targets, start)
# a long chain: 2 * 10**5 nodes
big = 200000
assert walk_end(list(range(big)), list(range(1, big + 1)), 0) == big
assert walk_end(list(range(big)), list(range(1, big)) + [0], 0) == big - 1


# Part 2: enumerate all 4-tuples of nodes
def paths_brute(n, edges, types):
    adj = [[False] * n for _ in range(n)]
    for u, v in edges:
        adj[u][v] = adj[v][u] = True
    count = 0
    for seq in permutations(range(n), 4):
        if all(adj[seq[i]][seq[i + 1]] for i in range(3)) and sorted(types[v] for v in seq) == [0, 1, 2, 3]:
            count += 1
    return count


for _ in range(300):
    n = random.randint(1, 8)
    pairs = [(u, v) for u in range(n) for v in range(u + 1, n)]
    edges = [e for e in pairs if random.random() < random.choice([0.3, 0.6, 0.9])]
    edges = [e if random.random() < 0.5 else (e[1], e[0]) for e in edges]
    types = [random.randrange(4) for _ in range(n)]
    assert count_typed_paths(n, edges, types) == paths_brute(n, edges, types)
n = 50
all_pairs = [(u, v) for u in range(n) for v in range(u + 1, n)]
random.shuffle(all_pairs)
count_typed_paths(n, all_pairs[:250], [random.randrange(4) for _ in range(n)])


# Part 3: re-implemented from the statement, with sizes read from the start of the round
def eat_brute(families, sizes):
    orgs = [[f, s] for f, s in zip(families, sizes)]
    while True:
        snapshot = [tuple(o) for o in orgs]
        used = set()
        eats = {}
        for i in range(len(snapshot)):
            if i in used:
                continue
            for j in (i - 1, i + 1):
                if 0 <= j < len(snapshot) and j not in used and snapshot[j][0] != snapshot[i][0] \
                        and snapshot[j][1] < snapshot[i][1]:
                    used.update({i, j})
                    eats[i] = j
                    break
        if not eats:
            break
        gone = set(eats.values())
        for i, j in eats.items():
            orgs[i][1] += snapshot[j][1]
        orgs = [o for k, o in enumerate(orgs) if k not in gone]
    top = max(o[1] for o in orgs)
    first = next(o for o in orgs if o[1] == top)
    return f"{first[0]} {first[1]}"


for _ in range(3000):
    m = random.randint(1, 12)
    fams = "".join(random.choice("ABC") for _ in range(m))
    szs = [random.randint(1, 9) for _ in range(m)]
    assert last_standing(fams, szs) == eat_brute(fams, szs)


# Part 4: try every blend sequence without equal neighbours
def plans_brute(costs):
    n = len(costs)
    scored = []
    for seq in product(range(3), repeat=n):
        if all(seq[d] != seq[d + 1] for d in range(n - 1)):
            scored.append((sum(costs[d][seq[d]] for d in range(n)), list(seq)))
    return sorted(scored)


for _ in range(1500):
    n = random.randint(1, 8)
    costs = [[random.randint(1, 10 ** random.choice([1, 3, 9])) for _ in range(3)] for _ in range(n)]
    ranked = plans_brute(costs)
    plan = cheapest_blends(costs)
    assert all(plan[d] != plan[d + 1] for d in range(n - 1))
    assert sum(costs[d][plan[d]] for d in range(n)) == ranked[0][0]
    if len(ranked) == 1 or ranked[0][0] < ranked[1][0]:
        assert plan == ranked[0][1]
assert len(cheapest_blends([[random.randint(1, 10 ** 9) for _ in range(3)] for _ in range(10 ** 5)])) == 10 ** 5
```

</details>

</details>
