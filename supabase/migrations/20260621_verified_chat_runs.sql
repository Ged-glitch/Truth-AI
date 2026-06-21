create table if not exists public.verified_chat_runs (
    run_hash text primary key,
    request_hash text not null,
    decision text not null,
    cleaned_output text not null,
    run_json text not null,
    created_at timestamptz not null default timezone('utc', now()),
    user_id uuid not null default auth.uid()
);

alter table public.verified_chat_runs enable row level security;

drop policy if exists "verified_chat_runs_select_own" on public.verified_chat_runs;
create policy "verified_chat_runs_select_own"
    on public.verified_chat_runs
    for select
    using (auth.uid() is not null and user_id = auth.uid());

drop policy if exists "verified_chat_runs_insert_own" on public.verified_chat_runs;
create policy "verified_chat_runs_insert_own"
    on public.verified_chat_runs
    for insert
    with check (auth.uid() is not null and user_id = auth.uid());

create index if not exists verified_chat_runs_created_at_idx
    on public.verified_chat_runs (created_at desc);
