from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
class ProjectChannelContract(unittest.TestCase):
 def test_private_defaults_and_browser_rights(self):
  s=(ROOT/'supabase/migrations/20260907034311_project_question_channel.sql').read_text()
  for required in ['using ((select auth.uid())=user_id)','unique(user_id,client_key)',"public_action_allowed=false",'CLAIM_EXPIRED_OR_CANCELLED','QUESTION_ALREADY_CLAIMED','PARENT_QUESTION_NOT_AVAILABLE','PROJECT_QUEUE_LIMIT','ACCOUNT_NOT_ACTIVE',"'automatic_model_trigger',false",'EXACTLY_ONE_REVIEWED_PRIVATE_PROJECT_REQUIRED']:
   self.assertIn(required,s)
  self.assertNotIn('grant update on public.stockradar_project_questions to authenticated',s)
  self.assertIn('public.read_stockradar_project_inbox(integer) from public,anon,authenticated',s)
  self.assertIn('public.complete_stockradar_project_question(uuid,uuid,text,jsonb) from public,anon,authenticated',s)
 def test_final_artifact_includes_channel_without_enabling_inference(self):
  s=(ROOT/'scripts/activate_chatgpt_workspace.py').read_text()
  self.assertIn('assets/project-channel.js',s)
  self.assertIn('assets/project-channel.css',s)
  self.assertNotIn("STOCKRADAR_INFERENCE_MODE=API",s)
 def test_route_source_contains_no_actual_account_identifiers(self):
  s=(ROOT/'PROJECT_CHANNEL.md').read_text()
  self.assertIn('does NOT automatically wake',s)
  self.assertIn('No new OpenAI key',s)
  self.assertNotIn('@gmail.com',s)
