import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_openai import ChatOpenAI

from agent import config, kb, llm
from agent.config import ConfigError, load_settings


def env(**overrides):
    """Isolated environment: only these vars exist and the real .env is not read."""
    stack = [patch.dict(os.environ, overrides, clear=True), patch("agent.config.load_dotenv")]

    class _Both:
        def __enter__(self):
            for p in stack:
                p.start()

        def __exit__(self, *exc):
            for p in reversed(stack):
                p.stop()

    return _Both()


class SettingsTest(unittest.TestCase):
    def test_missing_or_blank_key_fails_fast(self):
        for overrides in ({}, {"OPENAI_API_KEY": "   "}):
            with env(**overrides), self.assertRaises(ConfigError):
                load_settings()

    def test_defaults(self):
        with env(OPENAI_API_KEY="sk-test", MODEL_NAME=""):
            s = load_settings()
        self.assertEqual(s.model_name, config.DEFAULT_MODEL)
        self.assertEqual(s.knowledge_base_path, config.ROOT / "data" / "knowledge_base.json")

    def test_env_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            kb_path = str(Path(d) / "kb.json")
            with env(OPENAI_API_KEY="sk-test", MODEL_NAME="gpt-x", KNOWLEDGE_BASE_PATH=kb_path):
                s = load_settings()
        self.assertEqual(s.model_name, "gpt-x")
        self.assertEqual(s.knowledge_base_path, Path(kb_path))

    def test_relative_path_does_not_depend_on_cwd(self):
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        with tempfile.TemporaryDirectory() as d, env(OPENAI_API_KEY="sk-test"):
            os.chdir(d)
            s = load_settings()
            os.chdir(cwd)  # leave the temp dir before it is deleted (Windows)
        self.assertEqual(s.knowledge_base_path, config.ROOT / "data" / "knowledge_base.json")

    def test_secret_not_in_repr(self):
        with env(OPENAI_API_KEY="sk-very-secret"):
            self.assertNotIn("sk-very-secret", repr(load_settings()))

    def test_llm_extra_body_defaults_to_empty_and_parses_json_object(self):
        with env(OPENAI_API_KEY="sk-test"):
            self.assertEqual(load_settings().llm_extra_body, {})
        body = {"chat_template_kwargs": {"enable_thinking": False}}
        with env(OPENAI_API_KEY="sk-test", LLM_EXTRA_BODY=json.dumps(body)):
            self.assertEqual(load_settings().llm_extra_body, body)

    def test_invalid_llm_extra_body_fails_fast_without_echoing_the_value(self):
        for bad in ("{not json", "[1, 2]", '"text"'):
            with env(OPENAI_API_KEY="sk-test", LLM_EXTRA_BODY=bad), self.assertRaises(ConfigError) as ctx:
                load_settings()
            self.assertNotIn(bad, str(ctx.exception))


class LLMTest(unittest.TestCase):
    def setUp(self):
        llm.get_llm.cache_clear()
        self.addCleanup(llm.get_llm.cache_clear)

    def test_built_from_settings_and_cached(self):
        with env(OPENAI_API_KEY="sk-test", MODEL_NAME="gpt-x"):
            model = llm.get_llm()
            self.assertIs(model, llm.get_llm())
        self.assertIsInstance(model, ChatOpenAI)
        self.assertEqual(model.model_name, "gpt-x")
        self.assertEqual(model.temperature, 0)
        self.assertEqual(model.max_retries, 2)
        self.assertIsNone(model.extra_body)  # nothing provider-specific unless configured

    def test_extra_body_is_passed_to_the_client(self):
        body = {"chat_template_kwargs": {"enable_thinking": False}}
        with env(OPENAI_API_KEY="sk-test", LLM_EXTRA_BODY=json.dumps(body)):
            model = llm.get_llm()
        self.assertEqual(model.extra_body, body)

    def test_missing_key_fails_fast(self):
        with env(), self.assertRaises(ConfigError):
            llm.get_llm()


class KnowledgeBaseTest(unittest.TestCase):
    def setUp(self):
        kb.get_knowledge_base.cache_clear()
        self.addCleanup(kb.get_knowledge_base.cache_clear)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def write(self, data) -> Path:
        path = self.tmp / "kb.json"
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return path

    def test_real_knowledge_base_loads_completely(self):
        path = config.ROOT / "data" / "knowledge_base.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries = kb.load_knowledge_base(path)
        self.assertEqual(len(entries), sum(len(v) for v in raw.values()))
        by_id = {e.id: e for e in entries}
        self.assertEqual(len(by_id), len(entries))
        # Category comes from the file's top-level key.
        for category, items in raw.items():
            for item in items:
                self.assertEqual(by_id[item["id"]].category, category)
                self.assertEqual(by_id[item["id"]].content, item["content"])

    def test_invalid_files_are_rejected(self):
        ok = {"id": "a-1", "topic": "T", "content": "C"}
        cases = {
            "duplicate id": {"technical": [ok], "billing": [ok]},
            "unknown category": {"sports": [ok]},
            "missing field": {"technical": [{"id": "a-1", "topic": "T"}]},
            "empty content": {"technical": [{**ok, "content": ""}]},
            "extra field": {"technical": [{**ok, "extra": 1}]},
            "no entries": {"technical": []},
            "wrong shape": ["not", "a", "dict"],
            "malformed json": "{not json",
        }
        for name, data in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                kb.load_knowledge_base(self.write(data))

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            kb.load_knowledge_base(self.tmp / "nope.json")

    def test_get_knowledge_base_uses_configured_path_and_caches(self):
        path = self.write({"general": [{"id": "g-1", "topic": "T", "content": "C"}]})
        with env(OPENAI_API_KEY="sk-test", KNOWLEDGE_BASE_PATH=str(path)):
            entries = kb.get_knowledge_base()
            self.assertIs(entries, kb.get_knowledge_base())
        self.assertEqual([e.id for e in entries], ["g-1"])


if __name__ == "__main__":
    unittest.main()
