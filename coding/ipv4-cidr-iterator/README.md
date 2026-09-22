# IPv4 / CIDR Iterator

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★☆☆ | Medium | SWE | bit-manipulation, iterator, string | 5 parts |
<!-- meta:end -->

## Problem

An IPv4 address is written as four decimal segments separated by dots, `"a.b.c.d"`. Each segment is
between `0` and `255`, and is written without a leading zero unless the segment is exactly `0` — so
`"1.2.3.4"` and `"0.0.0.0"` are valid, `"1.2.03.4"` and `"1.2.00.4"` are not. Such an address
corresponds to the 32-bit integer $a \cdot 2^{24} + b \cdot 2^{16} + c \cdot 2^{8} + d$, and addresses
are ordered, and iterated, by this integer: `0.0.0.0` is the smallest possible address and
`255.255.255.255` is the largest. Implement the following five parts as one class, `IPV4Iterator`, where
each part extends the constructor and the iteration behaviour of the one before it. If the constructor's
argument `ip_or_cidr` does not split into exactly four such segments, or a segment is not written in the
form above, or a segment's value exceeds `255`, the constructor raises `ValueError`. Every invalid
argument in all five parts raises `ValueError`, so an input that breaks several rules at once may be
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

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two points worth confirming with the interviewer: whether malformed input should raise in the
constructor right away (assumed here) rather than lazily on the first `__next__`; and whether a CIDR
seed must already be the network address, rather than any address inside the block as here — the
standard library's own `ipaddress.IPv4Network(s, strict=False)` makes the same "loose" choice.

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

### Follow-ups

- IPv6 addresses are 128-bit; the same masking idea works unchanged with Python's arbitrary-width ints,
  replacing every `32`/`0xFFFFFFFF` above with `128`/`(1 << 128) - 1`.
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

print("all checks passed")
```

</details>

</details>
