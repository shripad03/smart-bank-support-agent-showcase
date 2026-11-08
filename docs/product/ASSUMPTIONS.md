# Smart Bank Customer Support Agent: Assumptions

## 1. Document control

| | |
|---|---|
| Version | 1.0 |
| Status | Approved by the product owner, 2026-11-08. The owner decisions in section 12 take their stated defaults until changed. |
| Date | 2026-11-08 |
| Owner | Product and Engineering |
| Related documents | `product/PRD.md` (requirement ids FR, PR, NFR, CR, RK, D), `product/KNOWN_ISSUES.md` (register ids), `product/USE_CASES.md` |

An assumption is something the design relies on that the project does not control or has not yet proven. Each row states why it is assumed, what happens if it is wrong, how it will be checked and in which delivery phase (PRD section 13). Constraints that are already decided are in PRD section 10 and the decision log (D-01 to D-05); they are not repeated here.

Status values: **Confirmed** (a recorded decision supports it), **Observed** (measured in a run, not guaranteed), **Open** (needs an owner decision; listed in section 12).

## 2. Identity and authentication

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-01 | The platform in front of the agent authenticates the customer and supplies a verified customer id. The agent never authenticates anyone and never takes an id from message text. | Open | The agent has no credential store; identity must be a platform responsibility (NFR-01). | Today the id is trusted from the caller and the handoff states `identity_verified: true` unconditionally, so any caller could receive another customer's context. | Threat model names the trust boundary (Phase 2). Phase 4 tests: no credential gives no customer data and `identity_verified: false`; an invalid credential is rejected, not treated as anonymous. | 2, 4 | NFR-01, FR-13, SEC-2, RK-4 |
| A-02 | Anonymous sessions are allowed for general policy questions only: no customer context, no account-specific statements, and any handoff records identity as not verified. | Open | General policy answers need no personal data, and a public channel is a plausible entry point. | The agent states account details for an anonymous caller (observed: Q15 assumed a Premier account without any customer context). | Tests that an anonymous turn never calls the customer-context tool and never mentions tier or tenure. | 3, 4 | GND-3, FR-13 |
| A-03 | Human agents confirm the customer's identity through their own process before acting on a handoff. The handoff's identity flag is an input to that process, not proof. | Open | The agent cannot verify identity and must not claim to. | A human acts on a handoff for a caller who impersonated a customer (social engineering through the handoff). | Phase 8 runbook step "verify identity before action"; handoff payload carries the verification level actually achieved. | 8 | RK-5, FR-09, SEC-2 |

## 3. Data

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-04 | All customers, transactions, policy text and contact details are synthetic. No real customer data enters the system. | Confirmed | PRD constraint; PR-09, CR-02. | Real personal data typed into a test chat lands in logs, handoffs and checkpoints, which redact only card numbers and emails. | Synthetic markers on data files; PII redaction corpus in Phase 2 and 6 (SSN, phone, name, address) so free text is safe even when a tester types real values. | 2, 6 | PR-09, CR-02, SEC-7 |
| A-05 | Customer profile and transaction data are supplied read-only by the platform and are accurate and current. The agent does not verify them. Transaction descriptions are untrusted free text. | Open | The agent explains policy and context; it is not a system of record. | Stale or wrong context produces a wrong account-specific answer; a malicious description acts as indirect injection. | Context fenced as untrusted in prompts; indirect-injection cases in the red-team set (Phase 3). | 2, 3 | FR-13, SEC-5 |
| A-06 | The customer's message and the minimised customer context are sent to the model provider's endpoint. This is acceptable for synthetic data; real data would need a processing agreement, region control and retention terms. | Open | The design calls an external hosted model. | A move to real data would breach data-handling obligations. | Data-flow diagram and provider assessment in the Phase 2 threat model; a gate before any real data is used. | 2, 7 | PR-09, NFR-02 |

## 4. Languages

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-07 | Customers write in English or Spanish. The router detects the language and the reply follows it. Fixed texts exist in both. | Confirmed | Decision D-04. | Other languages receive English fixed text; mixed-language messages are misdetected. Fixed refusals skip the router, so their language is unknown (injection refusals are English only). | Golden dataset with Spanish and mixed-language rows; a Spanish speaker reviews all fixed texts, including the UC-15 refusal. | 3 | D-04, FR-11, UC-15 |
| A-08 | The knowledge base is English only; Spanish questions are answered from English entries through the router's English summary and model translation. | Observed | One KB avoids duplicate content; the router already produces an English summary. | Raw Spanish retrieval returns nothing (Q14, RET-5), so Spanish quality depends entirely on the router summary. | Retrieval evaluation reports English and Spanish rows separately; compare keyword, hybrid and embedding retrieval against the baseline. | 3 | FR-03, FR-11, RET-5 |

## 5. Knowledge base ownership and freshness

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-09 | A named content owner approves every knowledge-base change, which goes through version control and the retrieval and grounding evaluations before release. | Open | The KB is the single source of policy truth (CR-01). | Unowned content drifts; the agent states outdated or unapproved policy confidently. | Owner named in this document before Phase 3; CI runs the evaluations on KB changes; KB hash recorded in every evaluation result. | 3, 7 | CR-01, FR-01 |
| A-10 | The knowledge base is small (17 entries), loaded once per process, and changes only through a release. A restart refreshes it. | Observed | Simplicity for the current stage. | A policy correction does not reach a running process; a growing KB outgrows keyword search and the in-memory cache. | Reload and invalidation test; recall tracked as entries grow. | 3, 5 | REL-6, RET-1 |
| A-11 | The product owner supplies approved synthetic wording for deposit insurance and the other coverage gaps. | Open | Decision D-02; no assurance may be given without a source. | Q13 keeps producing an unsupported assurance; customers read it as a real commitment. | Q13 passes with a cited source once the entry exists; coverage-gap decisions recorded for each CR-04 item. | 1, 3 | D-02, CR-03, CR-04, GND-1, RK-6 |

## 6. Model provider and availability

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-12 | Provider and model are configuration. Any OpenAI-compatible chat model that supports function-calling structured output and tool calling can be used after passing the evaluation set. Development currently uses NVIDIA NIM with thinking disabled. | Confirmed | Decision D-05, NFR-11. | A model without reliable function calling breaks routing silently; the offline fake cannot detect it. | Capability checks and the real-model evaluation run per model; every result labelled with the model name. | 3 | D-05, NFR-11, REL-1, TST-1 |
| A-13 | Model output varies between runs even at temperature 0, so any quality claim needs repeated runs and a stated tolerance. | Observed | Q08 was refused in 18 of 20 repeated calls and answered differently in the others. | A single passing run is read as a guarantee, and regressions go unnoticed. | Evaluation harness repeats each case N times and reports a rate, not a single outcome. | 3 | RK-1, RTR-1, REL-10 |
| A-14 | A paid provider with contractual limits and a defined fallback is available for production. The free tier is for development only. | Open | The free tier rate-limits and offers no service level. | Production inherits intermittent 429s and has no recovery path. | Failure-injection tests (429, timeout, malformed output) in Phase 3; provider terms recorded before Phase 7. | 3, 7 | RK-2, RK-7, NFR-03, NFR-05 |

## 7. Rate limits and load

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-15 | The deployment stays within the provider's request limit (the free tier returned HTTP 429 at roughly 30 or more requests per minute). Per-customer and per-deployment limits are applied in the service layer. | Observed | Each turn makes one to five model calls, and transport retries multiply them. | Router calls fail twice and ordinary customers are escalated or told their case is being passed on (4 of 80 burst calls failed). | Load test against the real provider; rate-limit and handoff-cap tests; retry budget with backoff. | 3, 4, 8 | NFR-03, NFR-09, REL-3, REL-11, SEC-8 |
| A-16 | Expected load is low (single-digit concurrent conversations until a target is agreed in `ACCEPTANCE_CRITERIA.md`), served by one process. | Open | No demand figure exists; the design is synchronous and in-memory. | Concurrency exposes the unlocked log writer and unbounded in-memory state. | Concurrency and long-thread tests; load targets set and verified in Phase 7. | 4, 7 | REL-5, REL-8, NFR-05 |

## 8. Tenancy

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-17 | Single tenant: one bank, one knowledge base, one configuration, one deployment region. | Open | Simplest model; no multi-tenant requirement exists (PRD open question 5). | Adding tenants later requires isolated KBs, configuration, logs and handoff stores, and a tenant id in every key. | Decision recorded in Phase 2; the threat model states the isolation boundary. | 2 | PRD 12.2 |

## 9. Retention of conversations and logs

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-18 | Conversations, checkpoints, logs and handoffs are kept for a defined period and deleted on request. The period is not yet set. Today nothing is deleted: checkpoints live in memory until the process ends, logs and handoffs are plain local files. | Open | Needed for privacy and for bounded storage (NFR-02). | Personal data accumulates without limit and cannot be removed on request. | Retention job and a deletion-request test (Phase 5 and 6); retention periods approved by the owner. | 5, 6 | NFR-02, SEC-7, REL-5, PRD 12.2 |
| A-19 | Logs and handoff files are readable only by engineering and operations staff and are never shared outside the deployment. | Open | They contain customer text excerpts and account context. | Unmasked names, phone numbers and SSNs leak through a shared or copied log. | Access control and redaction tests; no raw excerpts in shared artefacts. | 6 | SEC-7, NFR-07 |

## 10. Human escalation

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-20 | Human support staffs the four queues (`tier2_support`, `customer_care_supervisor`, `fraud_ops`, `compliance`) with service levels set by the business. The agent does not know queue capacity or opening hours. | Open | Escalation is only useful if someone answers. | Customers are told their case is with a person while it waits unattended. | Phase 8 console and handoff-age metric; the customer message makes no timing promise (PR-05). | 8 | FR-09, FR-15, PR-05, PRD 12.2 |
| A-21 | A handoff is delivered to a durable store that humans read. Today it is a line in a local file that nobody reads. | Observed | Phase 5 adds durable storage; Phase 8 adds the console. | An escalation silently goes nowhere. | Handoff persistence test across restart; delivery check in the human workflow. | 5, 8 | FR-09, REL-6, REL-8 |
| A-22 | The escalation weights and thresholds (30 to escalate, 60 for HIGH) are provisional. They were tuned on 15 cases and will be retuned against labelled data. | Observed | No evaluation of escalation correctness exists yet. | Over-escalation (Q14) or missed escalation goes undetected. | Evaluation measures escalation precision and recall per reason; threshold sweep before any target is claimed. | 3, 9 | FR-07, FR-08, D-03 |

## 11. Channel and input

| ID | Assumption | Status | Rationale | Risk if wrong | Validation | Phase | References |
|---|---|---|---|---|---|---|---|
| A-23 | Customers send one text message at a time, up to 2,000 characters. No attachments, voice or images. | Confirmed | PRD non-goals; the input guard truncates at 2,000. | Longer messages are silently truncated; a relevant detail after the cut is lost. | Oversize-input test; the service layer returns a clear error instead of silent truncation. | 4 | PRD 3.2, D-04 |

## 12. Decisions needed from the owner

| ID | Decision | Needed before | Proposed default |
|---|---|---|---|
| A-01, A-03 | Who authenticates customers and humans, and how the verification level is reported | Phase 2 design | Platform authenticates; the agent receives a verified claim |
| A-02 | Allow anonymous general questions | Phase 2 design | Yes, general policy only, no customer context |
| A-06 | Acceptability of sending data to a hosted model, for synthetic data and for any future real data | Phase 2 threat model | Acceptable for synthetic data only |
| A-09, A-11 | Named content owner; approved wording for deposit insurance and the CR-04 gaps | Phase 3 | Product owner |
| A-14 | Production provider, limits and fallback | Phase 7 | Paid provider with a second provider as fallback |
| A-16 | Expected load and availability target | Step 1.4 | Proposed in `ACCEPTANCE_CRITERIA.md` |
| A-17 | Single tenant | Phase 2 | Single tenant |
| A-18, A-19 | Retention periods and log access | Phase 5 | Proposed in the Phase 2 data-handling design |
| A-20 | Queue staffing and service levels | Phase 8 | Set by the business; the agent makes no timing promise |

## 13. Traceability

| Group | Assumptions | PRD requirements | Register items |
|---|---|---|---|
| Identity | A-01 to A-03 | NFR-01, FR-13, FR-09, RK-4, RK-5 | SEC-2, GND-3 |
| Data | A-04 to A-06 | PR-09, CR-02, NFR-02 | SEC-5, SEC-7 |
| Languages | A-07, A-08 | D-04, FR-03, FR-11 | RET-5 |
| Knowledge base | A-09 to A-11 | CR-01, CR-03, CR-04, FR-01 | GND-1, REL-6, RET-1 |
| Model provider | A-12 to A-14 | NFR-11, NFR-03, RK-1, RK-2, RK-7 | REL-1, TST-1, RTR-1, REL-10 |
| Rate limits and load | A-15, A-16 | NFR-03, NFR-09, NFR-05 | REL-3, REL-5, REL-8, REL-11, SEC-8 |
| Tenancy | A-17 | PRD 12.2 | none |
| Retention | A-18, A-19 | NFR-02, NFR-07 | SEC-7, REL-5 |
| Escalation | A-20 to A-22 | FR-07, FR-08, FR-09, FR-15, PR-05 | REL-6, REL-8 |
| Channel | A-23 | PRD 3.2 | none |
