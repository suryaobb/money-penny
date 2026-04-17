-- Money Penny Phase 2: Production Schema

-- Symbols watchlist
create table if not exists symbols (
  id bigint generated always as identity primary key,
  ticker text unique not null,
  is_active boolean default true,
  asset_type text not null default 'stock',
  signal_enabled boolean default false,
  created_at timestamptz default now()
);

-- Daily session levels (VWAP, ORB, EMA20)
create table if not exists session_levels (
  id bigint generated always as identity primary key,
  ticker text not null,
  trade_date date not null,
  open_price numeric,
  premarket_high numeric,
  premarket_low numeric,
  orb_high numeric,
  orb_low numeric,
  vwap numeric,
  ema_20 numeric,
  updated_at timestamptz default now(),
  unique(ticker, trade_date)
);

-- 1-minute candles for signal processing
create table if not exists candles (
  id bigint generated always as identity primary key,
  ticker text not null,
  time_utc timestamptz not null,
  open numeric not null,
  high numeric not null,
  low numeric not null,
  close numeric not null,
  volume bigint not null,
  vwap numeric,
  ema_20 numeric,
  created_at timestamptz default now(),
  unique(ticker, time_utc)
);

-- Setup states (WATCH, READY, TRIGGER, INVALIDATED, COOLDOWN)
create table if not exists setups (
  id bigint generated always as identity primary key,
  ticker text not null,
  setup_family text not null,  -- 'VWAP_EMA_CROSSOVER', 'VWAP_PULLBACK_RECLAIM', etc
  setup_state text not null,   -- WATCH, READY, TRIGGER, INVALIDATED, COOLDOWN
  entry_type text,              -- 'CROSSOVER', 'PULLBACK_RECLAIM', etc
  entry_price numeric,
  entry_time timestamptz,
  vwap_at_entry numeric,
  ema20_at_entry numeric,
  setup_score numeric,
  invalidation_price numeric,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Option snapshots (for flow analysis, future expansion)
create table if not exists option_snapshots (
  id bigint generated always as identity primary key,
  ticker text not null,
  expiration_date date not null,
  call_volume bigint,
  put_volume bigint,
  call_oi bigint,
  put_oi bigint,
  pcr_volume numeric,
  pcr_oi numeric,
  created_at timestamptz default now(),
  unique(ticker, expiration_date)
);

-- System state (last candle processed, polling status, etc)
create table if not exists system_state (
  id bigint generated always as identity primary key,
  key text unique not null,
  value jsonb,
  updated_at timestamptz default now()
);

-- Alerts (WATCH, READY, TRIGGER, INVALIDATION, COOLDOWN)
create table if not exists alerts (
  id bigint generated always as identity primary key,
  ticker text not null,
  alert_type text not null,    -- 'watch', 'ready', 'trigger', 'invalidation', 'cooldown'
  priority text not null,       -- 'info', 'watch', 'ready', 'trigger'
  headline text not null,
  message text not null,
  context jsonb default '{}'::jsonb,
  setup_id bigint,
  created_at timestamptz default now()
);

-- Signal snapshots (historical record of setup states)
create table if not exists signal_snapshots (
  id bigint generated always as identity primary key,
  ticker text not null,
  setup_family text not null,
  setup_state text not null,
  score numeric,
  payload jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

-- Enable RLS
alter table symbols enable row level security;
alter table session_levels enable row level security;
alter table candles enable row level security;
alter table setups enable row level security;
alter table option_snapshots enable row level security;
alter table system_state enable row level security;
alter table alerts enable row level security;
alter table signal_snapshots enable row level security;

-- Public read policies (dashboard can read)
create policy "symbols_read" on symbols for select using (true);
create policy "session_levels_read" on session_levels for select using (true);
create policy "candles_read" on candles for select using (true);
create policy "setups_read" on setups for select using (true);
create policy "option_snapshots_read" on option_snapshots for select using (true);
create policy "system_state_read" on system_state for select using (true);
create policy "alerts_read" on alerts for select using (true);
create policy "signal_snapshots_read" on signal_snapshots for select using (true);

-- Indexes for performance
create index if not exists idx_candles_ticker_time on candles(ticker, time_utc desc);
create index if not exists idx_setups_ticker_active on setups(ticker, is_active);
create index if not exists idx_alerts_created on alerts(created_at desc);
create index if not exists idx_alerts_ticker on alerts(ticker);
