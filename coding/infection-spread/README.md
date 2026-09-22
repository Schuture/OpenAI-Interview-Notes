# Infection Spread (Grid Cellular Automaton)

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★★★ | Medium | SWE · MLE · RE · RS · EM | bfs, simulation, grid | 5 parts / 60 min |
<!-- meta:end -->

## Problem

`grid` is a list of $R$ rows, each a list of $C$ integers. `grid[r][c]` is the state of the cell in row
$r$ and column $c$: `0` means *healthy* and `1` means *infected*. The *neighbours* of a cell are the
cells directly above, below, left and right of it that lie inside the grid. Diagonal cells are not
neighbours.

Time advances in whole days, and day 0 is the input grid. The grid of day $t + 1$ is computed from the
grid of day $t$ by applying the rule to all cells at the same time (*synchronous update*). A cell that
becomes infected on day $t + 1$ therefore starts infecting its neighbours in the step from day $t + 1$
to day $t + 2$.

The problem has five parts, and each part adds a rule to the previous one.

### Part 1 — Spread

A healthy cell becomes infected on day $t + 1$ if at least one of its neighbours is infected on day $t$.
Infected cells stay infected. Return the smallest $t$ such that no cell is healthy on day $t$, or `-1`
if there is no such day. If no cell is healthy on day 0, which includes the empty grid, return `0`.

```py
def days_until_all_infected(grid: list[list[int]]) -> int:
    """grid[r][c] is 0 (healthy) or 1 (infected); from Part 2 on also 2 (immune). Returns the day, or -1."""
```

Example: two cells are infected on day 0, every cell is infected on day 2, and the answer is `2`.

```text
day 0        day 1        day 2
1 0 0 0      1 1 0 0      1 1 1 1
0 0 0 0      1 0 0 1      1 1 1 1
0 0 0 1      0 0 1 1      1 1 1 1
```

### Part 2 — Immune cells

The grid may also contain `2`, which means *immune*. An immune cell never changes state and does not
count as an infected neighbour, so the infection cannot pass through it. The task is the same as in
Part 1. Return `-1` if some healthy cell can never be infected.

In the left grid the infection has to go around the immune cells and reaches the top-right cell on day
6. In the right grid the right-hand column is cut off, and the answer is `-1`.

```text
1 2 0                     1 2 0
0 2 0      -> 6           2 2 0      -> -1
0 0 0
```

### Part 3 — Recovery after D days

An integer $D \ge 1$ is given. A cell that has been infected for $D$ days recovers: it becomes immune
and stops infecting others. For every infected cell let $t_0$ be the day on which it became infected,
with $t_0 = 0$ for the cells that are infected in the input. The step from day $t - 1$ to day $t$ has
two phases, in this order:

1. Recovery: every infected cell with $t - t_0 \ge D$ becomes immune.
2. Spread: every healthy cell with at least one neighbour that is still infected after phase 1 becomes
   infected, with $t_0 = t$.

Return the smallest $t$ such that no cell is infected on day $t$ (`0` if no cell is infected on day 0).
Healthy cells may remain.

```py
def days_until_outbreak_ends(grid: list[list[int]], D: int) -> int:
    """grid holds 0, 1 or 2, and D >= 1. Returns the first day on which no cell is infected."""
```

Example: the single row `1 0 0` with $D = 2$, cells numbered 0, 1, 2 from the left. The answer is `4`.
With $D = 1$ cell 0 recovers on day 1 before it infects anyone, and the answer is `1`.

```text
day 0:  1 0 0
day 1:  1 1 0    cell 0: 1 - 0 < 2, no recovery; it infects cell 1 (t0 = 1)
day 2:  2 1 1    cell 0: 2 - 0 >= 2, recovers; cell 1 infects cell 2 (t0 = 2)
day 3:  2 2 1    cell 1: 3 - 1 >= 2, recovers; cell 2 has no healthy neighbour
day 4:  2 2 2    cell 2: 4 - 2 >= 2, recovers; no cell is infected
```

### Part 4 — Thresholds and deaths

This part has three versions.

**Version A, spread threshold.** An integer $K \ge 1$ is given. In phase 2 a healthy cell becomes
infected only if at least $K$ of its neighbours are infected. $K = 1$ is Part 3. The return value is
the same as in Part 3. Example with $K = 2$ and $D = 2$: the outbreak ends on day 4, and three cells are
never infected because they never have two infected neighbours on the same day.

```text
day 0      day 1      day 2      day 3      day 4
1 0 1      1 1 1      2 1 2      2 2 2      2 2 2
0 0 0      1 0 0      1 1 0      2 1 0      2 2 0
1 0 0      1 0 0      2 0 0      2 0 0      2 0 0
```

**Version B, deaths.** A new state `3` means *dead*. A dead cell never changes state and never infects
others. A healthy cell becomes infected as in Part 3. If it has at least $K$ infected neighbours at the
moment it becomes infected, then at the end of its $D$ days it dies instead of becoming immune. Return
the day on which the outbreak ends and the number of dead cells.

**Version C.** Immune cells, recovery, a spread threshold and deaths combined in one simulation.

```py
def simulate(grid: list[list[int]], recover_after: int, spread_threshold: int = 1,
             death_threshold: int | None = None) -> tuple[int, int]:
    """recover_after is D. spread_threshold is the K of version A. death_threshold is the K of
    version B, or None when nobody dies. Returns (day on which the outbreak ends, number of dead cells)."""
```

### Part 5 — Intervention

On each day you may choose one row or one column and clear every cell in it. Minimise the total number
of deaths. This part is open-ended: fix the remaining rules yourself, for example whether cleared cells
count as deaths and whether they block the spread afterwards, and state them.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Confirm with the interviewer before coding: four neighbours or eight; how cells are encoded (integers
or characters, immune as `2` or `-1`); in Part 3, whether recovery comes before the spread of the same
day and whether the test is $\ge$ or $>$; in Part 4, whether $K$ is a threshold for infection, for death,
or for both. With five parts in 60 minutes, Parts 1 and 2 should be written quickly and kept simple.

### Parts 1–2: multi-source BFS

Start a breadth-first search from all infected cells at once, that is, put all of them into the queue
with distance 0. The BFS distance of a cell is then its distance to the nearest infected cell, which is
exactly the day on which it becomes infected. One BFS level is one day, and the answer is the number of
the last level. Keep a count of the healthy cells not yet reached: stop when it is 0, and return `-1` if
the queue runs empty first. Immune cells are never entered, which is all that Part 2 adds. Every cell
enters the queue at most once, so time and memory are $O(R \cdot C)$. Recomputing the whole grid for
every day is easier to write but costs $O((R \cdot C)^2)$ in the worst case, because a corridor of immune
cells can make the infection take on the order of $R \cdot C$ days.

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

### Parts 3–4: day-by-day simulation

With timers, BFS levels are no longer enough. Store $t_0$ for every infected cell and simulate the two
phases of the statement day by day. Each cell is infected for at most $D$ days and costs constant work
on each of them, so the simulation takes $O(R \cdot C \cdot D)$. Part 4 uses the same loop with two
thresholds as parameters.

For Part 3 alone there is a closed form. With threshold 1 and $D \ge 2$, a cell infects all its healthy
neighbours on the day after it was infected, so the infection advances exactly as in Part 2. If
$d_{\max}$ is the largest BFS distance among the cells that are reached, the last cell is infected on day
$d_{\max}$ and recovers on day $d_{\max} + D$, which is the answer. For $D = 1$ the answer is 1, because
the initial cells recover before they spread. With a threshold $K > 1$ the closed form fails, since a
cell may collect its $K$ infected neighbours over several days.

```python
def simulate(grid, recover_after, spread_threshold=1, death_threshold=None):
    """Returns (day on which the outbreak ends, number of dead cells)."""
    if not grid or not grid[0]:
        return 0, 0
    rows, cols = len(grid), len(grid[0])
    state = [row[:] for row in grid]
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

There is no established algorithm. A reasonable answer is exhaustive search over the $R + C$ choices
per day on small grids, a greedy rule on large ones (clear the row or column that currently holds the
most infected cells), and a clear statement that the greedy rule is not optimal.

### Follow-ups

- Characters instead of integers (`.`, `X`, `I`): convert on input and keep the core numeric.
- Very large or sparse grids: store only the set of infected cells and the frontier, or split the grid
  into tiles that exchange their borders after every day.
- Counting infected neighbours for all cells at once is a 2D convolution with a plus-shaped kernel.

<details>
<summary>Checks (runnable)</summary>

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
```

</details>

</details>
