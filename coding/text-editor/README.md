# Text Editor: Buffer, Undo, Autocomplete

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Coding · object-oriented design | ★★★☆☆ | Medium | SWE · RE | data-structure, stack, trie, collaboration | 4 parts | Phone screen · Onsite |
<!-- meta:end -->

## Problem

Build up a text editor's backend in four stages, each adding methods to the same `TextBuffer`
class. Positions are always character offsets into the buffer, counted from 0; a range `[start, end)`
is half-open (`start` included, `end` excluded), following the usual slicing convention.

### Part 1 — Buffer: insert, delete, read

```py
class TextBuffer:
    def __init__(self, text: str = "") -> None:
        """Starts with these initial contents."""

    def __len__(self) -> int:
        """The current length, in characters."""

    def text(self) -> str:
        """The entire contents, equivalent to read(0, len(self))."""

    def insert(self, pos: int, text: str) -> None:
        """Inserts text so its first character lands at offset pos, shifting every character
        currently at or after pos to the right by len(text). Requires 0 <= pos <= len(self);
        raises IndexError otherwise."""

    def delete(self, start: int, end: int) -> str:
        """Removes the half-open range [start, end) and returns the removed text ("" if start == end).
        Requires 0 <= start <= end <= len(self); raises IndexError otherwise."""

    def read(self, start: int, end: int) -> str:
        """Returns [start, end) without modifying the buffer. Same bounds as delete."""
```

For example:

```text
buf = TextBuffer("draft notes")
len(buf)                      # 11
buf.insert(5, " short")
buf.text()                    # "draft short notes"
buf.read(0, 5)                # "draft"
buf.read(5, 11)               # " short"
buf.delete(5, 11)             # " short"
buf.text()                    # "draft notes"

buf.insert(100, "x")          # IndexError
buf.delete(3, 1)              # IndexError -- start > end
```

### Part 2 — Undo and redo

`TextBuffer` grows `undo` and `redo`, backed by two stacks. Each call to `insert` or `delete` that
actually changes the buffer (a non-empty `text`, or a non-empty `[start, end)`) is one undoable
operation; a call that changes nothing is not recorded and does not disturb either stack. `undo`
reverses the most recently recorded operation and returns `True`, or leaves the buffer alone and
returns `False` if there is nothing left to undo. `redo` re-applies the most recently undone
operation and returns `True`, or returns `False` if there is nothing to redo. Recording a new
operation (a real `insert` or `delete`, never `undo` or `redo` itself) clears the redo stack.

```py
def undo(self) -> bool:
    """Reverses the most recent recorded insert/delete. Returns whether there was one to reverse."""

def redo(self) -> bool:
    """Re-applies the most recently undone operation. Returns whether there was one to redo."""
```

For example:

```text
buf = TextBuffer("cat")
buf.insert(3, "s")            # "cats"
buf.insert(0, "wild")         # "wildcats"
buf.undo()                    # True  -> "cats"
buf.undo()                    # True  -> "cat"
buf.redo()                    # True  -> "cats"
buf.insert(4, "!")            # "cats!" -- a new edit, so the pending "wild" redo is discarded
buf.redo()                    # False -- nothing left to redo
buf.undo(); buf.undo()        # -> "cats" -> "cat"
buf.undo()                    # False -- nothing left to undo
```

### Part 3 — Autocomplete

`TextBuffer` grows `suggest`, backed by a prefix tree (trie) with a frequency count at each word. A
*word* is a maximal run of the letters `A`–`Z` and `a`–`z` (case-sensitive, so `"The"` and `"the"` are
different words). The vocabulary is exactly the words that currently appear in the buffer's contents:
a word's frequency is how many times it currently occurs, and deleting its only occurrence removes it
from the vocabulary. `suggest(prefix, k)` returns up to `k` words that start with `prefix`, ordered by
frequency (most frequent first); words tied on frequency are ordered by comparing them as strings,
uppercase before lowercase (`"Zoo"` before `"apple"`). `prefix = ""` matches every word; if fewer than
`k` words match, all of them are returned. `k = 0` returns `[]`, and `k < 0` raises `ValueError`.

```py
def suggest(self, prefix: str, k: int) -> list[str]:
    """Up to k words of the buffer's current vocabulary that start with prefix, highest frequency
    first, ties broken by string order (uppercase before lowercase)."""
```

For example:

```text
buf = TextBuffer("")
buf.insert(0, "the cat sat on the mat")
buf.suggest("ca", 5)          # ["cat"]
buf.suggest("t", 5)           # ["the"]
buf.suggest("", 3)            # ["the", "cat", "mat"]  -- "the" occurs twice; the four words that
                              #   occur once ("cat", "mat", "on", "sat") follow in string order
buf.delete(4, 8)              # removes "cat ", the only occurrence of "cat"
buf.suggest("ca", 5)          # []
```

### Part 4 — Concurrent editing

Several replicas edit the same document at once, each identified by a unique `site_id`. A replica
exposes:

```py
class CRDTDoc:
    def __init__(self, site_id: str) -> None:
        """A single replica, starting from an empty document."""

    def text(self) -> str:
        """This replica's current visible document."""

    def local_insert(self, index: int, ch: str) -> object:
        """Inserts one character (len(ch) == 1) at visible index (0 <= index <= len(text())) as a
        local edit, and returns an operation to broadcast to every other replica."""

    def local_delete(self, index: int) -> object:
        """Deletes the visible character at index (0 <= index < len(text())) as a local edit, and
        returns an operation to broadcast."""

    def apply(self, op: object) -> None:
        """Applies an operation returned by local_insert/local_delete on some replica (including
        this one). apply is idempotent: applying the same operation twice has no further effect."""
```

A multi-character edit is just several `local_insert` calls. An operation returned by one replica is
eventually delivered, via `apply`, to every other replica; delivery from one specific replica to
another preserves that replica's own generation order (as a reliable point-to-point connection would).
Nothing else is ordered: operations issued on different replicas, and the receiving replica's own local
edits, may interleave arbitrarily, so a deletion can reach a replica that has not yet seen the
character it deletes, and the same operation may be delivered more than once. Design the
representation of an operation, a character and its position however you like. The one requirement:
once two replicas have applied the same set of operations, `text()` must agree on both, however the
deliveries were interleaved along the way.

```text
a, b = CRDTDoc("A"), CRDTDoc("B")     # both start empty
op1 = a.local_insert(0, "H")          # replica A, locally: "H" -- b has not seen this yet
op2 = b.local_insert(0, "i")          # replica B, locally: "i" -- concurrently, a has not seen this
b.apply(op1)                          # the two operations arrive in whichever order
a.apply(op2)
assert a.text() == b.text()           # both must end up with the same document
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming up front: character offsets rather than (row, column) positions, and a small CRDT
for Part 4 rather than operational transformation.

### Part 1

The buffer is a Python `list` of characters, not a `str`; slice assignment does the shifting for both
`insert` and `delete`, each $O(n)$ in the number of characters that move.

```python
class TextBuffer:
    def __init__(self, text: str = "") -> None:
        self._chars = list(text)

    def __len__(self) -> int:
        return len(self._chars)

    def text(self) -> str:
        return "".join(self._chars)

    def insert(self, pos: int, text: str) -> None:
        if not 0 <= pos <= len(self):
            raise IndexError(f"insert position {pos} out of range for length {len(self)}")
        self._chars[pos:pos] = text                # NOTE: slice-assignment insert, no separate loop

    def delete(self, start: int, end: int) -> str:
        if not 0 <= start <= end <= len(self):
            raise IndexError(f"delete range [{start}, {end}) out of range for length {len(self)}")
        removed = self._chars[start:end]
        del self._chars[start:end]
        return "".join(removed)

    def read(self, start: int, end: int) -> str:
        if not 0 <= start <= end <= len(self):
            raise IndexError(f"read range [{start}, {end}) out of range for length {len(self)}")
        return "".join(self._chars[start:end])
```

### Part 2

`insert` and `delete` are redefined and reattached to `TextBuffer`, keeping each Part self-contained;
`_stacks` lazily creates the two lists, since Part 1's `__init__` doesn't know them. `undo`/`redo`
replay through the *original* `insert`/`delete`, so reversing an edit is never itself recorded.

```python
_insert_without_undo = TextBuffer.insert
_delete_without_undo = TextBuffer.delete


def _stacks(self):
    if not hasattr(self, "_undo_stack"):
        self._undo_stack, self._redo_stack = [], []
    return self._undo_stack, self._redo_stack


def insert(self, pos: int, text: str) -> None:
    _insert_without_undo(self, pos, text)
    undo_stack, redo_stack = _stacks(self)
    if text:
        undo_stack.append(("insert", pos, text))
        redo_stack.clear()


def delete(self, start: int, end: int) -> str:
    removed = _delete_without_undo(self, start, end)
    undo_stack, redo_stack = _stacks(self)
    if removed:
        undo_stack.append(("delete", start, removed))
        redo_stack.clear()
    return removed


def undo(self) -> bool:
    undo_stack, redo_stack = _stacks(self)
    if not undo_stack:
        return False
    kind, pos, payload = undo_stack.pop()
    if kind == "insert":
        _delete_without_undo(self, pos, pos + len(payload))
    else:
        _insert_without_undo(self, pos, payload)
    redo_stack.append((kind, pos, payload))
    return True


def redo(self) -> bool:
    undo_stack, redo_stack = _stacks(self)
    if not redo_stack:
        return False
    kind, pos, payload = redo_stack.pop()
    if kind == "insert":
        _insert_without_undo(self, pos, payload)
    else:
        _delete_without_undo(self, pos, pos + len(payload))
    undo_stack.append((kind, pos, payload))
    return True


TextBuffer.insert = insert
TextBuffer.delete = delete
TextBuffer.undo = undo
TextBuffer.redo = redo
```

### Part 3

`suggest` rebuilds the trie from scratch each call: tokenize the current text, count with `Counter`,
insert each word letter by letter, storing its count at the last node. A query walks to the prefix's
node ($O(\lvert \text{prefix} \rvert)$), depth-first-collects that subtree, and sorts the $m$ words it
found: $O(n + m \log m)$ for a buffer of $n$ characters. Frequent queries would keep the trie between
calls and update it inside `insert`/`delete` instead.

```python
import re
from collections import Counter

_WORD_RE = re.compile(r"[A-Za-z]+")


class _TrieNode:
    __slots__ = ("children", "count")

    def __init__(self):
        self.children: dict[str, "_TrieNode"] = {}
        self.count = 0                  # NOTE: 0 unless this node ends a word that occurs in the buffer


def _build_trie(words: Counter) -> _TrieNode:
    root = _TrieNode()
    for word, count in words.items():
        node = root
        for ch in word:
            node = node.children.setdefault(ch, _TrieNode())
        node.count = count
    return root


def suggest(self, prefix: str, k: int) -> list[str]:
    if k < 0:
        raise ValueError(f"k must be >= 0, got {k}")
    root = _build_trie(Counter(_WORD_RE.findall(self.text())))
    node = root
    for ch in prefix:
        if ch not in node.children:
            return []
        node = node.children[ch]
    matches: list[tuple[str, int]] = []

    def collect(n: _TrieNode, built: str) -> None:
        if n.count:
            matches.append((built, n.count))
        for ch, child in n.children.items():
            collect(child, built + ch)

    collect(node, prefix)
    matches.sort(key=lambda item: (-item[1], item[0]))   # NOTE: frequency first, then string order
    return [word for word, _ in matches[:k]]


TextBuffer.suggest = suggest
```

### Part 4

Every character gets an absolute, self-contained position: a `Fraction` strictly between the positions
of its two visible neighbours at the moment it is typed (0 and 1 are the document's fixed ends), tagged
with `(site_id, a local counter)` to make it unique. A position never refers to another operation —
unlike a scheme naming a left neighbour by id (RGA, WOOT) — so a replica's entire state is two sets:
the inserts it has applied, and the ids of characters deleted anywhere. `text()` sorts the first by
`(pos, site, seq)` and hides the second, so it depends on the *set* of operations applied and not on
their arrival order: a repeated delivery, or a deletion overtaking its own character, lands on the same
document. The point in the gap is **random** rather than its midpoint, so two replicas filling the same
gap get different positions and a later insert between those two characters still has room.

```python
import bisect
import random
from fractions import Fraction

_RAND_DENOM = 2 ** 32


class CRDTDoc:
    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        self._counter = 0
        self._entries = []       # (pos, site, seq, ch) tuples, kept sorted
        self._inserted = set()   # (site, seq) of inserts already applied
        self._deleted = set()    # (site, seq) of characters deleted on any replica

    def _live(self) -> list:
        return [e for e in self._entries if (e[1], e[2]) not in self._deleted]

    def text(self) -> str:
        return "".join(e[3] for e in self._live())

    def local_insert(self, index: int, ch: str):
        if len(ch) != 1:
            raise ValueError(f"local_insert takes exactly one character, got {ch!r}")
        live = self._live()
        if not 0 <= index <= len(live):
            raise IndexError(f"insert index {index} out of range for length {len(live)}")
        left = live[index - 1][0] if index > 0 else Fraction(0)
        right = live[index][0] if index < len(live) else Fraction(1)
        pos = left + (right - left) * Fraction(random.randint(1, _RAND_DENOM - 1), _RAND_DENOM)
        self._counter += 1
        op = ("insert", pos, self.site_id, self._counter, ch)
        self.apply(op)
        return op

    def local_delete(self, index: int):
        live = self._live()
        if not 0 <= index < len(live):
            raise IndexError(f"delete index {index} out of range for length {len(live)}")
        op = ("delete", live[index][1], live[index][2])
        self.apply(op)
        return op

    def apply(self, op) -> None:
        if op[0] == "insert":
            _, pos, site, seq, ch = op
            if (site, seq) in self._inserted:    # NOTE: a replayed insert changes nothing
                return
            self._inserted.add((site, seq))
            bisect.insort(self._entries, (pos, site, seq, ch))
        else:
            _, site, seq = op
            # NOTE: the id may arrive before the insert that creates the character
            self._deleted.add((site, seq))
```

Two replicas that have applied the same operations hold the same two sets, so they sort the same
entries and hide the same ids: the documents agree whatever the deliveries did. One run of the example
above converges both replicas to `text() == "iH"`.

### Follow-ups

- Two random fractions can collide in principle: the replicas still agree, but a character inserted
  between that pair can no longer be placed strictly between them and may end up on the wrong side of
  one of them. Logoot and LSEQ make a position a list of levels and add a level when a gap runs out.
- Both id sets grow for the lifetime of the document; collecting them needs every replica to confirm it
  has applied an operation, which is what a version vector exchanged between replicas is for.
- `local_insert` takes one character so every operation has exactly one id, which lets a concurrent
  edit land inside a multi-character paste — the trade-off RGA and WOOT make too. Deleting a range
  costs one operation per character, which a real implementation would batch into one wire message.

<details>
<summary>Checks (runnable)</summary>

```python
import re
import random
from collections import Counter


def expect(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


# every example in the problem statement, run as written
ex = TextBuffer("draft notes")
ex.insert(5, " short")
assert len(ex) == 17 and ex.text() == "draft short notes" and ex.read(0, 5) == "draft"
assert ex.delete(5, 11) == " short" and ex.text() == "draft notes"
expect(IndexError, ex.insert, 100, "x")
expect(IndexError, ex.delete, 3, 1)

ex = TextBuffer("cat")
ex.insert(3, "s")
ex.insert(0, "wild")
assert ex.undo() and ex.text() == "cats"
assert ex.undo() and ex.text() == "cat"
assert ex.redo() and ex.text() == "cats"
ex.insert(4, "!")
assert ex.redo() is False and ex.text() == "cats!"       # the new edit discarded the "wild" redo
assert ex.undo() and ex.undo() and ex.text() == "cat"
assert ex.undo() is False and ex.text() == "cat"
ex.insert(1, "")                                         # neither no-op is recorded
ex.delete(2, 2)
assert ex.undo() is False

ex = TextBuffer("")
ex.insert(0, "the cat sat on the mat")
assert ex.suggest("ca", 5) == ["cat"] and ex.suggest("t", 5) == ["the"]
assert ex.suggest("", 3) == ["the", "cat", "mat"]
assert ex.delete(4, 8) == "cat " and ex.suggest("ca", 5) == []

ex = TextBuffer("apple Zoo apple Zoo bee")
assert ex.suggest("", 3) == ["Zoo", "apple", "bee"]      # tied counts: uppercase sorts first
assert ex.suggest("", 0) == [] and ex.suggest("z", 5) == []
expect(ValueError, ex.suggest, "", -1)


class NaiveEditor:
    """Independent implementation straight from the problem statement, sharing no code with
    TextBuffer: string slicing, whole-buffer snapshots for undo/redo, a linear scan for suggest."""

    def __init__(self, text: str = "") -> None:
        self._text = text
        self._undo_stack: list[str] = []
        self._redo_stack: list[str] = []

    def text(self) -> str:
        return self._text

    def insert(self, pos: int, text: str) -> None:
        if not 0 <= pos <= len(self._text):
            raise IndexError("bad insert position")
        if text:
            self._undo_stack.append(self._text)
            self._redo_stack.clear()
        self._text = self._text[:pos] + text + self._text[pos:]

    def delete(self, start: int, end: int) -> str:
        if not 0 <= start <= end <= len(self._text):
            raise IndexError("bad delete range")
        removed = self._text[start:end]
        if removed:
            self._undo_stack.append(self._text)
            self._redo_stack.clear()
        self._text = self._text[:start] + self._text[end:]
        return removed

    def read(self, start: int, end: int) -> str:
        if not 0 <= start <= end <= len(self._text):
            raise IndexError("bad read range")
        return self._text[start:end]

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._text)
        self._text = self._undo_stack.pop()
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._text)
        self._text = self._redo_stack.pop()
        return True

    def suggest(self, prefix: str, k: int):
        if k < 0:
            raise ValueError("k must be >= 0")
        words = re.findall(r"[A-Za-z]+", self._text)
        counts = Counter(words)
        candidates = [w for w in set(words) if w.startswith(prefix)]
        candidates.sort(key=lambda w: (-counts[w], w))
        return candidates[:k]


def random_trial_1_3(seed, num_ops=60, max_len=12):
    rng = random.Random(seed)
    main = TextBuffer("")
    naive = NaiveEditor("")
    n_undo = n_redo = n_undo_empty = n_suggest = n_tie = n_noop = n_dropped_redo = 0
    for _ in range(num_ops):
        n = len(main.text())
        choice = rng.random()
        if choice < 0.35 or n == 0:
            pos = rng.randint(0, n)
            text = "".join(rng.choice("abAB ") for _ in range(rng.randint(1, 4))) if n < max_len else ""
            n_noop += not text
            n_dropped_redo += bool(text) and bool(naive._redo_stack)
            main.insert(pos, text)
            naive.insert(pos, text)
        elif choice < 0.55:
            start = rng.randint(0, n)
            end = rng.randint(start, n)
            n_noop += start == end
            n_dropped_redo += start != end and bool(naive._redo_stack)
            assert main.delete(start, end) == naive.delete(start, end)
        elif choice < 0.65:
            start = rng.randint(0, n)
            end = rng.randint(start, n)
            assert main.read(start, end) == naive.read(start, end)
        elif choice < 0.8:
            ok1, ok2 = main.undo(), naive.undo()
            assert ok1 == ok2
            n_undo += 1
            n_undo_empty += not ok1
        elif choice < 0.9:
            ok1, ok2 = main.redo(), naive.redo()
            assert ok1 == ok2
            n_redo += 1
        else:
            prefix = rng.choice(["", "a", "A", "b", "ab", "Ba"])
            k = rng.randint(0, 4)
            s1, s2 = main.suggest(prefix, k), naive.suggest(prefix, k)
            assert s1 == s2, (prefix, k, s1, s2, main.text())
            n_suggest += 1
            counts = Counter(re.findall(r"[A-Za-z]+", main.text()))
            vals = [counts[w] for w in s1]
            n_tie += any(vals[i] == vals[i + 1] for i in range(len(vals) - 1))
        assert main.text() == naive.text()
    # drain the undo history completely -- exercises "undo when there is nothing left to undo"
    while True:
        ok1, ok2 = main.undo(), naive.undo()
        assert ok1 == ok2
        if not ok1:
            break
        n_undo += 1
        assert main.text() == naive.text()
    n_undo_empty += 1
    return n_undo, n_redo, n_undo_empty, n_suggest, n_tie, n_noop, n_dropped_redo


totals = [0] * 7
for seed in range(400):
    totals = [t + x for t, x in zip(totals, random_trial_1_3(seed))]
n_undo, n_redo, n_undo_empty, n_suggest, n_tie, n_noop, n_dropped_redo = totals
print(f"400 trials cross-validated against NaiveEditor: {n_undo} undos ({n_undo_empty} on an empty "
      f"stack), {n_redo} redos, {n_suggest} suggest() calls ({n_tie} with a tie), {n_noop} no-ops, "
      f"{n_dropped_redo} edits that discarded a pending redo")
assert n_undo > 500 and n_undo_empty == 400 and n_redo > 200 and n_suggest > 500 and n_tie > 50
assert n_noop > 200 and n_dropped_redo > 200
```

```python
random.seed(0)   # position generation draws from the global RNG; fix it once for reproducible output

a, b = CRDTDoc("A"), CRDTDoc("B")
op_h = a.local_insert(0, "H")
op_i = b.local_insert(0, "i")
a.apply(op_i)
b.apply(op_h)
assert a.text() == b.text()
print("concurrent root inserts converge to", repr(a.text()))

# an insert anchored on a concurrently deleted character keeps its place
a2, b2 = CRDTDoc("A"), CRDTDoc("B")
for ch in "abc":
    op = a2.local_insert(len(a2.text()), ch)
    b2.apply(op)
del_op = a2.local_delete(1)                 # a2 deletes 'b'
ins_op = b2.local_insert(2, "Y")            # concurrently, b2 inserts right after 'b' on its own view
assert b2.text() == "abYc"
b2.apply(del_op)
a2.apply(ins_op)
assert a2.text() == b2.text() == "aYc"

# a deletion overtaking its own character: c3 hears of it before the insert that creates it
a3, b3, c3 = CRDTDoc("A"), CRDTDoc("B"), CRDTDoc("C")
ins_op = a3.local_insert(0, "z")
b3.apply(ins_op)
del_op = b3.local_delete(0)
c3.apply(del_op)
c3.apply(ins_op)
a3.apply(del_op)
assert a3.text() == b3.text() == c3.text() == ""

# idempotency: replaying an already-seen operation changes nothing
a4 = CRDTDoc("A")
a4.apply(a4.local_insert(0, "w"))
assert a4.text() == "w"
del_op = a4.local_delete(0)
a4.apply(del_op)
a4.apply(del_op)
assert a4.text() == ""
expect(ValueError, a4.local_insert, 0, "ab")   # one character per operation
expect(IndexError, a4.local_delete, 0)         # nothing visible left to delete
print("deterministic scenarios OK")


def random_trial_4(seed, n_replicas=3, rounds=40, dup_chance=0.3):
    """Random local edits on several replicas, delivered over per-pair FIFO channels that may lag
    arbitrarily far behind and may deliver the same operation twice."""
    rng = random.Random(seed)
    reps = [CRDTDoc(chr(ord("A") + i)) for i in range(n_replicas)]
    queue = {(i, j): [] for i in range(n_replicas) for j in range(n_replicas) if i != j}
    seen = [set() for _ in reps]              # applied insert ids, used only by the counters below
    stats = dict(ins=0, dele=0, dup=0, late_delete=0, races=0)
    for _ in range(rounds):
        stats["races"] += sum(1 for q in queue.values() if q) >= 2
        for i, rep in enumerate(reps):
            if rng.random() < 0.5:
                continue
            n = len(rep.text())
            if n == 0 or rng.random() < 0.6:
                index, ch = rng.randint(0, n), rng.choice("abc")
                op = rep.local_insert(index, ch)
                assert rep.text()[index] == ch        # NOTE: a local edit lands where it was asked to
                seen[i].add((op[2], op[3]))
                stats["ins"] += 1
            else:
                index, before = rng.randint(0, n - 1), rep.text()
                op = rep.local_delete(index)
                assert rep.text() == before[:index] + before[index + 1:]   # exactly that character
                stats["dele"] += 1
            for j in range(n_replicas):
                if j != i:
                    queue[(i, j)].append(op)
        for (i, j), q in queue.items():
            if not q or rng.random() < 0.5:
                continue
            k = rng.randint(1, len(q))
            for op in q[:k]:
                if op[0] == "insert":
                    seen[j].add((op[2], op[3]))
                elif (op[1], op[2]) not in seen[j]:
                    stats["late_delete"] += 1         # this deletion overtook its own character
                reps[j].apply(op)
                if rng.random() < dup_chance:
                    reps[j].apply(op)
                    stats["dup"] += 1
            del q[:k]
    for (i, j), q in queue.items():
        for op in q:
            reps[j].apply(op)
    return [r.text() for r in reps], stats


totals = dict(ins=0, dele=0, dup=0, late_delete=0, races=0)
for seed in range(400):
    texts, stats = random_trial_4(seed)
    assert len(set(texts)) == 1, (seed, texts)
    for key in totals:
        totals[key] += stats[key]
print("400 randomized 3-replica interleavings converged; {ins} inserts, {dele} deletes, {dup} repeat "
      "deliveries, {late_delete} deletions overtaking their own character, {races} rounds with two or "
      "more channels behind".format(**totals))
assert totals["ins"] > 10000 and totals["dele"] > 5000 and totals["dup"] > 8000
assert totals["late_delete"] > 150 and totals["races"] > 8000
```

</details>

</details>
