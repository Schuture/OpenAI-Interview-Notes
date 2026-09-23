# Monster Battle

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding · object-oriented design | ★★★★☆ | Medium | SWE | oop-design, simulation | 3 parts |
<!-- meta:end -->

## Problem

Team `A` and Team `B` each have a non-empty, ordered list of monsters. Every monster starts with a
positive integer HP and a positive integer attack power. Complete the following three parts.

### Part 1 — Plain attacks

A monster is *alive* while its HP is above 0, and *eliminated* once its HP drops to 0 or below. A team
is *defeated* once every monster in its list is eliminated.

The battle is a fixed sequence of individual attacks:

- Team `A` attacks first; the two teams alternate after every single attack, whether or not that attack
  eliminated anyone.
- On a team's turn, the *attacker* is the first alive monster in its list (index 0 first), and the
  *defender* is the first alive monster in the other team's list.
- The defender's HP decreases by exactly the attacker's attack power; the attacker takes no damage back.
- The battle ends the moment one team is defeated. (Only the side being hit ever loses HP, so the two
  teams cannot become defeated on the same attack.)

Record one line for every event, in exactly this format (the line after `damage.` depends on whether the
defender is still alive):

```text
Match start: {A.name} takes on {B.name}
{attacker.name} hits {defender.name} for {damage} damage. {defender.name} has {defender.hp} HP left.
{attacker.name} hits {defender.name} for {damage} damage. {defender.name} is defeated!
Match over: {winner.name} wins!
```

```py
class Monster:
    def __init__(self, name: str, hp: int, attack: int):
        """hp and attack are positive integers."""

    def is_alive(self) -> bool: ...
    def take_damage(self, damage: int) -> None: ...


class Team:
    def __init__(self, name: str, monsters: list[Monster]):
        """monsters is the attack/defense order; it is non-empty."""

    def first_alive(self) -> "Monster | None": ...
    def is_defeated(self) -> bool: ...


def run_battle(team_a: Team, team_b: Team) -> list[str]:
    """Simulates the battle and returns the event log, one string per line."""
```

Example: team `Vanguard` has a single monster `Talonis` (hp 25, attack 14); team `Marsh` has `Sable`
(hp 10, attack 5) followed by `Thornback` (hp 20, attack 6). `run_battle` returns:

```text
Match start: Vanguard takes on Marsh
Talonis hits Sable for 14 damage. Sable is defeated!
Thornback hits Talonis for 6 damage. Talonis has 19 HP left.
Talonis hits Thornback for 14 damage. Thornback has 6 HP left.
Thornback hits Talonis for 6 damage. Talonis has 13 HP left.
Talonis hits Thornback for 14 damage. Thornback is defeated!
Match over: Vanguard wins!
```

### Part 2 — Elemental types

Every monster also has an *element*: one of `Ember`, `Tide`, `Bramble` or `Spark`. The elements form a
cycle of advantage — `Ember` is strong against `Bramble`, `Bramble` is strong against `Tide`, `Tide` is
strong against `Spark`, and `Spark` is strong against `Ember`. Being strong against an element deals
double damage to it (`2x`); the reverse direction deals half damage (`0.5x`). Every other ordered pair,
including a monster's element against itself, is neutral (`1x`). The full table, attacker's element in
the row, defender's element in the column:

| | Ember | Tide | Bramble | Spark |
| --- | --- | --- | --- | --- |
| Ember | 1x | 1x | 2x | 0.5x |
| Tide | 1x | 1x | 0.5x | 2x |
| Bramble | 0.5x | 2x | 1x | 1x |
| Spark | 2x | 0.5x | 1x | 1x |

Damage is $\lfloor \text{attack} \times \text{multiplier} \rfloor$; if that value is below 1, use 1
instead. The attacker and defender are still chosen exactly as in Part 1. Each hit line now also names
the multiplier that applied, written with no trailing `.0` (`2x`, `0.5x`, `1x`):

```text
{attacker.name} hits {defender.name} for {damage} damage ({multiplier}). {defender.name} has {defender.hp} HP left.
{attacker.name} hits {defender.name} for {damage} damage ({multiplier}). {defender.name} is defeated!
```

```py
class ElementType(Enum):
    EMBER = "Ember"
    TIDE = "Tide"
    BRAMBLE = "Bramble"
    SPARK = "Spark"


class Monster:
    def __init__(self, name: str, hp: int, attack: int, element: ElementType): ...
    def calculate_damage(self, defender: "Monster") -> int:
        """Damage this monster deals to defender, after the type chart and the rounding rule above."""
```

Example: team `Wildfire` has `Cinder` (hp 30, attack 9, `Ember`); team `Thicket` has `Mossken`
(hp 26, attack 7, `Bramble`).

```text
Match start: Wildfire takes on Thicket
Cinder hits Mossken for 18 damage (2x). Mossken has 8 HP left.
Mossken hits Cinder for 3 damage (0.5x). Cinder has 27 HP left.
Cinder hits Mossken for 18 damage (2x). Mossken is defeated!
Match over: Wildfire wins!
```

### Part 3 — Smart targeting

The attacking team no longer always leads with its first alive monster. Instead, among all of its alive
monsters, it picks the one whose `calculate_damage` against the current defender is highest; if several
tie for the highest, the one that appears earliest in the list attacks. The defender is unchanged from
Parts 1 and 2: whichever monster is alive and comes first in the defending team's list.

```py
class Team:
    def best_attacker_against(self, defender: Monster) -> "Monster | None":
        """The living monster on this team with the highest calculate_damage(defender);
        ties go to whichever of them appears first in the list."""
```

Example: team `Skyfleet` has `Talos` (hp 20, attack 10, `Spark`) followed by `Draketh`
(hp 25, attack 12, `Ember`); team `Depths` has `Coraline` (hp 22, attack 8, `Tide`).

```text
Match start: Skyfleet takes on Depths
Draketh hits Coraline for 12 damage (1x). Coraline has 10 HP left.
Coraline hits Talos for 16 damage (2x). Talos has 4 HP left.
Draketh hits Coraline for 12 damage (1x). Coraline is defeated!
Match over: Skyfleet wins!
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Confirm with the interviewer which rule Part 3 means: attack with whoever's `calculate_damage` against
the current defender is highest (the rule used below), or attack with whoever is type-advantaged against
the defender regardless of the raw number — the two disagree whenever a `1x` attacker's attack stat is
high enough to out-damage a `2x` one, e.g. attack `10` at `1x` (damage `10`) against attack `3` at `2x`
(damage `6`): the highest-damage rule below picks the first, the type-advantage rule the second.

Write `Monster` and `Team` first, then turn "who attacks" and "what the log line says about the hit"
into two swappable hooks with the simplest possible default; Part 2 only has to supply a new hit
description, and Part 3 only a new attacker choice — `run_battle` itself never needs to change again.

### Part 1

`choose_attacker` picks the attacker and gets the current defender as an argument even though Part 1's
default ignores it; that is what lets Part 3 plug in a defender-aware strategy later without touching
`run_battle`. `describe_hit` similarly starts as a no-op so the log has no multiplier tag yet.

```python
class Monster:
    def __init__(self, name, hp, attack):
        self.name = name
        self.hp = hp
        self.attack = attack

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, damage):
        self.hp -= damage

    def calculate_damage(self, defender):
        return self.attack


class Team:
    def __init__(self, name, monsters):
        self.name = name
        self.monsters = monsters

    def first_alive(self):
        return next((m for m in self.monsters if m.is_alive()), None)

    def is_defeated(self):
        return self.first_alive() is None


def default_choose_attacker(attacking_team, defender):
    return attacking_team.first_alive()      # NOTE: `defender` is unused here, only in Part 3's strategy


def default_describe_hit(attacker, defender):
    return ""


def run_battle(team_a, team_b, choose_attacker=default_choose_attacker, describe_hit=default_describe_hit):
    log = [f"Match start: {team_a.name} takes on {team_b.name}"]
    attacking, defending = team_a, team_b
    while attacking.first_alive() is not None and defending.first_alive() is not None:
        defender = defending.first_alive()
        attacker = choose_attacker(attacking, defender)
        damage = attacker.calculate_damage(defender)
        tag = describe_hit(attacker, defender)
        defender.take_damage(damage)              # NOTE: apply damage before reading is_alive()/hp below
        if defender.is_alive():
            log.append(f"{attacker.name} hits {defender.name} for {damage} damage{tag}. "
                        f"{defender.name} has {defender.hp} HP left.")
        else:
            log.append(f"{attacker.name} hits {defender.name} for {damage} damage{tag}. "
                        f"{defender.name} is defeated!")
        attacking, defending = defending, attacking
    winner = team_a if team_a.first_alive() is not None else team_b
    log.append(f"Match over: {winner.name} wins!")
    return log
```

### Part 2

The four elements form a single cycle of advantage, so the table only needs the four "strong against"
entries plus their four reverses; a pair that is not in `TYPE_CHART` (same element, or the two elements
that are neither strong nor weak against each other) defaults to `1.0`. `Monster.__init__` and
`calculate_damage` are attached to the `Monster` class of Part 1 instead of rewriting `is_alive` and
`take_damage`.

```python
from enum import Enum
import math


class ElementType(Enum):
    EMBER = "Ember"
    TIDE = "Tide"
    BRAMBLE = "Bramble"
    SPARK = "Spark"


TYPE_CHART = {
    (ElementType.EMBER, ElementType.BRAMBLE): 2.0,
    (ElementType.BRAMBLE, ElementType.EMBER): 0.5,
    (ElementType.BRAMBLE, ElementType.TIDE): 2.0,
    (ElementType.TIDE, ElementType.BRAMBLE): 0.5,
    (ElementType.TIDE, ElementType.SPARK): 2.0,
    (ElementType.SPARK, ElementType.TIDE): 0.5,
    (ElementType.SPARK, ElementType.EMBER): 2.0,
    (ElementType.EMBER, ElementType.SPARK): 0.5,
}


def type_multiplier(attacker_element, defender_element):
    return TYPE_CHART.get((attacker_element, defender_element), 1.0)


def format_multiplier(multiplier):
    return f"{int(multiplier)}x" if multiplier == int(multiplier) else f"{multiplier}x"


def type_effect_tag(attacker, defender):
    return f" ({format_multiplier(type_multiplier(attacker.element, defender.element))})"


def _init_with_element(self, name, hp, attack, element):
    self.name = name
    self.hp = hp
    self.attack = attack
    self.element = element


def calculate_damage_by_type(self, defender):
    multiplier = type_multiplier(self.element, defender.element)
    return max(1, math.floor(self.attack * multiplier))   # NOTE: floor(1 * 0.5) is 0; the rules say a hit
                                                            #       always deals at least 1


Monster.__init__ = _init_with_element          # attach to the Monster class of Part 1
Monster.calculate_damage = calculate_damage_by_type
```

Calling `run_battle(wildfire, thicket, describe_hit=type_effect_tag)` reproduces the Part 2 example.

### Part 3

`best_attacker_against` is attached to the `Team` class of Part 1. Python's `max` returns the first
element that reaches the maximum key when several tie, which is exactly the required tie-break.

```python
def best_attacker_against(self, defender):
    living = [m for m in self.monsters if m.is_alive()]
    # NOTE: max() keeps the FIRST element on a tie (checked: max(['a', 'b'], key={'a': 5, 'b': 5}.get) == 'a')
    return max(living, key=lambda m: m.calculate_damage(defender), default=None)


Team.best_attacker_against = best_attacker_against   # attach to the Team class of Part 1


def smart_choose_attacker(attacking_team, defender):
    return attacking_team.best_attacker_against(defender)
```

Calling `run_battle(skyfleet, depths, choose_attacker=smart_choose_attacker, describe_hit=type_effect_tag)`
reproduces the Part 3 example; `run_battle` is exactly the function from Part 1, unmodified.

### Follow-ups

- A `speed` field that decides who acts first each round would be a third hook (which side goes next),
  independent of the damage and targeting hooks above; the turn loop would not otherwise change.
- Area attacks or status effects (poison, stun) need a phase that resolves existing effects before the
  usual attack, the same before-then-act structure a day-by-day grid simulation uses.
- With many more elements, most pairs stay neutral, so keeping only the exceptions in a dict remains
  cheap; if the lookup ever becomes the hot loop, a small integer code per element and a 2D table is
  several times faster than the `Enum`-keyed dict, whose cost is hashing a tuple of two `Enum` members,
  not its size.
- Greedy targeting is minimax-optimal under these rules, not just a heuristic — for the win and for the
  winner's remaining HP: the choice of attacker changes nothing but how much HP the current defender
  loses, and a position in which the opponent has pointwise less HP is never worse for you (induction
  over the game tree, since the defender is forced and the attacker takes no damage). It stops being
  optimal as soon as the attacking team may also choose its target: a lone `Tide` monster (hp 7,
  attack 2) facing `Bramble` (hp 1, attack 6) then `Ember` (hp 2, attack 3) loses if it takes the bigger
  2-damage hit on `Ember`, and wins if it spends a 1-damage hit on `Bramble` first.
- Once a mechanic adds randomness (crits, miss chance), exact log comparison stops working; fix the seed
  so a run is reproducible, and check invariants instead — combined HP never increases, and the battle
  still terminates.

<details>
<summary>Checks (runnable)</summary>

```python
expected1 = [
    "Match start: Vanguard takes on Marsh",
    "Talonis hits Sable for 14 damage. Sable is defeated!",
    "Thornback hits Talonis for 6 damage. Talonis has 19 HP left.",
    "Talonis hits Thornback for 14 damage. Thornback has 6 HP left.",
    "Thornback hits Talonis for 6 damage. Talonis has 13 HP left.",
    "Talonis hits Thornback for 14 damage. Thornback is defeated!",
    "Match over: Vanguard wins!",
]
same = ElementType.EMBER  # NOTE: Monster requires an element by this point (Part 2 patched __init__);
                          #       giving everyone the same one makes every multiplier 1.0, i.e. Part 1
vanguard = Team("Vanguard", [Monster("Talonis", hp=25, attack=14, element=same)])
marsh = Team("Marsh", [Monster("Sable", hp=10, attack=5, element=same),
                       Monster("Thornback", hp=20, attack=6, element=same)])
assert run_battle(vanguard, marsh) == expected1

expected2 = [
    "Match start: Wildfire takes on Thicket",
    "Cinder hits Mossken for 18 damage (2x). Mossken has 8 HP left.",
    "Mossken hits Cinder for 3 damage (0.5x). Cinder has 27 HP left.",
    "Cinder hits Mossken for 18 damage (2x). Mossken is defeated!",
    "Match over: Wildfire wins!",
]
wildfire = Team("Wildfire", [Monster("Cinder", hp=30, attack=9, element=ElementType.EMBER)])
thicket = Team("Thicket", [Monster("Mossken", hp=26, attack=7, element=ElementType.BRAMBLE)])
assert run_battle(wildfire, thicket, describe_hit=type_effect_tag) == expected2

expected3 = [
    "Match start: Skyfleet takes on Depths",
    "Draketh hits Coraline for 12 damage (1x). Coraline has 10 HP left.",
    "Coraline hits Talos for 16 damage (2x). Talos has 4 HP left.",
    "Draketh hits Coraline for 12 damage (1x). Coraline is defeated!",
    "Match over: Skyfleet wins!",
]
skyfleet = Team("Skyfleet", [Monster("Talos", hp=20, attack=10, element=ElementType.SPARK),
                             Monster("Draketh", hp=25, attack=12, element=ElementType.EMBER)])
depths = Team("Depths", [Monster("Coraline", hp=22, attack=8, element=ElementType.TIDE)])
assert run_battle(skyfleet, depths, choose_attacker=smart_choose_attacker,
                  describe_hit=type_effect_tag) == expected3

# --- cross-validation against a naive simulator: no hooks, its own copy of the table, exact arithmetic ---
import copy
import random
from fractions import Fraction
from functools import lru_cache

GRID = {"Ember": ("1", "1", "2", "0.5"), "Tide": ("1", "1", "0.5", "2"),        # the rows of the table
        "Bramble": ("0.5", "2", "1", "1"), "Spark": ("2", "0.5", "1", "1")}      # in the statement
COLUMNS = ("Ember", "Tide", "Bramble", "Spark")
MAX_ROUNDS = 10_000  # safety cap for the random tests below; never hit since damage is always >= 1


def naive_battle(team_a, team_b, part):
    """Direct implementation of the rules of Part 1, 2 or 3, with no strategy abstraction."""
    log = [f"Match start: {team_a.name} takes on {team_b.name}"]
    teams, side, rounds = (team_a, team_b), 0, 0
    while all(any(m.hp > 0 for m in t.monsters) for t in teams):
        rounds += 1
        assert rounds <= MAX_ROUNDS, "battle did not terminate"
        defender = next(m for m in teams[1 - side].monsters if m.hp > 0)

        def hit(m):                                   # (damage, multiplier text) of m against defender
            if part == 1:
                return m.attack, ""
            text = GRID[m.element.value][COLUMNS.index(defender.element.value)]
            f = Fraction(text)
            return max(1, m.attack * f.numerator // f.denominator), f" ({text}x)"

        alive = [m for m in teams[side].monsters if m.hp > 0]
        attacker = alive[0]
        if part == 3:
            for m in alive[1:]:
                if hit(m)[0] > hit(attacker)[0]:     # strict >, so a tie keeps the earlier monster
                    attacker = m
        damage, tag = hit(attacker)
        defender.hp -= damage
        line = f"{attacker.name} hits {defender.name} for {damage} damage{tag}. "
        log.append(line + (f"{defender.name} has {defender.hp} HP left." if defender.hp > 0
                           else f"{defender.name} is defeated!"))
        side = 1 - side
    winner = team_a if any(m.hp > 0 for m in team_a.monsters) else team_b
    log.append(f"Match over: {winner.name} wins!")
    return log


def random_team(rng, name, size, fixed_element):
    monsters = []
    for i in range(size):
        hp, attack = rng.randint(1, 20), rng.randint(1, 6)   # NOTE: attack down to 1 exercises the clamp
        element = fixed_element if fixed_element is not None else rng.choice(list(ElementType))
        monsters.append(Monster(f"M{i}", hp, attack, element))
    return Team(name, monsters)


def cross_check(trials, seed, part, choose_attacker, describe_hit):
    rng = random.Random(seed)
    for _ in range(trials):
        # Part 1: one element for everyone makes every multiplier 1.0, so run_battle() at its defaults
        # follows exactly the Part 1 rules (calculate_damage still applies the chart and the clamp)
        fixed = ElementType.EMBER if part == 1 else None
        a = random_team(rng, "A", rng.randint(1, 4), fixed)
        b = random_team(rng, "B", rng.randint(1, 4), fixed)
        a2, b2 = copy.deepcopy(a), copy.deepcopy(b)
        got = run_battle(a, b, choose_attacker=choose_attacker, describe_hit=describe_hit)
        assert got == naive_battle(a2, b2, part)


cross_check(300, 0, 1, default_choose_attacker, default_describe_hit)
cross_check(300, 1, 2, default_choose_attacker, type_effect_tag)
cross_check(300, 2, 3, smart_choose_attacker, type_effect_tag)

# tie-break: equal damage against the current defender -> the earlier monster in the list attacks
tie_team = Team("Tied", [Monster("First", hp=30, attack=10, element=ElementType.EMBER),
                         Monster("Second", hp=30, attack=10, element=ElementType.EMBER)])
tie_defender = Monster("Target", hp=100, attack=1, element=ElementType.SPARK)
assert tie_team.best_attacker_against(tie_defender).name == "First"

# is_defeated() itself, unused inside run_battle but still part of the required interface
down = Monster("Down", hp=1, attack=1, element=ElementType.EMBER)
lone_team = Team("Lone", [down])
assert lone_team.is_defeated() is False
down.take_damage(1)
assert lone_team.is_defeated() is True

# the type chart is antisymmetric: attacker beats defender iff defender is weak to attacker
for x in ElementType:
    for y in ElementType:
        mx, my = type_multiplier(x, y), type_multiplier(y, x)
        assert (mx, my) in {(1.0, 1.0), (2.0, 0.5), (0.5, 2.0)}


# --- Part 3's greedy choice is minimax-optimal: full game-tree search over the attacker choice ---
def game_value(team_a, team_b, searching):
    """Signed HP left on the winning side (positive: team_a wins). The sides in `searching` try every
    alive attacker; the others take the greedy one. The defender is always the first alive monster."""
    rosters = (team_a.monsters, team_b.monsters)

    @lru_cache(maxsize=None)
    def value(hp_a, hp_b, side):
        if max(hp_a) <= 0:
            return -sum(h for h in hp_b if h > 0)
        if max(hp_b) <= 0:
            return sum(h for h in hp_a if h > 0)
        hp = (hp_a, hp_b)
        d = next(i for i, h in enumerate(hp[1 - side]) if h > 0)
        defender = rosters[1 - side][d]
        alive = [m for m, h in zip(rosters[side], hp[side]) if h > 0]
        options = alive if side in searching else [max(alive, key=lambda m: m.calculate_damage(defender))]
        results = []
        for attacker in options:
            new = list(hp[1 - side])
            new[d] -= attacker.calculate_damage(defender)
            nxt = (hp_a, tuple(new)) if side == 0 else (tuple(new), hp_b)
            results.append(value(*nxt, 1 - side))
        return max(results) if side == 0 else min(results)   # NOTE: team_a maximises, team_b minimises

    return value(tuple(m.hp for m in team_a.monsters), tuple(m.hp for m in team_b.monsters), 0)


rng = random.Random(3)
for _ in range(150):
    a = random_team(rng, "A", rng.randint(1, 3), None)
    b = random_team(rng, "B", rng.randint(1, 3), None)
    best = game_value(a, b, searching={0, 1})           # both sides free
    # greedy is a best response for either side, and greedy vs greedy reaches the same value
    assert best == game_value(a, b, {0}) == game_value(a, b, {1}) == game_value(a, b, set())

# ... but not once the attacker may also pick its target: Ripple loses by taking its biggest hit
ripple = Monster("Ripple", hp=7, attack=2, element=ElementType.TIDE)
thistle = Monster("Thistle", hp=1, attack=6, element=ElementType.BRAMBLE)
ashen = Monster("Ashen", hp=2, attack=3, element=ElementType.EMBER)
assert ripple.calculate_damage(ashen) == 2 > ripple.calculate_damage(thistle) == 1   # greedy: hit Ashen
assert thistle.calculate_damage(ripple) == 12 >= ripple.hp                           # then Thistle kills Ripple
assert ripple.calculate_damage(thistle) >= thistle.hp and ashen.calculate_damage(ripple) < ripple.hp \
    and ripple.calculate_damage(ashen) >= ashen.hp    # Thistle first, survive one hit, then Ashen: a win
```

</details>

</details>
