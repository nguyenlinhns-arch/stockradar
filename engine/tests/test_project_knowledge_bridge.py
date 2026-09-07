"""Regression coverage for the reviewed project-knowledge bridge."""
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[2]
class ProjectKnowledgeBridgeTest(unittest.TestCase):
    def test_shared_loader_contract(self):
        result = subprocess.run(['node','--test','scripts/project_knowledge_bridge_test.mjs'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout + result.stderr)
    def test_both_research_endpoints_use_server_knowledge(self):
        for name in ('stock-ai','stock-ai-guest'):
            with self.subTest(endpoint=name):
                text=(ROOT/'supabase/functions'/name/'index.ts').read_text()
                self.assertIn('const projectKnowledge=await loadProjectKnowledge(db);',text)
                self.assertIn('instructions:projectKnowledgeInstructions(STOCKRADAR_SYSTEM_CORE,projectKnowledge)',text)
                self.assertIn('projectKnowledgeMeta(projectKnowledge,Boolean(modelText))',text)
                self.assertNotIn('instructions:STOCKRADAR_SYSTEM_CORE,',text)
                self.assertNotIn('body.knowledge',text)
                self.assertIn('releasedReport(r.data,Date.now(),message)',text)
                self.assertIn('store:false',text)
    def test_chat_uses_same_loader_and_actual_downstream_version(self):
        text=(ROOT/'supabase/functions/stock-ai-chat/index.ts').read_text()
        self.assertIn('return await loadProjectKnowledge(db);',text)
        self.assertIn('const instructions = projectKnowledgeInstructions(',text)
        self.assertIn('result?.knowledge_version || knowledge.version',text)
        self.assertIn('.eq("user_id",userId)',text)
        self.assertIn('auth.auth.getUser(token)',text)
    def test_bridge_does_not_publish_transcripts_or_private_contents(self):
        text=(ROOT/'supabase/functions/_shared/stockradar-knowledge.ts').read_text()
        self.assertIn("knowledge_sync_mode: 'REVIEWED_PROJECT_SNAPSHOT'",text)
        metadata=text[text.index('export function projectKnowledgeMeta'):text.index('export function projectKnowledgeInstructions')]
        self.assertNotIn('content:',metadata)
        self.assertNotIn('knowledge.content',metadata)
