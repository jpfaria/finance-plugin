"""SQLite DDL for the disposable query cache."""

SCHEMA = """
create table entries (
  id text primary key,
  date text not null,
  year_month text not null,
  account text not null,
  amount text not null,
  description text not null,
  category text not null,
  tags text not null,
  installment text not null,
  installment_group text not null,
  transfer_group text not null,
  status text not null,
  source text not null,
  import_hash text not null
);
create index entries_month on entries(year_month);
create index entries_account_date on entries(account, date);

create table accounts (
  id text primary key,
  name text not null,
  bank text not null,
  type text not null,
  closing_day integer,
  due_day integer
);

create table budget (
  category text primary key,
  amount text not null
);
"""
