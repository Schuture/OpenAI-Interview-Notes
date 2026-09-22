# 可持久化 KV 存储：自定义序列化

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★☆☆ | 中等 | SWE · Infra Eng | serialization, persistence, parsing, storage, fault-tolerance | 3 个部分 |
<!-- meta:end -->

## 题目

`FileSystem` 在内存里模拟一块磁盘：它保存带名字的字节串，寿命比建在它上面的任何存储对象都长，所以“新进程”就用在同一个 `fs` 上新建的实例来表示。每个 Part 都原样使用它，不做修改。在它之上，*键值存储*（key-value store）让调用者在内存里把字符串键关联到字符串值，并把它们持久化，使新实例能够恢复出完全相同的映射。键和值是任意的 `str`：长度不限，可以是空字符串，可以含任意字符——`:`、`,`、`=` 这类像分隔符的字符、换行符、空字符（null character）、emoji 这类基本多文种平面（Basic Multilingual Plane）之外的字符，都必须原样往返（round-trip）。不能使用 `json`、`pickle` 或其他任何现成的序列化模块；`str.encode`、`bytes.decode`、`int.to_bytes`、`int.from_bytes` 可以使用。

```python
class FileSystem:
    """An in-memory mock file system that stores named byte blobs. Files are independent: writing
    "b" never touches "a". write and delete are atomic: if the process dies, the call has either
    taken full effect or had no effect at all. append is not atomic."""

    def __init__(self, max_file_size: int | None = None):
        self.max_file_size = max_file_size
        self._files: dict[str, bytes] = {}

    def write(self, name: str, data: bytes) -> None:
        """Creates or overwrites the file called name with exactly data. Raises ValueError if
        max_file_size is set and len(data) exceeds it; name is then left exactly as it was before
        this call (unchanged, or still absent)."""
        if self.max_file_size is not None and len(data) > self.max_file_size:
            raise ValueError(f"{name}: {len(data)} bytes exceeds max_file_size={self.max_file_size}")
        self._files[name] = data

    def append(self, name: str, data: bytes) -> None:
        """Adds data to the end of the file called name, creating it if absent; raises ValueError,
        changing nothing, if the file would then exceed max_file_size. NOT atomic: if the process
        dies during this call, the file may be left ending in any prefix of data, and the bytes of
        that prefix may be damaged (zeroed, for instance)."""
        old = self._files.get(name, b"")
        if self.max_file_size is not None and len(old) + len(data) > self.max_file_size:
            raise ValueError(f"{name}: {len(old) + len(data)} bytes exceeds max_file_size={self.max_file_size}")
        self._files[name] = old + data

    def read(self, name: str) -> bytes | None:
        """Returns the current bytes of name, or None if no such file exists."""
        return self._files.get(name)

    def list(self) -> list[str]:
        """Names of every file that currently exists, in arbitrary order."""
        return list(self._files)

    def delete(self, name: str) -> None:
        """Removes name if present; a no-op if it does not exist."""
        self._files.pop(name, None)
```

### Part 1 —— 基本的可持久化存储

实现 `KVStore`。`save()` 把整个内存映射持久化到 `fs`；在同一个 `fs` 上新建一个 `KVStore` 并调用 `load()` 之后，`get` 返回的必须与那次 `save()` 之前 `put` 的内容完全一致。键没有值时 `get` 返回 `None`；`fs` 上从未保存过任何内容时，`load()` 之后存储为空。后一次 `save()` 完全取代前一次：此后 `load()` 还原的只是后一次保存的映射。

```py
class KVStore:
    def __init__(self, fs: FileSystem):
        """fs is the FileSystem this store persists to and restores from."""

    def put(self, key: str, value: str) -> None:
        """Sets key -> value in memory, overwriting any previous value for key."""

    def get(self, key: str) -> str | None:
        """Returns the current value of key, or None if key has no value."""

    def save(self) -> None:
        """Persists the entire in-memory store to fs."""

    def load(self) -> None:
        """Replaces the in-memory store with what fs currently holds."""
```

例如，执行

```py
fs = FileSystem()
store = KVStore(fs)
store.put("time:now", "12:00")
store.put("", "empty key")
store.put("emoji", "🙂\n")
store.save()
```

之后，在同一个 `fs` 上新建的 `KVStore(fs)` 调用 `load()`，对 `"time:now"` 必须返回 `"12:00"`，对 `""` 返回 `"empty key"`，对 `"emoji"` 返回 `"🙂\n"`，对其他任何键都返回 `None`。

### Part 2 —— 有大小上限的文件与被中断的保存

现在 `fs` 是 `FileSystem(max_file_size=...)`，只要 `data` 的长度超过上限，`fs.write` 就抛出异常。`ChunkedKVStore` 的接口和约定与 `KVStore` 相同，此外还要满足：

- 单个键或值本身就比 `max_file_size` 长时，仍然要能原样往返。
- `save()` 返回时，`fs.list()` 里的每个文件都必须是 `load()` 还原刚保存的这份数据时要用到的——更早的保存留下的文件，无论那次保存是完成了还是被中断了，都要清掉。
- `save()` 可能被中断：进程可能在它对 `fs` 的任意一次调用之前或之后崩溃（不会在一次调用的中间崩溃，因为 `write` 和 `delete` 是*原子*（atomic）的）。此后在同一个 `fs` 上新建实例并调用 `load()`，得到的要么完整地是被中断的这次 `save()` 的映射，要么是这次 `save()` 开始之前 `load()` 本来会得到的内容（从未保存过就是空存储）——不能是两次保存的混合，也不能抛出异常。
- `max_file_size` 不小于 64 字节时都必须支持。上限更小时，`save()` 可以改为抛出 `ValueError`，这算作一次被中断的保存。

```py
class ChunkedKVStore:
    def __init__(self, fs: FileSystem):
        """fs is the FileSystem this store persists to and restores from; fs.max_file_size may be set."""

    def put(self, key: str, value: str) -> None:
        """Same contract as KVStore.put."""

    def get(self, key: str) -> str | None:
        """Same contract as KVStore.get."""

    def save(self) -> None:
        """Persists the entire in-memory store to fs, never writing more than fs.max_file_size
        bytes to any single file."""

    def load(self) -> None:
        """Replaces the in-memory store with what fs currently holds."""
```

例如，`max_file_size=64`，键值对多到整个存储有几百字节，`save()` 就必须产生不止一个文件；而在一个全新的 `ChunkedKVStore(fs)` 上调用 `load()`，每一对键值都必须原样返回。

### Part 3 —— 只追加日志与崩溃恢复

`LogKVStore` 没有 `save()`：`put` 和 `delete` 一返回就已经持久化。两者都不能重写已经存下的内容——每次操作只用一次 `fs.append` 把自己记下来，写入的大小只取决于这次操作自己的键和值。新实例通过 `load()` 恢复。这里的 `fs` 是普通的 `FileSystem()`，没有大小上限。

`delete(key)` 删除 `key`：此后 `get(key)` 返回 `None`，在新实例上 `load()` 之后也一样，直到 `key` 再次被 `put`。

进程可能在任何时刻崩溃，包括 `fs.append` 执行到一半的时候；这会在文件末尾留下一段不完整或已损坏的片段。`load()` 必须还原出在这个片段之前已经完整持久化的每一次 `put` 和 `delete` 的效果；它不能抛出异常，也不能采用片段里的任何数据。这样恢复之后再执行的操作，和其他操作一样，必须能在下一次 `load()` 时恢复出来。

`compact()` 让存储的数据不再随着被覆盖、被删除的键的历史一起增长：调用之后，`fs` 上所有文件的总大小只取决于存储里当前的键和值，而 `load()`（无论在这个实例上还是在新实例上）重建出的仍然恰好是这份存储。`compact()` 被中断时不能丢失任何数据。

```py
class LogKVStore:
    def __init__(self, fs: FileSystem):
        """fs is the FileSystem this store appends to and recovers from."""

    def put(self, key: str, value: str) -> None:
        """Durably records key -> value before returning."""

    def delete(self, key: str) -> None:
        """Durably records the removal of key before returning."""

    def get(self, key: str) -> str | None:
        """Same contract as KVStore.get."""

    def load(self) -> None:
        """Rebuilds the in-memory store from what fs currently holds."""

    def compact(self) -> None:
        """Rewrites what is stored so that its size no longer depends on the history of overwritten
        or deleted keys; a subsequent load() reconstructs the same in-memory store."""
```

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得先确认：`fs` 的哪些调用是原子的，这决定了崩溃之后会留下什么；以及 `get` 遇到不存在的键是返回 `None` 而不是抛异常。

### Part 1

像 `key + ":" + value + "\n"` 这样用分隔符拼接的格式，键或值里一旦含有分隔符就有歧义。转义在原理上能解决，但转义字符自身在每一处出现时也都要转义，很容易写出隐蔽的错误。*长度前缀*（length-prefixed）编码从根本上避开了这个问题：每个字符串前面先写它占多少字节，读取时不需要在数据里寻找分隔符，也就没有哪种字节序列是不允许出现的。下面的实现在每个字符串前放一个定长 8 字节、大端序的长度。

```python
def _encode_str(s):
    raw = s.encode("utf-8", "surrogatepass")  # a str may hold a lone surrogate such as "\ud800"
    return len(raw).to_bytes(8, "big") + raw  # NOTE: the length counts BYTES; len(s) would count code points


def _read_str(data, pos):
    length = int.from_bytes(data[pos:pos + 8], "big")
    raw = data[pos + 8:pos + 8 + length]
    return raw.decode("utf-8", "surrogatepass"), pos + 8 + length


def _serialize_store(data):
    return b"".join(_encode_str(k) + _encode_str(v) for k, v in data.items())


def _deserialize_store(blob):
    store, pos = {}, 0
    while pos < len(blob):
        key, pos = _read_str(blob, pos)
        value, pos = _read_str(blob, pos)
        store[key] = value
    return store


class KVStore:
    FILE_NAME = "store"

    def __init__(self, fs):
        self.fs = fs
        self._data = {}

    def put(self, key, value):
        self._data[key] = value

    def get(self, key):
        return self._data.get(key)

    def save(self):
        self.fs.write(self.FILE_NAME, _serialize_store(self._data))  # NOTE: one write replaces the whole file

    def load(self):
        blob = self.fs.read(self.FILE_NAME)
        self._data = _deserialize_store(blob) if blob is not None else {}
```

### Part 2

Part 1 序列化出的字节串与文件无关，满足上限最简单的办法就是保持这一点：先序列化，再按固定偏移切片。比 `max_file_size` 还长的键或值不需要特殊处理，因为切片时根本不看记录的边界；`load()` 把各段拼起来，交给 Part 1 的 `_deserialize_store`。

需要小心的是被中断的 `save()`。如果每次保存都原地覆盖 `chunk_0`、`chunk_1`……，写到一半崩溃就会留下新旧混杂的分片，`load()` 会拼出一个从未存在过的存储。所以分片的文件名里带一个*代*（generation）号，再用一个很小的*清单*（manifest）文件记录当前是哪一代、有几个分片。`save()` 从清单读出当前的代号 $g$，把全部分片写在 $g + 1$ 名下，然后写清单，最后才删除旧文件。对 `fs` 的每次调用都是原子的，崩溃只会落在两次调用之间，因此只有两种情形。清单写入之前：清单仍指向第 $g$ 代，这一代的文件这次保存没有碰过，`load()` 得到上一次保存的内容。清单写入之后：新清单提到的分片都已就位，`load()` 得到新的内容，删除进行到哪一步都不影响。写清单的那一次调用就是提交点。

被中断的保存会留下不属于任何清单的分片文件，而下一次保存用的还是同一个代号 $g + 1$。这不会误导 `load()`，因为一次保存在提交之前会把清单将要提到的每个分片重新写一遍；但下标更大的残留文件会永远留下，崩溃发生在删除阶段时没删完的第 $g$ 代分片也一样。所以清理时删除的是新一代之外的全部分片文件，而不只是第 $g$ 代的。

清单里还存了字节串的长度和 CRC-32。崩溃不会让它们与分片对不上；它们防的是分片被别的东西删掉或改动，这时 `load()` 抛出 `CorruptStoreError`，而不是悄悄返回一个错误的存储。清单是四个 8 字节整数，共 32 字节：`max_file_size` 小于 32 时写清单会抛出 `ValueError`，`save()` 让它原样传出。这发生在提交点之前，所以 `load()` 得到的仍是上一次保存的内容。

```python
import zlib


class CorruptStoreError(RuntimeError):
    pass


def _encode_manifest(*fields):  # generation, num_chunks, total_length, checksum
    return b"".join(field.to_bytes(8, "big") for field in fields)


def _decode_manifest(data):
    return [int.from_bytes(data[i:i + 8], "big") for i in range(0, 32, 8)]


class ChunkedKVStore(KVStore):
    MANIFEST = "manifest"

    def save(self):
        old = self.fs.read(self.MANIFEST)
        generation = _decode_manifest(old)[0] + 1 if old is not None else 0  # NOTE: never the live generation

        blob = _serialize_store(self._data)
        cap = self.fs.max_file_size or len(blob)  # no cap: a single chunk
        chunks = [blob[i:i + cap] for i in range(0, len(blob), cap)] if blob else []
        names = [f"chunk_{generation}_{i}" for i in range(len(chunks))]
        for name, chunk in zip(names, chunks):  # NOTE: a cut may fall inside a length header or a character;
            self.fs.write(name, chunk)          # load() re-joins the chunks before parsing
        # NOTE: the commit point -- one atomic write switches load() to the new generation
        self.fs.write(self.MANIFEST, _encode_manifest(generation, len(chunks), len(blob), zlib.crc32(blob)))

        keep = set(names)
        for name in self.fs.list():  # NOTE: not only the previous generation -- interrupted saves leave others
            if name.startswith("chunk_") and name not in keep:
                self.fs.delete(name)

    def load(self):
        manifest = self.fs.read(self.MANIFEST)
        if manifest is None:
            self._data = {}
            return
        generation, num_chunks, total_length, checksum = _decode_manifest(manifest)
        blob = b"".join(self.fs.read(f"chunk_{generation}_{i}") or b"" for i in range(num_chunks))
        if len(blob) != total_length or zlib.crc32(blob) != checksum:
            raise CorruptStoreError("chunk contents do not match the manifest")
        self._data = _deserialize_store(blob)
```

### Part 3

每次 `put` 或 `delete` 向同一个日志文件追加一条*记录*（record），`load()` 按顺序重放这些记录。删除是一种单独的记录类型（*墓碑*，tombstone），而不是写入空值，因为 `put(key, "")` 是合法的、含义不同的操作。

写到一半的追加会在日志末尾留下一段坏数据，记录的布局——长度、校验和、内容——要能把它暴露出来。坏数据太短，比较记录声称的长度与实际剩余的字节数就能发现；长度字段被破坏成一个巨大的数，同样过不了这一比较。够长但内容不对，由 CRC-32 发现。校验和连长度字段一起覆盖：否则末尾的 12 个零字节（崩溃后很常见）会通过两项检查，被当成一条长度为 0 的记录（`crc32(b"") == 0`），接着在解析空内容时抛出异常。重放在第一条坏记录处停止，因为它之后的内容无法可靠定位。随后 `load()` 把这段坏数据截掉；否则之后的记录会追加在它后面，任何一次 `load()` 都读不到。

`compact()` 为每个现存的键写一条 put 记录；墓碑不再需要，因为新日志里没有需要它们去抵消的旧记录。`fs.write` 是原子的，所以 `compact()` 被中断时旧日志原样保留。

```python
PUT, DELETE = 1, 0


def _encode_record(op, key, value=""):
    payload = bytes([op]) + _encode_str(key) + (_encode_str(value) if op == PUT else b"")
    header = len(payload).to_bytes(8, "big")
    return header + zlib.crc32(header + payload).to_bytes(4, "big") + payload  # NOTE: the checksum covers the length


def _read_record(data, pos):
    """Returns (op, key, value, end), or None if no complete, checksum-valid record starts at pos."""
    if pos + 12 > len(data):
        return None  # NOTE: not even a full header remains
    length = int.from_bytes(data[pos:pos + 8], "big")
    end = pos + 12 + length
    if end > len(data):
        return None  # NOTE: cut off mid-record, or a damaged (huge) length
    payload = data[pos + 12:end]
    if zlib.crc32(data[pos:pos + 8] + payload) != int.from_bytes(data[pos + 8:pos + 12], "big"):
        return None  # NOTE: enough bytes, but not the ones that were written
    op = payload[0]
    key, kpos = _read_str(payload, 1)
    value = _read_str(payload, kpos)[0] if op == PUT else ""
    return op, key, value, end


class LogKVStore(KVStore):
    LOG = "log"

    def put(self, key, value):
        self.fs.append(self.LOG, _encode_record(PUT, key, value))  # NOTE: log first, memory second
        super().put(key, value)

    def delete(self, key):
        self.fs.append(self.LOG, _encode_record(DELETE, key))
        self._data.pop(key, None)

    def load(self):
        data = self.fs.read(self.LOG) or b""
        store, pos = {}, 0
        while (record := _read_record(data, pos)) is not None:  # NOTE: stop at the first bad record, for good
            op, key, value, pos = record
            if op == PUT:
                store[key] = value
            else:
                store.pop(key, None)
        if pos < len(data):  # NOTE: cut the bad tail off, or later appends land behind it and are never replayed
            self.fs.write(self.LOG, data[:pos])
        self._data = store

    def compact(self):
        self.fs.write(self.LOG, b"".join(_encode_record(PUT, k, v) for k, v in self._data.items()))
```

### 追问

- 真实的文件系统上，原地覆盖一个文件不是原子的。与这里的 `fs.write` 等价的做法是先写临时文件、`fsync`，再 `rename` 覆盖旧文件名；追加也要在 `fsync` 之后才算持久。
- 变长整数（varint，每字节存 7 位）能把短字符串的长度开销从 8 字节降到 1 字节，代价是解码要写循环，而不是一次切片。
- Bitcask 在内存里只保留从键到文件偏移量的索引，值在需要时才从日志里读，因此全部的值不必放得进内存。

<details>
<summary>验证代码（可运行）</summary>

```python
import random

# --- Part 1: round-trip with adversarial strings ---
WEIRD = ["", "a", "a:b", "a,b", "a=b", "key\nwith\nnewlines", "\x00null\x00byte", "\x00" * 12,
         "emoji \U0001F600 \U0001F4A9", "long" * 5000, "mixed 中文 and English", ":,=\n\x00", "\ud800"]

rng = random.Random(0)
for _ in range(300):
    n = rng.randint(0, len(WEIRD))
    pairs = {k: rng.choice(WEIRD) for k in rng.sample(WEIRD, k=n)}
    fs = FileSystem()
    writer = KVStore(fs)
    for k, v in pairs.items():
        writer.put(k, v)
    writer.save()
    reader = KVStore(fs)
    reader.load()
    assert reader._data == pairs
    assert reader.get("definitely-not-a-key") is None

assert _encode_str("\U0001F600")[:8] == (4).to_bytes(8, "big")     # one code point, four bytes

fs_empty = FileSystem()
assert KVStore(fs_empty).get("x") is None      # nothing put yet
fresh = KVStore(fs_empty)
fresh.put("unsaved", "1")
fresh.load()                                    # nothing ever saved: load() leaves the store empty
assert fresh._data == {}
writer = KVStore(fs_empty)
writer.put("a", "1")
writer.put("b", "2")
writer.save()
other = KVStore(fs_empty)
other.put("a", "3")
other.save()                                    # a later save fully replaces the earlier one
reader = KVStore(fs_empty)
reader.load()
assert reader._data == {"a": "3"}

# a naive delimiter scheme really does fail once a key contains the delimiter
naive_serialize = lambda data: "".join(f"{k}:{v}\n" for k, v in data.items())
def naive_deserialize(text):
    return {line.split(":", 1)[0]: line.split(":", 1)[1] for line in text.splitlines()}
original = {"time:now": "value"}
assert naive_deserialize(naive_serialize(original)) != original

# --- Part 2: round-trip across a range of caps, including the smallest that can work and no cap ---
def saved(fs):
    reader = ChunkedKVStore(fs)
    reader.load()                                # must never raise after a crash
    return reader._data


def needed_files(fs):
    generation, num_chunks, _, _ = _decode_manifest(fs.read("manifest"))
    return {"manifest"} | {f"chunk_{generation}_{i}" for i in range(num_chunks)}


MANIFEST_SIZE = len(_encode_manifest(0, 0, 0, 0))
assert MANIFEST_SIZE == 32
for cap in [MANIFEST_SIZE, MANIFEST_SIZE + 5, 40, 64, 100, 1024, 10_000, None]:
    fs = FileSystem(max_file_size=cap)
    writer = ChunkedKVStore(fs)
    pairs = {}
    for i in range(30):
        k = f"key_{i}_" + "x" * rng.randint(0, 200)
        pairs[k] = rng.choice(WEIRD) if i % 3 == 0 else "y" * rng.randint(0, 300)
        writer.put(k, pairs[k])
    writer.save()
    assert cap is None or all(len(fs.read(name)) <= cap for name in fs.list())
    size = len(_serialize_store(pairs))
    assert len(fs.list()) == 1 + (1 if cap is None else -(-size // cap))      # the manifest plus ceil(size / cap) chunks
    assert saved(fs) == pairs and set(fs.list()) == needed_files(fs)

# a chunk boundary (byte 64) inside the value's length header, which occupies bytes [8 + key_len, 16 + key_len),
# or inside one of the 4-byte characters that follow it
assert 8 + 52 < 64 < 16 + 52 and 16 + 42 + 4 < 64 < 16 + 42 + 8
for key_len in range(30, 60):
    fs = FileSystem(max_file_size=64)
    writer = ChunkedKVStore(fs)
    writer.put("k" * key_len, "\U0001F600" * 3)
    writer.save()
    assert saved(fs) == {"k" * key_len: "\U0001F600" * 3}

for cap in range(MANIFEST_SIZE):                 # too small for the manifest: ValueError, nothing committed
    too_small = FileSystem(max_file_size=cap)
    writer = ChunkedKVStore(too_small)
    writer.put("a", "b")
    try:
        writer.save()
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    assert saved(too_small) == {}


class Crash(Exception):
    pass


class CrashingFileSystem(FileSystem):
    """The process dies (Crash) just before its mutating call number crash_at, counted from 0."""

    def __init__(self, max_file_size=None):
        super().__init__(max_file_size)
        self.calls, self.crash_at = 0, None

    def _tick(self):
        if self.calls == self.crash_at:
            raise Crash
        self.calls += 1

    def write(self, name, data):
        self._tick()
        super().write(name, data)

    def delete(self, name):
        self._tick()
        super().delete(name)


def try_save(fs, state, crash_at):
    """save() of state from a new instance; returns False if the process died before call crash_at."""
    store = ChunkedKVStore(fs)
    for k, v in state.items():
        store.put(k, v)
    fs.calls, fs.crash_at = 0, crash_at
    try:
        store.save()
        return True
    except Crash:
        return False
    finally:
        fs.crash_at = None


# every crash point of one save, followed by every crash point of the next, followed by a clean save
S0 = {f"k{i}": "v" * 30 for i in range(5)}
S1 = {"big": "z" * 300, "\U0001F600": ""}
S2 = {"tiny": "t"}
chunks_of = lambda state: -(-len(_serialize_store(state)) // 48)
scenarios, first, done1 = 0, 0, False
while not done1:
    second, done2 = 0, False
    while not done2:
        fs = CrashingFileSystem(max_file_size=48)
        assert try_save(fs, S0, None)
        done1 = try_save(fs, S1, first)
        after1 = saved(fs)
        assert after1 == (S1 if first > chunks_of(S1) else S0)     # committed iff the manifest write happened
        done2 = try_save(fs, S2, second)
        after2 = saved(fs)
        assert after2 == (S2 if second > chunks_of(S2) else after1)
        assert not done2 or set(fs.list()) == needed_files(fs)
        assert try_save(fs, S0, None) and saved(fs) == S0
        assert set(fs.list()) == needed_files(fs)                  # leftovers of both crashes are gone
        scenarios, second = scenarios + 1, second + 1
    first += 1
assert scenarios > 100

# damage that no crash can cause is reported, not silently returned
for damage in ["flip", "delete"]:
    fs_corrupt = FileSystem(max_file_size=64)
    victim = ChunkedKVStore(fs_corrupt)
    for i in range(10):
        victim.put(f"k{i}", "v" * 40)
    victim.save()
    if damage == "flip":                         # NOTE: reaches into the mock to simulate bit rot
        fs_corrupt._files["chunk_0_0"] = bytes([fs_corrupt.read("chunk_0_0")[0] ^ 0xFF]) + fs_corrupt.read("chunk_0_0")[1:]
    else:
        fs_corrupt.delete("chunk_0_1")
    try:
        ChunkedKVStore(fs_corrupt).load()
        raise AssertionError("expected CorruptStoreError")
    except CorruptStoreError:
        pass

# --- Part 3: replay against a plain dict, a cut at every byte, damaged tails, compaction ---
SMALL = [w for w in WEIRD if len(w) < 50]
fs_log = FileSystem()
log_writer = LogKVStore(fs_log)
model, states, ends = {}, [{}], [0]              # states[n] / ends[n]: the store / the log size after n operations
for _ in range(40):
    key = rng.choice(SMALL)
    if rng.random() < 0.3:
        log_writer.delete(key)
        model.pop(key, None)
    else:
        model[key] = rng.choice(SMALL)
        log_writer.put(key, model[key])
    assert log_writer._data == model
    states.append(dict(model))
    ends.append(len(fs_log.read("log")))
full_log = fs_log.read("log")


def recover(log_bytes):
    fs = FileSystem()
    fs._files["log"] = log_bytes                 # NOTE: reaches into the mock to plant what a crash left
    store = LogKVStore(fs)
    store.load()
    return store, fs


assert recover(b"")[0]._data == {} and LogKVStore(FileSystem()).get("x") is None
for cut in range(len(full_log) + 1):
    n = max(i for i in range(len(ends)) if ends[i] <= cut)         # complete records before the cut
    store, fs = recover(full_log[:cut])
    assert store._data == states[n], cut
    store.put("after", "recovery")                                  # must survive the next load()
    reloaded = LogKVStore(fs)
    reloaded.load()
    assert reloaded._data == {**states[n], "after": "recovery"}, cut

for i in range(ends[-2], len(full_log)):         # the last record, damaged: one byte flipped, or zeroed from byte i on
    flipped = full_log[:i] + bytes([full_log[i] ^ 0xFF]) + full_log[i + 1:]
    assert recover(flipped)[0]._data == states[-2], i
    zeroed = full_log[:i] + bytes(len(full_log) - i)
    assert zeroed == full_log or recover(zeroed)[0]._data == states[-2], i
huge = full_log[:ends[-2]] + b"\xff" * 8 + full_log[ends[-2] + 8:]  # the last length field reads 2**64 - 1
assert recover(huge)[0]._data == states[-2]
assert zlib.crc32(b"") == 0
for n in range(1, 40):                           # zero-filled or random garbage after the last complete record
    for tail in [bytes(n), bytes(rng.randrange(256) for _ in range(n))]:
        store, fs = recover(full_log + tail)
        assert store._data == states[-1] and fs.read("log") == full_log

# compaction: same store, size independent of the history, and an interrupted compact() loses nothing
fs_compact = CrashingFileSystem()
compactor = LogKVStore(fs_compact)
for i in range(50):
    compactor.put("x", str(i))
compactor.put("y", "keep")
compactor.delete("y")
compactor.put("", "")
size_before = len(fs_compact.read("log"))
fs_compact.crash_at = fs_compact.calls
try:
    compactor.compact()
    raise AssertionError("expected Crash")
except Crash:
    pass
assert len(fs_compact.read("log")) == size_before
fs_compact.crash_at = None
compactor.compact()
direct = LogKVStore(FileSystem())
direct.put("x", "49")
direct.put("", "")
assert fs_compact.read("log") == direct.fs.read("log") and fs_compact.list() == ["log"]
verifier = LogKVStore(fs_compact)
verifier.load()
assert verifier._data == {"x": "49", "": ""}
```

</details>

</details>
