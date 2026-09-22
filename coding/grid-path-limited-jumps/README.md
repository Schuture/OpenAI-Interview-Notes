# Best Grid Path with K Row Skips

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Hard | SWE | dp, grid, counting | 4 parts |
<!-- meta:end -->

## Problem

`board` is a grid of $N$ rows and $M$ columns holding integers (negative values allowed), indexed by row
`i` and column `j`, both starting at 0. A *path* starts at `(0, p)` for a given starting column `p`, and
from `(i, j)` it either takes a *step* to `(i+1, j-1)`, `(i+1, j)`, or `(i+1, j+1)` — whichever of these
has a column inside `[0, M)` — or, using one of a budget of at most `K` uses over the whole path, takes
the *special move* to `(i+2, j)`. Any move whose destination falls outside the grid is illegal — in
particular, the special move can never be taken from row `N - 2`, since that would put `i + 2` at `N`,
past the last row. The path stops
the first time it reaches row `N - 1`. When `N = 1` that is the starting cell itself, and the path takes
no move at all. Write $v_0, v_1, \dots, v_L$ for the values of the cells visited, in the order they are
visited ($v_0 = board[0][p]$, $v_L$ is the value at row `N - 1`). The *base score* of a path is
$\sum_{t=0}^{L} v_t$.

Implement the following four parts.

### Part 1 — Maximum score

Return the largest base score over all paths from `(0, p)` to row `N - 1`.

```py
def max_score(board: list[list[int]], p: int, K: int) -> int:
    """board has N >= 1 rows and M >= 1 columns, 0 <= p < M, K >= 0. Returns the largest base score."""
```

Example: with

```text
board = [[-3,  1,  4],
         [-1,  4,  4],
         [-3, -2, -3],
         [ 1,  0, -1],
         [ 5,  5,  3]]
```

`p = 0`, `K = 1`: `max_score(board, 0, 1) == 6`, attained e.g. by
`(0,0) -> (1,1) -> (3,1) -> (4,0)` (values `-3, 4, 0, 5`), which uses the special move once, from row 1
to row 3.

### Part 2 — Recovering a path

Return one path attaining the maximum base score, as the list of cells it visits,
`[(0, p), ..., (N - 1, ·)]`. When several paths attain the maximum, compare their visited-cell lists with
the usual lexicographic order — compare the first cell as a `(row, column)` pair, then the second, and so
on — and return the smallest one.

```py
def optimal_path(board: list[list[int]], p: int, K: int) -> list[tuple[int, int]]:
    """Same input as max_score. Returns the lexicographically smallest cell list among the
    paths that attain the maximum base score."""
```

Example: on the `board` above with `p = 0`, `K = 1`, two paths attain the maximum score 6:
`(0,0) -> (1,1) -> (3,1) -> (4,0)` and `(0,0) -> (1,1) -> (3,1) -> (4,1)`. They agree on every cell except
the last, where `(4,0) < (4,1)`, so `optimal_path` returns the first one.

### Part 3 — Counting maximum-score paths

Two paths are *different* if their visited-cell lists differ. In particular, a path that uses the special
move from `(i,j)` to `(i+2,j)` is different from one that steps through `(i+1,j)` on the way from `(i,j)`
to `(i+2,j)`, even though the two agree on every cell before and after that segment. Return the number of
different paths attaining the maximum base score, modulo `10^9 + 7`.

```py
def count_optimal_paths(board: list[list[int]], p: int, K: int) -> int:
    """Same input as max_score. Returns the number of distinct maximum-base-score paths,
    modulo 10**9 + 7."""
```

Example: with

```text
board = [[ 2,  5],
         [ 0, -9],
         [ 3,  1]]
```

`p = 0`, `K = 1`: the maximum base score is `5`, attained by exactly two paths —
`(0,0) -> (1,0) -> (2,0)` (values `2, 0, 3`) and `(0,0) -> (2,0)` (values `2, 3`, using the special move) —
so `count_optimal_paths(board, 0, 1) == 2`.

### Part 4 — Bonuses

Two bonus rules apply on top of the base score, both stated in terms of the order cells are *visited* —
a special move still makes its two endpoints visited consecutively, exactly like a step. Given integers
`X` and `Y`:

- For every `t` with `1 <= t <= L` such that $v_{t-1} = v_t$, add `X`.
- For every `t` with `2 <= t <= L` such that $v_{t-2} < v_{t-1} < v_t$, add `Y`.

Return the largest score (base score plus both bonuses) over all paths from `(0, p)` to row `N - 1`.

```py
def max_score_with_bonuses(board: list[list[int]], p: int, K: int, X: int, Y: int) -> int:
    """Same input as max_score, plus bonus amounts X and Y. Returns the largest base
    score plus bonuses over all paths."""
```

Example: with

```text
board = [[ 3,  1],
         [-2,  5],
         [ 1,  2],
         [ 6,  6],
         [ 5,  6]]
```

`p = 0`, `K = 1`, `X = 3`, `Y = 6`: without bonuses the maximum score is `22`. With bonuses,
`max_score_with_bonuses(board, 0, 1, 3, 6) == 29`, attained only by
`(0,0) -> (1,1) -> (3,1) -> (4,1)` (values `3, 5, 6, 6`, using the special move from row 1 to row 3): the
last two values are equal (`+X`), and the first three, `3 < 5 < 6`, are strictly increasing even though
the special move puts two rows between the second and third (`+Y`).

## Reference solution

<details>
<summary>Show the reference solution</summary>

Implement Part 1 first and get it fully checked before touching anything else — the later parts only add
a table or a dimension to the same recurrence, and debugging all of them at once is much harder than
debugging the score first.

### Part 1

Let $dp[i][j][k]$ be the largest base score of a path that starts at $(i, j)$ and ends at row $N - 1$,
using at most $k$ further special moves. At the last row there is nothing left to do:
$dp[N-1][j][k] = board[N-1][j]$ for every $j, k$. Otherwise the path's first move fixes the rest:

$$dp[i][j][k] = board[i][j] + \max\Bigl(\{\, dp[i{+}1][j{+}\delta][k] : \delta \in \{-1,0,1\},\ 0 \le j{+}\delta < M \,\} \ \cup\ \{\, dp[i{+}2][j][k{-}1] : k \ge 1,\ i{+}2 \le N{-}1 \,\}\Bigr).$$

The answer is $dp[0][p][K]$. There are $N \cdot M \cdot (K+1)$ states and each does $O(1)$ work, so this
is $O(N M K)$ time and space.

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

Rebuild the path forward from `(0, p, K)`. At a state `(i, j, k)`, list its possible next states in
ascending `(row, column)` order — the three steps by increasing column, then the special move, which
always has the larger row — and take the first one whose `dp` value shows it still reaches the overall
optimum, i.e. `board[i][j] + dp[next] == dp[i][j][k]`. Some next state always qualifies, since `dp[i][j][k]`
was itself defined as a maximum over exactly these candidates. Choosing the smallest qualifying next cell
at every step gives the lexicographically smallest optimal path. Take any other optimal path and the first
position where the two differ — neither can be a proper prefix of the other, since every path stops the
first time it reaches row $N - 1$. The shared prefix fixes the current cell and how many special moves
have been used, so both paths are at the same state there; the other path's next cell qualifies too,
because the rest of an optimal path is optimal from that state; and the greedy rule took the smallest
qualifying cell, so the greedy path is the smaller of the two.

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

Extend the same recurrence with a parallel table $cnt[i][j][k]$: the number of optimal-from-here paths,
modulo $10^9+7$. The base case is $cnt[N-1][j][k] = 1$. For $i < N - 1$, among the same candidate next
states as in Part 1, let $S$ be the ones that actually attain $dp[i][j][k]$; then
$cnt[i][j][k] = \sum_{s \in S} cnt[s] \bmod (10^9+7)$. The membership test for $S$ compares the exact
(possibly negative) scores computed in Part 1 — reducing a score modulo $10^9+7$ before comparing it could
make a strictly smaller score look equal to the best one, or even larger, so only the running counts,
never the scores, are ever taken modulo $10^9+7$.

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

Consider step $t$ of a path, the move out of $(i, j)$, so $v_{t-1} = board[i][j]$ and $v_t = w$ is the
value of the cell it lands on. Its pair bonus depends only on these two values, both read directly off the
board. Its triple bonus also involves $v_{t-2}$, the value visited just before $(i, j)$, but only through
the one comparison $v_{t-2} < board[i][j]$; the other half, $board[i][j] < w$, uses values already on hand.
So the state needs one extra bit — not the path so far, not the previous cell's position, not even its value: $u = 1$ if the cell visited right before $(i, j)$ has a smaller value than $board[i][j]$,
and $u = 0$ otherwise, including at the start, where there is no earlier cell. Any two partial paths that
reach $(i, j)$ with the same $k$ and $u$ collect exactly the same bonuses from then on, so merging them
loses nothing. Let $g[i][j][k][u]$ be the largest score (base plus bonuses) of a path from $(i, j)$ to row
$N - 1$ using at most $k$ more special moves, with $g[N-1][j][k][u] = board[N-1][j]$. For a move to a
candidate $(i', j', k')$ of Part 1, write $w = board[i'][j']$ and $u' = [board[i][j] < w]$, the bit that
state starts with (a bracketed condition is 1 when it holds and 0 otherwise):

$$g[i][j][k][u] = board[i][j] + \max_{(i',j',k')} \Bigl( X \cdot [board[i][j] = w] + Y \cdot u \cdot u' + g[i'][j'][k'][u'] \Bigr).$$

The answer is $g[0][p][K][0]$. The table is twice the size of Part 1's, so this is still $O(NMK)$ time and
space. Keeping the previous value itself in the state instead of $u$ is also correct, since the value
determines $u$; it only splits states that behave identically.

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

### Follow-ups

- Let `p` range over every starting column and take the best: Part 1's table already holds `dp[0][j][K]`
  for every `j`, so the answer is their maximum at no extra cost.
- Row `i` of the table reads only rows `i + 1` and `i + 2`, so keeping three rolling layers cuts the space
  of Parts 1, 3 and 4 to $O(MK)$; Part 2 still needs the whole table to walk forward.
- For `K` close to `N`, cap it at `(N - 1) // 2` first: a path descends `N - 1` rows and each special move
  takes two of them, so no path can use more.
- Requiring the path to end at a given column `q` only changes the base case: `dp[N-1][j][k]` becomes
  `board[N-1][q]` for `j = q` and `-inf` for every other `j`, and an answer of `-inf` means no path ends there.

<details>
<summary>Checks (runnable)</summary>

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
