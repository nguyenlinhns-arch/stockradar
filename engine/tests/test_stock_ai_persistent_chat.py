from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260906144605_add_stockradar_ai_knowledge_and_persistent_chat.sql"
CHAT_EDGE = ROOT / "supabase" / "functions" / "stock-ai-chat" / "index.ts"
KNOWLEDGE = ROOT / "supabase" / "functions" / "_shared" / "stockradar-knowledge.ts"
CLIENT = ROOT / "website" / "assets" / "ai-center.js"
PRIVACY = ROOT / "website" / "quyen-rieng-tu" / "index.html"


class StockAiPersistentChatTests(unittest.TestCase):
    def test_schema_keeps_knowledge_threads_and_messages_server_side(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "stockradar_ai_knowledge_versions",
            "stockradar_ai_threads",
            "stockradar_ai_messages",
            "stockradar_ai_user_memory",
            "AI_CORE_V1_20260906",
            "enable row level security",
            "revoke all on public.stockradar_ai_threads from anon, authenticated",
            "revoke all on public.stockradar_ai_messages from anon, authenticated",
        ):
            self.assertIn(marker, sql)
        for private_ticker in ("MBB", "HPG", "ACB"):
            self.assertNotIn(private_ticker, sql)

    def test_chat_orchestrator_restores_context_and_supports_new_threads(self):
        source = CHAT_EDGE.read_text(encoding="utf-8")
        for marker in (
            '"ask","history","new_thread"',
            "stockradar_ai_threads",
            "stockradar_ai_messages",
            "return await loadProjectKnowledge(db);",
            "last_ticker",
            "forwardHistory",
            "knowledgeAnswer",
            "/functions/v1/stock-ai",
            "OPENAI_MODEL",
            "store:false",
        ):
            self.assertIn(marker, source)
        # Knowledge retrieval moved to the shared loader; ownership and active-version
        # filtering remain required rather than relying on an obsolete inline query.
        knowledge = KNOWLEDGE.read_text(encoding="utf-8")
        self.assertIn(".from('stockradar_ai_knowledge_versions')", knowledge)
        self.assertIn(".eq('status', 'ACTIVE')", knowledge)
        self.assertIn(".in('source', PROJECT_KNOWLEDGE_SOURCES)", knowledge)
        self.assertIn('auth.auth.getUser(token)', source)
        self.assertIn('.eq("user_id",userId)', source)
        self.assertIn('result?.knowledge_version || knowledge.version', source)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY =", source)
        self.assertNotIn("OPENAI_API_KEY =", source)

    def test_home_ai_uses_persistent_authenticated_chat(self):
        source = CLIENT.read_text(encoding="utf-8")
        for marker in (
            "/functions/v1/stock-ai-chat",
            "operation: 'history'",
            "operation: 'new_thread'",
            "THREAD_KEY",
            "Cuộc trò chuyện mới",
            "Đã lưu ngữ cảnh theo tài khoản",
        ):
            self.assertIn(marker, source)

    def test_privacy_discloses_ai_history(self):
        source = PRIVACY.read_text(encoding="utf-8")
        self.assertIn("Lịch sử hội thoại StockRadar AI", source)
        self.assertIn("OpenAI API", source)
        self.assertIn("store:false", source)
        self.assertIn("lịch sử hội thoại AI", source)


if __name__ == "__main__":
    unittest.main()
