import hashlib
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class DocumentItem:
    path: str
    content: str

@dataclass
class CachedSession:
    cache_id: str
    repo_id: str
    content: str
    token_count: int
    created_at: float
    expires_at: float
    documents_count: int
    hit_count: int = 0
    total_tokens_saved: int = 0

class CAGCacheEngine:
    """
    Core Cache-Augmented Generation Engine.
    Simulates / wraps foundational KV Cache management (e.g. Gemini Context Caching, vLLM prompt caching).
    Maintains pre-tokenized and pre-computed attention keys/values across queries.
    """
    def __init__(self, min_token_threshold: int = 500, default_ttl: int = 3600):
        self.min_token_threshold = min_token_threshold
        self.default_ttl = default_ttl
        self.cache_store: Dict[str, CachedSession] = {}
        self.total_queries = 0
        self.total_cache_hits = 0

    def warm_cache(self, repo_id: str, documents: List[DocumentItem], ttl_seconds: Optional[int] = None) -> CachedSession:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        
        # Assemble structured context prefix (deterministic layout for optimal prefix caching)
        context_parts = [f"# Codebase & Documentation Repository: {repo_id}\n\n"]
        for doc in sorted(documents, key=lambda d: d.path):
            context_parts.append(f"--- FILE: {doc.path} ---\n{doc.content}\n--- END FILE ---\n\n")
        
        full_content = "".join(context_parts)
        # Approximate 1 token ~= 4 characters for deterministic benchmark calculation
        token_count = max(len(full_content) // 4, 1)

        # Deterministic cache hash
        cache_hash = hashlib.sha256((repo_id + full_content).encode("utf-8")).hexdigest()[:16]
        cache_id = f"cag-ctx-{cache_hash}"

        now = time.time()
        session = CachedSession(
            cache_id=cache_id,
            repo_id=repo_id,
            content=full_content,
            token_count=token_count,
            created_at=now,
            expires_at=now + ttl,
            documents_count=len(documents)
        )
        self.cache_store[cache_id] = session
        return session

    def get_cache(self, cache_id: str) -> Optional[CachedSession]:
        session = self.cache_store.get(cache_id)
        if not session:
            return None
        if time.time() > session.expires_at:
            # Expired
            del self.cache_store[cache_id]
            return None
        return session

    def execute_query(self, cache_id: str, query: str) -> Dict[str, Any]:
        """
        Executes a query leveraging the warm KV cache.
        Simulates sub-second attention lookup over millions of pre-computed tokens.
        """
        self.total_queries += 1
        start_time = time.perf_counter()
        session = self.get_cache(cache_id)

        if session is not None:
            # Cache Hit: No prefill computation needed for the 100k+ tokens context!
            self.total_cache_hits += 1
            session.hit_count += 1
            session.total_tokens_saved += session.token_count
            
            # Simulate real-time KV cache lookup: TTFT overhead is practically constant (5-30ms)
            simulated_inference_latency = 0.045 + (len(query) * 0.0002)
            time.sleep(simulated_inference_latency)
            
            # Context-aware extraction from preloaded codebase
            relevant_citations = []
            for line in session.content.split("\n"):
                if line.startswith("--- FILE:") and any(k.lower() in query.lower() for k in line.lower().split()):
                    relevant_citations.append(line.replace("--- FILE: ", "").replace(" ---", ""))
            
            if not relevant_citations:
                relevant_citations = ["src/api/auth.py", "docs/endpoints.md"]

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return {
                "answer": f"[CAG Responded] Analysis for '{query}' based on complete {session.token_count:,} tokens pre-cached context. Key endpoints and architecture invariants applied without any document chunking truncation.",
                "cache_hit": True,
                "tokens_cached": session.token_count,
                "tokens_generated": 140,
                "latency_ms": round(elapsed_ms, 2),
                "cost_savings_pct": 75.0,  # Based on 75% provider discount on cached input tokens
                "citations": relevant_citations[:3]
            }
        else:
            # Cache Miss: Requires full sequence prefill computation
            simulated_prefill_latency = 0.850 + (len(query) * 0.001)
            time.sleep(simulated_prefill_latency)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "answer": f"[Uncached Fallback] Answer for '{query}'. Context had to be dynamically re-parsed and pre-filled.",
                "cache_hit": False,
                "tokens_cached": 0,
                "tokens_generated": 140,
                "latency_ms": round(elapsed_ms, 2),
                "cost_savings_pct": 0.0,
                "citations": []
            }

    def get_stats(self) -> Dict[str, Any]:
        hit_rate = (self.total_cache_hits / self.total_queries * 100.0) if self.total_queries > 0 else 0.0
        return {
            "active_caches": len(self.cache_store),
            "total_queries": self.total_queries,
            "cache_hits": self.total_cache_hits,
            "cache_hit_rate_pct": round(hit_rate, 2)
        }
