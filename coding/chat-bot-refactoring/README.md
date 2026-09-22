# Chat Bot Refactoring

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Refactoring | ★★★☆☆ | Medium | SWE | refactoring, oop-design, event-driven, testing | 4 parts |
<!-- meta:end -->

## Problem

A chat service delivers every incoming message to a set of bots that react to slash commands. A
message has a sender name, a text, and an integer timestamp `now`: the number of minutes since
midnight of the service's first day, never smaller than the previous message's, so 9:00 on the
first day is `540` and 9:00 on the second day is `1980`. Nothing reads the system clock — every
call passes `now` explicitly. Sending a message first appends `"{sender}: {text}"` to a shared log,
then lets each bot look at the raw text and possibly append more lines to that same log. A command
is recognized only at the very start of the text, as the command word followed by one space
(`/cheer `, `/focus `, `/poll `, `/vote `); whitespace around the rest of the text is ignored.
Three bots are registered.

**CheerBot**

- Recognizes `/cheer @<name>`, where `<name>` is one or more characters right after the `@`. Any
  other shape (no `@`, or nothing after it) is not a valid command.
- Keeps a running cheer count per username, starting at 0.
- On a valid command, adds 1 to the named user's count and announces the sender, the target
  exactly as written (with its leading `@`), and the new count.

**FocusBot**

- Recognizes `/focus <n>`, where `<n>` is one or more decimal digits spelling a number `>= 1`. Any
  other shape (missing, negative, non-numeric) is not a valid command.
- On a valid command, starts a focus session for the sender that ends at minute `now + n`,
  replacing any session the sender already has, and announces the sender and the time of day the
  session ends at, formatted `HH:MM` (a session can run past midnight: one started at 23:50 for 20
  minutes ends at 00:10).
- Independently of that, on *every* incoming message — including this bot's own command and every
  other bot's — for every user whose name appears as a substring of the raw text and whose session
  is still running (this message's `now` strictly before the session's end), the bot appends one
  reminder line, in the order those users first ever started a session. Reminders come before
  every other bot's line for the message, and are decided before a `/focus` in the same message
  takes effect.

**PollBot**

- Recognizes `/poll <question> | <option 1> | <option 2> | ...`: split the text after `/poll ` on
  `|` and strip the surrounding whitespace from every piece; the first piece is the question, the rest
  are the options. Valid only with at least 2 options; a valid command replaces whatever poll is
  currently in progress (voted on or not) with a fresh one, options labelled `A`, `B`, `C`, ... in
  the given order, every count starting at 0. Announces the poll's author (the sender), its
  question, and its labelled options.
- Recognizes `/vote <letter>`, matched case-insensitively against the labels of the poll currently
  in progress. Valid only when a poll is in progress and the letter matches one of its labels;
  adds one vote to that option and announces the voter, the chosen option's text, and the updated
  tally for every label, in label order.
- A command that isn't a valid `/poll` or `/vote` by the rules above is not recognized.

A command that fails its bot's validity rule above gets no response from any bot as a command; its
text still counts as an ordinary message for FocusBot's reminders.

Here is the current implementation:

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

Its output on the script below is the reference for "unchanged behavior" in every part:

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

### Part 1 — Reading the legacy code

Answer the following, each grounded in specific lines of the code above.

1. Trace the call for `("Leo", "/cheer @Theo", 561)` in the script above. Which blocks of
   `handle_message` run, in what order, and why does the FocusBot line appear before the CheerBot
   line even though the message is a cheer command, not a focus one?
2. Give a concrete scenario where calling `handle_message` twice — from two separate test
   functions, in the same process — makes the second test's result depend on what the first one
   did, and name the line(s) responsible.
3. Suppose you add a fourth bot, `PingBot`, triggered by `/ping`. List every place in the file
   above you would have to touch, and explain what (if anything) stops two bots from silently
   claiming the same command prefix.
4. Name two pieces of behavior that cannot be unit-tested without exercising all of
   `handle_message`, and explain why. What happens to the blocks after `# CheerBot logic` if the
   loop above it (lines 15-18) were to raise an exception partway through?

### Part 2 — A bot interface

Replace the single function with one class per bot behind a shared interface, and a room that
dispatches an incoming message to whichever registered bots want to see it. State that used to
live in a module-level dict — the cheer counts, the focus end times, the poll in progress — must
instead be handed to each bot's constructor, and no bot may read the wall clock: one that needs
`now` is given a clock object that the room advances.

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

Implement these classes so that, for any sequence of `(sender, text, now)` triples, a `ChatRoom`
with the three bots registered reproduces `handle_message`'s log line for line.

### Part 3 — Cross-bot events

`PollBot` and `CheerBot` must react to each other only by publishing and subscribing to events on
a shared bus — neither may call the other's methods or hold a reference to it. New rule: once any
option's vote count reaches 3, that poll ends immediately. `PollBot` must not accept any further
`/vote` for it (a later `/vote` behaves exactly as if no poll were in progress), and `CheerBot`
must add 1 to the cheer count of the poll's author and announce it, appended right after
`PollBot`'s own line for that vote:

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

In the script above, the last message, `Priya: /vote B` at minute 612, brings B's tally to 3. With
the new rule, the log is `EXPECTED_LOG` followed by one more line:

```text
CheerBot: Maya's poll reached 3 votes! Maya's cheer count is now 1.
```

### Part 4 — Testing

Using the standard library's `unittest` (plain functions with `assert` work too):

- Write unit tests for at least two of the three bots, each constructing only that bot's own
  dependencies (an explicit `Clock`, an explicit `dict`) without going through `ChatRoom`,
  covering at least one core rule and at least one input the bot is specified to ignore.
- Write one end-to-end test that builds a fresh `ChatRoom` with the three bots, replays `SCRIPT`,
  and asserts the resulting log equals `EXPECTED_LOG`.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Confirm with the interviewer that a malformed command is silently ignored rather than answered
with an error (assumed below).

### Part 1

1. Line 12 appends `"Leo: /cheer @Theo"`. Next come lines 15-18, which every message passes
   through: `focus_until` holds `{"Theo": 565}` from minute 545, `"Theo"` is a substring of the
   text, and `561 < 565`, so line 18 appends the reminder. Only then does line 21's `/cheer ` check
   run and append the CheerBot line. The order comes purely from the reminder loop sitting above
   the CheerBot block: the two blocks touch disjoint state, so swapping them only swaps the two
   lines.
2. `cheer_counts` (line 1) lives as long as the process, and lines 25-27 only ever add to it. A test
   that calls `handle_message("A", "/cheer @X", 0)` and expects the line to end in `is now 1.`
   passes on its own, but fails after any earlier test that cheered `X`. Likewise for `messages`
   (line 4).
3. One change is always needed: a new `if msg[:6] == "/ping ":` block somewhere in lines 12-82,
   whose position decides the order of the output (question 1); if it keeps state, also a new
   module-level dict next to lines 1-4. Nothing stops a collision: the prefixes on lines 21, 41, 61
   and 74 are string literals scattered over separate `if` blocks, with no registry of prefixes in
   use, so a new block that also tested `"/poll "` would run alongside PollBot's block without any
   error.
4. CheerBot's counting (lines 21-38) and PollBot's vote validation (lines 61-71) are statements in
   one function body; the only way to run them is `handle_message`, which also runs every other
   block against the shared globals. If lines 15-18 raised partway through, the exception would
   leave `handle_message` at once and none of the blocks from line 20 on would run for that message.

### Part 2

Each module-level dict becomes a constructor argument, each group of `if` blocks becomes a class,
and `ChatRoom.send` goes through the bots in registration order. FocusBot is registered first
because its reminders precede every other line; CheerBot and PollBot never answer the same message,
so their relative order is free.

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

`DecisivePollBot` and `RewardedCheerBot` subclass Part 2's `PollBot` and `CheerBot` and only add
code around `super()`, so Part 2's classes need no change. When a count reaches 3,
`DecisivePollBot` closes the poll and publishes `poll_decided` with the author's name;
`RewardedCheerBot`'s handler updates the count and queues the line, which `handle` returns on the
bot's turn. It must be registered after `DecisivePollBot`; otherwise the line appears one message late.

`publish` is synchronous: it calls the handlers subscribed when it starts, in subscription order,
and an event published inside a handler is fully handled before the outer event's next handler
runs (depth-first). Two bots that publish as soon as they receive each other's events would
recurse without end.

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

Dependencies are constructor arguments, so a unit test builds just one bot: `CheerBot({})` checks
that the count starts at 1 and that a missing `@` is ignored; `FocusBot(Clock(now=1430), {})` checks
that 20 minutes from 23:50 shows as `00:10` and that a non-numeric argument is ignored. The
end-to-end test registers the three bots in turn, replays `SCRIPT`, and compares the log with
`EXPECTED_LOG`.

### Follow-ups

- To answer a malformed command with a usage line, let `can_handle` accept the bare prefix and
  return the usage text where the parser gives `None`; `ChatRoom` and the other bots do not change.
- The prefix collision from Part 1, question 3 can be caught at `register`: each bot declares its
  command prefixes, and `register` raises if one is already taken.

<details>
<summary>Checks (runnable)</summary>

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
