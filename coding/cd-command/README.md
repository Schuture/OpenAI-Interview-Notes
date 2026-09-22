# cd Command / Path Resolution

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Medium | SWE | string-processing, stack, symlinks | 4 parts |
<!-- meta:end -->

## Problem

Implement `cd`, a function that computes the absolute path `pwd` would print after running `cd destination`
in a shell (from Part 3 on, the physical path that `cd -P destination` followed by `pwd` prints). The
function grows a parameter at a time across three parts: `cd_relative` takes a relative destination,
`cd_absolute` adds absolute destinations and `~`, and `cd` adds symbolic links. A final part asks about the
real shell command instead of code.

### Part 1 — Normalize a Relative Destination

`cwd` is given as an absolute, already-normalized path such as `"/srv/www/docs"`: it starts with `/`,
contains no `.` or `..` segment, no empty segment from a repeated `/`, and no trailing `/` (except `cwd
== "/"` itself). `destination` is relative (it never starts with `/`) and may contain `.` (stay), `..`
(go up one level), repeated slashes, and a trailing slash. Compute the absolute, normalized result of
starting at `cwd` and following `destination` component by component. Going above `/` leaves you at `/`
instead of erroring.

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
cd_relative("/srv/www", "../../../static")            -> "/static"        (clamped at root, then descends)
cd_relative("/", "../..")                             -> "/"
cd_relative("/srv/www/docs", "../../logs/./today//")  -> "/srv/logs/today"
```

### Part 2 — Absolute Paths and `~`

Extend the function so `destination` may also be an absolute path (starts with `/`) or start with `~`,
which stands for the caller's home directory, given explicitly as `home` (also an absolute, normalized
path). `~` expands to exactly `home`; `~/rest` expands to `home` joined with `rest`, and `rest` is then
subject to the same `.`/`..`/repeated-slash handling as Part 1. A destination that starts with `~` but is
neither `~` nor `~/...` (for example `~bob`, another user's home directory) is out of scope: raise
`ValueError`. `~` is only special as the very first character of `destination` — `a/~b` is an ordinary
two-component relative path, not an expansion.

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
cd_absolute("/home/priya", "~bob", "/home/priya")              -> raises ValueError
```

### Part 3 — Symbolic Links

You are additionally given `symlinks`, a mapping from the absolute, normalized path of a symbolic link to
its target, which may itself be an absolute path or a path relative to the directory that contains the
link:

```python
symlinks = {
    "/srv/www/current": "/srv/archive/2025-09",
}
```

Extend the function to resolve symbolic links the way a real filesystem does when it follows a path
*physically* (as `cd -P` or `realpath` would), matching these rules exactly:

- `destination` is followed one component at a time, left to right. Whenever the path reached so far is a
  key of `symlinks`, you are in fact at that link's target, and the remaining components continue from
  there.
- `..` goes to the parent of the physical directory reached so far: right after a symbolic link, that is
  the parent of the directory the link leads to, not the directory that contains the link. At `/`, `..`
  stays at `/` as in Part 1.
- A relative target is resolved against the directory that *contains the link*, not against `cwd`.
- A target may contain `.`, `..` and other symbolic links, at its end or in its middle; it is followed by
  these same rules.
- Keys match whole path components, not substrings: `/srv/www/current-backup` is unrelated to a key
  `/srv/www/current`. Keys, `cwd` and `home` are physical paths: none of them lies under a key, since a
  symbolic link has no entries. Every path that is not a key is an ordinary, existing directory — the
  function does not check the real filesystem.
- Each replacement of a link by its target counts as one expansion, including another expansion of a link
  already expanded in the same call. If one call needs more than `MAX_SYMLINK_HOPS = 20` expansions, raise
  `SymlinkLoopError`.

```py
class SymlinkLoopError(Exception): ...

MAX_SYMLINK_HOPS = 20

def cd(cwd: str, destination: str, home: str, symlinks: dict[str, str]) -> str:
    ...
```

With `cwd = "/srv/www"`, `symlinks = {"/srv/www/current": "/srv/archive/2025-09"}`, and `destination =
"current/gallery/../notes"`, the link is entered first, then `gallery/..` cancels inside the target, so
the result is `"/srv/archive/2025-09/notes"`.

### Part 4 — How Does a Shell Actually Run `cd`?

No code for this part. Explain why `cd` has to be a built-in command of the shell rather than a separate
program the shell launches, and describe, briefly, the steps a shell goes through to execute a `cd`
command.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming with the interviewer before coding: that symbolic links are resolved physically, as
`cd -P` does, rather than lexically, and what a cycle should produce (here, an exception once a fixed number
of expansions is exceeded). Parts 2 and 3 both reuse the token-by-token walk of Part 1 instead of re-deriving
it.

### Part 1

The current directory and the destination are both just sequences of components; the whole problem is
walking them with a stack.

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

`destination` first gets classified into a starting point (`base`) and a remaining relative tail
(`rest`); from there it is exactly the walk of Part 1.

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

The key is to check for a symbolic link *immediately after each component is pushed*, before any later
`..` has a chance to remove it lexically. With `symlinks = {"/srv/www/current": "/srv/archive/2025-09"}`
and `destination = "current/../snapshot"`, pushing `current` matches the link right away and swaps the
stack for the target; the `..` that follows then pops `2025-09`, giving `"/srv/archive/snapshot"`. A
version that first cancels `current/..` as plain strings never even looks the link up and returns
`"/srv/www/snapshot"` instead — a different directory, silently.

Concretely, the walk keeps a queue of components still to be followed. A name that is not a link is pushed
onto the stack. On a match, an absolute target first empties the stack (for a relative target the stack
already holds the link's own directory), and the target's components go to the front of the queue — so
they go through the very same push-then-check step, which is what makes a target that lands on, or passes
through, another link keep resolving.

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

In a cycle such as `a → b → a`, every expansion puts another link at the front of the queue, so the walk
would never end; the hop counter turns that into a `SymlinkLoopError`. This is deliberately not "raise the
first time a link is seen twice": a link that points at its own containing directory is legitimate and can
appear in `destination` several times in a row (`self/self/self/x` behind `{"/srv/shared/self": "."}`
resolves to `"/srv/shared/x"` in three hops, well under the cap), so a seen-before set would reject valid
input. Linux bounds the count the same way: after `ln -s . loop`, both the kernel and glibc's `realpath()`
resolve a path made of 40 `loop/` components and fail with `ELOOP` ("Too many levels of symbolic links")
only at the 41st.

### Part 4

A process's current working directory is state that belongs to that process — the kernel keeps one for
each process. `fork()` gives a child a copy of it, but afterwards the two are independent: a child that
calls `chdir()` only moves itself, and once it exits, the parent's own working directory is exactly as it
was. So if `cd` ran the way an ordinary command does — the shell
forking a child process that execs `cd` and calls `chdir()` — only that short-lived child would move, and
the interactive shell itself would never leave its old directory. The only way `cd` can move the shell
itself is to run inside the shell's own process, with no fork or exec, which is what "shell built-in"
means: when the shell looks up the command name (after expanding the command line), it finds `cd` among its
built-ins and runs it directly instead of searching `$PATH` for a program to run.

The built-in itself does roughly this. The shell has already expanded `~`, variables and quotes in the
argument; `cd` itself treats an argument of `-` as `$OLDPWD`. It computes the new directory, lexically for
a plain `cd` (text manipulation of the shell's own `$PWD`, the same rules as Parts 1–2; this computed path
is what it passes to `chdir()`) or physically for `cd -P` (following symbolic links and applying `..` to
the real directory tree, as in Part 3). It then calls the `chdir()` system call and, if that succeeds,
updates `$PWD` and `$OLDPWD`. If it fails — the directory does not exist, or a component along the way is
not a directory or is not searchable — `chdir()` returns an error and the shell reports it without changing
its working directory.

### Follow-ups

- `CDPATH`: for a relative `destination` whose first component is not `.` or `..`, a POSIX shell first
  tries each directory listed in `$CDPATH` as the parent and falls back to the current directory only if
  none of them has it (printing the new directory when it came from `CDPATH`). It is a shell search
  convenience, not part of this problem's `cd()`.
- `cd -` changes to `$OLDPWD`, prints the new directory, and leaves `$PWD` and `$OLDPWD` swapped.
- A destination that does not exist makes the real `chdir()` fail with `ENOENT`; this problem never
  touches the filesystem, so that case does not arise here.
- Linux refuses to create a hard link to a directory (`link()` fails with `EPERM`, even for root): the
  directory would get two parents, making `..` ambiguous, and a link to one of its own ancestors would put a
  cycle into a tree that tools such as `du` and `fsck` walk on the assumption that it has none.
- The working directory is process-wide, not per-thread: two threads of one process share it, so one
  thread's `chdir()` moves the other too — the opposite of the parent/child isolation that makes `cd` need
  to be a built-in in the first place.

<details>
<summary>Checks (runnable)</summary>

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
