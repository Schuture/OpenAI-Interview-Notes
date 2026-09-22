# In-Memory SQL-like Database

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Medium | SWE | data-structure, oop-design, sql | 4 parts |
<!-- meta:end -->

## Problem

Implement a `Database` class that keeps its tables in memory and answers every query through a
direct method call: there is no SQL text to parse anywhere in this problem, arguments are passed
straight to Python methods instead. A *table* has a fixed, ordered list of column names, chosen once
when it is created with `create_table`; every row inserted into it afterwards is a Python `dict` with
exactly those keys, and every value in a row is a Python `int`, a `str`, or `None` (meaning "this row
has no value in this column").

Every method below that takes a table name or a column name raises `KeyError` if that table, or that
column of that table, does not exist; this includes a column named in `select`'s `columns`, `where` or
`order_by`, even on an empty table. `create_table` also raises `KeyError` if a table with that name
already exists. `insert` checks its `row` argument in this order: first that every key of `row` is one
of the table's columns (`KeyError` if not), then that every column of the table is a key of `row`
(`ValueError` if not) — so a row that is both missing a column and carries an unknown one raises
`KeyError`, not `ValueError`.

### Part 1 — Tables, insertion, projection

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

For example:

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

### Part 2 — Filtering with WHERE

`select` grows a `where` parameter: a list of `(column, operator, value)` conditions, all of which must
hold (combined with AND). `operator` is one of `"="`, `"!="`, `"<"`, `"<="`, `">"`, `">="`. A condition
is false whenever the row's value in `column`, or `value` itself, is `None` — this holds for every
operator, including `"="`, so a row with no value in a column never matches a condition on that
column, not even `("salary", "!=", 60000)`. When neither side is `None`, two values of the same type
compare as Python compares them, while an `int` never equals a `str` and every `int` is smaller than
every `str` (so `("salary", "<", "0")` holds for every row whose salary is an `int`).

```py
def select(self, table: str, columns: list[str] | None = None,
           where: list[tuple[str, str, int | str | None]] | None = None) -> list[dict[str, int | str | None]]:
    """Same as Part 1, but keeps only the rows for which every (column, operator, value) condition
    of where holds; where=None (or []) means no filtering."""
```

Continuing the table of Part 1:

```text
db.select("employees", ["name"], where=[("dept", "=", "eng"), ("salary", ">=", 90000)])
# [{"name": "Ana"}]

db.select("employees", ["name"], where=[("salary", "<", 70000)])
# [{"name": "Dee"}]   -- Gia's and Hu's salary is None, so "<" never matches for them
```

### Part 3 — Sorting with ORDER BY

`select` grows an `order_by` parameter: a list of `(column, ascending)` pairs, the most significant
column first. Rows that tie on every `order_by` column keep their relative insertion order. Within one
column, values are ordered as in Part 2 and `None` counts as smaller than every `int` and every `str`,
so combined with that column's direction, `None` values come first when it is ascending and last when
it is descending.

```py
def select(self, table, columns=None, where=None,
           order_by: list[tuple[str, bool]] | None = None) -> list[dict[str, int | str | None]]:
    """Same as Part 2, but sorts the returned rows by order_by; order_by=None (or []) keeps
    insertion order."""
```

Sorting by a single column:

```text
[r["name"] for r in db.select("employees", order_by=[("salary", True)])]
# ["Gia", "Hu", "Dee", "Bo", "Fo", "Cy", "Eli", "Ana"]     -- None first, ascending
```

Sorting by department ascending, and within each department by salary descending:

```text
[r["name"] for r in db.select("employees", order_by=[("dept", True), ("salary", False)])]
# ["Ana", "Cy", "Eli", "Dee", "Gia", "Hu", "Bo", "Fo"]
# dept "eng": 95000, 88000, 88000 (Cy before Eli: insertion order)
# dept "ops": 60000, then None, None (Gia before Hu; None sorts last because the column is descending)
# dept "sales": 71000, 71000 (Bo before Fo: insertion order)
```

### Part 4 — Indexes

`create_index(table, column, kind)` builds an index on `column`, from the rows already in `table`;
every `insert` afterwards keeps every index of that table up to date. `kind` is `"hash"`, which serves
`"="` conditions, or `"sorted"`, which serves `"<"`, `"<="`, `">"` and `">="` conditions. `select`
returns the same rows, in the same order, whether or not a matching index exists — only how much work
it does can change: if at least one condition of `where` names an indexed column with a matching
operator, `select` must not scan every row of the table, even when the other conditions of the same
`where` are not backed by an index. `"!="`, and a condition on a column without a matching index, are always checked row by row.

```py
def create_index(self, table: str, column: str, kind: str) -> None:
    """kind is "hash" or "sorted". Rebuilds the index if one already exists for this (column, kind)."""
```

```text
db.create_index("employees", "dept", "hash")
db.create_index("employees", "salary", "sorted")

db.select("employees", ["name"], where=[("dept", "=", "eng")])
# [{"name": "Ana"}, {"name": "Cy"}, {"name": "Eli"}]     -- same rows as before create_index
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming up front: whether `where` should be structured conditions (assumed here, since
Part 4 needs to inspect which column and operator a condition uses) or an arbitrary callback; and
how a missing value and an `int` compared with a `str` should behave.

### Part 1

`create_table` records the schema and an empty row list; `insert` checks `row` against it in the
stated order and stores a copy; `select` is one dict comprehension per row. `_check_names` is written
once here and reused later for `where`, `order_by` and `create_index`.

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

`_sort_key` maps a value to a tuple that encodes the statement's whole order: `None` first, then every
`int`, then every `str`. The `isinstance` flag separates an `int` from a `str`, so the two values
themselves are never compared and nothing raises `TypeError`. `_matches` answers `False` when either
side is `None` and otherwise applies the operator to the two keys, which makes `5 = "5"` false and
`5 != "5"` true. Sorting by several columns is $o$ stable sorts, one per `order_by` column, run from
the **least** significant column to the **most** significant one: `sorted` is stable, so a later pass
never disturbs the relative order an earlier pass decided, and rows that tie on every column keep
insertion order.

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

Without an index, filtering is $O(n \cdot w)$ for $w$ conditions, and each of the $o$ sorting passes is
$O(m \log m)$ on the $m$ surviving rows: $O(n \cdot w + m \log m \cdot o)$ altogether.

### Part 4

An index sits alongside `_rows`, built by `create_index` and kept current by `insert`. A `"hash"`
index is a `dict` from value to the row positions with that value, in insertion order; a `"sorted"`
index is a list of `(_sort_key(value), position)` pairs kept sorted by `bisect.insort` (the standard
library has no balanced tree), which shifts every later element and so costs $O(n)$ per insert.
Storing the key instead of the raw value lets one index hold `int`s and `str`s side by side; `None`
never satisfies a range operator and is left out. The rewritten `_filtered_rows` returns `[]` at once
if any condition compares against `None`; otherwise it takes the first condition in `where` that an
index can serve, reads the matching positions from the index, sorts them back into insertion order (a
slice of the sorted index is ordered by value), and checks the other conditions on just those rows.
`select` already calls `self._filtered_rows`, so it is unchanged.

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

A `"="` served by a `"hash"` index costs $O(1)$ average plus $O(k)$ for the $k$ matches, instead of
$O(n)$; a range served by a `"sorted"` index costs $O(\log n)$ plus $O(k \log k)$ to gather and re-sort
the matches. On a table of 20,000 rows, an indexed equality lookup measured more than three orders of
magnitude faster than a full scan, and an indexed range lookup that matches 100 rows about two orders
of magnitude faster; an `insert` into the table with both indexes measured several times slower than
into the table without them.

### Follow-ups

- `where` only combines conditions with AND; OR and parentheses need an expression tree instead of a
  flat list. An index can still serve any top-level AND term, and an OR only when every branch can be
  served, by taking the union of the positions.
- A real query planner estimates how many rows each condition would keep (its *selectivity*) and picks
  the index that removes the most rows first; `_filtered_rows` instead always takes the first indexable
  condition it finds in `where`.

<details>
<summary>Checks (runnable)</summary>

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
