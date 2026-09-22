# 玩具语言的类型推断

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★★☆ | 中等 | SWE · RE | recursion, unification, tree | 2 个部分 |
<!-- meta:end -->

## 题目

一个*类型*（type）要么是原子的，要么是元组。原子类型用一个字符串命名：要么是五个基本类型
（primitive）`int`、`float`、`str`、`bool`、`char` 之一，要么是一个泛型（generic），例如 `T1`、`T2`、
`T3`、……。元组类型包含零个或多个类型，可以任意嵌套。一个*函数*（function）有一份参数类型列表和一个返回类型：

```text
Type      ::= Primitive | Generic | Tuple
Primitive ::= "int" | "float" | "str" | "bool" | "char"
Generic   ::= "T" Digit+
Tuple     ::= "[" [Type ("," Type)*] "]"
Function  ::= "(" [Type ("," Type)*] ")" "->" Type
```

类型直接用 Python 对象给出，不需要解析文本：

```py
class Node:
    def __init__(self, value: Union[str, List["Node"]]) -> None:
        """An atomic node: value is its name. A tuple node: value is the list of its element
        types, possibly empty."""

class Function:
    def __init__(self, parameters: List[Node], return_type: Node) -> None: ...
```

### Part 1 —— 字符串表示

实现 `Node.__str__`、`Function.__str__`，以及结构相等 `Node.__eq__`（两个节点相等当且仅当它们的字符串形式相等）。
原子节点的字符串就是它的名字。元组节点的字符串把各个元素用逗号连接、逗号后不加空格，再放进方括号里：
`[t1,t2,...]`，空元组是 `[]`。函数的字符串把参数按同样的方式放进圆括号里，接一个空格、`->`、再一个空格，然后是返回类型：
`(p1,p2,...) -> returnType`。

```py
def __str__(self) -> str: ...        # Node
def __eq__(self, other) -> bool: ... # Node
def __str__(self) -> str: ...        # Function
```

例子：一个函数，参数依次是元组 `[T1, bool]`、`T2`、`char`，返回元组 `[T2, [T1, int]]`，打印出来是：

```text
([T1,bool],T2,char) -> [T2,[T1,int]]
```

### Part 2 —— 返回类型推断

上面的五个基本类型是固定的，其余的原子名字都是*泛型*：判断依据是名字是不是基本类型，而不是 `T` 加数字这种拼写。一次调用给每个声明的参数一个具体类型，放在列表 `parameters` 里；具体类型里不会出现泛型。实现：

```py
def get_return_type(parameters: List[Node], function: Function) -> Node: ...
```

它把 `function.parameters[i]` 与 `parameters[i]` 逐个匹配（*合一，unification*）：声明类型里的泛型，
被绑定为调用里同一位置上的具体类型；同一次调用里，同一个泛型名的每一次出现都必须绑定到同一个（结构相等的）类型；
一个泛型可以绑定到整个元组，不只是基本类型。然后把 `function.return_type` 里的每个泛型替换成它绑定的类型，
作为返回值（*代入，substitution*）。可能出现三类错误：

- `ArityError` —— `len(parameters) != len(function.parameters)`。
- `TypeMismatchError` —— 在某个不涉及泛型的位置上，两个类型不同：基本类型不一样，或者元组长度不一样。
- `GenericConflictError` —— 同一次调用里，同一个泛型名被要求绑定到两个结构不同的类型。

下面的例子用 Part 1 的字符串形式作简写（`call` 按顺序列出具体实参类型）：

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

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前先向面试官确认：三类错误是要用不同的异常类型区分，还是用一个异常类型加错误码（本文用三个共享一个基类的小异常类）；
空元组和零参数函数是否合法（本文都算合法）。把匹配和代入写成两个独立的函数——合成一个函数很容易在返回类型里漏掉某个还没绑定的泛型。

### Part 1

`Node` 只存两样东西之一：原子节点存 `name`，元组节点存 `children`，另一个字段留 `None`。这一个判断就足以区分两种情况，
包括空元组（`children == []`，不是 `None`）。`__str__` 在 `children` 不是 `None` 时递归处理，否则直接返回 `name`；
`Function.__str__` 用同样的方式拼接 `parameters`，再接上返回类型。

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

`get_return_type` 在树上跑两遍。`bind_generics` 同时遍历 `function.parameters` 和 `parameters`，每次处理一对节点，
填一个字典 `bindings`（泛型名 → 具体的 `Node`）；然后 `substitute_generics` 遍历一遍 `function.return_type`，
把里面每个泛型换成它绑定的类型。

`bind_generics` 必须最先判断声明这一侧是不是泛型，而且这个判断只能问“这个节点本身是不是泛型”，绝不能问
“它内部某处是不是含有泛型”——像 `[T1,int]` 这样的元组本身不是泛型（它必须落到元组分支，把两个子节点分别匹配），
尽管 `T1` 在它*内部*是泛型。排除这种情况之后，才轮到结构相等（两边都是具体类型且已经相同），再之后才是元组对元组的递归；
剩下的情况就是不匹配：

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

代入只遍历一遍返回类型。内部完全不含泛型的子树原样拷贝一份；一个裸露的泛型换成它绑定的类型，这个绑定值本身也可能是个元组；
其余情况就是一个元组，用代入后的子节点重新搭建。每个分支返回的都是一份*拷贝*，绝不直接使用取自 `function.return_type`
或 `bindings` 的节点：`function` 会在多次调用间复用，所以写进这一次调用结果里的节点，不能和下一次调用读到的对象图有任何交集；
即使在同一次调用内部，如果同一个泛型在返回类型里出现两次，也必须产生两个互相独立的 `Node` 对象，否则改动其中一份会悄悄改到另一份。

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

### 追问

- 如果 `parameters` 里也可能出现泛型，匹配就要双向进行，还要加一个*跑圈检测*（occurs check），
  拒绝把一个泛型绑定到一个内部含有它自己的类型上，否则代入会无限递归下去。
- 给类型系统加上子类型（例如 `int <: float`）或联合类型，会把每一次“相等”判断换成“是……的子类型”或
  “匹配其中一个分支”，一个泛型因此可能有不止一个合法的绑定，算法要维护的就不再是一个固定类型，而是一个公共的父类型。

<details>
<summary>验证代码（可运行）</summary>

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
