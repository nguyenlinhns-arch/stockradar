from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
class WorkspaceSQLContract(unittest.TestCase):
 def test_default_private_and_owner_read_only(self):
  s=(ROOT/'supabase/migrations/20260907025732_stockradar_chatgpt_workspace_reports.sql').read_text()
  for marker in ['enable row level security','using ((select auth.uid())=user_id)',"default 'DRAFT'","status in ('DRAFT','ARCHIVED')",'security invoker',"set search_path=''",'unique(user_id,idempotency_key)','IDEMPOTENCY_CONFLICT_REVIEW_REQUIRED','WORKSPACE_NOT_LINKED']:
   self.assertIn(marker,s)
  self.assertNotIn('security definer',s.lower())
  self.assertNotIn('grant insert on',s.lower())
  self.assertNotIn("'PUBLISHED'",s)
 def test_workflow_has_no_secret_or_private_gpt_dependency(self):
  s=(ROOT/'website/assets/execution-config.js').read_text()
  self.assertIn("mode",(ROOT/'supabase/functions/_shared/chatgpt-workspace.ts').read_text())
  self.assertIn("dedicated_app_published:false",s)
  self.assertNotIn('chatgpt.com/g/',s)
  self.assertNotIn('sk-proj-',s)
