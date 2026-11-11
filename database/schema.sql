-- Run in Supabase SQL Editor. stock_id is your permanent ID (e.g. STK001).

create extension if not exists pgcrypto;

create table if not exists public.stock_list (
  stock_id text primary key,
  symbol text not null,
  yfinance_symbol text not null, -- e.g. RELIANCE.NS or RELIANCE.BO
  company_name text,
  exchange text default 'NSE',
  bse_scrip_code text,
  sector text,
  industry text,
  active boolean not null default true,
  fundamentals jsonb not null default '{}'::jsonb,
  latest_prediction jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Complete daily OHLCV history: one row per stock per trading session.
-- The latest price is the close on the most recent trade_date; no rolling 31-day JSON cache is used.
create table if not exists public.stock_prices (
  stock_id text not null references public.stock_list(stock_id) on delete cascade,
  trade_date date not null,
  open numeric(18,4) not null,
  high numeric(18,4) not null,
  low numeric(18,4) not null,
  close numeric(18,4) not null,
  volume bigint,
  adj_close numeric(18,4),
  created_at timestamptz not null default now(),
  primary key (stock_id, trade_date),
  constraint valid_ohlc check (high >= low and high >= open and high >= close and low <= open and low <= close)
);
create index if not exists idx_stock_prices_date on public.stock_prices(trade_date desc);

create table if not exists public.news (
  news_id uuid primary key default gen_random_uuid(),
  stock_id text not null references public.stock_list(stock_id) on delete cascade,
  headline text not null,
  content text,
  source text,
  source_url text not null,
  published_at timestamptz,
  sentiment text,
  created_at timestamptz not null default now(),
  unique(stock_id, source_url)
);
create index if not exists idx_news_stock_published on public.news(stock_id, published_at desc);

create table if not exists public.announcements (
  announcement_id uuid primary key default gen_random_uuid(),
  stock_id text not null references public.stock_list(stock_id) on delete cascade,
  title text not null,
  category text,
  description text,
  source_url text not null,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  unique(stock_id, source_url)
);
create index if not exists idx_ann_stock_published on public.announcements(stock_id, published_at desc);

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

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_stock_list_updated_at on public.stock_list;
create trigger trg_stock_list_updated_at
before update on public.stock_list
for each row execute function public.set_updated_at();

-- Enable RLS. Keep writes server-side using SUPABASE_SERVICE_ROLE_KEY only.
alter table public.stock_list enable row level security;
alter table public.stock_prices enable row level security;
alter table public.news enable row level security;
alter table public.announcements enable row level security;
