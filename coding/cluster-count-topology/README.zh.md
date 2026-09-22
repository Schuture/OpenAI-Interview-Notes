# 集群节点计数与拓扑（树上消息传递）

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★★☆ | 中等 | SWE | tree, message-passing, distributed-systems, idempotency | 3 个部分 |
<!-- meta:end -->

## 题目

一个集群的机器组成一棵有根树。每台机器只能给自己的*父节点*或某个*子节点*发消息，机器之间没有别的通信通道，
尤其是两个兄弟节点不能直接对话。通信是异步的：发送一条消息只是把它放进队列，接收方的 `receive_message`
会在之后某个不确定的时刻才被调用。本题基于下面这个模拟网络，完整给出，后面每个 Part 都会用到它。

```python
import random


class Network:
    """A minimal asynchronous network. send_async_message only enqueues a message; nothing is
    delivered synchronously. run() repeatedly takes every message currently queued, shuffles it
    with the network's own random generator (delivery order has nothing to do with send order),
    and calls receive_message on each target in that shuffled order. A handler invoked while a
    round is being delivered may itself call send_async_message; those new messages join the queue
    for the NEXT round, never the one being delivered, so a message can never be processed before
    it is sent. run() stops once the queue is empty, or after max_rounds as a safety net against a
    handler that keeps sending forever."""

    def __init__(self, seed=0):
        self.nodes = {}
        self._queue = []                 # list of (to_id, from_id, message), not yet delivered
        self._rng = random.Random(seed)  # NOTE: seeded, so a run is reproducible for a fixed seed

    def register(self, node):
        self.nodes[node.node_id] = node

    def send_async_message(self, from_id, to_id, message):
        self._queue.append((to_id, from_id, message))

    def run(self, max_rounds=10_000):
        rounds = 0
        while self._queue and rounds < max_rounds:
            batch, self._queue = self._queue, []       # NOTE: freeze this round's batch first, so
            self._rng.shuffle(batch)                    #       sends made while delivering it land
            for to_id, from_id, message in batch:       #       in self._queue for the NEXT round
                self.nodes[to_id].receive_message(from_id, message)
            rounds += 1
        return rounds


class Node:
    """Given skeleton, subclassed for every part. node_id is this machine's id, parent_id its
    parent's id (None only for the root), children_ids the ids of its children, and network the
    Network instance to send through."""

    def __init__(self, node_id, parent_id, children_ids, network):
        self.node_id = node_id
        self.parent_id = parent_id
        self.children_ids = list(children_ids)
        self.network = network
        network.register(self)

    def send(self, to_id, message):
        self.network.send_async_message(self.node_id, to_id, message)

    def receive_message(self, from_id, message):
        raise NotImplementedError

    def on_tick(self):
        """Called once per round by UnreliableNetwork.run() (Part 3); unused before that, and the
        base Network above never calls it."""
```

`message` 可以是你选择的任意 Python 对象——字符串、元组、一个小 dict 都可以；这个模拟环境完全不检查也不序列化它，
格式由你自己决定。启动一次查询的那次调用，是直接在根节点上调用 `receive_message(None, ...)`，
就好像这条消息是“从集群外部”发来的一样；`from_id` 只在这一次调用时为 `None`，来自集群内其他机器的消息永远不会是 `None`。

下面例子里用到的树有 8 台机器：

```text
        A
     /  |  \
    B   C   D
   / \      |
  E   F     G
            |
            H
```

### Part 1 —— 统计集群机器数

在一个 `Node` 子类上实现 `receive_message`，使得 `Network.run()` 返回之后，根节点自己的 `result`
属性保存集群里机器的总数（包含根节点本身）。

- 计数从根节点收到最初的 `receive_message(None, ...)` 调用时开始。
- 没有子节点的机器立即应答，不需要联系其他机器。
- 有子节点的机器把请求转发给全部子节点，等所有子节点都应答之后，把自己算作 1 加进去，
  再把总数汇报给自己的父节点——如果自己就是根节点，则把总数存进 `result`，不再发送。
- 子节点应答的先后顺序任意，代码不能假设某个特定顺序。
- 如果根节点自己没有子节点，计数结果就是 1。

```py
class CountingNode(Node):
    def receive_message(self, from_id: str | None, message) -> None:
        """After Network.run() returns, self.result on the ROOT holds the number of machines in
        the whole cluster."""
```

在上面这棵树上：`A` 把请求转发给 `B`、`C`、`D`。`C` 是叶子，立刻应答 `1`。`B` 把请求转发给 `E` 和 `F`，
两者都是叶子；等两个都应答之后（不论谁先到），`B` 汇报 `1 + 1 + 1 = 3` 给 `A`。`D` 把请求转发给 `G`，
`G` 再转发给 `H`；`H` 应答 `1`，`G` 汇报 `1 + 1 = 2`，`D` 汇报 `1 + 2 = 3`。等 `A` 收齐来自 `B`、`C`、`D`
的应答（不论先后），计算出 `1 + 3 + 1 + 3 = 8`，这就是 `A.result`。

### Part 2 —— 汇总拓扑结构

采用和 Part 1 相同的“向下请求、向上汇聚”过程，但汇总的是整棵树的形状，而不是个数。
用嵌套元组 `(x, [t_1, ..., t_k])` 表示以 id 为 `x` 的机器为根、子树依次为 `t_1, ..., t_k`
（顺序与 `children_ids` 一致）的子树；叶子的表示是 `(x, [])`。`Network.run()` 返回之后，
根节点的 `result` 属性必须保存整个集群的这个元组。

```py
class TopologyNode(Node):
    def receive_message(self, from_id: str | None, message) -> None:
        """After Network.run() returns, self.result on the ROOT holds (node_id, [child topologies])
        for the whole cluster, children listed in the order of children_ids."""
```

在上面这棵树上，结果是
`("A", [("B", [("E", []), ("F", [])]), ("C", []), ("D", [("G", [("H", [])])])])`。

### Part 3 —— 消息重复与丢失

现在请求和响应都可能被投递不止一次，也可能一次都没有投递到。`Network` 增加两个相互独立的、按消息计算的概率，
以及一个逻辑时钟，完整给出如下：

```python
class UnreliableNetwork(Network):
    """A message is independently dropped with probability drop_prob (never delivered at all) and,
    if not dropped, duplicated with probability duplicate_prob (a second, unrelated copy is queued,
    so receive_message runs twice for that one send). After every round -- including one where the
    queue happened to be empty -- on_tick() is called once on every registered node; this is the
    model's only notion of time, and it is what a node uses to notice that a child has been silent
    for too long and resend to it. run() stops once the queue has been empty for
    idle_rounds_to_stop consecutive rounds, or after max_rounds, whichever comes first."""

    def __init__(self, drop_prob=0.0, duplicate_prob=0.0, seed=0):
        super().__init__(seed=seed)
        self.drop_prob = drop_prob
        self.duplicate_prob = duplicate_prob

    def send_async_message(self, from_id, to_id, message):
        if self._rng.random() < self.drop_prob:
            return                                        # NOTE: silently discarded, never queued
        super().send_async_message(from_id, to_id, message)
        if self._rng.random() < self.duplicate_prob:
            super().send_async_message(from_id, to_id, message)   # a second, independent delivery

    def run(self, max_rounds=10_000, idle_rounds_to_stop=30):
        idle, rounds = 0, 0
        while rounds < max_rounds:
            if self._queue:
                batch, self._queue = self._queue, []
                self._rng.shuffle(batch)
                for to_id, from_id, message in batch:
                    self.nodes[to_id].receive_message(from_id, message)
                idle = 0
            else:
                idle += 1
            for node in self.nodes.values():
                node.on_tick()                            # NOTE: ticks even on an idle round, so a
            rounds += 1                                    #       pending timeout still fires
            if idle >= idle_rounds_to_stop and not self._queue:
                break
        return rounds
```

`run()` 无从知道一次查询是否已经完成：它把队列连续 `idle_rounds_to_stop` 轮为空当作结束。被丢弃的消息不会在队列里留下任何东西，
所以一台还在等待应答的机器必须在远少于这个数目的 tick 之内重发，否则 `run()` 会在结果产生之前就返回。

重新实现 Part 1 和 Part 2，使得在 `UnreliableNetwork` 上运行时最终结果依然正确。每次查询都带一个
`request_id`，对这一次调用唯一，由发起者（在根节点上调用 `receive_message(None, ...)` 的那一方）指定。

- 一台机器收到一个它已经算完的 `request_id` 的请求时，必须重发它缓存的那个答案，而不是重新计算。
- 一台机器收到一个它还在处理中的 `request_id` 的请求时，必须忽略这个重复请求，而不是重新开始一次汇聚。
- 一台机器不能把同一个子节点的答案计入两次：对同一个 `request_id`，来自同一个子节点的两次响应不能都被并入总数。
- 如果一台机器在若干个 tick 内都没有收到某个子节点对某个 `request_id` 的响应，就必须只向那一个子节点重发请求，
  而不是向全部子节点重发。

```py
class RobustNode(Node):
    def receive_message(self, from_id: str | None, message) -> None:
        """Same task as Parts 1-2, run over an UnreliableNetwork. Once the query for a given
        request_id has finished, its value is stored in self.results[request_id] on the ROOT;
        correct even when requests or responses are duplicated or dropped."""

    def on_tick(self) -> None:
        """Called once per round by UnreliableNetwork.run(). Resend a request to any child that has
        been pending too long for some request_id."""
```

在上面这棵树上，取 `drop_prob = duplicate_prob = 0.2`，先发起查询（例如
`root.receive_message(None, ("request", "count", "q1"))`），再执行 `network.run()`；网络的随机种子取 0 到 999
中的任何一个，`root.results["q1"]` 都必须等于 `8`，和 Part 1 的结果一致。

## 参考解答

<details>
<summary>展开参考解答</summary>

开始写代码前值得跟面试官确认：是否要支持同一台机器同时处理多个查询（假设要），以及请求状态是否可以永久保留
（假设可以，这只是逻辑练习，不是长期运行的服务）。

### Part 1

Part 1 和 Part 2 的过程相同——向下广播、向上汇聚——只有合并规则不同，所以这个过程只写一次，再按 `query_type` 配上一对函数：
`leaf_value(node)` 给出叶子的贡献，`combine(node, child_values)` 给出子节点（按 `children_ids` 顺序）全部应答之后的结果。

```python
QUERIES = {}   # query_type -> (leaf_value(node), combine(node, child_values in children_ids order))


class QueryNode(Node):
    """Broadcasts a request down the tree and aggregates the answers back up."""

    def __init__(self, node_id, parent_id, children_ids, network):
        super().__init__(node_id, parent_id, children_ids, network)
        self.result = None     # set on the ROOT only, once the query has completed
        self._pending = {}     # query_type -> set of children that have not answered yet
        self._answers = {}     # query_type -> {child_id: value}  NOTE: per child, not a running total

    def _respond(self, query_type, value):
        if self.parent_id is None:
            self.result = value
        else:
            self.send(self.parent_id, ("response", query_type, value))

    def receive_message(self, from_id, message):
        kind = message[0]
        if kind == "request":             # from the parent, or from outside for the root
            _, query_type = message
            leaf_value, _combine = QUERIES[query_type]
            if not self.children_ids:
                self._respond(query_type, leaf_value(self))     # a leaf answers immediately
            else:
                self._pending[query_type] = set(self.children_ids)
                self._answers[query_type] = {}
                for child in self.children_ids:
                    self.send(child, ("request", query_type))
        elif kind == "response":          # from one child
            _, query_type, value = message
            pending = self._pending.get(query_type, ())
            if from_id not in pending:
                return                    # NOTE: not a child we are still waiting on
            self._answers[query_type][from_id] = value
            pending.discard(from_id)
            if not pending:               # every child has now answered
                _, combine = QUERIES[query_type]
                ordered = [self._answers[query_type][c] for c in self.children_ids]
                self._respond(query_type, combine(self, ordered))


QUERIES["count"] = (
    lambda node: 1,
    lambda node, child_counts: 1 + sum(child_counts),
)
CountingNode = QueryNode      # Part 1: start it with ("request", "count")
```

记下每个答案来自哪个子节点、而不是只往一个总数上累加，对可靠网络上的计数没有区别；但 Part 2 要靠它把答案按
`children_ids` 的顺序排好，Part 3 要靠它认出重复的应答。

### Part 2

拓扑查询只需换一对函数：叶子贡献 `(自己的 id, [])`；合并时把节点 id 包在子节点拓扑列表外面，
`ordered` 已按 `children_ids` 排好顺序。

```python
QUERIES["topology"] = (
    lambda node: (node.node_id, []),
    lambda node, child_topologies: (node.node_id, child_topologies),
)
TopologyNode = QueryNode      # Part 2: the same class, started with ("request", "topology")
```

### Part 3

按 `request_id` 保存三份状态：汇聚是否已经 `done`，以及算出的 `value`；尚未应答的子节点集合 `pending`，连同和 `QueryNode`
一样按子节点 id 存放的答案；每个未应答的子节点上一次被请求时的 tick。`RobustNode` 仍然从 `QUERIES` 里取 Part 1、2 的
`leaf_value` 和 `combine`，变的只是包在外面的状态机。

```python
class RobustNode(Node):
    """QueryNode's protocol over the same QUERIES table, with all state kept per request_id."""

    TIMEOUT = 3   # ticks to wait for a child's answer before asking that child again

    def __init__(self, node_id, parent_id, children_ids, network):
        super().__init__(node_id, parent_id, children_ids, network)
        self.results = {}   # request_id -> final value, on the ROOT only
        self._state = {}    # request_id -> see _new_state; kept forever, it is also the cache
        self._tick = 0

    def _new_state(self, query_type):
        return {
            "query_type": query_type,
            "pending": set(self.children_ids),
            "answers": {},   # NOTE: keyed by child_id, never `+=`
            "done": False,
            "value": None,
            "last_sent": {c: self._tick for c in self.children_ids},
        }

    def receive_message(self, from_id, message):
        kind = message[0]
        if kind == "request":
            _, query_type, request_id = message
            state = self._state.get(request_id)
            if state is not None:
                if state["done"]:
                    self._reply(request_id)   # NOTE: cached replay, nothing is recomputed
                return                        # NOTE: still in progress -> ignore, do not restart
            leaf_value, _combine = QUERIES[query_type]
            self._state[request_id] = self._new_state(query_type)
            if not self.children_ids:
                self._finish(request_id, leaf_value(self))
            else:
                for child in self.children_ids:
                    self.send(child, ("request", query_type, request_id))
        elif kind == "response":
            _, request_id, value = message
            state = self._state.get(request_id)
            if state is None or state["done"] or from_id not in state["pending"]:
                return   # NOTE: a repeated or late answer: this child is already recorded
            state["answers"][from_id] = value
            state["pending"].discard(from_id)
            if not state["pending"]:
                _, combine = QUERIES[state["query_type"]]
                ordered = [state["answers"][c] for c in self.children_ids]
                self._finish(request_id, combine(self, ordered))

    def _finish(self, request_id, value):
        state = self._state[request_id]
        state["done"], state["value"] = True, value
        self._reply(request_id)

    def _reply(self, request_id):
        state = self._state[request_id]
        if self.parent_id is None:
            self.results[request_id] = state["value"]
        else:
            self.send(self.parent_id, ("response", request_id, state["value"]))

    def on_tick(self):
        self._tick += 1
        for request_id, state in self._state.items():
            if state["done"]:
                continue
            for child in self.children_ids:   # NOTE: not the set: its order changes from run to run
                if child in state["pending"] and self._tick - state["last_sent"][child] >= self.TIMEOUT:
                    self.send(child, ("request", state["query_type"], request_id))
                    state["last_sent"][child] = self._tick
```

重放的消息不会改变已经记录的状态。重复的请求不会开启第二次广播：汇聚还在进行时被忽略，已经 `done` 时用缓存作答。
接受一条响应的同时，发送它的子节点就从 `pending` 里移除，所以这个子节点之后的每一份响应——网络造成的重复，
或者重试引出的重放——都会被丢弃，每个子节点恰好进入 `combine` 一次。超时只向仍在 `pending` 里的子节点重发；如果丢失的是某台机器自己的响应，
重试到达时它已经 `done`，直接重放 `state["value"]`，不再询问自己的子节点。因此一次运行最终得到的值，只可能是可靠网络上会得到的那个值。

能否结束则是概率问题，不是必然。只要根节点还没有完成，就一定有某台机器还有未应答的子节点，它每 `TIMEOUT` 个 tick 重发一次；
如果网络一直运行下去，查询以概率 1 完成。但 `run()` 在连续 `idle_rounds_to_stop = 30` 轮没有消息之后就会停止，
这至少需要连续十次重发全部丢失，概率的量级是 `drop_prob ** 10`：0.2 时可以忽略（约 $10^{-7}$），0.5 时则不能（约 $10^{-3}$）。
在那棵 8 台机器的树上取 `drop_prob = duplicate_prob = 0.5`，10000 个种子里有 6 个在返回时 `results` 里还没有结果
（但从不出现错误的结果）；改用 `idle_rounds_to_stop=100`，它们全部能完成。

### 追问

- 宕机的机器和只是丢包的机器不同：无论父节点重试多少次，它都不会应答；区分两者需要另一套机制，比如心跳或租约，超出本题范围。
- 深度为 $d$ 的树上，无故障的一次查询需要 $2d$ 轮，最慢路径上每丢一条消息最多再加 `TIMEOUT` 轮。固定的 `TIMEOUT = 3`
  比深子树的往返时间短，所以父节点也会向还没算完的子节点重发（被忽略，无害但浪费）：深度 100 的链在不丢消息时也要发
  3586 条消息，而 200 条就够了。
- 同时进行两个查询无需改代码：`_state`、`results` 都按 `request_id` 存放，调用方只需挑两个不同的 id。

<details>
<summary>验证代码（可运行）</summary>

```python
def random_tree(rng, n):
    """children[i]: ids of the children of node i, numbered 0..n-1 with node 0 as the root."""
    children = {i: [] for i in range(n)}
    for i in range(1, n):
        parent = rng.randrange(i)
        children[parent].append(i)
    return children


def chain_tree(n):
    return {i: ([i + 1] if i + 1 < n else []) for i in range(n)}


def star_tree(n):
    return {0: list(range(1, n))} | {i: [] for i in range(1, n)}


def true_count(children, node=0):
    return 1 + sum(true_count(children, c) for c in children[node])


def true_topology(children, node=0):
    return (str(node), [true_topology(children, c) for c in children[node]])


def build_nodes(children, network, cls):
    parent = {}
    for p, kids in children.items():
        for k in kids:
            parent[k] = p
    return {i: cls(str(i), (str(parent[i]) if i in parent else None), [str(c) for c in children[i]], network)
            for i in children}


import random as _random

# Parts 1-2: random trees, a lone node, a chain and a star, against a direct traversal of the same tree.
rng = _random.Random(0)
shapes = [random_tree(rng, n) for n in [1, 2, 3, 5, 8, 12]] + [chain_tree(6), star_tree(7), {0: []}]
for children in shapes:
    for seed in range(8):
        network = Network(seed=seed)
        nodes = build_nodes(children, network, QueryNode)
        nodes[0].receive_message(None, ("request", "count"))
        network.run()
        assert nodes[0].result == true_count(children)

        network2 = Network(seed=seed + 100)
        nodes2 = build_nodes(children, network2, QueryNode)
        nodes2[0].receive_message(None, ("request", "topology"))
        network2.run()
        assert nodes2[0].result == true_topology(children)

# Part 3: the same kinds of tree over UnreliableNetwork, several (drop_prob, duplicate_prob) pairs and seeds.
rng = _random.Random(1)
shapes3 = [random_tree(rng, n) for n in [1, 2, 3, 5, 9, 14]] + [chain_tree(7), star_tree(6)]
for children in shapes3:
    for drop, dup in [(0.1, 0.1), (0.2, 0.3), (0.3, 0.2)]:
        for seed in range(6):
            network = UnreliableNetwork(drop_prob=drop, duplicate_prob=dup, seed=seed)
            nodes = build_nodes(children, network, RobustNode)
            rid = f"count-{seed}"
            nodes[0].receive_message(None, ("request", "count", rid))
            assert network.run(max_rounds=5000) < 5000   # did not hit the safety net
            assert nodes[0].results[rid] == true_count(children)

            network2 = UnreliableNetwork(drop_prob=drop, duplicate_prob=dup, seed=seed + 1000)
            nodes2 = build_nodes(children, network2, RobustNode)
            rid2 = f"topo-{seed}"
            nodes2[0].receive_message(None, ("request", "topology", rid2))
            network2.run(max_rounds=5000)
            assert nodes2[0].results[rid2] == true_topology(children)

# The examples of the problem statement, on the 8-machine tree.
EXAMPLE = {"A": ["B", "C", "D"], "B": ["E", "F"], "C": [], "D": ["G"], "E": [], "F": [], "G": ["H"], "H": []}
EXAMPLE_TOPOLOGY = ("A", [("B", [("E", []), ("F", [])]), ("C", []), ("D", [("G", [("H", [])])])])


def build_example(network, cls):
    parent = {c: p for p, kids in EXAMPLE.items() for c in kids}
    return {x: cls(x, parent.get(x), EXAMPLE[x], network) for x in EXAMPLE}["A"]


for seed in range(20):
    network = Network(seed=seed)
    root = build_example(network, CountingNode)
    root.receive_message(None, ("request", "count"))
    assert network.run() == 6 and root.result == 8   # depth 3 -> 2 * 3 rounds
    network = Network(seed=seed)
    root = build_example(network, TopologyNode)
    root.receive_message(None, ("request", "topology"))
    network.run()
    assert root.result == EXAMPLE_TOPOLOGY


def early_stops(drop, dup, seeds, timeout=RobustNode.TIMEOUT, **run_kwargs):
    """Number of seeded count queries on the example tree for which run() returns before the root has a
    result. A wrong result fails the assert instead."""
    node_class = type("RobustNodeWithTimeout", (RobustNode,), {"TIMEOUT": timeout})
    missing = 0
    for seed in seeds:
        network = UnreliableNetwork(drop_prob=drop, duplicate_prob=dup, seed=seed)
        root = build_example(network, node_class)
        root.receive_message(None, ("request", "count", "q1"))
        network.run(**run_kwargs)
        assert root.results.get("q1", 8) == 8
        missing += "q1" not in root.results
    return missing


assert early_stops(0.2, 0.2, range(1000)) == 0   # the Part 3 example
assert early_stops(0.5, 0.5, range(10_000)) == 6   # 30 silent rounds in a row do happen at 0.5
assert early_stops(0.5, 0.5, range(10_000), idle_rounds_to_stop=100) == 0
assert early_stops(0.2, 0.2, range(2000), timeout=10) == 6   # a retry interval too close to 30

big_tree = random_tree(_random.Random(2), 300)   # heavy loss on a large tree, with a stop rule to match
for seed in range(5):
    network = UnreliableNetwork(drop_prob=0.5, duplicate_prob=0.5, seed=seed)
    nodes = build_nodes(big_tree, network, RobustNode)
    nodes[0].receive_message(None, ("request", "topology", "big"))
    network.run(idle_rounds_to_stop=200)
    assert nodes[0].results["big"] == true_topology(big_tree)

for seed in range(50):   # two queries in flight at once
    network = UnreliableNetwork(drop_prob=0.3, duplicate_prob=0.3, seed=seed)
    root = build_example(network, RobustNode)
    root.receive_message(None, ("request", "count", "c"))
    root.receive_message(None, ("request", "topology", "t"))
    network.run()
    assert root.results == {"c": 8, "t": EXAMPLE_TOPOLOGY}


class ManualNetwork(Network):
    """Delivers nothing on its own: the test picks which queued message arrives, or loses it."""

    def take(self, to_id):
        index = next(i for i, m in enumerate(self._queue) if m[0] == to_id)
        return self._queue.pop(index)

    def deliver(self, to_id, copies=1):
        to_id, from_id, message = self.take(to_id)
        for _ in range(copies):
            self.nodes[to_id].receive_message(from_id, message)


# The four rules of Part 3, one at a time, on the tree 0 -> 1 -> {2, 3}.
network = ManualNetwork()
nodes = build_nodes({0: [1], 1: [2, 3], 2: [], 3: []}, network, RobustNode)
REQUEST = ("request", "count", "r1")
nodes[0].receive_message(None, REQUEST)
nodes[0].receive_message(None, REQUEST)   # repeated start while in progress
assert network._queue == [("1", "0", REQUEST)]
network.deliver("1", copies=2)   # duplicated request at node 1: one broadcast
assert sorted(network._queue) == [("2", "1", REQUEST), ("3", "1", REQUEST)]
network.deliver("2", copies=2)   # leaf 2 answers, then replays its cached answer
assert network._queue.count(("1", "2", ("response", "r1", 1))) == 2
network.deliver("1"), network.deliver("1")   # both copies reach node 1: counted once
assert nodes[1]._state["r1"]["answers"] == {"2": 1} and nodes[1]._state["r1"]["pending"] == {"3"}
network.take("3")   # the request to leaf 3 is lost ...
for _ in range(RobustNode.TIMEOUT):
    nodes[1].on_tick()
assert network._queue == [("3", "1", REQUEST)]   # ... and resent to leaf 3 alone
network.deliver("3"), network.deliver("1")
assert network.take("0") == ("0", "1", ("response", "r1", 3))   # node 1 is done; its response is lost
for _ in range(RobustNode.TIMEOUT):
    nodes[0].on_tick()
network.deliver("1")   # the root's retry reaches a finished node 1,
assert network._queue == [("0", "1", ("response", "r1", 3))]   # which replays without asking 2 and 3 again
network.deliver("0", copies=2)   # a late second copy changes nothing
nodes[0].receive_message("1", ("response", "r1", 99))
assert nodes[0].results == {"r1": 4}
for _ in range(50):
    for node in nodes.values():
        node.on_tick()
assert network._queue == []   # nobody retries once everything is done


class CountingNetwork(UnreliableNetwork):
    sent = 0

    def send_async_message(self, from_id, to_id, message):
        self.sent += 1
        super().send_async_message(from_id, to_id, message)


network = CountingNetwork()   # no loss, no duplication
nodes = build_nodes(chain_tree(101), network, RobustNode)
nodes[0].receive_message(None, ("request", "count", "deep"))
network.run()
assert nodes[0].results["deep"] == 101
assert network.sent == 3586   # 200 would do: the rest are premature retries


class NaiveCountNode(Node):
    """None of RobustNode's bookkeeping: every request is forwarded again and every response is added
    to a running total, with no memory of which child has already answered."""

    def __init__(self, node_id, parent_id, children_ids, network):
        super().__init__(node_id, parent_id, children_ids, network)
        self.result = None
        self._total = 1
        self._remaining = len(children_ids)

    def receive_message(self, from_id, message):
        if message == "request":
            if not self.children_ids:
                self.send(self.parent_id, "response:1")
            else:
                for child in self.children_ids:
                    self.send(child, "request")
        else:
            self._total += int(message.split(":")[1])
            self._remaining -= 1
            if self._remaining <= 0:
                if self.parent_id is None:
                    self.result = self._total
                else:
                    self.send(self.parent_id, f"response:{self._total}")


naive_children = {0: [1, 2, 3], 1: [], 2: [4], 3: [], 4: []}   # 5 machines
network = UnreliableNetwork(drop_prob=0.0, duplicate_prob=0.1, seed=0)
nodes = build_nodes(naive_children, network, NaiveCountNode)
nodes[0].receive_message(None, "request")
network.run()
assert true_count(naive_children) == 5
# In this seeded run a single message is duplicated, the request 2 -> 4. Leaf 4 answers twice; node 2 adds
# both and reports twice (2, then 3); the root adds both reports: 1 + 1 + 1 + 2 + 3.
assert nodes[0].result == 8
```

</details>

</details>
