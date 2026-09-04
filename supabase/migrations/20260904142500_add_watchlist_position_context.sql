alter table public.watchlist_items
  add column if not exists average_cost numeric(18,4),
  add column if not exists portfolio_weight_pct numeric(6,2);

alter table public.watchlist_items
  drop constraint if exists watchlist_items_average_cost_check;
alter table public.watchlist_items
  add constraint watchlist_items_average_cost_check
  check (average_cost is null or average_cost > 0);

alter table public.watchlist_items
  drop constraint if exists watchlist_items_portfolio_weight_pct_check;
alter table public.watchlist_items
  add constraint watchlist_items_portfolio_weight_pct_check
  check (portfolio_weight_pct is null or (portfolio_weight_pct >= 0 and portfolio_weight_pct <= 100));

comment on column public.watchlist_items.average_cost is 'Optional user-supplied average cost for private AI position context; never public.';
comment on column public.watchlist_items.portfolio_weight_pct is 'Optional user-supplied portfolio weight percentage for private AI risk context; never public.';
