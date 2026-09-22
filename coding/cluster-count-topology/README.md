# Cluster Node Count & Topology (Tree Messaging)

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★★☆ | Medium | SWE | tree, message-passing, distributed-systems, idempotency | 3 parts |
<!-- meta:end -->

## Problem

A cluster's machines form a rooted tree. Each machine can send a message only to its *parent* or to
one of its *children*; there is no other channel between machines, and in particular two siblings
cannot talk directly. Communication is asynchronous: sending a message only queues it, and the
receiving machine's `receive_message` runs at some later, unpredictable time. The exercise runs on
the following simulated network, given here in full and used by every part below.

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

A `message` can be any Python object you choose — a string, a tuple, a small dict; this simulation
never inspects or serialises it, so its shape is entirely up to you. The process that starts a query
calls `receive_message(None, ...)` directly on the root, exactly as if it were a message "from
outside the cluster"; `from_id` is `None` only for that one call, never for a message from another
machine.

The tree used in the examples below has 8 machines:

```text
        A
     /  |  \
    B   C   D
   / \      |
  E   F     G
            |
            H
```

### Part 1 — Counting the cluster

Implement `receive_message` on a `Node` subclass so that, once `Network.run()` returns, the root's
own `result` attribute holds the number of machines in the cluster, including the root itself.

- The count starts when the root receives the initial `receive_message(None, ...)` call.
- A machine with no children answers immediately, without contacting anyone.
- A machine with children forwards the request to all of them and waits until every one of them has
  answered before adding 1 for itself and reporting the total to its own parent — or, if it is the
  root, storing it in `result` instead of sending it anywhere.
- Children may answer in any order, and the code must not assume a particular one.
- If the root itself has no children, the count is 1.

```py
class CountingNode(Node):
    def receive_message(self, from_id: str | None, message) -> None:
        """After Network.run() returns, self.result on the ROOT holds the number of machines in
        the whole cluster."""
```

On the tree above: `A` forwards to `B`, `C`, `D`. `C` is a leaf and answers `1` right away. `B`
forwards to `E` and `F`, both leaves, and once both have answered — in whichever order they arrive —
reports `1 + 1 + 1 = 3` to `A`. `D` forwards to `G`, which forwards to `H`; `H` answers `1`, `G`
reports `1 + 1 = 2`, and `D` reports `1 + 2 = 3`. Once `A` has heard from `B`, `C` and `D`, in
whatever order, it computes `1 + 3 + 1 + 3 = 8`, which is `A.result`.

### Part 2 — Mapping the topology

Do the same downward-request, upward-aggregation as Part 1, but gather the shape of the whole tree
instead of a count. Represent the subtree rooted at a machine with id `x` and children subtrees
`t_1, ..., t_k`, listed in the same order as `children_ids`, as the nested tuple `(x, [t_1, ...,
t_k])`; a leaf is `(x, [])`. Once `Network.run()` returns, the root's `result` attribute must hold
this tuple for the whole cluster.

```py
class TopologyNode(Node):
    def receive_message(self, from_id: str | None, message) -> None:
        """After Network.run() returns, self.result on the ROOT holds (node_id, [child topologies])
        for the whole cluster, children listed in the order of children_ids."""
```

On the tree above, the result is
`("A", [("B", [("E", []), ("F", [])]), ("C", []), ("D", [("G", [("H", [])])])])`.

### Part 3 — Duplicated and lost messages

Requests and responses can now be delivered more than once, or not at all. `Network` gains two
independent per-message probabilities and a logical clock, given here in full:

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

`run()` cannot tell whether a query has finished: it treats `idle_rounds_to_stop` consecutive rounds
with an empty queue as the end. A dropped message leaves nothing in the queue, so a machine that is
still waiting for an answer has to resend well within that many ticks, or `run()` returns before the
result exists.

Redo Part 1 and Part 2 so the final result is still correct when running on an `UnreliableNetwork`.
Every query now carries a `request_id`, unique to that one invocation, chosen by whoever starts it
(the caller that invokes `receive_message(None, ...)` on the root).

- A machine that receives a request whose `request_id` it has already finished must resend its
  cached answer for that request, not recompute it.
- A machine that receives a request whose `request_id` it is still working on must ignore the
  duplicate rather than starting a second aggregation.
- A machine must not count the same child's answer twice: two responses from the same child for the
  same `request_id` must not both be folded into the total.
- If a machine has not heard back from one of its children for a given `request_id` within some
  number of ticks, it must resend the request to that child alone, not to every child again.

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

On the tree above, with `drop_prob = duplicate_prob = 0.2`, after a start call such as
`root.receive_message(None, ("request", "count", "q1"))` followed by `network.run()`,
`root.results["q1"]` must equal `8`, exactly as in Part 1, for every network seed from 0 to 999.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Confirm with the interviewer whether the same machine ever needs to answer two different queries at
once (assumed yes below, since it costs nothing extra) and whether keeping per-request state forever
is acceptable (assumed yes, this is a logic exercise, not a long-running service).

### Part 1

Parts 1 and 2 are the same shape — broadcast a request down, aggregate the answers back up — with
only the combining rule different, so write that shape once, keyed by a `query_type`, and configure
it with a pair of functions: `leaf_value(node)` for what a childless machine contributes, and
`combine(node, child_values)` for what a machine with children computes once every entry of
`children_ids`, in that order, has answered.

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

Recording which child each answer came from, instead of just adding to a running total, makes no
difference to a count on a reliable network. Part 2 needs it to put the answers back into
`children_ids` order, and Part 3 needs it to recognise a repeated answer.

### Part 2

The topology query needs only a different pair of functions: a leaf contributes its own id with no
children, and combining wraps a node's id around the list of its children's topologies, which
`ordered` above already produces in `children_ids` order.

```python
QUERIES["topology"] = (
    lambda node: (node.node_id, []),
    lambda node, child_topologies: (node.node_id, child_topologies),
)
TopologyNode = QueryNode      # Part 2: the same class, started with ("request", "topology")
```

### Part 3

Three pieces of state are kept per `request_id`: whether the aggregation is already `done`, and
with what `value`; the children still `pending`, together with the answers received so far, keyed by
child id as in `QueryNode`; and, for each pending child, the tick at which it was last asked.
`RobustNode` looks up the same `leaf_value` and `combine` functions in `QUERIES` as Parts 1 and 2 —
only the state machine wrapped around them changes.

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

No replayed message changes what has been recorded. A duplicate request never starts a second broadcast: it is ignored
while the aggregation is in progress and answered from the cache once it is `done`. Accepting a
response removes its sender from `pending`, so every later copy from that child — a network
duplicate, or the replay triggered by a retry — is dropped, and each child enters `combine` exactly
once. A timeout resends only to children still in `pending`; if the lost message was a machine's own
response, the retry reaches a machine that is already `done`, which replays `state["value"]` without
asking its children again. The only value a run can settle on is therefore the one a reliable network
would produce.

Termination holds with high probability, not with certainty. While the root is unfinished, some
machine has a pending child and resends every `TIMEOUT` ticks, so on a network that kept running the
query would finish with probability 1. `run()`, however, gives up after `idle_rounds_to_stop = 30`
silent rounds, which takes at least ten lost resends in a row: on the order of `drop_prob ** 10`,
negligible at 0.2 (about $10^{-7}$) but not at 0.5 (about $10^{-3}$). On the 8-machine tree with
`drop_prob = duplicate_prob = 0.5`, 6 of 10,000 seeds return with no entry in `results` — never
with a wrong one — and with `idle_rounds_to_stop=100` all of them finish.

### Follow-ups

- A crashed machine, as opposed to a merely slow or lossy one, never answers no matter how many times
  its parent retries; telling the two apart needs a separate mechanism such as heartbeats or a lease,
  which is out of scope here.
- On a tree of depth $d$ a fault-free query takes $2d$ rounds, and each lost message on the slowest path
  adds at most `TIMEOUT` more. The fixed `TIMEOUT = 3` is shorter than a deep subtree's round trip, so
  parents also re-ask children that are merely still working (ignored, harmless, but wasteful): a chain
  of depth 100 sends 3,586 messages without any loss, where 200 would do.
- Two queries in flight at once already work unmodified, since `_state` and `results` are both keyed
  by `request_id`; the caller only has to pick two different ids.

<details>
<summary>Checks (runnable)</summary>

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
