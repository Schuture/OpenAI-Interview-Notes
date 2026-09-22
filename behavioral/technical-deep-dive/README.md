# Technical Deep Dive (with slides)

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Presentation and Q&A | ★★★★★ | — | SWE · MLE · RE · Infra Eng | presentation, project-deep-dive | 60 min | Onsite |
<!-- meta:end -->

## Problem

This round is 60 minutes. Before it, you prepare a short slide deck about one technical project you
drove yourself and are ready to defend against detailed pushback: the architecture, the key technical
decisions and their trade-offs, and the measurable impact. You present the deck, and the interviewer
interrupts throughout with follow-up questions that push past the slides into implementation detail.

Expect the follow-ups to fall into five groups.

### Architecture and key decisions

- Walk through the architecture: the main components and how a request or a piece of data moves
  through them.
- For each key decision, what alternatives did you consider, and why did you rule them out?
- Why did you use your actual choice instead of a specific named alternative, for a specific piece of
  the system?
- Which part of the design would you defend most strongly if someone pushed back on it?
- Where did you compromise on what you considered the ideal design because of a real constraint — time,
  team size, or an existing system you had to integrate with?

### Scale and limits

- What happens to the system if traffic or data volume grows 10x? Which component breaks first?
- What was the actual bottleneck once the system was in production, and how did you find it?
- If you had to support 100x instead of 10x, would the same architecture still work, or would it need
  to change shape?
- What is the failure mode when a specific resource — memory, a queue, a rate limit — is exhausted, and
  how does the system behave then?

### Measuring impact

- What metric did you use to show the project worked, and why that metric rather than another one?
- What was the number before and after, and what did you compare it against — a previous baseline, a
  control group, a rollback?
- How much of the result is your individual contribution, and how much is the team's?
- How do you know the change in the metric was caused by your project and not by something else that
  changed at the same time?

### Retrospective

- If you started this project again today, what would you do differently?
- What was the single biggest mistake in the project, and when did you realize it?
- What did you learn that you have since applied to a later project?
- Was there a simpler design that would have captured most of the benefit for a fraction of the effort?

### Where AI could help

- Which part of the system, if any, could be replaced or improved with a machine-learned model?
- If the project itself had nothing to do with AI, where in the pipeline could a model reduce manual or
  heuristic work today?
- Where would the training and evaluation data for that model come from?
- What is the risk of adding a model there, and how would you bound it?

## Reference solution

<details>
<summary>Show the reference solution</summary>

Confirm two things with your recruiter before you prepare: how the 60 minutes splits between your
presentation and questions, and whether you should share your screen or send the deck ahead of time.

### Slide outline

Eight slides is a reasonable target. Much more than that and the deck does not fit the time, and the
interviewer starts interrupting before you reach the results. The throughline is motivation and
constraints, then the solution and its trade-offs, then the result in metrics, then the lessons — in
that order, so each later slide answers a question the earlier ones raised.

- **Slide 1: title and one-line summary** — what the system does, who used it, over what period. Not: your
  background or the team's org chart.
- **Slide 2: motivation and constraints** — the problem before the project existed, and the constraints that
  actually shaped the design (a deadline, team size, a system you had to integrate with, a budget).
  Not: a full requirements document.
- **Slide 3: architecture** — a diagram of the main components and how one request or one piece of data flows
  through them. Not: every internal service, only what the rest of the talk refers back to.
- **Slides 4–5: two key decisions, one slide each** — the alternative you did not take and the constraint that ruled
  it out (one row of the comparison table in the next section). Not: a bullet list of technology names with no reasoning attached.
- **Slide 6: results** — the metric, the before/after numbers, what they were measured against. Not: a number you
  cannot explain how you computed.
- **Slide 7: what you would change** — the biggest mistake, and what breaks first at 10x. Not: a vague "add more
  monitoring".
- **Slide 8: backup** — a fuller architecture diagram, secondary metrics, a third decision you did not have room for
  on slides 4–5. Shown only if asked.

A workable split for the hour is a short presentation, on the order of 15–20 minutes, leaving most of
the round for questions; use the split your recruiter confirms rather than assuming one.

### Architecture and key decisions

This tests whether you actually made the decision, or the "decision" was really the only option you
looked at.

Skeleton for each decision: state the decision, the constraint that drove it, the alternative(s) you
considered, why you ruled them out, and the condition under which you would choose differently today.
Prepare this as a table, one row per alternative, for every decision you expect to be asked about. A
fictional example, for a batch pipeline that merges small files and loads them into a warehouse once an
hour:

| Alternative | Why not, at the time | Under what condition you'd switch |
| --- | --- | --- |
| Stream each record through a queue instead of batching hourly | The upstream system only produced hourly snapshots, so minute-level latency bought nothing and added operational surface | The upstream moved to change-data-capture and a downstream consumer needed minute-level freshness |
| A managed ETL product instead of the team's own scheduler | The team already ran everything else on that scheduler; a second tool costs more in operational overhead than it saves | This pipeline's complexity grew past what the existing scheduler can express |

The most common way to lose points here is naming the choice without the alternatives — "we used X"
instead of "we considered X, Y, Z and ruled out Y and Z because...". Prepare the table before the round,
not during it.

A second common failure: the interviewer proposes an alternative that does not actually apply to your
problem, and you answer as if it does. Before defending against it, restate the constraint or input the
alternative assumes and check it against your actual problem. If that constraint does not hold in your
case, say so and explain what would have to change for the alternative to make sense, rather than
forcing a defense of a comparison that does not fit.

### Scale and limits

This tests whether you can reason about the real bottleneck quantitatively, not recite "add more
servers" or "add caching".

Skeleton: name the resource that is the current bottleneck, say what breaks first at 10x, name the
concrete change (sharding, an added cache, batching, a different data structure), and say where that
change itself hits a new limit.

The common failure is a generic answer — "we'd scale horizontally" — with no resource named and no
order-of-magnitude numbers from the actual system. Memorize two or three real numbers from your project
(current throughput, current data size, the actual bottleneck you hit) before the round, and be ready to
say which of them would move first if the others stayed fixed.

### Measuring impact

This tests whether the metric is well defined, whether you can rule out other explanations, and whether
you can separate what you did from what the team did.

Skeleton: define the metric and how it was computed, name what it was compared against (a prior
baseline, a control group, a rollback), name a plausible confound and why you believe it is not the
explanation, then state your own contribution in one sentence, separate from the team's.

The common failure is a metric you cannot explain the computation of, or an attribution that is either
all "I" or all "we" — interviewers read both as evasive. Prepare one sentence that names exactly which
piece was yours, for example "I designed and built the ranking change; a teammate built the logging
that measured it; the rollout plan was a team decision."

### Retrospective

This tests self-awareness: whether you can name a real cost, not a cosmetic one.

Skeleton: one decision you would reverse, the signal that would have told you earlier, and what you did
differently on a later project because of it.

The common failure is "nothing, it went well" or naming something trivial as the biggest mistake. Pick a
decision that had a real cost — rework, an outage, months of delay — not a stylistic regret.

### Where AI could help

This tests whether you can point at a specific step, not just say "add AI".

Skeleton: name one manual or heuristic step in the pipeline, describe what a model would replace it
with, say where the training and evaluation data would come from, and name the failure mode and how you
would bound it (a fallback, a confidence threshold, human review).

The common failure is naming the idea without the data — "a model could do this triage" without saying
what the inputs, outputs, or labels would be, even at a sketch level — and skipping the failure mode
entirely, as if the model would simply always be right.

### Staying within scope

Part of the system was built by other people, and saying so plainly is safer than guessing. Before the
round, separate what you built from what you only know as an interface: for a component you did not
own, be ready to state its contract — what goes in, what comes out, what it promises — and say directly
that you do not know its internals, rather than answering a detail question about it as if you did.

The common failure is guessing at another component's internals well enough to sound plausible, and
then getting caught by the one follow-up that needs the actual number. A safer sentence to have ready:
"that part belonged to another team; I know it as an interface with this input and this output, and I
don't know how it's implemented inside." Naming the boundary costs you nothing — the interviewer is
checking whether you know where your own work ends, not whether you can speak to the whole system.

### Prep outline

Copy this into `my/` and fill it in with your own project.

```text
Project in one sentence:
Constraints (time / team size / existing systems / budget):

Key decision 1:
  Alternative:
  Why not, at the time:
  Under what condition you'd switch:

Key decision 2:
  Alternative:
  Why not, at the time:
  Under what condition you'd switch:

Key decision 3:
  Alternative:
  Why not, at the time:
  Under what condition you'd switch:

Three numbers (the metric, what it's compared against, your individual share of it):
  1.
  2.
  3.

Two lessons:
  1.
  2.

Where AI could improve this system:

Five follow-up questions you expect:
  1.
  2.
  3.
  4.
  5.
```

</details>
