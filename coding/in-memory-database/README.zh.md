# 类 SQL 的内存数据库

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 中等 | SWE | data-structure, oop-design, sql | 4 个部分 |
<!-- meta:end -->

## 题目

实现一个 `Database` 类，把表保存在内存里，所有查询都通过直接的方法调用完成：这道题里没有任何 SQL 文本需要解析，
参数直接传给 Python 方法。一张*表*（table）有一份固定的、有先后顺序的列名列表，在用 `create_table` 建表时一次性定好；
之后插入的每一行都是一个 Python `dict`，键恰好是这些列名；行里每个值要么是 `int`，要么是 `str`，要么是 `None`
（表示“这一行在这一列没有值”）。

下面任何一个方法，只要参数里的表名或列名不存在，就抛出 `KeyError`；这包括 `select` 的 `columns`、`where`、
`order_by` 里出现的列名，哪怕表是空的也一样。`create_table` 在表名已经存在时也抛出 `KeyError`。`insert`
按下面的顺序检查 `row` 参数：先检查 `row` 的每个键是不是表的某一列（不是就抛 `KeyError`），再检查表的每一列
是不是都在 `row` 的键里（不是就抛 `ValueError`）——因此一行如果既缺了一列、又带了一个不认识的列，抛出的是
`KeyError`，不是 `ValueError`。

### Part 1 —— 建表、插入、投影

```py
class Database:
    def create_table(self, table: str, columns: list[str]) -> None:
        """Creates an empty table with these columns, in this order."""

    def insert(self, table: str, row: dict[str, int | str | None]) -> None:
        """Appends a copy of row to table."""

    def select(self, table: str, columns: list[str] | None = None) -> list[dict[str, int | str | None]]:
        """Returns every row of table, projected to columns (all of the table's columns, in schema
        order, if columns is None), as a list of dicts, in the order the rows were inserted."""
```

例如：

```text
db = Database()
db.create_table("employees", ["id", "name", "dept", "salary"])
for row in [
    {"id": 101, "name": "Ana", "dept": "eng", "salary": 95000},
    {"id": 102, "name": "Bo", "dept": "sales", "salary": 71000},
    {"id": 103, "name": "Cy", "dept": "eng", "salary": 88000},
    {"id": 104, "name": "Dee", "dept": "ops", "salary": 60000},
    {"id": 105, "name": "Eli", "dept": "eng", "salary": 88000},
    {"id": 106, "name": "Fo", "dept": "sales", "salary": 71000},
    {"id": 107, "name": "Gia", "dept": "ops", "salary": None},
    {"id": 108, "name": "Hu", "dept": "ops", "salary": None},
]:
    db.insert("employees", row)

db.select("employees", ["id", "name"])
# [{"id": 101, "name": "Ana"}, {"id": 102, "name": "Bo"}, {"id": 103, "name": "Cy"}, {"id": 104, "name": "Dee"},
#  {"id": 105, "name": "Eli"}, {"id": 106, "name": "Fo"}, {"id": 107, "name": "Gia"}, {"id": 108, "name": "Hu"}]
```

### Part 2 —— 用 WHERE 过滤

`select` 增加一个 `where` 参数：一份 `(column, operator, value)` 条件的列表，全部条件都成立才算匹配（用 AND
连接）。`operator` 是 `"="`、`"!="`、`"<"`、`"<="`、`">"`、`">="` 之一。只要这一行在 `column` 上的值、或者
`value` 本身是 `None`，这个条件就为假——对每一种运算符都成立，包括 `"="`，所以一行如果在某一列上没有值，
它在这一列上的任何条件都不会匹配，包括 `("salary", "!=", 60000)`。两边都不是 `None` 时，同类型的两个值
按 Python 的规则比较；`int` 与 `str` 永远不相等，并且任何 `int` 都小于任何 `str`（所以对 salary 是 `int`
的每一行，`("salary", "<", "0")` 都成立）。

```py
def select(self, table: str, columns: list[str] | None = None,
           where: list[tuple[str, str, int | str | None]] | None = None) -> list[dict[str, int | str | None]]:
    """Same as Part 1, but keeps only the rows for which every (column, operator, value) condition
    of where holds; where=None (or []) means no filtering."""
```

接着 Part 1 的表：

```text
db.select("employees", ["name"], where=[("dept", "=", "eng"), ("salary", ">=", 90000)])
# [{"name": "Ana"}]

db.select("employees", ["name"], where=[("salary", "<", 70000)])
# [{"name": "Dee"}]   -- Gia 和 Hu 的 salary 是 None，"<" 对他们永远不会匹配
```

### Part 3 —— 用 ORDER BY 排序

`select` 增加一个 `order_by` 参数：一份 `(column, ascending)` 的列表，最重要的列排在最前面。如果两行在
`order_by` 的每一列上都打平，就保持它们原来的插入顺序。在同一列内，值按 Part 2 的规则排序，`None` 算作
比任何 `int` 和任何 `str` 都小，结合这一列的方向，就是：这一列升序时 `None` 排在最前面，降序时排在最后面。

```py
def select(self, table, columns=None, where=None,
           order_by: list[tuple[str, bool]] | None = None) -> list[dict[str, int | str | None]]:
    """Same as Part 2, but sorts the returned rows by order_by; order_by=None (or []) keeps
    insertion order."""
```

先按单列排序：

```text
[r["name"] for r in db.select("employees", order_by=[("salary", True)])]
# ["Gia", "Hu", "Dee", "Bo", "Fo", "Cy", "Eli", "Ana"]     -- None 排最前，升序
```

再按部门升序，同一部门内再按薪水降序：

```text
[r["name"] for r in db.select("employees", order_by=[("dept", True), ("salary", False)])]
# ["Ana", "Cy", "Eli", "Dee", "Gia", "Hu", "Bo", "Fo"]
# dept "eng"：95000、88000、88000（Cy 排在 Eli 前面：插入顺序）
# dept "ops"：60000，然后是 None、None（Gia 排在 Hu 前面；这一列降序，所以 None 排在最后）
# dept "sales"：71000、71000（Bo 排在 Fo 前面：插入顺序）
```

### Part 4 —— 索引

`create_index(table, column, kind)` 在 `column` 上建一个索引，用 `table` 里已有的行构建；之后每次 `insert`
都会让这张表的每个索引保持最新。`kind` 是 `"hash"`，服务于 `"="` 条件；或者是 `"sorted"`，服务于 `"<"`、
`"<="`、`">"`、`">="` 条件。不管有没有匹配的索引，`select` 返回的行都一样，顺序也一样——变化的只是要做
多少工作：如果 `where` 里至少有一个条件的列上建有与其运算符相应的索引，`select` 就不能扫描整张表，哪怕同一个
`where` 里的其他条件都没有索引可用。`"!="` 条件，以及列上没有相应索引的条件，始终逐行检查。

```py
def create_index(self, table: str, column: str, kind: str) -> None:
    """kind is "hash" or "sorted". Rebuilds the index if one already exists for this (column, kind)."""
```

```text
db.create_index("employees", "dept", "hash")
db.create_index("employees", "salary", "sorted")

db.select("employees", ["name"], where=[("dept", "=", "eng")])
# [{"name": "Ana"}, {"name": "Cy"}, {"name": "Eli"}]     -- 与 create_index 之前是同一批行
```

## 参考解答

<details>
<summary>展开参考解答</summary>

值得先确认两件事：`where` 用结构化条件还是任意的回调函数（这里用前者，因为 Part 4 要看条件用的是哪一列、
哪个运算符）；缺失值、以及 `int` 与 `str` 之间的比较应当怎样处理。

### Part 1

`create_table` 记下 schema 和空的行列表；`insert` 按顺序校验 `row`，存入它的一份拷贝；`select` 是每行
一次字典推导。`_check_names` 只写一次，之后 `where`、`order_by` 和 `create_index` 也用它检查列名。

```python
from typing import Any


class Database:
    def __init__(self):
        self._schemas: dict[str, list[str]] = {}
        self._rows: dict[str, list[dict[str, Any]]] = {}

    def create_table(self, table: str, columns: list[str]) -> None:
        if table in self._schemas:
            raise KeyError(f"table already exists: {table!r}")
        self._schemas[table] = list(columns)
        self._rows[table] = []

    def _schema(self, table: str) -> list[str]:
        if table not in self._schemas:
            raise KeyError(f"no such table: {table!r}")
        return self._schemas[table]

    def insert(self, table: str, row: dict[str, Any]) -> None:
        schema = self._schema(table)
        extra = set(row) - set(schema)
        if extra:
            raise KeyError(f"no such column(s) in {table!r}: {sorted(extra)}")
        missing = set(schema) - set(row)
        if missing:
            raise ValueError(f"row is missing column(s) for {table!r}: {sorted(missing)}")
        self._rows[table].append(dict(row))     # NOTE: a copy, so mutating the caller's dict is safe

    def select(self, table: str, columns: list[str] | None = None) -> list[dict[str, Any]]:
        schema = self._schema(table)
        columns = list(columns) if columns is not None else list(schema)
        _check_names(schema, table, columns)
        return [{col: row[col] for col in columns} for row in self._rows[table]]


def _check_names(schema, table, names):
    for col in names:
        if col not in schema:
            raise KeyError(f"no such column in {table!r}: {col!r}")
```

### Part 2-3

`_sort_key` 把值映射成元组，编码了题面规定的整个顺序：`None` 最小，其次是所有 `int`，最后是所有 `str`。
元组里的 `isinstance` 标志先把 `int` 和 `str` 分开，这两个值本身永远不会被直接比较，所以不会抛 `TypeError`。
`_matches` 在任一边是 `None` 时返回 `False`，否则对两个键应用运算符，于是 `5 = "5"` 为假、`5 != "5"` 为真。
多列排序做 $o$ 次稳定排序，一列一次，从**最不重要**的列排到**最重要**的列：`sorted` 是稳定的，后一轮不会打乱
前一轮定下的相对顺序，所有列都打平的行保持插入顺序。

```python
import operator

_OPERATORS = {
    "=": operator.eq, "!=": operator.ne,
    "<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge,
}


def _sort_key(value):
    return (0,) if value is None else (1, isinstance(value, str), value)   # NOTE: never compares int with str


def _matches(actual, op, target):
    if actual is None or target is None:       # NOTE: None fails every operator, "!=" included
        return False
    return _OPERATORS[op](_sort_key(actual), _sort_key(target))


def _filtered_rows(self, table, where):     # NOTE: overridden by Part 4
    return [row for row in self._rows[table]
            if all(_matches(row[col], op, value) for col, op, value in where)]


def select(self, table, columns=None, where=None, order_by=None):
    schema = self._schema(table)
    columns = list(columns) if columns is not None else list(schema)
    where, order_by = list(where or []), list(order_by or [])
    _check_names(schema, table, columns + [c for c, _, _ in where] + [c for c, _ in order_by])
    for _, op, _ in where:                      # NOTE: validated up front, even for an empty table
        if op not in _OPERATORS:
            raise ValueError(f"unknown operator: {op!r}")

    rows = self._filtered_rows(table, where)
    for col, ascending in reversed(order_by):    # NOTE: least-significant column first
        rows = sorted(rows, key=lambda row: _sort_key(row[col]), reverse=not ascending)  # NOTE: str has no -x
    return [{col: row[col] for col in columns} for row in rows]   # NOTE: project after filter/sort


Database._filtered_rows = _filtered_rows
Database.select = select
```

不用索引时，过滤是 $O(n \cdot w)$（$w$ 是条件数），每次排序是 $O(m \log m)$（$m$ 是剩下的行数），共 $o$
次：合起来 $O(n \cdot w + m \log m \cdot o)$。

### Part 4

索引放在 `_rows` 之外，由 `create_index` 建立、`insert` 维护。`"hash"` 索引是从值到行位置列表的 `dict`，
列表按插入顺序排列；`"sorted"` 索引是用 `bisect.insort` 保持有序的 `(_sort_key(value), position)` 列表
（标准库没有平衡树），每次插入都要把后面的元素逐个后移，是 $O(n)$。存键而不存原值，一个索引里就能同时放
`int` 和 `str`；`None` 不满足任何范围运算符，不进索引。改写后的 `_filtered_rows` 遇到拿 `None` 作比较的条件
就直接返回 `[]`；否则取 `where` 里第一个能用索引的条件，从索引读出行位置，排序以恢复插入顺序（`sorted` 索引
的一段按值有序），再只在这些行上检查其余条件。`select` 本来就调用 `self._filtered_rows`，不用改。

```python
import bisect

_insert_without_indexes = Database.insert   # Part 1's insert, unchanged


def _add_to_index(index, kind, value, pos):
    if kind == "hash":
        index.setdefault(value, []).append(pos)
    elif value is not None:                 # NOTE: sorted index never holds None
        bisect.insort(index, (_sort_key(value), pos))


def insert(self, table, row):
    _insert_without_indexes(self, table, row)
    pos = len(self._rows[table]) - 1
    for (col, kind), index in getattr(self, "_indexes", {}).get(table, {}).items():
        _add_to_index(index, kind, self._rows[table][pos][col], pos)


def create_index(self, table, column, kind):
    schema = self._schema(table)
    _check_names(schema, table, [column])
    if kind not in ("hash", "sorted"):
        raise ValueError(f"unknown index kind: {kind!r}")
    if not hasattr(self, "_indexes"):        # NOTE: lazy init -- predates __init__
        self._indexes = {}
    index = {} if kind == "hash" else []
    for pos, row in enumerate(self._rows[table]):
        _add_to_index(index, kind, row[column], pos)
    self._indexes.setdefault(table, {})[(column, kind)] = index


def _filtered_rows(self, table, where):
    if any(value is None for _, _, value in where):
        return []                                # NOTE: that condition is false on every row
    indexes = getattr(self, "_indexes", {}).get(table, {})
    candidates, remaining = self._rows[table], where
    for i, (col, op, value) in enumerate(where):
        if op == "=" and (col, "hash") in indexes:
            positions = indexes[(col, "hash")].get(value, [])
        elif op in ("<", "<=", ">", ">=") and (col, "sorted") in indexes:
            entries = indexes[(col, "sorted")]
            search = bisect.bisect_right if op in ("<=", ">") else bisect.bisect_left
            cut = search(entries, _sort_key(value), key=lambda e: e[0])
            lo, hi = (0, cut) if op in ("<", "<=") else (cut, len(entries))
            positions = sorted(p for _, p in entries[lo:hi])   # NOTE: restores row-insertion order
        else:
            continue
        candidates = [self._rows[table][p] for p in positions]
        remaining = where[:i] + where[i + 1:]
        break
    return [row for row in candidates
            if all(_matches(row[col], op, value) for col, op, value in remaining)]


Database.insert = insert
Database.create_index = create_index
Database._filtered_rows = _filtered_rows
```

命中 `"hash"` 索引的 `"="`，代价是平均 $O(1)$ 加上 $k$ 个匹配行的 $O(k)$，而不是 $O(n)$；命中 `"sorted"`
索引的范围条件，代价是 $O(\log n)$ 加上收集并重排匹配行的 $O(k \log k)$。两万行的表上实测：索引等值查询比
全扫描快三个数量级以上，匹配 100 行的范围查询快约两个数量级；往带两个索引的表里 `insert`，比不带索引的表
慢几倍。

### 追问

- `where` 只支持 AND；OR 和括号需要把条件列表换成表达式树。顶层 AND 里的任何一项仍然可以走索引；
  OR 则要每个分支都能走索引，再取行位置的并集。
- 真正的查询规划器会估计每个条件保留多少行，即*选择率*（selectivity），优先用排除行数最多的索引；
  `_filtered_rows` 则总是取 `where` 里第一个能用索引的条件。

<details>
<summary>验证代码（可运行）</summary>

```python
def expect(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} from {fn.__name__}{args!r}")


ROWS = [
    {"id": 101, "name": "Ana", "dept": "eng", "salary": 95000},
    {"id": 102, "name": "Bo", "dept": "sales", "salary": 71000},
    {"id": 103, "name": "Cy", "dept": "eng", "salary": 88000},
    {"id": 104, "name": "Dee", "dept": "ops", "salary": 60000},
    {"id": 105, "name": "Eli", "dept": "eng", "salary": 88000},
    {"id": 106, "name": "Fo", "dept": "sales", "salary": 71000},
    {"id": 107, "name": "Gia", "dept": "ops", "salary": None},
    {"id": 108, "name": "Hu", "dept": "ops", "salary": None},
]


def fresh():
    db = Database()
    db.create_table("employees", ["id", "name", "dept", "salary"])
    for row in ROWS:
        db.insert("employees", row)
    return db


def names(db, **query):
    return [r["name"] for r in db.select("employees", **query)]


# ---- Part 1: the statement's example, plus the insert/select error paths ----
db = fresh()
assert db.select("employees", ["id", "name"]) == [{"id": r["id"], "name": r["name"]} for r in ROWS]
assert db.select("employees") == ROWS
expect(KeyError, db.select, "nope")
expect(KeyError, db.select, "employees", ["nope"])
expect(KeyError, db.create_table, "employees", ["x"])
expect(KeyError, db.insert, "employees", {"id": 1, "name": "X", "dept": "eng", "salary": 1, "extra": "n"})
expect(ValueError, db.insert, "employees", {"id": 1, "name": "X"})
t2 = Database()
t2.create_table("t", ["a", "b"])
expect(KeyError, t2.insert, "nope", {})
expect(KeyError, t2.insert, "t", {"a": 1, "c": 2})   # missing "b" AND has "c": KeyError wins
row = {"a": 1, "b": 2}
t2.insert("t", row)
row["a"] = 99                                        # the stored copy must not change
assert t2.select("t") == [{"a": 1, "b": 2}]

# ---- Part 2 ----
assert names(db, where=[("dept", "=", "eng"), ("salary", ">=", 90000)]) == ["Ana"]
assert names(db, where=[("salary", "<", 70000)]) == ["Dee"]
assert names(db, where=[("salary", "=", None)]) == [] == names(db, where=[("salary", "!=", None)])
assert names(db, where=[("salary", "!=", 60000)]) == ["Ana", "Bo", "Cy", "Eli", "Fo"]
assert names(db, where=[("salary", "<", "0")]) == ["Ana", "Bo", "Cy", "Dee", "Eli", "Fo"]   # int < str
assert names(db, where=[("salary", ">", "0")]) == [] and len(names(db, where=[("id", "!=", "101")])) == 8
expect(ValueError, db.select, "employees", ["name"], [("salary", "~=", 1)])
expect(KeyError, db.select, "employees", None, [("nope", "=", 1)])
expect(KeyError, db.select, "employees", None, None, [("nope", True)])

# ---- Part 3 ----
assert names(db, order_by=[("salary", True)]) == ["Gia", "Hu", "Dee", "Bo", "Fo", "Cy", "Eli", "Ana"]
assert names(db, order_by=[("salary", False)]) == ["Ana", "Cy", "Eli", "Bo", "Fo", "Dee", "Gia", "Hu"]
assert names(db, order_by=[("dept", True), ("salary", False)]) == \
    ["Ana", "Cy", "Eli", "Dee", "Gia", "Hu", "Bo", "Fo"]

# ---- Part 4: index built after some rows, kept current by later inserts, never a full scan ----
db.create_index("employees", "dept", "hash")
db.create_index("employees", "salary", "sorted")
db.insert("employees", {"id": 109, "name": "Ivy", "dept": "eng", "salary": "n/a"})
assert names(db, where=[("dept", "=", "eng")]) == ["Ana", "Cy", "Eli", "Ivy"]
assert names(db, where=[("salary", ">=", 88000)]) == ["Ana", "Cy", "Eli", "Ivy"]   # "n/a" > every int
assert names(db, where=[("salary", "<", "a")]) == ["Ana", "Bo", "Cy", "Dee", "Eli", "Fo"]
expect(KeyError, db.create_index, "employees", "nope", "hash")
expect(ValueError, db.create_index, "employees", "dept", "btree")


class NoScan(list):                 # fails the check if anything iterates over every row
    def __iter__(self):
        raise AssertionError("full scan")


db._rows["employees"] = NoScan(db._rows["employees"])
assert names(db, where=[("name", "!=", "Cy"), ("salary", ">", 80000)]) == ["Ana", "Eli", "Ivy"]
assert names(db, where=[("salary", "!=", 1), ("dept", "=", "ops")]) == ["Dee"]
assert names(db, where=[("id", "=", None)]) == []
print("Part 1-4 checks OK")
```

```python
# ---- independent cross-validation against sqlite3's in-memory engine ----
# to_sql() is written from the problem statement alone and shares no code with the solution. The
# columns are declared without a type, so SQLite applies no type affinity and follows the statement's
# rules: NULL fails every comparison and is the smallest value in ORDER BY, and an INTEGER never equals
# a TEXT and sorts before every TEXT. (A column declared INTEGER would convert '5' to 5 when comparing,
# so v = '5' would match there.)
import random
import sqlite3

OPS = ["=", "!=", "<", "<=", ">", ">="]


def random_value(rng, typ):
    if rng.random() < 0.2:
        return None
    if typ == "mixed":
        typ = rng.choice(["int", "str"])
    return rng.randint(-3, 3) if typ == "int" else rng.choice("abc")


def to_sql(where, order_by, columns):
    sql = f"SELECT {', '.join(columns)} FROM t"
    if where:
        sql += " WHERE " + " AND ".join(f"{col} {op} ?" for col, op, _ in where)
    keys = [f"{col} {'ASC' if asc else 'DESC'}" for col, asc in order_by] + ["rowid"]  # NOTE: rowid ==
    return sql + " ORDER BY " + ", ".join(keys), [value for _, _, value in where]      # insertion order


def run_trial(seed, nrows=24, nqueries=15):
    rng = random.Random(seed)
    cols = ["c0", "c1", "c2"]
    types = {c: rng.choice(["int", "str", "mixed"]) for c in cols}
    rows = [{c: random_value(rng, types[c]) for c in cols} for _ in range(nrows)]
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE t (c0, c1, c2)")          # NOTE: no declared types, so no affinity
    con.executemany("INSERT INTO t VALUES (?, ?, ?)", [[r[c] for c in cols] for r in rows])

    db = Database()
    db.create_table("t", cols)
    split = rng.randint(0, nrows)                          # rows after split arrive after create_index
    for row in rows[:split]:
        db.insert("t", row)
    indexes = {(c, kind) for c in cols for kind in ("hash", "sorted") if rng.random() < 0.4}
    for col, kind in indexes:
        db.create_index("t", col, kind)
    for row in rows[split:]:
        db.insert("t", row)
    kinds = {c: {type(r[c]) for r in rows if r[c] is not None} for c in cols}

    ties = hits = cross = 0
    for _ in range(nqueries):
        where = []
        for _ in range(rng.randint(0, 3)):
            col = rng.choice(cols)
            value = rng.choice(rows)[col] if rng.random() < 0.5 else random_value(rng, "mixed")
            where.append((col, rng.choice(OPS), value))
        order_by = [(c, rng.random() < 0.5) for c in rng.sample(cols, rng.randint(0, 3))]
        columns = rng.sample(cols, rng.randint(1, 3))

        sql, params = to_sql(where, order_by, columns)
        expected = [dict(zip(columns, r)) for r in con.execute(sql, params)]
        got = db.select("t", columns, where=where, order_by=order_by)
        assert got == expected, (sql, params, got, expected)

        full = db.select("t", where=where, order_by=order_by)
        keys = [tuple(r[c] for c, _ in order_by) for r in full]
        ties += bool(order_by) and any(a == b for a, b in zip(keys, keys[1:]))
        hits += any(v is not None and ((c, "hash") in indexes and op == "="
                                       or (c, "sorted") in indexes and op in OPS[2:]) for c, op, v in where)
        cross += any(v is not None and kinds[c] - {type(v)} for c, _, v in where)
    return nqueries, ties, hits, cross


totals = [0, 0, 0, 0]
for seed in range(300):
    totals = [t + x for t, x in zip(totals, run_trial(seed))]
n, ties, hits, cross = totals
assert ties > 1000 and hits > 1000 and cross > 1500   # tie-breaks, index paths, int-vs-str comparisons
print(f"cross-validated {n} queries against sqlite3: {ties} had an ORDER BY tie, {hits} could use "
      f"an index, {cross} compared an int with a str; all matched")
```

```python
# ---- timing: index vs full scan, and the cost the indexes add to insert ----
import timeit

N = 20_000


def build(indexed):
    big = Database()
    big.create_table("t", ["k", "v"])
    for i in range(N):
        big.insert("t", {"k": i, "v": i % 1000})
    if indexed:
        big.create_index("t", "k", "hash")
        big.create_index("t", "v", "sorted")
    return big


def per_call(fn, number):
    return min(timeit.repeat(fn, number=number, repeat=5)) / number


plain, indexed = build(indexed=False), build(indexed=True)
t_scan = per_call(lambda: plain.select("t", ["k"], where=[("k", "=", N // 2)]), 5)
t_hash = per_call(lambda: indexed.select("t", ["k"], where=[("k", "=", N // 2)]), 200)
t_range_scan = per_call(lambda: plain.select("t", ["k"], where=[("v", "<", 5)]), 5)   # 100 rows match
t_range_idx = per_call(lambda: indexed.select("t", ["k"], where=[("v", "<", 5)]), 50)
t_ins_plain = per_call(lambda: plain.insert("t", {"k": -1, "v": 1}), 200)
t_ins_indexed = per_call(lambda: indexed.insert("t", {"k": -1, "v": 1}), 200)
# NOTE: bounds far below the measured ratios, so a slow or busy machine does not fail them
assert t_scan > 10 * t_hash and t_range_scan > 5 * t_range_idx and t_ins_indexed > t_ins_plain
print(f"n={N}: '=' {t_scan / t_hash:.0f}x faster with a hash index, range "
      f"{t_range_scan / t_range_idx:.0f}x faster with a sorted index; insert "
      f"{t_ins_indexed / t_ins_plain:.1f}x slower with both indexes")
```

</details>

</details>
