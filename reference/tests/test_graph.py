import contextlib
import io
import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage

import run_tests
from fakes import AgentTestCase, R, load_queries


class ScenarioQueriesTest(AgentTestCase):
    """All 15 regression queries through the real graph, policy, tools and guards (router and writer model faked)."""

    def setUp(self):
        super().setUp()
        self.out = {q["id"]: self.run_query(q["query"]) for q in load_queries()}

    def resp(self, qid):
        return self.out[qid]["response"]

    def path(self, qid):
        return self.out[qid]["trace"]

    def test_every_query_gets_a_non_empty_string_answer(self):
        self.assertEqual(len(self.out), 15)
        for qid, state in self.out.items():
            self.assertIsInstance(state["response"], str, qid)
            self.assertTrue(state["response"].strip(), qid)
            self.assertNotIn("error", state, qid)

    def test_standard_queries_route_to_the_specialist_and_cite_the_kb(self):
        for qid, specialist, kb_id in [("Q01", "technical", "tech-001"), ("Q02", "billing", "bill-001"),
                                       ("Q03", "billing", "bill-003"), ("Q04", "general", "gen-001"),
                                       ("Q05", "technical", "tech-002")]:
            with self.subTest(qid):
                self.assertIn(specialist, self.path(qid))
                self.assertIn(kb_id, self.resp(qid))
                self.assertIsNone(self.out[qid].get("handoff"))

    def test_fee_answer_comes_from_the_kb_not_the_model(self):
        self.assertIn("$12/month", self.resp("Q02"))
        self.assertIn("$1,500", self.resp("Q02"))

    def test_multi_topic_query_answers_both_parts(self):  # Q06
        self.assertEqual([p for p in self.path("Q06") if p in ("billing", "technical")], ["billing", "technical"])
        self.assertIn("Billing:", self.resp("Q06"))
        self.assertIn("Technical:", self.resp("Q06"))
        self.assertIn("bill-002", self.resp("Q06"))

    def test_ambiguous_rates_query_covers_both_readings(self):  # Q07
        self.assertIn("bill-005", self.resp("Q07"))
        self.assertIn("bill-006", self.resp("Q07"))
        self.assertIn("4.35%", self.resp("Q07"))

    def test_frustration_without_an_issue_asks_a_question_and_does_not_escalate(self):  # Q08
        self.assertIn("running into", self.resp("Q08"))
        self.assertIn("sorry", self.resp("Q08"))
        self.assertIsNone(self.out["Q08"].get("handoff"))
        self.assertEqual(self.out["Q08"]["unresolved_turns"], 1)

    def test_international_transfer_finds_wire_fees_across_categories(self):  # Q09
        self.assertIn("general", self.path("Q09"))
        self.assertIn("bill-004", self.resp("Q09"))
        self.assertIn("$45", self.resp("Q09"))

    def test_fraud_escalates_high_with_structured_handoff_and_safety_steps(self):  # Q10
        h = self.out["Q10"]["handoff"]
        self.assertEqual((h["priority"], h["reason"], h["recommended_queue"]), ("HIGH", "ACTIVE_FRAUD", "fraud_ops"))
        for key in ("handoff_id", "priority_score", "priority_factors", "conversation", "attempted_resolution", "trace_id"):
            self.assertIn(key, h)
        self.assertIn("gen-004", self.resp("Q10"))
        self.assertIn("1-800-555-0142", self.resp("Q10"))
        self.assertIn(f"[Handoff {h['handoff_id']} | Priority HIGH", self.resp("Q10"))
        self.assertEqual(self.log_events("handoffs.jsonl")[0]["handoff_id"], h["handoff_id"])

    def test_prompt_injection_is_refused_without_model_or_specialist(self):  # Q11
        self.assertEqual(self.path("Q11"), ["intake", "router", "policy", "refuse", "finalize"])
        self.assertNotIn("Ignore your previous instructions", self.resp("Q11"))
        self.assertIn("can't help with that", self.resp("Q11"))
        self.assertFalse(any("Ignore your previous" in r for r in self.model.routed))
        self.assertEqual(self.out["Q11"]["injection_flags"], 1)
        self.assertEqual(self.out["Q11"]["messages"][0].content, "[message removed by policy]")
        security = [e for e in self.log_events() if e["event"] == "security_event"]
        self.assertEqual(len(security), 1)
        self.assertTrue(security[0]["excerpt"])

    def test_out_of_scope_is_declined_politely(self):  # Q12
        self.assertEqual(self.path("Q12"), ["intake", "router", "policy", "refuse", "finalize"])
        self.assertIn("customer support topics", self.resp("Q12"))
        self.assertEqual(self.out["Q12"].get("injection_flags", 0), 0)

    def test_bank_robbery_worry_is_answered_not_escalated(self):  # Q13
        self.assertIn("general", self.path("Q13"))
        self.assertIsNone(self.out["Q13"].get("handoff"))
        self.assertIn("don't have that information", self.resp("Q13"))  # KB has no deposit-insurance entry

    def test_spanish_query_is_answered_in_spanish_scaffolding_without_error(self):  # Q14
        self.assertEqual(self.out["Q14"]["route"]["language"], "es")
        self.assertIn("Fuentes:", self.resp("Q14"))

    def test_furious_manager_demand_escalates_high_after_citing_overdraft_policy(self):  # Q15
        h = self.out["Q15"]["handoff"]
        self.assertEqual((h["priority"], h["reason"], h["secondary_reasons"]), ("HIGH", "EXPLICIT_HUMAN_REQUEST", ["EMOTIONAL_DISTRESS"]))
        self.assertIn("bill-002", self.resp("Q15"))
        self.assertIn("$105", self.resp("Q15"))
        self.assertIsNone(h["customer"])  # the harness supplies no customer id
        self.assertEqual(h["relevant_transactions"], [])


class CustomerContextTest(AgentTestCase):
    def test_handoff_carries_verified_customer_context(self):
        q = next(q["query"] for q in load_queries() if q["id"] == "Q15")
        h = self.run_query(q, customer_id="CST-1002")["handoff"]
        self.assertEqual(h["customer"]["customer_id"], "CST-1002")
        self.assertTrue(h["customer"]["identity_verified"])
        self.assertIn({"factor": "OPEN_TICKET", "points": 10}, h["priority_factors"])
        self.assertEqual(h["relevant_transactions"][0]["description"], "Overdraft fee")

    def test_specialist_can_fetch_context_through_the_tool_but_only_for_its_session_customer(self):
        seen = []

        def answer(messages, tools_bound):
            if tools_bound and not any(m.type == "tool" for m in messages):
                call = {"name": "get_customer_context", "id": "c1", "type": "tool_call",
                        "args": {"focus": "billing", "customer_id": "CST-1001"}}  # injected id must be ignored
                return AIMessage(content="", tool_calls=[call])
            seen.append([m.content for m in messages if m.type == "tool"])
            return AIMessage("You were charged an overdraft fee of $35.00.")

        self.model.answer_fn = answer
        q = next(q["query"] for q in load_queries() if q["id"] == "Q03")
        state = self.run_query(q, customer_id="CST-1002")
        self.assertIn("CST-1002", seen[0][0])
        self.assertNotIn("CST-1001", seen[0][0])
        self.assertIn("overdraft fee of $35.00", state["response"])


class MultiTurnTest(AgentTestCase):
    VAGUE = "I'm really frustrated. Nothing is working and I've been a customer for years."

    def test_vague_distress_escalates_on_the_second_unresolved_turn_and_only_once(self):
        t = "thread-1"
        first = self.run_query(self.VAGUE, thread_id=t)
        self.assertIsNone(first.get("handoff"))
        second = self.run_query(self.VAGUE, thread_id=t)
        h = second["handoff"]
        self.assertEqual((h["reason"], h["priority"]), ("REPEATED_UNRESOLVED", "MEDIUM"))
        self.assertEqual(h["conversation"]["turn_count"], 2)
        third = self.run_query(self.VAGUE, thread_id=t)
        self.assertEqual(third["handoff"]["handoff_id"], h["handoff_id"])  # no duplicate
        self.assertIn(h["handoff_id"], third["response"])
        self.assertNotIn("[Handoff", third["response"])
        self.assertEqual(len(self.log_events("handoffs.jsonl")), 1)

    def test_pending_clarification_is_given_to_the_router_on_the_next_turn(self):
        t = "thread-2"
        self.run_query(self.VAGUE, thread_id=t)
        self.assertNotIn("previously asked", self.model.routed[0])
        self.model.route_fn = lambda text: R(("technical", "mobile app problem"))
        self.run_query("It's the mobile app", thread_id=t)
        self.assertIn("previously asked the customer", self.model.routed[1])
        self.assertIn("Could you tell me what problem you're running into?", self.model.routed[1])

    def test_answered_turn_resets_the_unresolved_counter(self):
        t = "thread-3"
        self.run_query(self.VAGUE, thread_id=t)
        self.model.route_fn = lambda text: R(("technical", "cannot log into the mobile app, PIN incorrect"))
        state = self.run_query("I can't log in", thread_id=t)
        self.assertEqual((state["unresolved_turns"], state["awaiting_clarification"], state["turn_count"]), (0, None, 2))

    def test_threads_are_isolated(self):
        self.run_query(self.VAGUE, thread_id="a")
        other = self.run_query(self.VAGUE, thread_id="b")
        self.assertEqual(other["turn_count"], 1)
        self.assertIsNone(other.get("handoff"))


class FailureModesTest(AgentTestCase):
    def test_router_failure_fails_closed_to_a_human_without_calling_the_writer_model(self):
        def boom(text):
            raise RuntimeError("provider down")

        self.model.route_fn = boom
        state = self.run_query("What are your branch hours?")
        h = state["handoff"]
        self.assertEqual((h["reason"], h["priority"], h["priority_score"]), ("SYSTEM_FAILURE", "MEDIUM", 30))
        self.assertIn("[Handoff", state["response"])
        self.assertEqual(self.model.answered, [])
        self.assertEqual(len(self.model.routed), 2)  # tried twice

    def test_specialist_model_outage_degrades_to_the_knowledge_base_text(self):
        def down(messages, tools_bound):
            raise RuntimeError("provider down")

        self.model.answer_fn = down
        q = next(q["query"] for q in load_queries() if q["id"] == "Q04")
        state = self.run_query(q)
        self.assertIn("142 branches", state["response"])
        self.assertIn("gen-001", state["response"])

    def test_invented_numbers_are_replaced_by_the_grounded_kb_text(self):
        self.model.answer_fn = lambda m, t: AIMessage("The classic fee is $99/month.")
        q = next(q["query"] for q in load_queries() if q["id"] == "Q02")
        state = self.run_query(q)
        self.assertNotIn("$99", state["response"])
        self.assertIn("$12/month", state["response"])
        self.assertTrue(any(e["event"] == "output_guard" for e in self.log_events()))

    def test_other_customers_data_never_leaves_the_graph(self):
        self.model.answer_fn = lambda m, t: AIMessage("Sarah Mitchell (CST-1001) also has this issue.")
        q = next(q["query"] for q in load_queries() if q["id"] == "Q04")
        state = self.run_query(q, customer_id="CST-1002")
        self.assertNotIn("Sarah", state["response"])
        self.assertIn("couldn't complete", state["response"])

    def test_unknown_kb_topic_says_so_instead_of_guessing(self):
        self.model.route_fn = lambda text: R(("billing", "mortgage refinance calculator"))
        state = self.run_query("Can you calculate my mortgage refinance?")
        self.assertIn("don't have that information", state["response"])
        self.assertNotIn("Sources", state["response"])
        self.assertEqual(state["unresolved_turns"], 1)

    def test_tool_loop_is_bounded(self):
        calls = {"n": 0}

        def forever(messages, tools_bound):
            calls["n"] += 1
            if tools_bound:
                return AIMessage(content="", tool_calls=[{"name": "search_knowledge_base", "id": f"c{calls['n']}",
                                                         "type": "tool_call", "args": {"query": "branch hours"}}])
            return AIMessage("Branches open 9 to 5.")

        self.model.answer_fn = forever
        q = next(q["query"] for q in load_queries() if q["id"] == "Q04")
        state = self.run_query(q)
        self.assertEqual(calls["n"], 4)  # 3 tool rounds, then one forced final answer
        self.assertIn("Branches open", state["response"])

    def test_unknown_tool_call_is_survivable(self):
        def odd(messages, tools_bound):
            if tools_bound and not any(m.type == "tool" for m in messages):
                return AIMessage(content="", tool_calls=[{"name": "delete_everything", "id": "x", "type": "tool_call", "args": {}}])
            return AIMessage("Branches are open 9 to 5.")

        self.model.answer_fn = odd
        q = next(q["query"] for q in load_queries() if q["id"] == "Q04")
        self.assertIn("Branches are open", self.run_query(q)["response"])

    def test_run_agent_never_raises_even_if_the_graph_blows_up(self):
        from agent import run_agent
        with patch("agent.graph.get_graph", side_effect=RuntimeError("boom")):
            out = run_agent("hello")
        self.assertIn("couldn't complete", out)

    def test_empty_and_oversized_input(self):
        self.assertIn("what you need help with", self.run_query("   ")["response"])
        self.model.route_fn = lambda text: R(("general", "branch hours"))
        state = self.run_query("branch hours " + "x" * 10_000)
        self.assertLessEqual(len(state["query"]), 2000)


class HarnessIntegrationTest(AgentTestCase):
    def test_existing_harness_runs_all_queries_through_run_agent(self):
        import agent
        self.assertIs(run_tests.run_agent, agent.run_agent)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_tests.run_tests(run_tests.run_agent, load_queries())
        out = buf.getvalue()
        self.assertIn("OK      : 15", out)
        self.assertIn("Errors  : 0", out)


if __name__ == "__main__":
    unittest.main()
