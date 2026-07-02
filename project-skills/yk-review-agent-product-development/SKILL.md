---
name: yk-review-agent-product-development
description: Use when working on this repository's product logic, especially intent routing, answerability, capability boundaries, metric expansion, and V0.1-to-V1 evolution for the hospital PGT data review agent. Apply when a request is about “能不能回答”, “怎么路由”, “如何避免答非所问”, product scope, database-supported analytics, or controlled Q&A behavior.
---

# YK Review Agent Product Development

This skill governs product-facing development for the hospital PGT review agent.

## Fast Start

Before reading large history, prefer these short project docs in order:

1. `docs/当前产品边界速记.md`
2. `docs/执行级技术架构方案.md`
3. `docs/PGTA问法标准答案基线-20260702.md`
4. `docs/V0.2路由语料回归说明.md`

Only open longer docs like `人工测试说明` or `PGTA指标计算说明` when the current task truly needs them.

Use it whenever the task touches:

- intent recognition
- answerability judgment
- supported vs unsupported question boundaries
- metric expansion
- database-backed analytics capability
- follow-up behavior in the chat agent
- product decisions that affect whether the agent should answer, clarify, or refuse

Do not use this skill for:

- pure UI polish
- isolated CSS/layout fixes
- infrastructure-only changes
- generic code cleanup that does not affect product behavior

## Core Philosophy

This project is not a keyword router and not a general chatbot.

It is a controlled analytics agent for hospital PGT review.

That means every user question must be evaluated from **two angles at the same time**:

1. `Product positioning`
2. `Database support`

A feature is not ready just because one example works.
A route is not correct just because it can be mapped to some nearby metric.

The agent must avoid two failure modes:

1. `Local optimization`
   The user gives one example, the implementation hardcodes around that example, and the system breaks on the next phrasing.

2. `Answer drift`
   The question is unsupported or underspecified, but the system answers a nearby supported metric anyway.

If there is tension between “looks helpful” and “stays faithful”, choose faithfulness.

## Non-Negotiable Rules

### 1. Never default to a nearby metric

Bad:

- User asks an unrelated question, system returns send volume
- User asks a combined analysis, system answers only half of it
- User asks a question outside scope, system answers the closest supported metric

Good:

- refuse
- ask for clarification
- explain the currently supported scope

### 2. Judge answerability before analysis

The first layer is not “which SQL to run”.
The first layer is:

1. Is this a hospital PGT review question?
2. Is it within the current product scope?
3. Is it supported by the current data source?
4. Is the requested combination of metric + dimension + time grain valid?
5. Does the question need clarification before execution?

Only if all relevant checks pass should the system produce an analysis plan.

### 3. Product scope beats model creativity

Even if the model can infer something plausible, do not answer if the product does not support it.

Examples:

- weather
- general knowledge
- clinical interpretation beyond current data scope
- unsupported product lines
- unsupported derived indicators

### 4. Data support must be explicit

A question is answerable only if the current data source supports it with a defined business meaning.

Do not assume:

- a field exists -> therefore the metric is ready
- a metric exists in a PDF -> therefore the current detail file can compute it
- one exported table supports all future analyses

### 5. Build for classes of questions, not examples

When the user gives an example, extract the class:

- metric type
- breakdown dimension
- time grain
- filter pattern
- answerability rule

Then implement the class, not the literal sentence.

## Canonical Decision Order

For every incoming user question, apply this order:

1. `Domain relevance`
   Is this about hospital PGT data review at all?

2. `Product scope`
   Is it inside current supported product scope?
   For V0.1 and current V0.2 snapshot mode this is mainly executable `PGT-A`.

3. `Capability mapping`
   Can it be mapped to a supported metric family?

4. `Combination validation`
   Is this exact combination supported?
   Example:
   - metric: euploid rate
   - breakdown: by QC
   - time grain: day
   A combination may be invalid even when each piece is individually valid.

5. `Data support validation`
   Does the current data source support the required fields and business semantics?

6. `Clarification check`
   If multiple valid interpretations remain, ask for clarification instead of guessing.

7. `Execution`
   Only now create the analysis plan and run data logic.

## Preferred Output States

Every question should end in exactly one of these states:

1. `answer`
   The question is supported and sufficiently specified.

2. `clarify`
   The question is in-domain but underspecified or ambiguous.

3. `refuse`
   The question is out of domain, out of scope, or unsupported by current data/product capability.

Do not silently downgrade `clarify` or `refuse` into `answer`.

## Implementation Guidance

### Keep these layers separate

Do not collapse everything into prompt logic.

Maintain distinct layers for:

- `Intent parsing`
- `Answerability policy`
- `Metric catalog`
- `Analysis plan`
- `Query execution`
- `Report rendering`

### The metric catalog is a contract

Each metric family should define:

- business name
- supported products
- supported dimensions
- supported time grains
- required data support
- unsupported combinations
- expected response shape

If this is not explicit, the agent will drift.

### Refusal quality matters

A refusal should say **why** the agent cannot answer:

- not a PGT review question
- not in current product scope
- current data source does not support this metric
- this metric/dimension combination is not supported
- the question needs a clearer indicator or time range

Good refusals reduce bad follow-up implementation.

## What To Do When A User Gives One Example

When the user says:

- “this case is wrong”
- “this example should refuse”
- “this should be answerable”

do not patch that sentence only.

Instead:

1. Identify the failure class
2. Define the rule that should generalize
3. Update the answerability layer or metric contract
4. Re-test with at least:
   - the user’s exact example
   - one paraphrase
   - one nearby but unsupported case
   - one unrelated out-of-domain case

## Repository-Specific Ground Rules

At the current stage of this repo:

- treat the current business-reviewed snapshot bundle as the active source of truth for executable analytics before formal APIs arrive
- do not claim support based only on aggregated business tables
- do not expose raw database fields to end users as product language
- frame capability in business terms, not schema terms
- keep hospital filtering, time filtering, and product scope explicit in every analysis path

## Review Checklist Before Shipping Any Logic Change

Ask all of these:

1. Does this change generalize beyond the example that triggered it?
2. Does it reduce answer drift?
3. Does it preserve product scope discipline?
4. Does it explicitly check data support?
5. Does it improve the answer / clarify / refuse split?
6. Would an out-of-domain question still be rejected?
7. Would an unsupported combination still be rejected?

If any answer is “no”, the change is incomplete.

## Anti-Patterns

Avoid these:

- “If nothing matches, return send volume”
- “This example failed, so add one more keyword”
- “The model probably knows what the user meant”
- “The data might have it, so answer first”
- “This looks close enough to a supported question”

These patterns create product drift and destroy trust.

## Success Criterion

A good change makes the agent:

- more principled
- more explicit
- less guessy
- less example-bound
- more faithful to product scope
- more faithful to current database support

If a change only improves one screenshot or one phrase, it is probably too local.
