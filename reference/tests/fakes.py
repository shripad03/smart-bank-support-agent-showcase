"""Offline stand-in for the chat model. Duck-typed: only the three methods the agent calls."""
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from agent.schemas import Intent, RouteDecision

ROOT = Path(__file__).resolve().parent.parent
_USER = re.compile(r"<user_message>\n(.*?)\n</user_message>", re.S)
_ENTRY = re.compile(r'<kb_entry id="[^"]+" topic="[^"]*">(.*?)</kb_entry>', re.S)


def default_answer(messages, tools_bound):
    """Grounded by construction: repeats the retrieved knowledge base text."""
    entries = _ENTRY.findall(messages[1].content)
    if "escalation specialist" in messages[0].content:
        return AIMessage("I'm sorry about this; I'm passing your case to a member of our team. " + " ".join(entries[:1]))
    return AIMessage(" ".join(entries[:2]) if entries else "I don't have that information.")


class _Bound:
    def __init__(self, model):
        self.model = model

    def invoke(self, messages):
        self.model.answered.append(messages)
        return self.model.answer_fn(messages, True)


class FakeModel:
    def __init__(self, route_fn, answer_fn=default_answer):
        self.route_fn, self.answer_fn = route_fn, answer_fn
        self.routed: list[str] = []
        self.answered: list[list] = []

    def with_structured_output(self, schema, **kwargs):
        return RunnableLambda(self._route)

    def _route(self, messages):
        self.routed.append(messages[-1].content)
        text = _USER.search(messages[-1].content).group(1)
        return self.route_fn(text)

    def bind_tools(self, tools):
        return _Bound(self)

    def invoke(self, messages):
        self.answered.append(messages)
        return self.answer_fn(messages, False)


def R(*intents, **kw) -> RouteDecision:
    """R(("billing", "summary"), sentiment=2, signals=[...])"""
    return RouteDecision(intents=[Intent(category=c, summary=s) for c, s in intents], **kw)


# Router output for each regression query: what a competent router would return (tests the pipeline, not the LLM).
ROUTES = {
    "Q01": R(("technical", "cannot log into the mobile app, PIN incorrect")),
    "Q02": R(("billing", "monthly fee for a Classic Checking account")),
    "Q03": R(("billing", "how to dispute a charge on my account")),
    "Q04": R(("general", "branch hours")),
    "Q05": R(("technical", "mobile app keeps crashing when opening")),
    "Q06": R(("billing", "charged an overdraft fee although funds seemed sufficient"),
             ("technical", "app is not showing my correct balance"), sentiment=1),
    "Q07": R(("billing", "savings account interest rates"), ("billing", "credit card interest rates"),
             ambiguity="multiple_readings"),
    "Q08": RouteDecision(ambiguity="needs_clarification", sentiment=2,
                         clarifying_question="Could you tell me what problem you're running into?"),
    "Q09": R(("general", "send money to someone in Japan international transfer")),
    "Q10": R(("general", "report unauthorized use of my card"), signals=["active_fraud"], sentiment=1),
    "Q11": RouteDecision(scope="injection"),
    "Q12": RouteDecision(scope="out_of_scope"),
    "Q13": R(("general", "is my money safe after bank robbery deposits insured")),
    "Q14": R(("technical", "customer's card was blocked and does not know why"), language="es", sentiment=1),
    "Q15": R(("billing", "charged three overdraft fees in one day"), signals=["explicit_human_request"], sentiment=2),
}


def load_queries() -> list[dict]:
    return json.loads((ROOT / "tests" / "test_queries.json").read_text(encoding="utf-8"))["queries"]


def router_for_scenarios():
    by_query = {q["query"]: ROUTES[q["id"]] for q in load_queries()}
    return lambda text: by_query[text].model_copy(deep=True)


class AgentTestCase(unittest.TestCase):
    """Isolated env (dummy key, temp log dir) and a patched model: no network, no real logs."""

    route_fn = staticmethod(router_for_scenarios())
    answer_fn = staticmethod(default_answer)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.log_dir = Path(tmp.name)
        env = patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "LOG_DIR": str(self.log_dir)})
        env.start()
        self.addCleanup(env.stop)
        self.model = FakeModel(self.route_fn, self.answer_fn)
        patched = patch("agent.llm.get_llm", return_value=self.model)
        patched.start()
        self.addCleanup(patched.stop)

    def run_query(self, query, **kw) -> dict:
        from agent import run_agent_detailed
        return run_agent_detailed(query, **kw)

    def log_events(self, name="agent.jsonl") -> list[dict]:
        path = self.log_dir / name
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
