# Smart Bank Customer Support Agent: Product Requirements Document

## 1. Document control

| | |
|---|---|
| Version | 1.0 |
| Status | Approved by the product owner, 2026-11-08. |
| Date | 2026-11-06 |
| Owner | Product and Engineering |
| Baseline | Branch `phase-0-baseline`, 66 offline tests passing, live run of 2026-11-03 |
| Related documents | `product/KNOWN_ISSUES.md` (register v2), `ARCHITECTURE.md`, `PROJECT_ASSESSMENT.md`, `tests/test_queries.json`, `eval/results/baseline_retrieval.md`; to follow: `USE_CASES.md`, `ASSUMPTIONS.md`, `ACCEPTANCE_CRITERIA.md` |

Conventions. "Current" describes behaviour verified at the baseline. "Target" is a requirement that is not yet met. Register identifiers (for example RTR-1, SEC-11) refer to `product/KNOWN_ISSUES.md`. Thresholds are deliberately not set here; they are proposed in `ACCEPTANCE_CRITERIA.md` for approval.

## 2. Purpose and problem statement

Retail banking customers contact support about the mobile app, fees and charges, accounts and suspected fraud. Most questions are answered by published policy; a minority are urgent, emotional or sensitive and must reach a person quickly with full context.

The Smart Bank Customer Support Agent answers policy questions from an approved knowledge base, uses the signed-in customer's own account context where it helps, and hands urgent or unresolved cases to human support with a structured, auditable handoff. It never acts on accounts, never discloses another person's information, and says plainly when it does not know.

The system operates on synthetic customers, transactions and policy text. No real banking system or real customer data is connected.

## 3. Goals, non-goals and success metrics

### 3.1 Goals

| ID | Goal |
|---|---|
| G-1 | Answer in-scope policy questions correctly and only from approved sources. |
| G-2 | Escalate the right cases, with the right priority, to the right queue, with context. |
| G-3 | Keep each customer's data isolated, including against social-engineering attempts. |
| G-4 | Degrade gracefully: an outage or rate limit must not mislead customers or flood human queues. |
| G-5 | Be measurable: every quality claim is backed by a repeatable evaluation. |
| G-6 | Be operable: observable, auditable, deployable and recoverable. |

### 3.2 Non-goals

- Performing account actions: moving money, unlocking accounts, filing disputes, changing details, issuing refunds, waivers or credits.
- Financial, tax or legal advice, product recommendations or credit decisions.
- Commenting on news events, general conversation, or topics unrelated to the bank's services.
- Voice, telephony or in-branch channels.
- Languages other than English and Spanish.
- Connecting to real banking systems or processing real customer data.

### 3.3 Success metrics and current values

Targets are proposed in `ACCEPTANCE_CRITERIA.md`. Current values below come from single engineering runs, not from a labelled evaluation.

| Metric | Current value | Source |
|---|---|---|
| Scenario conformance (expected behaviour met) | 10 of 15 fully, 3 partially, 2 not met | Section 11, live run 2026-11-03 |
| Retrieval recall@3 on raw customer text | 13 of 21 (62%) | `eval/results/baseline_retrieval.md` |
| Retrieval recall@3 with scripted router summaries | 11 of 11 scenario rows | same |
| Turn latency (live, thinking disabled) | 0.9 to 10 s per query, 70 s for 15 queries | Live run |
| Router calls that failed on both attempts (rate limit) | 4 of 80 in a burst test | KNOWN_ISSUES REL-3 |
| Unsupported factual claims observed | 1 in 15 scenarios (Q13) | KNOWN_ISSUES GND-1 |
| Cross-customer data leaks observed | 0 in 12 probes | KNOWN_ISSUES SEC-11 |

## 4. Users and stakeholders

| Role | Description | Interaction with the system |
|---|---|---|
| Customer | Authenticated retail customer, English or Spanish speaking | Asks questions; receives answers, clarifications, refusals or a handoff confirmation |
| Human support agent (tier 2) | Handles unresolved cases | Receives handoffs in queue `tier2_support` (target: console, Phase 8) |
| Customer care supervisor | Handles explicit requests for a person and distress | Queue `customer_care_supervisor` |
| Fraud operations | Handles reported unauthorised activity | Queue `fraud_ops` |
| Compliance | Handles legal or regulatory threats | Queue `compliance` |
| Administrator and operations | Owns knowledge-base content, configuration, limits and runbooks | Target: admin interface, Phase 8 |
| Engineering | Builds, tests and operates the system | Repository, evaluations, observability |
| Security and compliance reviewers | Review threat model, data handling and audit trail | Phase 2 deliverables, logs |

Queue names are current behaviour (`agent/policy.py`); the human-side tooling is a target.

## 5. Scope

### 5.1 In scope

- **Channels:** chat through an API (Phase 4) with a customer-facing web interface. Current: a Python entry point `run_agent(query, thread_id, customer_id)` and the assessment harness.
- **Languages:** English and Spanish. The reply follows the customer's language.
- **Topics:** technical (app, login, PIN, two-factor, cards in the app, notifications, scheduled-transfer failures), billing (fees, overdraft, disputes, wires, rates, late fees), general (branches, account opening, Zelle and ACH, fraud-reporting information, loans, deposit safety).
- **Capabilities:** grounded answers with sources, multi-topic questions, clarification, escalation with handoff, refusal of injection, out-of-scope and third-party requests, conversation continuity.

### 5.2 Boundary

The agent is read-only. It explains how the customer performs an action; it does not perform it. Anything not covered by the knowledge base is answered with a plain statement that the information is not available, with an offer to connect the customer to support.

## 6. Functional requirements

Each row states the requirement, the current behaviour and the gap. "Phase" is the delivery phase in section 13.

| ID | Requirement | Current | Gap and register references | Phase |
|---|---|---|---|---|
| FR-01 | **Grounded answers.** Every factual statement (amounts, rates, hours, durations, contact details, policy claims) must be supported by a retrieved knowledge-base entry or the customer's own context. | Retrieval runs before generation; no match gives a fixed "no information" reply; dollar and percentage figures are checked against sources; extractive fallback on failure. | Only `$` and `%` are checked (SEC-6). Unsupported assurance observed (GND-1). | 3 |
| FR-02 | **Sources.** The reply lists only the entries actually used, and never cites sources while saying it has no information. | The sources line lists every retrieved entry. | GND-2 (for example Q09, Q05). | 3 |
| FR-03 | **Retrieval quality.** Natural phrasing, synonyms, short queries and Spanish must retrieve the correct entry without depending on a hand-written English summary. | Keyword search with stemming; 62% recall on raw text. | RET-1, RET-2, RET-3, RET-5. | 3 |
| FR-04 | **Routing.** Classify language, scope (in scope, out of scope, injection), up to three intents with category, sentiment and escalation signals; results must be stable across repeated runs. | One LLM structured-output call, two attempts, fail closed. | RTR-1 (emotion-only message refused 18 of 20), REL-10, REL-3. | 3 |
| FR-05 | **Multi-topic.** A message with several questions is answered in full, in priority order, without silently dropping a part. | Sequential specialists, up to three intents. | Technical advice grounding in Q06 unverified. | 3 |
| FR-06 | **Clarification.** When there is no actionable question (for example only emotion), acknowledge the sentiment and ask one clarifying question; escalate if the customer remains distressed without detail. | Designed; the live router refuses such messages instead. | RTR-1. Scenario Q08 not met. | 3 |
| FR-07 | **Escalation.** One score decides: threshold 30, HIGH at 60. Reasons: active fraud 70, legal or regulatory threat 60, explicit request for a person 40, repeated unresolved 30, system failure 30, knowledge-base gap 15, emotional distress 10 or 25; modifiers for amount, open ticket, tier and tenure. | Implemented as specified and covered by offline tests. | Weights hand-tuned on 15 cases; no live evaluation of escalation correctness. | 3 |
| FR-08 | **Fraud rule.** Fraud escalation applies only when the customer reports unauthorised activity or compromise. A blocked card with no stated cause is a technical question: answer from the knowledge base and offer to connect support. | Q14 ("card blocked, I don't know why") was escalated HIGH as possible unauthorised activity. | ESC-1 (over-escalation). Decision D-03. | 3 |
| FR-09 | **Handoff.** Each escalation produces a structured payload: id, reason, secondary reasons, priority and score with factors, recommended queue, customer context, relevant transactions, attempted resolution, conversation excerpt and flags. It is stored durably and visible to the assigned human. | Payload written to a local JSONL file; no queue; `identity_verified` is always true for a known id. | SEC-2, REL-6, REL-9. | 5, 8 |
| FR-10 | **Open-case follow-ups.** A message on a thread with an open handoff is appended to that handoff, or answered normally if it is a new question; the reply must not claim an action that did not happen. | The reply says the message was added, but the handoff is unchanged. | REL-2 (High), REL-9. | 3, 8 |
| FR-11 | **Language.** Reply in the customer's language. Fixed texts exist in English and Spanish. | Works for Q14; fixed text for other languages falls back to English. | RET-5 (Spanish raw retrieval returns nothing). | 3 |
| FR-12 | **Conversation continuity.** The agent keeps context within a conversation across turns and across restarts. | Per-thread state in memory; specialists see only the current message and the router's summary. | REL-4, REL-5, REL-6. | 5 |
| FR-13 | **Customer context.** Use only the signed-in customer's minimised, read-only data (account type, open tickets, recent transactions). | Tools are bound to the session customer id; the model cannot choose whose data to read. | The id is trusted from the caller (SEC-2). | 4 |
| FR-14 | **Refusals.** Injection attempts, out-of-scope requests and third-party account requests receive fixed refusals that do not echo the request. | Injection and out-of-scope: fixed text. Third-party requests: not recognised. | SEC-3, SEC-4, SEC-11. | 2, 3 |
| FR-15 | **Human workflow (target).** Supervisors and agents can see, claim, update and close handoffs; the customer sees case status. | Not built. | Phases 4 and 8. | 8 |
| FR-16 | **Feedback (target).** Customers can rate answers; ratings feed evaluation. | Not built. | Phase 8. | 8 |

## 7. Prohibited actions and safety requirements

The agent must never do the following. Each is enforced by design and verified by a test or evaluation case.

| ID | Prohibition | Enforcement | Register |
|---|---|---|---|
| PR-01 | Disclose any other customer's data: ids, names (including first names), balances, transactions, tickets. | Tools bound to the session customer; output guard blocks other ids and full names. Target: block first names and other identifiers. | SEC-6b |
| PR-02 | **Third-party account requests.** A request for another person's account details (relative, representative or any other claim of authority) receives a **fixed refusal stating that only the signed-in customer's own account can be discussed, plus a logged security event, with no handoff and no model-written wording.** | Target: deterministic policy check ahead of the specialists; fixed text in English and Spanish. | SEC-11, decision D-01 |
| PR-03 | Follow instructions found in customer text, transaction descriptions, knowledge-base text or tool output; reveal system prompts or rules. | Input screening, delimited prompts, router scope check, canary. | SEC-3, SEC-4, SEC-5 |
| PR-04 | Perform or claim to perform account actions: move money, unlock or freeze accounts, file disputes, change details. | Read-only tools; explain how the customer does it. | none |
| PR-05 | Promise refunds, waivers, credits, outcomes or timelines that a knowledge-base entry does not state. | Prompt rules and grounding check. | FR-01 |
| PR-06 | Give financial, tax or legal advice, or comment on news events. | Router scope and prompt rules. | none |
| PR-07 | State figures, hours, phone numbers, URLs or durations that are not in a source. | Target: extend the grounding check beyond `$` and `%`. | SEC-6 |
| PR-08 | Echo or acknowledge injected instructions. | Fixed refusal text. | none |
| PR-09 | Process real customer or real banking data. | Synthetic data only; no external banking connections. | none |

Proposed fixed refusal for PR-02 (wording to be approved in `USE_CASES.md`):
- English: "I can only discuss the account you are signed in to. For someone else's account, the account holder, or a legally authorised representative, needs to contact us directly."
- Spanish: the equivalent text, with the same meaning.

The security event for PR-02 records the trace id, thread id, signed-in customer id and a redacted excerpt, so repeated attempts are visible.

## 8. Non-functional requirements

| ID | Requirement | Current | Register | Phase |
|---|---|---|---|---|
| NFR-01 | **Identity.** Customer identity is derived from authenticated context supplied by the platform, never from the model or free text. `identity_verified` is true only after real verification. | Caller-supplied id trusted; flag hard-coded. | SEC-2 | 4 |
| NFR-02 | **Privacy.** Redact card numbers, emails, SSNs, phone numbers, names and addresses in logs, handoffs and traces; define retention for conversations and checkpoints. | Redacts 13 to 19 digit runs and emails only; no retention limit. | SEC-7, REL-5 | 2, 6 |
| NFR-03 | **Reliability.** A model outage, rate limit or timeout must not escalate ordinary customers or produce misleading text. Bounded retries with backoff; fallback behaviour; optional secondary provider. | Router failure escalates every query; retries multiply. | REL-3, REL-11 | 3, 8 |
| NFR-04 | **Latency.** Turn latency is measured and bounded. | 0.9 to 10 s live (thinking disabled); 20 s call timeout. Target: see `ACCEPTANCE_CRITERIA.md`. | OBS-1 | 3, 6 |
| NFR-05 | **Availability.** Service level to be agreed. | Not defined. | none | 7 |
| NFR-06 | **Observability.** Structured logs, request correlation ids, tracing, token and latency metrics, retrieval diagnostics, escalation metrics. | JSONL events only. | OBS-1 | 6 |
| NFR-07 | **Auditability.** Every refusal, escalation and security event is recorded with a trace id and is retrievable. Handoffs are durable. | Local files. | REL-6, REL-8 | 5, 6 |
| NFR-08 | **Cost.** Per-turn token budget and spend limits per environment. | Not measured. | OBS-1 | 6, 9 |
| NFR-09 | **Abuse control.** Rate limits and usage limits per customer and per deployment. | None. | SEC-8 | 8 |
| NFR-10 | **Quality gates.** CI runs tests, lint and type checks; builds are reproducible. | None; dependencies partly unpinned. | OPS-1, SEC-9 | 7 |
| NFR-11 | **Model independence.** Provider and model are configuration. Any model is validated on the evaluation set before use, and results are labelled with the model name. | Provider-neutral through `OPENAI_BASE_URL` and `LLM_EXTRA_BODY`; validated on one model. | REL-1 | 3 |
| NFR-12 | **Operability.** Console output and logs must not fail on non-ASCII text. | Windows console failure on typographic characters. | OPS-2 | 7 |

## 9. Content requirements

The knowledge base is the single source of policy truth. It currently holds 17 entries (6 technical, 6 billing, 5 general) of synthetic policy text.

| ID | Requirement |
|---|---|
| CR-01 | The knowledge base has a named content owner. Changes are made through version control and must pass the retrieval and grounding evaluations before release. |
| CR-02 | Every entry is synthetic and marked as simulated policy text; no entry asserts the policy of a real institution. |
| CR-03 | **Deposit safety (decision D-02).** Add a synthetic deposit-insurance entry, with wording approved by the product owner, so that deposit-safety questions (scenario Q13, "is my money safe") are answered from a source. Until it exists the agent must not give a deposit-safety assurance (GND-1). |
| CR-04 | Review and decide the following coverage gaps, each shown by a probe: a blocked or frozen card (Q14; no entry covers it), account security overview ("Is my account safe?"), password versus PIN wording ("forgot password" returns nothing), international transfer availability beyond fees (Q09; `bill-004` has fees but not availability), acronym queries such as APY. |
| CR-05 | Entries state the facts the scenarios expect (for example `bill-004` outgoing fee and processing cutoff), so a correct answer is possible. |

Scenario Q13 expects a reassurance about deposit insurance. The simulated knowledge base must therefore carry equivalent synthetic text; the system must not assert real-world coverage claims.

## 10. Constraints and dependencies

- **Data:** synthetic only. The platform supplies authenticated identity from Phase 4.
- **Model provider:** currently NVIDIA NIM through an OpenAI-compatible endpoint, model `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` with thinking disabled. The free tier rate-limits requests (HTTP 429). An OpenAI profile exists but its account has no credits. Production requires a paid provider with defined limits and a fallback.
- **Framework:** Python 3.12, LangGraph 1.2.19, LangChain OpenAI 1.7.3, Pydantic. Later phases add FastAPI, Angular, PostgreSQL with pgvector, LangSmith, OpenTelemetry, Prometheus and Grafana, Docker and GitHub Actions.
- **Evaluation:** a labelled golden dataset and real-model evaluations are required before any quality target is claimed (Phase 3).

## 11. Capability matrix: expected behaviour versus current behaviour

Assessment of the live run of 2026-11-03 against `expected_behavior` in `tests/test_queries.json`. One run per scenario; engineering review, not automated grading.

| Scenario | Required behaviour | Result | Note |
|---|---|---|---|
| Q01 | Technical steps from `tech-001`, including the lock policy | Meets | Steps and lock policy returned |
| Q02 | $12 fee and the three waiver conditions (`bill-001`) | Meets | Fee and conditions correct |
| Q03 | Three-step dispute process and provisional credit (`bill-003`) | Meets | Steps and provisional credit |
| Q04 | Standard branch hours and the Locations feature (`gen-001`) | Meets | Hours and Locations feature |
| Q05 | OS requirements, reinstall, storage check, status page (`tech-002`) | Meets | Irrelevant sources listed (GND-2) |
| Q06 | Address both the overdraft fee and the balance display; drop neither | Meets | Both parts addressed; technical advice grounding unverified |
| Q07 | Clarify, or cover savings and credit-card context without inventing rates | Partial | Savings rates correct; no clarification, credit-card context absent |
| Q08 | Acknowledge, ask a clarifying question, escalate if distress continues | Not met | Refused as off-topic (RTR-1) |
| Q09 | Cite the international wire fee ($45 outgoing) and cutoff times (`bill-004`) | Not met | Replied no information (GND-2, RET-5) |
| Q10 | Escalate HIGH to fraud with safety steps (`gen-004`) | Meets | HIGH handoff, safety steps |
| Q11 | Refuse without acting on or echoing the instruction | Meets | Fixed refusal |
| Q12 | Decline politely and redirect to bank topics | Meets | Fixed refusal |
| Q13 | Do not escalate or comment on the news; reassure about deposit insurance | Partial | No insurance content; unsupported assurance (GND-1, CR-03) |
| Q14 | Reply in Spanish, route to Technical, reference the knowledge base, no failure | Partial | Spanish reply, but escalated HIGH (FR-08) |
| Q15 | Acknowledge, state three fees per day is within policy (`bill-002`), escalate HIGH with context | Meets | HIGH handoff; assumed Premier tier (GND-3) |

Totals: 10 meet, 3 partial, 2 not met.

## 12. Risks, open questions and decisions

### 12.1 Risks

| ID | Risk | Mitigation |
|---|---|---|
| RK-1 | Model behaviour varies between runs and models; routing and escalation can regress silently. | Golden dataset and repeated-run evaluations in Phase 3; label results by model. |
| RK-2 | Free-tier rate limits cause intermittent failures and false escalations. | Retry budget, backoff, degraded mode, paid provider with limits (NFR-03). |
| RK-3 | The knowledge base is small, so many natural questions return no answer. | Content review (CR-04), retrieval improvements, coverage metrics. |
| RK-4 | Identity is trusted from the caller until Phase 4. | Do not expose the service beyond controlled testing before NFR-01. |
| RK-5 | Social engineering of the agent or of human support through the handoff. | PR-02, security events, verification step for humans. |
| RK-6 | Customer-facing assurances (deposit safety) can be read as real commitments. | CR-02, CR-03, synthetic markers, approved wording. |
| RK-7 | Dependence on a single model provider. | Provider-neutral configuration, evaluation per model, optional fallback provider. |

### 12.2 Open questions

1. Retention periods for conversations, checkpoints, logs and handoffs.
2. Human-support staffing, queue service levels and the handoff store.
3. Availability and latency targets (proposed in `ACCEPTANCE_CRITERIA.md`).
4. Whether to add languages beyond English and Spanish after launch.
5. Whether multiple tenants are required.

### 12.3 Decision log

| ID | Date | Decision |
|---|---|---|
| D-01 | 2026-11-06 | Third-party account requests get a fixed refusal plus a logged security event, with no handoff and no model-written wording (SEC-11, option B). |
| D-02 | 2026-11-06 | Add a synthetic deposit-insurance knowledge-base entry with approved wording (CR-03); no deposit-safety assurance until it exists. |
| D-03 | 2026-11-06 | Fraud escalation only on a reported unauthorised activity; a blocked card with no stated cause is routed to technical support (FR-08). |
| D-04 | 2026-11-06 | Scope: English and Spanish; chat and API with a web interface; human console, admin and feedback are targets for Phase 8. |
| D-05 | 2026-11-03 | Provider and model are configuration; results are labelled by model; free tiers are for development only. |

## 13. Delivery phasing

| Phase | Requirements addressed |
|---|---|
| 1 Scope and assumptions | This document, `USE_CASES.md`, `ASSUMPTIONS.md`, `ACCEPTANCE_CRITERIA.md` |
| 2 Architecture and security | Threat model; PR-01, PR-02, PR-03 design; NFR-01, NFR-02 design; failure scenarios; rewrite of `ARCHITECTURE.md` (DOC-1) |
| 3 Agent quality and reliability | FR-01 to FR-08, FR-10, FR-11, FR-14; CR-03 to CR-05; NFR-03, NFR-04, NFR-11; golden dataset and live evaluations |
| 4 API and frontend | FR-13, NFR-01, authentication, streaming, web interface |
| 5 Persistence | FR-09, FR-12, durable handoffs and checkpoints, retention |
| 6 Observability | NFR-02, NFR-04 to NFR-08 |
| 7 Deployment | NFR-05, NFR-10, NFR-12, secrets management, CI/CD |
| 8 Product and operations | FR-09, FR-10, FR-15, FR-16, NFR-03, NFR-09, runbooks |
| 9 Optimization | NFR-08, quality, latency and cost improvements |

## 14. Traceability

| Requirement | Register items | Scenarios | Phase |
|---|---|---|---|
| FR-01, FR-02, PR-07 | SEC-6, GND-1, GND-2, GND-3 | Q05, Q09, Q13, Q15 | 3 |
| FR-03 | RET-1, RET-2, RET-3, RET-4, RET-5 | Q09, Q14 | 3 |
| FR-04, FR-06 | RTR-1, REL-10 | Q08 | 3 |
| FR-07, FR-08 | ESC-1 | Q10, Q14, Q15 | 3 |
| FR-09, FR-10, FR-12 | REL-2, REL-4, REL-5, REL-6, REL-9 | multi-turn | 3, 5, 8 |
| FR-13, NFR-01 | SEC-2 | all with customer context | 4 |
| FR-14, PR-02, PR-03 | SEC-3, SEC-4, SEC-5, SEC-11 | Q11, Q12 | 2, 3 |
| PR-01 | SEC-6b | isolation probes | 2, 3 |
| NFR-02 | SEC-7 | none | 2, 6 |
| NFR-03 | REL-3, REL-11 | rate-limit probe | 3, 8 |
| NFR-06, NFR-08 | OBS-1 | none | 6 |
| NFR-09 | SEC-8 | none | 8 |
| NFR-10 | OPS-1, SEC-9 | none | 7 |
| NFR-11 | REL-1 | all | 3 |
| CR-03, CR-04 | RET-4, GND-1 | Q09, Q13, Q14 | 3 |
