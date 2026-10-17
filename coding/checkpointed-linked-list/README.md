# Linked List with Checkpoints

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Medium | SWE | linked-list, data-structure, indexing | 3 parts / 60 min | Onsite |
<!-- meta:end -->

## Problem

A *vector* (a dynamic array, like `std::vector` in C++ or `ArrayList` in Java) holds an ordered sequence of
`n >= 0` strings `a[0], ..., a[n-1]`; `n` is its *size*, and `i` in `a[i]` is the element's *index*.
Implement a vector whose elements are stored in a *singly linked list*: each element lives in a *node* with exactly
two fields, `value` (the string) and `next` (a reference to another node, or `None`). The vector object holds
`head`, a reference to one of the two *end nodes* of the chain, so that following `next` from `head` visits every node
once; which end is the head is up to the implementation. Elements may not be kept in a Python `list` or any
other container, and nodes carry no field besides these two. The operations are:

- `add(index, value)` for `0 <= index <= n`: inserts `value` so that it becomes `a[index]`; the old `a[index], ..., a[n-1]`
  move to indices `index+1, ..., n`. Any other `index` raises `IndexError`.
- `get(index)` for `0 <= index < n`: returns `a[index]`. Any other `index`, negative ones included, raises `IndexError`.
- `len(v)` returns `n`.

### Part 1 — plain singly linked list

`head` is the node holding `a[0]`. Implement `LinkedVector`; `add` and `get` may take $O(n)$ time.

```py
class LinkedVector:
    def __init__(self) -> None: ...
    def __len__(self) -> int: ...
    def add(self, index: int, value: str) -> None: ...
    def get(self, index: int) -> str: ...
```

Example:

```text
v = LinkedVector()
add(0, "pear")    # [pear]
add(1, "fig")     # [pear, fig]
add(1, "plum")    # [pear, plum, fig]
get(1)            # "plum"
add(3, "kiwi")    # [pear, plum, fig, kiwi]
add(0, "lime")    # [lime, pear, plum, fig, kiwi]
get(4)            # "kiwi"
get(5)            # IndexError
add(7, "x")       # IndexError
```

### Part 2 — exact checkpoints

Fix a positive integer `k`, given to the constructor (`ValueError` if it is not a positive `int`). The vector also
keeps `checkpoints`, a Python `list` of nodes in which `checkpoints[j]` is the node holding `a[j*k]`, for every `j`
with `j*k < n`. So `checkpoints` has `ceil(n/k)` entries, none when `n = 0`, and this must hold after every call to
`add`. Implement `CheckpointVector(k)` with the cost bounds below, where a *link read* is one read of a `next` field.

- `get` performs at most `k - 1` link reads.
- `add` performs at most `k + ceil(n/k)` link reads, takes $O(n/k + k)$ time and $O(1)$ extra space besides the
  `checkpoints` list. In particular it may not rebuild `checkpoints` by walking the whole chain.

```py
class CheckpointVector:
    def __init__(self, k: int) -> None: ...
    k: int                  # the spacing
    head: Node              # an end node; None when n = 0
    checkpoints: list       # checkpoints[j] is the node holding a[j*k]
    def __len__(self) -> int: ...
    def add(self, index: int, value: str) -> None: ...
    def get(self, index: int) -> str: ...
```

Example with `k = 3`, showing the values the checkpoints hold:

```text
add "a", "b", ..., "g" at indices 0, 1, ..., 6    # [a b c d e f g]   checkpoints: a d g   (indices 0 3 6)
add(1, "X")                                       # [a X b c d e f g] checkpoints: a c f
add(8, "h")                                       # [a X b c d e f g h]   checkpoints: a c f
add(9, "i")                                       # [a X b c d e f g h i] checkpoints: a c f i   (index 9 is new)
```

### Part 3 — choosing the spacing

No `k` is given. Implement `AutoVector()`, which chooses its own spacing, readable as the attribute `k`, and keeps the
Part 2 invariant for the current `k` after every call. After every call with `n >= 1`, `k` is an integer with
$\sqrt{n} \le k \le 2\sqrt{n}$. `get` performs at most `k - 1` link reads, so $O(\sqrt{n})$; any sequence of `m` calls
starting from the empty vector performs $O(m\sqrt{m})$ link reads and takes that much time in total.

```py
class AutoVector:
    def __init__(self) -> None: ...
    k: int                  # the current spacing, chosen by the vector
    def add(self, index: int, value: str) -> None: ...
    def get(self, index: int) -> str: ...
```

Example: after `add(i, "v" + str(i))` for `i = 0, ..., 9` (`n = 10`), any `k` in `{4, 5, 6}` is allowed; with `k = 4`
the checkpoints hold `v0, v4, v8`.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Points to confirm: `index == n` is a valid `add` (append) and negative indices are errors; the choice of which end
the head is belongs to the implementation, and Part 2 depends on it.

### Part 1

Walk from the head. `add` after position `index-1` needs the predecessor, so it stops one node early; `index == 0` is
the only case without a predecessor.

```python
class Node:
    __slots__ = ("value", "next")

    def __init__(self, value: str, next: "Node | None" = None):
        self.value = value
        self.next = next


class LinkedVector:
    """Part 1: head holds element 0, every operation walks from the head."""

    def __init__(self) -> None:
        self.head = None
        self._n_items = 0

    def __len__(self) -> int:
        return self._n_items

    def _node_at(self, i: int) -> Node:
        node = self.head
        for _ in range(i):
            node = node.next
        return node

    def add(self, index: int, value: str) -> None:
        if not 0 <= index <= self._n_items:  # warning: index == n is allowed (append), index == -1 is not
            raise IndexError(index)
        if index == 0:  # warning: no predecessor, the new node becomes the head
            self.head = Node(value, self.head)
        else:
            prev = self._node_at(index - 1)  # we insert after the predecessor, so we stop one node early
            prev.next = Node(value, prev.next)
        self._n_items += 1

    def get(self, index: int) -> str:
        if not 0 <= index < self._n_items:
            raise IndexError(index)
        return self._node_at(index).value
```

Both operations cost $O(n)$.

### Part 2

**Why the head must be the last element.** Insert at `index = i`. Every element with index at least `i` moves up by
one, and nodes never move, so the node that must be `checkpoints[j]` afterwards, for `j*k > i`, is the node that held
`a[j*k - 1]` before: the *predecessor in index order* of the old checkpoint. A node whose `next` leads to the larger
index (head = `a[0]`) cannot step to its predecessor; finding it costs a walk of up to `k` links per checkpoint, $O(n)$
in all, and storing the nodes before the checkpoints only moves the problem one node back. With the head holding `a[n-1]`
and `next` of the node holding `a[m]` leading to the node holding `a[m-1]`, the predecessor in index order is simply
`next`, and every later checkpoint moves by one link read.

**The invariant.** The chain is `head = node(a[n-1]) -> node(a[n-2]) -> ... -> node(a[0]) -> None`, and
`checkpoints[j] = node(a[j*k])`.

**`add(i, v)` with `i < n`.** Let `anchor = node(a[i])` and let `b` be the sequence after the insertion:
`b[m] = a[m]` for `m < i`, `b[i] = v`, `b[m] = a[m-1]` for `m > i`.

1. Link a new node after `anchor`: `new.next = anchor.next`, `anchor.next = new`. The chain now reads
   `node(a[n-1]) -> ... -> anchor -> new -> node(a[i-1]) -> ...`, which is the chain of `b` (`anchor` holds `b[i+1]`,
   `new` holds `b[i]`), and `head`, which holds `b[n] = a[n-1]`, is unchanged.
2. A checkpoint with `j*k < i` is unchanged, since `b[j*k] = a[j*k]` is the same node.
3. A checkpoint with `j*k = i` was `anchor`; `b[i]` is `new = anchor.next`.
4. A checkpoint with `i < j*k <= n-1` was `node(a[j*k])` and is not `anchor`; `b[j*k] = a[j*k-1]` is the node it linked to,
   which step 1 did not change. So steps 3 and 4 are the same statement: **after step 1, `checkpoints[j] = checkpoints[j].next`
   for every `j >= ceil(i/k)`**.
5. If `n` is a multiple of `k`, `b` has the new index `n = (n/k)*k`, and `b[n] = a[n-1]` is the old head; append it.

`add(n, v)` is a new head with no index changing, plus step 5 with `b[n] = v`.

**`get(i)`.** The nearest checkpoint at or above `i` is `j = ceil(i/k)`, holding `a[j*k]`, and the chain leads from larger
to smaller indices, so walk `j*k - i <= k-1` links. If `j*k > n-1` there is no such checkpoint; the head holds `a[n-1]`,
and `n-1-i < j*k - i <= k-1` links suffice.

**Cost of `add`.** At most `k-1` links to reach `anchor`, one for `anchor.next`, and one per shifted checkpoint, at most
`ceil(n/k)`: $O(n/k + k)$ time. Besides the `checkpoints` list, only a constant number of references are kept.

```python
class CheckpointVector:
    """Part 2: head holds the last element; node(a[m]).next is node(a[m-1]);
    checkpoints[j] is the node holding a[j*k]."""
    # an add at i moves every a[m] with m >= i up to m+1, and nodes never move,
    # so the new checkpoint j (j*k > i) is the node of a[j*k - 1], the predecessor of the old one
    # we put the head at a[n-1], so next is that predecessor and each checkpoint moves by one link read

    def __init__(self, k: int) -> None:
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("k must be a positive int")
        self.k = k
        self.head = None
        self.checkpoints = []
        self._n_items = 0

    def __len__(self) -> int:
        return self._n_items

    def _walk(self, node: Node, n_steps: int) -> Node:
        for _ in range(n_steps):
            node = node.next
        return node

    def _node_at(self, i: int) -> Node:
        j = -(-i // self.k)  # ceil(i / k): the nearest checkpoint at or above i
        if j < len(self.checkpoints):
            return self._walk(self.checkpoints[j], j * self.k - i)
        # warning: past the last checkpoint, we start from the head, which holds a[n-1]
        return self._walk(self.head, self._n_items - 1 - i)

    def get(self, index: int) -> str:
        if not 0 <= index < self._n_items:
            raise IndexError(index)
        return self._node_at(index).value

    def add(self, index: int, value: str) -> None:
        n, k = self._n_items, self.k
        if not 0 <= index <= n:
            raise IndexError(index)
        old_head = self.head
        if index == n:  # append: a new head, no index changes
            new = self.head = Node(value, old_head)
        else:
            # first we link the new node just below anchor
            anchor = self._node_at(index)  # holds a[index]; it will sit just above the new node
            new = Node(value, anchor.next)
            anchor.next = new  # warning: relink before shifting, the checkpoint at index itself moves to anchor.next
            # then every checkpoint at or above index takes one step toward smaller indices
            for j in range(-(-index // k), len(self.checkpoints)):
                self.checkpoints[j] = self.checkpoints[j].next
        if n % k == 0:  # index n is now occupied and is a multiple of k
            # warning: for index < n that node is the old head (a[n-1] moved up by one), not new
            self.checkpoints.append(new if index == n else old_head)
        self._n_items = n + 1
```

### Part 3

With a fixed `k`, `n/k + k` is smallest, `2 sqrt(n)`, at `k = sqrt(n)`, so `k` has to follow `n`. Keep `k` a power of two
with `n <= k*k`: before an `add` that would break it (`n == k*k`), double `k` and rebuild `checkpoints` in one walk from
the head, which holds `a[n-1]`, down to `a[0]`.

- `n <= k*k` holds after every call, so `k >= sqrt(n)`. Right after a doubling `n = (k/2)^2`, and `n` only grows, so
  `k/2 <= sqrt(n)` for good (for `n >= 1`): `k <= 2 sqrt(n)`.
- A call that does not rebuild costs `k - 1 + 1 + ceil(n/k) <= 3 sqrt(n) + 1` link reads (Part 2), and `get` at most
  `2 sqrt(n)`.
- Rebuilds happen at `n = 1, 4, 16, ..., 4^t`, each costing `n` link reads. Over `m` calls the sum is below
  `1 + 4 + ... + 4^t < 4m/3` (as `4^t < m`). Total: $O(m\sqrt{m})$.

```python
class AutoVector(CheckpointVector):
    """Part 3: the spacing k is a power of two with n <= k*k, doubled when n reaches k*k."""
    # with a fixed k an add costs n/k + k, which is smallest (2 sqrt(n)) at k = sqrt(n), so k has to follow n
    # we keep n <= k*k and double k when n reaches k*k, so sqrt(n) <= k <= 2 sqrt(n)

    def __init__(self) -> None:
        super().__init__(1)

    def _rebuild(self) -> None:
        n, k = self._n_items, self.k
        checkpoints = [None] * -(-n // k)  # ceil(n / k) entries
        node, index = self.head, n - 1  # the head holds a[n-1]; we walk down to a[0]
        while node is not None:
            if index % k == 0:
                checkpoints[index // k] = node
            node, index = node.next, index - 1
        self.checkpoints = checkpoints

    def add(self, index: int, value: str) -> None:
        if self._n_items == self.k * self.k:
            self.k *= 2  # warning: double before the add, so that n + 1 <= k*k afterwards
            self._rebuild()  # O(n) once per doubling: amortised O(1) per add
        super().add(index, value)
```

### Follow-ups

- `remove(index)` with the same exact invariant moves every later checkpoint to the node holding the next larger index;
  in this orientation that is the node that links *to* the checkpoint, which a singly linked chain cannot reach, and
  with the head at `a[0]` the mirror image holds for `add`. Both operations at once need a link back from each node: a doubly linked list
  moves every later checkpoint by one link read in either direction, $O(n/k + k)$ again.
- Relaxed design (unrolled linked list): a chain of blocks, each an array of at most `k` strings, plus a Fenwick tree over
  the block sizes. `get(i)` finds the block by prefix sums in $O(\log(n/k))$ and reads the slot; `add` shifts inside one
  block in $O(k)$, updates the tree in $O(\log(n/k))$, and splits a block that exceeds `k` into two halves, which
  rebuilds the tree in $O(n/k)$ but happens at most once per `k/2` inserts into that block; `remove` merges
  blocks symmetrically.
- The doubling rebuild is one call of cost $O(n)$; the worst case per call can be brought to $O(\sqrt{n})$ by building
  the next `checkpoints` list a few entries per call while the current one stays in use.
- Space beyond the `n` nodes is `ceil(n/k)` references, about $\sqrt{n}$ in Part 3; a larger `k` trades `get` and `add`
  time for less memory, down to `k >= n` where `checkpoints` has a single entry.

<details>
<summary>Checks (runnable)</summary>

```python
import math
import random


def expect(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


# Count every read of a `next` link, so that the link bounds in the statement can be asserted.
LINKS = [0]
_next_slot = Node.next


class CountingNode(Node):
    __slots__ = ()

    @property
    def next(self):
        LINKS[0] += 1
        return _next_slot.__get__(self)

    @next.setter
    def next(self, other):
        _next_slot.__set__(self, other)


RealNode, Node = Node, CountingNode


def chain(v):
    """All nodes from the head, followed through `next`."""
    out, node = [], v.head
    while node is not None:
        out.append(node)
        node = node.next
    return out


def check_state(v, model, k):
    """Independent check of the statement: size, contents, and checkpoints[j] holds index j*k."""
    n = len(model)
    nodes = chain(v)
    assert len(v) == n == len(nodes)
    assert len(v.checkpoints) == -(-n // k)
    values = [x.value for x in nodes]
    # the head is one of the two end nodes, so the chain reads the sequence in one of two directions
    if values == model and all(v.checkpoints[j] is nodes[j * k] for j in range(len(v.checkpoints))):
        return
    assert values == model[::-1], (values, model)
    assert all(v.checkpoints[j] is nodes[n - 1 - j * k] for j in range(len(v.checkpoints)))


def cp_values(v):
    return [x.value for x in v.checkpoints]


# --- Part 1: the example in the statement ---
v = LinkedVector()
v.add(0, "pear")
v.add(1, "fig")
v.add(1, "plum")
assert [v.get(i) for i in range(3)] == ["pear", "plum", "fig"]
v.add(3, "kiwi")
v.add(0, "lime")
assert [v.get(i) for i in range(5)] == ["lime", "pear", "plum", "fig", "kiwi"] and len(v) == 5
expect(IndexError, v.get, 5)
expect(IndexError, v.get, -1)
expect(IndexError, v.add, 6, "x")
expect(IndexError, v.add, -1, "x")

rng = random.Random(2024)
for _ in range(200):
    v, model = LinkedVector(), []
    for _ in range(rng.randint(0, 40)):
        index = rng.randint(0, len(model))
        word = rng.choice("abcdef")
        v.add(index, word)
        model.insert(index, word)
        assert [v.get(i) for i in range(len(model))] == model and len(v) == len(model)

# --- Part 2: the example in the statement ---
v = CheckpointVector(3)
for i, ch in enumerate("abcdefg"):
    v.add(i, ch)
assert cp_values(v) == ["a", "d", "g"]
v.add(1, "X")                                  # a X b c d e f g
assert cp_values(v) == ["a", "c", "f"]
v.add(8, "h")                                  # n = 9
assert cp_values(v) == ["a", "c", "f"]
v.add(9, "i")                                  # n = 10, index 9 is a multiple of 3
assert cp_values(v) == ["a", "c", "f", "i"]
assert "".join(v.get(i) for i in range(10)) == "aXbcdefghi"
expect(ValueError, CheckpointVector, 0)
expect(ValueError, CheckpointVector, -3)
expect(ValueError, CheckpointVector, 2.0)
expect(IndexError, v.add, 11, "x")
expect(IndexError, v.get, 10)
check_state(v, list("aXbcdefghi"), 3)


# --- Part 2: random operations against a Python list, with the link bounds ---
def exercise(make, steps, rng, bounds):
    v, model = make(), []
    for _ in range(steps):
        n = len(model)
        r = rng.random()
        if r < 0.65:
            index = rng.choice([0, n, rng.randint(0, n), rng.randint(0, n)])
            word = "w%d" % rng.randrange(8)          # repeated values on purpose
            k, before = v.k, LINKS[0]
            v.add(index, word)
            assert LINKS[0] - before <= bounds(n, k), (n, k, index)
            model.insert(index, word)
        elif r < 0.9 and n:
            index = rng.randrange(n)
            k, before = v.k, LINKS[0]
            assert v.get(index) == model[index]
            assert LINKS[0] - before <= k - 1
        else:
            expect(IndexError, v.add, rng.choice([-1, n + 1, n + 5]), "bad")
            expect(IndexError, v.get, rng.choice([-1, n, n + 3]))
        yield v, model


rng = random.Random(7)
ops = 0
for k in (1, 2, 3, 4, 5, 7, 8, 16):
    for _ in range(25):
        for v, model in exercise(lambda: CheckpointVector(k), rng.randint(1, 160), rng,
                                 lambda n, k: k + -(-n // k)):
            check_state(v, model, k)
            ops += 1
print("part 2 states checked:", ops)

# --- Part 3: the example in the statement ---
v = AutoVector()
for i in range(10):
    v.add(i, "v%d" % i)
assert 10 <= v.k * v.k <= 4 * 10 and v.k == 4
assert cp_values(v) == ["v0", "v4", "v8"]
check_state(v, ["v%d" % i for i in range(10)], v.k)


# --- Part 3: random operations; size bounds on k after every call, amortised link count ---
def part3_bounds(n, k):
    return 2 * k + -(-n // k) + n      # a call that doubles k also follows n links to rebuild


rng = random.Random(11)
for _ in range(60):
    for v, model in exercise(AutoVector, rng.randint(1, 300), rng, part3_bounds):
        n = len(model)
        if n:
            assert n <= v.k * v.k <= 4 * n and v.k & (v.k - 1) == 0, (n, v.k)
        check_state(v, model, v.k)

m = 3000
v, total = AutoVector(), 0
rebuilds = []
original_rebuild = v._rebuild
v._rebuild = lambda: (rebuilds.append(len(v)), original_rebuild())
for i in range(m):
    before = LINKS[0]
    v.add(rng.randint(0, i), "x")
    assert v.get(rng.randrange(i + 1)) == "x"
    total += LINKS[0] - before
assert rebuilds == [1, 4, 16, 64, 256, 1024], rebuilds
assert total <= 4 * m * math.isqrt(m), total
print("part 3 links for", m, "adds and gets:", total, "<=", 4 * m * math.isqrt(m))

Node = RealNode
print("all checks passed")
```

</details>

</details>
