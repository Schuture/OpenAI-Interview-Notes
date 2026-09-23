# 带依赖的工具调用调度

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 | 轮次 |
| --- | --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 中等 | SWE · RE · Infra Eng | scheduling, dag, simulation, concurrency | 3 个部分 | 电话面 |
<!-- meta:end -->

## 题目

一个 agent 框架同时运行 $A$ 个 agent，编号 $0, \dots, A - 1$。第 $a$ 个 agent 会发起一批固定数量的
*工具调用*（tool call）——写代码、跑测试、跑 lint 之类——在这个 agent 内部编号为 $0, \dots, T_a - 1$。
每个工具调用都有一个 1 到 $10^9$ 之间的整数*执行时长*（duration），以及一个（可能为空的）*依赖*
列表：依赖项是同一个 agent 里其他工具调用的编号，这些调用必须先跑完。依赖关系里可能有环：只要有
任何一个工具调用因为直接或间接依赖到一个环而永远跑不起来，下面每个函数都要抛出 `CycleError`，
而不是返回一份调度。

时间按整数向前推进。一个调度方案要给每个工具调用指定一个*开始时刻*，并遵守下面的规则：

- 一个工具调用从它的开始时刻起占用一个并发*槽位*，直到（但不包含）`start_time + duration`；槽位被
  占用期间，不能分给别的调用。
- 一个调用可以在时刻 $t$ 开始，当且仅当它每一个依赖的 `start_time + duration` 都不超过 $t$：一个
  依赖在时刻 $t$ 完成，它解锁的后继从 $t$ 起就可以开始，但不能早于 $t$。
- 某一时刻如果同时有调用完成、又有调用可以开始，规则规定先把每一个完成的调用处理掉——释放它的槽位，
  并检查这是否解锁了某个后继——等所有完成的调用都处理完了，才把新的调用放进空出来的槽位。
- 调用一旦开始就必须执行到完成，中途不能被打断：没有抢占。
- 只要还有能做的活，就不允许槽位空闲：任何时刻都不允许出现“一个槽位空着，同时还有某个依赖已全部
  满足的调用没开始”——这样的槽位在这一刻统统要被填满，一个都不能剩（调度是*work-conserving*的）。
- 当空槽位不够分给所有满足开始条件的调用，或者干脆有好几个调用同时开始，都按 `(agent_id, tool_id)`
  升序打破并列。

下面每个 Part 都返回被启动的调用，格式是 `(start_time, agent_id, tool_id)` 三元组，先按 `start_time`
排序，相同再按 `(agent_id, tool_id)` 排序；此外还要返回*makespan*：全部调用里 `start_time + duration`
的最大值（如果压根没有调用，记为 0）。

```py
from typing import NamedTuple, Sequence

class ToolCall(NamedTuple):
    tool_id: int
    duration: int              # 1 .. 10**9
    deps: Sequence[int] = ()   # other tool_id's belonging to the SAME agent, all required first

class CycleError(Exception):
    """Some tool calls can never run: their dependencies form a cycle."""
```

### Part 1 —— 单个 agent 自己的工具调用

单个 agent 提交一串 `ToolCall`，`0, ..., len(calls) - 1` 里的每个整数都恰好作为某个调用的 `tool_id`
出现一次（调用在列表里的位置不必等于它的 `tool_id`）。这个 agent 自己的并发上限 `capacity` 是一个
正整数；上限超过 `len(calls)` 只会让一些槽位始终空着。实现 `schedule_agent`。

```py
from typing import List, Tuple

def schedule_agent(calls: List[ToolCall], capacity: int) -> Tuple[List[Tuple[int, int, int]], int]:
    """Every triple in the returned list has agent_id == 0. Returns ([], 0) for an empty `calls`."""
```

例子，`capacity = 1`，三个调用——`ToolCall(0, 2)`、`ToolCall(1, 1)`、`ToolCall(2, 1, deps=(0,))`：

```text
schedule_agent(calls, 1) == ([(0, 0, 0), (2, 0, 1), (3, 0, 2)], 4)
```

调用 1 没有依赖，从时刻 0 起就已就绪，但唯一的槽位被调用 0 占到时刻 2，所以调用 1 要到那时才开始；
调用 2 等待调用 0，紧接着在时刻 3 开始。

### Part 2 —— 多个 agent，各自有自己的并发上限

现在有 $A$ 个 agent，各自提交自己的 `ToolCall` 列表。agent $a$ 的 `tool_id` 只在 agent $a$ 内部有
意义——两个不同 agent 里相同的 `tool_id` 指的是两个不同的调用。agent $a$ 有它自己的正整数上限
`capacities[a]`，而且任何一个 agent 的调用都不会跟另一个 agent 的调用争用槽位。实现
`schedule_agents_independently`。

```py
def schedule_agents_independently(
    agents: List[List[ToolCall]], capacities: List[int]
) -> Tuple[List[Tuple[int, int, int]], int]:
    """agents[a] is agent a's own calls, scheduled exactly as schedule_agent would schedule them on
    their own under capacities[a]. Returns every started call across every agent, and the largest of
    the per-agent makespans."""
```

例子，agent 0 的调用是 `ToolCall(0, 2)`、`ToolCall(1, 1, deps=(0,))`，`capacities[0] = 1`；agent 1 的
调用是 `ToolCall(0, 1)`、`ToolCall(1, 1)`，`capacities[1] = 2`：

```text
schedule_agents_independently(agents, [1, 2]) == ([(0, 0, 0), (0, 1, 0), (0, 1, 1), (2, 0, 1)], 3)
```

agent 1 的两个调用都没有依赖，上限 2 让它们在时刻 0 同时开始；真正决定总 makespan 的是 agent 0 自己
的 makespan（3），尽管 agent 1 更早结束。

### Part 3 —— 所有 agent 共享同一个上限

跟 Part 2 一样的 $A$ 个 agent，现在共用同一个正整数的全局 `capacity`——任何 agent 的调用都能占用
任何一个空槽位，agent 之间是真正在抢槽位。实现 `schedule_agents_global`。

```py
def schedule_agents_global(
    agents: List[List[ToolCall]], capacity: int
) -> Tuple[List[Tuple[int, int, int]], int]:
    """Same `agents` shape as schedule_agents_independently, but one `capacity` shared by all of
    them."""
```

约束：$1 \le A \le 10^5$；全部调用数 $N = \sum_a \text{len(agents[a])}$ 满足
$N \le 2 \times 10^5$；依赖边总数 $E$ 满足 $E \le 5 \times 10^5$；要求时间 $O((N + E) \log N)$、
空间 $O(N + E)$。

例子，三个 agent，`capacity = 2`：

- agent 0：`ToolCall(0, 2)`、`ToolCall(1, 3, deps=(0,))`、`ToolCall(2, 1, deps=(0,))`
- agent 1：`ToolCall(0, 4)`、`ToolCall(1, 2, deps=(0,))`
- agent 2：`ToolCall(0, 2)`

用 $(a, i)$ 表示 agent $a$ 的调用 $i$，逐步推演：

- $t = 0$：$(0,0)$、$(1,0)$、$(2,0)$ 都没有依赖，都已就绪，但只有 2 个槽位。字典序让 $(0,0)$ 和
  $(1,0)$ 先开始；$(2,0)$ 保持就绪状态，继续等一个槽位。$(0,0)$ 在时刻 2 完成，$(1,0)$ 在时刻 4 完成。
- $t = 2$：$(0,0)$ 完成，空出一个槽位，同时解锁 $(0,1)$ 和 $(0,2)$——它们各自唯一的依赖就是它。此刻
  就绪的有 $(0,1)$、$(0,2)$，还有一直在等的 $(2,0)$；只有一个槽位空着（$(1,0)$ 还在跑）。字典序选中
  $(0,1)$ 开始，它在时刻 5 完成。
- $t = 4$：$(1,0)$ 完成，解锁 $(1,1)$。此刻就绪的有 $(0,2)$、$(1,1)$、$(2,0)$；有一个槽位空着
  （$(0,1)$ 还在跑）。$(0,2)$ 在字典序上胜出，开始运行，时刻 5 完成。
- $t = 5$：$(0,1)$ 和 $(0,2)$ 同时完成，两个槽位都空出来；两者都没有再解锁别的调用。就绪的还剩
  $(1,1)$ 和 $(2,0)$——两个槽位都空，两者同时开始，顺序如上。两者都在时刻 7 完成。
- $t = 7$：全部结束。

```text
schedule_agents_global(agents, 2) == (
    [(0, 0, 0), (0, 1, 0), (2, 0, 1), (4, 0, 2), (5, 1, 1), (5, 2, 0)],
    7,
)
```

注意 $(2,0)$ 在时刻 0 就已经就绪，却在每一次抢槽位时都被更小的 `agent_id` 压下去，一直等到时刻 5
才开始：字典序规则决定的是好几个调用争抢同一个槽位时谁能拿到它，不只是同时开始的几条记录该按什么
顺序打印。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前有一点值得跟面试官确认：抢到一个被争用的槽位所用的 `(agent_id, tool_id)` 顺序，和打印同时
开始的几条记录所用的顺序，是不是同一条规则——下面的代码，以及上面 Part 3 的例子，都把这两件事当作
同一条规则，而不是两条互相独立的规则。

### Part 1

三个 Part 共用同一套引擎：一个*就绪*堆，存放 `(agent_id, tool_id, position)`，里面是依赖已经全部
满足、但还没开始的调用；一个*运行中*堆，存放 `(finish_time, agent_id, tool_id, position)`，里面是
正占着槽位的调用。主循环交替两个阶段——只要就绪堆非空且还有空槽位，就不断把就绪堆里的调用放进空槽位；
否则就直接跳到下一个完成时刻，把在那一刻完成的全部调用释放掉，顺便把它们每一个后继的入度减一。这个
顺序正好就是“先把每一个完成的调用处理掉、解锁它的后继，再开始任何新的调用”：新的调用只能在跳过去
之后、重新进入放置阶段时才会开始。

按每个时间单位往前挪一步也能做，但执行时长可以到 $10^9$，这样时间步数就跟 $N$ 脱钩，可以任意大。
直接跳到下一个完成时刻，则把“宏观步骤”的数量限制在 $N$ 以内（每一步是启动一个调用，或者释放一批
同时完成的调用）；每个宏观步骤要做 $O(\log N)$ 的堆操作，而整个过程里给入度做减法的总开销是
$O(E)$——加起来就是 $O((N + E) \log N)$ 的时间，以及给堆和依赖表用的 $O(N + E)$ 空间。

同一套入度记账顺便就做了题面要求的环检测：如果循环跑到某一步，两个堆都空了，却还有调用没被安排，
那这些调用就永远不可能把入度降到 0，而这恰好等价于它们依赖到了一个环——也就是 Kahn 算法背后的标准
论证。`CycleError` 就在这里抛出，而不是死循环，或者返回一份不完整的调度。

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

每个 agent 自己的调度跟别的 agent 完全无关，所以 `schedule_agents_independently` 只是把
`schedule_agent` 对每个 agent 各调用一次——调用时把这个 agent 自己的 `agent_id` 打到每个调用上，
让输出的三元组是对的——再把结果合并起来。跟 Part 1、Part 3 不同，这次合并需要显式排序：每次调用
`_event_driven_schedule` 产出的开始时间自己就是有序的，但把两条（或更多条）*互相独立*的时间线按
`start_time` 交织在一起，不是任何一次调用自己会做的事。

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

一个全局上限意味着所有 agent 的调用都从同一批槽位里取用，所以像 Part 2 那样各自调度再合并，只要
同时有两个 agent 都有调用就绪，就会出错：引擎必须同时看到所有 agent 的调用，才能决定槽位给谁。把
所有 agent 的调用合成一个列表、共用一个 `capacity` 交给 `_event_driven_schedule`，做的正是这件事；
之后也不需要再单独合并一次，因为它走的是同一条时间线，产出时已经按要求的顺序把所有 agent 的开始
记录交织好了。

```python
def schedule_agents_global(agents: List[List[ToolCall]], capacity: int):
    tasks = [(agent_id, call) for agent_id, calls in enumerate(agents) for call in calls]
    return _event_driven_schedule(tasks, capacity)
```

### 追问

- 真实的执行器沿用同一套入度计数：由最后完成的那个依赖在锁里把计数减一，减到 0 才把这个调用提交
  给线程池，上限就由 `capacity` 个工作线程本身来管。反过来让每个任务先在依赖的 `threading.Event`
  上等，一旦有 `capacity` 个任务都卡在还排在它们后面的依赖上就会死锁；而且真实的完成时刻不会落在
  同一个瞬间，上面的字典序规则只剩下“某个工作线程空出来时，在当下就绪的那几个里挑一个”的作用。
- 例子里 $(2, 0)$ 等了很久并不是 bug：字典序规则是确定性的，但不公平；它只会推迟一个调用，不会让它
  永远等不到——实例是有限的，每个开始的调用都会结束，所以每个调用迟早都会开始。
- 再叠加一层“每个 agent 自己的上限”，单个就绪堆就不够用了：堆顶那个调用可能属于一个已经打满自己
  上限的 agent，所以要给每个 agent 各配一个就绪堆，再在还没打满上限的那些 agent 里取最小的一个。

<details>
<summary>验证代码（可运行）</summary>

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
