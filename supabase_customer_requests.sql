-- Run once in your Supabase SQL Editor. This is a separate table;
-- it does not modify existing lead or customer tables.
create table if not exists public.customer_requests (
  id uuid primary key,
  created_at timestamptz not null default now(),
  name text not null,
  phone text not null,
  email text not null default '',
  address text not null,
  city text not null,
  zip text not null,
  service text not null,
  timing text not null,
  description text not null,
  consent boolean not null check (consent = true),
  source text not null default 'customer_form',
  status text not null default 'new' check (status in ('new','contacted','quoted','won','lost')),
  followup timestamptz,
  notes text not null default ''
);
alter table public.customer_requests enable row level security;
revoke all on public.customer_requests from anon, authenticated;
grant select, insert, update, delete on public.customer_requests to service_role;
-- No public read or write policies. Submissions use the server endpoint.
