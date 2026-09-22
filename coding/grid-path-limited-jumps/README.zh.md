# 最多跳过 K 行的网格最优路径

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 困难 | SWE | dp, grid, counting | 4 个部分 |
<!-- meta:end -->

## 题目

`board` 是一个 $N$ 行 $M$ 列的整数网格（允许负数），行下标 `i`、列下标 `j` 都从 0 开始。一条*路径*
（path）从给定的起始列 `p` 出发，起点是 `(0, p)`；从 `(i, j)` 出发，可以走一次*普通移动*（step）到
`(i+1, j-1)`、`(i+1, j)`、`(i+1, j+1)` 三者中列号落在 `[0, M)` 内的那些，或者使用一次*特殊移动*
（special move）走到 `(i+2, j)`——特殊移动在整条路径里总共最多能用 `K` 次。落点在网格外的移动一律不合法；
特别地，特殊移动永远不能从第 `N - 2` 行发起，因为那样会让 `i + 2` 落到 `N`，超出最后一行。路径在第一次到达第 `N - 1` 行时停止；
当 `N = 1` 时，这一行就是起点本身，路径不走任何一步。记 $v_0, v_1, \dots, v_L$ 为按访问顺序排列的各格子的值
（$v_0 = board[0][p]$，$v_L$ 是第 `N - 1` 行上的值）。路径的*基础分数*（base score）是
$\sum_{t=0}^{L} v_t$。

完成下面四个部分。

### Part 1 —— 最大分数

返回从 `(0, p)` 到第 `N - 1` 行的所有路径中，基础分数的最大值。

```py
def max_score(board: list[list[int]], p: int, K: int) -> int:
    """board has N >= 1 rows and M >= 1 columns, 0 <= p < M, K >= 0. Returns the largest base score."""
```

例子，取

```text
board = [[-3,  1,  4],
         [-1,  4,  4],
         [-3, -2, -3],
         [ 1,  0, -1],
         [ 5,  5,  3]]
```

`p = 0`、`K = 1`：`max_score(board, 0, 1) == 6`，例如由 `(0,0) -> (1,1) -> (3,1) -> (4,0)`
（依次经过 `-3, 4, 0, 5`）取得，它用了一次特殊移动，从第 1 行直接跳到第 3 行。

### Part 2 —— 还原一条路径

返回一条取得最大基础分数的路径，用它经过的格子列表表示：`[(0, p), ..., (N - 1, ·)]`。如果有多条路径
都取得最大值，把它们经过的格子列表按通常的字典序比较——先比较第一个格子这个 `(row, column)` 元组，
再比较第二个，依此类推——返回其中最小的一条。

```py
def optimal_path(board: list[list[int]], p: int, K: int) -> list[tuple[int, int]]:
    """Same input as max_score. Returns the lexicographically smallest cell list among the
    paths that attain the maximum base score."""
```

例子：在上面的 `board` 上取 `p = 0`、`K = 1`，有两条路径都取得最大值 6：
`(0,0) -> (1,1) -> (3,1) -> (4,0)` 和 `(0,0) -> (1,1) -> (3,1) -> (4,1)`。它们除最后一个格子外完全相同，
而 `(4,0) < (4,1)`，所以 `optimal_path` 返回前一条。

### Part 3 —— 统计最优路径的条数

两条路径*不同*，当且仅当它们经过的格子列表不同。特别地，一条用特殊移动从 `(i,j)` 直接走到 `(i+2,j)`
的路径，与一条从 `(i,j)` 经过 `(i+1,j)` 再走到 `(i+2,j)` 的路径，即使前后经过的格子完全一样，也算作
两条不同的路径。返回取得最大基础分数的不同路径条数，对 `10^9 + 7` 取模。

```py
def count_optimal_paths(board: list[list[int]], p: int, K: int) -> int:
    """Same input as max_score. Returns the number of distinct maximum-base-score paths,
    modulo 10**9 + 7."""
```

例子，取

```text
board = [[ 2,  5],
         [ 0, -9],
         [ 3,  1]]
```

`p = 0`、`K = 1`：最大基础分数是 `5`，恰好由两条路径取得——`(0,0) -> (1,0) -> (2,0)`
（依次经过 `2, 0, 3`）和 `(0,0) -> (2,0)`（依次经过 `2, 3`，用了特殊移动）——所以
`count_optimal_paths(board, 0, 1) == 2`。

### Part 4 —— 奖励分

在基础分数之上叠加两条奖励规则，都是针对格子被*访问*（visited）的先后顺序定义的——一次特殊移动同样会让
它的两个端点被连续访问，效果与一次普通移动完全一样。给定整数 `X` 和 `Y`：

- 对每个满足 `1 <= t <= L` 且 $v_{t-1} = v_t$ 的 `t`，加上 `X`。
- 对每个满足 `2 <= t <= L` 且 $v_{t-2} < v_{t-1} < v_t$ 的 `t`，加上 `Y`。

返回从 `(0, p)` 到第 `N - 1` 行的所有路径中，总分数（基础分数加上两项奖励）的最大值。

```py
def max_score_with_bonuses(board: list[list[int]], p: int, K: int, X: int, Y: int) -> int:
    """Same input as max_score, plus bonus amounts X and Y. Returns the largest base
    score plus bonuses over all paths."""
```

例子，取

```text
board = [[ 3,  1],
         [-2,  5],
         [ 1,  2],
         [ 6,  6],
         [ 5,  6]]
```

`p = 0`、`K = 1`、`X = 3`、`Y = 6`：不算奖励时最大分数是 `22`。算上奖励后，
`max_score_with_bonuses(board, 0, 1, 3, 6) == 29`，唯一取得这个值的是
`(0,0) -> (1,1) -> (3,1) -> (4,1)`（依次经过 `3, 5, 6, 6`，用了一次从第 1 行到第 3 行的特殊移动）：
最后两个值相等（`+X`）；前三个值 `3 < 5 < 6` 严格递增，即使特殊移动让第二个和第三个值之间隔了两行
（`+Y`）。

## 参考解答

<details>
<summary>展开参考解答</summary>

先把 Part 1 完整实现并验证过，再动手写后面的部分——后面几问只是在同一个递推上加一张表或加一维状态，
把它们放在一起一次调试会比先调好分数难得多。

### Part 1

设 $dp[i][j][k]$ 为从 $(i, j)$ 出发、到第 $N - 1$ 行结束、最多还能使用 $k$ 次特殊移动的路径，
其基础分数的最大值。到了最后一行就无事可做：对所有 $j, k$，$dp[N-1][j][k] = board[N-1][j]$。
否则，路径的第一步决定了剩下的部分：

$$dp[i][j][k] = board[i][j] + \max\Bigl(\{\, dp[i{+}1][j{+}\delta][k] : \delta \in \{-1,0,1\},\ 0 \le j{+}\delta < M \,\} \ \cup\ \{\, dp[i{+}2][j][k{-}1] : k \ge 1,\ i{+}2 \le N{-}1 \,\}\Bigr).$$

答案就是 $dp[0][p][K]$。状态共有 $N \cdot M \cdot (K+1)$ 个，每个状态的转移是 $O(1)$，所以时间和空间都是
$O(N M K)$。

```python
def _best_scores(board, K):
    """dp[i][j][k]: max base score of a path from (i, j) to row N - 1, using at
    most k more special moves."""
    N, M = len(board), len(board[0])
    dp = [[[0] * (K + 1) for _ in range(M)] for _ in range(N)]
    for j in range(M):
        for k in range(K + 1):
            dp[N - 1][j][k] = board[N - 1][j]
    for i in range(N - 2, -1, -1):
        for j in range(M):
            for k in range(K + 1):
                candidates = [dp[i + 1][j + dj][k] for dj in (-1, 0, 1) if 0 <= j + dj < M]
                if k > 0 and i + 2 <= N - 1:              # NOTE: excludes i == N-2, where i+2 == N is outside the grid
                    candidates.append(dp[i + 2][j][k - 1])
                dp[i][j][k] = board[i][j] + max(candidates)   # NOTE: dj = 0 is always in range, candidates is never empty
    return dp


def max_score(board, p, K):
    return _best_scores(board, K)[0][p][K]
```

### Part 2

从 `(0, p, K)` 正向重建路径。在状态 `(i, j, k)` 处，把它可能的下一个状态按 `(row, column)` 升序列出——
三个普通移动按列号从小到大，然后是特殊移动，它的行号总是更大——取第一个 `dp` 值显示它仍能达到整体最优的候选，
也就是满足 `board[i][j] + dp[next] == dp[i][j][k]` 的那个。一定存在这样的候选，因为 `dp[i][j][k]`
本来就是在这些候选上取的最大值。每一步都选满足条件的最小下一格，得到的就是字典序最小的最优路径。任取另一条最优路径，
看两者第一次不同的位置——两条路径不可能一条是另一条的真前缀，因为每条路径都在第一次到达第 $N - 1$ 行时停止。
相同的前缀确定了当前格子和已经用掉的特殊移动次数，所以两条路径在那里处于同一个状态；另一条路径的下一格同样满足条件，
因为最优路径的剩余部分从这个状态出发也是最优的；而贪心规则选的是满足条件的最小格子，所以贪心得到的路径在这里更小。

```python
def optimal_path(board, p, K):
    dp = _best_scores(board, K)
    N, M = len(board), len(board[0])
    i, j, k = 0, p, K
    path = [(0, p)]
    while i != N - 1:
        moves = [(i + 1, j + dj, k) for dj in (-1, 0, 1) if 0 <= j + dj < M]
        if k > 0 and i + 2 <= N - 1:
            moves.append((i + 2, j, k - 1))
        # NOTE: `moves` is already in ascending (row, column) order, so the first
        # one that keeps the score optimal is the lexicographically smallest choice
        for (ni, nj, nk) in moves:
            if board[i][j] + dp[ni][nj][nk] == dp[i][j][k]:
                i, j, k = ni, nj, nk
                break
        path.append((i, j))
    return path
```

### Part 3

在同一个递推上再维护一张表 $cnt[i][j][k]$：从这个状态出发、取得最优值的路径条数，对 $10^9+7$ 取模。
边界是 $cnt[N-1][j][k] = 1$。当 $i < N - 1$ 时，在 Part 1 同样的那些候选状态里，设 $S$ 是其中真正取得
$dp[i][j][k]$ 的那些；于是 $cnt[i][j][k] = \sum_{s \in S} cnt[s] \bmod (10^9+7)$。判断一个候选是否属于
$S$ 时比较的是 Part 1 里算出来的、未经处理的（可能为负的）真实分数——如果先对分数取模再比较，一个本来严格更小的分数
可能看起来与最大值相等，甚至比它更大；所以只有累计的路径条数会被取模，分数本身永远不取模。

```python
MOD = 10 ** 9 + 7


def count_optimal_paths(board, p, K):
    N, M = len(board), len(board[0])
    dp = [[[0] * (K + 1) for _ in range(M)] for _ in range(N)]
    cnt = [[[0] * (K + 1) for _ in range(M)] for _ in range(N)]
    for j in range(M):
        for k in range(K + 1):
            dp[N - 1][j][k] = board[N - 1][j]
            cnt[N - 1][j][k] = 1
    for i in range(N - 2, -1, -1):
        for j in range(M):
            for k in range(K + 1):
                moves = [(i + 1, j + dj, k) for dj in (-1, 0, 1) if 0 <= j + dj < M]
                if k > 0 and i + 2 <= N - 1:
                    moves.append((i + 2, j, k - 1))
                best, total = None, 0
                for (ni, nj, nk) in moves:
                    val = dp[ni][nj][nk]
                    if best is None or val > best:       # NOTE: strict '>' — a new best discards the old tie count
                        best, total = val, cnt[ni][nj][nk]
                    elif val == best:                     # NOTE: compare the real (possibly negative) scores, never
                        total = (total + cnt[ni][nj][nk]) % MOD  #      `% MOD`-reduced ones; only `total` is reduced
                dp[i][j][k] = board[i][j] + best
                cnt[i][j][k] = total
    return cnt[0][p][K]
```

### Part 4

考虑路径的第 $t$ 步，即从 $(i, j)$ 出发的那一次移动：$v_{t-1} = board[i][j]$，$v_t = w$ 是落点格子的值。
这一步的相等奖励只取决于这两个值，二者都能直接从网格里读到；递增奖励还牵涉 $v_{t-2}$，即紧挨在 $(i, j)$
之前被访问的格子的值，但只通过一个比较 $v_{t-2} < board[i][j]$ 用到它，另一半 $board[i][j] < w$ 用的都是手头已有的值。所以状态只需多记一位——不需要已走过的路径，不需要上一个格子的位置，
甚至不需要它的值：紧挨在 $(i, j)$ 之前被访问的格子的值小于 $board[i][j]$ 时 $u = 1$，否则 $u = 0$；
起点之前没有格子，也取 $u = 0$。以相同的 $k$ 和 $u$ 到达 $(i, j)$ 的任意两段路径，此后能拿到的奖励完全相同，
所以把它们合并不会丢失任何东西。设 $g[i][j][k][u]$ 为从 $(i, j)$ 出发、到第 $N - 1$ 行结束、最多还能使用
$k$ 次特殊移动的路径的最大总分（基础分数加奖励），边界是 $g[N-1][j][k][u] = board[N-1][j]$。对 Part 1 的每个候选
$(i', j', k')$，记 $w = board[i'][j']$、$u' = [board[i][j] < w]$，它就是那个状态的 $u$（方括号里的条件成立时取 1，
否则取 0）：

$$g[i][j][k][u] = board[i][j] + \max_{(i',j',k')} \Bigl( X \cdot [board[i][j] = w] + Y \cdot u \cdot u' + g[i'][j'][k'][u'] \Bigr).$$

答案是 $g[0][p][K][0]$。这张表是 Part 1 的两倍大，所以时间和空间仍然是 $O(NMK)$。把上一个格子的值本身
而不是 $u$ 放进状态也是正确的，因为值决定了 $u$；只是把行为完全相同的状态拆成了几份。

```python
def max_score_with_bonuses(board, p, K, X, Y):
    """g[i][j][k][u]: max base score plus bonuses of a path from (i, j) to row N - 1,
    using at most k more special moves, where u = 1 iff the cell visited just before
    (i, j) has a smaller value than (i, j)."""
    N, M = len(board), len(board[0])
    g = [[[[0, 0] for _ in range(K + 1)] for _ in range(M)] for _ in range(N)]
    for j in range(M):
        for k in range(K + 1):
            g[N - 1][j][k] = [board[N - 1][j], board[N - 1][j]]
    for i in range(N - 2, -1, -1):
        for j in range(M):
            cur = board[i][j]
            for k in range(K + 1):
                moves = [(i + 1, j + dj, k) for dj in (-1, 0, 1) if 0 <= j + dj < M]
                if k > 0 and i + 2 <= N - 1:
                    moves.append((i + 2, j, k - 1))
                for u in (0, 1):
                    best = None
                    for (ni, nj, nk) in moves:
                        nxt = board[ni][nj]
                        up = 1 if cur < nxt else 0     # NOTE: this is the next cell's u
                        cand = g[ni][nj][nk][up] + (X if cur == nxt else 0) + (Y if u and up else 0)
                        if best is None or cand > best:
                            best = cand
                    g[i][j][k][u] = cur + best
    return g[0][p][K][0]   # NOTE: u = 0 at the start: no earlier cell, so no triple can end at t = 1
```

### 追问

- 让 `p` 取遍每一个起始列，取其中最大的：Part 1 的表里已经有每个 `j` 的 `dp[0][j][K]`，答案就是它们的最大值，
  不需要额外计算。
- 表的第 `i` 行只读取第 `i + 1` 行和第 `i + 2` 行，所以只保留三层滚动的行，就能把 Part 1、3、4 的空间降到
  $O(MK)$；Part 2 正向重建路径时仍然需要整张表。
- 当 `K` 接近 `N` 时，先把它截断到 `(N - 1) // 2`：路径一共下降 `N - 1` 行，每次特殊移动占去其中两行，
  所以任何路径都用不了更多次。
- 要求路径停在指定的列 `q`，只需要改边界：`j = q` 时 `dp[N-1][j][k]` 取 `board[N-1][q]`，其余的 `j` 取 `-inf`；
  答案为 `-inf` 表示没有路径能停在那一列。

<details>
<summary>验证代码（可运行）</summary>

```python
def brute_force_all_paths(board, p, K):
    N, M = len(board), len(board[0])
    paths = []

    def dfs(i, j, k, path):
        if i == N - 1:
            paths.append(list(path))
            return
        for dj in (-1, 0, 1):
            nj = j + dj
            if 0 <= nj < M:
                path.append((i + 1, nj))
                dfs(i + 1, nj, k, path)
                path.pop()
        if k > 0 and i + 2 <= N - 1:
            path.append((i + 2, j))
            dfs(i + 2, j, k - 1, path)
            path.pop()

    dfs(0, p, K, [(0, p)])
    return paths


def _base_score(board, path):
    return sum(board[r][c] for r, c in path)


def _bonus_score(board, path, X, Y):
    vals = [board[r][c] for r, c in path]
    total = sum(vals)
    for t in range(1, len(vals)):
        if vals[t - 1] == vals[t]:
            total += X
    for t in range(2, len(vals)):
        if vals[t - 2] < vals[t - 1] < vals[t]:
            total += Y
    return total


import random
from itertools import product

random.seed(0)
trials = 0
pools = [[-3, -2, -1, 0, 0, 1, 1, 2, 3], [0, 0, 1], [4, 4, 4, -4], list(range(-9, 10))]
for N, M, K in product(range(1, 10), range(1, 6), range(0, 4)):
    for _ in range(4):
        pool = random.choice(pools)                   # small pools: ties and equal-value bonuses show up often
        board = [[random.choice(pool) for _ in range(M)] for _ in range(N)]
        p = random.randrange(M)
        trials += 1

        all_paths = brute_force_all_paths(board, p, K)
        best_score = max(_base_score(board, path) for path in all_paths)
        assert max_score(board, p, K) == best_score

        best_paths = [path for path in all_paths if _base_score(board, path) == best_score]
        assert count_optimal_paths(board, p, K) == len(best_paths) % MOD

        got_path = optimal_path(board, p, K)
        assert got_path in all_paths and _base_score(board, got_path) == best_score
        assert got_path == min(best_paths)          # matches the lexicographic tie-break rule

        for _ in range(2):
            X, Y = random.randint(-5, 5), random.randint(-5, 5)   # zero and negative bonuses included
            assert max_score_with_bonuses(board, p, K, X, Y) == max(
                _bonus_score(board, path, X, Y) for path in all_paths
            )
print(f"{trials} random (N, M, K) instances checked against the brute-force enumeration")

# Counts past the modulus: on an all-zero board every path is optimal, so the answer is the
# total number of paths, counted here exactly with Python integers.
from functools import lru_cache

ZN, ZM, ZK = 30, 4, 3


@lru_cache(maxsize=None)
def _paths_from(i, j, k):
    if i == ZN - 1:
        return 1
    total = sum(_paths_from(i + 1, j + d, k) for d in (-1, 0, 1) if 0 <= j + d < ZM)
    if k > 0 and i + 2 < ZN:
        total += _paths_from(i + 2, j, k - 1)
    return total


assert _paths_from(0, 1, ZK) > MOD
assert count_optimal_paths([[0] * ZM for _ in range(ZN)], 1, ZK) == _paths_from(0, 1, ZK) % MOD

# A 3000-row board: with X = Y = 0, Part 4 must agree with Part 1
tall = [[random.randint(-3, 3) for _ in range(4)] for _ in range(3000)]
assert max_score_with_bonuses(tall, 1, 3, 0, 0) == max_score(tall, 1, 3)

# Examples from the statement
boardA = [[-3, 1, 4], [-1, 4, 4], [-3, -2, -3], [1, 0, -1], [5, 5, 3]]
assert max_score(boardA, 0, 1) == 6
assert count_optimal_paths(boardA, 0, 1) == 2
assert optimal_path(boardA, 0, 1) == [(0, 0), (1, 1), (3, 1), (4, 0)]

boardC = [[2, 5], [0, -9], [3, 1]]
assert count_optimal_paths(boardC, 0, 1) == 2

boardD = [[3, 1], [-2, 5], [1, 2], [6, 6], [5, 6]]
assert max_score(boardD, 0, 1) == 22
assert max_score_with_bonuses(boardD, 0, 1, 3, 6) == 29
assert [path for path in brute_force_all_paths(boardD, 0, 1)
        if _bonus_score(boardD, path, 3, 6) == 29] == [[(0, 0), (1, 1), (3, 1), (4, 1)]]
```

</details>

</details>
