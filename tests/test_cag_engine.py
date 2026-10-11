import unittest
import time
from src.cag_engine import CAGCacheEngine, DocumentItem
from src.rag_engine import VectorRAGEngine
from src.config import load_settings

class TestCAGDeveloperAssistant(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings()
        self.cag = CAGCacheEngine(default_ttl=10)
        self.sample_docs = [
            DocumentItem(
                path="src/auth/jwt.py",
                content="def generate_token(user_id: str) -> str:\n    return f'token-{user_id}'\n\ndef verify_token(token: str) -> bool:\n    return token.startswith('token-')\n"
            ),
            DocumentItem(
                path="docs/api_reference.md",
                content="# API Reference\nEndpoint `/api/v1/auth/login` requires username and password.\nReturns JWT Bearer.\n"
            ),
            DocumentItem(
                path="src/payments/stripe.py",
                content="class StripeWebhookHandler:\n    def handle_charge_succeeded(self, event):\n        return {'status': 'processed'}\n"
            )
        ]

    def test_cache_warming_creates_active_session(self):
        session = self.cag.warm_cache("test-repo", self.sample_docs, ttl_seconds=60)
        self.assertIsNotNone(session.cache_id)
        self.assertTrue(session.cache_id.startswith("cag-ctx-"))
        self.assertEqual(session.repo_id, "test-repo")
        self.assertGreater(session.token_count, 10)
        self.assertEqual(session.documents_count, 3)

    def test_cache_hit_query_execution(self):
        session = self.cag.warm_cache("test-repo", self.sample_docs)
        result = self.cag.execute_query(session.cache_id, "How is JWT token verified?")
        
        self.assertTrue(result["cache_hit"])
        self.assertGreater(result["tokens_cached"], 0)
        self.assertEqual(result["cost_savings_pct"], 75.0)
        self.assertLess(result["latency_ms"], 250.0)

    def test_cache_miss_fallback(self):
        result = self.cag.execute_query("non-existent-cache-id", "Explain payment webhook")
        self.assertFalse(result["cache_hit"])
        self.assertEqual(result["tokens_cached"], 0)
        self.assertEqual(result["cost_savings_pct"], 0.0)

    def test_cache_expiration(self):
        short_cag = CAGCacheEngine(default_ttl=1)
        session = short_cag.warm_cache("test-repo", self.sample_docs, ttl_seconds=1)
        time.sleep(1.1)
        expired_session = short_cag.get_cache(session.cache_id)
        self.assertIsNone(expired_session)

    def test_cag_vs_rag_latency_comparison(self):
        session = self.cag.warm_cache("test-repo", self.sample_docs)
        cag_result = self.cag.execute_query(session.cache_id, "What does StripeWebhookHandler do?")
        
        rag = VectorRAGEngine(self.sample_docs)
        rag_result = rag.query("What does StripeWebhookHandler do?")
        
        # CAG should be significantly faster because prompt prefix is already cached
        self.assertLess(cag_result["latency_ms"], rag_result["latency_ms"])
        self.assertTrue(cag_result["cache_hit"])

    def test_stats_tracking(self):
        session = self.cag.warm_cache("test-repo", self.sample_docs)
        self.cag.execute_query(session.cache_id, "Query 1")
        self.cag.execute_query(session.cache_id, "Query 2")
        self.cag.execute_query("invalid-cache", "Query 3")
        
        stats = self.cag.get_stats()
        self.assertEqual(stats["total_queries"], 3)
        self.assertEqual(stats["cache_hits"], 2)
        self.assertAlmostEqual(stats["cache_hit_rate_pct"], 66.67, delta=0.1)

if __name__ == "__main__":
    unittest.main()
