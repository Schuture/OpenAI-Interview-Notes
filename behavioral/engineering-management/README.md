# Engineering Management Round

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Round |
| --- | --- | --- | --- | --- | --- |
| Behavioral | ★☆☆☆☆ | — | EM | leadership, hiring, mentorship, performance-management, team-composition | Phone screen |
<!-- meta:end -->

## Problem

This is a one-on-one management round for an engineering-manager (EM) role, with an engineering manager as
the interviewer. The questions cover a lot of ground and fall into six groups; nearly every one is to be
answered with a specific example — who was involved, what you actually decided, and what happened
afterward — rather than a general statement of principle.

### Background and team growth

- Give a short account of your background as an engineer and as a manager.
- Is this your first role managing people, or have you managed a team before this one?
- Describe how the size and shape of your team changed over the time you've managed it.

### Management philosophy and day-to-day operations

- How would you describe your management philosophy?
- How do you run your one-on-ones?
- How do you divide your time between writing code and managing, and how does that show up in the way
  you build your calendar?

### Hiring

- Have you hired someone into your team from outside the company?
- What bar and what specific criteria did you apply to that hire?
- Where did that candidate come from — a referral, a recruiter's pipeline, or somewhere else?
- Did the person perform the way the interviews predicted? Where they didn't, what did the process miss?

### Mentorship and growth

- Walk through a specific case of helping a junior engineer, or someone new to the industry, grow.
- What did the road to independent ownership of a clearly-scoped task look like for them, and roughly
  how long did it take?
- What changes in your expectations of them once they move from that point to being able to
  independently define and drive a piece of ambiguous work themselves?

### Performance management

- Have you ever reorganized a team, or had a report leave it, because of a performance issue?
- How do you carry out performance management inside your company's formal process?
- Walk through a specific report whose performance was below the bar: what exactly was wrong, was it a
  skill gap or something else, and what support or coaching did you put in place?

### Team composition

- How do you judge whether the team as a whole, not any one individual, meets the bar you hold it to?
- Have you restructured a team even when every individual on it was performing well? Why?
- How did you pin down which specific skill gap was driving that decision?

## Reference solution

<details>
<summary>Show the reference solution</summary>

Before the round, line up one story with numbers in it for each of five areas — hiring, mentorship, a
performance correction, a reorg, and team-level delivery — and rehearse each as a timeline: the trigger,
the decision you made, and the result. When a question asks for a principle, answer it with one of these
stories too, not with the principle alone.

### Background and team growth

This tests whether you can state what you have managed in concrete numbers, and how much of the team's
change was your doing.

Skeleton: two or three sentences of background — the engineering work you did before managing, when you
started managing people, and whether this is your first management role — then a short timeline of the
team: the headcount and makeup at each point (the senior-to-junior mix, which functions), the specific
event behind each change (a reorg, a new charter, attrition, a hiring push), and where the team stands now
relative to where it started. Say which changes you decided (opening a round of hiring, splitting the
team) and which came from outside (a company-level reorg, someone choosing to leave).

The common failure is giving only today's headcount and skipping the path to it. The fix is to walk
through at least one inflection point on the timeline — what triggered it, how you responded, and the
number that resulted.

### Management philosophy and day-to-day operations

This tests whether your philosophy is a set of practices you actually run, not a value statement that
would fit any manager.

Skeleton, one sub-answer per question:

- **Philosophy.** State it as a rule you apply when priorities conflict, not a slogan — for example, a
  default of giving the team enough context to decide for themselves, with the specific condition under
  which you make the call instead.
- **One-on-ones.** State the cadence and length (for example, weekly or every other week with each direct
  report, thirty minutes, rarely cancelled); the agenda belongs to the report by default, because it is
  their time; use it for what they are stuck on, their growth, and feedback in both directions, not for
  project status — status belongs in standups or written updates. Then name the one thing you track across
  meetings, such as a recurring blocker or an item that keeps getting pushed, which lets you notice a
  problem before it surfaces anywhere else.
- **Coding vs. management.** State the actual split, and how it changes with team size. Put the code you
  still write where it cannot block the team: prototypes or spikes, internal tools, non-urgent bug fixes —
  not a feature the team depends on to hit a deadline, because your calendar can be interrupted at any
  time. Make the calendar match the split: for example, one-on-ones and meetings grouped into fixed slots,
  with coding in whatever uninterrupted blocks remain; when the two collide, coding time is what gives way.

Across the three, have at least one specific moment ready where the practice itself, not the team simply
doing fine on its own, changed an outcome — for instance, the same blocker coming up in two consecutive
one-on-ones, so you dealt with it early.

The common failure is a philosophy with no practice behind it, or one-on-ones described as open time with
nothing you track across them. The fix is to tie each sub-answer to a concrete rule or record, not an
intention.

### Hiring

This tests whether your bar can be applied consistently by other people, what you personally did to find
the candidate, and whether you check your process against how the hire turned out.

Skeleton for the bar: first write down the scope of work the person must own on their own once hired, then
break it into two or three capabilities you can observe in an interview, not adjectives like "strong".
Then say how you kept the bar consistent: a *structured interview*, where each interviewer covers one of
those capabilities with the same questions and a *rubric* written in advance; interviewers submitting
written feedback independently before discussing it, so whoever speaks first does not sway the rest; and a
bar *calibrated* against current team members at the same level, fixed before interviews start and not
lowered because the role has been open a long time. Finally, name the one signal that made you hire this
person, and what would push a borderline candidate to a no.

Skeleton for sourcing: name the actual channel and what you yourself did within it — writing the job
description, reaching out to candidates directly, asking the team for referrals, aligning with the
recruiter on the kind of person you were looking for.

Skeleton for the outcome: compare how the person performed after joining with each assessment from the
interviews. Where the two differ, name which part of the loop failed to test the capability that later fell
short (or exceeded expectations), and what you changed in the loop afterward.

The common failure is a bar stated only in adjectives, with no way to check it, or no account of how the
rubric and the discussion worked. The fix is to replace each adjective with a behavior observable in the
interview, and to say who judged it and against what standard.

### Mentorship and growth

This tests whether you can describe someone's growth as a sequence of specific changes with checkable
milestones, and how your expectations change as their capability does.

Skeleton for the concrete example: name the starting gap (a skill, or a kind of responsibility they had
not yet held), what you changed in their day-to-day — how tasks were chosen for them, the cadence at which
you reviewed their work, which stretch assignment you gave them — and when, and based on what, you saw the
gap close, with a rough timeline. Say which part was your doing and which was the person's own effort.

Skeleton for the expectations question: describe growth as two milestones, each defined by a few
observable things rather than by title names.

- **Delivers a clearly-scoped task independently.** Estimates their own work and delivers against the
  estimate; asks for help when stuck instead of going quiet; code reviews needing major rework become rare.
  At this point you stop tracking task-level progress and review their designs instead.
- **Defines and drives ambiguous work independently.** Given a problem with only a goal, writes the plan,
  decides what "done" means, and breaks it into tasks others could pick up; when another team is needed,
  pulls them in without being prompted. At this point the design is theirs too, and you focus on how they
  framed the problem and which pieces they chose to do.

The common failure is a growth story with no milestone, which can only say "they got better", or
expectations stated as years of experience rather than scope of ownership. The fix is to attach a date and
one marker event to each milestone, and to describe the second as a larger scope of what they own.

### Performance management

This tests whether you diagnose the cause of a performance problem before choosing an intervention, and
whether you can describe someone leaving the team as a process with a plan, a timeline and the person's
dignity intact — not a sudden decision, and not something left to drag on.

| Likely cause | Signal that points to it | Intervention | What you document |
| --- | --- | --- | --- |
| Expectations were never made explicit | The work delivered is reasonable for what they understood, not for what the role actually needs | A specific, written restatement of the bar, with a checkpoint date | The restated expectation and the date you set |
| A skill gap | Consistent misses in one specific area, unrelated to effort | Targeted coaching or pairing on that one area, with a defined re-check | What was coached, by whom, and the re-check date |
| Motivation or personal circumstances | A recent drop from a previously adequate baseline | A direct, private conversation about what changed and what support would help, including a temporary change in workload | That the conversation happened and what was agreed, without detail that belongs to the person |
| Role or team mismatch | Consistently strong on one kind of work, weak on another the role now requires | A change of scope or team, tried before anything more drastic | The mismatch and the change made |

Skeleton for the formal-process question: say what you do outside the formal review cycle so the formal
review holds no surprises — specific feedback given in one-on-ones as things happen, and concrete examples
noted down along the way to support the assessment — and, at review time, aligning your assessments with
other managers against the same standard.

Skeleton for the specific case: name the cause from this table, the specific coaching or support you put
in place, and a timeline: expectations in writing, progress checked against them regularly in one-on-ones,
and a review date agreed in advance. State the specific change you asked for and by when. If nothing had
improved by the review date, state what you actually did next, up to and including the person leaving the
team.

Principles for someone leaving the team: it should not come as a surprise to them — before this point they
already know, clearly and in writing, where the gap is and what the deadline is; the whole thing runs inside
your company's formal process, together with your manager and HR, not with you working around it; and it
stays private — the reasons are not discussed in front of the team, which is told only how the work will be
redistributed. Say which steps were your own decision and which you settled with your manager and HR, and
own the decision itself rather than attributing it to the process. A reorg driven by performance, from the
first question, follows the same line.

The common failure is "coaching" with no content or deadline, indistinguishable from doing nothing, or a
decision to let someone go that comes as a surprise to them. The fix is to name the written expectation,
the check-in cadence and the review date, and what the person already knew before the final step.

### Team composition

This tests whether you can evaluate a team as a whole rather than by adding up individual reviews, and
whether you restructure for structural reasons even when no one is underperforming.

Skeleton for judging the whole team: name two or three signals that don't show up in any single person's
review — whether any piece of work stalls when one person is out for two weeks, whether every area has at
least two people who could take it over, and how much of what the team committed to shipped on time.

Skeleton for restructuring despite strong individuals: first state the structural problem in one sentence,
for example [two roles] overlapping on the same work with no clear owner between them; [one capability]
living entirely in one person, so the team's real capacity is lower than its headcount suggests; or team
boundaries that don't match system boundaries, so every change needs coordination across two teams. Then
state the change you made — redrew ownership boundaries, moved a person, split a team — its cost (lower
output during the handover, the moved person rebuilding context), and that you talked to each affected
person before announcing it to the team. Finally, name a checkpoint you could verify that shows the gap
closed, such as a second person handling an incident in that system on their own, rather than "the team's
output looked fine in the meantime".

Skeleton for identifying the gap: compare what the team's near-term roadmap requires with what the team can
do today without you personally filling the difference, and name the capability that comparison exposes.

The common failure is restating each person's review in place of evaluating the team, or a reorg story
with no structural cause, which sounds like performance management under another name. The fix is to name a
team-level signal no individual review would surface, and to state the structural cause before the change.

### Prep outline

Copy this into `my/` and fill it in with your own stories.

```text
Background (engineering work before managing, when you started managing, which management role this is):

Team timeline (each point: headcount / makeup / triggering event / your decision or from outside):
  1.
  2.
  3.

Management philosophy (the rule + when you make the call yourself instead):
One-on-ones (cadence and length / agenda owner / what for / what not for / the one thing you track):
Coding vs. management (split / what you write / how the calendar reflects it):
One moment your practice changed an outcome:

Hiring story:
  Title:
  Bar (scope to own solo + two or three capabilities):
  Structured interview, rubric and calibration:
  Signal that made you hire:
  Channel (what you did yourself within it):
  Performance after joining vs. the interview assessments:

Mentorship story:
  Title:
  Starting gap:
  What you changed:
  First milestone (date + marker event):
  Second milestone (date + marker event):

Performance management:
  How you keep the formal review free of surprises:
  Performance correction story title:
  Cause (which row of the table):
  Coaching or support:
  Written expectation / check-in cadence / review date:
  Result:

Reorg story:
  Title:
  Structural problem (one sentence):
  What the roadmap needs vs. what the team can do today:
  Change made and its cost:
  Checkpoint:

Team-level delivery story:
  Title:
  Team-level signal:
  Your decision:
  Result:
```

</details>
