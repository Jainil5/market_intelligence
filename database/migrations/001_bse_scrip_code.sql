-- Run once on existing projects created before bse_scrip_code was added.
alter table public.stock_list add column if not exists bse_scrip_code text;
