# Events Sequence Diagram

Sequence diagram of events flowing through the agent pipeline, including observability.

## Diagram

Paste this into [sequencediagram.org](https://sequencediagram.org/) to render:

```
title Events

participant Human
participant GitHub
participant Router
participant Planner
participant Architect
participant Builder
participant Verifier
participant Observability

Human->GitHub:create issue
GitHub->Router:issues.created event
Router-->Observability:span received
Human->GitHub:label issue
GitHub->Router:issues.labeled event
Router-->Observability:span received
Router->Planner:trigger plan
Planner-->Observability:span plan.created
Planner->Architect:plan
Architect-->Observability:span architecture.defined
Architect->Builder:plan + architecture
Builder-->Observability:span builder.started
Builder-->GitHub:create branch
GitHub->Router:create event
Builder-->Observability:span branch.created
Builder-->GitHub:create draft PR
GitHub->Router:pull_requests.created
Router-->Observability:span received
Router->Verifier:trigger check
Verifier-->Observability:span check.started
Verifier-->GitHub:check result
Verifier-->Observability:span check.completed
alt check success
    Verifier-->GitHub:promote PR on check success
    Verifier-->Observability:span pr.promoted
else check failure
    Verifier-->GitHub:post_verifier_failure_comment
    GitHub->Router:check_run.completed event
    Router-->Observability:span received
    Router->Builder:trigger retry
    Builder-->Observability:span builder.retry
    Builder->Builder:fix and push
end
```

## Notes

- **Planner** is implemented — issues with `agent` trigger planner worker; plans are stored and posted as comments. **Architect** is not yet implemented.
- **Observability** receives telemetry spans at each stage (traces, metrics, or logs).
- Dashed arrows (`-->`) indicate async, non-blocking emission.
- GitHub event names follow webhook conventions: `issues` (action: opened/labeled), `create` (ref_type: branch), `pull_request` (action: opened), `check_run` (action: completed).

## Suggested flow changes (reduce coupling)

Based on coupling analysis, these changes would loosen tight dependencies:

1. **Planner–Architect–Builder chain** — Route via Router (or internal event bus) instead of direct calls:
   - `Router->Planner`, `Planner->Router:plan.created`, `Router->Architect:plan`, `Architect->Router:architecture.defined`, `Router->Builder:plan+architecture`
   - Agents emit to Router; Router routes. No agent knows the next in the chain.

2. **Subscription-based routing** — Agents register for event types instead of Router hard-coding routes. Router forwards events to subscribers; adding agents does not require Router changes.

3. **Normalize check-failure semantics** — A dedicated component (or Verifier) emits `agent_pr_check_failed` when retry is appropriate. Router routes on that event only; it does not need to interpret `check_run` conclusion or agent-PR logic.

4. **Success-path event** — Have Verifier (or GitHub) emit an event when PR is promoted, so other agents can subscribe (e.g. notifications, metrics) without special handling.
