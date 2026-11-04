# Create a private bucket in Supabase Dashboard (Storage) named e.g. market-intelligence
# or run (service role / SQL editor with appropriate privileges):
#
# insert into storage.buckets (id, name, public)
# values ('market-intelligence', 'market-intelligence', false)
# on conflict (id) do nothing;
#
# Backend uploads use SUPABASE_SERVICE_ROLE_KEY and upsert CSV objects to:
#   historical_prices/{stock_id}.csv
