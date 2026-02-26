---
name: handoff-templates
description: Pre-written message templates for common ANC Proposal Engine development handoffs. Use when the developer needs to report results, request approval, or communicate status to the project lead.
---

# Handoff Templates

Use these when reporting back to the project lead (Ahmad).

## After a Deploy + Test
```
Pushed commit [HASH] to phase2/product-database.
EasyPanel build: [complete/pending]
Local dev tested on: http://localhost:3003

Test results:
- Indiana Audit: [PASS/FAIL] — [tables], [total]
- Indiana LOI: [PASS/FAIL] — [tables], [total]
- Scotia CAD: [PASS/FAIL] — [tables], [currency], [tax]
- Regression: [PASS/FAIL]
- Conditional UI: [PASS/FAIL]

Issues found: [none / describe]
```

## After a Bug Fix
```
Fixed: [describe what was broken]
Root cause: [what caused it]
Files changed: [list]
Regression check: [PASS/FAIL on existing test files]
Pushed: [yes/no] commit [HASH]
```

## When Blocked
```
Blocked on: [what's needed]
What I tried: [list attempts]
What I need from you: [specific ask]
```

## When Proposing a Change
```
Problem: [what's wrong]
Proposed fix: [what I want to do]
Files affected: [list]
Risk to existing features: [none/low/medium/high + why]
Waiting for your approval before proceeding.
```
