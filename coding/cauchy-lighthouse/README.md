# Lighthouse Beams and Heavy Tails

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Spoken maths · probability | ★☆☆☆☆ | Hard | RS · RE | probability, heavy-tails, simulation, estimation | 4 parts |
<!-- meta:end -->

## Problem

A lighthouse stands in the sea at perpendicular distance $d > 0$ from a long straight shore. Put a
coordinate on the shore and let $x_0$ be the coordinate of the shore point nearest the lighthouse. The
lamp sends out a narrow beam; its direction is described by the angle $\Theta$ between the beam and the
perpendicular from the lighthouse to the shore, and $\Theta$ is uniform on $(-\pi/2,\; \pi/2)$, so the beam
always reaches the shore. Detectors along the shore record the coordinate $X$ of the point where it lands.
Successive flashes are independent, with the same $d$ and $x_0$ every time.

Example with $d = 2$ and $x_0 = -3$, in kilometres:

```text
theta =  0       beam perpendicular to the shore   x = -3 + 2 *  0.00  =  -3.00
theta =  pi/4    tan(theta) =  1.00                x = -3 + 2 *  1.00  =  -1.00
theta = -1.45    tan(theta) = -8.24                x = -3 + 2 * -8.24  = -19.48
theta =  1.52    tan(theta) = 19.67                x = -3 + 2 * 19.67  =  36.34
```

Each of the four parts asks for a derivation. There is nothing to implement.

### Part 1 — Where one flash lands

Derive the distribution function $F(x) = P(X \le x)$ and the density $f$ of $X$. Write $X$ as $x_0 + dZ$
for a random variable $Z$ whose law depends on neither $x_0$ nor $d$, give the density of $Z$, and name
the family. Where are the median and the quartiles of $X$, and how fast does the tail of $F$ decay?

### Part 2 — Averaging the flashes

Does $E[X]$ exist? Then let $X_1, \dots, X_n$ be the positions of $n$ flashes and find the exact
distribution of the sample mean $\bar X_n = \frac1n \sum_{i=1}^{n} X_i$ for every $n$. What does the answer
say about using $\bar X_n$ to locate the lighthouse, and which step of the usual "averaging shrinks the
error by $\sqrt n$" argument fails?

### Part 3 — Estimators that do converge

For this part $d$ is known, $x_0$ is not, and the $n$ recorded positions are the only data; the angles are
not observed. Call a sequence of estimators $T_n = T_n(X_1, \dots, X_n)$ *consistent* if
$T_n \to x_0$ in probability, and say it has *asymptotic variance* $v$ if
$\sqrt n\;(T_n - x_0)$ converges in distribution to $N(0,\; v)$; among consistent estimators,
smaller $v$ is better. The benchmark is the *Fisher information*
$I = E\bigl[(\partial_\theta \ln f(X; \theta))^{2}\bigr]$ at $\theta = x_0$, where $f(\cdot\;; \theta)$ is
the density of Part 1 with $x_0$ replaced by $\theta$; an estimator with $v = 1/I$ is called *efficient*.

Give two consistent estimators of $x_0$, prove that each one is consistent, compute $I$ and the asymptotic
variance of each estimator, and say which one is efficient and by how much the other misses.

### Part 4 — What a simulation would have to show

Suppose the three conclusions above are now checked numerically, by drawing angles and forming the landing
positions. For each of them — the law of $X$, the law of $\bar X_n$, the rate at which the estimators of
Part 3 converge — name the quantity you would measure and the number your derivation predicts for it. The
mean-squared error $\frac1R \sum_{r=1}^{R} (T^{(r)} - x_0)^{2}$ over $R$ repetitions is a poor
instrument here; say why, and give a measure of error that behaves.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Settle two things with the interviewer first: the beam is uniform in *angle*, not in landing position, and
in Part 3 only $x_0$ is unknown. Say of every number whether it is exact, an asymptotic limit or a
simulation estimate.

### Part 1

Put the shore on the horizontal axis and the lighthouse at height $d$ above the point $x_0$. A beam at
angle $\Theta$ covers $d$ vertically and $d \tan\Theta$ horizontally before it lands, so
$X = x_0 + d \tan\Theta$. On $(-\pi/2,\; \pi/2)$ the tangent is a strictly increasing bijection onto the
whole line, and $P(\Theta \le a) = (a + \pi/2)/\pi$, so

$$F(x) = P\left(\Theta \le \arctan\frac{x - x_0}{d}\right) = \frac{1}{2} + \frac{1}{\pi}\arctan\frac{x - x_0}{d}, \qquad f(x) = F'(x) = \frac{d}{\pi\left(d^{2} + (x - x_0)^{2}\right)} .$$

With $Z = \tan\Theta$ this reads $X = x_0 + dZ$, where $Z$ has density $1/(\pi(1 + z^{2}))$: the
*standard Cauchy* distribution, so $X \sim \mathrm{Cauchy}(x_0,\; d)$. As $F$ is symmetric about $x_0$ with
$F(x_0) = 1/2$, the median is $x_0$; and
$F(x_0 \pm d) = \frac12 \pm \frac{\arctan 1}{\pi} = \frac12 \pm \frac14$, so the lower and upper quartiles
are $x_0 - d$ and $x_0 + d$. The tail, though, is heavy:
$1 - F(x) = \frac{1}{\pi}\arctan\frac{d}{x - x_0} \sim \frac{d}{\pi (x - x_0)}$ as $x \to \infty$, of order
$1/x$ rather than the $e^{-x^{2}/2}$ of a normal law: beams within $\varepsilon$ of grazing the shore
have probability only $2\varepsilon/\pi$, but land beyond $d \cot\varepsilon \approx d/\varepsilon$.

### Part 2

**The expectation does not exist.** With $z = x - x_0$,

$$E\bigl\lvert X - x_0 \bigr\rvert = \frac{d}{\pi}\int_{-\infty}^{\infty} \frac{\lvert z \rvert}{d^{2} + z^{2}}\;dz = \frac{2d}{\pi}\int_{0}^{\infty} \frac{z}{d^{2} + z^{2}}\;dz = \frac{d}{\pi}\Bigl[\ln (d^{2} + z^{2})\Bigr]_{0}^{\infty} = \infty .$$

The positive and the negative part both diverge, so $E[X]$ is undefined rather than $\pm\infty$, and
symmetry does not rescue it: truncating at $x_0 - M$ and $x_0 + cM$ leaves $x_0 + \frac{d}{\pi}\ln c$ in the
limit, so the value depends on how the two tails are trimmed.

**The law of the sample mean.** For standard Cauchy $Z$ the *characteristic function* is
$\varphi_Z(t) = E\bigl[e^{itZ}\bigr] = e^{-\lvert t \rvert}$. Start from the Laplace density
$g(x) = \frac12 e^{-\lvert x \rvert}$, whose transform is elementary:
$\int e^{isx} g(x)\;dx = \frac{1}{2}\bigl(\frac{1}{1 - is} + \frac{1}{1 + is}\bigr) = \frac{1}{1 + s^{2}}$.
That is integrable in $s$, so Fourier inversion gives
$\frac12 e^{-\lvert x \rvert} = \frac{1}{2\pi}\int e^{-isx}(1 + s^{2})^{-1}\;ds$; read at $x = -t$ and
doubled, it is exactly the integral wanted:

$$e^{-\lvert t \rvert} = \int_{-\infty}^{\infty} e^{ist}\;\frac{ds}{\pi (1 + s^{2})} = \varphi_Z(t).$$

Hence $\varphi_X(t) = e^{itx_0}\varphi_Z(dt) = \exp\bigl(itx_0 - d\lvert t \rvert\bigr)$, and for independent
flashes $\varphi_{\bar X_n}(t) = \varphi_X(t/n)^{n} = \exp\bigl(itx_0 - d\lvert t \rvert\bigr) = \varphi_X(t)$.
A characteristic function determines the law, so for every $n$

$$\bar X_n \sim \mathrm{Cauchy}(x_0,\; d), \qquad P\bigl(\lvert \bar X_n - x_0 \rvert > 10 d\bigr) = 1 - \frac{2}{\pi}\arctan 10 \approx 6.3\% .$$

The average of a million flashes has exactly the law of one flash; $\bar X_n$ is not consistent, and an
error bar $\sigma/\sqrt n$ would be meaningless.

The step that fails is the first one: $\mathrm{Var}(\bar X_n) = \sigma^{2}/n$ and the law of large numbers
both need a finite $E\lvert X \rvert$. What happens instead is that
$P(\lvert X - x_0 \rvert > nd) \approx \frac{2}{\pi n}$: whatever $n$ is, about $2/\pi$ flashes are expected
further than $nd$ from $x_0$, and one of those alone moves $\bar X_n$ by order $d$. Cauchy is the symmetric
stable law of index 1, the one index at which averaging neither concentrates nor spreads.

### Part 3

Both estimators below solve $\sum_i \psi\bigl((X_i - \theta)/d\bigr) = 0$ for some $\psi$, and everything
turns on how fast $\psi$ grows. The sample mean is the case $\psi(r) = r$, where a flash at $1000\;d$
carries a thousand times the weight of one at $d$: that is Part 2.

**The sample median** $\hat m_n = X_{(\lceil n/2 \rceil)}$ is the case $\psi(r) = \mathrm{sign}(r)$.

*Consistency.* Fix $\varepsilon > 0$ and put $\delta = \frac{1}{\pi}\arctan\frac{\varepsilon}{d} > 0$, so
that $p = 1 - F(x_0 + \varepsilon) = \frac12 - \delta$. If $\hat m_n \ge x_0 + \varepsilon$ then at least
half the flashes landed at $x_0 + \varepsilon$ or beyond, so Hoeffding's inequality gives
$P(\hat m_n \ge x_0 + \varepsilon) \le P\bigl(\mathrm{Bin}(n,\; p) \ge n/2\bigr) \le e^{-2n\delta^{2}}$, and
symmetrically below. That is summable in $n$, so Borel–Cantelli gives $\hat m_n \to x_0$ almost surely;
only $F$ entered, no moment.

*Asymptotic variance.* Let $B_n$ count the flashes with $X_i \le x_0 + u/\sqrt n$, so that
$B_n \sim \mathrm{Bin}(n,\; q_n)$ and
$q_n = F(x_0 + u/\sqrt n) = \frac12 + \frac{f(x_0) u}{\sqrt n} + o(n^{-1/2})$. Now
$\sqrt n (\hat m_n - x_0) > u$ holds exactly when $B_n < \lceil n/2 \rceil$, and $q_n(1 - q_n) \to \frac14$,
so the central limit theorem for the binomial gives

$$P\bigl(\sqrt n (\hat m_n - x_0) > u\bigr) = P\left(\frac{B_n - n q_n}{\sqrt{n q_n (1 - q_n)}} < -2 f(x_0) u + o(1)\right) \longrightarrow \Phi\bigl(-2 f(x_0) u\bigr),$$

that is $\sqrt n (\hat m_n - x_0) \Rightarrow N\bigl(0,\; 1/(4 f(x_0)^{2})\bigr)$. With $f(x_0) = 1/(\pi d)$,
$v_{\mathrm{med}} = \pi^{2} d^{2}/4$ and $\sqrt{v_{\mathrm{med}}/n} = \pi d/(2\sqrt n) \approx 1.57\;d/\sqrt n$.

**The maximum likelihood estimator** $\hat\theta_n$ maximises

$$\ell(\theta) = -\sum_{i=1}^{n} \ln\left(d^{2} + (X_i - \theta)^{2}\right) + \text{const}, \qquad \ell'(\theta) = \frac{1}{d}\sum_{i=1}^{n} \psi\left(\frac{X_i - \theta}{d}\right), \quad \psi(r) = \frac{2r}{1 + r^{2}} .$$

This $\psi$ is not merely bounded but *redescending*: $\psi(r) \to 0$ as $\lvert r \rvert \to \infty$, so a
flash 100 km out pulls less than one 2 km out — not an ad-hoc robustification, but what the Cauchy tail
makes optimal.

*Consistency.* The log-likelihood ratio $\ln\frac{d^{2} + (X - \theta)^{2}}{d^{2} + (X - x_0)^{2}}$ is a
bounded function of $X$ for fixed $\theta$, and $1/d$-Lipschitz in $\theta$ for any sample, so the law of
large numbers needs no moment and its convergence is uniform on compact sets:

$$\frac{1}{n}\bigl[\ell(\theta) - \ell(x_0)\bigr] \longrightarrow -K(\theta) = -\ln\left(1 + \frac{(\theta - x_0)^{2}}{4 d^{2}}\right) \quad \text{almost surely},$$

where $K$ is the Kullback–Leibler divergence between the two laws, positive except at $\theta = x_0$. Far
out no uniformity is needed: if $\theta > \hat m_n$ then half the flashes are at distance
$\theta - \hat m_n$ or more from $\theta$, so
$\frac1n \ell(\theta) \le -\frac12 \ln\bigl(d^{2} + (\theta - \hat m_n)^{2}\bigr) - \ln d$, while
$\frac1n \ell(x_0) \to -\ln (4d^{2})$ since $E \ln(1 + Z^{2}) = 2 \ln 2$ is finite, so every $\theta$ beyond
$x_0 \pm 8d$ is eventually beaten by $x_0$. Hence $\hat\theta_n \to x_0$ almost surely.

*Asymptotic variance.* Expand the score at $x_0$:
$0 = \ell'(\hat\theta_n) = \ell'(x_0) + \ell''(x_0)(\hat\theta_n - x_0) + \dots$. The summands of
$\ell'(x_0)$ are bounded, so the ordinary central limit theorem applies although $X$ has no moments at all;
they are centred by symmetry, and their variance is the Fisher information

$$I = \mathrm{Var}\left(\frac{\psi(Z)}{d}\right) = \frac{4}{\pi d^{2}}\int_{-\infty}^{\infty} \frac{z^{2}}{(1 + z^{2})^{3}}\;dz = \frac{4}{\pi d^{2}} \cdot \frac{\pi}{8} = \frac{1}{2 d^{2}} ,$$

while $-\frac1n \ell''(x_0) \to I$ as well. So $\sqrt n (\hat\theta_n - x_0) \Rightarrow N(0,\; 1/I)$ with
$v_{\mathrm{mle}} = 2 d^{2}$ and $\sqrt{v_{\mathrm{mle}}/n} = \sqrt 2\;d/\sqrt n$: the estimator
attains $1/I$ and is efficient. The median's efficiency is
$v_{\mathrm{mle}} / v_{\mathrm{med}} = 8/\pi^{2} \approx 0.81$: 23% more flashes for the same precision.

*Computing it.* Cleared of denominators, $\ell'(\theta) = 0$ is a polynomial equation of degree $2n - 1$
whose roots need not be unique: at $n = 25$, about a quarter of the samples give $\ell$ two or more
local maxima, so the estimator is the global maximiser and not "the" root; Newton's method started at
$\hat m_n$ is the usual recipe.

### Part 4

**The law of $X$.** Draw angles, form $X_i = x_0 + d \tan\Theta_i$, and measure the Kolmogorov–Smirnov
distance $D_n = \sup_x \lvert F_n(x) - F(x) \rvert$ between the empirical distribution function and the
derived $F$. The prediction does not depend on $F$: if $F$ is right, $\sqrt n D_n$ converges to the
Kolmogorov law, whose mean is $\sqrt{\pi/2}\;\ln 2 \approx 0.869$ and whose 95th percentile is $1.358$. Get
the scale wrong by 30% and $D_n$ instead settles at a positive constant, so $\sqrt n D_n$ grows like
$\sqrt n$.

**The law of $\bar X_n$.** Mean-squared error is the wrong instrument: $E[(X - x_0)^{2}] = \infty$, so
$\frac1R \sum_r (\bar X_n^{(r)} - x_0)^{2}$ has no limit in $R$ — it is set by the largest of the $R$
repetitions and drifts up as more arrive. Use the *median absolute error*
$\mathrm{med}_r \lvert \bar X_n^{(r)} - x_0 \rvert$, which needs only a quantile; since
$P(\lvert X - x_0 \rvert \le d) = \frac{2}{\pi}\arctan 1 = \frac12$, it is exactly $d$, for every $n$.

**The rate of Part 3.** The same measure, at several $n$. From
$\sqrt n (T_n - x_0) \Rightarrow N(0,\; v)$ and $\Phi^{-1}(3/4) \approx 0.6745$ it is about
$0.6745 \sqrt{v/n}$, that is $1.06\;d/\sqrt n$ for the median and $0.954\;d/\sqrt n$ for the maximum
likelihood estimator, against a flat $d$ for the sample mean. Multiplying $n$ by 16 must divide the first
two by 4 and leave the third alone: that one comparison separates all three conclusions.

### Follow-ups

- If $d$ is unknown as well, $Q_1 = x_0 - d$ and $Q_3 = x_0 + d$ give $\hat x_0 = (\hat Q_1 + \hat Q_3)/2$ and
  $\hat d = (\hat Q_3 - \hat Q_1)/2$ for one sort; the two-parameter information matrix is
  $\frac{1}{2 d^{2}}$ times the identity, so the two parameters do not interfere asymptotically.
- With $\hat\varphi_n(t) = \frac1n \sum_j e^{itX_j}$ and $\varphi_X(t) = \exp(itx_0 - d\lvert t \rvert)$,
  $-\ln\lvert \hat\varphi_n(t) \rvert / \lvert t \rvert$ is consistent for $d$ at every fixed $t \neq 0$;
  the argument is read in $(-\pi,\; \pi]$, so $\arg \hat\varphi_n(t) / t$ needs
  $\lvert t x_0 \rvert < \pi$ to be consistent for $x_0$. One pass over the data, no sort.
- The ratio $N_1/N_2$ of two independent standard normals is standard Cauchy: whenever a statistic is a
  ratio, a denominator that can come close to zero gives the same $1/x$ tail, and averaging runs will not
  tame it.

<details>
<summary>Checks (runnable)</summary>

```python
import math

import numpy as np
from scipy import integrate, stats

X0, D = -3.0, 2.0                    # the example: x0 = -3 km along the shore, d = 2 km out to sea
rng = np.random.default_rng(2026)


def cdf(x, loc=X0, scale=D):
    return 0.5 + np.arctan((np.asarray(x, dtype=float) - loc) / scale) / math.pi


def pdf(x, loc=X0, scale=D):
    return scale / (math.pi * (scale ** 2 + (np.asarray(x, dtype=float) - loc) ** 2))


def flashes(shape):
    """The physical model only: uniform angles through tan, with no Cauchy sampler involved."""
    return X0 + D * np.tan(rng.uniform(-math.pi / 2, math.pi / 2, shape))


# ---- Part 1: the derived F and f, against quadrature, against the library, and against the simulation
probe = np.array([-60.0, -9.0, X0 - D, X0, X0 + D, 4.0, 31.0])
assert np.allclose([integrate.quad(pdf, -np.inf, x)[0] for x in probe], cdf(probe), atol=1e-10)
assert np.allclose(cdf(probe), stats.cauchy(loc=X0, scale=D).cdf(probe))
assert np.allclose(pdf(probe), stats.cauchy(loc=X0, scale=D).pdf(probe))
assert cdf(X0) == 0.5 and math.isclose(cdf(X0 - D), 0.25) and math.isclose(cdf(X0 + D), 0.75)

n, reps = 2_000, 400
scaled_ks = np.array([math.sqrt(n) * stats.kstest(flashes(n), cdf).statistic for _ in range(reps)])
assert abs(scaled_ks.mean() - math.sqrt(math.pi / 2) * math.log(2)) < 0.05     # the Kolmogorov limit law
assert abs(np.mean(scaled_ks > stats.kstwobign.ppf(0.95)) - 0.05) < 0.03
big = 50_000                                                                   # NOTE: negative control
wrong = math.sqrt(big) * stats.kstest(flashes(big), lambda x: cdf(x, scale=1.3 * D)).statistic
assert math.isclose(wrong / math.sqrt(big), 2 * math.atan(math.sqrt(1.3)) / math.pi - 0.5, rel_tol=0.2)
assert wrong > 3 * scaled_ks.max()

# ---- Part 2: no expectation, the characteristic function, and the law of the sample mean
for cut in (1e3, 1e6, 1e9):                    # E|X - x0| diverges logarithmically
    tail = integrate.quad(lambda z: z * pdf(z, loc=0.0), 0.0, cut, points=[D])[0]
    assert math.isclose(tail, (D / (2 * math.pi)) * math.log1p(cut ** 2 / D ** 2), rel_tol=1e-9)
    assert abs(tail - (D / math.pi) * math.log(cut / D)) < 1e-5
for c in (1.0, 2.0, 9.0):                      # cutting at x0 - M and x0 + c M leaves x0 + (d / pi) ln c
    off = integrate.quad(lambda z: z * pdf(z, loc=0.0), -1e5, c * 1e5, points=[-D, D])[0]
    assert math.isclose(off, (D / math.pi) * math.log(c), abs_tol=1e-6)

for t in (0.35, 1.0, 4.0):                     # phi(t) = exp(i x0 t - d |t|), by oscillatory quadrature
    even = integrate.quad(lambda z: 2 * pdf(z, loc=0.0), 0, np.inf, weight="cos", wvar=t)[0]
    assert math.isclose(even, math.exp(-D * t), rel_tol=1e-6)
for y in (-14.0, 2 * X0, 5.0):                 # X1 + X2 is Cauchy(2 x0, 2 d), by convolution
    conv = integrate.quad(lambda u: pdf(u) * pdf(y - u), -np.inf, np.inf, limit=300)[0]
    assert math.isclose(conv, float(pdf(y, loc=2 * X0, scale=2 * D)), rel_tol=1e-8)
for size in (2, 32, 512):                      # so the sample mean has exactly the law of one flash
    assert stats.kstest(flashes((20_000, size)).mean(axis=1), cdf).pvalue > 1e-3
assert math.isclose(1 - 2 * math.atan(10.0) / math.pi, 0.0635, abs_tol=5e-5)   # P(|mean - x0| > 10 d)

# ---- Part 3: Fisher information, Kullback-Leibler divergence, and the two estimators
def derivative(x):                   # f'(x)
    return -2 * D * (x - X0) / (math.pi * (D ** 2 + (x - X0) ** 2) ** 2)


assert math.isclose(integrate.quad(lambda x: derivative(x) ** 2 / pdf(x), -np.inf, np.inf)[0],
                    1 / (2 * D ** 2), rel_tol=1e-6)
assert math.isclose(integrate.quad(lambda z: math.log1p(z * z) * pdf(z, loc=0.0, scale=1.0),
                                   -np.inf, np.inf)[0], 2 * math.log(2), rel_tol=1e-9)
for delta in (0.4, 3.0, 11.0):
    kl = integrate.quad(lambda x: pdf(x) * math.log(pdf(x) / pdf(x, loc=X0 + delta)), -np.inf, np.inf, limit=300)[0]
    assert math.isclose(kl, math.log1p(delta ** 2 / (4 * D ** 2)), rel_tol=1e-7)


def neg_log_likelihood(sample, theta):
    """-l(theta) up to a constant, straight from the density; one row of theta values per row of sample."""
    return np.log(D ** 2 + (sample[:, :, None] - theta[:, None, :]) ** 2).sum(axis=1)


def newton_mle(sample, theta, steps=12):
    """Newton on the score, started at theta (the sample median); one estimate per row."""
    for _ in range(steps):
        r = (sample - theta[:, None]) / D
        u = 1.0 + r * r
        score = (2 * r / u).sum(axis=1) / D                                   # l'(theta)
        curvature = (2 * (1 - r * r) / (u * u)).sum(axis=1) / D ** 2          # -l''(theta)
        step = np.where(curvature > 0, score / np.maximum(curvature, 1e-12), np.sign(score) * D)
        theta = theta + np.clip(step, -4 * D, 4 * D)       # NOTE: -l'' turns negative far from the root
    return theta


def brute_mle(sample, rounds=4, points=400):
    """The global maximiser by nested grid search on -l itself: no score, no Hessian, no Newton."""
    lo, hi = sample.min(axis=1), sample.max(axis=1)        # l' > 0 below the smallest flash, < 0 above the largest
    for _ in range(rounds):
        grid = lo[:, None] + (hi - lo)[:, None] * np.linspace(0.0, 1.0, points)
        best = grid[np.arange(len(sample)), neg_log_likelihood(sample, grid).argmin(axis=1)]
        width = (hi - lo) / (points - 1)
        lo, hi = best - width, best + width
    return (lo + hi) / 2


one_run, h = flashes(40)[None, :], 1e-3                    # score and curvature against finite differences
for theta in X0 + np.array([-1.7, -0.3, 0.0, 0.6, 2.2]):
    r = (one_run[0] - theta) / D
    left, here, right = neg_log_likelihood(one_run, np.array([[theta - h, theta, theta + h]]))[0]
    assert np.isclose((2 * r / (1 + r * r)).sum() / D, -(right - left) / (2 * h), rtol=1e-5, atol=1e-4)
    assert np.isclose((2 * (1 - r * r) / (1 + r * r) ** 2).sum() / D ** 2,
                      (right - 2 * here + left) / h ** 2, rtol=1e-4, atol=1e-3)

small = flashes((400, 25))                                 # Newton from the median against the grid search
middle = np.median(small, axis=1)
newton, brute = newton_mle(small, middle.copy()), brute_mle(small)
column = lambda v: neg_log_likelihood(small, v[:, None])[:, 0]
assert np.all(column(brute) <= column(newton) + 1e-6)
assert np.mean(np.abs(newton - brute) < 1e-3) > 0.97       # Newton lands on the global maximum
assert np.allclose(newton, newton_mle(small, middle.copy(), steps=30))          # 12 steps are enough

few = small[:200]                                                              # several roots of l' = 0
grid = np.linspace(few.min(axis=1), few.max(axis=1), 3000).T
r = (few[:, :, None] - grid[:, None, :]) / D
signs = np.sign((2 * r / (1 + r * r)).sum(axis=1))
maxima = ((signs[:, :-1] > 0) & (signs[:, 1:] < 0)).sum(axis=1)
assert 0.15 < np.mean(maxima > 1) < 0.42 and maxima.max() >= 3

# ---- Parts 3 and 4: how the error of the three estimators moves with n
COEF = stats.norm.ppf(0.75)                                # median of |N(0, v)| is 0.6745 sqrt(v)
table = {}
for size, reps in ((15, 20_000), (255, 8_000), (4095, 4_000)):
    draws = flashes((reps, size))
    centre = np.median(draws, axis=1)
    guesses = {"mean": draws.mean(axis=1), "median": centre, "mle": newton_mle(draws, centre.copy())}
    table[size] = {name: float(np.median(np.abs(g - X0))) for name, g in guesses.items()}

for size in table:                                         # the sample mean: median absolute error d, at every n
    assert math.isclose(table[size]["mean"], D, rel_tol=0.1)
    assert math.isclose(table[size]["median"], COEF * math.pi * D / 2 / math.sqrt(size), rel_tol=0.08)
    assert math.isclose(table[size]["mle"], COEF * math.sqrt(2) * D / math.sqrt(size), rel_tol=0.08)
    assert table[size]["mle"] < table[size]["median"] < table[size]["mean"]
assert 0.9 < table[4095]["mean"] / table[15]["mean"] < 1.1                      # flat in n
for name in ("median", "mle"):                                                 # and falling like 1 / sqrt(n)
    assert math.isclose(table[4095][name] / table[15][name], math.sqrt(15 / 4095), rel_tol=0.1)
assert math.isclose(table[4095]["mle"] / table[4095]["median"], 2 * math.sqrt(2) / math.pi, rel_tol=0.07)

# ---- Follow-ups
quartiles = np.percentile(flashes((2_000, 4095)), [25, 75], axis=1)
assert abs(np.median(quartiles.mean(axis=0)) - X0) < 0.05
assert abs(np.median((quartiles[1] - quartiles[0]) / 2) - D) < 0.05
phi = np.exp(0.5j * flashes((2_000, 4095))).mean(axis=1)   # empirical characteristic function at t = 1/2
assert abs(np.median(2 * np.angle(phi)) - X0) < 0.05 and abs(np.median(-2 * np.log(np.abs(phi))) - D) < 0.05
ratio = rng.standard_normal(200_000) / rng.standard_normal(200_000)            # N(0,1) / N(0,1) is standard Cauchy
assert stats.kstest(ratio, lambda x: cdf(x, loc=0.0, scale=1.0)).pvalue > 1e-3

step = 1e-5                                                # the two-parameter information matrix is diag(1, 1) / (2 d^2)
gradient = [lambda x: (np.log(pdf(x, loc=X0 + step)) - np.log(pdf(x, loc=X0 - step))) / (2 * step),
            lambda x: (np.log(pdf(x, scale=D + step)) - np.log(pdf(x, scale=D - step))) / (2 * step)]
for a, first in enumerate(gradient):
    for b, second in enumerate(gradient):
        entry = integrate.quad(lambda x: first(x) * second(x) * pdf(x), -np.inf, np.inf, limit=400)[0]
        assert abs(entry - (1 / (2 * D ** 2) if a == b else 0.0)) < 1e-8
```

</details>

</details>
