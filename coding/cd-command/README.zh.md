# cd 命令 / 路径解析

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 中等 | SWE | string-processing, stack, symlinks | 4 个部分 |
<!-- meta:end -->

## 题目

实现 `cd`：给定当前目录和一个目标，计算在 shell 里执行 `cd destination` 之后 `pwd` 会打印出的绝对路径
（从 Part 3 起是物理路径，即执行 `cd -P destination` 之后 `pwd` 打印出的路径）。函数的参数分三个 Part 逐步增加：
`cd_relative` 处理相对路径的目标，`cd_absolute` 加上绝对路径和 `~`，`cd` 再加上符号链接。最后一个 Part 不写代码，
问的是真实的 shell 命令本身。

### Part 1 —— 规范化一个相对目标

`cwd` 总是一个已经规范化过的绝对路径，例如 `"/srv/www/docs"`：以 `/` 开头，不含 `.` 或 `..` 这样的分量，
不含因为重复 `/` 产生的空分量，也没有结尾的 `/`（`cwd` 本身就是 `"/"` 的情形除外）。`destination` 是相对路径
（不以 `/` 开头），其中可能出现 `.`（停留原地）、`..`（回到上一级）、重复的斜杠，以及结尾的斜杠。
从 `cwd` 出发，逐个分量地跟随 `destination`，计算出规范化的绝对结果。越过根目录的 `..` 停在 `/`，不报错。

```py
def cd_relative(cwd: str, destination: str) -> str:
    ...
```

```text
cd_relative("/srv/www/docs", "guides")               -> "/srv/www/docs/guides"
cd_relative("/srv/www/docs", "../assets")             -> "/srv/www/assets"
cd_relative("/srv/www/docs", "../guides/v2/")         -> "/srv/www/guides/v2"
cd_relative("/srv/www/docs", "./guides/")             -> "/srv/www/docs/guides"
cd_relative("/srv/www/docs", "../guides/v2/../")      -> "/srv/www/guides"
cd_relative("/srv/www", "../../../static")            -> "/static"        （先被限制在根目录，再向下）
cd_relative("/", "../..")                             -> "/"
cd_relative("/srv/www/docs", "../../logs/./today//")  -> "/srv/logs/today"
```

### Part 2 —— 绝对路径与 `~`

扩展函数，使 `destination` 也可以是绝对路径（以 `/` 开头），或者以 `~` 开头——`~` 代表调用者的家目录，
由参数 `home` 显式给出（同样是一个规范化过的绝对路径）。`~` 单独出现时展开为恰好 `home`；`~/rest` 展开为
`home` 与 `rest` 拼接，`rest` 之后再按 Part 1 的规则处理 `.`、`..` 和重复斜杠。如果 `destination` 以 `~`
开头，但既不是 `~` 也不是 `~/...`（例如 `~bob`，指代另一个用户的家目录），这种形式超出本题范围：抛出
`ValueError`。`~` 只有作为 `destination` 的第一个字符时才有特殊含义——`a/~b` 是一个普通的两段式相对路径，
不做展开。

```py
def cd_absolute(cwd: str, destination: str, home: str) -> str:
    ...
```

```text
cd_absolute("/srv/www/docs", "/opt/tools/bin", "/home/priya")  -> "/opt/tools/bin"
cd_absolute("/srv/www/docs", "~", "/home/priya")               -> "/home/priya"
cd_absolute("/srv/www/docs", "~/scripts", "/home/priya")       -> "/home/priya/scripts"
cd_absolute("/tmp/scratch", "../backups", "/home/priya")       -> "/tmp/backups"
cd_absolute("/home/priya", "a/~b", "/home/priya")              -> "/home/priya/a/~b"
cd_absolute("/home/priya", "~bob", "/home/priya")              -> 抛出 ValueError
```

### Part 3 —— 符号链接

再给定 `symlinks`：一个从符号链接的绝对规范路径映射到其目标的字典，目标既可能是绝对路径，也可能是相对于
链接所在目录的相对路径：

```python
symlinks = {
    "/srv/www/current": "/srv/archive/2025-09",
}
```

扩展函数，让它按真实文件系统解析*物理*路径的方式处理符号链接（就像 `cd -P` 或 `realpath` 那样），必须精确
满足下面这些规则：

- 从左到右逐个分量地跟随 `destination`。每当目前走到的路径是 `symlinks` 的一个 key，实际所在的位置就是
  这个链接的目标，剩下的分量从那里接着走。
- `..` 回到目前所在的物理目录的上一级：紧跟在符号链接之后时，是链接所指向的目录的上一级，而不是链接
  所在的目录。在 `/` 处，`..` 与 Part 1 一样停在 `/`。
- 相对目标相对于*链接所在的目录*解析，而不是相对于 `cwd`。
- 目标里可以有 `.`、`..` 和别的符号链接，出现在结尾或中间都可以；目标按同样的规则跟随。
- key 按完整的路径分量匹配，不是子串匹配：`/srv/www/current-backup` 与 key `/srv/www/current` 无关。
  key、`cwd` 和 `home` 都是物理路径：符号链接下面没有条目，所以它们都不会位于某个 key 之下。不是 key 的
  路径一律视为已经存在的普通目录——函数不检查真实文件系统。
- 把一个链接替换成它的目标记为一次展开；同一次调用里再次展开已经展开过的链接，也要再记一次。如果一次
  调用需要超过 `MAX_SYMLINK_HOPS = 20` 次展开，抛出 `SymlinkLoopError`。

```py
class SymlinkLoopError(Exception): ...

MAX_SYMLINK_HOPS = 20

def cd(cwd: str, destination: str, home: str, symlinks: dict[str, str]) -> str:
    ...
```

取 `cwd = "/srv/www"`、`symlinks = {"/srv/www/current": "/srv/archive/2025-09"}`、
`destination = "current/gallery/../notes"`：先进入链接，`gallery/..` 在目标内部抵消，结果是
`"/srv/archive/2025-09/notes"`。

### Part 4 —— shell 到底是怎么执行 `cd` 的？

这一部分不写代码。解释为什么 `cd` 必须是 shell 自带的内建命令，而不能是 shell 另外启动的一个独立程序；
再简要描述一下 shell 执行一次 `cd` 命令大致要经过哪些步骤。

## 参考解答

<details>
<summary>展开参考解答</summary>

开始写代码前值得和面试官确认：符号链接要像 `cd -P` 那样按物理路径解析，而不是按文本做逻辑解析；出现环时
怎么处理（这里是展开次数超过固定上限就抛出异常）。Part 2、Part 3 都复用 Part 1 逐分量处理的栈式写法，
不必每次重新推导。

### Part 1

当前目录和目标本质上都只是一串分量；整道题就是用一个栈来走这串分量。

```python
def _split(path: str) -> list[str]:
    return [tok for tok in path.split("/") if tok != ""]     # NOTE: drops "" from //, a leading /, or a trailing /


def _apply(stack: list[str], token: str) -> None:
    if token in ("", "."):
        return
    if token == "..":
        if stack:                # NOTE: popping an empty stack is the root clamp, not an error
            stack.pop()
        return
    stack.append(token)


def cd_relative(cwd: str, destination: str) -> str:
    stack = _split(cwd)
    for token in destination.split("/"):        # NOTE: split, not _split -- "" tokens must reach _apply
        _apply(stack, token)
    return "/" + "/".join(stack)                 # NOTE: build the leading "/" here; join([]) is "", not "/"
```

### Part 2

先把 `destination` 分类成一个起点（`base`）和剩下的相对尾巴（`rest`），之后就完全是 Part 1 的那套逐分量
处理。

```python
def _start(cwd: str, destination: str, home: str) -> tuple[str, str]:
    if destination == "~" or destination.startswith("~/"):
        return home, destination[2:]      # NOTE: "~"[2:] is "", so a bare "~" lands exactly on home
    if destination.startswith("~"):
        raise ValueError(f"unsupported destination: {destination!r} (~user is out of scope)")
    if destination.startswith("/"):
        return "/", destination           # NOTE: destination's own leading "/" becomes an "" token, dropped by _apply
    return cwd, destination               # NOTE: only a leading "~" is special; "a/~b" falls through to here


def cd_absolute(cwd: str, destination: str, home: str) -> str:
    base, rest = _start(cwd, destination, home)
    stack = _split(base)
    for token in rest.split("/"):
        _apply(stack, token)
    return "/" + "/".join(stack)
```

### Part 3

关键在于：每接上一个分量，*立刻*检查它是不是符号链接，不能等后面的 `..` 先在词法上把它抵消掉。取
`symlinks = {"/srv/www/current": "/srv/archive/2025-09"}`、`destination = "current/../snapshot"`：
压入 `current` 的瞬间就命中了链接，把栈换成目标对应的内容；紧接着的 `..` 弹出的是 `2025-09`，结果是
`"/srv/archive/snapshot"`。如果先把 `current/..` 当纯字符串抵消掉，压根不会去查这个链接，得到的会是
`"/srv/www/snapshot"`——一个完全不同的目录，而且不会有任何报错提示你算错了。

具体做法是维护一个待处理分量的队列：不是链接的名字直接入栈；一旦命中链接，绝对目标先把栈清空（相对目标
不动栈，此时栈里正好是链接所在的目录），再把目标的各个分量放到队列最前面——这样目标的分量会经过同样的
“先入栈、再检查”流程，目标落在另一个链接上、或者中途经过另一个链接时，都能继续解析下去。

```python
from collections import deque


class SymlinkLoopError(Exception):
    pass


MAX_SYMLINK_HOPS = 20   # NOTE: a choice of this problem; Linux (kernel lookup and glibc realpath) fails with ELOOP after 40


def cd(cwd: str, destination: str, home: str, symlinks: dict[str, str]) -> str:
    base, rest = _start(cwd, destination, home)
    stack = _split(base)                  # physical already: cwd and home never lie under a link
    pending = deque(rest.split("/"))
    hops = 0
    while pending:
        token = pending.popleft()
        if token in ("", ".", ".."):
            _apply(stack, token)          # NOTE: ".." pops the PHYSICAL stack -- already past any earlier link
            continue
        target = symlinks.get("/" + "/".join(stack + [token]))   # the path this token would create
        if target is None:
            stack.append(token)
            continue
        hops += 1
        if hops > MAX_SYMLINK_HOPS:
            raise SymlinkLoopError(f"more than {MAX_SYMLINK_HOPS} symlink expansions resolving {destination!r}")
        if target.startswith("/"):
            stack = []
        # NOTE: otherwise `stack` is still the directory that contains the link -- the base of a relative target
        pending.extendleft(reversed(target.split("/")))
    return "/" + "/".join(stack)
```

在 `a → b → a` 这样的环里，每次展开都会把另一个链接放回队列最前面，处理永远不会结束；展开次数计数器的
作用，就是把这种情况变成一次 `SymlinkLoopError`。这里刻意没有采用“一个链接第二次出现就报错”的做法：
一个指向自己所在目录的链接是合法的，在 `destination` 里连续出现好几次也完全正常
（`{"/srv/shared/self": "."}` 下，`self/self/self/x` 只需 3 次展开就能解析成 `"/srv/shared/x"`，远低于
上限），按“见过就报错”的规则反而会误判这种合法输入。Linux 也是这样限制次数的：执行 `ln -s . loop` 之后，
内核和 glibc 的 `realpath()` 都能解析由 40 个 `loop/` 组成的路径，到第 41 次展开才以 `ELOOP`
（“Too many levels of symbolic links”）失败。

### Part 4

进程的当前工作目录属于该进程自身的状态——内核为每个进程各记录一份。`fork()` 会把它拷贝一份给子进程，
但从那以后两者互不相干：子进程调用 `chdir()` 只会移动它自己，它退出之后，父进程的工作目录丝毫未变。所以如果 `cd` 也像普通命令一样执行——shell fork 出一个子进程，子进程 exec
`cd` 再调用 `chdir()`——那么真正移动的只是这个转瞬即逝的子进程，交互式的 shell 本身永远不会离开原来的
目录。唯一能让 `cd` 真正移动 shell 自己的办法，就是在 shell 自己的进程里执行，不 fork 也不 exec，这正是
“shell 内建命令”的含义：shell（在展开命令行之后）查找命令名时，在自己的内建命令里找到 `cd`，直接在自己
内部执行，而不是去 `$PATH` 里找一个同名程序来运行。

内建命令本身大致做这些事。参数里的 `~`、变量和引号已经由 shell 展开过；参数是 `-` 时，由 `cd` 自己把它
当作 `$OLDPWD`。然后算出新目录：普通的 `cd` 是逻辑式的（对 shell 自己的 `$PWD` 做文本操作，规则与 Part 1、2
相同，传给 `chdir()` 的就是这样算出的路径），`cd -P` 则是物理式的（跟随符号链接，把 `..` 作用在真实目录树上，
就像 Part 3 那样）。接着调用 `chdir()` 系统调用，成功的话更新 `$PWD` 和 `$OLDPWD`。如果失败——目标不存在，
或者路径中途某个分量不是目录、或不可搜索——`chdir()` 会返回一个错误，shell 汇报这个错误，自己的工作目录
保持不变。

### 追问

- `CDPATH`：如果 `destination` 是相对路径、而且第一个分量不是 `.` 或 `..`，POSIX shell 会先依次把
  `$CDPATH` 里列出的每个目录当作父目录去尝试，都没有时才回到当前目录（用的是 `CDPATH` 里的目录时，还会把
  新目录打印出来）。这是 shell 自己的搜索便利，不属于本题 `cd()` 的语义。
- `cd -` 会跳到 `$OLDPWD`，打印出新目录，并让 `$PWD` 与 `$OLDPWD` 互换。
- 目标不存在时，真正的 `chdir()` 会失败并返回 `ENOENT`；本题的函数从不接触文件系统，所以不会出现这种
  情况。
- Linux 拒绝给目录建硬链接（即使是 root，`link()` 也会以 `EPERM` 失败）：否则同一个目录会有两个父目录，
  `..` 就有了歧义；而指向自己祖先的硬链接会在目录树里造出一个环，`du`、`fsck` 这类遍历目录树的工具都假设
  这种环不存在。
- 工作目录是进程级别的，不是线程级别的：一个进程内的多个线程共享同一个工作目录，一个线程 `chdir` 会
  连带移动另一个线程——这恰好与父子进程之间的隔离相反，而正是那种隔离让 `cd` 必须是内建命令。

<details>
<summary>验证代码（可运行）</summary>

```python
import itertools
import os
import posixpath
import random
import tempfile

# --- Part 1 ---
assert cd_relative("/srv/www/docs", "guides") == "/srv/www/docs/guides"
assert cd_relative("/srv/www/docs", "../assets") == "/srv/www/assets"
assert cd_relative("/srv/www/docs", "../guides/v2/") == "/srv/www/guides/v2"
assert cd_relative("/srv/www/docs", "./guides/") == "/srv/www/docs/guides"
assert cd_relative("/srv/www/docs", "../guides/v2/../") == "/srv/www/guides"
assert cd_relative("/srv/www", "../../../static") == "/static"
assert cd_relative("/", "../..") == "/"
assert cd_relative("/srv/www/docs", "../../logs/./today//") == "/srv/logs/today"

# --- Part 2 ---
home = "/home/priya"
assert cd_absolute("/srv/www/docs", "/opt/tools/bin", home) == "/opt/tools/bin"
assert cd_absolute("/srv/www/docs", "~", home) == "/home/priya"
assert cd_absolute("/srv/www/docs", "~/scripts", home) == "/home/priya/scripts"
assert cd_absolute("/tmp/scratch", "../backups", home) == "/tmp/backups"
assert cd_absolute("/home/priya", "a/~b", home) == "/home/priya/a/~b"
try:
    cd_absolute("/home/priya", "~bob", home)
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# --- Part 3: worked examples, including the physical-vs-lexical contrast ---
symlinks_ex = {"/srv/www/current": "/srv/archive/2025-09"}
assert cd("/srv/www", "current/gallery/../notes", home, symlinks_ex) == "/srv/archive/2025-09/notes"

physical = cd("/srv/www", "current/../snapshot", home, symlinks_ex)
lexical_first = cd_relative("/srv/www", "current/../snapshot")     # NOTE: wrong on purpose, for contrast
assert physical == "/srv/archive/snapshot"
assert lexical_first == "/srv/www/snapshot"

symlinks_rel = {"/srv/www/current": "../archive/vault"}            # relative target
assert cd("/srv/www", "current/notes", home, symlinks_rel) == "/srv/archive/vault/notes"

symlinks_chain = {                                                  # target is itself a symlink
    "/srv/www/current": "/srv/archive/latest",
    "/srv/archive/latest": "/srv/archive/2025-09",
}
assert cd("/srv/www", "current/notes", home, symlinks_chain) == "/srv/archive/2025-09/notes"

cycle_symlinks = {"/opt/cycle/a": "/opt/cycle/b", "/opt/cycle/b": "/opt/cycle/a"}
repeat_symlinks = {"/srv/shared/self": "."}   # visited several times, but not a cycle
assert cd("/srv/shared", "self/self/self/notes", home, repeat_symlinks) == "/srv/shared/notes"


def chain(n):   # /c/l1 -> l2 -> ... -> ln -> real: n expansions
    links = {f"/c/l{k}": f"l{k + 1}" for k in range(1, n)}
    links[f"/c/l{n}"] = "real"
    return links


# the cap counts expansions, not distinct links: 20 are allowed, the 21st raises
assert cd("/c", "l1", home, chain(20)) == "/c/real"
assert cd("/srv/shared", "/".join(["self"] * 20), home, repeat_symlinks) == "/srv/shared"
for cwd, destination, links in [("/c", "l1", chain(21)), ("/srv/shared", "/".join(["self"] * 21), repeat_symlinks),
                                ("/opt/cycle", "a", cycle_symlinks)]:
    try:
        cd(cwd, destination, home, links)
        raise AssertionError("expected SymlinkLoopError")
    except SymlinkLoopError:
        pass

# --- independent check 1: Parts 1-2 against posixpath.normpath. normpath also stops ".." at "/" for an
# absolute path, but keeps exactly two leading slashes, so every combined path starts with a single "/" ---
assert posixpath.normpath("/../a/../../b") == "/b"
assert posixpath.normpath("//x/y") == "//x/y" and posixpath.normpath("///x/y") == "/x/y"

names = ["alpha", "beta", "gamma"]
rng = random.Random(0)
for _ in range(3000):
    cwd = "/" + "/".join(rng.choice(names) for _ in range(rng.randint(0, 3)))     # includes cwd == "/"
    tokens = [rng.choice(names + [".", ".."])]                                    # never "" first
    tokens += [rng.choice(names + [".", "..", ""]) for _ in range(rng.randint(0, 6))]
    rest = "/".join(tokens)
    kind = rng.choice(["relative", "absolute", "home"])
    if kind == "relative":
        got, combined = cd_relative(cwd, rest), cwd.rstrip("/") + "/" + rest
    elif kind == "absolute":
        got, combined = cd_absolute(cwd, "/" + rest, home), "/" + rest
    else:
        got, combined = cd_absolute(cwd, "~/" + rest, home), home + "/" + rest
    assert not combined.startswith("//")
    assert got == posixpath.normpath(combined), (cwd, kind, rest)


# --- independent check 2: Part 3 against a direct, recursive reading of the rules (on every input, including
# ".." at "/", cycles and the cap), and against os.path.realpath on a real directory tree with real links ---
class TooManyExpansions(Exception):
    pass


def spec_cd(cwd, destination, home, symlinks):
    """Returns (path, or None past 20 expansions; number of expansions; whether a ".." was applied at "/")."""
    if destination == "~" or destination.startswith("~/"):
        start, rest = home, destination[2:]
    elif destination.startswith("/"):
        start, rest = "/", destination
    else:
        start, rest = cwd, destination
    hops, hit_root = 0, False

    def follow(parts, path):          # from directory `parts`, follow every component of `path`
        nonlocal hops, hit_root
        for comp in path.split("/"):
            if comp == "..":
                hit_root = hit_root or not parts
                parts = parts[:-1]
            elif comp not in ("", "."):
                here = "/" + "/".join(parts + [comp])
                if here not in symlinks:
                    parts = parts + [comp]
                    continue
                hops += 1
                if hops > 20:
                    raise TooManyExpansions
                target = symlinks[here]
                parts = follow([] if target.startswith("/") else parts, target)
        return parts

    try:
        path = "/" + "/".join(follow([c for c in start.split("/") if c], rest))
    except TooManyExpansions:
        path = None
    return path, hops, hit_root


with tempfile.TemporaryDirectory() as tmp:
    root = os.path.realpath(tmp)       # NOTE: the temp directory itself may sit behind a link (macOS: /tmp)
    dirs = ["/"] + ["/" + "/".join(p) for n in (1, 2, 3) for p in itertools.product("pq", repeat=n)]
    for d in dirs:
        os.makedirs(root + d, exist_ok=True)
    # links named x / y in random directories: absolute and relative targets, targets that climb (even past
    # "/"), point at their own directory, end at or pass through another link, and genuine cycles
    targets = ["/q/p", "/p/q/x", "/q/x/p", "..", "../..", "../../../../q", ".", "y", "../x/q", "x/..", "./y/p"]
    rng = random.Random(1)
    real_symlinks = {}
    for d in dirs:
        for name in ("x", "y"):
            if rng.random() < 0.6:
                real_symlinks[d.rstrip("/") + "/" + name] = rng.choice(targets)
    for link, target in real_symlinks.items():
        os.symlink(root + target if target.startswith("/") else target, root + link)
    words = ["p", "q", "x", "y", "x", "y", ".", "..", ""]

    compared_with_realpath = with_links = loops = 0
    for _ in range(8000):
        cwd, home_dir = rng.choice(dirs), rng.choice(dirs)
        rest = "/".join(rng.choice(words) for _ in range(rng.randint(1, 7)))
        kind = rng.choice(["relative", "relative", "absolute", "home"])
        if kind == "home":
            destination, full = "~/" + rest, home_dir.rstrip("/") + "/" + rest
        elif kind == "absolute" or rest.startswith("/"):
            destination, full = "/" + rest, "/" + rest
        else:
            destination, full = rest, cwd.rstrip("/") + "/" + rest
        try:
            got = cd(cwd, destination, home_dir, real_symlinks)
        except SymlinkLoopError:
            got = None
        expected, hops, hit_root = spec_cd(cwd, destination, home_dir, real_symlinks)
        assert got == expected, (cwd, destination, home_dir, got, expected)
        loops += expected is None
        if expected is None or hit_root:   # the real tree has a parent above `root`; realpath() does not stop there
            continue
        real = os.path.realpath(root + full)
        assert (real[len(root):] or "/") == expected, (cwd, destination, home_dir, expected, real)
        compared_with_realpath += 1
        with_links += hops > 0
    assert compared_with_realpath > 4000 and with_links > 1500 and loops > 500

    # a genuine cycle: os.path.realpath(strict=True) refuses it as well
    os.symlink(root + "/p/p/p/b", root + "/p/p/p/a")
    os.symlink("a", root + "/p/p/p/b")
    assert spec_cd("/p/p/p", "a", home, {"/p/p/p/a": "/p/p/p/b", "/p/p/p/b": "a"})[0] is None
    try:
        os.path.realpath(root + "/p/p/p/a", strict=True)
        raise AssertionError("expected OSError")
    except OSError as e:
        import errno
        assert e.errno == errno.ELOOP
```

</details>

</details>
