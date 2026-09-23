# Spreadsheet with Cell Dependencies (OpenSheet)

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Medium | SWE | graph, dfs, topological-sort, recursion | 3 parts |
<!-- meta:end -->

## Problem

A *cell name* is one or more uppercase letters `A`–`Z` (the column) followed by one or more digits
`0`–`9` (the row) and nothing else, such as `A1` or `AB12`; `a1`, `A` and `A1B` are not cell names. A
cell holds either a Python `int` or a *formula*: a string made of `=` followed by one or more *terms*,
with exactly one `+` or `-` between consecutive terms, for example `=R1 + 20 - S3` or `=5`. A term is a
cell name or a non-negative integer literal of at most 18 digits. Spaces may appear before or after any
term or operator, but not inside a term. Nothing else is allowed: no `*`, `/` or parentheses, and no
operator before the first term or after the last, so `=-R1`, `=R1 - -S3` and `=R1 2` are all invalid.
Reading a cell name that was never passed to `set`, directly or through a formula, gives `0`. Both `set`
and `get` raise `FormulaError` when given a name that is not a cell name; `set` also raises it for a
value that is neither an `int` nor a valid formula.

### Part 1 — Evaluate on demand

Implement `LazySpreadsheet`. `set(name, value)` stores `value` — an `int`, or a formula string — for
`name`, replacing whatever `name` held before. `get(name)` returns the current integer value of `name`:
the literal itself, or the formula evaluated by substituting, for every cell it references, that cell's
own current value, recursively. Cells form a *circular dependency* when a cell's formula reads that same
cell, directly or through other cells' formulas. `set` stores a formula even if it creates one;
`get(name)` must raise `CycleError` if evaluating `name` needs the value of a cell on a circular
dependency, and return normally otherwise. You may assume that following references from any cell,
without visiting a cell twice, never passes through more than 200 cells.

```py
class LazySpreadsheet:
    def set(self, name: str, value: int | str) -> None:
        """Stores value for name. Raises FormulaError if name or value is not of the shape above."""

    def get(self, name: str) -> int:
        """Evaluates name, recursively reading the cells its formula references.
        Raises CycleError if that needs a cell on a circular dependency."""
```

For example, after setting `P4 = 6`, `Q2 = 17`, `M3 = "=Q2 - P4"` and `M8 = "=M3 - P4 + 30"`,
`get("M8")` is `35`. Setting `P4 = 14` afterwards and reading `M8` again gives `19`, since `M3` is now
`3`. Setting `U1 = "=U2"` and then `U2 = "=U1"` both succeed; `get("U1")` then raises `CycleError`, and
so does `get` on any cell whose formula reads `U1`.

### Part 2 — Update eagerly

Implement `Spreadsheet` with the same `set`/`get` contract, except that `set` keeps every cell's value
up to date immediately, so that `get` only ever reads an already-computed value and runs in $O(1)$.
Unlike `LazySpreadsheet.set`, if the new `value` would create a circular dependency, `set` must reject
it and raise `CycleError` instead of storing anything, leaving the cell's previous content, the
dependency graph and every cached value exactly as they were.

```py
class Spreadsheet:
    def set(self, name: str, value: int | str) -> None:
        """Same contract as LazySpreadsheet.set, but recomputes every affected cell immediately, and
        raises CycleError (without changing anything) if value would create a circular dependency."""

    def get(self, name: str) -> int:
        """O(1): returns the already-computed value of name."""
```

With the same sequence of `set` calls as the Part 1 example, `get("M8")` again returns `35`, then `19`
after `P4` is updated — but now every `get` is a plain cache lookup, because `set` already recomputed
`M8` (and everything between it and `P4`) when `P4` changed. Calling `set("U1", "=U2")` and then
`set("U2", "=U1")` raises `CycleError` on the second call, and neither `U1`, `U2`, nor any other cell is
affected by the rejected call.

### Part 3 — Edge cases

Implement and pass tests for the following behaviors of `Spreadsheet` (and, where noted, of
`LazySpreadsheet`):

- Overwriting a cell that held a formula, with a new formula or a literal, drops its old dependency
  edges: a cell it used to read no longer triggers its recomputation.
- A direct self-reference (`set("H2", "=H2")`) and a cycle that runs through several cells are both
  rejected by `Spreadsheet.set`; the same two cases are only caught by `LazySpreadsheet.get`.
- A formula may reference a cell that has not been `set` yet (it reads as `0`); setting that cell
  afterwards updates every cell that transitively depends on it.
- In a "diamond" — two cells that both read a common cell, and a fourth cell that reads both of them —
  a single `set` on the common cell recomputes the fourth cell exactly once, not once per path to it.
- Overwriting a cell that held a literal with a formula adds its new dependency edges immediately: the
  cell's own cached value and every cell that transitively reads it reflect the formula from that same
  `set` call, not a stale literal.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming first: whether formulas may use multiplication, division or ranges (assumed not here,
to keep the parser under twenty lines), and whether a malformed cell name should fail immediately or
only once it is actually read (assumed immediately, in both `set` and `get`).

### Part 1

`_FORMULA_RE` encodes the whole grammar — a term, then any number of `[+-]term` blocks — in one pattern,
so a single `fullmatch` both validates a formula and rejects a leading operator, two terms in a row,
and a trailing operator; `_SIGNED_TERM_RE` then splits an already-valid formula into its signed terms.
`get` walks the formula tree recursively, with a `visiting` set catching a path back into a cell still
being evaluated, the same idea as DFS cycle detection in a directed graph. A memo persisted across
separate `get` calls would go stale the moment a cell it read is `set` again, since Part 1 keeps no
record of who depends on whom; a `memo` local to one call needs no invalidation and still gives $O(N)$
time for $N$ cells, since a shared sub-cell is evaluated once per call rather than once per path. The
price is recursion depth: three Python frames per cell of the longest chain, so a chain of about 330
cells exhausts the default limit of 1000.

```python
import re


class FormulaError(ValueError):
    """Bad cell name, or bad formula syntax."""


class CycleError(ValueError):
    """A formula depends on itself, directly or indirectly."""


CELL_RE = re.compile(r'[A-Z]+[0-9]+')


def _check_name(name):
    if not CELL_RE.fullmatch(name):  # NOTE: not match() with '$', which also accepts 'A1\n'
        raise FormulaError(f"not a valid cell name: {name!r}")


_TERM = r'(?:[A-Z]+[0-9]+|[0-9]{1,18})'
_FORMULA_RE = re.compile(rf' *{_TERM}(?: *[+-] *{_TERM})* *')  # spaces only around terms
_SIGNED_TERM_RE = re.compile(rf'[+-]?{_TERM}')


def parse_formula(formula):
    """Returns the formula's (sign, kind, value) terms, kind in {'NUM', 'CELL'}."""
    if not isinstance(formula, str) or not formula.startswith('='):
        raise FormulaError(f"formula must start with '=': {formula!r}")
    body = formula[1:]
    if not _FORMULA_RE.fullmatch(body):  # NOTE: a bare term comes first, so no unary minus ("=-A1")
        raise FormulaError(f"not a valid formula: {formula!r}")
    terms = []
    for tok in _SIGNED_TERM_RE.findall(body.replace(' ', '')):
        sign, tok = (-1, tok[1:]) if tok[0] == '-' else (1, tok.lstrip('+'))
        terms.append((sign, 'CELL', tok) if CELL_RE.fullmatch(tok) else (sign, 'NUM', int(tok)))
    return terms


def _referenced_cells(value):
    """Validates value; returns the cells its formula references (empty for a literal)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return set()
    if isinstance(value, str) and value.startswith('='):
        return {item for _, kind, item in parse_formula(value) if kind == 'CELL'}
    raise FormulaError(f"neither an int nor a formula: {value!r}")


def _eval_terms(value, lookup):
    """lookup(cell) returns the value of a cell the formula reads."""
    if isinstance(value, int):
        return value
    total = 0
    for sign, kind, item in parse_formula(value):
        total += sign * (item if kind == 'NUM' else lookup(item))
    return total


class LazySpreadsheet:
    def __init__(self):
        self.contents = {}

    def set(self, name, value):
        _check_name(name)
        _referenced_cells(value)  # validate now; get() parses the formula again
        self.contents[name] = value  # NOTE: no cycle check here; get() finds cycles

    def get(self, name):
        _check_name(name)
        return self._eval(name, set(), {})

    def _eval(self, name, visiting, memo):
        if name in memo:
            return memo[name]
        if name in visiting:
            raise CycleError(f"circular reference through {name!r}")
        value = self.contents.get(name)
        if value is None:
            result = 0
        else:
            visiting.add(name)  # NOTE: mark before recursing, so a path back to `name` is caught
            result = _eval_terms(value, lambda c: self._eval(c, visiting, memo))
            visiting.discard(name)  # NOTE: visiting is the current path; finished cells answer from memo
        memo[name] = result
        return result
```

### Part 2

Two maps replace the recursion: `dependencies[name]` is what `name`'s formula reads, `dependents[name]`
is who reads `name`. A formula referencing `refs` creates a cycle exactly when some cell in `refs` is
`name` itself or already transitively depends on `name` — i.e. `name` can reach it by walking
`dependents` forward. One traversal from `name` over `dependents`, run *before* touching anything,
answers that (is any of `refs` in the reached set?) and also gives `affected`: exactly the cells to
recompute, since that set depends only on who reads `name`, untouched by this call. Because the check
runs before any mutation, rejecting means simply not proceeding; committing first and rolling back on
a detected cycle would have to restore the cell's *previous* formula, not just erase it — easy to get
wrong for a cell that already existed. Once accepted, `affected` is recomputed in topological order, so
a diamond-shaped dependency is visited once, not once per path into it.

```python
from collections import deque


class Spreadsheet:
    def __init__(self):
        self.contents = {}
        self.cache = {}
        self.dependencies = {}   # cell -> set of cells it reads
        self.dependents = {}     # cell -> set of cells that read it

    def set(self, name, value):
        _check_name(name)
        new_refs = _referenced_cells(value)  # raises FormulaError; touches nothing yet
        affected = self._affected(name)      # everyone that (transitively) reads `name`, incl. itself
        if new_refs & affected:
            raise CycleError(f"{name} = {value!r} would close a cycle")
        # NOTE: nothing above was mutated, so a rejected set needs no rollback.

        for old in self.dependencies.get(name, ()):  # NOTE: drop old edges first -- otherwise a formula
            self.dependents[old].discard(name)         #       that no longer reads X would still recompute on X
        self.dependencies[name] = new_refs
        for r in new_refs:
            self.dependents.setdefault(r, set()).add(name)
        self.contents[name] = value
        for cell in self._topological_order(affected):
            self._recompute_one(cell)

    def get(self, name):
        _check_name(name)
        return self.cache.get(name, 0)

    def _affected(self, name):
        """name plus everything reachable from it by following `dependents` (who reads whom)."""
        affected, stack = {name}, [name]
        while stack:
            cell = stack.pop()
            for dep in self.dependents.get(cell, ()):
                if dep not in affected:
                    affected.add(dep)
                    stack.append(dep)
        return affected

    def _topological_order(self, affected):
        indegree = {c: sum(d in affected for d in self.dependencies.get(c, ())) for c in affected}
        queue = deque(c for c in affected if not indegree[c])
        order = []
        while queue:
            c = queue.popleft()
            order.append(c)
            for dep in self.dependents.get(c, ()):
                if dep in affected:
                    indegree[dep] -= 1
                    if not indegree[dep]:
                        queue.append(dep)
        return order

    def _recompute_one(self, cell):
        value = self.contents.get(cell)
        self.cache[cell] = 0 if value is None else _eval_terms(
            value, lambda c: self.cache.get(c, 0))
```

`get` is a name check plus one dict lookup: a few hundred nanoseconds, the same on a sheet of two cells
as on one of 20000. `set` takes time linear in the number of affected cells plus the length of their
formulas (and of `name`'s old one), since every dependency edge it follows is a term of one of those
formulas: several microseconds per cell of a long chain, however many cells lie outside it.

### Part 3

The first three fall out of the pieces above: dropping old edges is the loop right after the cycle
check in `set`; a never-`set` cell reads as `0` through `.get(name, 0)`, and setting it later finds its
readers in `dependents` like any other `set`; `LazySpreadsheet` keeps no graph, so it finds a cycle
only by recursing into one. The diamond is what the topological order is for: `_affected` collects each cell
once and `_topological_order` emits each once, so no cell is recomputed twice in one `set`. The last
point is the same code path seen from the other side: `set` reads `self.dependencies.get(name, ())`
before writing anything, which is simply empty the first time `name` holds a formula, so adding edges
for a literal-to-formula change and dropping edges for the reverse are the same four lines, not two
separate cases to keep in sync.

### Follow-ups

- A range such as `SUM(A1:A100)` would add a dependency edge to every cell it covers; the hard part is
  updating that edge set when rows are inserted or deleted, not evaluating the sum itself.
- A batched `set_many` must check for cycles with all of its new edges in place, since two writes can
  close a cycle together (`X1 = "=Y1"`, `Y1 = "=X1"`); one Kahn topological sort over the union of the
  affected cells both detects that and gives the recompute order, so $B$ writes touching $K$ cells cost
  $O(K)$, not $O(B \cdot K)$.
- Eager recomputation pays for every `set`, even one nobody reads again; a sheet written far more often
  than it is read favors marking dependents merely "dirty" and recomputing only on the next `get`.

<details>
<summary>Checks (runnable)</summary>

```python
import random
import re
import time


def expect(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} from {fn.__name__}{args!r}")


# ---- the worked example from the statement, both spreadsheets ----
for Sheet in (LazySpreadsheet, Spreadsheet):
    sh = Sheet()
    sh.set('P4', 6)
    sh.set('Q2', 17)
    sh.set('M3', '=Q2 - P4')
    sh.set('M8', '=M3 - P4 + 30')
    assert sh.get('M8') == 35
    sh.set('P4', 14)
    assert sh.get('M8') == 19 and sh.get('M3') == 3

# ---- LazySpreadsheet: set() stores cycles; get() raises on every cell that needs one ----
lz = LazySpreadsheet()
lz.set('U1', '=U2')
lz.set('U2', '=U1')
lz.set('V1', '=U1 + 1')  # not on the cycle, but reads it
lz.set('H2', '=H2 + 1')  # self-reference
lz.set('W1', 5)
for cell in ('U1', 'U2', 'V1', 'H2'):
    expect(CycleError, lz.get, cell)
assert lz.get('W1') == 5
lz.set('U2', 8)  # overwriting breaks both cycles
lz.set('H2', 3)
assert (lz.get('U1'), lz.get('V1'), lz.get('H2')) == (8, 9, 3)
deep = LazySpreadsheet()  # the longest chain Part 1 allows
deep.set('K1', 1)
for i in range(2, 201):
    deep.set(f'K{i}', f'=K{i - 1} + 1')
assert deep.get('K200') == 200
for i in range(201, 400):
    deep.set(f'K{i}', f'=K{i - 1} + 1')
expect(RecursionError, deep.get, 'K399')  # ~3 frames per cell: 399 cells pass the limit of 1000


# ---- Spreadsheet: set() rejects a cycle and changes nothing ----
def state(sh):
    return (dict(sh.contents), dict(sh.cache),
            {k: set(v) for k, v in sh.dependencies.items()}, {k: set(v) for k, v in sh.dependents.items()})


sh = Spreadsheet()
sh.set('U1', '=U2 + 1')  # U2 is not set yet; reads as 0 for now
sh.set('H2', 7)
sh.set('V1', '=H2 + U1')
before = state(sh)
for name, value in (('U2', '=U1'), ('H2', '=H2 + 1'), ('H2', '=V1 - 2'), ('U2', '=V1')):
    expect(CycleError, sh.set, name, value)
    assert state(sh) == before
assert (sh.get('U1'), sh.get('H2'), sh.get('V1')) == (1, 7, 8)
sh.set('U1', 4)  # U1 stops reading U2 ...
sh.set('U2', '=U1')  # ... so this no longer closes a cycle
assert (sh.get('U2'), sh.get('V1')) == (4, 11)

# ---- Part 3 and the statement's syntax rules ----
for bad_name in ('a1', '1A', 'A', 'A1B', 'A 1', 'A1\n'):
    for sheet in (LazySpreadsheet(), Spreadsheet()):
        expect(FormulaError, sheet.set, bad_name, 1)
        expect(FormulaError, sheet.get, bad_name)
for bad in ('=', '=D4*2', '=(D4+2)', '=D4++E4', '=D4--E4', '=D4 - -E4', '=D4+', '=-D4', '=+D4', '=D4 E4',
            '=D 4', '=D4 2', '=d4+2', '=D4\t+ 2', '=' + '9' * 19, '=' + '9' * 5000, '42', ' =D4', 4.0, True):
    for sheet in (LazySpreadsheet(), Spreadsheet()):
        expect(FormulaError, sheet.set, 'D5', bad)
sh = Spreadsheet()
for good, value in (('=5', 5), ('=007', 7), ('=' + '9' * 18, 10 ** 18 - 1), ('=  D4 +E4 -  3 ', -3)):
    sh.set('D5', good)
    assert sh.get('D5') == value

sh = Spreadsheet()  # overwriting drops the old dependency
sh.set('J1', 4)
sh.set('K1', '=J1 + 6')
sh.set('K1', 70)
assert 'K1' not in sh.dependents['J1']
sh.set('J1', 500)
assert sh.get('K1') == 70

sh = Spreadsheet()  # ... and the reverse: a literal overwritten with a formula picks up edges at once
sh.set('J1', 4)
sh.set('K1', 70)
sh.set('K1', '=J1 + 6')
assert 'K1' in sh.dependents['J1'] and sh.get('K1') == 10
sh.set('J1', 500)
assert sh.get('K1') == 506

sh = Spreadsheet()  # a formula may reference a cell that is set only later
sh.set('M1', '=N1 + 5')
sh.set('M2', '=M1 - 1')
assert (sh.get('N1'), sh.get('M2')) == (0, 4)
sh.set('N1', 3)
assert sh.get('M2') == 7

sh = Spreadsheet()  # diamond: recomputed exactly once per set()
calls, recompute = [], sh._recompute_one
sh._recompute_one = lambda cell: (calls.append(cell), recompute(cell))
sh.set('E5', 2)
sh.set('F5', '=E5 + 3')
sh.set('G5', '=E5 - 1')
sh.set('H5', '=F5 + G5')
calls.clear()
sh.set('E5', 40)
assert sorted(calls) == ['E5', 'F5', 'G5', 'H5'] and sh.get('H5') == 43 + 39

# ---- cross-validation against a naive evaluator written from the statement alone ----
# It shares no code with the solution: its own reference regex, its own cycle rule, eval for arithmetic.
CELL_PATTERN = re.compile(r'[A-Z]+[0-9]+')


def naive_values(raw):
    """raw: cell -> int or formula. Values of the cells that need no cycle; the rest of raw is missing."""
    values, progress = {}, True
    while progress:  # keep evaluating cells whose references are all known or never set
        progress = False
        for cell, v in raw.items():
            refs = [] if isinstance(v, int) else CELL_PATTERN.findall(v)
            if cell not in values and all(r in values or r not in raw for r in refs):
                expr = str(v) if isinstance(v, int) else CELL_PATTERN.sub(
                    lambda m: str(values.get(m.group(), 0)), v[1:])
                assert re.fullmatch(r'[0-9+\- ]+', expr)  # eval only ever sees digits, '+', '-', spaces
                values[cell] = eval(expr, {'__builtins__': {}}, {})
                progress = True
    return values


def random_value(rng, pool, readers):
    r = rng.random()
    if readers and r < 0.25:
        return f"={rng.choice(readers)} + 1"  # closes a cycle
    if r < 0.4:
        return rng.randint(-20, 20)
    text = rng.choice(pool)
    for _ in range(rng.randint(0, 2)):
        text += rng.choice([' + ', '-']) + rng.choice(pool + ['0', '7', '42'])
    return '=' + text


def cross_validate(seed, steps=300):
    rng = random.Random(seed)
    pool = [f"{c}{r}" for c in "ABC" for r in range(1, 5)]
    eager, lazy, eager_raw, lazy_raw = Spreadsheet(), LazySpreadsheet(), {}, {}
    rejected = lazy_cycles = 0
    for _ in range(steps):
        name = rng.choice(pool)
        readers = [c for c, v in eager_raw.items() if isinstance(v, str) and name in CELL_PATTERN.findall(v)]
        value = random_value(rng, pool, readers)
        lazy.set(name, value)  # Part 1 stores cycles too
        lazy_raw[name] = value
        trial = {**eager_raw, name: value}
        expected = naive_values(trial)
        if len(expected) < len(trial):  # the new value would close a cycle
            before = [eager.get(c) for c in pool]
            expect(CycleError, eager.set, name, value)
            assert [eager.get(c) for c in pool] == before
            rejected += 1
        else:
            eager.set(name, value)
            eager_raw = trial
            assert all(eager.get(c) == expected.get(c, 0) for c in pool)
        lazy_expected = naive_values(lazy_raw)
        for c in pool:
            if c in lazy_raw and c not in lazy_expected:
                expect(CycleError, lazy.get, c)
                lazy_cycles += 1
            else:
                assert lazy.get(c) == lazy_expected.get(c, 0)
    return rejected, lazy_cycles


results = [cross_validate(seed) for seed in range(20)]
assert all(r >= 20 and c >= 100 for r, c in results)  # both cycle paths exercised in every run


# ---- timing: ratios only, since absolute times depend on the machine ----
def best_per_call(fn, n, repeats=5):
    best = float('inf')
    for _ in range(repeats):  # the minimum over repeats shrugs off background load
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        best = min(best, (time.perf_counter() - t0) / n)
    return best


def chain_sheet(length, unrelated):
    sh = Spreadsheet()
    sh.set('C0', 0)
    for i in range(1, length):
        sh.set(f'C{i}', f'=C{i - 1} + 1')
    for i in range(unrelated):
        sh.set(f'Y{i}', i)
    return sh


small, big = chain_sheet(2, 0), chain_sheet(2, 20000)
get_small = best_per_call(lambda: small.get('C1'), 20000)
get_big = best_per_call(lambda: big.get('C1'), 20000)
assert get_big < 5 * get_small  # get() does not grow with the sheet

bare, crowded = chain_sheet(2000, 0), chain_sheet(2000, 20000)
set_bare = best_per_call(lambda: bare.set('C0', 1), 3)
set_crowded = best_per_call(lambda: crowded.set('C0', 1), 3)
assert set_crowded < 5 * set_bare  # set() does not grow with cells outside the affected set
assert crowded.get('C1999') == 1 + 1999

print(f"get: {get_small * 1e9:.0f} ns on 2 cells, {get_big * 1e9:.0f} ns on 20002; set through a 2000-cell "
      f"chain: {set_bare / 2000 * 1e6:.1f} us/cell, {set_crowded / 2000 * 1e6:.1f} us/cell with 20000 more")
print("all checks OK; (rejected sets, lazy CycleErrors) for the first seeds:", results[:3])
```

</details>

</details>
