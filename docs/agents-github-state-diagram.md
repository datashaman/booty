# Agent–GitHub State Diagram

State diagram of interactions between Booty agents (Builder, Verifier, Observability) and GitHub.

## Overview

```mermaid
sequenceDiagram
    participant GitHub
    participant Sentry
    participant Observability
    participant Planner
    participant Architect
    participant Builder
    participant Verifier

    Sentry->>Observability: alert
    Observability->>GitHub: create issue

    GitHub->>Planner: issues.labeled
    Planner->>Architect: plan
    Architect->>Builder: plan + architecture
    Builder->>GitHub: create PR

    GitHub->>Verifier: pull_request
    Verifier->>GitHub: check run
    Note over Verifier,Builder: on check failure: Verifier reports, Router triggers Builder retry
    Verifier->>GitHub: post_verifier_failure_comment
    Verifier->>Builder: enqueue retry
```

## Main Flow (Issue → PR → Merge)

```mermaid
stateDiagram-v2
    [*] --> IssueCreated: Human/Sentry creates
    IssueCreated --> IssueLabeled: Label agent
    IssueLabeled --> PlannerCheck: Webhook received
    PlannerCheck --> PlannerEnqueued: agent + no plan
    PlannerEnqueued --> PlanStored: Planner worker completes
    PlanStored --> BuilderEnqueued: (worker enqueues, autonomous)
    PlannerCheck --> BuilderEnqueued: agent + plan exists
    PlannerCheck --> BuilderBlocked: agent + no plan + Planner disabled
    BuilderBlocked --> [*]: post_builder_blocked_comment
    BuilderEnqueued --> BuilderProcessing: Job dequeued
    BuilderProcessing --> PRDraft: create_pull_request, add_agent_builder_label
    BuilderProcessing --> FailureCommented: post_failure_comment on issue
    FailureCommented --> [*]

    PRDraft --> VerifierEnqueued: PR webhook (opened/synchronize/reopened)
    VerifierEnqueued --> VerifierProcessing: Job dequeued
    VerifierProcessing --> CheckQueued: create_check_run
    CheckQueued --> CheckInProgress: edit_check_run
    CheckInProgress --> CheckSuccess: tests passed
    CheckInProgress --> CheckFailure: tests/config/setup failed

    CheckSuccess --> PRReadyForReview: promote_to_ready_for_review
    PRReadyForReview --> [*]: Human merges

    CheckFailure --> VerifierCommentPosted: post_verifier_failure_comment on PR
    VerifierCommentPosted --> BuilderRetryEnqueued: enqueue_builder_retry (if under limit)
    BuilderRetryEnqueued --> BuilderProcessing: Job dequeued
    VerifierCommentPosted --> [*]: retry limit reached
```

## Agent Responsibilities

| Agent | Trigger | GitHub API Actions |
|-------|---------|--------------------|
| **Observability** | Sentry webhook (`event_alert`) | `create_issue` with `agent` label |
| **Planner** | `issues` webhook (action=`opened`/`labeled`, label=`agent`) | Produce plan, post comment, store JSON |
| **Architect** | Plan from Planner | Define architecture (future) |
| **Builder** | Plan exists + `agent` | `clone`, `create_pull_request`, `add_to_labels`, `post_failure_comment`; requires valid Plan artifact |
| **Verifier** | `pull_request` webhook (opened/synchronize/reopened) | `create_check_run`, `edit_check_run`, `promote_to_ready_for_review`, `post_verifier_failure_comment`, enqueue Builder retry |

## Verifier Check Run States

```mermaid
stateDiagram-v2
    [*] --> Queued: create_check_run
    Queued --> InProgress: edit_check_run
    InProgress --> CompletedSuccess: tests passed
    InProgress --> CompletedFailure: schema/limits/setup/install/compile/tests failed
    CompletedSuccess --> [*]
    CompletedFailure --> [*]
```

## Failure Paths

- **Builder blocked (no plan)**: `post_builder_blocked_comment` on issue; add `agent` or await Planner
- **Builder pipeline crash**: `post_failure_comment` on issue; PR may exist in draft
- **Verifier failure**: Verifier posts `post_verifier_failure_comment` on PR; **Router** enqueues **Builder** retry (up to `MAX_VERIFIER_RETRIES`). Builder responds by fixing and pushing.
- **Self-modification disabled**: `post_self_modification_disabled_comment` on issue; job ignored
