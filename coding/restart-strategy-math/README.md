# Restart Strategies under a Known Mean (Las Vegas)

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Spoken maths · probability, no code | ★★★☆☆ | Hard | RS · RE | probability, inequalities, algorithm-design | 6 oral parts |
<!-- meta:end -->

## Problem

An LLM inference service needs a random time $T \ge 0$, measured in minutes, to complete one request.
The distribution of $T$ is unknown, and only its mean $E[T] = 1$ is given.

A running request may be abandoned and *restarted*. Every attempt draws a new completion time from the
same distribution, independently of all earlier attempts, and restarting itself takes no time. An
attempt with *timeout* $t$ runs for at most $t$ minutes: it *succeeds* if its completion time satisfies
$T \le t$, and otherwise it is abandoned after $t$ minutes. A *schedule* is a list of timeouts
$(t_1, \dots, t_m)$ with $t_1 + \dots + t_m = 10$, the total budget in minutes. Attempt $i$ runs with
timeout $t_i$ and starts when attempt $i - 1$ is abandoned. The schedule succeeds if one of its
attempts succeeds.

Example: the schedule $(2, 3, 5)$, when the three attempts draw the completion times 2.6, 3.4 and 4.1.

```text
attempt 1: minutes 0 to 2     2.6 > 2, abandoned
attempt 2: minutes 2 to 5     3.4 > 3, abandoned
attempt 3: minutes 5 to 10    4.1 <= 5, succeeds at minute 5 + 4.1 = 9.1
```

The *guarantee* of a schedule is the largest number $g$ such that the schedule succeeds with
probability at least $g$ under every distribution with $T \ge 0$ and $E[T] = 1$.

Each of the six parts asks for a derivation. There is nothing to implement.

### Part 1 — A tail bound

What is the best upper bound on $P(T > 5)$ that holds for every such distribution? Is there a
distribution for which it holds with equality?

### Part 2 — One restart

Find the guarantee of the schedule $(5, 5)$ and compare it with that of the single attempt $(10)$.

### Part 3 — Several restarts, budget split equally

With $N$ restarts there are $N + 1$ attempts. The budget is divided equally among them, so every
timeout is $10 / (N + 1)$. Find the guarantee for every $N \ge 0$.

### Part 4 — The best number of equal attempts

Which number of attempts $m = N + 1$ gives the schedule of Part 3 its largest guarantee, and how large
is that guarantee?

### Part 5 — A distribution for which restarting changes nothing

Suppose for this part that the distribution of $T$ is known. Is there a distribution with $E[T] = 1$
under which all schedules, including the single attempt $(10)$, succeed with the same probability?

### Part 6 — Unequal timeouts

The distribution is again unknown apart from $E[T] = 1$, and the timeouts of a schedule may differ. Is
there a schedule with a larger guarantee than the best schedule of Part 4? Find the best schedule with
two attempts, then describe what happens with $m$ attempts. Finally, say how the choice of a schedule
changes when the distribution is known.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Settle two things with the interviewer first: attempts are independent and restarting is free, and the
goal is the probability of finishing within the budget, not the expected time. For every number you
give, say whether it is a bound for all distributions, the exact worst case, or the exact value for one
known distribution.

### Part 1

Since $T \ge 0$, the inequality $a \cdot \mathbf{1}[T \ge a] \le T$ holds for every $a > 0$. Taking
expectations gives Markov's inequality $P(T \ge a) \le E[T] / a$, hence

$$P(T > 5) \le P(T \ge 5) \le \frac{1}{5}.$$

For $P(T \ge 5)$ the bound is attained: $T = 5$ with probability $1/5$ and $T = 0$ otherwise has mean 1.
For $P(T > 5)$ it is not, because $P(T > 5) = 1/5$ would force
$E[T] \ge E\bigl[T \cdot \mathbf{1}[T > 5]\bigr] > 5 \cdot \frac{1}{5} = 1$. It is approached, however:
$T = 5 + \varepsilon$ with probability $1/(5 + \varepsilon)$ and $T = 0$ otherwise again has mean 1, and
its tail $P(T > 5) = 1/(5 + \varepsilon)$ tends to $1/5$. So $1/5$ is the best bound, as a supremum and
not as a maximum. In the same way $S(t) = P(T > t)$, the *survival function* of $T$, has
$\sup S(t) = 1/t$ for every $t \ge 1$, approached by the mass $1/t$ just above $t$.

### Part 2

The two attempts are independent, so the schedule fails with probability $S(5)^2 \le 1/25$. The
distribution of Part 1 brings both factors close to $1/5$ at once, because both attempts have the same
timeout. The guarantee is therefore exactly $1 - 1/25 = 0.96$. The single attempt $(10)$ has
$1 - 1/10 = 0.9$.

### Part 3

With $m = N + 1$ attempts and the timeout $t = 10/m$, the schedule fails with probability $S(t)^m$,
which is the exact answer when $S$ is known. With only the mean known, Part 1 gives
$S(t) \le 1/t = m/10$ for $m \le 10$, and the mass just above $t$ again brings all $m$ factors
arbitrarily close to this bound at once:

$$\text{guarantee} = 1 - \left(\frac{m}{10}\right)^{m} = 1 - \left(\frac{N+1}{10}\right)^{N+1}, \qquad N + 1 \le 10.$$

For $N + 1 \ge 10$ the timeout is at most 1 and the guarantee is 0. A request that always takes
$T = 1$ never finishes within a timeout below 1, and for the timeout 1 the distribution
$T = 1 + \varepsilon$ with probability $1/(1 + \varepsilon)$, $T = 0$ otherwise, fails with probability
$(1 + \varepsilon)^{-10} \to 1$.

### Part 4

Minimise the failure probability $(m/10)^m$ through its logarithm $f(m) = m \ln(m/10)$, first over
real $m$:

$$f'(m) = \ln\frac{m}{10} + 1 = 0 \quad\Longrightarrow\quad m = \frac{10}{e} \approx 3.68 .$$

$f''(m) = 1/m > 0$, so $f$ is convex and the best integer is 3 or 4. Since $0.3^3 = 0.027$ and
$0.4^4 = 0.0256$, four attempts of 2.5 minutes each are best, with the guarantee
$1 - 0.0256 = 0.9744$. For comparison, $m = 2$ gives $0.96$ and $m = 5$ gives $0.9688$. By Part 3 these
numbers are the exact worst case of each schedule, not only bounds. The trade-off: every additional
attempt adds a factor to the product, but moves each factor $m/10$ closer to 1. The real-valued optimum
has the timeout $10/m = e$ for every budget, so under this criterion an attempt is abandoned after
about $e \approx 2.7$ times the mean.

### Part 5

Yes: the exponential distribution with rate 1, $S(t) = e^{-t}$, which has mean 1. Every schedule fails
with probability

$$\prod_{i=1}^{m} S(t_i) = e^{-(t_1 + \dots + t_m)} = e^{-10} \approx 4.5 \times 10^{-5}.$$

This is the *memoryless property* $P(T > s + t \mid T > s) = P(T > t)$: an attempt that has already run
for $s$ minutes is exactly as good as a fresh one. Conversely, if all schedules fail with the same
probability, then $S(s + t) = S(s) S(t)$ whenever $s + t \le 10$, whose only non-increasing solutions
are $S(t) = e^{-\lambda t}$, so within the budget the distribution has to be exponential.

### Part 6

The answer depends on how a schedule is judged.

**By the product of the Markov bounds.** Bounding each factor separately gives
$\prod_i S(t_i) \le 1/(t_1 \cdots t_m)$ when all $t_i \ge 1$ (a timeout below 1 only contributes the
factor 1), and by the AM–GM inequality a product with a fixed sum is largest when all factors are
equal. Judged by this bound, unequal timeouts never help and Part 4 is final: $(2.5, 7.5)$ scores
$1/(2.5 \cdot 7.5) \approx 0.053$, worse than the $0.04$ of $(5, 5)$.

**By the true worst case.** For unequal timeouts the product bound is not the guarantee. The factor
$S(t_i)$ comes close to $1/t_i$ only if the mass $1/t_i$ sits just above $t_i$, which uses up the
whole mean. All attempts draw from the same distribution, and one distribution cannot do this at two
different timeouts. Think of the distribution as chosen by an *adversary* who knows the schedule.

*Two attempts.* Let the timeouts be $a \le b$ with $a + b = 10$, and write $s_1 = S(a)$, $s_2 = S(b)$,
so $s_1 \ge s_2$. Since $E[T] = \int_0^\infty S(t)\;dt$ and $S$ is non-increasing,

$$1 = E[T] \ge \int_0^a S(t)\;dt + \int_a^b S(t)\;dt \ge a s_1 + (b - a) s_2 .$$

Conversely, every pair $1 \ge s_1 \ge s_2 \ge 0$ that satisfies this inequality is approached by a
distribution with mean 1: mass $s_2$ just above $b$, mass $s_1 - s_2$ just above $a$, the rest at 0
(a mean below 1 is made up by an arbitrarily small mass moved far out). The adversary therefore
maximises $s_1 s_2$ under these constraints. By AM–GM,

$$a s_1 \cdot (b - a) s_2 \le \left(\frac{a s_1 + (b - a) s_2}{2}\right)^{2} \le \frac{1}{4}, \qquad\text{so}\qquad s_1 s_2 \le \frac{1}{4a(b - a)} = \frac{1}{4a(10 - 2a)},$$

with equality for $s_1 = 1/(2a)$ and $s_2 = 1/(2(10 - 2a))$. This pair satisfies $s_2 \le s_1 \le 1$
exactly when $1/2 \le a \le 10/3$, and the worst-case failure probability is then $1/(4a(10 - 2a))$.
It is smallest where $a(10 - 2a)$ is largest, at $a = 2.5$:

$$\text{schedule } (2.5,\; 7.5), \qquad \text{worst-case failure probability } \frac{1}{4 \cdot 2.5 \cdot 5} = \frac{1}{50}, \qquad \text{guarantee } 0.98 .$$

Outside that range a constraint is active: for $a > 10/3$ the maximum is at $s_1 = s_2 = 1/b$, with
failure probability $1/(10 - a)^2 > 9/400$, and for $a < 1/2$ it is at $s_1 = 1$, with failure
probability $(1 - a)/(10 - 2a) > 1/18$. Both exceed $1/50$, so $(2.5, 7.5)$ is the best schedule with
two attempts. Its guarantee $0.98$ beats the $0.96$ of $(5, 5)$ and the $0.9744$ of four equal attempts.
The adversary's distribution against it has mass $0.1$ just above $2.5$, mass $0.1$ just above $7.5$ and
mass $0.8$ at 0.

*With $m$ attempts.* Sort the timeouts, $t_1 \le \dots \le t_m$, and let $d_i = t_i - t_{i-1}$ with
$t_0 = 0$, and $s_i = S(t_i)$. The integral argument gives $\sum_i d_i s_i \le 1$ for every distribution,
and the budget reads $\sum_i (m - i + 1) d_i = \sum_i t_i = 10$. Two observations settle $m \le 10$:

- With the gaps $d_i = \frac{10}{m (m - i + 1)}$, AM–GM over the $m$ terms $d_i s_i$ gives
  $\prod_i d_i s_i \le m^{-m}$, so $\prod_i s_i \le 1 / (m^m \prod_i d_i) = m!/10^m$ for every distribution.
- Against any schedule the adversary can put mass $1/10$ just above every timeout and the rest at 0.
  The mean is $\sum_i t_i / 10 = 1$ and $S(t_i) \ge (m - i + 1)/10$, so the failure probability comes
  arbitrarily close to a value of at least $m!/10^m$.

The best guarantee with $m \le 10$ attempts is therefore exactly $1 - m!/10^m$: $0.98$ for $m = 2$,
$0.994$ for $m = 3$ with the timeouts $(10/9,\; 25/9,\; 55/9) \approx (1.11,\; 2.78,\; 6.11)$, and $0.9976$
for $m = 4$. One more attempt multiplies the failure probability by $(m + 1)/10$, so it falls until
$m = 9$, where $9!/10^9 = 10!/10^{10} \approx 3.6 \times 10^{-4}$. With more than 10 attempts the
adversary treats the 10 largest timeouts in the same way, so no schedule of any length has a guarantee
above $1 - 9!/10^9 \approx 0.9996$.

*Known distribution.* The failure probability $\prod_i S(t_i)$ is then exact, and the *hazard rate*
$h(t) = f(t)/S(t)$, with $f$ the density of $T$, decides. From $\ln S(t) = -\int_0^t h(u)\;du$, a
decreasing $h$ gives $S(s + t) \ge S(s) S(t)$, so splitting an attempt lowers the failure probability.
An increasing $h$ reverses the inequality and the single attempt $(10)$ is best, and a constant $h$ is
the exponential distribution of Part 5.

### Follow-ups

- Known distribution, and the goal is the expected time until success, without a budget: a fixed cutoff
  $\tau$ gives $E = E[\min(T, \tau)] + S(\tau) E$, that is $E = E[\min(T, \tau)] / P(T \le \tau)$. The
  optimal strategy uses the cutoff $\tau^{\ast}$ that minimises this ratio in every attempt (Luby,
  Sinclair and Zuckerman).
- The same goal with an unknown distribution: using Luby's universal sequence
  $1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8, \dots$ as cutoffs has expected time
  $O(T_{\mathrm{opt}} \log T_{\mathrm{opt}})$, where $T_{\mathrm{opt}}$ is the expected time under
  $\tau^{\ast}$. No strategy that ignores the distribution is better by more than a constant factor.
- If the variance $\sigma^2$ is known as well, Cantelli's inequality
  $P(T \ge 1 + \lambda) \le \sigma^2 / (\sigma^2 + \lambda^2)$ replaces Markov's. With $\sigma = 1$ it gives
  $P(T \ge 5) \le 1/17$, attained by $T = 5$ with probability $1/17$ and $T = 0.75$ otherwise.
- If every restart costs $c$ minutes, $m$ attempts leave $10 - (m - 1)c$ minutes for the timeouts, and
  this number replaces 10 in all the formulas. With $c = 0.5$ the best number of attempts drops from 4
  to 3 for equal timeouts and from 9 to 5 for unequal ones.
- In a real service the attempts are not independent: a request that is slow because of its own length
  or a loaded replica is slow again after a restart. The usual remedy is a hedged request, which sends
  a second copy to another replica after a delay and takes whichever answer arrives first.

<details>
<summary>Checks (runnable)</summary>

```python
import itertools
import math

import numpy as np
from scipy.optimize import minimize
from scipy.stats import expon, weibull_min

BUDGET = 10.0
rng = np.random.default_rng(0)


class Discrete:
    """A distribution on finitely many points, evaluated exactly."""

    def __init__(self, values, probs):
        self.values, self.probs = np.asarray(values, dtype=float), np.asarray(probs, dtype=float)
        assert np.all(self.values >= 0) and np.all(self.probs >= 0) and math.isclose(self.probs.sum(), 1.0)

    def mean(self):
        return float(self.values @ self.probs)

    def sf(self, t):                                    # NOTE: strict, P(T > t): an attempt with T == t succeeds
        return float(self.probs[self.values > t].sum())


def failure_probability(sf, timeouts):
    """P(every attempt is abandoned) for independent attempts; sf(t) = P(T > t)."""
    return math.prod(sf(t) for t in timeouts)


def atoms_above(timeouts, masses, eps):
    """Mass masses[i] / (1 + eps) at timeouts[i] * (1 + eps), the rest at 0: the mean does not depend on eps."""
    masses = np.asarray(masses, dtype=float) / (1 + eps)
    return Discrete(np.append(np.asarray(timeouts) * (1 + eps), 0.0), np.append(masses, 1.0 - masses.sum()))


# ---- Part 1: Markov's bound is attained for P(T >= 5), and only approached for P(T > 5)
two_point = Discrete([0.0, 5.0], [0.8, 0.2])
assert math.isclose(two_point.mean(), 1.0)
assert math.isclose(two_point.probs[two_point.values >= 5].sum(), 0.2) and two_point.sf(5) == 0.0
for eps in (1e-2, 1e-4, 1e-6):
    dist = atoms_above([5.0], [1 / 5], eps)
    assert math.isclose(dist.mean(), 1.0) and 0.2 / (1 + eps) <= dist.sf(5) < 0.2

# ---- Parts 2-4: equal timeouts; the two-point distribution approaches the product of Markov bounds
equal_bound = {m: (m / BUDGET) ** m for m in range(1, 11)}
assert math.isclose(1 - equal_bound[2], 24 / 25)
assert min(equal_bound, key=equal_bound.get) == 4 and math.isclose(1 - equal_bound[4], 0.9744)
assert 3 < BUDGET / math.e < 4 and equal_bound[3] > equal_bound[4] < equal_bound[5]
for m in range(1, 11):
    t = BUDGET / m
    dist = atoms_above([t], [1 / t], 1e-9)
    assert math.isclose(dist.mean(), 1.0)
    assert math.isclose(failure_probability(dist.sf, [t] * m), equal_bound[m], rel_tol=1e-7)
assert failure_probability(Discrete([1.0], [1.0]).sf, [BUDGET / 11] * 11) == 1.0   # timeout < 1: T = 1 always fails

# ---- Part 5: for the exponential distribution every schedule fails with probability e^-10
for m in (1, 2, 5, 40):
    schedule = rng.dirichlet(np.ones(m)) * BUDGET
    assert math.isclose(failure_probability(expon.sf, schedule), math.exp(-BUDGET), rel_tol=1e-9)


def simulate_failure(sample, timeouts, runs=400_000):
    """Monte Carlo version of failure_probability; sample(shape) draws independent completion times."""
    draws = sample((runs, len(timeouts)))
    return float(np.mean(np.all(draws > np.asarray(timeouts), axis=1)))


for schedule in ([3.0], [1.0, 2.0], [0.5, 0.5, 2.0]):       # a budget of 3, so that e^-3 is visible in a simulation
    assert abs(simulate_failure(lambda shape: rng.exponential(size=shape), schedule) - math.exp(-3)) < 1.5e-3


# ---- Part 6: the adversary's problem, solved numerically
def worst_case_failure(timeouts):
    """sup of prod_i S(t_i) over all distributions with T >= 0 and E[T] = 1. With s_i = S(t_i) for the
    sorted timeouts and the gaps d_i = t_i - t_(i-1): maximise sum_i log s_i (concave) subject to
    sum_i d_i s_i <= 1 and 1 >= s_1 >= ... >= s_m (linear)."""
    t = np.sort(np.asarray(timeouts, dtype=float))
    d = np.diff(t, prepend=0.0)
    m = len(t)
    order = np.eye(m)[:-1] - np.eye(m)[1:]              # row i: s_i - s_(i+1) >= 0
    constraints = [{"type": "ineq", "fun": lambda s: 1.0 - d @ s, "jac": lambda s: -d},
                   {"type": "ineq", "fun": lambda s: order @ s, "jac": lambda s: order}]
    start = np.full(m, min(1.0, 0.5 / t[-1]))           # feasible: 0.5 * sum(d) / t_m = 0.5
    result = minimize(lambda s: -np.log(s).sum(), start, jac=lambda s: -1.0 / s, method="SLSQP",
                      bounds=[(1e-9, 1.0)] * m, constraints=constraints, options={"ftol": 1e-12, "maxiter": 1000})
    return math.exp(-result.fun), result.x


def best_schedule(m):
    gaps = [BUDGET / (m * (m - i)) for i in range(m)]   # d_i = 10 / (m (m - i + 1)) for i = 1..m
    return np.cumsum(gaps)


# m = 2: the solver reproduces the piecewise closed form of the worst case of (a, 10 - a)
for a in np.arange(0.05, 5.0001, 0.05):
    if a < 0.5:
        closed_form = (1 - a) / (BUDGET - 2 * a)
    elif a <= BUDGET / 3:
        closed_form = 1 / (4 * a * (BUDGET - 2 * a))
    else:
        closed_form = 1 / (BUDGET - a) ** 2
    assert math.isclose(worst_case_failure([a, BUDGET - a])[0], closed_form, rel_tol=1e-6)


def minimax(m, step):
    """Designer: grid search over schedules with m attempts, then Nelder-Mead from the best grid point."""
    n = round(BUDGET / step)
    grid = [np.diff((0,) + cuts + (n,)) * step for cuts in itertools.combinations(range(1, n), m - 1)]
    grid = [t for t in grid if np.all(np.diff(t) >= 0)]                        # sorted schedules only
    start = min(grid, key=lambda t: worst_case_failure(t)[0])

    def objective(z):                                   # z = log-weights, so every schedule sums to the budget
        w = np.exp(z - z.max())
        return worst_case_failure(w / w.sum() * BUDGET)[0]

    result = minimize(objective, np.log(start), method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-13})
    w = np.exp(result.x - result.x.max())
    return result.fun, np.sort(w / w.sum() * BUDGET)


for m, step in ((2, 0.1), (3, 0.5)):
    value, schedule = minimax(m, step)
    assert math.isclose(value, math.factorial(m) / BUDGET ** m, rel_tol=1e-5)
    assert np.allclose(schedule, best_schedule(m), atol=2e-3)
assert np.allclose(best_schedule(2), [2.5, 7.5]) and np.allclose(best_schedule(3), [10 / 9, 25 / 9, 55 / 9])

# the closed-form schedule attains m! / 10^m, and the solver's s_i are (m - i + 1) / 10
for m in range(1, 11):
    value, s = worst_case_failure(best_schedule(m))
    assert math.isclose(value, math.factorial(m) / BUDGET ** m, rel_tol=1e-6)
    assert np.allclose(s, np.arange(m, 0, -1) / BUDGET, atol=1e-4)
assert math.isclose(math.factorial(9) / 1e9, math.factorial(10) / 1e10) and round(math.factorial(9) / 1e9, 6) == 0.000363

# no schedule beats it: mass 1/10 just above each of the (at most 10) largest timeouts has mean <= 1
for _ in range(200):
    m = int(rng.integers(1, 15))
    schedule = np.sort(rng.dirichlet(np.ones(m)) * BUDGET)
    k = min(m, 10)
    dist = atoms_above(schedule[-k:], [1 / BUDGET] * k, 1e-9)
    assert dist.mean() <= 1 + 1e-12
    floor = math.factorial(k) / BUDGET ** k
    assert failure_probability(dist.sf, schedule) >= floor * (1 - 1e-7)
    assert worst_case_failure(schedule)[0] >= floor * (1 - 1e-6)

# every distribution obeys sum_i d_i S(t_i) <= E[T], the one inequality behind the adversary's problem
for _ in range(2000):
    size = int(rng.integers(1, 7))
    dist = Discrete(rng.uniform(0, 12, size), rng.dirichlet(np.ones(size)))
    schedule = np.sort(rng.dirichlet(np.ones(3)) * BUDGET)
    gaps = np.diff(schedule, prepend=0.0)
    assert gaps @ [dist.sf(t) for t in schedule] <= dist.mean() + 1e-12

# (2.5, 7.5) against its own worst case, exactly and by simulation, and against the worst case of (5, 5)
dist = atoms_above([2.5, 7.5], [0.1, 0.1], 1e-9)
assert math.isclose(dist.mean(), 1.0)
assert math.isclose(failure_probability(dist.sf, [2.5, 7.5]), 0.02, rel_tol=1e-7)
assert math.isclose(failure_probability(dist.sf, [5.0, 5.0]), 0.01, rel_tol=1e-7)
assert abs(simulate_failure(lambda shape: rng.choice(dist.values, shape, p=dist.probs), [2.5, 7.5]) - 0.02) < 1e-3
assert failure_probability(atoms_above([5.0], [0.2], 1e-9).sf, [2.5, 7.5]) == 0.0

# known distribution: a decreasing hazard rate favours splitting, an increasing one favours a single attempt
for shape, splitting_helps in ((0.5, True), (2.0, False)):
    sf = weibull_min(shape, scale=1 / math.gamma(1 + 1 / shape)).sf                # scaled to mean 1
    assert (failure_probability(sf, [5.0, 5.0]) < failure_probability(sf, [10.0])) == splitting_helps


# ---- Follow-ups
def expected_time_with_cutoff(dist, cutoff):
    return float(np.minimum(dist.values, cutoff) @ dist.probs) / (1.0 - dist.sf(cutoff))


bimodal = Discrete([0.5, 5.5], [0.9, 0.1])                                         # mean 1
assert math.isclose(expected_time_with_cutoff(bimodal, 0.5), 0.5 / 0.9)
assert math.isclose(expected_time_with_cutoff(bimodal, 5.5), 1.0)
total = np.zeros(200_000)
running = np.ones(total.shape, dtype=bool)
while running.any():                                                               # simulate the cutoff 0.5
    draws = rng.choice(bimodal.values, int(running.sum()), p=bimodal.probs)
    total[running] += np.minimum(draws, 0.5)
    running[running] = draws > 0.5
assert abs(total.mean() - 0.5 / 0.9) < 2e-3


def luby(i):
    """i-th term (i >= 1) of Luby's universal sequence."""
    k = i.bit_length()
    return 1 << (k - 1) if i == (1 << k) - 1 else luby(i - (1 << (k - 1)) + 1)


assert [luby(i) for i in range(1, 16)] == [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8]

cantelli = Discrete([0.75, 5.0], [16 / 17, 1 / 17])                                # mean 1, variance 1
variance = float((cantelli.values - 1.0) ** 2 @ cantelli.probs)
assert math.isclose(cantelli.mean(), 1.0) and math.isclose(variance, 1.0)
assert math.isclose(cantelli.probs[cantelli.values >= 5].sum(), 1 / (1 + 4 ** 2))

for overhead, best_equal, best_unequal in ((0.0, 4, 9), (0.5, 3, 5), (1.0, 2, 4)):   # each restart costs `overhead` minutes
    left = {m: BUDGET - (m - 1) * overhead for m in range(1, 11)}
    left = {m: b for m, b in left.items() if b >= m}
    assert min(left, key=lambda m: (m / left[m]) ** m) == best_equal
    assert min(left, key=lambda m: math.factorial(m) / left[m] ** m) == best_unequal
```

</details>

</details>
