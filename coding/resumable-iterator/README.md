# Resumable Iterators (1D, 2D, Arbitrary Depth)

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Medium | SWE | iterator, oop-design, state | 4 parts |
<!-- meta:end -->

## Problem

A *resumable iterator* produces items one at a time like an ordinary Python iterator, but can also
export its position with `get_state()` and later use `set_state(state)` to continue from that position,
exactly as if it had never stopped. Implement the following four parts.

Every iterator below walks data nested $d$ levels deep ($d = 1$ for a plain list): what $d$ indexing
steps reach, $\text{items}[i_1][i_2] \cdots [i_d]$, is an item, and items are produced in lexicographic
order of their *index tuples* $(i_1, \ldots, i_d)$ — for a matrix, row by row. States are such tuples:

- `get_state()` returns a `tuple` of $d$ non-negative `int`s: the index tuple of the item the next
  `__next__` call will produce. Once no item remains (the iterator is *exhausted*), it returns
  $(\text{len}(\text{items}), 0, \ldots, 0)$ instead.
- A tuple is *canonical* for given data if it is that exhausted tuple, or if at every level $k$,
  $0 \le i_k < \text{len}(L_k)$, where $L_k$ is the list reached by indexing $i_1, \ldots, i_{k-1}$
  ($L_1$ is `items`). These are exactly the tuples `get_state()` can return. The second condition rules out pointing into an empty list and
  pointing at the end of a non-empty one: in both cases the position has already moved on to the next
  item. For example, with rows `[[5, 7], [2]]` the position after 7 is `(1, 0)`, so `(0, 2)` is not
  canonical; with rows `[[], [4]]`, `(0, 0)` is not canonical because row 0 is empty.

`set_state(state)` checks, in this order: `TypeError` if `state` is not a tuple or a list, its length is
not $d$, or an element is not an `int` (a `bool` does not count as an `int`); otherwise `ValueError` if
`state` is not canonical for this iterator's own data. A rejected state leaves the iterator where it
was. Otherwise the next `__next__` call produces the item the tuple points to, or raises
`StopIteration` for the exhausted tuple. A list is accepted like a tuple, because a state that goes
through `json.dumps` / `json.loads` comes back as a list. `set_state` may move backward or forward,
including after `StopIteration` has been raised.

Because `set_state` judges a state only against the receiving iterator's own data, a state saved on one
instance can be given to another. On data of the same *shape* — every corresponding list, at every
level, has the same length; the items may differ — iteration continues exactly as it would have on the
original. On data of another shape, the state is accepted only if it is canonical there, and iteration
then continues from the item it points to in that data. Modifying a list after constructing an iterator
over it is outside this contract.

### Part 1 — Abstract interface

Define `ResumableIterator`, an abstract base class that every iterator below inherits from, declaring
`__iter__`, `__next__`, `get_state`, and `set_state` as abstract methods with the contract above.

```py
class ResumableIterator(ABC):
    @abstractmethod
    def __iter__(self) -> "ResumableIterator": ...

    @abstractmethod
    def __next__(self):
        """Returns the next item. Raises StopIteration once none remain."""

    @abstractmethod
    def get_state(self) -> tuple:
        """Returns a copyable, JSON-serializable tuple describing the current position."""

    @abstractmethod
    def set_state(self, state) -> None:
        """Moves to the position state describes. Raises TypeError or ValueError as specified above."""
```

### Part 2 — 1D list

`items` is a plain Python list of any length, possibly empty. Implement `ResumableListIterator(items)`;
it produces `items[0], items[1], ...` in order.

```py
class ResumableListIterator(ResumableIterator):
    def __init__(self, items: list) -> None:
        """items may be empty."""
```

Example:

```text
items = [68, 71, 74, 70, 73, 69]

next -> 68
next -> 71
next -> 74
state = get_state()      # (3,)
next -> 70
set_state(state)
next -> 70                # produced again
next -> 73
next -> 69
next -> StopIteration
```

### Part 3 — 2D list (matrix)

`items` is a list of lists (*rows*); any row may be empty, including the first, the last, or all of
them. Implement `Resumable2DIterator(items)`; it produces the elements of `items[0]`, then `items[1]`,
and so on, skipping every empty row.

```py
class Resumable2DIterator(ResumableIterator):
    def __init__(self, items: list) -> None:
        """items is a list of lists; a row may be empty."""
```

Example:

```text
items = [[7, 2], [], [9], [], [3, 5, 1]]

next -> 7
next -> 2
state = get_state()      # (2, 0) -- already past the empty row 1, pointing at the 9 in row 2
next -> 9
set_state(state)
next -> 9                 # produced again
next -> 3
next -> 5
next -> 1
next -> StopIteration
get_state()               # (5, 0) -- exhausted
```

`Resumable2DIterator([[], []])` produces nothing; its `get_state()` is `(2, 0)` from the start.

### Part 4 — nested lists of arbitrary depth

`items` is nested `depth` levels deep ($\text{depth} = d \ge 1$): whatever `depth` indexing steps reach
is an item, even if it is itself a list. A list at any level may be empty. Implement
`ResumableNestedIterator(items, depth)`; with `depth=1` or `depth=2` it behaves exactly like Part 2's or
Part 3's iterator.

```py
class ResumableNestedIterator(ResumableIterator):
    def __init__(self, items: list, depth: int) -> None:
        """items is nested depth levels deep, depth >= 1; a list at any level may be empty."""
```

Example with `depth=3`:

```text
items = [
    [[5, 3], []],
    [],
    [[], [9, 1]],
    [[6]],
]

next -> 5
next -> 3
state = get_state()      # (2, 1, 0) -- skipped items[0][1], items[1] and items[2][0], all empty
next -> 9
set_state(state)
next -> 9                 # produced again
next -> 1
next -> 6
next -> StopIteration
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Write the tests for the awkward positions before the code: a save just before a run of empty lists, a
save after exhaustion, a state that has been through JSON, a tuple `get_state` could never return.

### Part 1

The base class carries no logic, only the contract; the type check is shared by all three iterators.

```python
from abc import ABC, abstractmethod


class ResumableIterator(ABC):
    @abstractmethod
    def __iter__(self):
        return self

    @abstractmethod
    def __next__(self):
        ...

    @abstractmethod
    def get_state(self):
        ...

    @abstractmethod
    def set_state(self, state) -> None:
        ...


def _check_index_tuple(state, length):
    # NOTE: bool is a subclass of int, so isinstance(True, int) is True
    if (not isinstance(state, (tuple, list)) or len(state) != length
            or not all(isinstance(v, int) and not isinstance(v, bool) for v in state)):
        raise TypeError(f"expected a {length}-tuple of ints, got {state!r}")
    return tuple(state)          # NOTE: a state that went through JSON arrives as a list
```

### Part 2

One index, advanced by one on every call; `len(items)` is the exhausted state.

```python
class ResumableListIterator(ResumableIterator):
    def __init__(self, items):
        self.items = items
        self._pos = 0                                 # index of the next element to produce

    def __iter__(self):
        return self

    def __next__(self):
        pos = self._pos
        if pos == len(self.items):                    # the exhausted state; set_state never goes past it
            raise StopIteration
        self._pos = pos + 1
        return self.items[pos]

    def get_state(self):
        return (self._pos,)

    def set_state(self, state):
        (pos,) = _check_index_tuple(state, 1)
        if not 0 <= pos <= len(self.items):          # NOTE: '<=': pos == len(items) is exhausted
            raise ValueError(f"{state!r} is not a canonical position")
        self._pos = pos
```

### Part 3

Two indices, `_outer` and `_inner`. `_skip_empty` runs at construction and after every `__next__`, so the
pair is always canonical and `get_state` just reads it off. Skipping lazily at the start of `__next__`
instead would leave `(0, 2)` behind after the 2 in the Part 3 example, a state `set_state` must reject.

```python
class Resumable2DIterator(ResumableIterator):
    def __init__(self, items):
        self.items = items
        self._outer = 0
        self._inner = 0
        self._skip_empty()

    def _skip_empty(self):
        while self._outer < len(self.items) and self._inner >= len(self.items[self._outer]):
            self._outer += 1
            self._inner = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._outer >= len(self.items):
            raise StopIteration
        item = self.items[self._outer][self._inner]
        self._inner += 1
        self._skip_empty()              # NOTE: right away, not before producing the next item
        return item

    def get_state(self):
        return (self._outer, self._inner)

    def set_state(self, state):
        outer, inner = _check_index_tuple(state, 2)
        exhausted = (outer, inner) == (len(self.items), 0)
        inside = 0 <= outer < len(self.items) and 0 <= inner < len(self.items[outer])
        if not (exhausted or inside):   # NOTE: strict '<': inner == len(row) is not canonical
            raise ValueError(f"{state!r} is not a canonical position")
        self._outer, self._inner = outer, inner
```

### Part 4

Part 3 generalizes to a stack of `(container, index)` frames, one per level; an empty stack means
exhausted. `_advance` decides whether to descend by *counting* levels (`len(self._stack) < self.depth`),
not by testing `isinstance(x, list)`: at `depth=1`, `[[], [], []]` holds three items that happen to be
empty lists, and an `isinstance` test would skip all three as empty branches.

```python
class ResumableNestedIterator(ResumableIterator):
    def __init__(self, items, depth):
        self.items = items
        self.depth = depth
        self._stack = [(items, 0)]
        self._advance()

    def _advance(self):
        while self._stack:
            container, idx = self._stack[-1]
            if idx >= len(container):
                self._stack.pop()
                if self._stack:
                    parent, pidx = self._stack[-1]
                    self._stack[-1] = (parent, pidx + 1)
                continue
            if len(self._stack) < self.depth:
                self._stack.append((container[idx], 0))
            else:
                return                   # top of stack points at the next item

    def __iter__(self):
        return self

    def __next__(self):
        if not self._stack:
            raise StopIteration
        container, idx = self._stack[-1]
        item = container[idx]
        self._stack[-1] = (container, idx + 1)
        self._advance()
        return item

    def _exhausted_state(self):
        return (len(self.items),) + (0,) * (self.depth - 1)

    def get_state(self):
        if not self._stack:              # NOTE: the empty stack alone would give (), not a d-tuple
            return self._exhausted_state()
        return tuple(idx for _, idx in self._stack)

    def set_state(self, state):
        indices = _check_index_tuple(state, self.depth)
        if indices == self._exhausted_state():
            self._stack = []
            return
        stack, container = [], self.items
        for idx in indices:
            if not 0 <= idx < len(container):    # NOTE: the same strict '<' at every level
                raise ValueError(f"{state!r} is not a canonical position")
            stack.append((container, idx))
            container = container[idx]
        self._stack = stack
```

A full pass does $O(N + M)$ work in total for $N$ items and $M$ lists at all levels, because `_advance`
pushes and pops each list once; a single `__next__` can still cost $O(M)$ when it has to skip a long run
of empty lists. `get_state` and `set_state` cost $O(\text{depth})$, and the iterator keeps
$O(\text{depth})$ extra state however many items there are. Flattening into one list and reusing Part 2
is simpler, but costs $O(N)$ memory, and its state, a single flat position, is not the index tuple the
contract asks for.

### Follow-ups

- Iterating the lines of a file instead: the state is the byte offset from `f.tell()`, and `set_state`
  reopens the file and seeks there; the handle itself never goes into the state. Open the file in binary
  mode: in text mode, `f.tell()` after `next(f)` raises `OSError: telling position disabled by next() call`.
- To reject a state saved on differently shaped data, compute a fingerprint of the shape at
  construction (for example a hash of every list's length), put it in the state, and compare it in
  `set_state`.
- A generator object cannot be copied or pickled (`TypeError: cannot pickle 'generator' object`), so a
  plain generator traversal can only be restored by rerunning it and discarding every item it had
  already produced.
- The classes only use `len()` and indexing, so tuples and NumPy arrays work unchanged: items come out
  as NumPy scalars, while the state stays plain `int`s.

<details>
<summary>Checks (runnable)</summary>

```python
import copy
import io
import json
import random

import numpy as np


def expect(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


# --- the examples in the statement ---
it = ResumableListIterator([68, 71, 74, 70, 73, 69])
assert [next(it), next(it), next(it)] == [68, 71, 74]
s = it.get_state()
assert s == (3,) and next(it) == 70
it.set_state(s)
assert list(it) == [70, 73, 69] and it.get_state() == (6,)

it2 = Resumable2DIterator([[7, 2], [], [9], [], [3, 5, 1]])
assert [next(it2), next(it2)] == [7, 2]
s2 = it2.get_state()
assert s2 == (2, 0) and next(it2) == 9
it2.set_state(s2)
assert list(it2) == [9, 3, 5, 1] and it2.get_state() == (5, 0)
empty_rows = Resumable2DIterator([[], []])
assert empty_rows.get_state() == (2, 0) and list(empty_rows) == []
rows = Resumable2DIterator([[5, 7], [2]])
assert [next(rows), next(rows)] == [5, 7] and rows.get_state() == (1, 0)
expect(ValueError, rows.set_state, (0, 2))
expect(TypeError, rows.set_state, (0, True))
expect(ValueError, Resumable2DIterator([[], [4]]).set_state, (0, 0))

data3 = [[[5, 3], []], [], [[], [9, 1]], [[6]]]
it3 = ResumableNestedIterator(data3, depth=3)
assert [next(it3), next(it3)] == [5, 3]
s3 = it3.get_state()
assert s3 == (2, 1, 0) and next(it3) == 9
it3.set_state(json.loads(json.dumps(s3)))          # a list after the JSON round trip
assert list(it3) == [9, 1, 6] and it3.get_state() == (4, 0, 0)
it3.set_state((4, 0, 0))
expect(StopIteration, next, it3)
# depth counts levels; what an item is does not matter
assert list(ResumableNestedIterator([[], [8], []], depth=1)) == [[], [8], []]


# --- independent oracle, written from the statement: enumerate every index tuple ---
class NaiveIterator:
    def __init__(self, items, d):
        self.items, self.d, self.pos = items, d, 0
        self.paths, self.empty_lists = [], []

        def walk(x, prefix):
            if len(prefix) == d:
                self.paths.append(prefix)
                return
            if len(x) == 0:
                self.empty_lists.append(prefix)
            for i in range(len(x)):
                walk(x[i], prefix + (i,))

        walk(items, ())
        self.end = (len(items),) + (0,) * (d - 1)

    def state(self):
        return self.paths[self.pos] if self.pos < len(self.paths) else self.end

    def next(self):
        if self.pos == len(self.paths):
            raise StopIteration
        x = self.items
        for i in self.paths[self.pos]:
            x = x[i]
        self.pos += 1
        return x

    def seek(self, s):
        if not isinstance(s, (tuple, list)) or len(s) != self.d or any(type(v) is not int for v in s):
            raise TypeError
        if tuple(s) == self.end:
            self.pos = len(self.paths)
        elif tuple(s) in self.paths:
            self.pos = self.paths.index(tuple(s))
        else:
            raise ValueError

    def rest(self):
        return [self.next() for _ in range(len(self.paths) - self.pos)]

    def skipped_empty(self):
        """Whether an empty list lies between the last produced item and the next one."""
        lo = self.paths[self.pos - 1] if self.pos else ()
        return any(lo < e < self.state() for e in self.empty_lists)   # tuples compare in walk order


def gen(rng, d, max_len=3):
    if d == 1:
        return [rng.randint(0, 9) for _ in range(rng.randint(0, max_len))]
    return [[] if rng.random() < 0.35 else gen(rng, d - 1) for _ in range(rng.randint(0, max_len))]


def relabel(x, d):
    return [v + 100 for v in x] if d == 1 else [relabel(sub, d - 1) for sub in x]


def random_state(rng, naive):
    """Mostly near misses: a real position nudged by one, or small ints with the odd bool or float."""
    if rng.random() < 0.3 and naive.paths:
        s = list(rng.choice(naive.paths))
        s[rng.randrange(naive.d)] += rng.choice([-1, 1])
    else:
        s = [rng.choice([-1, True, False, 1.0]) if rng.random() < 0.1 else rng.randint(0, 3)
             for _ in range(naive.d + rng.choice([0, 0, 0, 0, -1, 1]))]
    return tuple(s) if rng.random() < 0.5 else s


def outcome(fn, *args):
    try:
        return ("ok", fn(*args))
    except (StopIteration, TypeError, ValueError) as e:
        return (type(e).__name__,)


def makers(d):
    out = [lambda data: ResumableNestedIterator(data, d)]
    if d == 1:
        out.append(ResumableListIterator)
    if d == 2:
        out.append(Resumable2DIterator)
    return out


rng = random.Random(0)
cov = dict(skip_saves=0, end_saves=0, TypeError=0, ValueError=0, ok=0, other_shape_ok=0, other_shape_bad=0)
for d in (1, 2, 3, 4):
    for _ in range(500):
        data = gen(rng, d)
        for make in makers(d):
            it, naive, pool = make(data), NaiveIterator(data, d), []
            for _ in range(25):
                r = rng.random()
                if r < 0.45:
                    assert outcome(next, it) == outcome(naive.next), data
                elif r < 0.6:
                    s = it.get_state()
                    assert type(s) is tuple and s == naive.state(), (data, s, naive.state())
                    pool.append(s)
                    cov["skip_saves"] += naive.skipped_empty()
                    cov["end_saves"] += s == naive.end
                elif r < 0.75 and pool:
                    s = json.loads(json.dumps(rng.choice(pool)))
                    it.set_state(s)
                    naive.seek(s)
                else:
                    s = random_state(rng, naive)
                    got = outcome(it.set_state, s)
                    assert got == outcome(naive.seek, s), (data, s, got)
                    cov[got[0]] += 1
                assert it.get_state() == naive.state(), data      # also after a rejected state
            # hand the state to an iterator over other data: same shape, then a random shape
            s = it.get_state()
            for other, same_shape in ((relabel(data, d), True), (gen(rng, d), False)):
                it_o, naive_o = make(other), NaiveIterator(other, d)
                got = outcome(it_o.set_state, s)
                assert got == outcome(naive_o.seek, s), (data, other, s)
                if got[0] == "ok":
                    assert list(it_o) == naive_o.rest()
                if not same_shape:
                    cov["other_shape_ok" if got[0] == "ok" else "other_shape_bad"] += 1
print(cov)
assert min(cov.values()) > 300, cov

# --- follow-ups ---
buf = io.TextIOWrapper(io.BytesIO(b"alpha\nbeta\n"))
next(buf)
expect(OSError, buf.tell)                       # text mode: telling position disabled by next() call
raw = io.BufferedReader(io.BytesIO(b"alpha\nbeta\n"))
next(raw)
assert raw.tell() == 6

gen_it = (x for row in [[7, 2], [9]] for x in row)
next(gen_it)
try:
    copy.deepcopy(gen_it)
    raise AssertionError
except TypeError as e:
    assert "cannot pickle 'generator' object" in str(e)

cube = ResumableNestedIterator(np.arange(24).reshape(2, 3, 4), depth=3)
assert [int(next(cube)) for _ in range(9)] == list(range(9))
s_np = cube.get_state()
assert s_np == (0, 2, 1) and all(type(v) is int for v in s_np)
cube.set_state(json.loads(json.dumps(s_np)))
assert [int(v) for v in cube] == list(range(9, 24))
assert list(Resumable2DIterator(np.zeros((3, 0)))) == []
assert list(Resumable2DIterator(((4, 1), (), (8,)))) == [4, 1, 8]
print("all checks passed")
```

</details>

</details>
