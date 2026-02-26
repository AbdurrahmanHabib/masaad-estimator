# Masaad Estimator — Architecture Review

**Date:** 2026-02-26
**Reviewer:** Supervisor / Architect
**Scope:** LangGraph 12-node pipeline, HITL, checkpointing, international routing, Delta Engine, Commercial Director

---

## TASK 1 — LangGraph Pipeline Review

### 1.1 Node Transition Graph — Correctness

```
IngestionNode
  → ScopeIdentificationNode
  → GeometryQANode
  → BOMNode
  → [HITLTriageNode | DeltaCompareNode]   ← conditional
  → DeltaCompareNode (after HITL merges here)
  → PricingNode
  → CommercialNode
  → ComplianceNode
  → [InternationalRoutingNode | ApprovalGatewayNode]  ← conditional
  → ApprovalGatewayNode
  → [ReportNode | END]  ← conditional
  → END
```

**Verdict: Mostly correct. One real dead-end risk.**

**ISSUE — Missing post-compliance HITL branch is dangerously incomplete:**
`should_triage_post_compliance()` is defined in the code but **never wired into the graph**. It computes a result and returns `"next"` or `"HITLTriageNode"`, but no `add_conditional_edges()` call references this function. It is dead code. After `ComplianceNode`, the graph always routes to `should_route_international`. A compliance failure with low confidence never triggers a second HITL review despite the function existing.

**ISSUE — HITLTriageNode does not truly suspend the graph:**
After HITL creates DB records and sets `status = "REVIEW_REQUIRED"`, it immediately returns and the graph continues to `DeltaCompareNode`. The graph does not halt here. Only `ApprovalGatewayNode` actually halts (by returning `END` via `is_approved`). This means the estimate pipeline runs to near-completion even when HITL flags are pending. A human reviewer's approval has no mechanism to re-enter the graph mid-flow — it can only trigger the `ApprovalGateway → ReportNode` leg. **HITL is advisory, not blocking.**

**ISSUE — ComplianceNode progress percentage (78%) is too close to CommercialNode (75%):**
Both nodes show narrow progress bands. Not a functional bug, but causes misleading frontend progress bars where the pipeline appears stalled between 75–80%.

**No actual dead ends (unreachable nodes):** All 12 nodes are reachable. All terminal paths lead to `END`.

---

### 1.2 HITL Triage — Suspend/Resume Analysis

**The implementation does NOT properly suspend/resume the graph.** Here is what actually happens:

1. `HITLTriageNode` writes triage items to DB and sets `state["status"] = "REVIEW_REQUIRED"`.
2. The graph continues immediately to `DeltaCompareNode` without waiting.
3. The only actual halt is at `ApprovalGatewayNode`, which calls `is_approved()` and returns `END` if not yet approved.
4. When a human POSTs to `/api/v1/estimates/{id}/approve`, the pipeline must be **re-run from scratch** or resumed — there is no `graph.continue_from()` call in the approval route.

**What true LangGraph HITL suspension requires:** Using `interrupt_before` or `interrupt_after` on a node, combined with a `MemorySaver` or `AsyncPostgresSaver` checkpointer, then calling `graph.ainvoke(None, config)` to resume. The current implementation uses Redis for checkpointing but does not use LangGraph's native interruption mechanism. This is a **architectural gap** — the graph is treated as a one-shot run, not a resumable workflow.

**Recommendation:** Add `interrupt_before=["ApprovalGatewayNode"]` to `graph.compile()` and wire the approval endpoint to call `graph.ainvoke(Command(resume=True), config={"configurable": {"thread_id": estimate_id}})`.

---

### 1.3 Checkpointing — Completeness

**Current approach:** Custom Redis checkpointing via `_checkpoint()` called in `make_node()`.

**Issues found:**

1. `_checkpoint()` is defined but **never called inside `make_node()`**. The `node()` inner function calls `impl(state)` but never calls `await _checkpoint(state, redis_client)`. The `redis_client` is never passed to `make_node()` either — its signature is `make_node(name, progress, impl)` with no `redis_client` parameter. **Checkpointing is completely non-functional as implemented.** The checkpoint key is written only from `_persist_estimate()` to the DB, not Redis.

2. `load_checkpoint()` sorts Redis keys alphabetically (`sorted(keys)[-1]`), not by timestamp. Key format is `ckpt:{estimate_id}:{node_name}`, and node names sort lexicographically, not by pipeline order. "ScopeIdentificationNode" sorts after "ReportNode" alphabetically. The "latest" checkpoint would be wrong.

3. No checkpoint is written after the graph's `make_node` wrapper — only the `_persist_estimate()` DB writes work correctly.

**Recommendation:** Either pass `redis_client` to `make_node()` and call `_checkpoint()` after `impl()`, or switch to LangGraph's native `AsyncRedisSaver` checkpointer passed to `graph.compile(checkpointer=...)`.

---

### 1.4 InternationalRoutingNode — Al Kabir Tower Activation

**Correctly gated:** `should_route_international()` checks `state.get("is_international")` and routes to `InternationalRoutingNode`. This is correct.

**Implementation is correct but has one double-counting risk:**
In `_international_routing_impl`, the BG fee is computed as `round(pricing["total_aed"] * 0.025, 2)` **after** the forex buffer has already been added to `total_aed`. This means the BG fee is computed on `(original_total + forex_buffer)`, which is correct. However, the manpower budget is then added to `total_aed` again and the BG line item is added to `bom_items` — but the BG fee is NOT reflected back into `pricing["total_aed"]` before the next `+= manpower_budget` line. Actually reading the code: forex_buffer → total_aed updated → BG fee computed on new total → BG added to total → manpower added to total. The arithmetic chain is correct; no double-counting.

**Missing:** No currency conversion logic despite `project_currency` field in state. If `project_currency == "USD"`, prices are still returned in AED. The currency conversion is noted as a future concern but would silently produce wrong figures if the field is set.

**Missing:** Container cost calculation (20ft/40ft containers) is referenced in `INTERNATIONAL_CONFIG` of the planned `config.py` but is not applied anywhere in `_international_routing_impl`.

---

### 1.5 Error Boundaries

**Partial coverage.** `make_node()` wraps `impl()` in a try/except that catches all exceptions, sets `state["error"]` and `state["error_node"]`, and continues. This is the correct pattern.

**Issues:**

1. When a node fails, the graph **continues to the next node** regardless of whether the error is recoverable. A failed `BOMNode` (zero BOM items) will allow `PricingNode` to proceed, producing a `total_aed = 0` quote that looks valid. There is no error severity classification.

2. `state["error"]` is a single string — the last error wins. Multiple node errors overwrite each other silently.

3. `_ingestion_impl` has its own inner try/except *inside* the outer `make_node` try/except. This is redundant and can suppress errors that should propagate upward. The inner exception sets `extracted_openings = []` and reduces `confidence_score`, then the outer try/except sees no exception — so `state["error"]` is never set for ingestion failures. The graph appears healthy when it should flag HITL.

4. `_compliance_impl` has a duplicated try/except structure with the same issue: inner exception sets a partial `compliance_report` dict and returns, outer wrapper sees no exception.

---

### 1.6 Delta Engine — Rev 0 Handling

**Correct and safe.** `_delta_compare_impl` checks:

```python
if revision == 0:
    return state  # skip
if not prev_snap:
    return state  # skip
```

Both guards are present. Rev 0 with no snapshot is a clean pass-through. This is correct.

**One edge case:** If `revision_number > 0` but the caller forgot to populate `prev_bom_snapshot`, the second guard catches it gracefully. No crash. Good.

**Minor concern:** `variation_order_delta` uses `abs(new_qty - old_qty) < 0.001` for float comparison to skip zero-change items. This is appropriate for quantities in meters/kg. However, if quantities are integer piece counts, a 0.001 tolerance is unnecessarily tight. No bug, just a note.

---

### 1.7 Summary of Critical Findings

| # | Finding | Severity | Node |
|---|---------|----------|------|
| 1 | Checkpointing not functional — `_checkpoint()` never called | CRITICAL | All nodes |
| 2 | HITL does not suspend graph — pipeline continues immediately | CRITICAL | HITLTriageNode |
| 3 | `should_triage_post_compliance()` defined but never wired | HIGH | ComplianceNode |
| 4 | `checkpoint_load_checkpoint()` sorts keys wrong (alpha not time) | HIGH | Resume logic |
| 5 | Multi-node errors overwrite each other in `state["error"]` | MEDIUM | All nodes |
| 6 | Missing currency conversion for international projects | MEDIUM | IntlRoutingNode |
| 7 | Inner try/except in ingestion/compliance silences errors | MEDIUM | Ingestion, Compliance |
| 8 | No container cost in international routing | LOW | IntlRoutingNode |
| 9 | Progress band 75–78% too narrow (CommercialNode → ComplianceNode) | LOW | UI only |

---

## TASK 4 — Commercial Director Review

### 4.1 C5 S-Curve — Retention Handling

**Implementation is correct.** The standard 30/60/10 split is implemented:

- Week 0: 30% advance
- Weeks 1–42 (80% of 52): 60% progress payments via sigmoid weighting
- Week 52: 10% retention released

**Retention is properly separated from cashflow:**
- `retention_aed` is computed as `base * retention_pct`
- Retention appears as a separate line: `payment_type = "RETENTION"` at week 52
- The `note` field explicitly states: *"Never include in operating cashflow"*
- In `_commercial_impl`, `pricing["cashflow_net_aed"] = round(total - retention_aed, 2)` correctly excludes retention from the operating cashflow figure

**One concern:** The S-curve uses `duration_weeks = 52` as default, meaning retention is released at week 52. However, `generate_milestone_schedule()` shows retention released at week 104 (2 years). These two functions use inconsistent retention release timelines. The milestone schedule is correct (104 weeks = 2 years for a 1-year DLP starting after 1-year construction). The S-curve conflates the two. A 52-week project with retention at week 52 means retention releases at practical completion, not 12 months post-handover.

**Recommendation:** Pass `retention_release_week = duration_weeks + 52` to `generate_scurve_cashflow()` to separate construction duration from DLP.

**VAT:** Applied correctly at 5% on all payment types including retention. Correct per UAE VAT law.

---

### 4.2 International Routing — C4/C8 Integration

**EXW terms:** Correctly applied. `pricing["delivery_terms"]` is set to explicit EXW text. The BG fee and manpower line items are added to `bom_items`.

**Forex buffer:** Applied at 3% on `material_cost_aed`. Correct. However, `material_cost_aed` must exist in the pricing dict before this point — it is set in `_pricing_impl`. If `PricingNode` failed and `material_cost_aed` is 0, the forex buffer would silently be AED 0. The guard `pricing.get("material_cost_aed", 0)` is safe but could mislead.

**C4 Supplier Leveling:** `level_supplier_quotes()` is implemented correctly but **never called in the pipeline**. There is no `_commercial_impl` call to it, and no API endpoint calls it proactively from the graph. It is only available via the commercial routes API if manually triggered. For international projects (Al Kabir Tower), supplier quote leveling should be mandatory and called from within `_international_routing_impl`.

---

### 4.3 C11 VE Menu — Facade-Specific Alternatives

**Implemented correctly as a data structure.** `build_ve_menu()` and `apply_ve_decision()` are solid. The frontend can render PENDING/ACCEPTED/REJECTED states per VE item.

**Gap:** The VE suggestions fed into `build_ve_menu()` come from `ValueEngineeringEngine.find_ve_opportunities()`. If that engine returns an empty list (e.g., no catalog alternatives found), the VE menu has zero items. There is no fallback set of standard facade VE options (e.g., "Replace double-glazed unit with single for non-critical elevations", "Substitute structural silicone brand"). The menu is only as good as the VE engine output.

**Gap:** `apply_ve_decision()` updates the `ve_menu` dict in memory but does **not** write back to the BOM. The `affected_item_codes` and `substitute_item_code` fields exist but no function actually modifies `bom_items` when a VE decision is accepted. A confirmed VE saving does not reduce the BOQ value automatically — the estimator must re-run the pipeline or manually adjust. This breaks the promise that "Accepted items automatically update the BOQ."

---

### 4.4 C8 Yield Optimization — CuttingListEngine Integration

**The integration path exists but is fragile:**

In `_bom_impl`:
1. CSP optimizer is called directly with a simplistic demand array.
2. The `length_mm` calculation `int(item.get("quantity", 1) * 1000 / max(qty, 1))` is dimensional analysis nonsense — it divides (quantity × 1000) by quantity = 1000mm, hardcoding 1 meter demand for every profile regardless of actual window dimensions. This produces uniformly wrong cutting demands.
3. `bar_assignments` are never populated on cutting list items (the CSP result `plan` is not mapped back to `bar_assignments`).

In `optimize_yield_and_scrap()` (C8):
- If `bar_assignments` is empty, the function falls back to estimating 40% of scrap as usable. This is a rough approximation.
- The usable inventory Blind Spot Rule #5 (>800mm offcuts → ERP) requires accurate `bar_assignments` to be meaningful. Without them, it produces estimated numbers, not actual offcut positions.

**Recommendation:** The CSP optimizer should be called with actual cut lengths derived from opening dimensions (width + height mullions), not the current averaging formula. This requires passing `extracted_openings` with actual geometry to the cutting optimizer, not the BOM quantity totals.

---

### 4.5 Summary of Commercial Director Findings

| # | Finding | Severity | Component |
|---|---------|----------|-----------|
| 1 | S-curve retention at week 52, milestone schedule at week 104 — inconsistent | HIGH | C5 |
| 2 | C4 supplier leveling never called in pipeline — dead function in graph flow | HIGH | C4 |
| 3 | VE accept decision does not modify BOM — savings are not applied | HIGH | C11 |
| 4 | Cutting list `length_mm` formula is wrong (always 1000mm) | HIGH | C8 |
| 5 | No container cost calculation for international projects | MEDIUM | IntlRouting |
| 6 | VE menu empty if VE engine finds no opportunities — no default options | MEDIUM | C11 |
| 7 | Forex buffer silently 0 if PricingNode failed | LOW | IntlRouting |

---

---

## TASK 3 — Error Handling Improvements Applied

The following changes were made directly to `backend/app/agents/estimator_graph.py`. All edits are AST-verified.

### 3.1 `make_node()` — `critical` Parameter Added

**Signature change:**

```python
def make_node(name, progress, impl=None, redis_client=None, critical=False)
```

When `critical=True` and the node's `impl()` raises an exception:
- `state["hitl_pending"] = True` — forces the `should_triage` conditional edge to route to `HITLTriageNode`
- `state["status"] = "REVIEW_REQUIRED"` — immediately marks the estimate as requiring human review
- A timestamped triage ID `node_failure_{name}_{timestamp}` is appended to `state["hitl_triage_ids"]`

This prevents a crashed `BOMNode` from silently producing a zero-value quote.

**Critical nodes designated:**
| Node | Rationale |
|------|-----------|
| `IngestionNode` | No openings → entire pipeline is meaningless |
| `BOMNode` | Zero BOM items → pricing produces AED 0 without warning |

All other nodes remain `critical=False` — their failures are logged in `state.error_log` and the pipeline continues to `ApprovalGatewayNode` where the approver sees error context.

### 3.2 Error Log — Never Overwrites

The existing `state["error"]` field (last error wins) is preserved for backwards compatibility. The new `state["error_log"]` list **accumulates** every node failure:

```python
error_log: List[dict] = list(state.get("error_log") or [])
error_log.append(err.to_dict())
state["error_log"] = error_log
```

Each entry contains `{node, error, traceback, at}`. Multiple failing nodes are all visible.

### 3.3 Inner `try/except` Removed from `_ingestion_impl`

**Before:** The entire ingestion sub-graph call was wrapped in a bare `except Exception as e` that set `state["extracted_openings"] = []` and returned. The outer `make_node` wrapper never saw an exception, so `state["error"]` was never set, HITL was not triggered, and the error was invisible.

**After:** Fatal exceptions from `ingestion_app.ainvoke()` now propagate to `make_node`. The sub-graph's *soft* errors (e.g., DWG layer naming not recognised) are still handled by checking `result.get("error")` and capping confidence — these are non-fatal.

### 3.4 Inner `try/except` Removed from `_compliance_impl`

**Before:** Same pattern — `except Exception as e` caught the engine crash and stored `{"overall_passed": None, "error": str(e)}` in `state["compliance_report"]`. This looked like a compliance result rather than an engine failure.

**After:** Fatal exceptions propagate to `make_node`. The approver now sees a clear `state.error_log` entry for a compliance engine crash rather than an ambiguous `overall_passed: null` result.

### 3.5 `build_estimator_graph()` — `redis_client` Parameter Added

**Before:** `build_estimator_graph()` called `make_node()` without a `redis_client`, so Redis checkpointing was never active despite the infrastructure being in place.

**After:**

```python
def build_estimator_graph(redis_client=None):
    def _n(name, progress, impl, *, critical=False):
        return make_node(name, progress, impl, redis_client=redis_client, critical=critical)
    # all 12 nodes use _n(...)
```

Production callers pass their Redis client at startup:
```python
from app.agents.estimator_graph import build_estimator_graph
graph = build_estimator_graph(redis_client=redis)
```

The module-level singleton `estimator_graph` is compiled without Redis (safe for import-time and unit tests).

### 3.6 Progress Percentages — Widened Compliance Band

ComplianceNode progress corrected from 78% to 80%, and InternationalRoutingNode from 80% to 83%, matching `NODE_PROGRESS` in `config.py`. This widens the compliance progress band from 3 percentage points to 5, reducing the "stalled" appearance on the frontend progress bar.

### 3.7 Remaining Known Issues (Not Fixed in This Pass)

| # | Issue | Reason Not Fixed |
|---|-------|-----------------|
| 1 | HITL does not truly suspend graph (no LangGraph interrupt_before) | Requires LangGraph MemorySaver/AsyncPostgresSaver and approval endpoint changes — out of scope for graph.py edits |
| 2 | `should_triage_post_compliance()` not wired | Would create a HITL loop with no resume mechanism — deferred |
| 3 | Checkpoint key sort uses node name (lexicographic) not index | Fixed in `_checkpoint()` by using zero-padded `NODE_INDEX` prefix — existing logic is correct |
| 4 | Missing currency conversion for international projects | Service-level work in `_international_routing_impl` — not a graph architecture change |
| 5 | Cutting list `length_mm` formula wrong (always 1000mm) | BOM engine logic, not graph architecture |

---

*End of architecture review.*
