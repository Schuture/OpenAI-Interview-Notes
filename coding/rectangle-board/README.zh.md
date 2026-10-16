# 带撤销的矩形画板

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 | 轮次 |
| --- | --- | --- | --- | --- | --- | --- |
| 编程 | ★★☆☆☆ | 中等 | SWE | data-structure, state-management, undo, spatial-index | 5 个部分 | 电话面 |
<!-- meta:end -->

## 题目

*画板*（board）是由 `width` × `height` 个单位格组成的网格。格子 `(x, y)` 的列号为 `x`、行号为 `y`，
满足 `0 <= x < width`、`0 <= y < height`。*矩形*（rectangle）由四个整数 `(x1, y1, x2, y2)` 给出，覆盖所有满足
`x1 <= x < x2` 且 `y1 <= y < y2` 的格子 `(x, y)`（两个方向都是左闭右开）。当
`0 <= x1 < x2 <= width` 且 `0 <= y1 < y2 <= height` 时矩形*合法*，即它至少覆盖一个格子且完全位于画板内。
矩形之间可以重叠。分五个部分搭建这块画板，每个部分都给同一个 `Board` 类增加方法。

画板上的每个矩形都有一个 *id*，是添加时分配的正整数。画板发出的第一个 id 是 1，之后每个 id 是前一个加 1，
且同一个 id 绝不会发出两次，即使它对应的矩形后来已被删除。矩形按 *z 序*（z-order）叠放：后添加的矩形位于
此前所有矩形之上。某个格子处的*最上层矩形*（topmost）是覆盖该格子的矩形中 id 最大的那一个。

### Part 1 —— 添加

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

例如：

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

### Part 2 —— 删除

```py
def remove(self, rect_id: int) -> None:
    """Removes the rectangle with this id. Raises KeyError if the board holds none;
    the board is unchanged then. The remaining rectangles keep their relative z-order."""
```

例如，接着上面的画板：

```text
b.remove(2)               # board now holds ids [1, 3]
b.remove(2)               # KeyError -- already gone
b.add(5, 0, 8, 2)         # 4 -- the id 2 is not issued again, and the next id is not 3
b.ids()                   # [1, 3, 4]
```

### Part 3 —— 撤销

*操作*（operation）指改变了画板的调用：成功的 `add` 或 `remove`，以及后续部分中成功的 `remove_at` 或
`remove_many`。抛出异常的调用、或没有改变任何东西的调用都不是操作。`undo` 回退最近一个尚未被回退的操作，
可以连续调用以继续往前回退。`undo` 之后画板与该操作之前完全一致：矩形、id 和 z 序都相同。id 计数器不回退。

```py
def undo(self) -> bool:
    """Reverts the most recent operation not yet reverted and returns True,
    or returns False and does nothing if there is no such operation."""
```

例如，在上面的画板上（历史：add 1、add 2、add 3、remove 2、add 4）：

```text
b.undo()                  # True  -- the rectangle 4 is gone:  ids [1, 3]
b.undo()                  # True  -- the rectangle 2 is back:  ids [1, 2, 3], z-order as before
b.add(0, 4, 2, 6)         # 5     -- not 4: ids are never reused, also after an undo
b.undo()                  # True  -- ids [1, 2, 3]
b.undo(); b.undo(); b.undo()   # True each time -> ids [], after undoing add 3, add 2, add 1
b.undo()                  # False -- nothing left to undo
```

### Part 4 —— 删除某个格子处的矩形

```py
def remove_at(self, x: int, y: int) -> int | None:
    """Removes the topmost rectangle covering cell (x, y) and returns its id, or returns None
    (board unchanged) if no rectangle covers the cell. Raises ValueError if (x, y) is not a
    cell of the board."""
```

一次成功的 `remove_at` 是一个操作，由 `undo` 回退，与 `remove` 相同。

例如，在一块新的 `Board(8, 6)` 上，id 1、2、3 依次为 `(0, 0, 4, 3)`、`(2, 1, 6, 5)`、`(1, 1, 3, 2)`：

```text
b.remove_at(2, 1)         # 3     -- all three cover (2, 1); id 3 is the topmost
b.remove_at(2, 1)         # 2
b.remove_at(5, 4)         # None  -- only id 2 covered (5, 4), and it is gone
b.remove_at(4, 0)         # None  -- x2 is excluded: id 1 covers columns 0..3 only
b.undo()                  # True  -- reverts the second remove_at(2, 1): id 2 is back
```

### Part 5 —— 批量删除

```py
def remove_many(self, rect_ids: list[int]) -> None:
    """Removes all the listed rectangles as one operation. Raises ValueError if the list contains
    the same id twice, and KeyError if any id is not on the board; in both cases nothing is removed.
    An empty list does nothing and is not an operation."""
```

一次 `undo` 回退整个 `remove_many` 调用：其中所有矩形一起恢复，各自保持原来的 id 和 z 序。

例如，在 Part 4 那样持有 id 1、2、3 的新 `Board(8, 6)` 上：

```text
b.remove_many([3, 1])     # ids [2]
b.undo()                  # True -- one step brings back both: ids [1, 2, 3]
b.remove_many([1, 9])     # KeyError -- 9 is not on the board; id 1 is still there
b.remove_many([2, 2])     # ValueError
b.remove_many([])         # nothing happens
b.undo()                  # True -- reverts the add of id 3, not an empty operation
```

## 参考解答

<details>
<summary>展开参考解答</summary>

值得先确认两件事：id 永不复用（因此它在程序运行期间可以唯一指代一个矩形），以及被撤销的操作对 id 计数器
有什么影响。两者题面都已规定；下面的设计不依赖比这更多的细节。

### 设计

无论名字是什么，每个操作对画板做的事都一样：拿走一些矩形、放上另一些矩形。把这一对称为一次*变更*
（change）：由 `(id, 矩形)` 对组成的元组 `added`，以及同样形式的元组 `removed`。于是

- 应用一次变更，就是删除 `removed` 中的 id，再插入 `added` 中的各对；
- 变更的*逆*把两个元组互换，应用逆变更恰好回退原变更；
- 历史是变更构成的栈，`undo` 弹出栈顶并应用它的逆。

画板只通过一个私有函数 `_apply(change)` 修改，公开操作只通过 `_commit(change)`，后者应用变更并记录它。
这样后面每个部分都只是构造变更的一种新方式，别无其他：`add` 构造 `added=((id, rect),)`，`remove` 构造
`removed=((id, rect),)`，`remove_at` 先找到 id 再交给 `remove`，批量删除则是 `removed` 里有多对的一次变更，
所以 `undo` 无需任何额外代码就把它作为一步回退。

z 序不需要单独的数据结构：它就是 id 序，因为 id 随时间递增。因此重新插入一个被删除的对时，它的 z 位置
自动恢复，不管字典把它放在哪里；`ids()` 排序后读出 z 序。

### Part 1

`add` 先校验，取下一个 id，再提交一次变更。画板用字典保存 id 到矩形的映射，因此 `add` 和 `get` 是
$`O(1)`$，`ids` 在画板上有 $`n`$ 个矩形时是 $`O(n \log n)`$。

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

`remove` 在改动任何东西之前先查找该矩形，所以抛出 `KeyError` 时画板保持不变。$`O(1)`$。

```python
def remove(self, rect_id: int) -> None:
    if rect_id not in self._rects:
        raise KeyError(rect_id)
    self._commit(Change(added=(), removed=((rect_id, self._rects[rect_id]),)))


Board.remove = remove
```

### Part 3

只有 `_commit` 需要知道历史：现在它在应用变更之后记录它。`undo` 通过 `_apply` 而不是 `_commit` 应用栈顶变更的
逆，因此回退本身不会被记录。没有 redo，所以其他地方都不需要入栈。`undo` 的耗时与变更的大小成正比。

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

历史里每个操作只存一个小元组，不复制画板，所以内存随操作数增长，而不是随画板大小乘以操作数增长。

### Part 4

扫描所有矩形，在覆盖该格子的矩形里保留最大的 id，再交给 `remove`。每次调用 $`O(n)`$。`ValueError` 的检查放在最前面，
所以画板之外的格子是错误，而不是“没有矩形覆盖”。

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

矩形很多时，扫描就是瓶颈。*均匀网格索引*（uniform grid index）可以解决：选一个桶边长 $`s`$，对每个桶（一个
$`s \times s`$ 的格子块）保存与它相交的矩形 id 的集合。`remove_at` 只读一个桶，在真正覆盖该格子的矩形里取最大 id，
所以代价是一个桶的占用量，而不是 $`n`$。`add` 和 `remove` 要向矩形触及的每个桶插入或删除，对 $`w \times h`$ 的矩形是
$`O((w/s + 1)(h/s + 1))`$。由于所有修改都已经经过 `_apply`，索引只需在这一个函数里维护，`undo` 和 `remove_many`
都不用改。

### Part 5

先校验整个列表，再提交唯一一次变更，其 `removed` 包含所有的对。校验结束之前不修改任何东西，这保证了调用的
原子性；变更只记录一次，这保证了 `undo` 把它作为一步回退。$`k`$ 个 id 的代价是 $`O(k)`$。

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

### 追问

- 加 `redo`：再用一个栈，`undo` 往里压，任何新操作都清空它；`Change` 已经带有所需的全部信息。
- 用 `deque(maxlen=N)` 把历史限制在最近 $`N`$ 个操作。
- 允许矩形移动或调整 z 序：此时 z 不能再等于 id，需要给每个矩形保存显式的 z 键，移动则是先删再加这一对的一次变更。
- 用 `begin()` / `end()` 把多次调用合成一个撤销步骤：缓存这些变更，在 `end` 时合并为一个。
- 用同一个网格索引实现不删除的 `topmost(x, y)` 查询。

<details>
<summary>检查（可运行）</summary>

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
