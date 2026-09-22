# 怪兽对战

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 · 面向对象设计 | ★★★★☆ | 中等 | SWE | oop-design, simulation | 3 个部分 |
<!-- meta:end -->

## 题目

队伍 `A` 和队伍 `B` 各自维护一个非空的、有序的怪兽列表。每个怪兽初始时都有一个正整数的 HP 和一个正整数的攻击力。
完成下面三个部分。

### Part 1 —— 普通攻击

一个怪兽在 HP 大于 0 时是*存活*（alive）的，HP 降到 0 或以下就被*淘汰*（eliminated）。一个队伍在它列表里的
全部怪兽都被淘汰后就是*落败*（defeated）的。

整场战斗是一串固定顺序的单次攻击：

- 队伍 `A` 先手；此后每完成一次攻击，双方就交换攻防身份，不论这次攻击有没有淘汰谁。
- 轮到某个队伍时，*攻击者*（attacker）是它列表里第一个存活的怪兽（下标 0 优先），*防御者*（defender）
  是对方列表里第一个存活的怪兽。
- 防御者的 HP 恰好减少攻击者的攻击力；攻击者不会受到反击伤害。
- 一旦某个队伍落败，战斗立刻结束。（每次攻击只会让被打的一方掉血，所以不可能出现两个队伍在同一次攻击里
  同时落败的情况。）

为每个事件记录一行文本，格式必须与下面完全一致（`damage.` 之后接哪一句，取决于防御者是否还活着）：

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

例子：队伍 `Vanguard` 只有一个怪兽 `Talonis`（hp 25，攻击力 14）；队伍 `Marsh` 依次是 `Sable`
（hp 10，攻击力 5）和 `Thornback`（hp 20，攻击力 6）。`run_battle` 返回：

```text
Match start: Vanguard takes on Marsh
Talonis hits Sable for 14 damage. Sable is defeated!
Thornback hits Talonis for 6 damage. Talonis has 19 HP left.
Talonis hits Thornback for 14 damage. Thornback has 6 HP left.
Thornback hits Talonis for 6 damage. Talonis has 13 HP left.
Talonis hits Thornback for 14 damage. Thornback is defeated!
Match over: Vanguard wins!
```

### Part 2 —— 元素属性

每个怪兽现在还有一个*元素*（element）：`Ember`、`Tide`、`Bramble`、`Spark` 四者之一。这四种元素构成一个
克制的环：`Ember` 克制 `Bramble`，`Bramble` 克制 `Tide`，`Tide` 克制 `Spark`，`Spark` 克制 `Ember`。
克制对方时造成双倍伤害（`2x`）；被克制的一方朝反方向打则只造成一半伤害（`0.5x`）。其余所有有序组合——
包括一个怪兽对同种元素——都是中性的（`1x`）。完整的表如下，行是攻击方的元素，列是防守方的元素：

| | Ember | Tide | Bramble | Spark |
| --- | --- | --- | --- | --- |
| Ember | 1x | 1x | 2x | 0.5x |
| Tide | 1x | 1x | 0.5x | 2x |
| Bramble | 0.5x | 2x | 1x | 1x |
| Spark | 2x | 0.5x | 1x | 1x |

伤害等于 $\lfloor \text{attack} \times \text{multiplier} \rfloor$；如果这个值小于 1，就取 1。攻击者与
防御者的选取方式和 Part 1 完全相同。每一条命中记录现在还要标出生效的倍率，写法是去掉多余的 `.0`
（`2x`、`0.5x`、`1x`）：

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

例子：队伍 `Wildfire` 有 `Cinder`（hp 30，攻击力 9，`Ember`）；队伍 `Thicket` 有 `Mossken`
（hp 26，攻击力 7，`Bramble`）。

```text
Match start: Wildfire takes on Thicket
Cinder hits Mossken for 18 damage (2x). Mossken has 8 HP left.
Mossken hits Cinder for 3 damage (0.5x). Cinder has 27 HP left.
Cinder hits Mossken for 18 damage (2x). Mossken is defeated!
Match over: Wildfire wins!
```

### Part 3 —— 更聪明的出手选择

进攻方不再总是让第一个存活的怪兽出手。它会在自己全部存活的怪兽里，挑选对当前防御者 `calculate_damage`
最高的那一个出手；如果有并列最高的，由列表里排在更前面的那个出手。防御者的选取方式和 Part 1、Part 2 完全
相同：始终是防守方队伍里第一个存活的怪兽。

```py
class Team:
    def best_attacker_against(self, defender: Monster) -> "Monster | None":
        """The living monster on this team with the highest calculate_damage(defender);
        ties go to whichever of them appears first in the list."""
```

例子：队伍 `Skyfleet` 依次是 `Talos`（hp 20，攻击力 10，`Spark`）和 `Draketh`
（hp 25，攻击力 12，`Ember`）；队伍 `Depths` 有 `Coraline`（hp 22，攻击力 8，`Tide`）。

```text
Match start: Skyfleet takes on Depths
Draketh hits Coraline for 12 damage (1x). Coraline has 10 HP left.
Coraline hits Talos for 16 damage (2x). Talos has 4 HP left.
Draketh hits Coraline for 12 damage (1x). Coraline is defeated!
Match over: Skyfleet wins!
```

## 参考解答

<details>
<summary>展开参考解答</summary>

先把 `Monster` 和 `Team` 写好，再把“谁来攻击”和“日志里要不要给这次命中加说明”做成两个可替换的钩子，
各自用最简单的默认实现；Part 2 只需要提供一个新的命中说明，Part 3 只需要提供一个新的攻击者选择，
`run_battle` 本身此后再也不用改动。

### Part 1

`choose_attacker` 用来挑选攻击者，它接收当前防御者作为参数，尽管 Part 1 的默认实现根本不看这个参数——
正是这一点让 Part 3 之后可以插入一个会看防御者的策略，而不用改动 `run_battle`。`describe_hit`
同样先做成空操作，日志里暂时不会带任何倍率说明。

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

四种元素只构成一个环，所以表里只需要写四条“克制”和它们反过来的四条；`TYPE_CHART` 里查不到的组合
（同一种元素，或者环上互不相邻的那两个）默认是 `1.0`。`Monster.__init__` 和 `calculate_damage`
是加到 Part 1 的 `Monster` 类上的两个新实现，`is_alive`、`take_damage` 都不用重写。

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

调用 `run_battle(wildfire, thicket, describe_hit=type_effect_tag)` 就能得到 Part 2 的例子。

### Part 3

`best_attacker_against` 加在 Part 1 的 `Team` 类上。Python 的 `max` 在多个元素并列最大值时，返回的
是先出现的那一个，正好就是题目要求的并列规则。

```python
def best_attacker_against(self, defender):
    living = [m for m in self.monsters if m.is_alive()]
    # NOTE: max() keeps the FIRST element on a tie (checked: max(['a', 'b'], key={'a': 5, 'b': 5}.get) == 'a')
    return max(living, key=lambda m: m.calculate_damage(defender), default=None)


Team.best_attacker_against = best_attacker_against   # attach to the Team class of Part 1


def smart_choose_attacker(attacking_team, defender):
    return attacking_team.best_attacker_against(defender)
```

调用 `run_battle(skyfleet, depths, choose_attacker=smart_choose_attacker, describe_hit=type_effect_tag)`
就能得到 Part 3 的例子；这里的 `run_battle` 就是 Part 1 那一个，一个字都没改。

### 追问

- 一个决定每轮谁先出手的 `speed` 字段可以做成第三个钩子（轮到哪一方），和上面伤害、选目标这两个钩子相互独立，
  回合的主循环不需要再改。
- 群体攻击或状态效果（中毒、眩晕）需要在照常攻击之前先加一个“结算已有效果”的阶段，
  和逐天模拟网格类问题里那种“先结算、再行动”的结构是一样的。
- 元素种类变多之后，大多数组合仍然是中性的，所以只在字典里存例外仍然划算；如果查表成了热点，
  给每种元素编一个小整数、用二维表存倍率，会比用 `Enum` 元组当键的字典快好几倍——字典慢在给两个 `Enum`
  成员组成的元组算哈希，和表的大小无关。
- 在这套规则下，贪心选攻击者不只是一个启发式，而是极小极大（minimax）意义下的最优策略——先比胜负，
  再比赢家剩余的 HP：派谁出手只改变当前防御者掉多少血，而对手的 HP 逐项更少的局面对自己永远不会更差
  （对博弈树归纳即可，因为防御者是固定的、攻击者又不会掉血）。一旦进攻方还能自己挑目标，贪心就不再最优：
  单独一只 `Tide` 怪兽（hp 7，攻击力 2）面对先 `Bramble`（hp 1，攻击力 6）后 `Ember`（hp 2，攻击力 3）
  的队伍，先打 `Ember` 那一下伤害更高的 2 点会输，先花 1 点伤害解决 `Bramble` 反而会赢。
- 一旦引入随机性（暴击、命中率），逐字比对日志就不再适用；应该固定随机种子让单次结果可复现，
  再退化为检查不变量——双方合计 HP 只会减少，战斗仍然会终止。

<details>
<summary>验证代码（可运行）</summary>

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
