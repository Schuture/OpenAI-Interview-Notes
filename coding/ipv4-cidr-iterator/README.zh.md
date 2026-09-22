# IPv4 / CIDR 迭代器

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★☆☆ | 中等 | SWE | bit-manipulation, iterator, string | 5 个部分 |
<!-- meta:end -->

## 题目

IPv4 地址写成用点分隔的四个十进制段，`"a.b.c.d"`。每一段在 `0` 到 `255` 之间，且不带前导零，除非这一段本身就是
`0`——所以 `"1.2.3.4"`、`"0.0.0.0"` 合法，`"1.2.03.4"`、`"1.2.00.4"` 不合法。这样一个地址对应 32 位整数
$a \cdot 2^{24} + b \cdot 2^{16} + c \cdot 2^{8} + d$，地址的大小顺序、以及迭代的顺序，都按这个整数来：
`0.0.0.0` 是最小的地址，`255.255.255.255` 是最大的地址。用一个类 `IPV4Iterator` 实现下面五个部分，
每一部分都在前一部分的构造函数和迭代行为上做扩展。如果构造函数的参数 `ip_or_cidr` 不能正好拆成四段这样的记法，
或者某一段不是上述形式，或者某一段的数值超过 `255`，构造函数就抛出 `ValueError`。五个部分里的非法参数一律抛出
`ValueError`，所以一个输入同时违反几条规则时，由哪一项检查先发现都可以。

### Part 1 —— 正向迭代

`ip_or_cidr` 是一个不带 `/` 的裸地址（带 `/` 是 Part 3 才加入的写法）。迭代按数值递增的顺序产生地址，每次调用产生一个，
从（且包含）`ip_or_cidr` 开始，一直到（且包含）`255.255.255.255`；此后再调用则抛出 `StopIteration`。
如果 `ip_or_cidr` 本身就是 `"255.255.255.255"`，就只产生这一个地址。

```py
class IPV4Iterator:
    def __init__(self, ip_or_cidr: str) -> None:
        """ip_or_cidr must be a bare address "a.b.c.d". Raises ValueError if it is not a valid
        address."""

    def __iter__(self) -> "IPV4Iterator": ...

    def __next__(self) -> str:
        """Returns the next address, starting from (and including) ip_or_cidr, in increasing
        numeric order, up to and including 255.255.255.255. Raises StopIteration afterwards."""
```

例如，从 `192.0.2.254` 开始：

```text
call 1: 192.0.2.254
call 2: 192.0.2.255
call 3: 192.0.3.0    # 最后一段超过 255，向前一段进位
call 4: 192.0.3.1
```

### Part 2 —— 反向迭代

新增 `reverse: bool = False`。当 `reverse=True` 时，迭代按数值递减的顺序产生地址，从（且包含）`ip_or_cidr` 开始，
一直到（且包含）`0.0.0.0`；此后再调用则抛出 `StopIteration`。如果 `ip_or_cidr` 本身就是 `"0.0.0.0"`，
就只产生这一个地址。

```py
class IPV4Iterator:
    def __init__(self, ip_or_cidr: str, reverse: bool = False) -> None:
        """reverse=False keeps Part 1's behaviour. reverse=True walks backward from (and
        including) ip_or_cidr, in decreasing numeric order, down to and including 0.0.0.0."""
```

例如，从 `192.0.2.1` 开始，`reverse=True`：

```text
call 1: 192.0.2.1
call 2: 192.0.2.0
call 3: 192.0.1.255   # 向前一段借位
call 4: 192.0.1.254
```

### Part 3 —— 限制在 CIDR 块内

`ip_or_cidr` 现在可以写成 `"a.b.c.d/prefix"`，即一个 *CIDR 块*：`prefix` 是 `0` 到 `32` 之间的整数，写法上遵循与地址段
相同的无前导零规则；如果它不是这种写法，或者数值不在 `0`-`32` 之间，构造函数就抛出 `ValueError`。
把地址的 32 位整数的低 `32 - prefix` 位清零，得到这个块的*网络地址*（network address）；
把这些低位全部置一，得到*广播地址*（broadcast address）；这个块就是从网络地址到广播地址（两端都含）的全部地址。
网络地址不必等于 `ip_or_cidr` 本身——因为网络地址正是由 `ip_or_cidr` 掩码得到的，所以给定的地址必然落在算出的块内。
迭代被限制在这个块里：正向在广播地址处停止（含广播地址），反向在网络地址处停止（含网络地址），迭代仍然从 `ip_or_cidr`
本身开始，它不必是块的任何一端。`/32` 块只有一个地址（`ip_or_cidr` 自己，此时它同时是块的两端）。`/0` 块是整个地址空间，
`0.0.0.0` 到 `255.255.255.255`，但迭代仍然从 `ip_or_cidr` 开始。

例如，块 `203.0.113.96`–`203.0.113.111`（即 `203.0.113.96/28`），从 `203.0.113.100` 开始：

```text
forward: 203.0.113.100, 203.0.113.101, ..., 203.0.113.111   （12 个地址，止于广播地址）
reverse: 203.0.113.100, 203.0.113.99, ..., 203.0.113.96      （5 个地址，止于网络地址）
```

特殊的前缀长度：`IPV4Iterator("198.51.100.77/32")` 只产生 `"198.51.100.77"`。
`IPV4Iterator("198.51.100.16/31")` 依次产生 `"198.51.100.16"`、`"198.51.100.17"`。
`IPV4Iterator("10.20.30.40/0")` 从 `"10.20.30.40"` 开始，正向要一直到 `"255.255.255.255"` 才停止。

### Part 4 —— 步长

新增 `step: int = 1`。`step` 必须是正整数；`step <= 0` 抛出 `ValueError`。
每次调用 `__next__`，当前位置沿 `reverse` 指定的方向前进 `step` 个地址；第一个产生的地址仍然是 `ip_or_cidr` 本身，
不受 `step` 影响。一旦下一个待产生的地址会落到允许范围之外（`0.0.0.0`–`255.255.255.255`，或 Part 3 的 CIDR 块），
迭代就停止——`step` 大于 `1` 时，这次跳跃可能直接越过边界而不会正好落在边界上，越过之后的地址永远不会被产生。

```py
class IPV4Iterator:
    def __init__(self, ip_or_cidr: str, reverse: bool = False, step: int = 1) -> None:
        """step is the number of addresses __next__ advances by on each call, in the direction
        reverse selects. Raises ValueError if step <= 0."""
```

例如，块 `203.0.113.16/28`（网络地址 `203.0.113.16`，广播地址 `203.0.113.31`），`step=3`：

```text
203.0.113.16, 203.0.113.19, 203.0.113.22, 203.0.113.25, 203.0.113.28, 203.0.113.31
# 下一个候选地址会是 203.0.113.34，已经超过广播地址 -> StopIteration
```

同一个块，从 `203.0.113.30` 开始，`reverse=True, step=4`：

```text
203.0.113.30, 203.0.113.26, 203.0.113.22, 203.0.113.18
# 下一个候选地址会是 203.0.113.14，已经低于网络地址 203.0.113.16 -> StopIteration
```

`IPV4Iterator("203.0.113.16/28", step=0)` 抛出 `ValueError`。

### Part 5 —— 批量读取

新增 `next_batch(size: int) -> list[str]`。它从当前位置开始，返回最多 `size` 个地址，等价于连续调用 `size` 次
`__next__` 并收集结果，区别在于它本身从不抛出 `StopIteration`：一旦迭代器即将耗尽，它就只返回不足 `size` 个的地址；
一旦没有地址剩余，就返回空列表。`size` 必须是非负整数；`size < 0` 抛出 `ValueError`。`size == 0` 总是返回 `[]`，
既不抛出异常，也不改变当前位置，无论迭代器当前是否已经耗尽。

```py
class IPV4Iterator:
    def next_batch(self, size: int) -> list[str]:
        """Returns up to size addresses from the current position, in the same order __next__
        would produce them. Returns fewer than size once fewer remain, [] once none remain.
        Raises ValueError if size < 0."""
```

例如，块 `203.0.113.16/28`（16 个地址，`203.0.113.16`–`203.0.113.31`）：

```text
it = IPV4Iterator("203.0.113.16/28")
it.next_batch(5)    -> ["203.0.113.16", "203.0.113.17", "203.0.113.18", "203.0.113.19", "203.0.113.20"]
it.next_batch(100)  -> 剩下的 11 个地址，最后一个是 "203.0.113.31"
it.next_batch(5)    -> []
```

## 参考解答

<details>
<summary>展开参考解答</summary>

有两点值得向面试官确认：非法输入是应该在构造函数里立刻报错（这里采用这种做法），还是等到第一次调用 `__next__` 时才报错；
CIDR 的种子地址是否必须已经是网络地址，还是像这里一样可以是块内任意地址——标准库的
`ipaddress.IPv4Network(s, strict=False)` 采用的正是同样“宽松”的做法。

### Part 1

把每个地址当作一个 32 位整数，最高位段在前；格式化时用 24、16、8、0 这四个位移把四个字节取出来，是它的逆运算。
一旦地址变成整数，“数值递增”就只是 `+= 1`，某一段超过 255 时的进位在这次加法里自动完成，不需要按段手写进位逻辑。
每次调用只用到几个整数状态，所以 `__next__` 是 $O(1)$ 的操作，对象占用的内存也是 $O(1)$，与已经走了多远无关——这一点很重要，
因为要走的路可能很长。从 `0.0.0.0` 开始，一次完整的正向遍历就有 $2^{32} = 4{,}294{,}967{,}296$ 个地址；
如果先把它们全部做成字符串列表再返回，内存放不下：每个字符串是一个约 60 字节的独立对象
（在 CPython 3.11 上 `sys.getsizeof("255.255.255.255")` 是 64），列表还要为每个元素存一个 8 字节的指针，
整个地址空间合计约 300 GB 量级。

```python
import re

_OCTET_RE = re.compile(r"\A(0|[1-9][0-9]{0,2})\Z")


def _parse_ip(s):
    parts = s.split(".")
    if len(parts) != 4:
        raise ValueError(f"expected 4 dot-separated octets, got {s!r}")
    value = 0
    for p in parts:
        if not _OCTET_RE.match(p):
            raise ValueError(f"bad octet {p!r} in {s!r}: must be digits with no leading zero")
        octet = int(p)
        if octet > 255:
            raise ValueError(f"octet {octet} out of range 0-255 in {s!r}")
        value = (value << 8) | octet      # NOTE: big-endian -- the leftmost octet is the most significant byte
    return value


def ip_to_int(ip):
    return _parse_ip(ip)


def int_to_ip(value):
    # NOTE: shifts 24,16,8,0 mirror _parse_ip's order -- swap either one and addresses would compare backwards
    return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


MAX_IP = (1 << 32) - 1   # 255.255.255.255


class IPV4Iterator:
    def __init__(self, ip_or_cidr):
        self._cursor = ip_to_int(ip_or_cidr)
        self._hi = MAX_IP

    def __iter__(self):
        return self

    def __next__(self):
        if self._cursor > self._hi:          # NOTE: > not >=, so MAX_IP itself is still produced
            raise StopIteration
        result = int_to_ip(self._cursor)
        self._cursor += 1
        return result
```

### Part 2

`reverse` 只改变每次移动的方向；`__next__` 把光标同时与范围的两端比较，哪个方向越界都会停下，
所以两个方向共用同一个 `__next__`。

```python
def __init__(self, ip_or_cidr, reverse=False):
    self._cursor = ip_to_int(ip_or_cidr)
    self._reverse = reverse
    self._lo, self._hi = 0, MAX_IP


def __next__(self):
    # NOTE: self._cursor is a plain Python int, so decrementing past 0 just makes it negative --
    # it does not wrap around the way a fixed-width unsigned counter would, and this comparison
    # alone is enough to catch the underflow, no separate "would this go negative" check needed
    if self._cursor < self._lo or self._cursor > self._hi:
        raise StopIteration
    result = int_to_ip(self._cursor)
    self._cursor += -1 if self._reverse else 1
    return result


IPV4Iterator.__init__ = __init__   # attach to the class defined in Part 1
IPV4Iterator.__next__ = __next__
```

### Part 3

掩码的低 `32 - prefix` 位是 `0`，其余是 `1`；把地址的这些低位清零得到网络地址，把这些低位置一得到广播地址。
`prefix == 0` 意味着移位整整 32 位。这在 Python 里没有问题：`0xFFFFFFFF << 32` 只是一个更宽的整数，低 32 位全是 `0`，
所以 `start & mask` 本来就是 `0`，末尾的 `& 0xFFFFFFFF` 只是让掩码本身保持 32 位宽。在 C 或 Java 里，
把 32 位整数移位 32 位是未定义行为或者等于不移位，`/0` 块会因此算错。`__next__` 完全不需要改动：它本来就只看
`self._lo`/`self._hi`，现在这两个值来自这个块，而不是整个地址空间。

```python
_PREFIX_RE = re.compile(r"\A(0|[1-9][0-9]?)\Z")


def _parse_prefix(s):
    if not _PREFIX_RE.match(s):
        raise ValueError(f"bad prefix {s!r}: must be digits with no leading zero")
    value = int(s)
    if not (0 <= value <= 32):
        raise ValueError(f"prefix {value} out of range 0-32")
    return value


def parse_ip_or_cidr(s):
    if s.count("/") > 1:
        raise ValueError(f"bad CIDR notation: {s!r}")
    if "/" in s:
        ip_part, prefix_part = s.split("/")
        return _parse_ip(ip_part), _parse_prefix(prefix_part)
    return _parse_ip(s), None


def network_and_broadcast(start, prefix):
    host_bits = 32 - prefix
    # NOTE: prefix == 0 shifts by 32 -- fine for a Python int (its low 32 bits come out 0), but a
    # 32-bit int in C/Java shifted by 32 is undefined or unchanged, and /0 comes out wrong
    mask = (0xFFFFFFFF << host_bits) & 0xFFFFFFFF
    network = start & mask
    broadcast = network + (1 << host_bits) - 1
    return network, broadcast


def __init__(self, ip_or_cidr, reverse=False):
    start, prefix = parse_ip_or_cidr(ip_or_cidr)
    self._cursor = start
    self._reverse = reverse
    if prefix is None:
        self._lo, self._hi = 0, MAX_IP
    else:
        self._lo, self._hi = network_and_broadcast(start, prefix)


IPV4Iterator.__init__ = __init__      # attach to the class of Part 1; Part 2's __next__ needs no change
```

### Part 4

`step` 只改变每次跳跃的距离，边界检查仍是同一个比较：跳出 `self._lo`/`self._hi` 的那一步，
和步长为 `1` 时一样会被拦下，区别只是它可能越过边界地址，而不是正好落在上面。

```python
def __init__(self, ip_or_cidr, reverse=False, step=1):
    start, prefix = parse_ip_or_cidr(ip_or_cidr)
    if step <= 0:
        raise ValueError(f"step must be a positive integer, got {step}")
    self._cursor = start
    self._reverse = reverse
    self._step = step
    if prefix is None:
        self._lo, self._hi = 0, MAX_IP
    else:
        self._lo, self._hi = network_and_broadcast(start, prefix)


def __next__(self):
    if self._cursor < self._lo or self._cursor > self._hi:
        raise StopIteration
    result = int_to_ip(self._cursor)
    self._cursor += -self._step if self._reverse else self._step
    return result


IPV4Iterator.__init__ = __init__
IPV4Iterator.__next__ = __next__
```

### Part 5

`next_batch` 就是对 `__next__` 的一次有上限的抽取，因此上面所有的停止规则都直接继承下来，不需要重新推导一遍。

```python
def next_batch(self, size):
    if size < 0:
        raise ValueError(f"size must be non-negative, got {size}")
    out = []
    for _ in range(size):
        try:
            out.append(next(self))
        except StopIteration:
            break
    return out


IPV4Iterator.next_batch = next_batch
```

调用方如果以 `len(batch) < size` 作为取完的信号，就必须用 `size > 0`：`size == 0` 时这个条件是 `0 < 0`，
永远不成立，循环一个地址也拿不到，却永远不会结束。

| 方法 | 每次调用的时间 | 额外内存 |
| --- | --- | --- |
| `__init__` | $O(1)$ | $O(1)$ |
| `__next__` | $O(1)$ | $O(1)$ |
| `next_batch(size)` | $O(k)$，$k$ 为返回的地址数 | $O(k)$ |

### 追问

- IPv6 地址是 128 位的；同样的掩码思路用 Python 任意精度整数原样成立，只需把上面的 `32`/`0xFFFFFFFF` 换成
  `128`/`(1 << 128) - 1`。
- 如果要在遍历一个 CIDR 块时跳过其中某些子块，做法是直接跳到被跳过子块的广播地址之后（或网络地址之前），
  而不是一个地址一个地址地走过去。
- 遍历多个 CIDR 块的并集，需要先把这些块合并成互不相交、按顺序排列的区间，否则重叠部分会被重复产生。
- 多个线程同时调用同一个 `IPV4Iterator` 会在 `self._cursor` 上产生竞争；给 `__next__` 里的读改写加锁，
  或者预先把地址空间切成若干子区间、每个线程只用自己的一份，都能避免两个调用者拿到同一个地址。

<details>
<summary>验证代码（可运行）</summary>

```python
import itertools
import random
import sys
import ipaddress

# --- Part 1-2: basic behaviour, boundaries, carry/borrow ---
assert list(itertools.islice(IPV4Iterator("192.0.2.254"), 4)) == \
    ["192.0.2.254", "192.0.2.255", "192.0.3.0", "192.0.3.1"]
assert list(IPV4Iterator("255.255.255.255")) == ["255.255.255.255"]
assert list(IPV4Iterator("0.0.0.0", reverse=True)) == ["0.0.0.0"]
rev_it = IPV4Iterator("192.0.2.1", reverse=True)
assert [next(rev_it) for _ in range(4)] == ["192.0.2.1", "192.0.2.0", "192.0.1.255", "192.0.1.254"]
exhausted = IPV4Iterator("255.255.255.255")
next(exhausted)
for _ in range(3):                                    # StopIteration stays raised, it does not un-exhaust
    try:
        next(exhausted)
        raise AssertionError("expected StopIteration")
    except StopIteration:
        pass

# --- Part 3: CIDR block, special prefixes ---
assert network_and_broadcast(ip_to_int("203.0.113.100"), 28) == \
    (ip_to_int("203.0.113.96"), ip_to_int("203.0.113.111"))
fwd = list(IPV4Iterator("203.0.113.100/28"))
assert fwd[0] == "203.0.113.100" and fwd[-1] == "203.0.113.111" and len(fwd) == 12
rev = list(IPV4Iterator("203.0.113.100/28", reverse=True))
assert rev[0] == "203.0.113.100" and rev[-1] == "203.0.113.96" and len(rev) == 5
assert list(IPV4Iterator("198.51.100.77/32")) == ["198.51.100.77"]
assert list(IPV4Iterator("198.51.100.16/31")) == ["198.51.100.16", "198.51.100.17"]
zero_it = IPV4Iterator("10.20.30.40/0")
assert [next(zero_it) for _ in range(3)] == ["10.20.30.40", "10.20.30.41", "10.20.30.42"]

# --- Part 4: step, both examples, and an invalid step ---
assert list(IPV4Iterator("203.0.113.16/28", step=3)) == \
    ["203.0.113.16", "203.0.113.19", "203.0.113.22", "203.0.113.25", "203.0.113.28", "203.0.113.31"]
assert list(IPV4Iterator("203.0.113.30/28", reverse=True, step=4)) == \
    ["203.0.113.30", "203.0.113.26", "203.0.113.22", "203.0.113.18"]
for bad_step in (0, -1, -100):
    try:
        IPV4Iterator("1.2.3.4", step=bad_step)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass

# --- Part 5: next_batch, including size 0 and negative size ---
batch_it = IPV4Iterator("203.0.113.16/28")
assert batch_it.next_batch(5) == \
    ["203.0.113.16", "203.0.113.17", "203.0.113.18", "203.0.113.19", "203.0.113.20"]
rest = batch_it.next_batch(100)
assert len(rest) == 11 and rest[-1] == "203.0.113.31"
assert batch_it.next_batch(5) == [] and batch_it.next_batch(0) == []
assert IPV4Iterator("1.2.3.4").next_batch(0) == []
try:
    IPV4Iterator("1.2.3.4").next_batch(-1)
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# --- illegal input, format / range / leading zero ---
bad_inputs = ["1.2.3", "1.2.3.4.5", "1.2.3.256", "01.2.3.4", "1.2.3.04", "1.2.3.-4", "1.2.3.a", "1..3.4",
              " 1.2.3.4", "1.2.3.4\n", "1.2.3.4/", "1.2.3.4/33", "1.2.3.4/-1", "1.2.3.4/1/2", "1.2.3.4/8\n",
              "198.51.100.0/08", "198.51.100.0/00", "198.51.100.0/255.0.0.0"]
for s in bad_inputs:
    try:
        IPV4Iterator(s)
        raise AssertionError(f"expected ValueError for {s!r}")
    except ValueError:
        pass

# --- stdlib behaviour the oracle below relies on ---
for s in ["01.2.3.4", "1.2.3.04", "1.2.3.00", "1.2.3.4\n"]:   # leading zeros rejected since Python 3.9.5
    try:
        ipaddress.IPv4Address(s)
        raise AssertionError(f"expected ipaddress to reject {s!r}")
    except ValueError:
        pass
# ipaddress takes a leading-zero or netmask-style prefix; IPV4Iterator deliberately does not
assert ipaddress.IPv4Network("198.51.100.0/08", strict=False).prefixlen == 8
assert ipaddress.IPv4Network("198.51.100.0/255.0.0.0", strict=False).prefixlen == 8

# --- memory for a full list of address strings: estimate only, never a real 2**32 loop ---
per_addr = sys.getsizeof("255.255.255.255") + 8          # the string object + the list's pointer to it
assert 2 * 10 ** 11 < (2 ** 32) * per_addr < 10 ** 12     # hundreds of GB

# --- independent oracle: ipaddress parses, masks and formats; nothing from the solution is called ---
MAX_ADDR = 2 ** 32 - 1


def oracle_bounds(s):
    """(start, lo, hi) for a valid input, ValueError otherwise."""
    ip_part, slash, prefix_part = s.partition("/")
    start = int(ipaddress.IPv4Address(ip_part))
    if not slash:
        return start, 0, MAX_ADDR
    if not (prefix_part.isascii() and prefix_part.isdigit()) or prefix_part != str(int(prefix_part)):
        raise ValueError(f"bad prefix {prefix_part!r}")
    net = ipaddress.IPv4Network(f"{ip_part}/{prefix_part}", strict=False)   # rejects a prefix > 32
    return start, int(net.network_address), int(net.broadcast_address)


def oracle_sequence(s, reverse, step, count):
    start, lo, hi = oracle_bounds(s)
    out, cur = [], start
    while len(out) < count and lo <= cur <= hi:
        out.append(str(ipaddress.IPv4Address(cur)))
        cur += -step if reverse else step
    return out


def rejects(make):
    try:
        make()
    except ValueError:
        return True
    return False


rng = random.Random(0)


def rand_addr():
    return str(ipaddress.IPv4Address(rng.getrandbits(32)))


# small blocks (/24 to /32): drain fully and compare address by address
for _ in range(1500):
    seed = f"{rand_addr()}/{rng.randint(24, 32)}"
    reverse, step = rng.random() < 0.5, rng.randint(1, 5)
    assert list(IPV4Iterator(seed, reverse=reverse, step=step)) == \
        oracle_sequence(seed, reverse, step, 10 ** 6), (seed, reverse, step)

# any prefix, or none: a seed within a few steps of the end it walks toward is drained fully, so the
# last address and the stop are checked even for /0 and bare addresses; a random seed checks the start
for _ in range(1500):
    suffix = rng.choice(["", f"/{rng.randint(0, 32)}"])
    reverse, step = rng.random() < 0.5, rng.choice([1, 1, 2, 3, 7, 256])
    _, lo, hi = oracle_bounds(rand_addr() + suffix)
    gap = rng.randint(0, min(20 * step, hi - lo))
    seed = str(ipaddress.IPv4Address(lo + gap if reverse else hi - gap)) + suffix
    assert list(IPV4Iterator(seed, reverse=reverse, step=step)) == \
        oracle_sequence(seed, reverse, step, 10 ** 6), (seed, reverse, step)
    seed = rand_addr() + suffix
    assert list(itertools.islice(IPV4Iterator(seed, reverse=reverse, step=step), 5)) == \
        oracle_sequence(seed, reverse, step, 5), (seed, reverse, step)

# random corruptions of valid inputs: rejected exactly when the oracle rejects them
ALPHABET = "0123456789./ -+x٣\n"
n_rejected = 0
for _ in range(20000):
    chars = list(rand_addr() + rng.choice(["", f"/{rng.randint(0, 32)}"]))
    for _ in range(rng.randint(1, 3)):
        i, op = rng.randrange(len(chars) + 1), rng.randrange(3)
        if op == 0:
            chars.insert(i, rng.choice(ALPHABET))
        elif i < len(chars):
            chars[i:i + 1] = [] if op == 1 else [rng.choice(ALPHABET)]
    s = "".join(chars)
    oracle_rejects = rejects(lambda: oracle_bounds(s))
    assert rejects(lambda: IPV4Iterator(s)) == oracle_rejects, repr(s)
    if oracle_rejects:
        n_rejected += 1
    else:
        assert list(itertools.islice(IPV4Iterator(s), 3)) == oracle_sequence(s, False, 1, 3), repr(s)
assert min(n_rejected, 20000 - n_rejected) > 2000         # both outcomes are well represented
assert rejects(lambda: IPV4Iterator(rand_addr(), step=rng.choice([0, -1, -9])))

# next_batch interleaved with next(), sizes including 0: the combined output equals the oracle's
# sequence, and an exhausted iterator stays exhausted
for _ in range(1000):
    seed = f"{rand_addr()}/{rng.randint(26, 32)}"
    reverse, step = rng.random() < 0.5, rng.randint(1, 4)
    it, got = IPV4Iterator(seed, reverse=reverse, step=step), []
    while True:
        if rng.random() < 0.3:
            try:
                got.append(next(it))
            except StopIteration:
                break
        else:
            size = rng.randint(0, 10)
            batch = it.next_batch(size)
            got += batch
            if len(batch) < size:
                break
    assert got == oracle_sequence(seed, reverse, step, 10 ** 6), (seed, reverse, step)
    assert it.next_batch(0) == [] and it.next_batch(3) == []
    assert rejects(lambda: it.next_batch(-1))

print("all checks passed")
```

</details>

</details>
