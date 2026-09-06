from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class AiConversationWorkspaceV2Tests(unittest.TestCase):
    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def test_fullscreen_ai_route_and_home_link_exist(self):
        page = self.read("website/ai/index.html")
        home = self.read("website/index.html")
        self.assertIn('data-stockradar-ai-center', page)
        self.assertIn('assets/ai-center.js', page)
        self.assertIn('href="ai/"', home)
        self.assertEqual(page.count('<h1'), 1)

    def test_conversation_client_lists_and_reopens_user_threads(self):
        source = self.read("website/assets/ai-center.js")
        for marker in (
            "get_my_stockradar_ai_threads",
            "sr-thread-sidebar",
            "sr-thread-item",
            "hydrateHistory(session, log, row.thread_id)",
            "operation: 'new_thread'",
            "Mở AI toàn màn hình",
            "Cuộc trò chuyện mới",
        ):
            self.assertIn(marker, source)

    def test_thread_list_rpc_is_user_scoped_and_not_anonymous(self):
        sql = self.read("supabase/migrations/20260906164000_add_my_stockradar_ai_thread_list.sql")
        for marker in (
            "t.user_id = auth.uid()",
            "security definer",
            "revoke all on function public.get_my_stockradar_ai_threads(integer) from public, anon",
            "grant execute on function public.get_my_stockradar_ai_threads(integer) to authenticated",
            "limit least(greatest(coalesce(p_limit, 30), 1), 50)",
        ):
            self.assertIn(marker, sql)

    def test_conversation_workspace_is_responsive(self):
        css = self.read("website/assets/ai-conversation-v2.css")
        for marker in (
            "grid-template-columns:250px minmax(0,1fr)",
            ".sr-thread-sidebar",
            ".sr-thread-list",
            "@media(max-width:760px)",
            "threads-open",
            ".ai-chat-page",
        ):
            self.assertIn(marker, css)


if __name__ == "__main__":
    unittest.main()
