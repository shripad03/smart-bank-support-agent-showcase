# Reference material

Read-only reference for the Smart Bank Customer Support Agent. Nothing here is runnable on its own: the tests import the `agent` package, which is maintained in a private repository.

| Path | Purpose |
|---|---|
| `tests/test_queries.json` | The 15 regression scenarios (5 standard, 5 edge case, 5 adversarial) with expected category, expected behaviour and grader notes. |
| `tests/fakes.py` | Scripted stand-in for the chat model and the expected router output for each scenario. Defines what a perfect router would say. |
| `tests/test_phase1_config_kb.py` | Configuration, model factory and knowledge-base loader (14 tests). |
| `tests/test_tools_policy_guards.py` | Retrieval, tool schema and customer isolation, injection screen, escalation scoring, input and output guards (23 tests). |
| `tests/test_graph.py` | All 15 scenarios through the full graph, multi-turn behaviour and failure modes (29 tests). |
| `data/knowledge_base.json` | 17 synthetic knowledge-base entries (technical, billing, general). |
| `data/customer_profiles.json` | 10 synthetic customer profiles. |

The suite proves pipeline behaviour (routing wiring, policy arithmetic, guards, fallbacks, state across turns). It does not prove language-model quality; see [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) section 9.
