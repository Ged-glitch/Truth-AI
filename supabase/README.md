# Supabase

Project dashboard:

```text
https://supabase.com/dashboard/project/yfdatlwczuqxbdfodfui
```

Project ref:

```text
yfdatlwczuqxbdfodfui
```

Public project URL:

```text
https://yfdatlwczuqxbdfodfui.supabase.co
```

## Secrets

Keep local values in `.env`. Do not commit `.env`.

Use `.env.example` for variable names only:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
```

`SUPABASE_ANON_KEY` may be used by a browser client when row-level security is
configured correctly. `SUPABASE_SERVICE_ROLE_KEY` is server-only and must never
be shipped to the static frontend.

## Planned Use

Truth-AI should use Supabase for product/runtime data outside the deterministic
kernel:

- user auth and workspace membership
- uploaded evidence metadata
- verification job records
- decision bundle indexes
- report metadata

The deterministic kernel and committed fixtures remain local, replayable, and
independent of Supabase. Network-backed storage belongs in adapters or service
layers, not inside `src/truthkernel/` predicate or hashing paths.
