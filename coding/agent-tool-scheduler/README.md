# Scheduling Agent Tool Calls with Dependencies

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Medium | SWE · RE · Infra Eng | scheduling, dag, simulation, concurrency | 3 parts | Phone screen |
<!-- meta:end -->

## Problem

An agent framework runs $A$ agents at once, agent $a$ numbered $0, \dots, A - 1$. Agent $a$ issues a
fixed batch of *tool calls* — writing code, running the test suite, running a linter, and so on —
numbered $0, \dots, T_a - 1$ within that agent. Every tool call has an integer *duration* between 1 and
$10^9$ and a (possibly empty) list of *dependencies*: other tool calls' ids, always belonging to that
same agent, that must run to completion first. Those dependencies may contain a cycle: if any tool call
can never run because it depends, directly or transitively, on one, every function below raises
`CycleError` instead of returning a schedule.

Time advances over the integers. A schedule assigns every tool call a *start time* under the following
rules:

- A tool call occupies one *slot* of the available concurrency from its start time up to (but not
  including) `start_time + duration`; while it holds a slot, nothing else may use that slot.
- A call may start at an instant $t$ only if every one of its dependencies has `start_time + duration`
  at most $t$: a dependency that finishes at $t$ unlocks its dependents at $t$, not before.
- At any instant where some calls finish and others could start, every finishing call is retired first —
  freeing its slot and checking whether that unlocks a dependent — and only once every finishing call has
  been retired are new calls started into the freed slots.
- Once started, a call runs to completion without interruption: there is no preemption.
- No slot is ever left idle while eligible work exists: at no instant may a slot sit free while some
  call whose dependencies are all satisfied has not started yet — every such slot is filled at that
  very instant (the schedule is *work-conserving*).
- Whenever slots run out before every eligible call can start, or several calls simply start together,
  ties are broken by ascending `(agent_id, tool_id)`.

Every part below returns the calls that were started, as `(start_time, agent_id, tool_id)` triples
ordered by `start_time` and then by `(agent_id, tool_id)`, together with the *makespan*: the largest
`start_time + duration` over every call (0 when there are no calls at all).

```py
from typing import NamedTuple, Sequence

class ToolCall(NamedTuple):
    tool_id: int
    duration: int              # 1 .. 10**9
    deps: Sequence[int] = ()   # other tool_id's belonging to the SAME agent, all required first

class CycleError(Exception):
    """Some tool calls can never run: their dependencies form a cycle."""
```

### Part 1 — One agent's own tool calls

A single agent submits a list of `ToolCall`s in which every value `0, ..., len(calls) - 1` occurs
exactly once as some call's `tool_id` (a call's position inside the list need not match its `tool_id`).
The agent's own concurrency cap `capacity` is a positive integer; a cap above `len(calls)` only leaves
slots permanently unused. Implement `schedule_agent`.

```py
from typing import List, Tuple

def schedule_agent(calls: List[ToolCall], capacity: int) -> Tuple[List[Tuple[int, int, int]], int]:
    """Every triple in the returned list has agent_id == 0. Returns ([], 0) for an empty `calls`."""
```

Example, with `capacity = 1` and three calls — `ToolCall(0, 2)`, `ToolCall(1, 1)`, and
`ToolCall(2, 1, deps=(0,))`:

```text
schedule_agent(calls, 1) == ([(0, 0, 0), (2, 0, 1), (3, 0, 2)], 4)
```

Call 1 has no dependency and is ready from time 0, but the single slot is held by call 0 until time 2,
so call 1 only starts then; call 2 waits on call 0 and starts right after it, at time 3.

### Part 2 — Several agents, each under its own cap

Now $A$ agents each submit their own list of `ToolCall`s. Agent $a$'s `tool_id`s are local to agent
$a$ — the same `tool_id` in two different agents names two different calls. Agent $a$ has its own
positive cap `capacities[a]`, and no agent's calls ever compete with another agent's for a slot.
Implement `schedule_agents_independently`.

```py
def schedule_agents_independently(
    agents: List[List[ToolCall]], capacities: List[int]
) -> Tuple[List[Tuple[int, int, int]], int]:
    """agents[a] is agent a's own calls, scheduled exactly as schedule_agent would schedule them on
    their own under capacities[a]. Returns every started call across every agent, and the largest of
    the per-agent makespans."""
```

Example, with agent 0's calls `ToolCall(0, 2)`, `ToolCall(1, 1, deps=(0,))` under
`capacities[0] = 1`, and agent 1's calls `ToolCall(0, 1)`, `ToolCall(1, 1)` under `capacities[1] = 2`:

```text
schedule_agents_independently(agents, [1, 2]) == ([(0, 0, 0), (0, 1, 0), (0, 1, 1), (2, 0, 1)], 3)
```

Agent 1's two calls have no dependencies, and its cap of 2 lets both start at time 0; agent 0's own
makespan of 3 is what sets the overall makespan, even though agent 1 finishes earlier.

### Part 3 — One cap shared by every agent

The same $A$ agents as in Part 2 now draw from a single positive global `capacity` — a call belonging
to any agent may take any free slot, so agents genuinely compete for slots. Implement
`schedule_agents_global`.

```py
def schedule_agents_global(
    agents: List[List[ToolCall]], capacity: int
) -> Tuple[List[Tuple[int, int, int]], int]:
    """Same `agents` shape as schedule_agents_independently, but one `capacity` shared by all of
    them."""
```

Constraints: $1 \le A \le 10^5$; the total number of calls $N = \sum_a \text{len(agents[a])}$ satisfies
$N \le 2 \times 10^5$; the total number of dependency edges $E$ satisfies $E \le 5 \times 10^5$; time
must be $O((N + E) \log N)$ and space $O(N + E)$.

Example, with three agents and `capacity = 2`:

- Agent 0: `ToolCall(0, 2)`, `ToolCall(1, 3, deps=(0,))`, `ToolCall(2, 1, deps=(0,))`
- Agent 1: `ToolCall(0, 4)`, `ToolCall(1, 2, deps=(0,))`
- Agent 2: `ToolCall(0, 2)`

Writing $(a, i)$ for agent $a$'s call $i$, and stepping through it:

- $t = 0$: $(0,0)$, $(1,0)$ and $(2,0)$ all have no dependency and are ready, but only 2 slots exist.
  The tie-break starts $(0,0)$ and $(1,0)$; $(2,0)$ stays ready, waiting for a slot. $(0,0)$ finishes at
  2, $(1,0)$ at 4.
- $t = 2$: $(0,0)$ finishes, freeing one slot and unlocking both $(0,1)$ and $(0,2)$ — each depended
  only on it. Ready now: $(0,1)$, $(0,2)$, and the still-waiting $(2,0)$; only one slot is free
  ($(1,0)$ still runs). The tie-break starts $(0,1)$; it finishes at 5.
- $t = 4$: $(1,0)$ finishes, unlocking $(1,1)$. Ready now: $(0,2)$, $(1,1)$, $(2,0)$; one slot is free
  ($(0,1)$ still runs). $(0,2)$ wins the tie-break and starts, finishing at 5.
- $t = 5$: $(0,1)$ and $(0,2)$ both finish, freeing both slots; neither unlocks anything else. Ready:
  $(1,1)$ and $(2,0)$ — with two free slots, both start, in that order. Both finish at 7.
- $t = 7$: everything has finished.

```text
schedule_agents_global(agents, 2) == (
    [(0, 0, 0), (0, 1, 0), (2, 0, 1), (4, 0, 2), (5, 1, 1), (5, 2, 0)],
    7,
)
```

Note that $(2,0)$ became ready at time 0 but is outranked by lower `agent_id`s at every contested slot
until time 5: the tie-break decides who gets a slot when several calls compete for it, not only how
simultaneous starts get printed.

## Reference solution

<details>
<summary>Show the reference solution</summary>

One point worth confirming before coding: the same `(agent_id, tool_id)` order that wins a contested
slot also governs how simultaneous starts are printed — the code below, and the Part 3 example above,
treat these as one rule rather than two independent ones.

### Part 1

Every part shares one engine: a *ready* heap of `(agent_id, tool_id, position)` for calls whose
dependencies are all satisfied but that have not started, and a *running* heap of
`(finish_time, agent_id, tool_id, position)` for calls currently holding a slot. The main loop
alternates two phases — drain `ready` into free slots for as long as both exist, otherwise jump straight
to the next finish time and release everything finishing there, decrementing the indegree of every
dependent. That order is exactly "retire every finishing call, and unlock its dependents, before
starting anything new": a new call can only start in the *next* pass through the drain phase, which
happens after that jump.

Stepping one time unit at a time would also work, but a duration can be as large as $10^9$, so the
number of ticks is unbounded in $N$. Jumping straight to the next finish time instead bounds the number
of *macro* steps by $N$ (one call starts, or one batch of calls finishes, per step); each macro step does
$O(\log N)$ heap work, and the indegree decrements cost $O(E)$ in total over the whole run — giving
$O((N + E) \log N)$ time and $O(N + E)$ space for the heaps and the dependency lists.

The same indegree bookkeeping doubles as the cycle check the statement asks for: if the loop ever finds
both heaps empty while calls remain unscheduled, none of those calls can ever reach indegree 0, which
happens exactly when they depend on a cycle — the standard argument behind Kahn's algorithm. That is
where `CycleError` is raised, rather than looping forever or returning a partial schedule.

```python
import heapq
from typing import List, Tuple, NamedTuple, Sequence


class ToolCall(NamedTuple):
    tool_id: int
    duration: int
    deps: Sequence[int] = ()


class CycleError(Exception):
    """Some tool calls can never run: their dependencies form a cycle."""


def _event_driven_schedule(tasks, capacity):
    """tasks: list of (agent_id, ToolCall); every dependency of a call is another tool_id sharing
    that same agent_id. `capacity` slots are shared by everything in `tasks`."""
    n = len(tasks)
    pos = {(agent_id, call.tool_id): i for i, (agent_id, call) in enumerate(tasks)}
    indegree = [0] * n
    dependents: List[List[int]] = [[] for _ in range(n)]
    for i, (agent_id, call) in enumerate(tasks):
        for dep in call.deps:
            j = pos[(agent_id, dep)]        # NOTE: KeyError here means a dep id outside this agent
            dependents[j].append(i)
            indegree[i] += 1

    ready = [(agent_id, call.tool_id, i)
             for i, (agent_id, call) in enumerate(tasks) if indegree[i] == 0]
    heapq.heapify(ready)
    running: List[Tuple[int, int, int, int]] = []
    starts: List[Tuple[int, int, int]] = []
    free, scheduled, now, makespan = capacity, 0, 0, 0

    while scheduled < n:
        while free > 0 and ready:                       # NOTE: drain before ever advancing `now`
            agent_id, tool_id, i = heapq.heappop(ready)
            starts.append((now, agent_id, tool_id))
            free, scheduled = free - 1, scheduled + 1
            finish = now + tasks[i][1].duration
            makespan = max(makespan, finish)
            heapq.heappush(running, (finish, agent_id, tool_id, i))
        if scheduled == n:
            break
        if not running:
            raise CycleError("some tool calls can never become ready")
        now = running[0][0]
        while running and running[0][0] == now:          # release EVERY call finishing at `now`
            _, agent_id, tool_id, i = heapq.heappop(running)
            free += 1
            for j in dependents[i]:
                indegree[j] -= 1
                if indegree[j] == 0:
                    heapq.heappush(ready, (tasks[j][0], tasks[j][1].tool_id, j))

    return starts, makespan


def schedule_agent(calls: List[ToolCall], capacity: int):
    return _event_driven_schedule([(0, c) for c in calls], capacity)
```

### Part 2

Every agent's own schedule is independent of every other agent's, so `schedule_agents_independently` is
just `schedule_agent` called once per agent — with that agent's own calls tagged by its `agent_id` so
the output triples come out right — followed by a merge. Unlike Parts 1 and 3, this merge needs an
explicit sort: each call to `_event_driven_schedule` produces its own start times already in order, but
interleaving two or more such *separate* timelines by `start_time` is not something either call did on
its own.

```python
def schedule_agents_independently(agents: List[List[ToolCall]], capacities: List[int]):
    all_starts: List[Tuple[int, int, int]] = []
    makespan = 0
    for agent_id, (calls, capacity) in enumerate(zip(agents, capacities)):
        starts, agent_makespan = _event_driven_schedule([(agent_id, c) for c in calls], capacity)
        all_starts.extend(starts)
        makespan = max(makespan, agent_makespan)
    all_starts.sort()                  # NOTE: needed here; each agent's own starts were already sorted
    return all_starts, makespan
```

### Part 3

A global cap means every agent's calls draw from the *same* pool of slots, so scheduling each agent on
its own and merging, as Part 2 did, is wrong the moment two agents both have a call ready at once: the
engine has to see every call across every agent to decide who gets a slot. That is exactly what
`_event_driven_schedule` already does when handed every agent's calls in one combined list under one
shared `capacity`; no separate merge step is needed afterward, because the single timeline it walks
already interleaves every agent's starts in the required order.

```python
def schedule_agents_global(agents: List[List[ToolCall]], capacity: int):
    tasks = [(agent_id, call) for agent_id, calls in enumerate(agents) for call in calls]
    return _event_driven_schedule(tasks, capacity)
```

### Follow-ups

- A real executor keeps the same indegree counters: a call is submitted to the pool only once its
  counter reaches 0, decremented under a lock by whichever dependency finishes last, and a pool of
  `capacity` workers is the cap. Having each job block on its dependencies' `threading.Event`s instead
  deadlocks as soon as `capacity` jobs are parked on dependencies still queued behind them; and since
  real completions do not land on one shared instant, the lexicographic rule above becomes a tie-break
  among whatever happens to be ready when a worker frees up.
- $(2, 0)$'s long wait in the Part 3 example is not a bug: the tie-break is deterministic, not fair, and
  it only ever delays a call, never drops it — the instance is finite and every started call finishes,
  so every call does start eventually.
- Layering a per-agent cap on top of the global one breaks the single `ready` heap: its smallest entry
  may belong to an agent already at its own cap, so keep one ready heap per agent and take the smallest
  entry among the agents still below theirs.

<details>
<summary>Checks (runnable)</summary>

```python
import random
import time as _time

# The three worked examples from the Problem section, pinned exactly.
assert schedule_agent([ToolCall(0, 2, ()), ToolCall(1, 1, ()), ToolCall(2, 1, (0,))], 1) == (
    [(0, 0, 0), (2, 0, 1), (3, 0, 2)], 4)
assert schedule_agents_independently(
    [[ToolCall(0, 2, ()), ToolCall(1, 1, (0,))], [ToolCall(0, 1, ()), ToolCall(1, 1, ())]], [1, 2]
) == ([(0, 0, 0), (0, 1, 0), (0, 1, 1), (2, 0, 1)], 3)
assert schedule_agents_global(
    [[ToolCall(0, 2, ()), ToolCall(1, 3, (0,)), ToolCall(2, 1, (0,))],
     [ToolCall(0, 4, ()), ToolCall(1, 2, (0,))],
     [ToolCall(0, 2, ())]], 2
) == ([(0, 0, 0), (0, 1, 0), (2, 0, 1), (4, 0, 2), (5, 1, 1), (5, 2, 0)], 7)

# Empty input at every level: no calls anywhere, and an agent that itself has no calls.
assert schedule_agent([], 1) == ([], 0)
assert schedule_agents_independently([], []) == ([], 0)
assert schedule_agents_global([], 1) == ([], 0)
assert schedule_agents_global([[]], 1) == ([], 0)


def brute_force_schedule(agents, capacity, max_ticks=5000):
    """Independent of _event_driven_schedule: scans one time unit at a time and rebuilds its own
    dependency bookkeeping from scratch, instead of jumping to event times."""
    flat = [(a, c) for a, calls in enumerate(agents) for c in calls]
    n = len(flat)
    finished_ids = {a: set() for a, _ in flat}
    started = [False] * n
    running_until = {}
    starts = []
    makespan = 0
    free, scheduled, t = capacity, 0, 0
    while scheduled < n:
        if t > max_ticks:
            raise RuntimeError("instance too large for the per-tick checker")
        for i in [i for i, ft in running_until.items() if ft == t]:
            del running_until[i]
            free += 1
            a, c = flat[i]
            finished_ids[a].add(c.tool_id)
        ready_now = sorted(
            (i for i in range(n)
             if not started[i] and all(d in finished_ids[flat[i][0]] for d in flat[i][1].deps)),
            key=lambda i: (flat[i][0], flat[i][1].tool_id),   # NOTE: by id, never by list position
        )
        for i in ready_now:
            if free == 0:
                break
            a, c = flat[i]
            starts.append((t, a, c.tool_id))
            started[i] = True
            free -= 1
            scheduled += 1
            running_until[i] = t + c.duration
            makespan = max(makespan, t + c.duration)
        if scheduled == n:
            break
        if not running_until:
            raise CycleError("some tool calls can never become ready")
        t += 1
    return starts, makespan


def random_instance(rng, max_agents=4, max_tasks=6, max_dur=4):
    agents = []
    total = 0
    for _ in range(rng.randint(1, max_agents)):
        n_tasks = rng.randint(1, max_tasks)
        calls = []
        for tid in range(n_tasks):
            n_deps = rng.randint(0, min(2, tid))
            deps = tuple(sorted(rng.sample(range(tid), n_deps))) if n_deps else ()
            calls.append(ToolCall(tid, rng.randint(1, max_dur), deps))
        rng.shuffle(calls)          # list position deliberately disagrees with tool_id
        agents.append(calls)
        total += n_tasks
    capacity = rng.randint(1, total)
    return agents, capacity


def assert_work_conserving(agents, capacity, starts, makespan):
    """Replays `starts` alone: at no instant may a slot sit free while a call whose dependencies are
    all finished has not started. Returns True if the cap ever held a ready call back."""
    flat = [(a, c) for a, calls in enumerate(agents) for c in calls]
    dur = {(a, c.tool_id): c.duration for a, c in flat}
    deps = {(a, c.tool_id): c.deps for a, c in flat}
    start_of = {(a, tid): st for st, a, tid in starts}
    finish_of = {k: st + dur[k] for k, st in start_of.items()}
    contested = False
    for tt in range(makespan + 1):
        running = sum(1 for k, st in start_of.items() if st <= tt < finish_of[k])
        free_now = capacity - running          # NOTE: `running` already counts whatever started at tt
        eligible_waiting = sum(
            1 for k in start_of
            if start_of[k] > tt and all(finish_of[(k[0], d)] <= tt for d in deps[k])
        )
        # NOTE: "some call started at tt" is far too weak -- with two free slots and three ready calls,
        # starting exactly one of them would pass that and still idle a slot.
        assert free_now == 0 or eligible_waiting == 0, (tt, free_now, eligible_waiting)
        contested |= eligible_waiting > 0
    return contested


# 300 random instances of Part 3 against an independent per-tick brute force, plus the work-conserving
# invariant on each, and three separate coverage counts: simultaneous starts, instances where the cap
# actually held a ready call back, and instances where list position disagrees with tool_id.
rng = random.Random(12345)
trials = 300
simultaneous = contested = shuffled = 0
for _ in range(trials):
    agents, capacity = random_instance(rng)
    fast_starts, fast_makespan = schedule_agents_global(agents, capacity)
    slow_starts, slow_makespan = brute_force_schedule(agents, capacity)
    assert fast_starts == slow_starts, (agents, capacity, fast_starts, slow_starts)
    assert fast_makespan == slow_makespan, (agents, capacity)
    contested += assert_work_conserving(agents, capacity, fast_starts, fast_makespan)
    simultaneous += len({st for st, _, _ in fast_starts}) < len(fast_starts)
    shuffled += any(c.tool_id != i for calls in agents for i, c in enumerate(calls))

assert simultaneous > trials // 4 and contested > trials // 4, (simultaneous, contested)
assert shuffled > trials // 2, shuffled   # position != tool_id often, so the tie-break key is pinned
print(f"{trials} random instances agree with the brute force; {simultaneous} had simultaneous starts, "
      f"{contested} held a ready call back for want of a slot, {shuffled} had shuffled list positions")

# Parts 1 and 2 against the same brute force: one agent alone, and every agent scheduled alone and
# merged by start time. Neither reduces to Part 3, so neither is covered by the loop above.
for _ in range(trials):
    agents, _unused = random_instance(rng)
    caps = [rng.randint(1, len(calls)) for calls in agents]
    assert schedule_agent(agents[0], caps[0]) == brute_force_schedule([agents[0]], caps[0])
    merged, span = [], 0
    for a, (calls, cap) in enumerate(zip(agents, caps)):
        one_starts, one_makespan = brute_force_schedule([calls], cap)
        merged += [(st, a, tid) for st, _zero, tid in one_starts]
        span = max(span, one_makespan)
    merged.sort()
    assert schedule_agents_independently(agents, caps) == (merged, span), (agents, caps)
print(f"{trials} random instances agree for Part 1 and Part 2 as well")

# Cycle detection, swept rather than spot-checked: random dependency relations on four calls of one
# agent, self-loops included, against an independent DFS colouring. A false alarm on an acyclic
# instance would fail here just as loudly as a missed cycle.
def dfs_has_cycle(deps):
    colour = [0] * len(deps)

    def visit(u):
        colour[u] = 1
        for v in deps[u]:
            if colour[v] == 1 or (colour[v] == 0 and visit(v)):
                return True
        colour[u] = 2
        return False

    return any(colour[u] == 0 and visit(u) for u in range(len(deps)))


rng3 = random.Random(77)
pairs = [(i, j) for i in range(4) for j in range(4)]
cyclic_seen = acyclic_seen = 0
for _ in range(3000):
    deps = [[] for _ in range(4)]
    for i, j in rng3.sample(pairs, rng3.randint(0, 6)):
        deps[i].append(j)
    calls = [ToolCall(i, rng3.randint(1, 3), tuple(deps[i])) for i in range(4)]
    rng3.shuffle(calls)
    want = dfs_has_cycle(deps)
    try:
        schedule_agent(calls, rng3.randint(1, 4))
        got = False
    except CycleError:
        got = True
    assert got == want, (deps, want, got)
    cyclic_seen += want
    acyclic_seen += not want
assert cyclic_seen > 1000 and acyclic_seen > 500, (cyclic_seen, acyclic_seen)

# ... and a cycle sharing an instance with an otherwise perfectly schedulable agent: the engine must
# still raise after it has already started and retired that agent's work, not return a partial schedule.
mixed = [
    [ToolCall(0, 1, deps=(1,)), ToolCall(1, 1, deps=(0,))],
    [ToolCall(0, 1, deps=())],
]
for run in (lambda: schedule_agents_global(mixed, capacity=2),
            lambda: schedule_agents_independently(mixed, [1, 1])):
    try:
        run()
        assert False, "expected CycleError"
    except CycleError:
        pass
print(f"cycle detection agrees with a DFS on {cyclic_seen + acyclic_seen} relations "
      f"({cyclic_seen} cyclic, {acyclic_seen} acyclic)")

# Performance sanity check near the stated limits: N = 2 * 10**5 calls, E close to 5 * 10**5 edges.
rng2 = random.Random(999)
big_agents = []
n_total = e_total = 0
for _ in range(2000):
    n_tasks = 100
    calls = []
    for tid in range(n_tasks):
        n_deps = min(2, tid)
        deps = tuple(sorted(rng2.sample(range(tid), n_deps))) if n_deps else ()
        e_total += len(deps)
        calls.append(ToolCall(tid, rng2.randint(1, 10**9), deps))
    big_agents.append(calls)
    n_total += n_tasks

t0 = _time.perf_counter()
big_starts, big_makespan = schedule_agents_global(big_agents, capacity=50_000)
elapsed = _time.perf_counter() - t0
assert len(big_starts) == n_total == 200_000
print(f"N={n_total}, E={e_total}, elapsed={elapsed:.2f}s, makespan={big_makespan}")
assert elapsed < 10   # order-of-magnitude guard; the exact seconds vary with the machine
```

</details>

</details>
