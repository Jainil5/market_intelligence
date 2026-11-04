-- Sample watchlist. Safe to re-run: skips rows that already exist.
insert into public.stock_list (
  stock_id, symbol, yfinance_symbol, company_name, exchange, bse_scrip_code, sector, active
) values
  ('STK001', 'RELIANCE', 'RELIANCE.NS', 'Reliance Industries', 'BOTH', '500325', 'Energy', true),
  ('STK002', 'TCS', 'TCS.NS', 'Tata Consultancy Services', 'NSE', null, 'Technology', true),
  ('STK003', 'INFY', 'INFY.NS', 'Infosys', 'BOTH', '500209', 'Technology', true)
on conflict (stock_id) do nothing;
