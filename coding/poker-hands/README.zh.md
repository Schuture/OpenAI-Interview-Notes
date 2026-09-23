# 三张牌的牌型与弃牌

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 | 轮次 |
| --- | --- | --- | --- | --- | --- | --- |
| 编程 | ★★★☆☆ | 中等 | SWE | simulation, sorting, rules-engine | 3 个部分 | 电话面 |
<!-- meta:end -->

## 题目

`N` 位玩家（`2 <= N <= 1e5`）各自拿到一手三张牌的扑克牌局，需要判定每手牌的牌型并输出获胜者（允许并列）。
一张牌写成两个字符，先是点数再是花色：点数的大小顺序是
`2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < T < J < Q < K < A`（`T` 表示 10），花色是 `C`、`D`、`H`、`S`。一手牌是恰好
三张这样的牌组成的列表，例如 `["9H", "TC", "9D"]`；全部玩家的手牌加起来不超过 `3e5` 张。

### Part 1 —— 牌型与比较（暂不考虑花色）

忽略花色时，每手牌恰好属于三种牌型之一，按优先级从强到弱排列：

- **三条（Three of a Kind）**：三张牌点数完全相同。
- **对子（Pair）**：恰好两张牌点数相同。
- **高牌（High Card）**：三张牌点数两两不同。

牌型更强的一手牌永远赢过牌型更弱的一手牌，与具体点数无关。两手牌牌型*相同*时，按以下规则比较：

- **三条**：比较那个相同的点数。
- **对子**：先比较对子的点数；若相等，再比较剩下那张单牌的点数。
- **高牌**：把两手牌各自的三个点数从大到小排序，依次比较——先比最大的，再比中间的，最后比最小的。

如果上述每一个比较点都相等，两手牌并列。花色永远不参与打破并列。

```py
def hand_type(cards: list[str]) -> str:
    """cards has exactly 3 elements, each formatted <rank><suit>, e.g. "9H" or "TC". Returns one of
    "Three of a Kind", "Pair", "High Card"."""

def compare_hands(cards_a: list[str], cards_b: list[str]) -> int:
    """Compares two 3-card hands under the rules above. Returns 1 if cards_a ranks strictly above
    cards_b, -1 if strictly below, 0 if the two hands tie."""

def rank_players(hands: list[list[str]]) -> list[int]:
    """hands[i] is player i's three cards. Returns, in increasing order, the 0-indexed players whose hand
    does not rank below any other player's hand -- more than one index means those players tie for the
    win."""
```

例子：玩家 0 拿到 `7H 7D 4C`，玩家 1 拿到 `7S 7C 4D`，玩家 2 拿到 `KD QS JC`。

```text
hand_type(玩家 0) = Pair       （一对 7，单牌 4）
hand_type(玩家 1) = Pair       （一对 7，单牌 4）
hand_type(玩家 2) = High Card  （K、Q、J）
rank_players(...) = [0, 1]     # 两手对子完全相同，玩家 0 和玩家 1 并列获胜
```

### Part 2 —— 加入同花

现在花色开始起作用：*同花*（Flush）指三张牌花色完全相同的一手牌。已经是三条的一手牌永远不会同时被
判定为同花。优先级顺序变为：

三条 > 同花 > 对子 > 高牌。

两手同花之间的比较方式与高牌完全相同：把各自三个点数从大到小排序，依次比较。

```py
def hand_type(cards: list[str]) -> str:
    """Same input as Part 1. Now also returns "Flush" for a same-suited hand that is not Three of a
    Kind, ranked between Three of a Kind and Pair."""
```

`compare_hands` 和 `rank_players` 的签名与 Part 1 保持一致；它们现在遵循更新后的优先级顺序，以及上面
同花的比较规则。

例子：玩家 0 拿到 `9C 7C 3C`，玩家 1 拿到 `JD JH 8S`，玩家 2 拿到 `AS QD 6H`。

```text
hand_type(玩家 0) = Flush      （9、7、3，全为梅花）
hand_type(玩家 1) = Pair       （一对 J，单牌 8）
hand_type(玩家 2) = High Card  （A、Q、6）
rank_players(...) = [0]        # 同花胜过对子，尽管它最大的那张牌点数更低
```

### Part 3 —— 弃牌

现在这些玩家从一副共用的 `deck` 里发牌：`deck` 是一个按发牌顺序排列、长度至少为 `3 * N` 的不重复牌列表。
发牌分三轮进行，每轮都按 `0, 1, ..., N-1` 的顺序依次访问每位玩家一次：

- **第 1、2 轮**始终从 `deck` 剩余部分的最前面给该玩家发下一张牌。
- **第 3 轮**先询问该玩家的*弃牌规则*——一个只依据该玩家自己前两张牌（按发牌顺序）做判断的函数，
  不看任何其他玩家的牌或决定。如果规则给出“弃牌”，该玩家被标记为*弃牌*（folded），不再拿第三张牌；
  这次不会消耗 `deck` 里的任何一张牌，因此之后轮到的玩家仍然拿到牌堆里下一张尚未发出的牌。否则，
  该玩家照常拿到第三张牌。

整局一共恰好发生 `3 * N` 次“发牌或弃牌”，每轮 `N` 次。第 3 轮访问完每一位玩家后，本局结束，结果按下列
规则判定：

- 若所有玩家都弃牌，本局没有获胜者。
- 若恰好一位玩家没有弃牌，该玩家直接获胜。
- 否则，用 Part 2 的规则（含同花）比较所有没有弃牌的玩家的手牌；他们之间的并列情况与 Part 1、Part 2
  的规则完全一样。

三种弃牌规则：

- **从不弃牌。**
- **前两张牌不是对子就弃牌**（点数相同才算对子）。
- **前两张牌不是同花听牌就弃牌**（花色相同才算听同花，即 flush draw）。

```py
def never_fold(first_two: list[str]) -> bool: ...
def fold_unless_pair(first_two: list[str]) -> bool: ...
def fold_unless_flush_draw(first_two: list[str]) -> bool: ...

class PokerRound:
    def __init__(self, num_players: int, deck: list[str], strategies: list):
        """strategies[i] is player i's fold rule, one of the three functions above."""

    def deal_card(self) -> str:
        """Called only while is_over() is False. Advances the round by exactly one deal-or-fold and
        returns a line describing it: either "Player {i} is dealt {card}." or "Player {i} folds."."""

    def is_over(self) -> bool: ...

    def check_result(self) -> str:
        """Valid once is_over() is True. Returns "Winner: Player {i}", or
        "Winner: Tie (Players {i}, {j}, ...)" with the indices in increasing order, or
        "No winner: all players folded."."""
```

例子：3 位玩家共用牌堆 `3S TD 8H QC TS 4H 2D 6H 7C`；玩家 0 如果两张牌之后没有对子就弃牌，玩家 1 从不
弃牌，玩家 2 如果两张牌之后没有同花听牌就弃牌。

```text
Player 0 is dealt 3S.
Player 1 is dealt TD.
Player 2 is dealt 8H.
Player 0 is dealt QC.
Player 1 is dealt TS.
Player 2 is dealt 4H.
Player 0 folds.
Player 1 is dealt 2D.
Player 2 is dealt 6H.
Winner: Player 2
```

玩家 0 的前两张牌（`3S`、`QC`）不是对子，于是弃牌，这一次不抽牌：玩家 1 的第三张牌就是牌堆里下一张尚未
发出的 `2D`，`6H` 归玩家 2。玩家 2 的前两张牌（`8H`、`4H`）花色相同，于是留到最后，凑成同花，赢过玩家 1
的一对 10；`7C` 始终没有发出。

## 参考解答

<details>
<summary>展开参考解答</summary>

先向面试官确认一点：点数相同时花色是否真的完全不参与打破并列——上面的规则已经这样规定了，但有些扑克
变体会给花色排大小，问一句不费事。然后把每手牌映射成一个可以直接比较的元组 `(type_priority, tie_break)`，
其中 `tie_break` 对同一牌型的所有手牌都是同样的形状：三条是一个一元组，对子是 `(对子点数, 单牌点数)`
这样的二元组，高牌（以及从 Part 2 起的同花）是排好序的三元组。每手牌都化成这样一个元组之后，
`compare_hands` 和 `rank_players` 各自只需要一行；Part 2 的同花和 Part 3 的摆牌比较都直接复用这同一个
元组，不需要新的比较逻辑。

### Part 1

```python
RANKS = "23456789TJQKA"  # index doubles as the rank's numeric value
TYPE_NAMES = ["High Card", "Pair", "Three of a Kind"]  # indexed by the priority inside a hand key


def _rank_value(card):
    return RANKS.index(card[0])


def _hand_key(cards):
    ranks = sorted((_rank_value(c) for c in cards), reverse=True)
    if ranks[0] == ranks[1] == ranks[2]:
        return (2, (ranks[0],))
    if ranks[0] == ranks[1]:                # NOTE: after a descending sort the pair is always adjacent,
        return (1, (ranks[0], ranks[2]))    #       at [0]/[1] or at [1]/[2] -- it can never be split
    if ranks[1] == ranks[2]:
        return (1, (ranks[1], ranks[0]))
    return (0, tuple(ranks))


def hand_type(cards):
    return TYPE_NAMES[_hand_key(cards)[0]]


def compare_hands(cards_a, cards_b):
    ka, kb = _hand_key(cards_a), _hand_key(cards_b)
    return 0 if ka == kb else (1 if ka > kb else -1)  # NOTE: tuples compare lexicographically, so the
                                                      #       priority always dominates the tie-break


def rank_players(hands):
    keys = [_hand_key(h) for h in hands]
    best = max(keys)
    return [i for i, k in enumerate(keys) if k == best]
```

对 Part 1 的例子调用 `rank_players` 得到的正是 `[0, 1]`。

### Part 2

同花被插进三条和对子之间，所以真正挪动的只有三条的优先级，从 2 变成 3；同花自己的比较关键字，就是高牌
已经在用的那个排好序的三元组。点数部分的规则一点没变，因此新的 `_hand_key` 直接调用旧的那个，再在它的
结果上打一个补丁，不必把点数规则再写一遍。`hand_type`、`compare_hands` 和 `rank_players` 每次调用时都按
名字去查 `TYPE_NAMES` 和 `_hand_key`，所以这三个函数一行都不用改。

```python
_ranks_only_key = _hand_key                                     # Part 1's key, suits ignored
TYPE_NAMES = ["High Card", "Pair", "Flush", "Three of a Kind"]  # flush slots in above pair


def _hand_key(cards):  # supersedes Part 1's version
    priority, tie_break = _ranks_only_key(cards)
    if priority == 2:                                 # NOTE: three of a kind is settled before the suits
        return (3, tie_break)                         #       are looked at, so it never reads as a flush
    if len({c[1] for c in cards}) == 1:
        return (2, tuple(sorted((_rank_value(c) for c in cards), reverse=True)))
    return (priority, tie_break)
```

对 Part 2 的例子调用 `rank_players`，现在返回 `[0]`。

### Part 3

`PokerRound` 只维护一个累加计数器 `calls_made`，用 `divmod` 从它同时读出当前是第几轮、该轮到哪位玩家，
而不是分开维护两个循环变量。指向 `deck` 的 `next_card` 是唯一的一个指针，只有在真的发出一张牌时才前移，
这正是弃牌“不花代价”的原因——不管前一位玩家弃牌与否，下一位要拿牌的玩家拿到的永远是牌堆里下一张尚未
发出的牌。

```python
def never_fold(first_two):
    return False


def fold_unless_pair(first_two):
    return first_two[0][0] != first_two[1][0]


def fold_unless_flush_draw(first_two):
    return first_two[0][1] != first_two[1][1]


class PokerRound:
    def __init__(self, num_players, deck, strategies):
        assert len(deck) >= 3 * num_players and len(set(deck)) == len(deck)
        self.num_players = num_players
        self.deck = deck
        self.strategies = strategies
        self.hands = [[] for _ in range(num_players)]
        self.folded = [False] * num_players
        self.next_card = 0        # NOTE: one running pointer -- a fold never advances it
        self.calls_made = 0

    def is_over(self):
        return self.calls_made >= 3 * self.num_players

    def deal_card(self):
        pass_no, player = divmod(self.calls_made, self.num_players)  # NOTE: pass_no is 0, 1 or 2
        self.calls_made += 1
        if pass_no == 2 and self.strategies[player](self.hands[player]):
            self.folded[player] = True
            return f"Player {player} folds."
        card = self.deck[self.next_card]
        self.next_card += 1
        self.hands[player].append(card)
        return f"Player {player} is dealt {card}."

    def check_result(self):
        active = [i for i in range(self.num_players) if not self.folded[i]]
        if not active:
            return "No winner: all players folded."
        if len(active) == 1:
            return f"Winner: Player {active[0]}"
        keys = {i: _hand_key(self.hands[i]) for i in active}
        best = max(keys.values())
        winners = [i for i in active if keys[i] == best]
        if len(winners) == 1:
            return f"Winner: Player {winners[0]}"
        return "Winner: Tie (Players " + ", ".join(str(i) for i in winners) + ")"


def play_round(num_players, deck, strategies):
    game = PokerRound(num_players, deck, strategies)
    log = []
    while not game.is_over():
        log.append(game.deal_card())
    log.append(game.check_result())
    return log
```

调用 `play_round(3, ["3S", "TD", "8H", "QC", "TS", "4H", "2D", "6H", "7C"], [fold_unless_pair, never_fold, fold_unless_flush_draw])` 得到的正是 Part 3 的例子。

### 追问

- 弃牌不会消耗 `deck` 里的牌，所以按最坏情况（`3 * num_players`，没有人弃牌）准备的 `deck` 永远够用；
  更短的牌堆则可能在弃牌人数不够多时，局进行到中途就被抽空。
- 每个 Part 处理每张牌的开销都是 O(1)（一手牌恰好三张），所以三个 Part 整体都是 O(发出的牌数总和)。
- 五张牌的牌型需要更多种比较关键字的形状（两对、顺子、葫芦……），但思路不变：把每手牌映射成一个元组，
  第一个分量是牌型优先级，其余分量只在同一牌型内部才拿来比较。
- 如果要针对一个已知的对手策略去选弃牌规则，是另一个更难的问题——弃牌与继续下去的期望值之差，要对
  牌堆里剩下的未知牌求平均——上面的规则和代码都没有涉及。

<details>
<summary>验证代码（可运行）</summary>

```python
p0, p1, p2 = ["7H", "7D", "4C"], ["7S", "7C", "4D"], ["KD", "QS", "JC"]
assert [hand_type(p) for p in (p0, p1, p2)] == ["Pair", "Pair", "High Card"]
assert rank_players([p0, p1, p2]) == [0, 1]

p0, p1, p2 = ["9C", "7C", "3C"], ["JD", "JH", "8S"], ["AS", "QD", "6H"]
assert [hand_type(p) for p in (p0, p1, p2)] == ["Flush", "Pair", "High Card"]
assert rank_players([p0, p1, p2]) == [0]

deck3 = ["3S", "TD", "8H", "QC", "TS", "4H", "2D", "6H", "7C"]
strategies3 = [fold_unless_pair, never_fold, fold_unless_flush_draw]
expected3 = [
    "Player 0 is dealt 3S.", "Player 1 is dealt TD.", "Player 2 is dealt 8H.",
    "Player 0 is dealt QC.", "Player 1 is dealt TS.", "Player 2 is dealt 4H.",
    "Player 0 folds.", "Player 1 is dealt 2D.", "Player 2 is dealt 6H.",
    "Winner: Player 2",
]
assert play_round(3, deck3, strategies3) == expected3

# --- an independently coded reading of the rules: label by rank counts, tie-break spelled out per type,
#     and compare by walking the tie-break left to right. Shares no code with the solution above. ---
import itertools
import random
from collections import Counter
from functools import cmp_to_key

SUITS = "CDHS"
FULL_DECK = [r + s for r in RANKS for s in SUITS]
PART1_TYPES = ["High Card", "Pair", "Three of a Kind"]          # Part 1 order, weakest first
PART2_TYPES = ["High Card", "Pair", "Flush", "Three of a Kind"]  # Part 2 order, weakest first


def naive_label(cards, types):
    counts = Counter(c[0] for c in cards)
    if len(counts) == 1:
        return "Three of a Kind"
    if "Flush" in types and len({c[1] for c in cards}) == 1:
        return "Flush"
    return "Pair" if len(counts) == 2 else "High Card"


def naive_tie_break(cards, label):
    values = sorted((RANKS.index(c[0]) for c in cards), reverse=True)
    if label == "Three of a Kind":
        return (values[0],)
    if label == "Pair":
        pair_value = next(v for v, c in Counter(values).items() if c == 2)
        return (pair_value, next(v for v in values if v != pair_value))
    return tuple(values)                       # High Card and Flush: all three, high to low


def naive_compare(a, b, types=PART2_TYPES):
    la, lb = naive_label(a, types), naive_label(b, types)
    if la != lb:
        return 1 if types.index(la) > types.index(lb) else -1
    for x, y in zip(naive_tie_break(a, la), naive_tie_break(b, lb)):
        if x != y:
            return 1 if x > y else -1
    return 0


# every one of the C(52, 3) = 22,100 possible 3-card hands, not just a random sample
type_counts = Counter()
class_rep = {}
for combo in itertools.combinations(FULL_DECK, 3):
    cards = list(combo)
    label = naive_label(cards, PART2_TYPES)
    type_counts[label] += 1
    assert hand_type(cards) == label
    p1_label = naive_label(cards, PART1_TYPES)                   # Part 1: the same hand without suits
    assert PART1_TYPES[_ranks_only_key(cards)[0]] == p1_label
    assert _ranks_only_key(cards)[1] == naive_tie_break(cards, p1_label)
    class_rep.setdefault((PART2_TYPES.index(label), naive_tie_break(cards, label)), cards)
assert type_counts == Counter({"High Card": 17160, "Pair": 3744, "Flush": 1144, "Three of a Kind": 52})

# hands with repeated cards are not dealt from a real deck, but the rules still have to place them
assert hand_type(["9H", "9H", "9H"]) == "Three of a Kind"       # three of a kind wins over flush
assert hand_type(["9H", "9H", "4H"]) == "Flush"                 # a same-suited pair is a flush
assert compare_hands(["9H", "9H", "9H"], ["AH", "KH", "QH"]) == 1

# --- the hand order is a total order on the 741 distinct (type, tie-break) classes: sort one
#     representative per class with the naive comparison, then check compare_hands against position ---
reps = sorted(class_rep.values(), key=cmp_to_key(naive_compare))
assert len(reps) == 13 + 286 + 156 + 286                        # 3oak, flush, pair, high card
for i in range(len(reps) - 1):
    assert naive_compare(reps[i], reps[i + 1]) == -1             # no two classes compare equal
for i, a in enumerate(reps):
    assert compare_hands(a, a) == 0                              # reflexive
    for j, b in enumerate(reps):
        assert compare_hands(a, b) == (0 if i == j else (1 if i > j else -1))
# antisymmetry and transitivity follow: compare_hands is the sign of a difference of positions

# every hand ties with its own class representative, so ties are exactly equal (type, tie-break)
for combo in itertools.combinations(FULL_DECK, 3):
    cards = list(combo)
    label = naive_label(cards, PART2_TYPES)
    assert compare_hands(cards, class_rep[(PART2_TYPES.index(label), naive_tie_break(cards, label))]) == 0


def naive_rank_players(hands):
    best = max(range(len(hands)), key=cmp_to_key(lambda i, j: naive_compare(hands[i], hands[j])))
    return [i for i in range(len(hands)) if naive_compare(hands[i], hands[best]) == 0]


NARROW_DECK = [r + s for r in "789" for s in SUITS]    # 12 cards: a narrow pool makes ties common
rng = random.Random(7)
tie_seen = 0
for trial in range(20_000):
    pool = FULL_DECK if trial % 2 else NARROW_DECK
    n = rng.randint(2, len(pool) // 3)
    deck = rng.sample(pool, 3 * n)
    hands = [deck[3 * i:3 * i + 3] for i in range(n)]
    got = rank_players(hands)
    assert got == naive_rank_players(hands)
    if len(got) > 1:
        tie_seen += 1
assert tie_seen > 500

# --- Part 3: an independent re-simulation -- its own pointer walk, its own scoring, and its own
#     re-coding of every fold rule, so a bug inside never_fold / fold_unless_pair /
#     fold_unless_flush_draw would not also be baked into the check ---
def naive_should_fold(strategy_name, first_two):
    if strategy_name == "never":
        return False
    if strategy_name == "pair":
        return len({c[0] for c in first_two}) != 1      # ranks differ iff this set has 2 elements
    return len({c[1] for c in first_two}) != 1          # "flush"; suits differ iff this set has 2 elements


def naive_play_round(num_players, deck, strategy_names):
    hands = [[] for _ in range(num_players)]
    folded = [False] * num_players
    ptr = 0
    log = []
    for pass_no in range(3):
        for player in range(num_players):
            if pass_no == 2 and naive_should_fold(strategy_names[player], hands[player]):
                folded[player] = True
                log.append(f"Player {player} folds.")
                continue
            card = deck[ptr]
            ptr += 1
            hands[player].append(card)
            log.append(f"Player {player} is dealt {card}.")
    active = [i for i in range(num_players) if not folded[i]]
    if not active:
        log.append("No winner: all players folded.")
    elif len(active) == 1:
        log.append(f"Winner: Player {active[0]}")
    else:
        top = max(active, key=cmp_to_key(lambda i, j: naive_compare(hands[i], hands[j])))
        winners = [i for i in active if naive_compare(hands[i], hands[top]) == 0]
        if len(winners) == 1:
            log.append(f"Winner: Player {winners[0]}")
        else:
            log.append("Winner: Tie (Players " + ", ".join(str(i) for i in winners) + ")")
    return log, ptr


strategy_names3 = ["pair", "never", "flush"]
assert naive_play_round(3, deck3, strategy_names3)[0] == play_round(3, deck3, strategies3)

# the same narrow pool makes pairs, flush draws and stalemates common across 20,000 rounds
STRATEGY_BY_NAME = {"never": never_fold, "pair": fold_unless_pair, "flush": fold_unless_flush_draw}
rng = random.Random(11)
branch_counts = Counter()
for _ in range(20_000):
    n = rng.randint(2, 4)
    deck_t = rng.sample(NARROW_DECK, 3 * n)
    names_t = [rng.choice(list(STRATEGY_BY_NAME)) for _ in range(n)]
    strat_t = [STRATEGY_BY_NAME[name] for name in names_t]
    game = PokerRound(n, deck_t, strat_t)
    got = []
    while not game.is_over():
        got.append(game.deal_card())
    assert game.calls_made == 3 * n                     # exactly 3N deals-or-folds, then the round is over
    got.append(game.check_result())
    want, ptr = naive_play_round(n, deck_t, names_t)
    assert got == want
    folded_count = sum(1 for line in got if line.endswith("folds."))
    assert game.next_card == 3 * n - folded_count == ptr   # a fold consumes no card
    result_line = got[-1]
    if result_line.startswith("No winner"):
        branch_counts["stalemate"] += 1
    elif n - folded_count == 1:
        branch_counts["outright"] += 1
    elif "Tie" in result_line:
        branch_counts["tie"] += 1
    else:
        branch_counts["showdown"] += 1
    for pos, line in enumerate(got):
        if line.endswith("folds.") and any(x.startswith("Player") and "dealt" in x for x in got[pos + 1:]):
            branch_counts["deal_after_fold"] += 1
            break
assert all(branch_counts[b] > 0 for b in
           ("stalemate", "outright", "tie", "showdown", "deal_after_fold"))
```

</details>

</details>
