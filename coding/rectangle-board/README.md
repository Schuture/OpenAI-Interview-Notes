# Rectangle Board with Undo

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Coding | ★★☆☆☆ | Medium | SWE | data-structure, state-management, undo, spatial-index | 5 parts | Phone screen |
<!-- meta:end -->

## Problem

A *board* is a grid of `width` × `height` unit cells. Cell `(x, y)` has column `x` and row `y`, with
`0 <= x < width` and `0 <= y < height`. A *rectangle* is given by four integers `(x1, y1, x2, y2)` and
covers the cells `(x, y)` with `x1 <= x < x2` and `y1 <= y < y2` (half-open on both axes). It is valid
when `0 <= x1 < x2 <= width` and `0 <= y1 < y2 <= height`, so it covers at least one cell and lies
inside the board. Rectangles may overlap. Build the board in five parts, each adding methods to the same
`Board` class.

Every rectangle on the board has an *id*, a positive integer assigned when it is added. The first id
issued by a board is 1, each later one is the previous plus 1, and an id is never issued twice, even if
its rectangle has been removed since. Rectangles are stacked in *z-order*: a rectangle added later lies
above every rectangle added before it. The *topmost* rectangle at a cell is the one with the largest id
among the rectangles covering that cell.

### Part 1 — Add

```py
class Board:
    def __init__(self, width: int, height: int) -> None:
        """An empty board. Requires width >= 1 and height >= 1; raises ValueError otherwise."""

    def add(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """Places a rectangle on top of all others and returns its new id.
        Raises ValueError if the rectangle is not valid; the board is unchanged then."""

    def get(self, rect_id: int) -> tuple[int, int, int, int] | None:
        """The rectangle (x1, y1, x2, y2) with this id, or None if the board holds none."""

    def ids(self) -> list[int]:
        """Ids of all rectangles on the board, in z-order from bottom to top."""
```

For example:

```text
b = Board(8, 6)
b.add(0, 0, 4, 3)         # 1
b.add(2, 1, 6, 5)         # 2
b.add(1, 1, 3, 2)         # 3
b.ids()                   # [1, 2, 3]
b.get(2)                  # (2, 1, 6, 5)
b.get(9)                  # None
b.add(5, 5, 5, 6)         # ValueError -- x1 == x2, no cell covered
b.add(6, 0, 9, 2)         # ValueError -- x2 > width
```

### Part 2 — Remove

```py
def remove(self, rect_id: int) -> None:
    """Removes the rectangle with this id. Raises KeyError if the board holds none;
    the board is unchanged then. The remaining rectangles keep their relative z-order."""
```

For example, continuing the board above:

```text
b.remove(2)               # board now holds ids [1, 3]
b.remove(2)               # KeyError -- already gone
b.add(5, 0, 8, 2)         # 4 -- the id 2 is not issued again, and the next id is not 3
b.ids()                   # [1, 3, 4]
```

### Part 3 — Undo

An *operation* is a call that changes the board: a successful `add` or `remove`, and from the next parts
on a successful `remove_at` or `remove_many`. A call that raises, or that changes nothing, is not an
operation. `undo` reverts the most recent operation that has not been reverted yet, and can be called
repeatedly to walk further back. After `undo` the board is exactly as it was before that operation:
the same rectangles with the same ids and the same z-order. The id counter is not rolled back.

```py
def undo(self) -> bool:
    """Reverts the most recent operation not yet reverted and returns True,
    or returns False and does nothing if there is no such operation."""
```

For example, on the board above (history: add 1, add 2, add 3, remove 2, add 4):

```text
b.undo()                  # True  -- the rectangle 4 is gone:  ids [1, 3]
b.undo()                  # True  -- the rectangle 2 is back:  ids [1, 2, 3], z-order as before
b.add(0, 4, 2, 6)         # 5     -- not 4: ids are never reused, also after an undo
b.undo()                  # True  -- ids [1, 2, 3]
b.undo(); b.undo(); b.undo()   # True each time -> ids [], after undoing add 3, add 2, add 1
b.undo()                  # False -- nothing left to undo
```

### Part 4 — Remove at a cell

```py
def remove_at(self, x: int, y: int) -> int | None:
    """Removes the topmost rectangle covering cell (x, y) and returns its id, or returns None
    (board unchanged) if no rectangle covers the cell. Raises ValueError if (x, y) is not a
    cell of the board."""
```

A successful `remove_at` is one operation, reverted by `undo` like `remove`.

For example, on a fresh `Board(8, 6)` holding `(0, 0, 4, 3)`, `(2, 1, 6, 5)` and `(1, 1, 3, 2)` as ids 1, 2, 3:

```text
b.remove_at(2, 1)         # 3     -- all three cover (2, 1); id 3 is the topmost
b.remove_at(2, 1)         # 2
b.remove_at(5, 4)         # None  -- only id 2 covered (5, 4), and it is gone
b.remove_at(4, 0)         # None  -- x2 is excluded: id 1 covers columns 0..3 only
b.undo()                  # True  -- reverts the second remove_at(2, 1): id 2 is back
```

### Part 5 — Batch removal

```py
def remove_many(self, rect_ids: list[int]) -> None:
    """Removes all the listed rectangles as one operation. Raises ValueError if the list contains
    the same id twice, and KeyError if any id is not on the board; in both cases nothing is removed.
    An empty list does nothing and is not an operation."""
```

One `undo` reverts a whole `remove_many` call: all its rectangles come back together, each with its
original id and z-order.

For example, on a fresh `Board(8, 6)` holding ids 1, 2, 3 as in Part 4:

```text
b.remove_many([3, 1])     # ids [2]
b.undo()                  # True -- one step brings back both: ids [1, 2, 3]
b.remove_many([1, 9])     # KeyError -- 9 is not on the board; id 1 is still there
b.remove_many([2, 2])     # ValueError
b.remove_many([])         # nothing happens
b.undo()                  # True -- reverts the add of id 3, not an empty operation
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming up front: that an id is never reused (so it can name a rectangle for as long as the
program runs), and what an undone operation does to the id counter. Both are fixed by the statement
above; the design below does not depend on any more detail than that.

### Design

Every operation, whatever its name, does the same thing to the board: it takes some rectangles off it
and puts some others on. Call this pair a *change*: a tuple `added` of `(id, rectangle)` pairs and a
tuple `removed` of `(id, rectangle)` pairs. Then

- applying a change deletes its `removed` ids and inserts its `added` pairs;
- the *inverse* of a change swaps the two tuples, so applying the inverse reverts the change exactly;
- the history is a stack of changes, and `undo` pops the top one and applies its inverse.

The board mutates only through one private function `_apply(change)`, and public operations only
through `_commit(change)`, which applies a change and records it. Every later part is then a new way of
building a change and nothing else: `add` builds `added=((id, rect),)`, `remove` builds
`removed=((id, rect),)`, `remove_at` finds an id and delegates to `remove`, and a batch is one change
with several `removed` pairs, which is why undo reverts it as one step with no further code.

Z-order needs no data structure of its own: it is the id order, since ids grow with time. Reinserting
a removed pair therefore restores its z-position automatically, wherever the dictionary happens to put
it, and `ids()` sorts to read the order off.

### Part 1

`add` validates, takes the next id, and commits a change. The board keeps a dictionary from id to
rectangle, so `add` and `get` are $O(1)$ and `ids` is $O(n \log n)$ for $n$ rectangles on the board.

```python
from typing import NamedTuple


class Change(NamedTuple):
    added: tuple     # ((id, rect), ...) inserted by this change
    removed: tuple   # ((id, rect), ...) deleted by this change

    def inverse(self) -> "Change":
        return Change(added=self.removed, removed=self.added)


class Board:
    def __init__(self, width: int, height: int) -> None:
        if width < 1 or height < 1:
            raise ValueError("board must have at least one cell")
        self.width, self.height = width, height
        self._rects: dict[int, tuple] = {}
        self._next_id = 1
        self._history: list[Change] = []     # unused until Part 3

    def _apply(self, change: Change) -> None:
        for rect_id, _ in change.removed:
            del self._rects[rect_id]
        for rect_id, rect in change.added:
            self._rects[rect_id] = rect

    def _commit(self, change: Change) -> None:
        self._apply(change)

    def add(self, x1: int, y1: int, x2: int, y2: int) -> int:
        if not (0 <= x1 < x2 <= self.width and 0 <= y1 < y2 <= self.height):
            raise ValueError(f"invalid rectangle {(x1, y1, x2, y2)}")
        rect_id = self._next_id
        self._next_id += 1      # NOTE: only ever incremented, so an undo of this add cannot hand the id out again
        self._commit(Change(added=((rect_id, (x1, y1, x2, y2)),), removed=()))
        return rect_id

    def get(self, rect_id: int):
        return self._rects.get(rect_id)

    def ids(self) -> list[int]:
        return sorted(self._rects)   # NOTE: z-order is id order; dict order is not, once a removal is undone
```

### Part 2

`remove` looks the rectangle up before changing anything, so a `KeyError` leaves the board untouched.
$O(1)$.

```python
def remove(self, rect_id: int) -> None:
    if rect_id not in self._rects:
        raise KeyError(rect_id)
    self._commit(Change(added=(), removed=((rect_id, self._rects[rect_id]),)))


Board.remove = remove
```

### Part 3

`_commit` is the only place that needs to know about history: it now records the change after applying
it. `undo` applies the inverse of the top change through `_apply`, not `_commit`, so that reverting is
itself not recorded. There is no redo, so nothing is pushed anywhere else. `undo` costs time
proportional to the size of the change.

```python
def _commit(self, change: Change) -> None:
    self._apply(change)
    self._history.append(change)    # NOTE: callers validate first, so a change is only recorded once it has happened


def undo(self) -> bool:
    if not self._history:
        return False
    self._apply(self._history.pop().inverse())   # NOTE: _apply, not _commit: an undo is not an operation
    return True


Board._commit = _commit
Board.undo = undo
```

The history holds one small tuple per operation and no copy of the board, so memory grows with the
number of operations, not with the board size times the number of operations.

### Part 4

Scan every rectangle, keep the largest id among those covering the cell, and delegate to `remove`.
$O(n)$ per call. The `ValueError` check comes first, so an out-of-board cell is an error and not just
an uncovered cell.

```python
def remove_at(self, x: int, y: int):
    if not (0 <= x < self.width and 0 <= y < self.height):
        raise ValueError(f"cell {(x, y)} is outside the board")
    best = None
    for rect_id, (x1, y1, x2, y2) in self._rects.items():
        if x1 <= x < x2 and y1 <= y < y2 and (best is None or rect_id > best):
            best = rect_id           # NOTE: compare ids, do not rely on the iteration order of the dict
    if best is not None:
        self.remove(best)            # NOTE: reuse remove, so this is recorded as exactly one operation
    return best


Board.remove_at = remove_at
```

For many rectangles the scan is the bottleneck. A *uniform grid index* fixes it: pick a bucket size
$s$ and keep, for each bucket (an $s \times s$ block of cells), the set of ids of rectangles that
intersect it. `remove_at` reads one bucket and takes the largest id that really covers the cell, so
its cost is the occupancy of one bucket, not $n$. `add` and `remove` insert into or delete from every
bucket the rectangle touches, $O((w/s + 1)(h/s + 1))$ for a $w \times h$ rectangle. Because every
mutation already goes through `_apply`, the index is maintained in that one function and neither
`undo` nor `remove_many` changes.

### Part 5

Validate the whole list first, then commit a single change whose `removed` holds every pair. Nothing is
modified before validation ends, which makes the call atomic; the change is recorded once, which makes
`undo` revert it as one step. $O(k)$ for $k$ ids.

```python
def remove_many(self, rect_ids: list[int]) -> None:
    rect_ids = list(rect_ids)
    if len(set(rect_ids)) != len(rect_ids):
        raise ValueError("duplicate id in batch")
    for rect_id in rect_ids:
        if rect_id not in self._rects:
            raise KeyError(rect_id)
    if not rect_ids:
        return                       # NOTE: an empty batch must not push an empty change onto the history
    self._commit(Change(added=(), removed=tuple((i, self._rects[i]) for i in rect_ids)))


Board.remove_many = remove_many
```

### Follow-ups

- Add `redo`: a second stack that `undo` pushes onto and every new operation clears; the `Change` already carries everything needed.
- Bound the history to the last $N$ operations by using a `deque(maxlen=N)`.
- Let a rectangle move or change z-order: z can no longer be the id, so store an explicit z-key per rectangle and make a move a change that removes and re-adds the pair.
- Group several calls into one undo step with `begin()` / `end()`: buffer the changes and merge them into one on `end`.
- Answer `topmost(x, y)` without removing, using the same grid index.

<details>
<summary>Checks (runnable)</summary>

```python
def attempt(fn, *args):
    try:
        return ("ok", fn(*args))
    except (ValueError, KeyError) as exc:
        return ("err", type(exc))


# every example in the problem statement, run as written
b = Board(8, 6)
assert [b.add(0, 0, 4, 3), b.add(2, 1, 6, 5), b.add(1, 1, 3, 2)] == [1, 2, 3]
assert b.ids() == [1, 2, 3] and b.get(2) == (2, 1, 6, 5) and b.get(9) is None
assert attempt(b.add, 5, 5, 5, 6) == ("err", ValueError)
assert attempt(b.add, 6, 0, 9, 2) == ("err", ValueError)
assert b.ids() == [1, 2, 3]

b.remove(2)
assert b.ids() == [1, 3] and attempt(b.remove, 2) == ("err", KeyError)
assert b.add(5, 0, 8, 2) == 4 and b.ids() == [1, 3, 4]

assert b.undo() and b.ids() == [1, 3]
assert b.undo() and b.ids() == [1, 2, 3] and b.get(2) == (2, 1, 6, 5)
assert b.add(0, 4, 2, 6) == 5
assert b.undo() and b.ids() == [1, 2, 3]
assert b.undo() and b.undo() and b.undo() and b.ids() == []
assert b.undo() is False

def fresh():
    board = Board(8, 6)
    board.add(0, 0, 4, 3); board.add(2, 1, 6, 5); board.add(1, 1, 3, 2)
    return board

b = fresh()
assert b.remove_at(2, 1) == 3 and b.remove_at(2, 1) == 2
assert b.remove_at(5, 4) is None and b.remove_at(4, 0) is None
assert attempt(b.remove_at, 8, 0) == ("err", ValueError)
assert b.undo() and b.ids() == [1, 2]                 # reverts the second remove_at
assert b.remove_at(2, 1) == 2                         # id 2 is topmost again

b = fresh()
b.remove_many([3, 1])
assert b.ids() == [2]
assert b.undo() and b.ids() == [1, 2, 3]
assert attempt(b.remove_many, [1, 9]) == ("err", KeyError) and b.ids() == [1, 2, 3]
assert attempt(b.remove_many, [2, 2]) == ("err", ValueError) and b.ids() == [1, 2, 3]
b.remove_many([])
assert b.undo() and b.ids() == [1, 2]                 # the empty batch left no history entry
```

```python
import random


class Model:
    """Written from the statement alone: a list of (id, rect) from bottom to top, one full snapshot
    per operation, and cell sets instead of coordinate comparisons."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.items, self.counter, self.snaps = [], 0, []

    def add(self, x1, y1, x2, y2):
        if not (0 <= x1 < x2 <= self.w and 0 <= y1 < y2 <= self.h):
            raise ValueError
        self.snaps.append(list(self.items))
        self.counter += 1
        self.items.append((self.counter, (x1, y1, x2, y2)))
        return self.counter

    def remove_ids(self, ids):
        have = [i for i, _ in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError
        if any(i not in have for i in ids):
            raise KeyError
        if ids:
            self.snaps.append(list(self.items))
            self.items = [(i, r) for i, r in self.items if i not in ids]

    def remove_at(self, x, y):
        if not (0 <= x < self.w and 0 <= y < self.h):
            raise ValueError
        for i, (x1, y1, x2, y2) in reversed(self.items):
            if (x, y) in {(cx, cy) for cx in range(x1, x2) for cy in range(y1, y2)}:
                self.remove_ids([i])
                return i
        return None

    def undo(self):
        if not self.snaps:
            return False
        self.items = self.snaps.pop()
        return True


def one_trial(seed, steps=80):
    rng = random.Random(seed)
    w, h = rng.randint(2, 7), rng.randint(2, 6)
    real, model = Board(w, h), Model(w, h)
    seen = dict(undo=0, undo_empty=0, batch=0, batch_err=0, at_hit=0, at_miss=0, deep=0)
    for _ in range(steps):
        op = rng.choice(["add", "add", "add", "remove", "undo", "at", "at", "many", "many"])
        top = model.counter + 2
        if op == "add":
            if rng.random() < 0.8:
                x1, y1 = rng.randint(0, w - 1), rng.randint(0, h - 1)
                args = (x1, y1, rng.randint(x1 + 1, w), rng.randint(y1 + 1, h))
            else:
                x1, y1 = rng.randint(-1, w + 1), rng.randint(-1, h + 1)
                args = (x1, y1, x1 + rng.randint(0, 3), y1 + rng.randint(0, 3))
            r1 = attempt(real.add, *args)
            r2 = attempt(model.add, *args)
        elif op == "remove":
            rid = rng.randint(1, top)
            r1, r2 = attempt(real.remove, rid), attempt(model.remove_ids, [rid])
        elif op == "undo":
            r1, r2 = real.undo(), model.undo()
            seen["undo"] += 1
            seen["undo_empty"] += not r1
        elif op == "at":
            x, y = rng.randint(-1, w), rng.randint(-1, h)
            r1, r2 = attempt(real.remove_at, x, y), attempt(model.remove_at, x, y)
            seen["at_hit"] += r1[0] == "ok" and r1[1] is not None
            seen["at_miss"] += r1[0] == "ok" and r1[1] is None
        else:
            have = [i for i, _ in model.items]
            ids = [rng.randint(1, top) for _ in range(rng.randint(0, 4))] if rng.random() < 0.5 \
                else rng.sample(have, min(len(have), rng.randint(0, 4)))
            r1, r2 = attempt(real.remove_many, ids), attempt(model.remove_ids, ids)
            seen["batch"] += len(ids) > 1 and r1[0] == "ok"
            seen["batch_err"] += r1[0] == "err"
        assert r1 == r2 or (r1[0] == "ok" and r2[0] == "ok" and r1[1] == r2[1]), (seed, op, r1, r2)
        assert real.ids() == [i for i, _ in model.items], (seed, op)
        assert all(real.get(i) == r for i, r in model.items)
        seen["deep"] += len(model.snaps) > 5
    while model.undo():
        assert real.undo() and real.ids() == [i for i, _ in model.items]
    assert real.undo() is False and real.ids() == []
    return seen


totals = {}
for seed in range(500):
    for key, val in one_trial(seed).items():
        totals[key] = totals.get(key, 0) + val
print("500 random runs agree with the snapshot model:", totals)
assert totals["undo_empty"] > 100 and totals["batch"] > 300 and totals["batch_err"] > 300
assert totals["at_hit"] > 500 and totals["at_miss"] > 300 and totals["deep"] > 5000
```

</details>

</details>
