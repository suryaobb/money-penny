create table if not exists symbols (
  id bigint generated always as identity primary key,
  ticker text unique not null,
  is_active boolean default true,
  asset_type text not null default 'stock',
  created_at timestamptz default now()
);

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
  created_at timestamptz default now()
);

create table if not exists alerts (
  id bigint generated always as identity primary key,
  ticker text not null,
  alert_type text not null,
  priority text not null,
  headline text not null,
  message text not null,
  context jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists signal_snapshots (
  id bigint generated always as identity primary key,
  ticker text not null,
  setup_family text not null,
  setup_state text not null,
  score numeric,
  payload jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);
