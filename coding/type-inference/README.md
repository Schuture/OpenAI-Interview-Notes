# Type Inference for a Toy Language

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★★☆ | Medium | SWE · RE | recursion, unification, tree | 2 parts |
<!-- meta:end -->

## Problem

A *type* is either atomic or a tuple. An atomic type is named by a string: one of the five
primitives `int`, `float`, `str`, `bool`, `char`, or a generic such as `T1`, `T2`, `T3`, .... A tuple
type holds zero or more types, nested to any depth. A *function* has a list of parameter types and one
return type:

```text
Type      ::= Primitive | Generic | Tuple
Primitive ::= "int" | "float" | "str" | "bool" | "char"
Generic   ::= "T" Digit+
Tuple     ::= "[" [Type ("," Type)*] "]"
Function  ::= "(" [Type ("," Type)*] ")" "->" Type
```

A type is given directly as a Python object, never as text to parse:

```py
class Node:
    def __init__(self, value: Union[str, List["Node"]]) -> None:
        """An atomic node: value is its name. A tuple node: value is the list of its element
        types, possibly empty."""

class Function:
    def __init__(self, parameters: List[Node], return_type: Node) -> None: ...
```

### Part 1 — String representation

Implement `Node.__str__`, `Function.__str__`, and structural equality `Node.__eq__` (two nodes are
equal exactly when their string forms are equal). An atomic node's string is its name. A tuple node's
string lists its elements separated by commas with no space after a comma, inside square brackets:
`[t1,t2,...]`, and `[]` for an empty tuple. A function's string lists its parameters the same way
inside parentheses, then one space, `->`, one space, then the return type: `(p1,p2,...) -> returnType`.

```py
def __str__(self) -> str: ...        # Node
def __eq__(self, other) -> bool: ... # Node
def __str__(self) -> str: ...        # Function
```

Example: the function taking the tuple `[T1, bool]`, then `T2`, then `char`, and returning the tuple
`[T2, [T1, int]]` prints as:

```text
([T1,bool],T2,char) -> [T2,[T1,int]]
```

### Part 2 — Return-type inference

The five primitives above are fixed, and every other atomic name is a *generic*: what counts is whether
a name is a primitive, not the spelling `T` followed by digits. A call supplies one concrete type per
declared parameter, in a list `parameters`; a concrete type never contains a generic. Implement:

```py
def get_return_type(parameters: List[Node], function: Function) -> Node: ...
```

It matches each of `function.parameters[i]` against `parameters[i]` (*unification*): a generic in the
declared type is bound to whatever concrete type occupies the same position in the call, every
occurrence of the same generic name within one call must bind to the same (structurally equal) type,
and a generic may bind to an entire tuple, not only to a primitive. It then returns
`function.return_type` with every generic replaced by its binding (*substitution*). Three errors are
possible:

- `ArityError` — `len(parameters) != len(function.parameters)`.
- `TypeMismatchError` — at some position with no generic involved, the two types differ: a different
  primitive, or tuples of different length.
- `GenericConflictError` — the same generic name would have to bind to two structurally different
  types within one call.

Examples, using the Part 1 string form as shorthand (`call` lists the concrete argument types in order):

```text
function: (T1,bool,T2) -> [T2,T1]
call: char, bool, float
-> [float,char]

function: (T1,[T1,bool],T2) -> [T2,[T1,T1]]
call: char, [char,bool], int
-> [int,[char,char]]

function: (T1,bool) -> [T1,T1]
call: [int,float], bool
-> [[int,float],[int,float]]

function: (T1,int,bool) -> T1
call: char, int
-> ArityError: expected 3 arguments, got 2

function: ([T1,int],bool) -> T1
call: [char,int,bool], bool
-> TypeMismatchError: expected [T1,int] but received [char,int,bool]

function: (int,T3,T3) -> T3
call: int, bool, char
-> GenericConflictError: T3 is bound to two different types: bool and char
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Confirm with the interviewer whether the three errors need distinct exception types or one type with
an error code (this page uses three small classes with a shared base), and whether an empty tuple and
a zero-parameter function are legal (both are, here). Keep matching and substitution as two separate
functions — merging them invites a bug where a still-unbound generic leaks into the return type.

### Part 1

`Node` stores exactly one of two things: `name` for an atomic node, `children` for a tuple, the other
field left `None`. That single check is enough to tell the two cases apart, including the empty tuple
(`children == []`, not `None`). `__str__` recurses over `children` when it is not `None`, otherwise
returns `name`; `Function.__str__` joins `parameters` the same way and appends the return type.

```python
from typing import List, Union


PRIMITIVES = {"int", "float", "str", "bool", "char"}


class Node:
    def __init__(self, value: Union[str, List["Node"]]) -> None:
        if isinstance(value, str):
            self.name, self.children = value, None
        else:
            self.name, self.children = None, list(value)   # NOTE: [] is a legal empty tuple, distinct from None

    def __str__(self) -> str:
        if self.children is None:
            return self.name
        return "[" + ",".join(str(c) for c in self.children) + "]"

    def __eq__(self, other) -> bool:
        return isinstance(other, Node) and str(self) == str(other)   # structural equality, via the string form

    def clone(self) -> "Node":
        if self.children is None:
            return Node(self.name)
        return Node([c.clone() for c in self.children])


class Function:
    def __init__(self, parameters: List[Node], return_type: Node) -> None:
        self.parameters, self.return_type = list(parameters), return_type

    def __str__(self) -> str:
        return "(" + ",".join(str(p) for p in self.parameters) + ") -> " + str(self.return_type)
```

### Part 2

`get_return_type` runs two passes over the trees. `bind_generics` walks `function.parameters` and
`parameters` two nodes at a time and fills one dict `bindings` (generic name → concrete `Node`); then
`substitute_generics` walks `function.return_type` once and replaces every generic it finds with its
binding.

`bind_generics` must check whether the declared side is a generic *before* anything else, and that
check has to ask about the node itself, never about whether a generic appears somewhere inside it — a
tuple such as `[T1,int]` is not a generic (it has to fall through to the tuple branch and match its two
children separately), even though `T1` is generic *inside* it. Only once that case is ruled out does
structural equality apply (both sides fully concrete and already identical), then tuple-vs-tuple
recursion; anything left over is a mismatch:

```python
class TypeInferenceError(Exception):
    pass


class ArityError(TypeInferenceError):
    pass


class TypeMismatchError(TypeInferenceError):
    pass


class GenericConflictError(TypeInferenceError):
    pass


def is_tuple(node: Node) -> bool:
    return node.children is not None


def is_generic_base(node: Node) -> bool:
    # NOTE: asks about `node` itself, never about a generic somewhere inside it -- see contains_generic below.
    return not is_tuple(node) and node.name not in PRIMITIVES


def contains_generic(node: Node) -> bool:
    if is_tuple(node):
        return any(contains_generic(c) for c in node.children)
    return is_generic_base(node)


def bind_generics(expected: Node, actual: Node, bindings: dict) -> None:
    if is_generic_base(expected):                                    # 1. a generic: bind it, or check the old binding
        if expected.name in bindings:
            if bindings[expected.name] != actual:
                raise GenericConflictError(
                    f"{expected.name} is bound to two different types: {bindings[expected.name]} and {actual}")
        else:
            bindings[expected.name] = actual.clone()                  # NOTE: clone so `bindings` never aliases `actual`
        return
    if expected == actual:                                           # 2. both concrete, and already identical
        return
    if is_tuple(expected) and is_tuple(actual):                      # 3. neither is a generic: recurse into tuples
        if len(expected.children) != len(actual.children):
            raise TypeMismatchError(f"expected {expected} but received {actual}")
        for e, a in zip(expected.children, actual.children):
            bind_generics(e, a, bindings)
        return
    raise TypeMismatchError(f"expected {expected} but received {actual}")   # 4. concrete and different
```

Substitution walks the return type once. A subtree with no generic in it at all is copied as is; a
bare generic is replaced by its binding, which may itself be a tuple; anything else is a tuple rebuilt
from substituted children. Every branch returns a *clone*, never a node taken from `function.return_type`
or from `bindings` directly: `function` is reused across many calls, so a node written into one call's
result must not be part of the object graph that the next call reads from; and within a single call, a
generic that appears twice in the return type must produce two independent `Node` objects, or mutating
one copy would silently mutate the other.

```python
def substitute_generics(node: Node, bindings: dict) -> Node:
    if not contains_generic(node):
        return node.clone()
    if is_generic_base(node):
        return bindings[node.name].clone()
    return Node([substitute_generics(c, bindings) for c in node.children])


def get_return_type(parameters: List[Node], function: Function) -> Node:
    if len(parameters) != len(function.parameters):
        raise ArityError(f"expected {len(function.parameters)} arguments, got {len(parameters)}")
    bindings: dict = {}
    for expected, actual in zip(function.parameters, parameters):
        bind_generics(expected, actual, bindings)
    return substitute_generics(function.return_type, bindings)
```

### Follow-ups

- If `parameters` may also contain generics, matching needs to run in both directions and add an
  *occurs check* that refuses to bind a generic to a type containing that same generic, or substitution
  would recurse forever.
- Adding subtyping (e.g. `int <: float`) or a union type turns each equality check into "is a subtype
  of" or "matches one branch", and a generic can then have more than one valid binding, so the
  algorithm has to track a common supertype instead of one fixed type.

<details>
<summary>Checks (runnable)</summary>

```python
fn1 = Function([Node([Node("T1"), Node("bool")]), Node("T2"), Node("char")],
               Node([Node("T2"), Node([Node("T1"), Node("int")])]))
assert str(fn1) == "([T1,bool],T2,char) -> [T2,[T1,int]]"
assert str(Node([])) == "[]"

examples = [
    (Function([Node("T1"), Node("bool"), Node("T2")], Node([Node("T2"), Node("T1")])),
     [Node("char"), Node("bool"), Node("float")], "[float,char]"),
    (Function([Node("T1"), Node([Node("T1"), Node("bool")]), Node("T2")],
              Node([Node("T2"), Node([Node("T1"), Node("T1")])])),
     [Node("char"), Node([Node("char"), Node("bool")]), Node("int")], "[int,[char,char]]"),
    (Function([Node("T1"), Node("bool")], Node([Node("T1"), Node("T1")])),
     [Node([Node("int"), Node("float")]), Node("bool")], "[[int,float],[int,float]]"),
]
for function, parameters, expected in examples:
    assert str(get_return_type(parameters, function)) == expected

fn_arity = Function([Node("T1"), Node("int"), Node("bool")], Node("T1"))
try:
    get_return_type([Node("char"), Node("int")], fn_arity)
    raise AssertionError
except ArityError as e:
    assert str(e) == "expected 3 arguments, got 2"

fn_mismatch = Function([Node([Node("T1"), Node("int")]), Node("bool")], Node("T1"))
try:
    get_return_type([Node([Node("char"), Node("int"), Node("bool")]), Node("bool")], fn_mismatch)
    raise AssertionError
except TypeMismatchError as e:
    assert str(e) == "expected [T1,int] but received [char,int,bool]"

fn_conflict = Function([Node("int"), Node("T3"), Node("T3")], Node("T3"))
try:
    get_return_type([Node("int"), Node("bool"), Node("char")], fn_conflict)
    raise AssertionError
except GenericConflictError as e:
    assert str(e) == "T3 is bound to two different types: bool and char"

# Two occurrences of the same generic in the return type must be independent objects.
result = get_return_type([Node([Node("int"), Node("float")]), Node("bool")],
                          Function([Node("T1"), Node("bool")], Node([Node("T1"), Node("T1")])))
assert result.children[0] is not result.children[1]

# Randomised cross-check: substituting a random binding into a random signature must agree with
# unifying the resulting (generic-free) call against that same signature.
import random


def generic_names_in(node):
    if is_tuple(node):
        return {n for c in node.children for n in generic_names_in(c)}
    return {node.name} if is_generic_base(node) else set()


def random_node(rng, generics, depth):
    if depth == 0 or rng.random() < 0.5:
        return Node(rng.choice(sorted(PRIMITIVES) + sorted(generics)))
    return Node([random_node(rng, generics, depth - 1) for _ in range(rng.randint(1, 2))])


def random_function(rng, generics=("T1", "T2")):
    parameters = [random_node(rng, generics, 2) for _ in range(3)]
    parameters[0] = random_node(rng, (), 2)              # NOTE: a purely concrete slot, for mismatch tests below
    g = rng.choice(generics)
    parameters[1] = parameters[2] = Node(g)              # NOTE: one generic reused, for conflict tests below
    used = sorted({name for p in parameters for name in generic_names_in(p)})
    return_type = random_node(rng, used, 2) if used else random_node(rng, (), 2)
    return Function(parameters, return_type)


def corrupt(rng, node):
    if is_tuple(node) and node.children:
        i = rng.randrange(len(node.children))
        return Node([corrupt(rng, c) if j == i else c for j, c in enumerate(node.children)])
    return Node(rng.choice(sorted(PRIMITIVES - {node.name})))


rng = random.Random(0)
for _ in range(300):
    function = random_function(rng)
    used = sorted({name for p in function.parameters for name in generic_names_in(p)})
    bindings = {name: random_node(rng, (), 2) for name in used}
    parameters = [substitute_generics(p, bindings) for p in function.parameters]
    expected = substitute_generics(function.return_type, bindings)
    assert get_return_type(parameters, function) == expected

    for i, error in ((None, ArityError), (0, TypeMismatchError), (2, GenericConflictError)):
        bad = parameters[:-1] if i is None else [corrupt(rng, p) if j == i else p for j, p in enumerate(parameters)]
        try:
            get_return_type(bad, function)
            raise AssertionError(f"expected {error.__name__}")
        except error:
            pass
```

</details>

</details>
