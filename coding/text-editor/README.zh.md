# 文本编辑器：缓冲区、撤销、补全

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 | 轮次 |
| --- | --- | --- | --- | --- | --- | --- |
| 编程 · 面向对象设计 | ★★★☆☆ | 中等 | SWE · RE | data-structure, stack, trie, collaboration | 4 个部分 | 电话面 · 现场面 |
<!-- meta:end -->

## 题目

分四步搭建一个文本编辑器的后端，每一步都给同一个 `TextBuffer` 类加方法。位置始终是缓冲区里的字符偏移
（从 0 开始计数）；区间 `[start, end)` 是左闭右开（含 `start`、不含 `end`），与切片的习惯一致。

### Part 1 —— 缓冲区：插入、删除、读取

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

例如：

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
buf.delete(3, 1)              # IndexError，因为 start > end
```

### Part 2 —— 撤销与重做

`TextBuffer` 增加 `undo` 和 `redo`，由两个栈支撑。每一次真正改变了缓冲区内容的 `insert` 或 `delete`
调用（`text` 非空，或 `[start, end)` 非空）算作一次可撤销的操作；什么都没改变的调用不会被记录，也不
会影响任何一个栈。`undo` 撤销最近记录的那次操作并返回 `True`；如果没有操作可撤销，缓冲区保持不变，
返回 `False`。`redo` 重新应用最近一次被撤销的操作并返回 `True`；如果没有操作可重做，返回 `False`。
记录一次新的操作（真正的 `insert` 或 `delete`，`undo`、`redo` 本身不算）会清空重做栈。

```py
def undo(self) -> bool:
    """Reverses the most recent recorded insert/delete. Returns whether there was one to reverse."""

def redo(self) -> bool:
    """Re-applies the most recently undone operation. Returns whether there was one to redo."""
```

例如：

```text
buf = TextBuffer("cat")
buf.insert(3, "s")            # "cats"
buf.insert(0, "wild")         # "wildcats"
buf.undo()                    # True  -> "cats"
buf.undo()                    # True  -> "cat"
buf.redo()                    # True  -> "cats"
buf.insert(4, "!")            # "cats!"，新的编辑，待重做的 "wild" 被丢弃
buf.redo()                    # False，没有可重做的了
buf.undo(); buf.undo()        # -> "cats" -> "cat"
buf.undo()                    # False，没有可撤销的了
```

### Part 3 —— 自动补全

`TextBuffer` 增加 `suggest`，由一棵带词频的前缀树（trie）支撑。*单词*是由字母 `A`–`Z`、`a`–`z`
组成的最长连续片段（大小写敏感，`"The"` 和 `"the"` 是两个不同的词）。词表恰好是缓冲区当前内容里出现
的那些词：一个词的频次是它当前出现的次数，删掉它唯一的那次出现，就会把它从词表里去掉。
`suggest(prefix, k)` 返回最多 `k` 个以 `prefix` 开头的词，按频次从高到低排列；频次相同的按字符串
比较排序，大写字母排在小写字母前面（`"Zoo"` 在 `"apple"` 之前）。`prefix = ""` 匹配所有词；匹配到
的词不足 `k` 个时全部返回。`k = 0` 返回 `[]`，`k < 0` 抛出 `ValueError`。

```py
def suggest(self, prefix: str, k: int) -> list[str]:
    """Up to k words of the buffer's current vocabulary that start with prefix, highest frequency
    first, ties broken by string order (uppercase before lowercase)."""
```

例如：

```text
buf = TextBuffer("")
buf.insert(0, "the cat sat on the mat")
buf.suggest("ca", 5)          # ["cat"]
buf.suggest("t", 5)           # ["the"]
buf.suggest("", 3)            # ["the", "cat", "mat"]，"the" 出现两次；只出现一次的四个词
                              #   ("cat"、"mat"、"on"、"sat") 按字符串顺序排在后面
buf.delete(4, 8)              # 删掉 "cat "，"cat" 唯一的一次出现
buf.suggest("ca", 5)          # []
```

### Part 4 —— 多人协同编辑

多个副本同时编辑同一份文档，每个副本有唯一的 `site_id`。一个副本对外暴露：

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

多字符的编辑就是多次 `local_insert` 调用。一个副本产生的操作最终都会经 `apply` 送达其余每个副本；
从某一个特定副本发出的操作，送达另一个副本时保持它自己产生的先后顺序（就像一条可靠的点对点连接）。
除此之外没有任何顺序保证：不同副本上产生的操作、以及接收方自己的本地编辑，可以任意交错，所以一条
删除可能先于它要删掉的那个字符送达某个副本，同一个操作也可能被送达不止一次。操作、字符以及位置怎样
表示，都由你自己决定。唯一的要求是：两个副本一旦应用过同一组操作，`text()` 就必须相同，不管这些
操作送达的顺序在中途是怎样交错的。

```text
a, b = CRDTDoc("A"), CRDTDoc("B")     # 两个副本都从空文档开始
op1 = a.local_insert(0, "H")          # 副本 A 本地是 "H"，b 还没看到
op2 = b.local_insert(0, "i")          # 与此同时，副本 B 本地是 "i"，a 还没看到
b.apply(op1)                          # 两个操作以任意先后送达
a.apply(op2)
assert a.text() == b.text()           # 两边最后必须得到同一份文档
```

## 参考解答

<details>
<summary>展开参考解答</summary>

值得先确认两件事：位置用字符偏移而不是（行，列）；Part 4 用一个小型 CRDT 而不是操作变换（OT）。

### Part 1

缓冲区是一个 Python `list`（字符列表），不是 `str`；`insert` 和 `delete` 都靠切片赋值完成移动，
各自是 $O(n)$（$n$ 是需要移动的字符数）。

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

`insert` 和 `delete` 被重新定义后再挂回 `TextBuffer`，让每个 Part 保持独立；`_stacks` 惰性建立两个栈，
因为 Part 1 的 `__init__` 并不知道它们。`undo`/`redo` 都通过*原始*的 `insert`/`delete` 重放，所以
撤销本身不会被记成新的一次操作。

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

`suggest` 每次调用都把 trie 完全重建：对当前文本分词，用 `Counter` 计数，再把每个词逐字母插入，在
最后一个节点上记下频次。查询先走到 `prefix` 对应的节点（$O(\lvert \text{prefix} \rvert)$），对这棵
子树做深度优先收集，再把收集到的 $m$ 个词排序：缓冲区有 $n$ 个字符时一次查询是 $O(n + m \log m)$。
查询频繁的话就把 trie 留下来，在 `insert`/`delete` 里增量更新。

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

每个字符都带一个绝对、自足的位置：一个 `Fraction`，严格落在它被敲下时两个可见邻居的位置之间
（0 和 1 是文档固定的两端），再配上 `(site_id, 一个本地计数器)` 保证唯一。位置从不引用别的操作——
不像靠 id 指名左邻居的方案（RGA、WOOT）——所以一个副本的全部状态就是两个集合：已经应用过的插入，
以及任何副本删除掉的字符 id。`text()` 把前者按 `(pos, site, seq)` 排序、把后者藏起来，于是它只
取决于已应用操作的*集合*，与到达顺序无关：重复的投递、比自己要删的字符还先到的删除，最后都落到
同一份文档上。空隙里取**随机**点而不是中点，这样两个副本填同一个空隙会得到不同的位置，之后再往
这两个字符之间插入才有容身之处。

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

两个副本只要应用过同一组操作，两个集合就相同，排出来的条目和藏起来的 id 也相同，文档自然一致。
上面例子的一次运行中，两个副本都收敛到 `text() == "iH"`。

### 追问

- 两个随机分数理论上可能碰撞：两个副本仍然一致，但之后要插到这对字符中间的字符没法严格落在两者
  之间，可能跑到其中一个的另一侧。Logoot 和 LSEQ 把位置做成多级的列表，空隙用完就加一级。
- 两个 id 集合会一直随文档增长；回收它们要先确认每个副本都应用过某个操作，这正是副本之间交换
  版本向量（version vector）的用途。
- `local_insert` 只接受一个字符，让每个操作正好对应一个 id，代价是并发编辑可能插进一次多字符粘贴
  的中间——RGA、WOOT 同样要面对这个权衡。按范围删除也是一个字符一次操作，实际实现会合并成一条消息。

<details>
<summary>验证代码（可运行）</summary>

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
