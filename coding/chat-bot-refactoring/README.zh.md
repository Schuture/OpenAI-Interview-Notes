# 聊天机器人重构

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 重构 | ★★★☆☆ | 中等 | SWE | refactoring, oop-design, event-driven, testing | 4 个部分 |
<!-- meta:end -->

## 题目

聊天服务把每一条到达的消息都发给一组机器人（bot），它们对斜杠命令（slash command）作出反应。一条消息
包含发送者姓名、正文，以及一个整数时间戳 `now`：从服务运行第一天的午夜起算的分钟数，不会小于上一条
消息的 `now`，所以第一天的 9:00 对应 `540`，第二天的 9:00 对应 `1980`。整个系统不读取系统时钟——`now`
都是由调用方显式传入的。发送一条消息，首先把 `"{sender}: {text}"` 追加到一个共享的日志（log）里，然后
依次让每个机器人查看这条消息的原始文本，各自可能再往同一个日志里追加若干行。命令只在正文的最开头才会
被识别，形式是命令词后面跟一个空格（`/cheer `、`/focus `、`/poll `、`/vote `）；其余部分首尾的空白
字符一律忽略。系统注册了三个机器人。

**CheerBot**

- 匹配形如 `/cheer @<name>` 的命令，其中 `<name>` 是 `@` 后面一个或多个字符；其他形式（没有 `@`，或者
  `@` 后面什么都没有）都不是合法命令。
- 为每个用户名维护一个不断累加的欢呼计数，初始为 0。
- 收到合法命令时，把目标用户的计数加 1，并宣布发送者、目标（保留原样，含开头的 `@`）和新的计数。

**FocusBot**

- 匹配形如 `/focus <n>` 的命令，其中 `<n>` 是一个或多个十进制数字，拼出一个 `>= 1` 的数；其他形式
  （缺失、负数、非数字）都不是合法命令。
- 收到合法命令时，为发送者开启一段在第 `now + n` 分钟结束的专注时段，取代发送者已有的专注时段，并宣布
  发送者和这段时段结束的钟点时间，格式为 `HH:MM`（时段可以跨过午夜：23:50 开始的 20 分钟时段在 00:10
  结束）。
- 与此独立，对*每一条*到达的消息——包括这个机器人自己的命令，以及其他机器人的命令——只要原始文本里
  包含某个用户名作为子串，并且这个用户的专注时段仍在进行（这条消息的 `now` 严格早于时段的结束时刻），
  机器人就为这个用户追加一行提醒，多个用户按他们第一次开启专注时段的先后顺序排列。这些提醒排在这条消息
  所有其他机器人的行之前，并且在同一条消息里的 `/focus` 生效之前就已确定。

**PollBot**

- 匹配形如 `/poll <question> | <option 1> | <option 2> | ...` 的命令：把 `/poll ` 之后的文本按 `|`
  切分，并去掉每一段前后的空白字符；第一段是问题，其余各段是选项。只有选项数不少于 2 个才合法；一条合法
  命令会替换掉当前正在进行的投票（不论有没有人投过票），新投票的选项依次标为 `A`、`B`、`C`、……，票数
  都从 0 开始。会宣布这次投票的发起人（发送者）、问题和带标签的选项列表。
- 匹配形如 `/vote <letter>` 的命令，`<letter>` 与当前进行中的投票的标签做不区分大小写的匹配。只有存在
  进行中的投票、且这个字母匹配它的某个标签时才合法；会给对应选项加一票，并宣布投票人、被选中选项的
  文本，以及每个标签按标签顺序排列的最新票数。
- 不符合上面两条规则的 `/poll`、`/vote` 命令都不被识别。

不满足上面对应机器人合法性规则的命令，不会作为命令得到任何机器人的回应；它的正文仍然和普通消息一样，
参与 FocusBot 的提醒检查。

下面是现有的实现：

```python
cheer_counts = {}
focus_until = {}
poll_state = {}
messages = []


def format_time(t):
    return f"{(t // 60) % 24:02d}:{t % 60:02d}"


def handle_message(name, msg, now):
    messages.append(name + ": " + msg)

    # FocusBot logic: warn if this message mentions someone who is still heads-down
    for user in focus_until:
        end = focus_until[user]
        if user in msg and now < end:
            messages.append("FocusBot: " + user + " is heads-down until " + format_time(end) + ", try again later.")

    # CheerBot logic
    if msg[:7] == "/cheer ":
        target = msg.split(" ", 1)[1].strip()
        if target[:1] == "@" and len(target) > 1:
            username = target[1:]
            if username not in cheer_counts:
                cheer_counts[username] = 0
            cheer_counts[username] += 1
            messages.append(
                "CheerBot: "
                + name
                + " cheers for "
                + target
                + "! "
                + target
                + "'s cheer count is now "
                + str(cheer_counts[username])
                + "."
            )

    # PollBot logic: start a new poll
    if msg[:6] == "/poll ":
        parts = msg[6:].split("|")
        parts = [p.strip() for p in parts]
        question = parts[0]
        options = parts[1:]
        if len(options) >= 2:
            poll_state.clear()
            poll_state["question"] = question
            poll_state["options"] = options
            votes = {}
            for i in range(len(options)):
                votes[chr(65 + i)] = 0
            poll_state["votes"] = votes
            poll_state["author"] = name
            labeled = []
            for i in range(len(options)):
                labeled.append(chr(65 + i) + ") " + options[i])
            messages.append(f"PollBot: {name} started a poll -- {question} [{', '.join(labeled)}]")

    # PollBot logic: vote on the poll in progress
    if msg[:6] == "/vote ":
        letter = msg.split(" ", 1)[1].strip().upper()
        if poll_state and letter in poll_state["votes"]:
            poll_state["votes"][letter] += 1
            idx = ord(letter) - 65
            option_text = poll_state["options"][idx]
            tally_bits = []
            for k in poll_state["votes"]:
                tally_bits.append(k + ": " + str(poll_state["votes"][k]))
            tally = ", ".join(tally_bits)
            messages.append(f"PollBot: {name} voted {letter} ({option_text}). Tally -- {tally}")

    # FocusBot logic: start a focus session
    if msg[:7] == "/focus ":
        arg = msg.split(" ", 1)[1].strip()
        if arg.isdecimal() and int(arg) >= 1:
            minutes = int(arg)
            end = now + minutes
            focus_until[name] = end
            messages.append(
                "FocusBot: " + name + " is heads-down for " + str(minutes) + " min, back at " + format_time(end) + "."
            )
```

它在下面这段脚本上的输出，就是后面各个部分都要保持的“行为不变”的基准：

```python
SCRIPT = [
    ("Maya", "Hello everyone", 540),
    ("Theo", "/focus 20", 545),
    ("Priya", "Hey Theo, quick question", 550),
    ("Noah", "/cheer @Priya", 552),
    ("Sana", "/cheer @Priya", 560),
    ("Leo", "/cheer @Theo", 561),
    ("Maya", "/poll Lunch spot? | Tacos | Pasta | Salad", 600),
    ("Theo", "/vote B", 605),
    ("Priya", "/vote B", 606),
    ("Noah", "/vote c", 607),
    ("Sana", "/vote Z", 608),
    ("Leo", "/focus abc", 609),
    ("Maya", "/cheer bob", 610),
    ("Theo", "/poll Coffee? | OnlyOneOption", 611),
    ("Priya", "/vote B", 612),
]

for sender, text, now in SCRIPT:
    handle_message(sender, text, now)

EXPECTED_LOG = [
    "Maya: Hello everyone",
    "Theo: /focus 20",
    "FocusBot: Theo is heads-down for 20 min, back at 09:25.",
    "Priya: Hey Theo, quick question",
    "FocusBot: Theo is heads-down until 09:25, try again later.",
    "Noah: /cheer @Priya",
    "CheerBot: Noah cheers for @Priya! @Priya's cheer count is now 1.",
    "Sana: /cheer @Priya",
    "CheerBot: Sana cheers for @Priya! @Priya's cheer count is now 2.",
    "Leo: /cheer @Theo",
    "FocusBot: Theo is heads-down until 09:25, try again later.",
    "CheerBot: Leo cheers for @Theo! @Theo's cheer count is now 1.",
    "Maya: /poll Lunch spot? | Tacos | Pasta | Salad",
    "PollBot: Maya started a poll -- Lunch spot? [A) Tacos, B) Pasta, C) Salad]",
    "Theo: /vote B",
    "PollBot: Theo voted B (Pasta). Tally -- A: 0, B: 1, C: 0",
    "Priya: /vote B",
    "PollBot: Priya voted B (Pasta). Tally -- A: 0, B: 2, C: 0",
    "Noah: /vote c",
    "PollBot: Noah voted C (Salad). Tally -- A: 0, B: 2, C: 1",
    "Sana: /vote Z",
    "Leo: /focus abc",
    "Maya: /cheer bob",
    "Theo: /poll Coffee? | OnlyOneOption",
    "Priya: /vote B",
    "PollBot: Priya voted B (Pasta). Tally -- A: 0, B: 3, C: 1",
]
assert messages == EXPECTED_LOG
```

### Part 1 —— 读遗留代码

回答下面的问题，每一条都要落到上面代码的具体行。

1. 追踪脚本中 `("Leo", "/cheer @Theo", 561)` 这次调用。`handle_message` 里哪些代码块会执行、执行顺序
   是怎样的？这条消息明明是欢呼命令而不是专注命令，为什么 FocusBot 那一行会出现在 CheerBot 那一行
   之前？
2. 给出一个具体场景：在同一个进程里，先后从两个不同的测试函数调用 `handle_message`，会让第二个测试
   的结果依赖于第一个测试做了什么，并指出是哪一行（或哪几行）代码造成的。
3. 假设要新增第四个机器人 `PingBot`，由 `/ping` 触发。列出上面这份文件里你需要改动的每一处，并说明
   （如果有的话）是什么机制阻止了两个机器人悄悄抢占同一个命令前缀。
4. 说出两处不经过整个 `handle_message` 就无法单独做单元测试的行为，并解释原因。如果它上方的循环
   （第 15–18 行）在执行到一半时抛出异常，`# CheerBot logic` 之后的那些代码块会发生什么？

### Part 2 —— 机器人接口

把这一个函数换成一组类：每个机器人一个类，共享同一个接口；再加一个聊天室（room），把到达的消息分发给
每一个想看它的、已注册的机器人。原来存在模块级字典里的状态——欢呼计数、专注时段的结束时间、进行中的
投票——都要改成传给各自机器人构造函数的参数；任何机器人都不能读墙上时钟，需要 `now` 的机器人由聊天室
注入一个会被它推进的时钟对象。

```py
class ChatBot(ABC):
    def can_handle(self, sender: str, text: str) -> bool:
        """Whether this bot has anything to say about this message."""

    def handle(self, sender: str, text: str) -> list[str]:
        """The lines this bot appends to the log for this message."""


class Clock:
    """now: minutes since midnight of the first day, never decreasing. ChatRoom.send sets it; bots only read it."""

    def __init__(self, now: int = 0): ...


class ChatRoom:
    def __init__(self, clock: Clock): ...
    def register(self, bot: "ChatBot") -> None: ...
    def send(self, sender: str, text: str, now: int) -> list[str]:
        """Advances clock.now, appends "sender: text", dispatches to every registered bot, returns the log."""


class CheerBot(ChatBot):
    def __init__(self, cheer_counts: dict[str, int]): ...


class FocusBot(ChatBot):
    def __init__(self, clock: Clock, focus_until: dict[str, int]): ...


class PollBot(ChatBot):
    def __init__(self, poll_state: dict): ...
```

实现这些类，使得对任意一串 `(sender, text, now)` 三元组，注册了这三个机器人的 `ChatRoom` 都能逐行
复现 `handle_message` 的日志。这里没有测试套件能帮你发现不一致：自己动手核对——把 `SCRIPT` 分别喂给
`handle_message` 和你的 `ChatRoom`，逐行比较两份日志，而不是把两条代码路径放在一起读、凭直觉相信它们一致。

### Part 3 —— 机器人之间的事件

PollBot 和 CheerBot 之间只能通过在一个共享的事件总线（event bus）上发布（publish）和订阅（subscribe）
事件来互相响应——谁都不能直接调用对方的方法，也不能持有对方的引用。新规则：一旦某个选项的票数达到
3，这次投票立刻结束。PollBot 此后不再接受针对这次投票的任何 `/vote`（之后的 `/vote` 的表现要跟没有
进行中的投票完全一样）；同时 CheerBot 要把这次投票发起人的欢呼计数加 1 并宣布，紧跟在 PollBot 为这次
投票追加的那一行之后：

```text
CheerBot: {author}'s poll reached 3 votes! {author}'s cheer count is now {count}.
```

```py
class Event:
    def __init__(self, type: str, data: dict): ...


class EventBus:
    def subscribe(self, event_type: str, handler) -> None:
        """handler(event) is called for every published event of this type, in subscription order."""

    def publish(self, event: "Event") -> None: ...
```

上面脚本的最后一条消息 `Priya: /vote B`（第 612 分钟）把 B 的票数推到 3。加上新规则之后，日志是
`EXPECTED_LOG` 后面再跟一行：

```text
CheerBot: Maya's poll reached 3 votes! Maya's cheer count is now 1.
```

### Part 4 —— 测试

用标准库的 `unittest`（用普通函数加 `assert` 也可以）：

- 为三个机器人中至少两个写单元测试，每个测试只构造该机器人自己需要的依赖（一个显式的 `Clock`、一个
  显式的 `dict`），不经过 `ChatRoom`，覆盖至少一条核心规则，以及至少一种题目规定会被忽略的输入。
- 写一个端到端测试：新建一个装好三个机器人的 `ChatRoom`，重放 `SCRIPT`，断言得到的日志等于
  `EXPECTED_LOG`。

## 参考解答

<details>
<summary>展开参考解答</summary>

先和面试官确认：格式不对的命令是静默忽略，而不是回复一条错误信息（下面都这样假设）。

### Part 1

1. 第 12 行追加 `"Leo: /cheer @Theo"`。接着是每条消息都要经过的第 15–18 行：`focus_until` 里有 Theo
   在第 545 分钟留下的 `{"Theo": 565}`，`"Theo"` 是正文的子串且 `561 < 565`，于是第 18 行追加提醒。
   然后才轮到第 21 行的 `/cheer ` 判断，追加 CheerBot 那一行。这个顺序完全来自提醒循环写在 CheerBot
   代码块上面：两块读写的状态互不相交，对调它们只会让这两行对调。
2. `cheer_counts`（第 1 行）在整个进程里一直存在，第 25–27 行只会往上加。一个测试调用
   `handle_message("A", "/cheer @X", 0)` 并期望那一行以 `is now 1.` 结尾，单独跑能通过，排在任何给
   `X` 欢呼过的测试之后就会失败。`messages`（第 4 行）同理。
3. 一定要改一处：在第 12–82 行之间加一个 `if msg[:6] == "/ping ":` 代码块，它的位置决定输出的顺序
   （第 1 问）；要保存状态的话，还要在第 1–4 行旁边加一个模块级字典。没有任何东西阻止冲突：第 21、41、
   61、74 行的前缀只是分散在各个 `if` 里的字符串字面量，没有“已占用前缀”的登记表，一个同样判断
   `"/poll "` 的新代码块会和 PollBot 的代码块一起运行，不报任何错。
4. CheerBot 的计数（第 21–38 行）和 PollBot 的投票校验（第 61–71 行）只是同一个函数体里的语句，要运行
   它们只能调用 `handle_message`，连带在共享的全局变量上运行其余代码块。第 15–18 行中途抛出异常时，
   异常会立刻离开 `handle_message`，第 20 行之后的代码块对这条消息都不会运行。

### Part 2

每个模块级字典变成构造函数的参数，每组 `if` 代码块变成一个类，`ChatRoom.send` 按注册顺序遍历机器人。
FocusBot 要最先注册，因为它的提醒排在其他所有行之前；CheerBot 和 PollBot 不会回应同一条消息，它们之间的
顺序无所谓。

```python
from abc import ABC, abstractmethod


def after(prefix, text):
    return text[len(prefix):].strip() if text.startswith(prefix) else None


def hhmm(m):
    return f"{m // 60 % 24:02d}:{m % 60:02d}"


class Clock:
    def __init__(self, now=0):
        self.now = now


class ChatBot(ABC):
    @abstractmethod
    def can_handle(self, sender, text): ...

    @abstractmethod
    def handle(self, sender, text): ...


class ChatRoom:
    def __init__(self, clock):
        self.clock, self.bots, self.log = clock, [], []

    def register(self, bot):
        self.bots.append(bot)

    def send(self, sender, text, now):
        self.clock.now = now
        self.log.append(f"{sender}: {text}")
        for bot in self.bots:  # NOTE: registration order = order of the bots' lines
            if bot.can_handle(sender, text):
                self.log.extend(bot.handle(sender, text))
        return self.log


class CheerBot(ChatBot):
    def __init__(self, cheer_counts):
        self.cheer_counts = cheer_counts

    def _target(self, text):
        arg = after("/cheer ", text) or ""
        return arg if arg.startswith("@") and len(arg) > 1 else None

    def can_handle(self, sender, text):
        return bool(self._target(text))

    def handle(self, sender, text):
        target = self._target(text)
        n = self.cheer_counts[target[1:]] = self.cheer_counts.get(target[1:], 0) + 1
        return [f"CheerBot: {sender} cheers for {target}! {target}'s cheer count is now {n}."]


class FocusBot(ChatBot):
    def __init__(self, clock, focus_until):
        self.clock, self.focus_until = clock, focus_until

    def _minutes(self, text):
        arg = after("/focus ", text) or ""
        return int(arg) if arg.isdecimal() and int(arg) >= 1 else None

    def _mentioned(self, text):  # NOTE: dict order = order of each user's FIRST session
        return [u for u, end in self.focus_until.items() if u in text and self.clock.now < end]

    def can_handle(self, sender, text):
        return bool(self._mentioned(text) or self._minutes(text))

    def handle(self, sender, text):
        lines = [f"FocusBot: {u} is heads-down until {hhmm(self.focus_until[u])}, try again later."
                 for u in self._mentioned(text)]  # NOTE: before this message's own /focus is recorded
        if minutes := self._minutes(text):
            end = self.focus_until[sender] = self.clock.now + minutes
            lines.append(f"FocusBot: {sender} is heads-down for {minutes} min, back at {hhmm(end)}.")
        return lines


class PollBot(ChatBot):
    def __init__(self, poll_state):
        self.poll_state = poll_state  # {} while no poll is in progress

    def _poll(self, text):
        pieces = [p.strip() for p in (after("/poll ", text) or "").split("|")]
        return pieces if len(pieces) >= 3 else None

    def _letter(self, text):
        letter = (after("/vote ", text) or "").upper()
        return letter if self.poll_state and letter in self.poll_state["votes"] else None

    def can_handle(self, sender, text):
        return bool(self._poll(text) or self._letter(text))

    def handle(self, sender, text):
        state, pieces = self.poll_state, self._poll(text)
        if pieces:
            question, *options = pieces
            votes = {chr(65 + i): 0 for i in range(len(options))}
            state.clear()
            state.update(options=options, author=sender, votes=votes)
            listed = ", ".join(f"{k}) {o}" for k, o in zip(votes, options))
            return [f"PollBot: {sender} started a poll -- {question} [{listed}]"]
        letter = self._letter(text)
        state["votes"][letter] += 1
        tally = ", ".join(f"{k}: {v}" for k, v in state["votes"].items())
        return [f"PollBot: {sender} voted {letter} ({state['options'][ord(letter) - 65]}). Tally -- {tally}"]
```

### Part 3

`DecisivePollBot` 和 `RewardedCheerBot` 分别继承 Part 2 的 `PollBot` 和 `CheerBot`，只在 `super()`
前后加代码，Part 2 的类不用改。票数达到 3 时，`DecisivePollBot` 关闭投票并发布带有发起人姓名的
`poll_decided` 事件；`RewardedCheerBot` 的处理函数更新计数、把那一行放进队列，轮到这个机器人时由
`handle` 返回。它必须注册在 `DecisivePollBot` 之后，否则这一行会晚一条消息出现。

`publish` 是同步的：按订阅顺序调用发布开始时已有的处理函数；处理函数里再发布的事件，会在外层事件的下一个
处理函数之前处理完（深度优先）。两个机器人如果一收到对方的事件就再发布，会一直递归下去。

```python
class Event:
    def __init__(self, type, data):
        self.type, self.data = type, data


class EventBus:
    def __init__(self):
        self.handlers = {}

    def subscribe(self, event_type, handler):
        self.handlers.setdefault(event_type, []).append(handler)

    def publish(self, event):  # NOTE: synchronous and depth-first
        for handler in list(self.handlers.get(event.type, [])):
            handler(event)


class DecisivePollBot(PollBot):
    def __init__(self, poll_state, bus):
        super().__init__(poll_state)
        self.bus = bus

    def handle(self, sender, text):
        letter = self._letter(text)  # None unless a valid /vote
        lines = super().handle(sender, text)
        if letter and self.poll_state["votes"][letter] >= 3:
            author = self.poll_state["author"]
            self.poll_state.clear()  # NOTE: close before publishing, so no handler sees it open
            self.bus.publish(Event("poll_decided", {"author": author}))
        return lines


class RewardedCheerBot(CheerBot):
    def __init__(self, cheer_counts, bus):
        super().__init__(cheer_counts)
        self.pending = []
        bus.subscribe("poll_decided", self._on_poll_decided)

    def _on_poll_decided(self, event):
        author = event.data["author"]
        n = self.cheer_counts[author] = self.cheer_counts.get(author, 0) + 1
        self.pending.append(f"CheerBot: {author}'s poll reached 3 votes! {author}'s cheer count is now {n}.")

    def can_handle(self, sender, text):
        return super().can_handle(sender, text) or bool(self.pending)

    def handle(self, sender, text):
        lines = super().handle(sender, text) if self._target(text) else []
        lines, self.pending = lines + self.pending, []
        return lines
```

### Part 4

依赖都是构造函数的参数，单元测试只构造一个机器人：`CheerBot({})` 测计数从 1 开始、缺 `@` 被忽略；
`FocusBot(Clock(now=1430), {})` 测 23:50 起 20 分钟显示为 `00:10`、非数字参数被忽略。端到端测试依次注册
三个机器人，重放 `SCRIPT` 并与 `EXPECTED_LOG` 比较。

### 追问

- 要对格式不对的命令回复用法说明，就让 `can_handle` 接受只有前缀的命令，在解析函数返回 `None` 的地方
  返回说明；`ChatRoom` 和其他机器人都不用改。
- Part 1 第 3 问里的前缀冲突可以在 `register` 时发现：每个机器人声明自己的命令前缀，前缀已被占用时
  `register` 抛出异常。

<details>
<summary>验证代码（可运行）</summary>

```python
import random


# Part 4: two unit tests, each building one bot without ChatRoom, and one end-to-end test
def test_cheer_bot():
    bot = CheerBot({})
    assert not bot.can_handle("Iris", "/cheer Kofi")  # no "@": ignored
    assert bot.handle("Iris", "/cheer @Kofi") == ["CheerBot: Iris cheers for @Kofi! @Kofi's cheer count is now 1."]


def test_focus_bot():
    bot = FocusBot(Clock(now=1430), {})
    assert not bot.can_handle("Kofi", "/focus soon")  # not a number: ignored
    assert bot.handle("Kofi", "/focus 20") == ["FocusBot: Kofi is heads-down for 20 min, back at 00:10."]


def test_script_end_to_end():
    room = ChatRoom(clock := Clock())
    for bot in (FocusBot(clock, {}), CheerBot({}), PollBot({})):
        room.register(bot)
    for sender, text, now in SCRIPT:
        room.send(sender, text, now)
    assert room.log == EXPECTED_LOG


for test in (test_cheer_bot, test_focus_bot, test_script_end_to_end):
    test()


# Part 2: the refactored room against the legacy handle_message, on random message sequences.
# The two share no code: the legacy function uses its own format_time and module-level dicts.
NAMES = ["Theo", "TheoBot", "Priya", "Pri", "Noah", "Noa", "Sana", "Leo", "Maya", "Kofi", "us"]
WORDS = ["hello", "quick", "update", "see", "you", "at", "the", "meeting", "lunch"]
JUNK = ["", "/", "/cheer", "/vote", "/poll", "/focus", "/Cheer @Theo", "/cheer\t@Theo", "hi @Theo"]


def random_message(rng, kinds):
    kind = rng.choice(kinds)
    pad = rng.choice(["", "", " ", "  "])                       # whitespace around the argument
    if kind == "cheer":
        arg = rng.choice(["@" + rng.choice(NAMES), "@", "@@x", "@Kofi Mensah", rng.choice(NAMES), ""])
    elif kind == "focus":
        arg = rng.choice(["1", "0", "-3", "abc", "007", "²", "٣", "5 extra", "", str(rng.randint(1, 3000))])
    elif kind == "poll":
        arg = rng.choice(WORDS) + "?" + "".join(f" |{pad}{rng.choice(WORDS)}" for _ in range(rng.randint(0, 4)))
    elif kind == "vote":
        arg = rng.choice(["A", "B", "C", "D", "Z", "a", "b", "", "AB"])
    elif kind == "plain":
        return rng.choice(NAMES), " ".join(rng.choice(WORDS + NAMES) for _ in range(rng.randint(1, 5)))
    else:
        return rng.choice(NAMES), rng.choice(JUNK)
    return rng.choice(NAMES), f"/{kind} {pad}{arg}{pad}"


def reset_legacy():
    for state in (cheer_counts, focus_until, poll_state, messages):
        state.clear()


def fuzz(seed, n, legacy, build_bots, kinds):
    rng = random.Random(seed)
    reset_legacy()
    clock = Clock()
    room = ChatRoom(clock)
    for bot in build_bots(clock):
        room.register(bot)
    now = 0
    for _ in range(n):
        now += rng.choice([0, 1, 5, 15, 120, 700])              # crosses midnight many times
        sender, text = random_message(rng, kinds)
        legacy(sender, text, now)
        room.send(sender, text, now)
    assert messages == room.log, f"mismatch at seed {seed}"
    return len(room.log)


ALL_KINDS = ["cheer", "focus", "poll", "vote", "plain", "junk"]
part2_bots = lambda clock: [FocusBot(clock, {}), CheerBot({}), PollBot({})]
lines2 = sum(fuzz(seed, 400, handle_message, part2_bots, ALL_KINDS) for seed in range(30))
print(f"Part 2: 30 seeds x 400 messages, {lines2} log lines, identical to handle_message")


# Part 3: an independent version of the new rule, written directly on top of the legacy code
def handle_message_part3(name, msg, now):
    handle_message(name, msg, now)
    if poll_state and max(poll_state["votes"].values()) >= 3:
        author = poll_state["author"]
        poll_state.clear()
        cheer_counts[author] = cheer_counts.get(author, 0) + 1
        messages.append(f"CheerBot: {author}'s poll reached 3 votes! "
                        f"{author}'s cheer count is now {cheer_counts[author]}.")


def part3_bots(clock):
    bus = EventBus()
    return [FocusBot(clock, {}), DecisivePollBot({}, bus), RewardedCheerBot({}, bus)]


VOTE_HEAVY = ALL_KINDS + ["vote"] * 6                             # so that polls actually reach 3 votes
decided = 0
for seed in range(30):
    fuzz(seed, 400, handle_message_part3, part3_bots, VOTE_HEAVY)
    decided += sum("poll reached 3 votes" in line for line in messages)
assert decided > 100
print(f"Part 3: 30 seeds x 400 messages, {decided} polls closed, identical to the direct version")

# the script from the statement, then one more vote: the poll is closed, so no line at all
room = ChatRoom(clock := Clock())
for bot in part3_bots(clock):
    room.register(bot)
for sender, text, now in SCRIPT + [("Noah", "/vote A", 615)]:
    room.send(sender, text, now)
assert room.log == EXPECTED_LOG + ["CheerBot: Maya's poll reached 3 votes! Maya's cheer count is now 1.",
                                   "Noah: /vote A"]

# registered before DecisivePollBot, RewardedCheerBot flushes the line one message late
bus, room = EventBus(), ChatRoom(clock := Clock())
for bot in (FocusBot(clock, {}), RewardedCheerBot({}, bus), DecisivePollBot({}, bus)):
    room.register(bot)
for sender, text, now in SCRIPT + [("Noah", "hi", 615)]:
    room.send(sender, text, now)
assert room.log[-3:] == [EXPECTED_LOG[-1], "Noah: hi",
                         "CheerBot: Maya's poll reached 3 votes! Maya's cheer count is now 1."]

# EventBus: subscription order, depth-first re-entrant publish, subscriber list fixed at publish time
bus, seen = EventBus(), []
bus.subscribe("a", lambda e: (seen.append("a1"), bus.publish(Event("b", {}))))
bus.subscribe("a", lambda e: seen.append("a2"))
bus.subscribe("b", lambda e: seen.append("b1"))
bus.subscribe("b", lambda e: bus.subscribe("b", lambda e: seen.append("late")))
bus.publish(Event("a", {}))
assert seen == ["a1", "b1", "a2"]
```

</details>

</details>
