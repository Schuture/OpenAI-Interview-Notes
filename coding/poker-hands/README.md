# Three-Card Hands and Folding

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Coding | ★★★☆☆ | Medium | SWE | simulation, sorting, rules-engine | 3 parts | Phone screen |
<!-- meta:end -->

## Problem

`N` players (`2 <= N <= 1e5`) are each dealt a three-card poker hand, and every hand must be ranked and
a winner (or a tied set of winners) reported. A card is written as two characters, a rank followed by a
suit: ranks are ordered `2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < T < J < Q < K < A` (`T` is ten) and suits are
`C`, `D`, `H`, `S`. A hand is a list of exactly three such cards, e.g. `["9H", "TC", "9D"]`; at most
`3e5` cards are in play in total.

### Part 1 — Hand types and comparisons (no suits yet)

Ignoring suits, every hand is one of three types, in priority order from strongest to weakest:

- **Three of a Kind**: all three cards share the same rank.
- **Pair**: exactly two of the three cards share a rank.
- **High Card**: the three ranks are all different.

A hand of a stronger type always beats a hand of a weaker type, regardless of the actual ranks involved.
Between two hands of the *same* type, compare as follows:

- **Three of a Kind**: compare the shared rank.
- **Pair**: compare the pair's rank first; if that is equal, compare the remaining (unpaired) card's
  rank.
- **High Card**: sort each hand's three ranks from high to low and compare them in that order — highest
  first, then middle, then lowest.

If every comparison point above comes out equal, the two hands tie. Suit never breaks a tie.

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

Example: player 0 has `7H 7D 4C`, player 1 has `7S 7C 4D`, player 2 has `KD QS JC`.

```text
hand_type(player 0) = Pair       (a pair of 7s, kicker 4)
hand_type(player 1) = Pair       (a pair of 7s, kicker 4)
hand_type(player 2) = High Card  (K, Q, J)
rank_players(...)   = [0, 1]     # identical pairs, so players 0 and 1 tie for the win
```

### Part 2 — Adding flush

Suits now matter: a **Flush** is a hand whose three cards all share the same suit. A hand that is
already Three of a Kind is never also called a Flush. The priority order becomes:

Three of a Kind > Flush > Pair > High Card.

Two flushes are compared exactly like High Card: sort each hand's three ranks high to low and compare in
that order.

```py
def hand_type(cards: list[str]) -> str:
    """Same input as Part 1. Now also returns "Flush" for a same-suited hand that is not Three of a
    Kind, ranked between Three of a Kind and Pair."""
```

`compare_hands` and `rank_players` keep the signatures from Part 1; they now follow the updated priority
order and the flush tie-break rule above.

Example: player 0 has `9C 7C 3C`, player 1 has `JD JH 8S`, player 2 has `AS QD 6H`.

```text
hand_type(player 0) = Flush      (9, 7, 3, all clubs)
hand_type(player 1) = Pair       (a pair of Js, kicker 8)
hand_type(player 2) = High Card  (A, Q, 6)
rank_players(...)   = [0]        # the flush beats the pair despite its lower top card
```

### Part 3 — Folding

Now the players are dealt from a shared `deck`: a list of at least `3 * N` distinct cards, in the exact
order they will be drawn. Dealing proceeds in three passes; each pass visits players
`0, 1, ..., N-1` in that order, once each:

- **Passes 1 and 2** always deal that player their next card, drawn from the front of the remaining
  `deck`.
- **Pass 3** first asks that player's *fold rule* — a function of that player's own first two cards, in
  the order they were dealt, and nothing else (not any other player's cards or decisions). If the rule
  says fold, the player is marked *folded* and receives no third card; no `deck` card is consumed for
  them, so whichever later player draws next still gets the next undrawn card. Otherwise, the player is
  dealt a third card as usual.

There are exactly `3 * N` deals-or-folds in total, `N` per pass. Once pass 3 has visited every player
the round is over, and the result is decided:

- If every player folded, there is no winner.
- If exactly one player never folded, that player wins outright.
- Otherwise, compare the hands of every player who never folded using the Part 2 rules (Flush included);
  ties among them follow the same rule as in Parts 1 and 2.

Three fold rules:

- **Never fold.**
- **Fold unless the first two cards are a pair** (same rank).
- **Fold unless the first two cards are a flush draw** (same suit).

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

Example: 3 players share the deck `3S TD 8H QC TS 4H 2D 6H 7C`; player 0 folds unless holding a pair
after two cards, player 1 never folds, player 2 folds unless holding a flush draw after two cards.

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

Player 0's first two cards (`3S`, `QC`) are not a pair, so player 0 folds and no card is drawn for them:
player 1's third card is `2D`, the next undrawn card, and `6H` goes to player 2. Player 2's first two
(`8H`, `4H`) share a suit, so player 2 stays in and ends with a flush, which beats player 1's pair of
tens; `7C` is never dealt.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Confirm with the interviewer that suit never breaks a tie once ranks match — the rules above already say
so, but some card games do rank suits, and it is cheap to ask before writing any comparison code. Then
map every hand to a single comparable tuple `(type_priority, tie_break)`, where `tie_break` has the same
shape for every hand of a given type: a 1-tuple for Three of a Kind, a 2-tuple `(pair_rank, kicker)` for
Pair, a 3-tuple of sorted ranks for High Card (and, from Part 2 on, for Flush). Once every hand reduces to
one such tuple, `compare_hands` and `rank_players` are one line each, and Part 2's flush and Part 3's
showdown reuse that same tuple with no new comparison logic.

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

Calling `rank_players` on the Part 1 example reproduces `[0, 1]`.

### Part 2

Flush slots between Three of a Kind and Pair, so the only priority that moves is Three of a Kind's,
from 2 to 3; the flush's own tie-break is the 3-tuple of sorted ranks already used for High Card.
Everything about the ranks is unchanged, so the new `_hand_key` calls the old one and patches its
result rather than restating the rank rules. `hand_type`, `compare_hands` and `rank_players` look up
`TYPE_NAMES` and `_hand_key` by name on every call, so the new rules reach all three untouched.

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

Calling `rank_players` on the Part 2 example now returns `[0]`.

### Part 3

`PokerRound` keeps one running counter, `calls_made`, and reads off both the pass number and the player
to visit from it with `divmod`, instead of tracking two separate loop variables. A single `next_card`
pointer into `deck` is advanced only when a card is actually dealt, which is exactly what makes a fold
"free" — the next player to draw always gets the next *undrawn* card, whether or not the player before
them folded.

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

Calling `play_round(3, ["3S", "TD", "8H", "QC", "TS", "4H", "2D", "6H", "7C"], [fold_unless_pair, never_fold, fold_unless_flush_draw])` reproduces the Part 3 example.

### Follow-ups

- Folding never consumes a `deck` card, so a `deck` sized for the worst case (`3 * num_players`, nobody
  folds) is always enough; a shorter one could run out mid-round if too few players end up folding.
- Every part does O(1) work per card (a hand has exactly three of them), so all three parts run in
  O(total cards dealt).
- A five-card hand needs more tie-break shapes (two pair, straight, full house, ...), but the same idea
  carries over: map every hand to a tuple whose first coordinate is the type priority and whose
  remainder is only ever compared within that type.
- Choosing a fold rule to beat a known opponent strategy is a different, harder question — the expected
  value of folding versus continuing, averaged over the unseen cards left in the deck — and is not
  covered by the rules or the code above.

<details>
<summary>Checks (runnable)</summary>

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
