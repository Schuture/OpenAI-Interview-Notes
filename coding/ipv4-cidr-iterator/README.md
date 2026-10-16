# IPv4 / CIDR Iterator

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★☆☆ | Medium | SWE | bit-manipulation, iterator, string | 6 parts |
<!-- meta:end -->

## Problem

An IPv4 address is written as four decimal segments separated by dots, `"a.b.c.d"`. Each segment is
between `0` and `255`, and is written without a leading zero unless the segment is exactly `0` — so
`"1.2.3.4"` and `"0.0.0.0"` are valid, `"1.2.03.4"` and `"1.2.00.4"` are not. Such an address
corresponds to the 32-bit integer $a \cdot 2^{24} + b \cdot 2^{16} + c \cdot 2^{8} + d$, and addresses
are ordered, and iterated, by this integer: `0.0.0.0` is the smallest possible address and
`255.255.255.255` is the largest. Implement Parts 1 to 5 as one class, `IPV4Iterator`, where
each part extends the constructor and the iteration behaviour of the one before it; Part 6 asks for the same interface over IPv6 addresses, as a second class, `IPV6Iterator`. If the constructor's
argument `ip_or_cidr` does not split into exactly four such segments, or a segment is not written in the
form above, or a segment's value exceeds `255`, the constructor raises `ValueError`. Every invalid
argument in all six parts raises `ValueError`, so an input that breaks several rules at once may be
rejected by whichever check runs first.

### Part 1 — Forward iteration

`ip_or_cidr` is a bare address (no `/`, that is Part 3's addition). Iterating produces addresses in
increasing numeric order, one per call, starting from (and including) `ip_or_cidr`, up to and including
`255.255.255.255`; after that, further calls raise `StopIteration`. If `ip_or_cidr` is already
`"255.255.255.255"`, exactly that one address is produced.

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

Example, starting from `192.0.2.254`:

```text
call 1: 192.0.2.254
call 2: 192.0.2.255
call 3: 192.0.3.0    # the last segment overflowed 255, carrying into the segment before it
call 4: 192.0.3.1
```

### Part 2 — Reverse iteration

Add `reverse: bool = False`. With `reverse=True`, iterating produces addresses in decreasing numeric
order, starting from (and including) `ip_or_cidr`, down to and including `0.0.0.0`; after that, further
calls raise `StopIteration`. If `ip_or_cidr` is already `"0.0.0.0"`, exactly that one address is
produced.

```py
class IPV4Iterator:
    def __init__(self, ip_or_cidr: str, reverse: bool = False) -> None:
        """reverse=False keeps Part 1's behaviour. reverse=True walks backward from (and
        including) ip_or_cidr, in decreasing numeric order, down to and including 0.0.0.0."""
```

Example, starting from `192.0.2.1` with `reverse=True`:

```text
call 1: 192.0.2.1
call 2: 192.0.2.0
call 3: 192.0.1.255   # borrowed from the segment before it
call 4: 192.0.1.254
```

### Part 3 — Confined to a CIDR block

`ip_or_cidr` may now be `"a.b.c.d/prefix"`, a *CIDR block*: `prefix` is an integer from `0` to `32`,
written with the same no-leading-zero rule as a segment; if it is not written in this form, or its
value is outside `0`-`32`, the constructor raises `ValueError`. Given the address's 32-bit integer and
`prefix`, the block's *network address* is that integer with its low `32 - prefix` bits cleared, and its
*broadcast address* is the network address with those same low bits set; the block is every address
from the network address to the broadcast address, inclusive of both. The network address need not be `ip_or_cidr` itself — since it is computed
by masking `ip_or_cidr`, the given address always lies inside the resulting block. Iteration is confined
to the block: forward stops after the broadcast address (inclusive), reverse stops after the network
address (inclusive), and iteration still starts at `ip_or_cidr` itself, which need not be either end. A
`/32` block holds exactly one address (`ip_or_cidr` itself, which is then both ends). A `/0` block is the
entire address space, `0.0.0.0` through `255.255.255.255`, but iteration still starts at `ip_or_cidr`.

Example, block `203.0.113.96`–`203.0.113.111` (`203.0.113.96/28`), starting from `203.0.113.100`:

```text
forward: 203.0.113.100, 203.0.113.101, ..., 203.0.113.111   (12 addresses, ends at the broadcast address)
reverse: 203.0.113.100, 203.0.113.99, ..., 203.0.113.96      (5 addresses, ends at the network address)
```

Special prefixes: `IPV4Iterator("198.51.100.77/32")` produces only `"198.51.100.77"`.
`IPV4Iterator("198.51.100.16/31")` produces `"198.51.100.16"` then `"198.51.100.17"`.
`IPV4Iterator("10.20.30.40/0")` starts at `"10.20.30.40"` and, forward, does not stop until
`"255.255.255.255"`.

### Part 4 — Step size

Add `step: int = 1`. `step` must be a positive integer; `step <= 0` raises `ValueError`. Each call to
`__next__` moves the current position `step` addresses in the direction `reverse` selects; the first
address produced is still `ip_or_cidr` itself, unaffected by `step`. Iteration stops as soon as the
*next* address to produce would fall outside the allowed range (`0.0.0.0`–`255.255.255.255`, or the CIDR
block from Part 3) — a `step` greater than `1` can jump past that boundary without ever landing on it
exactly, and no address beyond it is ever produced.

```py
class IPV4Iterator:
    def __init__(self, ip_or_cidr: str, reverse: bool = False, step: int = 1) -> None:
        """step is the number of addresses __next__ advances by on each call, in the direction
        reverse selects. Raises ValueError if step <= 0."""
```

Example, block `203.0.113.16/28` (network `203.0.113.16`, broadcast `203.0.113.31`), `step=3`:

```text
203.0.113.16, 203.0.113.19, 203.0.113.22, 203.0.113.25, 203.0.113.28, 203.0.113.31
# the next candidate would be 203.0.113.34, past the broadcast address -> StopIteration
```

Same block, starting from `203.0.113.30` with `reverse=True, step=4`:

```text
203.0.113.30, 203.0.113.26, 203.0.113.22, 203.0.113.18
# the next candidate would be 203.0.113.14, below the network address 203.0.113.16 -> StopIteration
```

`IPV4Iterator("203.0.113.16/28", step=0)` raises `ValueError`.

### Part 5 — Batch reads

Add `next_batch(size: int) -> list[str]`. It returns up to `size` addresses starting at the current
position, equivalent to `size` consecutive `__next__` calls collected into a list, except that it never
raises `StopIteration` itself: once the iterator would be exhausted it simply returns fewer than `size`
addresses, and an empty list once no addresses remain at all. `size` must be a non-negative integer;
`size < 0` raises `ValueError`. `size == 0` always returns `[]` without raising and without moving the
current position, regardless of whether the iterator is exhausted.

```py
class IPV4Iterator:
    def next_batch(self, size: int) -> list[str]:
        """Returns up to size addresses from the current position, in the same order __next__
        would produce them. Returns fewer than size once fewer remain, [] once none remain.
        Raises ValueError if size < 0."""
```

Example, block `203.0.113.16/28` (16 addresses, `203.0.113.16`–`203.0.113.31`):

```text
it = IPV4Iterator("203.0.113.16/28")
it.next_batch(5)    -> ["203.0.113.16", "203.0.113.17", "203.0.113.18", "203.0.113.19", "203.0.113.20"]
it.next_batch(100)  -> the remaining 11 addresses, ending with "203.0.113.31"
it.next_batch(5)    -> []
```

### Part 6 — IPv6

An IPv6 address is a 128-bit integer, written as eight *groups* of 16 bits separated by colons. A group is
written as 1 to 4 hexadecimal digits (`0`-`9`, `a`-`f`, `A`-`F`; the case is not significant and leading
zeros are allowed), so `2001:0DB8:0:0:0:0:0:1` is an address. The leftmost group holds the most significant
16 bits, addresses are ordered, and iterated, by their integer value, `::` (all zero) is the smallest address
and `ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff` is the largest.

An address may be written in *compressed* form: the sign `::` stands for one or more consecutive groups that
are all `0`, as many as are needed to make eight groups in total. `::` may appear at most once, and at either
end or in the middle (`::1`, `1::`, `1::2`, and `::` alone). Because it replaces at least one group, at most
seven groups are written around it. Without `::` exactly eight groups are written. Anything else is invalid:
dotted IPv4 notation, a zone id such as `%eth0`, square brackets, a sign, whitespace, a group of more than
four digits, an empty group (as in `:1::2`, `1::2:` or `:::`), more than one `::`, and a `::` next to eight
written groups.

Every address the iterator produces is written in *canonical* form (RFC 5952): lowercase hexadecimal, no leading
zeros in a group (a zero group is `0`), and the single longest run of two or more consecutive zero groups
replaced by `::`; if several runs have the same longest length, the leftmost is replaced. A single zero group
is never replaced.

```text
2001:0db8:0000:0000:0001:0000:0000:0001  ->  2001:db8::1:0:0:1    # two runs of length 2: the leftmost
2001:db8:0:0:1:0:0:0                     ->  2001:db8:0:0:1::     # the run of length 3 is longer
2001:db8:0:1:0:1:1:1                     ->  2001:db8:0:1:0:1:1:1 # a lone zero group is kept as 0
0:0:0:0:0:0:0:0 -> ::      0:0:0:0:0:0:0:1 -> ::1      1:0:0:0:0:0:0:0 -> 1::
```

`IPV6Iterator` has the interface and behaviour of Parts 1 to 5 with 128 in place of 32: `ip_or_cidr` is an
address or `"address/prefix"` with `prefix` an integer from `0` to `128` written without a leading zero; the
network address and broadcast address are obtained by clearing, respectively setting, the low `128 - prefix`
bits; `reverse`, `step` and `next_batch(size)` are as before, ending at `ffff:...:ffff` or `::` when no
block is given. The first address produced is `ip_or_cidr` itself, in canonical form whatever way it was
written. An argument that is not of this form raises `ValueError`, as does `step <= 0` or `size < 0`.

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

Example, starting from `2001:DB8:0:0:0:0:0:FFFE`:

```text
call 1: 2001:db8::fffe    # the input, in canonical form
call 2: 2001:db8::ffff
call 3: 2001:db8::1:0     # the last group overflowed, carrying into the group before it; the zero run is now shorter
call 4: 2001:db8::1:1
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two points worth confirming with the interviewer: whether malformed input should raise in the
constructor right away (assumed here) rather than lazily on the first `__next__`; and whether a CIDR
seed must already be the network address, rather than any address inside the block as here — the
standard library's own `ipaddress.IPv4Network(s, strict=False)` makes the same "loose" choice. For IPv6, whether a dotted IPv4 tail or a zone id
should be accepted (rejected here).

### Part 1

Treat every address as one 32-bit integer, most significant segment first, and format it back by
pulling out four bytes with shifts of 24, 16, 8 and 0. Once addresses are integers, "increasing numeric
order" is just `+= 1`, and a segment carrying past 255 falls out of the addition for free — no manual
per-segment carry logic is needed. Per-call state is a couple of integers, so `__next__` does $O(1)$ work
and the object uses $O(1)$ memory regardless of how far the walk has to go; that matters because the walk
can be long. Starting from `0.0.0.0`, a full forward walk covers $2^{32} = 4{,}294{,}967{,}296$
addresses, and building them all as a list of strings up front does not fit in memory: each string is a
separate object of about 60 bytes (`sys.getsizeof("255.255.255.255")` is 64 on CPython 3.11), and the
list holds an 8-byte pointer to each, so the whole space needs on the order of 300 GB.

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

`reverse` only changes the sign of the per-call step; `__next__` compares the cursor against both ends of
the range, which stops either direction, so both directions share one `__next__`.

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

The low `32 - prefix` bits of the mask are `0` and the rest are `1`; clearing those bits in the address
gives the network address, and setting them gives the broadcast address. `prefix == 0` means shifting by
the full 32 bits. In Python that is harmless: `0xFFFFFFFF << 32` is just a wider integer whose low 32 bits
are all `0`, so `start & mask` is already `0`, and the `& 0xFFFFFFFF` only keeps the mask itself 32 bits
wide. In C or Java, shifting a 32-bit integer by 32 is undefined or leaves it unchanged, and the `/0`
block would come out wrong. `__next__` from Part 2 does not change at all: it already only ever looks at
`self._lo`/`self._hi`, and those now come from the block instead of the whole address space.

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

`step` only changes the size of the per-call jump; the bound check stays a plain comparison, since a
jump that lands past `self._lo`/`self._hi` is caught the same way a jump of `1` would be, just possibly
skipping over the exact boundary address instead of landing on it.

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

`next_batch` is a bounded drain of `__next__`, so it inherits every stopping rule above for free instead
of re-deriving them.

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

A caller that stops draining once `len(batch) < size` must use `size > 0`: with `size == 0` the test is
`0 < 0`, never true, and the loop never ends even though nothing is produced.

| Method | Time per call | Extra memory |
| --- | --- | --- |
| `__init__` | $O(1)$ | $O(1)$ |
| `__next__` | $O(1)$ | $O(1)$ |
| `next_batch(size)` | $O(k)$, $k$ = addresses returned | $O(k)$ |

### Part 6

Only the width and the text form change. An address is still one integer, the cursor is still an integer,
and `_lo`/`_hi` still bound the walk, so Parts 2 to 5 carry over with `32` replaced by `128`. A 128-bit
value needs no special treatment in Python, whose ints have arbitrary precision; in a language with
fixed-width integers the cursor becomes two 64-bit words, an increment is an add with carry out of the low
word, and the bound check compares the high words first. `next_batch` only calls `next(self)`, so
`IPV6Iterator` borrows Part 5's function unchanged.

Parsing splits on `::` first. With no `::` the text must have exactly eight groups; with one, the two sides
are parsed on their own (either may be empty) and the zero groups between them are whatever is missing from
eight, which must be at least one. Each group is checked against `[0-9A-Fa-f]{1,4}`, which on its own rules
out signs, spaces, `%`, `.` and over-long groups, and an empty piece between colons.

Formatting scans the eight groups for maximal runs of zeros, remembers the first run of the greatest length,
and writes `::` in its place when that length is at least 2. Replacing `>` by `>=` in the scan would move
the compression to the rightmost run on a tie, which is what RFC 5952 forbids.

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

Parsing and formatting look at eight groups, so both are $O(1)$, and `__next__` is $O(1)$ time and memory as
for IPv4. Walking a whole IPv6 block is a different matter: a `/64` holds $2^{64}$ addresses, so a caller
must bound the walk with `next_batch` or `islice`.

### Follow-ups

- Accepting an embedded IPv4 tail, as in `::ffff:192.0.2.1`, means parsing the last 32 bits with the IPv4
  rules above; the tail counts as two groups toward the eight.
- One class for both families can dispatch on whether the address part contains `:`, with the width and the
  parser/formatter pair stored on the instance.
- To walk a CIDR block while excluding some sub-blocks, skip forward past an excluded sub-block's
  broadcast (or back past its network address) instead of advancing by one address at a time.
- Iterating the union of several CIDR blocks needs the blocks merged into disjoint, sorted ranges first,
  so that overlaps are not produced twice.
- Concurrent callers of one `IPV4Iterator` race on `self._cursor`; a lock around the read-modify-write in
  `__next__`, or handing each thread its own pre-computed sub-range, avoids two callers getting the same
  address.

<details>
<summary>Checks (runnable)</summary>

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
