# New-Grad Online Assessment

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Online assessment | ★☆☆☆☆ | Easy | SWE | graph, counting, simulation, dp | 4 independent parts |
<!-- meta:end -->

## Problem

Four independent problems, each auto-graded against hidden tests; no part builds on another. Solve each as a
function with the stated signature.

### Part 1 — End of a Walk in a Functional Graph

A *directed graph* has nodes identified by integers (not necessarily consecutive, possibly negative) and
directed *edges* `u -> v` between distinct nodes. In this graph every node has at most one outgoing edge, so
the edges are given as two parallel lists: the `i`-th edge goes from `from_ids[i]` to `to_ids[i]`, and the
values in `from_ids` are pairwise distinct. A node that appears only in `to_ids`, or in neither list, has no
outgoing edge.

The *walk* from a node `start` is the sequence of nodes `w_0 = start, w_1, w_2, ...` where `w_{t+1}` is the
head of the unique edge leaving `w_t`. The walk stops at the first `w_t` for which either

- `w_t` has no outgoing edge, or
- the head `w` of the edge leaving `w_t` already occurs among `w_0, ..., w_t`.

Return that last node `w_t`. In the second case this is the node just before the walk would close a cycle,
not the node where the cycle begins.

```py
def walk_end(from_ids: list[int], to_ids: list[int], start: int) -> int:
    """len(from_ids) == len(to_ids) <= 2 * 10**5; from_ids are distinct; from_ids[i] != to_ids[i]."""
```

Example: edges `7 -> 12`, `12 -> 40`, `40 -> 3`, `3 -> 12`, `90 -> 7`.

```text
walk_end(..., 90) -> 3    walk: 90, 7, 12, 40, 3; the edge from 3 leads back to 12, already visited
walk_end(..., 3)  -> 40   walk: 3, 12, 40; the edge from 40 leads back to 3
walk_end(..., 55) -> 55   node 55 has no outgoing edge
```

### Part 2 — Four-Node Paths Covering Four Types

An undirected simple graph (no loops, no repeated edges) has nodes `0, ..., n - 1` and an edge list `edges`
of unordered pairs. Node `v` carries a *type* `types[v]` in `{0, 1, 2, 3}`.

A *4-path* is a sequence `(v_1, v_2, v_3, v_4)` of four pairwise distinct nodes such that `v_i` and `v_{i+1}`
are adjacent for `i = 1, 2, 3`. It is *covering* if `types[v_1], ..., types[v_4]` are the numbers `0, 1, 2, 3`
in some order, each exactly once. Sequences are ordered: `(v_1, v_2, v_3, v_4)` and its reverse
`(v_4, v_3, v_2, v_1)` are two different 4-paths. Return the number of covering 4-paths.

```py
def count_typed_paths(n: int, edges: list[tuple[int, int]], types: list[int]) -> int:
    """1 <= n <= 50, len(edges) <= 250, types[v] in {0, 1, 2, 3}. Returns the number of ordered
    4-node paths whose four nodes have four different types."""
```

Example: `n = 6`, `types = [0, 1, 2, 3, 0, 3]`, `edges = [(0,1), (1,2), (2,3), (3,4), (2,5), (4,1)]`.
The answer is `14`: there are seven covering 4-paths up to reversal, namely
`(0,1,2,3)`, `(0,1,2,5)`, `(4,1,2,3)`, `(4,1,2,5)`, `(1,2,3,4)`, `(2,1,4,3)` and `(2,3,4,1)`, and each is counted
together with its reverse. The sequence `(0,1,4,3)` is not covering because `4` has the same type as `0`.

### Part 3 — Neighbour Eating on a Line

`families` is a string and `sizes` a list of positive integers of the same length `m <= 20`. Organism `i`
(0-indexed, left to right) belongs to the family `families[i]` and has size `sizes[i]`. The simulation runs in
*rounds*; a round is defined on the line of organisms as it stands at the start of the round, with sizes taken
as they are at that moment.

In a round, positions `i = 0, 1, ..., m - 1` are processed in this order. Each organism is either *free* or
*used*; all start free, and an organism becomes used when it eats or is eaten. When position `i` is processed:

1. If organism `i` is used, nothing happens.
2. Otherwise, call a neighbour `j` (`j = i - 1` or `j = i + 1`, if it exists) *edible* if it is free, belongs
   to a different family, and is strictly smaller than organism `i`.
3. If the left neighbour is edible, organism `i` eats it. Otherwise, if the right neighbour is edible, organism
   `i` eats that one. Otherwise nothing happens. When `i` eats `j`, both become used, and `j` will be removed.

At the end of the round, every eaten organism is removed from the line and every eater's size is increased
by the size of the organism it ate. If the round had at least one eating event, another round starts on the
new line; otherwise the simulation stops. Return the family and size of the largest organism as
`"<family> <size>"`; if several share the largest size, take the leftmost.

```py
def last_standing(families: str, sizes: list[int]) -> str:
    """1 <= len(families) == len(sizes) <= 20, families are letters, sizes are positive integers.
    Returns "<family> <size>" of the largest organism once no eating event can occur."""
```

Example: `families = "ABABBCA"`, `sizes = [4, 2, 5, 3, 1, 6, 2]`.

```text
Round 1   line: A4 B2 A5 B3 B1 C6 A2
  i=0  A4: no left neighbour; right B2 is free, other family, smaller      -> A4 eats B2
  i=1  B2: used
  i=2  A5: left B2 is used; right B3 is free, other family, smaller         -> A5 eats B3
  i=3  B3: used
  i=4  B1: left B3 is used; right C6 is larger                             -> nothing
  i=5  C6: left B1 is free, other family, smaller -> C6 eats B1
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

### Part 4 — Cheapest Blend Plan

A café plans `n` days. On each day it serves exactly one of three blends, numbered `0, 1, 2`; serving blend
`b` on day `d` costs `costs[d][b]`. The same blend may not be served on two consecutive days. The *cost* of a
plan is the sum of the daily costs. Return the plan of minimum cost as the list of blend numbers, one per day.
The input is such that exactly one plan has minimum cost.

```py
def cheapest_blends(costs: list[list[int]]) -> list[int]:
    """1 <= len(costs) <= 10**5, costs[d] has 3 entries, 1 <= costs[d][b] <= 10**9. Returns the blend
    chosen on each day in a plan of minimum total cost; that plan is unique."""
```

Example: `costs = [[4, 7, 3], [6, 2, 5], [3, 8, 1], [5, 4, 9]]` gives `[2, 1, 2, 1]` with total cost
`3 + 2 + 1 + 4 = 10`; the next best plan, `[2, 1, 2, 0]`, costs 11.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming before coding, part by part: in Part 1, which node is returned when the walk meets a visited
node (the current one, not the repeated one) and that `start` itself may have no outgoing edge; in Part 2,
that a path and its reverse are counted separately; in Part 3, that sizes are compared at the start of the
round and that the left neighbour has priority; in Part 4, that the minimum plan is unique, so no tie-break
is needed.

### Part 1

Index the edges by tail in a dictionary and simulate the walk, keeping the set of visited nodes. Each node is
added once, so the time is O(E).

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

Fix the middle edge `(b, c)` of the path, in both orientations. The two end nodes must supply the two types
that `b` and `c` do not have, so only the types matter: let `x`, `y` be those two missing types. Either the
first node has type `x` and the last has type `y`, or the other way round. With `nbr_count[v][t]` the number of
neighbours of `v` of type `t`, the number of such paths with middle `(b, c)` is

```text
nbr_count[b][x] * nbr_count[c][y] + nbr_count[b][y] * nbr_count[c][x]
```

The end nodes cannot coincide with each other or with `b`, `c`, because the four types are different, so no
subtraction is needed. Summing over both orientations of every edge costs O(n + E). A brute force over all
n^4 tuples is already feasible at n = 50 (about 6 million tuples), and a dynamic programme over the
set of types used so far is the other standard route; the formula above is the shortest.

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

Trace of the example (`types = [0, 1, 2, 3, 0, 3]`): the middle edge `{1, 2}`, with types 1 and 2, misses
types 0 and 3. Node 1 has two type-0 neighbours (0 and 4) and no type-3 neighbour, node 2 has two type-3
neighbours (3 and 5) and no type-0 neighbour, so each orientation contributes `2*2 + 0*0 = 4`, for 8
in total. The middle edges `{2, 3}`, `{1, 4}` and `{3, 4}` contribute 2 each, and `{0, 1}`, `{2, 5}`
contribute 0; the sum is 14.

### Part 3

The input has at most 20 organisms and every round with an event removes at least one, so there are at most
19 eventful rounds of O(m) work: direct simulation is enough. The rule is implemented literally with a
`taken` flag array; because every organism that grew is `taken`, comparing sizes at the start of the round is
the same as comparing current sizes, and the growth can be applied when the round ends.

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

Let `best[d][b]` be the minimum cost of days `0..d` given that day `d` serves blend `b`. Then
`best[0][b] = costs[0][b]` and, for `d >= 1`,

```text
best[d][b] = costs[d][b] + min(best[d-1][q] for q != b)
```

The answer cost is the minimum of the last row. To recover the plan, store for each state the predecessor
blend that achieved its minimum, start from the best final blend and walk back. Time and space are O(n)
(three values per day).

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

### Follow-ups

- Part 1 for many starts on the same graph: compute each node's answer once with memoisation along the walk.
- Part 2 with `k` types and paths of `k` nodes: dynamic programme over (node, set of types used).
- Part 3 with the eating order reversed (right neighbour first): which inputs change their result?
- Part 4 with `m` blends, still O(nm) by keeping the two smallest values of the previous day.

<details>
<summary>Checks (runnable)</summary>

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
