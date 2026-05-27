# Multi-MAS Federation Architecture

**Doc Type**: Architecture Decision Record (ADR)
**Status**: Production

---

## 0. Summary

Multi-MAS Federation extends the single-MAS architecture with a meta-level coordinator and a cross-instance message broker. The single-MAS limit (7 to 8 agents, single domain) gives way to enterprise scale (50+ agents, multiple domains).

---

## 1. Four Federation Patterns
<protocol_definition>

| Pattern | Description | Recommended Use Case |
|---|---|---|
| **Hierarchical** | Meta-Orchestrator -> domain MAS | 50+ agent enterprise |
| **Peer-to-Peer** | Direct instance-to-instance communication | Independent cross-audit |
| **Hub-Spoke** | Central hub MAS + domain spokes | Domain specialization + central control |
| **Swarm** | Homogeneous many-MAS with distributed consensus | Redundancy and fault tolerance |

Each pattern carries trade-offs. Production deployments often use hybrids (for example, Hierarchical on top + Hub-Spoke below).
</protocol_definition>

---

## 2. Integrated Architecture
<integration_note>

```
+----------------------------------------------------+
|         Federation Coordinator (Meta)              |
|   - Pattern: hub_spoke / hierarchical / ...        |
|   - Task routing (domain match)                    |
|   - Message broker (cross-instance)                |
|   - Cross-MAS audit                                |
|   - Learning share                                 |
+----------------------------------------------------+
             |
   +---------+---------+---------+---------+
   v         v         v         v         v
+------+ +------+ +------+ +------+ +------+
| MAS  | | MAS  | | MAS  | | MAS  | | MAS  |
|Finance| |Legal | |Mktg  | |R&D   | |Audit |
+------+ +------+ +------+ +------+ +------+
   |        |        |        |        |
   +-- 8-agent + harness inside each instance ---+
   +-- Isolated state/ and persistent/ dirs -----+
```

Each MAS instance keeps the full 8-agent + harness capability. Federation is layered on top.
</integration_note>

---

## 3. Federation Coordinator Responsibilities
<protocol_definition>

### 3.1 Instance Lifecycle
- spawn (per domain)
- monitor (heartbeat-based health)
- terminate (on completion or failure)

### 3.2 Task Routing
```
Hierarchical: router decides task -> domain -> instance
Hub-Spoke: hub classifies then dispatches to spoke
Peer-to-Peer: broadcast and pick the first responder
Swarm: any available instance
```

### 3.3 Cross-Instance Message Broker
- File-based (development): `federation_messages.json`.
- Production: Kafka, Redis Streams, or Anthropic Managed Agents memory.

Message types:
- `task_request`
- `audit_request` / `audit_response`
- `learning_share`
- `status_query` / `status_response`
- `result_return`
- `heartbeat`
- `termination_signal`

### 3.4 Cross-MAS Audit
One instance audits another's output as part of its self-audit mode.
- Finance MAS output -> Legal MAS audits from a compliance angle.
- Worker A instance result -> independent instance B re-verifies facts.

### 3.5 Cross-Instance Learning Share
One instance broadcasts learned patterns / specialists to the others.
</protocol_definition>

---

## 4. Production Deployment Paths
<integration_note>

### 4.1 Anthropic Managed Agents API (recommended)
- Each MAS instance registers as a managed agent.
- Pros: managed sandboxing, hardened security, SSE streaming.
- Cons: beta spec with possible breaking changes.

### 4.2 Multi-process / Container Orchestration
- Each MAS instance = OS process or Kubernetes pod.
- Message broker: Kafka, Redis Streams.
- Pros: true parallelism, fault isolation.
- Cons: high operational complexity.

### 4.3 Single Session Sub-Agent Fork (limited)
- Simulate inside a single Claude session using sub-agents.
- Pros: immediately available, no external infra.
- Cons: not truly parallel, token cost explodes.
</integration_note>

---

## 5. Migration Steps
<integration_note>

```
[Step 1] Stabilize single-MAS + harness operation for 5+ sessions.
   |
[Step 2] Choose a federation pattern.
   |
[Step 3] Choose a production path.
   |
[Step 4] Promote scaffolding to production code.
   - Implement MASInstance.spawn().
   - Integrate the message broker with an external system.
   - Formalize the cross-MAS audit protocol.
   |
[Step 5] Pilot in a single domain (e.g., Finance only).
   |
[Step 6] Expand to multiple domains (Finance + Legal + Marketing).
   |
[Step 7] Enable cross-MAS audit + learning share.
   |
[Step 8] Operate 50+ agent enterprise.
```
</integration_note>

---

## 6. Risk Register
<integration_note>

| ID | Risk | P | I | RPN | Mitigation |
|---|---|---|---|---|---|
| F-R1 | Federation token cost explosion (Nx) | 5 | 5 | 25 | Prefer Hub-Spoke; avoid Swarm |
| F-R2 | Cross-instance message loss | 3 | 4 | 12 | Persistent broker + retry policy |
| F-R3 | Learning share propagates a bad pattern | 4 | 4 | 16 | Only share patterns that passed cross-MAS audit |
| F-R4 | Managed Agents spec breaking | 3 | 5 | 15 | Adapter pattern + multi-process fallback |
| F-R5 | Coordinator is a single point of failure | 3 | 4 | 12 | Coordinator HA / redundancy |
| F-R6 | Cross-instance auth / security | 3 | 5 | 15 | OAuth + scoping + audit log |
</integration_note>

---

## 7. Success Metrics
<integration_note>

| KPI | Target | Measurement |
|---|---|---|
| Domain expert accuracy | +10 to +20% vs. single MAS | A/B test |
| Cross-MAS audit detection | >= 5% additional critical_false vs. single MAS | Synthetic ground truth |
| Learning-share transfer rate | >= 30% pattern reuse across domains | hot_pattern analytics |
| Federation token overhead | <= 12% on top of N x (single MAS) | Telemetry |
| Message latency | p95 <= 500ms (file) / <= 100ms (Redis) | Measurement |
</integration_note>

---

## 8. Single-MAS vs. Federation
<integration_note>

| Area | Single MAS + Harness | Federation |
|---|---|---|
| Agents | 8 (incl. Polisher) | 8 x N + 1 Coordinator |
| Communication | state file + agent_messages.json | + federation_messages.json |
| Learning | persistent `meta.json` | + cross-instance learning share |
| Verification | Watchdog Pool + Adversarial Critic | + cross-MAS audit |
| Domain | Single (general) | Multiple (finance, legal, marketing, ...) |
| Token cost | 2 to 3x baseline | N x 1.2x baseline |
| Operational complexity | medium | high (coordinator HA) |
</integration_note>

---

## 9. When to Use Which
<integration_note>

**Single MAS + Harness** (about 90% of use cases):
- General analysis, reporting, review tasks.
- Single-domain deep dives.
- Cases that benefit from review rounds and debates.

**Federation** (about 10% of use cases):
- Enterprise scale (50+ agents required).
- Multi-domain simultaneous analysis (Finance + Legal + Marketing).
- Independent cross-audit required (high-stakes decisions).
- Repeated domains where federation learning provides value.
</integration_note>
