# Team Config

> Copy this file to `.claude/team.md` in your repo to customize teamwork routing.
> The team-lead and planner-lead read this file before starting.

## Executor Routing

<!-- Override default routing. Only two executors: codex and copilot. -->
<!--
Examples:
- *.swift, *.m, *.xib → copilot
- *.ts, *.tsx, *.js   → codex
- src/ui/**           → copilot
- src/api/**          → codex
- tests/**            → codex
- *.py, *.sh          → copilot
-->

## Review Mode

<!-- Options: review, adversarial-review -->
default: review

## Verification

<!-- Optional post-execution verification commands (run in repo root). -->
<!--
Examples:
- npm run lint
- npm test
- pnpm -r test
- go test ./...
-->

## Model Config

<!-- Per-agent model override. Concrete model IDs resolved from templates/model-tiers.md. -->
<!-- Resolution: Primary → Secondary → Primary default → Secondary default → omit. -->

### Primary

default: claude-sonnet-4.6
team-lead: claude-opus-4.6
planner-lead: claude-opus-4.6
linter: gpt-5.4
researcher: gpt-5.4
plan-reviewer: gpt-5.4
designer: claude-sonnet-4.6
fullstack-engineer: claude-sonnet-4.6
verifier: gpt-5.4-mini
final-reviewer: gpt-5.4
git-monitor: gpt-5.4-mini
pm: gpt-5.4
security-reviewer: gpt-5.4
devil-advocate: claude-haiku-4.5
a11y-reviewer: gpt-5.4
perf-reviewer: gpt-5.4
user-perspective: claude-sonnet-4.6

### Secondary

default: gpt-5.4
team-lead: gpt-5.4
planner-lead: gpt-5.4
linter: claude-sonnet-4.6
researcher: claude-sonnet-4.6
plan-reviewer: claude-opus-4.6
designer: gpt-5.4
fullstack-engineer: gpt-5.4
verifier: claude-haiku-4.5
final-reviewer: claude-opus-4.6
git-monitor: claude-haiku-4.5
pm: claude-sonnet-4.6
security-reviewer: claude-sonnet-4.6
devil-advocate: gpt-5.4-mini
a11y-reviewer: claude-sonnet-4.6
perf-reviewer: claude-sonnet-4.6
user-perspective: gpt-5.4


## Definition of Done

<!-- Answer these three questions before planning begins. -->
<!-- Leave blank to auto-infer from codebase context. -->

<!-- What does "done" look like? -->
<!-- How will we verify it? -->
<!-- How will we evaluate quality? -->

## Flow Template

<!-- Override default flow template selection. Options: standard, review, build-verify, pre-release -->
<!-- default: standard -->

## Specialty Reviewers

<!-- Uncomment roles to include in review stages. -->
<!-- These are invoked during pre-release flow or adversarial-review mode. -->
<!--
- security-reviewer
- perf-reviewer
- a11y-reviewer
- devil-advocate
- pm
- user-perspective
-->

## Notes

<!-- Context for the planner-lead and team-lead about this repo -->
