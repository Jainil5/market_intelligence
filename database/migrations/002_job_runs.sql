create table if not exists public.job_runs (
  job_id uuid primary key default gen_random_uuid(),
  job_name text not null,
  status text not null,
  summary jsonb not null default '{}'::jsonb,
  duration_ms int,
  started_at timestamptz not null default now(),
  finished_at timestamptz not null default now()
);
create index if not exists idx_job_runs_started on public.job_runs(started_at desc);
alter table public.job_runs enable row level security;
