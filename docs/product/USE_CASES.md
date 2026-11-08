# Smart Bank Customer Support Agent: Use Cases

## 1. Document control

| | |
|---|---|
| Version | 1.0 |
| Status | Approved by the product owner, 2026-11-08. Refusal wording for UC-15 awaits review (DQ-6 in `ACCEPTANCE_CRITERIA.md`). |
| Date | 2026-11-06 |
| Owner | Product and Engineering |
| Parent document | `product/PRD.md` v0.1 (requirements FR, PR, NFR, CR; decisions D-01 to D-05) |
| Evidence base | Live run of `run_tests.py` on 2026-11-03, offline tests (66 passing), probes recorded in `product/KNOWN_ISSUES.md` |

**Status labels.** *Supported today*: the behaviour exists and has been observed. *Partially supported*: it exists but fails or is unverified in a way that matters. *Target*: not built, or the current behaviour contradicts the requirement.

**Evidence tags.** [L] live run 2026-11-03, one run per scenario, not an evaluation. [O] offline scripted tests. [P] probe recorded in the register. [C] code inspection only.

## 2. Actors and common preconditions

| Actor | Role in the use cases |
|---|---|
| Customer | Authenticated retail customer writing in English or Spanish |
| Agent (the system) | Intake, router, policy, specialists, escalation handler |
| Human support agent, supervisor, fraud operations, compliance | Receive handoffs through the queues `tier2_support`, `customer_care_supervisor`, `fraud_ops`, `compliance` |
| Administrator | Maintains knowledge-base content and settings (target) |

Common preconditions for every use case: the customer has a conversation identified by a thread id; the customer's identity is supplied by the caller (current) or by authenticated context (target, NFR-01); the knowledge base and customer data load successfully at start-up.

## 3. Common behaviour (applies to every use case)

1. **Intake.** The message is normalised (Unicode NFKC, control characters and prompt delimiters removed, mojibake repaired, capped at 2,000 characters) and screened by the injection pattern check. [C]
2. **Routing.** One model call returns language, scope, up to three intents (category, English summary, confidence), ambiguity, sentiment and escalation signals. If it fails twice the case is escalated as `SYSTEM_FAILURE`. [C]
3. **Policy.** Deterministic code chooses refuse, clarify, escalate or answer, and computes the escalation score (threshold 30, HIGH at 60). [C]
4. **Answering.** For each actionable intent the specialist retrieves knowledge-base entries first, then writes the answer from them; dollar and percentage figures must appear in the sources, otherwise the answer is replaced by the knowledge-base text itself. [C, O]
5. **Composition.** Section headers appear only when different specialists contributed. A `Sources:` line lists the retrieved entry ids (GND-2). A handoff line `[Handoff <id> | Priority <level> | Reason: <label>]` is appended to a newly created handoff. [L]
6. **Output guard.** The final text is replaced by a fixed fallback if it contains the planted canary, another customer's id or another customer's full name. [C]
7. **Logging.** One `turn_end` event per turn records the trace id, outcome, path, sources and escalation score. [L]
8. **Failure.** The entry point never raises; an unhandled error returns the fixed fallback text. [C]

## 4. Catalogue

| ID | Use case | Scenarios | Status | PRD references |
|---|---|---|---|---|
| UC-01 | Technical support question | Q01, Q05 | Supported today | FR-01, FR-04 |
| UC-02 | Billing and fee question | Q02, Q03 | Supported today | FR-01, FR-04 |
| UC-03 | General bank question | Q04, Q09 | Partially supported | FR-01, FR-03 |
| UC-04 | Multi-topic question | Q06 | Supported today | FR-05 |
| UC-05 | Ambiguous question | Q07 | Partially supported | FR-05, FR-06 |
| UC-06 | Emotion with no question | Q08 | Partially supported | FR-06, FR-04 |
| UC-07 | Reported fraud or unauthorised activity | Q10 | Supported today | FR-07, FR-09 |
| UC-08 | Blocked or frozen card, cause unknown | Q14 | Partially supported | FR-08 |
| UC-09 | Explicit request for a person or severe distress | Q15 | Supported today | FR-07, FR-09 |
| UC-10 | Legal or regulatory threat | none | Partially supported | FR-07 |
| UC-11 | Follow-up on an open handoff | none | Partially supported | FR-10 |
| UC-12 | Question the knowledge base cannot answer | Q09, Q13 | Partially supported | FR-01, FR-02 |
| UC-13 | Prompt-injection attempt | Q11 | Partially supported | PR-03, FR-14 |
| UC-14 | Out-of-scope request | Q12 | Supported today | PR-06, FR-14 |
| UC-15 | Request for another person's account details | none | Target | PR-01, PR-02, D-01 |
| UC-16 | Spanish-language request | Q14 | Partially supported | FR-11 |
| UC-17 | Deposit-safety question | Q13 | Target | CR-03, D-02 |
| UC-18 | Conversation across several turns | none | Partially supported | FR-12 |
| UC-19 | Degraded operation (model unavailable or rate-limited) | none | Partially supported | NFR-03 |
| UC-20 | Human works a handoff | none | Target | FR-09, FR-15 |
| UC-21 | Customer gives feedback | none | Target | FR-16 |
| UC-22 | Administrator maintains knowledge base and settings | none | Target | CR-01, NFR-09 |

Totals: 6 supported today, 11 partially supported, 5 target.

## 5. Use cases

### UC-01 Technical support question
- **Actor:** Customer. **Status:** Supported today. [L] Q01 (3.8 s) and Q05 (4.6 s) returned the knowledge-base steps for `tech-001` and `tech-002`.
- **Trigger:** the customer reports a problem with the mobile app, login, PIN, two-factor codes, notifications, a card not shown in the app, or a failed scheduled transfer.
- **Main flow:** (1) common intake and routing, category technical; (2) policy decides answer; (3) the technical specialist retrieves entries and writes numbered steps from them; (4) post-check re-scores escalation; (5) the reply is composed with a sources line.
- **Alternate flows:** no matching entry gives UC-12; repeated unresolved turns escalate (UC-09 rules); customer context (open tickets) may be used to explain status.
- **Expected response:** concise, empathetic, numbered steps that appear in the knowledge base; no invented versions, limits or timings.
- **Escalation rule:** none unless the score reaches 30 (FR-07).
- **Data touched:** knowledge-base entries; the signed-in customer's open tickets and recent transactions (read-only); `agent.jsonl`.
- **Gaps:** sources line lists irrelevant entries for Q05 (GND-2); retrieval depends on the router's English summary (RET-5).

### UC-02 Billing and fee question
- **Actor:** Customer. **Status:** Supported today. [L] Q02 returned the $12 fee and the waiver conditions (`bill-001`); Q03 returned the dispute steps and provisional credit (`bill-003`).
- **Trigger:** the customer asks about fees, overdraft, disputes, wire fees, interest rates or late fees.
- **Main flow:** as UC-01 with the billing specialist; the specialist may read the customer's recent transactions to explain a charge.
- **Alternate flows:** no entry gives UC-12; an amount of 250 or more, or 1,000 or more, adds weight to an escalation that already exists; a request to dispute is explained, never filed (PR-04).
- **Expected response:** states the policy and how the customer acts on it; never promises a refund, waiver or credit that no entry states (PR-05).
- **Escalation rule:** FR-07; amount and open-ticket modifiers apply only when another reason exists.
- **Data touched:** knowledge-base entries; customer transactions and open tickets (read-only).
- **Gaps:** none beyond GND-2 and RET-5.

### UC-03 General bank question
- **Actor:** Customer. **Status:** Partially supported. [L] Q04 returned the hours and the Locations feature (`gen-001`); Q09 ("send money to Japan") replied that no information exists although `bill-004` holds the international wire fee and cutoff.
- **Trigger:** questions about branches, opening an account, Zelle and ACH transfers, loans, fraud-reporting information.
- **Main flow:** as UC-01 with the general specialist, which has no access to customer data.
- **Alternate flows:** a question that touches fees is answered from billing entries because retrieval is not limited by category.
- **Expected response:** the knowledge-base facts the scenario requires, for example the $45 outgoing international wire fee and processing cutoff for Q09.
- **Escalation rule:** FR-07.
- **Data touched:** knowledge-base entries only.
- **Gaps:** Q09 expectation not met (RET-5, GND-2); coverage of availability by country is absent (CR-04).

### UC-04 Multi-topic question
- **Actor:** Customer. **Status:** Supported today. [L] Q06 (10.0 s): the overdraft fee and the incorrect balance were both answered under Billing and Technical headers.
- **Trigger:** one message contains two or three questions.
- **Main flow:** the router returns up to three intents ordered by urgency (money problems before technical ones); the specialists run one after another; the sections are joined with headers when the categories differ.
- **Alternate flows:** two intents of the same category are answered without headers; more than three intents: the first three are answered.
- **Expected response:** no part is silently dropped; the most urgent part comes first.
- **Escalation rule:** scored once over the whole turn.
- **Data touched:** as the contributing specialists.
- **Gaps:** advice outside the retrieved text may appear in the technical section of Q06 (unverified).

### UC-05 Ambiguous question
- **Actor:** Customer. **Status:** Partially supported. [L] Q07 ("interest rates") returned savings, money-market and loan rates from the knowledge base; it neither asked which product nor covered credit-card context.
- **Trigger:** one message with two plausible readings.
- **Main flow:** the router marks multiple readings and lists each as an intent; the specialists cover both, or the agent asks one clarifying question.
- **Alternate flows:** the customer answers the clarification on the next turn (UC-18).
- **Expected response:** either a clarifying question or coverage of each reading; no rate that is not in the knowledge base.
- **Escalation rule:** none by itself.
- **Data touched:** knowledge-base entries.
- **Gaps:** the choice between clarifying and covering is not defined; to be set in acceptance criteria.

### UC-06 Emotion with no question
- **Actor:** Customer. **Status:** Partially supported. [O] the scripted tests clarify and escalate on the second turn. [L] Q08 was refused as off-topic; the router marked it out of scope in 18 of 20 calls (RTR-1).
- **Trigger:** the message expresses frustration but states no issue.
- **Main flow:** (1) router marks needs clarification; (2) policy chooses clarify; (3) the agent acknowledges the feeling and asks one question; (4) the question is remembered for the next turn.
- **Alternate flows:** the customer answers, then UC-01 to UC-03 apply; a second vague turn escalates as `REPEATED_UNRESOLVED` (score 30); stated distress adds 10 or 25.
- **Expected response:** an acknowledgement and a single clarifying question in the customer's language, never an out-of-scope refusal.
- **Escalation rule:** emotion alone never escalates; repeated unresolved turns do.
- **Data touched:** conversation state only.
- **Gaps:** RTR-1.

### UC-07 Reported fraud or unauthorised activity
- **Actor:** Customer. **Status:** Supported today. [L] Q10 (3.2 s): HIGH handoff with the freeze-card and hotline steps from `gen-004`.
- **Trigger:** the customer says unauthorised activity or compromise is happening to them now (not a question about how fraud reporting works).
- **Main flow:** (1) router sets the `active_fraud` signal; (2) the score is at least 70, so priority is HIGH; (3) the escalation handler looks up the fraud steps by reason code, not by model judgement; (4) the reply gives the safety steps and says a person will follow up; (5) the handoff is created for queue `fraud_ops` with recent transactions filtered to suspicious ones; (6) the handoff line is appended.
- **Alternate flows:** the model is unavailable: fixed acknowledgement plus the knowledge-base fraud text; a handoff already exists: UC-11.
- **Expected response:** empathy, immediate safety steps from the knowledge base, no promised outcome except what the entry states.
- **Escalation rule:** always, priority HIGH.
- **Data touched:** fraud steps; customer context with fraud focus; `handoffs.jsonl`.
- **Gaps:** `identity_verified` is always true for a known id (SEC-2); the handoff is a local file (REL-6).

### UC-08 Blocked or frozen card, cause unknown
- **Actor:** Customer. **Status:** Partially supported. [L] Q14 (Spanish) returned a Spanish reply but escalated HIGH as possible unauthorised activity.
- **Trigger:** the customer says a card is blocked and does not know why.
- **Main flow (target, D-03):** (1) router routes to technical with no fraud signal; (2) the specialist answers from the knowledge base and offers to connect support; (3) no escalation.
- **Alternate flows:** the customer then states transactions they did not make: UC-07.
- **Expected response:** causes and next steps from the knowledge base, plus the offer; a fraud escalation only after a report of unauthorised activity.
- **Escalation rule:** none for a blocked card by itself.
- **Data touched:** knowledge-base entries; card status from customer context if added.
- **Gaps:** over-escalation (to be added to the register); no knowledge-base entry covers blocked cards (CR-04).

### UC-09 Explicit request for a person or severe distress
- **Actor:** Customer. **Status:** Supported today. [L] Q15 (2.9 s): HIGH handoff, reason "customer asked for a person", overdraft policy stated.
- **Trigger:** the customer asks for a manager or agent, or is angry or distressed about a concrete issue.
- **Main flow:** (1) router sets `explicit_human_request` and sentiment; (2) the score is 40 plus distress plus modifiers; (3) the policy escalates; (4) the handler acknowledges the feeling, states relevant policy from the knowledge base, and says the case is passed on; (5) the handoff goes to `customer_care_supervisor`.
- **Alternate flows:** a handoff exists: UC-11; the model is down: fixed acknowledgement.
- **Expected response:** empathetic, factual about policy, no promises.
- **Escalation rule:** at 30 or more; HIGH at 60 or more.
- **Data touched:** knowledge base; customer context (billing focus); `handoffs.jsonl`.
- **Gaps:** the reply assumed "your Premier account" without customer context (GND-3).

### UC-10 Legal or regulatory threat
- **Actor:** Customer. **Status:** Partially supported. [C] the signal weighs 60 (HIGH) and routes to queue `compliance`; no scenario or live run covers it.
- **Trigger:** the customer mentions a lawyer, lawsuit, regulator or formal complaint.
- **Main flow:** as UC-09 with reason `LEGAL_OR_REGULATORY_THREAT`.
- **Alternate flows:** as UC-09.
- **Expected response:** empathetic acknowledgement, no legal commentary (PR-06), case passed to compliance.
- **Escalation rule:** always, priority HIGH.
- **Data touched:** as UC-09.
- **Gaps:** needs a scenario in the golden dataset (Phase 3).

### UC-11 Follow-up on an open handoff
- **Actor:** Customer. **Status:** Partially supported. [P] a vague follow-up gets "Your request <id> is already with our team, and I've added your latest message to it", but the handoff record is unchanged (REL-2); an answerable follow-up is answered normally and not attached.
- **Trigger:** a message on a thread that has an open handoff.
- **Main flow (target, FR-10):** (1) the message is classified; (2) if it relates to the open case it is appended to the handoff and the customer is told so; (3) if it is a new question it is answered normally.
- **Alternate flows:** the case is closed by a human: the thread returns to normal behaviour.
- **Expected response:** never states an action that did not happen.
- **Escalation rule:** one open handoff per thread.
- **Data touched:** the handoff record; `handoffs.jsonl`.
- **Gaps:** REL-2, REL-9 (a handoff is never closed).

### UC-12 Question the knowledge base cannot answer
- **Actor:** Customer. **Status:** Partially supported. [L] Q09 and Q13 show the no-information path and its weaknesses.
- **Trigger:** retrieval returns nothing relevant.
- **Main flow:** (1) the specialist finds no entry; (2) the reply is the fixed text "I don't have that information in our knowledge base, so I can't confirm it. I can connect you with our support team if you'd like."; (3) post-check adds the knowledge-base gap weight (15); (4) two unresolved turns escalate.
- **Alternate flows:** entries are retrieved but do not answer: the model must say so and must not cite them as support.
- **Expected response:** a plain statement of what is not known; no guess; no source line that implies support.
- **Escalation rule:** KB_GAP 15 alone does not escalate.
- **Data touched:** knowledge base.
- **Gaps:** Q09 cites three sources while saying there is no information (GND-2); coverage gaps (CR-04).

### UC-13 Prompt-injection attempt
- **Actor:** Customer (or hostile text in data). **Status:** Partially supported. [L] Q11 was refused with no model call (0.9 s). [P] the pattern check misses paraphrased and obfuscated attempts and blocks one benign sentence (SEC-3).
- **Trigger:** the message tries to change the agent's role or rules, extract prompts, or reach other customers' data.
- **Main flow:** (1) the pattern check or the router's scope marks injection; (2) the reply is the fixed refusal; (3) the raw message is replaced in the stored conversation by "[message removed by policy]"; (4) a `security_event` is logged.
- **Alternate flows:** injection text inside transaction descriptions or knowledge-base text is treated as data (PR-03).
- **Expected response:** "I can't help with that request. I can help with questions about accounts, fees, cards, transfers and the mobile app." No echo of the instruction.
- **Escalation rule:** none.
- **Data touched:** none beyond the log.
- **Gaps:** SEC-3, SEC-4, SEC-5.

### UC-14 Out-of-scope request
- **Actor:** Customer. **Status:** Supported today. [L] Q12 received the fixed refusal and redirection (1.1 s).
- **Trigger:** the message is not about the bank's services (restaurants, trivia, news, general advice).
- **Main flow:** the router marks out of scope; the fixed text is returned: "I can only help with customer support topics such as accounts, fees, cards, transfers and the mobile app. Is there something along those lines I can help with?"
- **Alternate flows:** a legitimate bank concern that merely mentions a news event stays in scope (UC-17).
- **Expected response:** polite refusal and a redirect.
- **Escalation rule:** none.
- **Data touched:** none.
- **Gaps:** false refusals of in-scope messages (UC-06).

### UC-15 Request for another person's account details
- **Actor:** Customer signed in as one person, asking about another (relative, representative, anyone claiming authority). **Status:** Target. [P] 12 probes: no data leaked, but outcomes varied (generic no-information reply, model-written refusal, clarification, handoff) and no security event was logged (SEC-11).
- **Trigger:** the message asks for another person's balance, transactions, status or other account data, or names another customer id, with or without a claim of authority.
- **Main flow (target, D-01):** (1) the request is recognised before any specialist runs; (2) the reply is the **fixed refusal**; (3) a `security_event` is logged with trace id, thread id, signed-in customer id and a redacted excerpt; (4) **no handoff is created and no model-written text is shown**; (5) the conversation continues normally.
- **Fixed refusal, proposed wording for approval:**
  - English: "I can only discuss the account you are signed in to. For someone else's account, the account holder, or a legally authorised representative, needs to contact us directly."
  - Spanish: "Solo puedo hablar de la cuenta con la que ha iniciado sesión. Para la cuenta de otra persona, el titular, o un representante legalmente autorizado, debe comunicarse directamente con nosotros."
- **Alternate flows:** the customer mentions their own id: not a violation; repeated attempts on one thread are counted and visible in the log; the claimed relationship or urgency never changes the outcome.
- **Expected response:** the same text for every phrasing, no echo of the other customer's id, no confirmation that the other account exists.
- **Escalation rule:** none.
- **Data touched:** the log only; no customer data is read.
- **Gaps:** detection method is a Phase 2 design decision; acceptance requires zero leaks and the fixed refusal across the red-team set in Phase 3.

### UC-16 Spanish-language request
- **Actor:** Customer. **Status:** Partially supported. [L] Q14 was answered in Spanish with a Spanish source label. [P] raw Spanish text retrieves nothing; success depends on the router's English summary (RET-5).
- **Trigger:** the message is in Spanish.
- **Main flow:** the router detects the language and writes an English summary; retrieval uses the summary; the reply and fixed texts are Spanish.
- **Alternate flows:** another language gets an English fixed text and a model reply in that language (not supported by requirement).
- **Expected response:** Spanish throughout, including refusals, clarifications and handoff acknowledgements.
- **Escalation rule:** as the underlying use case.
- **Data touched:** as the underlying use case.
- **Gaps:** RET-5; over-escalation in Q14 (UC-08).

### UC-17 Deposit-safety question
- **Actor:** Customer. **Status:** Target. [L] Q13 returned "Your money is protected" with no supporting entry (GND-1).
- **Trigger:** the customer asks whether their money or account is safe, possibly after a news item.
- **Main flow (target, D-02):** (1) router keeps it in scope as a general question; (2) retrieval finds the synthetic deposit-insurance entry; (3) the reply states what that entry says and nothing more; (4) no fraud escalation and no comment on the news event.
- **Alternate flows:** until the entry exists the reply is the no-information text (UC-12) and must not offer an assurance.
- **Expected response:** a grounded reassurance, clearly synthetic policy text, no news commentary.
- **Escalation rule:** none, unless the customer also reports unauthorised activity.
- **Data touched:** the new knowledge-base entry (CR-03).
- **Gaps:** the entry and its approved wording do not exist yet.

### UC-18 Conversation across several turns
- **Actor:** Customer. **Status:** Partially supported. [O] multi-turn tests cover clarification memory, a single handoff per thread, counter reset and thread isolation.
- **Trigger:** more than one message on the same thread.
- **Main flow:** state persists per thread (turn count, unresolved count, open handoff, pending clarification); the router sees the last six messages; the pending question is passed to the router on the next turn.
- **Alternate flows:** a new thread starts fresh.
- **Expected response:** the agent does not ask again for what the customer already said.
- **Escalation rule:** repeated unresolved turns count across the thread.
- **Data touched:** conversation state (in memory).
- **Gaps:** state is lost on restart (REL-6), grows without bound (REL-5), and specialists see only the current message (REL-4).

### UC-19 Degraded operation
- **Actor:** Customer and operations. **Status:** Partially supported. [O] a failing specialist model returns the knowledge-base text directly. [P] a router that fails twice escalates the customer as `SYSTEM_FAILURE`; 4 of 80 calls failed this way under a rate limit.
- **Trigger:** the model is unavailable, times out or returns HTTP 429.
- **Main flow (target, NFR-03):** bounded retries with backoff; if the model is still unavailable, answer clearly matching knowledge-base entries directly, otherwise tell the customer plainly and offer support, without creating a handoff for every message.
- **Alternate flows:** fall back to a secondary provider if configured.
- **Expected response:** truthful, never an invented answer, never a handoff flood.
- **Escalation rule:** `SYSTEM_FAILURE` weighs 30 today; the target is to avoid escalating ordinary customers because of an outage.
- **Data touched:** logs and metrics.
- **Gaps:** REL-3, REL-11, OBS-1.

### UC-20 Human works a handoff
- **Actor:** Human support agent, supervisor, fraud operations, compliance. **Status:** Target (Phase 8).
- **Trigger:** a handoff arrives in a queue.
- **Main flow:** the agent opens the handoff, sees the reason, score factors, customer context, relevant transactions, attempted resolution and conversation excerpt, claims it, replies or resolves, and closes it; the customer sees the status.
- **Alternate flows:** reassign to another queue; add notes; reopen.
- **Expected response:** the customer's thread reflects the case state, and a closed case returns the thread to normal behaviour.
- **Escalation rule:** not applicable.
- **Data touched:** handoff store (Phase 5).
- **Gaps:** no console, no durable store, no queue.

### UC-21 Customer gives feedback
- **Actor:** Customer. **Status:** Target (Phase 8).
- **Trigger:** the customer rates a reply or reports a wrong answer.
- **Main flow:** the rating is stored with the trace id and used in evaluation and content review.
- **Alternate flows:** a negative rating on an answer lacking sources is queued for content review.
- **Expected response:** a brief acknowledgement.
- **Escalation rule:** none.
- **Data touched:** feedback store.
- **Gaps:** not built.

### UC-22 Administrator maintains knowledge base and settings
- **Actor:** Administrator. **Status:** Target (Phase 8).
- **Trigger:** policy changes, a coverage gap is found, or limits need adjusting.
- **Main flow:** the administrator changes an entry or a limit through version control or an admin interface; evaluations run before release; the change is audited.
- **Alternate flows:** roll back a release that lowers evaluation scores.
- **Expected response:** not customer-facing.
- **Escalation rule:** not applicable.
- **Data touched:** knowledge base, configuration, rate limits.
- **Gaps:** there is no admin interface; the knowledge base is a JSON file loaded at start-up (REL-6 caches).
