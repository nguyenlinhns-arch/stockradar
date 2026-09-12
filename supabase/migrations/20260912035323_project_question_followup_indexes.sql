create index if not exists stockradar_project_questions_thread_id_idx
  on public.stockradar_project_questions(thread_id);

create index if not exists stockradar_project_questions_parent_id_idx
  on public.stockradar_project_questions(parent_id)
  where parent_id is not null;
