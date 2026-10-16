# IPv4 / CIDR 迭代器

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★☆☆ | 中等 | SWE | bit-manipulation, iterator, string | 6 个部分 |
<!-- meta:end -->

## 题目

IPv4 地址写成用点分隔的四个十进制段，`"a.b.c.d"`。每一段在 `0` 到 `255` 之间，且不带前导零，除非这一段本身就是
`0`——所以 `"1.2.3.4"`、`"0.0.0.0"` 合法，`"1.2.03.4"`、`"1.2.00.4"` 不合法。这样一个地址对应 32 位整数
$a \cdot 2^{24} + b \cdot 2^{16} + c \cdot 2^{8} + d$，地址的大小顺序、以及迭代的顺序，都按这个整数来：
`0.0.0.0` 是最小的地址，`255.255.255.255` 是最大的地址。用一个类 `IPV4Iterator` 实现 Part 1 到 Part 5，
每一部分都在前一部分的构造函数和迭代行为上做扩展；Part 6 要求在 IPv6 地址上提供同样的接口，用第二个类 `IPV6Iterator` 实现。如果构造函数的参数 `ip_or_cidr` 不能正好拆成四段这样的记法，
或者某一段不是上述形式，或者某一段的数值超过 `255`，构造函数就抛出 `ValueError`。六个部分里的非法参数一律抛出
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

### Part 6 —— IPv6

IPv6 地址是一个 128 位整数，写成用冒号分隔的八个 16 位*组*（group）。每一组写成 1 到 4 位十六进制数字
（`0`-`9`、`a`-`f`、`A`-`F`；不区分大小写，允许前导零），所以 `2001:0DB8:0:0:0:0:0:1` 是一个地址。最左边的一组是最高的
16 位，地址的大小顺序、以及迭代的顺序，都按整数值来：`::`（全零）是最小的地址，
`ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff` 是最大的地址。

地址可以写成*压缩*（compressed）形式：符号 `::` 代表一个或多个连续的、值全为 `0` 的组，个数恰好补足到总共八组。
`::` 至多出现一次，可以在两端或中间（`::1`、`1::`、`1::2`，以及单独的 `::`）。因为它至少代替一组，
它周围最多写出七组。没有 `::` 时必须正好写出八组。其余写法都不合法：点分十进制 IPv4 写法、
形如 `%eth0` 的区域标识（zone id）、方括号、正负号、空白、超过四位的组、空组（如 `:1::2`、`1::2:`、`:::`）、
出现不止一次的 `::`，以及 `::` 旁边已经写满八组。

迭代器产生的每个地址都写成*规范*（canonical）形式（RFC 5952）：十六进制小写，每组不带前导零（零组写成 `0`），
并把最长的、由两个或更多连续零组构成的那一段换成 `::`；如果有几段并列最长，换最左边的一段。单独一个零组永远不被替换。

```text
2001:0db8:0000:0000:0001:0000:0000:0001  ->  2001:db8::1:0:0:1    # 两段长度都是 2：取最左边的
2001:db8:0:0:1:0:0:0                     ->  2001:db8:0:0:1::     # 长度为 3 的一段更长
2001:db8:0:1:0:1:1:1                     ->  2001:db8:0:1:0:1:1:1 # 单独的零组保持写成 0
0:0:0:0:0:0:0:0 -> ::      0:0:0:0:0:0:0:1 -> ::1      1:0:0:0:0:0:0:0 -> 1::
```

`IPV6Iterator` 的接口和行为与 Part 1 到 Part 5 相同，只是把 32 换成 128：`ip_or_cidr` 是一个地址或 `"地址/prefix"`，
`prefix` 是 `0` 到 `128` 之间不带前导零的整数；网络地址和广播地址分别由把低 `128 - prefix` 位清零、置一得到；
`reverse`、`step` 和 `next_batch(size)` 同前，没有给出块时终点是 `ffff:...:ffff` 或 `::`。第一个产生的地址是 `ip_or_cidr`
本身，无论输入怎么写，都输出规范形式。参数不是这种形式时抛出 `ValueError`，`step <= 0` 或 `size < 0` 同样如此。

```py
class IPV6Iterator:
    def __init__(self, ip_or_cidr: str, reverse: bool = False, step: int = 1) -> None:
        """ip_or_cidr is an IPv6 address or "address/prefix", in any spelling allowed above.
        Raises ValueError if it is invalid or if step <= 0."""

    def __iter__(self) -> "IPV6Iterator": ...

    def __next__(self) -> str:
        """Returns the next address in canonical form; StopIteration once the block (or the address
        space) is left."""

    def next_batch(self, size: int) -> list[str]:
        """As in Part 5."""
```

例如，从 `2001:DB8:0:0:0:0:0:FFFE` 开始：

```text
call 1: 2001:db8::fffe    # 输入本身，写成规范形式
call 2: 2001:db8::ffff
call 3: 2001:db8::1:0     # 最后一组溢出，向前一组进位；零组连续的一段变短了
call 4: 2001:db8::1:1
```

## 参考解答

<details>
<summary>展开参考解答</summary>

有两点值得向面试官确认：非法输入是应该在构造函数里立刻报错（这里采用这种做法），还是等到第一次调用 `__next__` 时才报错；
CIDR 的种子地址是否必须已经是网络地址，还是像这里一样可以是块内任意地址——标准库的
`ipaddress.IPv4Network(s, strict=False)` 采用的正是同样“宽松”的做法。对 IPv6，还要确认是否接受点分的 IPv4 尾部和区域标识（这里一律拒绝）。

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
| `next_batch(size)` | $O(k)$，$`k`$ 为返回的地址数 | $O(k)$ |

### Part 6

变的只有位宽和文本形式。地址仍然是一个整数，光标仍然是整数，`_lo`/`_hi` 仍然框定遍历范围，所以 Part 2 到 Part 5
把 `32` 换成 `128` 就能沿用。128 位的值在 Python 里不需要任何特殊处理，因为它的 int 是任意精度的；在使用定长整数的语言里，
光标要拆成两个 64 位字，自增是低位字加一并向高位字进位，边界比较先比高位字。`next_batch` 只调用 `next(self)`，
所以 `IPV6Iterator` 直接借用 Part 5 的函数，不用改。

解析先按 `::` 切开。没有 `::` 时文本必须正好是八组；有一个 `::` 时，两侧各自解析（任何一侧都可以为空），
中间的零组个数就是八减去已写出的组数，而且必须至少为一。每一组用 `[0-9A-Fa-f]{1,4}` 检查，仅这一条就排除了
正负号、空格、`%`、`.`、过长的组，以及冒号之间的空片段。

格式化时扫描八个组，找出极大的零组连续段，记住长度最大的第一段，长度至少为 2 时在那里写 `::`。
如果把扫描里的 `>` 改成 `>=`，并列时压缩的就变成最右边那一段，而这正是 RFC 5952 禁止的。

```python
_GROUP_RE = re.compile(r"\A[0-9A-Fa-f]{1,4}\Z")
_PREFIX6_RE = re.compile(r"\A(0|[1-9][0-9]{0,2})\Z")
MAX_IP6 = (1 << 128) - 1   # ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff


def _parse_groups(text):
    # NOTE: "" gives [] -- that is how "::" at either end, or "::" alone, has an empty side. An empty
    # piece after a split, from ":::" or a lone leading/trailing colon, fails the group regex instead
    if text == "":
        return []
    groups = []
    for piece in text.split(":"):
        if not _GROUP_RE.match(piece):
            raise ValueError(f"bad group {piece!r} in {text!r}: 1-4 hex digits expected")
        groups.append(int(piece, 16))
    return groups


def parse_ip6(s):
    if s.count("::") > 1:
        raise ValueError(f"'::' may appear at most once: {s!r}")
    if "::" in s:
        head, tail = s.split("::")      # NOTE: exactly two parts here, either of which may be empty
        left, right = _parse_groups(head), _parse_groups(tail)
        # NOTE: '::' must stand for at least one zero group, so at most 7 groups are written around it;
        # "1:2:3:4:5:6:7:8::" is rejected even though its value would be well defined
        if len(left) + len(right) > 7:
            raise ValueError(f"'::' must replace at least one group: {s!r}")
        groups = left + [0] * (8 - len(left) - len(right)) + right
    else:
        groups = _parse_groups(s)
        if len(groups) != 8:
            raise ValueError(f"expected 8 groups without '::', got {len(groups)}: {s!r}")
    value = 0
    for g in groups:
        value = (value << 16) | g       # NOTE: big-endian -- the leftmost group is the most significant 16 bits
    return value


def int_to_ip6(value):
    groups = [(value >> shift) & 0xFFFF for shift in range(112, -1, -16)]
    best_start, best_len, i = 0, 0, 0
    while i < 8:                         # find the longest run of zero groups
        if groups[i] != 0:
            i += 1
            continue
        j = i
        while j < 8 and groups[j] == 0:
            j += 1
        # NOTE: strict '>' keeps the leftmost run on a tie, as RFC 5952 requires
        if j - i > best_len:
            best_start, best_len = i, j - i
        i = j
    # NOTE: a lone zero group is written "0", never "::" -- only runs of 2 or more are compressed
    if best_len < 2:
        return ":".join(f"{g:x}" for g in groups)
    left = ":".join(f"{g:x}" for g in groups[:best_start])
    right = ":".join(f"{g:x}" for g in groups[best_start + best_len:])
    return left + "::" + right           # NOTE: an empty side gives "::1", "1::" and "::" with no stray colon


def _parse_prefix6(s):
    if not _PREFIX6_RE.match(s):
        raise ValueError(f"bad prefix {s!r}: must be digits with no leading zero")
    value = int(s)
    if value > 128:
        raise ValueError(f"prefix {value} out of range 0-128")
    return value


def block_bounds6(start, prefix):
    low = (1 << (128 - prefix)) - 1      # the host bits; prefix 0 gives all 128 bits, prefix 128 gives none
    network = start & (MAX_IP6 ^ low)
    return network, network | low


class IPV6Iterator:
    def __init__(self, ip_or_cidr, reverse=False, step=1):
        if step <= 0:
            raise ValueError(f"step must be a positive integer, got {step}")
        if ip_or_cidr.count("/") > 1:
            raise ValueError(f"bad CIDR notation: {ip_or_cidr!r}")
        ip_part, slash, prefix_part = ip_or_cidr.partition("/")
        self._cursor = parse_ip6(ip_part)
        if slash:
            self._lo, self._hi = block_bounds6(self._cursor, _parse_prefix6(prefix_part))
        else:
            self._lo, self._hi = 0, MAX_IP6
        self._reverse = reverse
        self._step = step

    def __iter__(self):
        return self

    def __next__(self):
        # NOTE: the cursor is a Python int, so a jump past ffff:...:ffff (or below ::) does not wrap
        # around; a pair of uint64 words would wrap to a small value here and the walk would never stop
        if self._cursor < self._lo or self._cursor > self._hi:
            raise StopIteration
        result = int_to_ip6(self._cursor)
        self._cursor += -self._step if self._reverse else self._step
        return result


IPV6Iterator.next_batch = IPV4Iterator.next_batch   # next_batch only calls next(self), so it is shared as is
```

解析和格式化只看八个组，所以都是 $O(1)$，`__next__` 与 IPv4 一样是 $O(1)$ 时间和内存。但是完整遍历一个 IPv6 块是另一回事：
一个 `/64` 有 $2^{64}$ 个地址，调用方必须用 `next_batch` 或 `islice` 给遍历设上限。

### 追问

- 如果要接受内嵌的 IPv4 尾部，如 `::ffff:192.0.2.1`，就要用上面的 IPv4 规则解析最后 32 位；这个尾部算作八组中的两组。
- 一个类同时支持两种地址族，可以根据地址部分是否含有 `:` 来分派，把位宽和解析/格式化这一对函数存在实例上。
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

# --- Part 6: IPv6, the worked example and the canonical-form rules ---
assert list(itertools.islice(IPV6Iterator("2001:DB8:0:0:0:0:0:FFFE"), 4)) == \
    ["2001:db8::fffe", "2001:db8::ffff", "2001:db8::1:0", "2001:db8::1:1"]
CANON = {
    "2001:0db8:0000:0000:0001:0000:0000:0001": "2001:db8::1:0:0:1",    # tie between two runs: leftmost
    "2001:db8:0:1:1:1:1:1": "2001:db8:0:1:1:1:1:1",
    "2001:db8:0:1:0:1:1:1": "2001:db8:0:1:0:1:1:1",                    # a single zero group stays "0"
    "2001:db8:0:0:1:0:0:0": "2001:db8:0:0:1::",                        # the longer, trailing run wins
    "0:0:0:0:0:0:0:0": "::", "0:0:0:0:0:0:0:1": "::1", "1:0:0:0:0:0:0:0": "1::",
    "ABCD:EF01:0:0:0:0:0:2": "abcd:ef01::2", "1:2:3:4:5:6:7:8": "1:2:3:4:5:6:7:8",
    "0:1:0:0:2:0:0:0": "0:1:0:0:2::", "1:0:0:2:0:0:3:4": "1::2:0:0:3:4",
}
for text, want in CANON.items():
    assert int_to_ip6(parse_ip6(text)) == want, text
    assert next(IPV6Iterator(text)) == want, text
assert parse_ip6("::") == 0 and parse_ip6("::1") == 1 and parse_ip6("1::") == 1 << 112
assert parse_ip6("1:2:3:4:5:6:7::") == 0x0001000200030004000500060007 << 16
assert parse_ip6("::2:3:4:5:6:7:8") == 0x0002000300040005000600070008
assert parse_ip6("a::B") == parse_ip6("A::b") == parse_ip6("000A:0:0:0:0:0:0:000b")
assert list(IPV6Iterator("ffff:ffff:ffff:ffff:ffff:ffff:ffff:fffe")) == \
    ["ffff:ffff:ffff:ffff:ffff:ffff:ffff:fffe", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"]
assert list(IPV6Iterator("::1", reverse=True)) == ["::1", "::"]
assert list(IPV6Iterator("2001:db8::7/128")) == ["2001:db8::7"]
assert list(IPV6Iterator("2001:db8::5/126")) == ["2001:db8::5", "2001:db8::6", "2001:db8::7"]
assert list(IPV6Iterator("2001:db8::5/126", reverse=True)) == ["2001:db8::5", "2001:db8::4"]
assert list(IPV6Iterator("2001:db8::ffff:fff0/124", step=5)) == \
    ["2001:db8::ffff:fff0", "2001:db8::ffff:fff5", "2001:db8::ffff:fffa", "2001:db8::ffff:ffff"]
assert list(IPV6Iterator("2001:db8::ffff:fff0/124", step=6)) == \
    ["2001:db8::ffff:fff0", "2001:db8::ffff:fff6", "2001:db8::ffff:fffc"]
assert block_bounds6(parse_ip6("2001:db8::5"), 0) == (0, MAX_IP6)
assert IPV6Iterator("2001:db8::fff0/124").next_batch(100)[-1] == "2001:db8::ffff"
assert IPV6Iterator("::").next_batch(0) == [] and rejects(lambda: IPV6Iterator("::").next_batch(-1))
assert rejects(lambda: IPV6Iterator("::", step=0))

BAD6 = ["", ":", ":::", "::::", "1::2::3", "1:2:3:4:5:6:7", "1:2:3:4:5:6:7:8:9", "1:2:3:4:5:6:7:8::",
        "::1:2:3:4:5:6:7:8", ":1:2:3:4:5:6:7", "1:2:3:4:5:6:7:", "1::2:", ":1::2", "1:::2", "12345::", "g::",
        "::1.2.3.4", "::ffff:1.2.3.4", "fe80::1%eth0", "[::1]", " ::1", "::1\n", "::1 ", "+1::", "-1::",
        "::/", "::/-1", "::/129", "::/08", "::/00", "::/1/2", "::/8\n", "::/ 8", "::/٣"]
for s in BAD6:
    assert rejects(lambda: IPV6Iterator(s)), repr(s)

# --- Part 6: independent oracle, ipaddress parses, masks and formats; nothing from the solution is called ---
MAX6 = 2 ** 128 - 1


def oracle6_bounds(s):
    ip_part, slash, prefix_part = s.partition("/")
    if "%" in ip_part or "." in ip_part:                # zone ids and embedded IPv4 are out of scope
        raise ValueError(ip_part)
    start = int(ipaddress.IPv6Address(ip_part))
    if not slash:
        return start, 0, MAX6
    if not (prefix_part.isascii() and prefix_part.isdigit()) or prefix_part != str(int(prefix_part)):
        raise ValueError(f"bad prefix {prefix_part!r}")
    net = ipaddress.IPv6Network(f"{ip_part}/{prefix_part}", strict=False)
    return start, int(net.network_address), int(net.broadcast_address)


def oracle6_sequence(s, reverse, step, count):
    start, lo, hi = oracle6_bounds(s)
    out, cur = [], start
    while len(out) < count and lo <= cur <= hi:
        out.append(oracle6_text(cur))
        cur += -step if reverse else step
    return out


def oracle6_text(value):
    addr = ipaddress.IPv6Address(value)
    if addr.ipv4_mapped is None:
        return addr.compressed
    # newer Pythons print ::ffff:0:0/96 with a dotted tail; the canonical form here is all hexadecimal
    return "::ffff:%x:%x" % ((value >> 16) & 0xFFFF, value & 0xFFFF)


def exploded6(value):
    return ":".join(format((value >> shift) & 0xFFFF, "04x") for shift in range(112, -1, -16))


def rand6_value():
    # many zero groups, so that runs, ties and lone zeros all occur often
    groups = [rng.choice([0, 0, 0, 0xFFFF, rng.getrandbits(rng.randint(1, 16))]) for _ in range(8)]
    return int("".join(f"{g:04x}" for g in groups), 16)


def rand6():
    return oracle6_text(rand6_value())


for s in BAD6:                                          # the oracle agrees on every rejected string
    assert rejects(lambda: oracle6_bounds(s)), repr(s)

def padded(g):
    return format(g, "x").zfill(rng.randint(1, 4))      # leading zeros up to four digits, never fewer than needed


# round trip against ipaddress: format, and parse every spelling of the same address
for _ in range(5000):
    value = rand6_value()
    addr = ipaddress.IPv6Address(value)
    assert int_to_ip6(value) == oracle6_text(value), hex(value)
    groups = [(value >> sh) & 0xFFFF for sh in range(112, -1, -16)]
    spellings = [oracle6_text(value), oracle6_text(value).upper(), exploded6(value), exploded6(value).upper(),
                 ":".join(f"{g:x}" for g in groups), ":".join(padded(g) for g in groups)]
    # every '::' placement over a run of zero groups, maximal or not, at either end or in the middle
    for i in range(8):
        for j in range(i + 1, 9):
            if all(g == 0 for g in groups[i:j]):
                spellings.append(":".join(f"{g:x}" for g in groups[:i]) + "::" + ":".join(f"{g:x}" for g in groups[j:]))
    for text in spellings:
        assert parse_ip6(text) == value, (text, hex(value))
        assert next(IPV6Iterator(text)) == oracle6_text(value), text
assert int_to_ip6(0) == "::" and int_to_ip6(MAX6) == "ffff:" * 7 + "ffff"

# small blocks (/120 to /128): drain fully and compare address by address
for _ in range(1500):
    seed = f"{rand6()}/{rng.randint(120, 128)}"
    reverse, step = rng.random() < 0.5, rng.randint(1, 5)
    assert list(IPV6Iterator(seed, reverse=reverse, step=step)) == \
        oracle6_sequence(seed, reverse, step, 10 ** 6), (seed, reverse, step)

# any prefix, or none: a seed within a few steps of the end it walks toward is drained fully (so the stop
# after ffff:...:ffff and after :: is checked, with steps beyond 64 bits too); a random seed checks the start
for _ in range(1500):
    suffix = rng.choice(["", f"/{rng.randint(0, 128)}"])
    reverse, step = rng.random() < 0.5, rng.choice([1, 1, 2, 3, 7, 2 ** 16, 2 ** 64 + 1])
    _, lo, hi = oracle6_bounds(rand6() + suffix)
    gap = rng.randint(0, min(20 * step, hi - lo))
    seed = oracle6_text(lo + gap if reverse else hi - gap) + suffix
    assert list(IPV6Iterator(seed, reverse=reverse, step=step)) == \
        oracle6_sequence(seed, reverse, step, 10 ** 6), (seed, reverse, step)
    seed = rand6() + suffix
    assert list(itertools.islice(IPV6Iterator(seed, reverse=reverse, step=step), 5)) == \
        oracle6_sequence(seed, reverse, step, 5), (seed, reverse, step)

# random corruptions of valid inputs: rejected exactly when the oracle rejects them
ALPHABET6 = "0123456789abcdefABCDEFgx:::./ -+%\n٣"
n_rejected6 = 0
for _ in range(20000):
    base = rng.choice([oracle6_text(rand6_value()), exploded6(rand6_value())])
    chars = list(base + rng.choice(["", f"/{rng.randint(0, 128)}"]))
    for _ in range(rng.randint(1, 3)):
        i, op = rng.randrange(len(chars) + 1), rng.randrange(3)
        if op == 0:
            chars.insert(i, rng.choice(ALPHABET6))
        elif i < len(chars):
            chars[i:i + 1] = [] if op == 1 else [rng.choice(ALPHABET6)]
    s = "".join(chars)
    oracle_rejects = rejects(lambda: oracle6_bounds(s))
    assert rejects(lambda: IPV6Iterator(s)) == oracle_rejects, repr(s)
    if oracle_rejects:
        n_rejected6 += 1
    else:
        assert list(itertools.islice(IPV6Iterator(s), 3)) == oracle6_sequence(s, False, 1, 3), repr(s)
assert min(n_rejected6, 20000 - n_rejected6) > 2000

# next_batch interleaved with next() on IPv6 blocks
for _ in range(500):
    seed = f"{rand6()}/{rng.randint(122, 128)}"
    reverse, step = rng.random() < 0.5, rng.randint(1, 4)
    it, got = IPV6Iterator(seed, reverse=reverse, step=step), []
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
    assert got == oracle6_sequence(seed, reverse, step, 10 ** 6), (seed, reverse, step)
    assert it.next_batch(0) == [] and it.next_batch(3) == []

print("all checks passed")
```

</details>

</details>
