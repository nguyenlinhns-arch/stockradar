alter table public.watchlist_items
  add column if not exists cost_basis numeric(18,4),
  add column if not exists portfolio_weight_pct numeric(5,2);

alter table public.watchlist_items
  drop constraint if exists watchlist_cost_basis_positive,
  add constraint watchlist_cost_basis_positive check (
    cost_basis is null or cost_basis > 0
  ),
  drop constraint if exists watchlist_portfolio_weight_range,
  add constraint watchlist_portfolio_weight_range check (
    portfolio_weight_pct is null or (portfolio_weight_pct >= 0 and portfolio_weight_pct <= 100)
  ),
  drop constraint if exists watchlist_position_context_requires_ownership,
  add constraint watchlist_position_context_requires_ownership check (
    owns_stock = true or (cost_basis is null and portfolio_weight_pct is null)
  );

comment on column public.watchlist_items.cost_basis is
  'Optional user-declared average cost basis for AI personalization; not brokerage data.';

comment on column public.watchlist_items.portfolio_weight_pct is
  'Optional user-declared portfolio weight percentage for AI personalization; not NAV or position quantity.';
