-- Optional read access for authenticated Supabase users (dashboard / mobile app with anon key + login).
-- Service-role backend writes are unaffected.

drop policy if exists "read stock_list" on public.stock_list;
create policy "read stock_list" on public.stock_list
  for select to authenticated using (true);

drop policy if exists "read stock_prices" on public.stock_prices;
create policy "read stock_prices" on public.stock_prices
  for select to authenticated using (true);

drop policy if exists "read news" on public.news;
create policy "read news" on public.news
  for select to authenticated using (true);

drop policy if exists "read announcements" on public.announcements;
create policy "read announcements" on public.announcements
  for select to authenticated using (true);
