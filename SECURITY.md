# Security Policy

## Reporting Vulnerabilities

Do not open a public issue for a suspected vulnerability. Report it privately to
the repository owner through GitHub security advisories, or contact the maintainer
using the GitHub profile linked from the repository.

Include:

- affected route, command or package area
- reproduction steps
- expected impact
- whether credentials, private standards content or user data may be exposed

## Secret Handling

Never commit real secrets. This includes:

- Supabase service-role keys
- provider API keys for OpenAI, Gemini, Anthropic or local gateways
- Vercel tokens
- GitHub tokens
- paid standards documents or private evidence corpora

Allowed in git:

- empty placeholders in `.env.example`
- public Supabase project URL
- browser-safe Supabase anon key only when row-level security is correctly
  configured
- masked UI examples that are not real credentials

Server-only secrets belong in Vercel environment variables or ignored local
`.env.local` files.

## User-Provided LLM Keys

Truth-AI should keep the option for users to bring their own model or API key.
Those keys must not be committed, logged, mirrored into deterministic artefacts,
or passed into `src/truthkernel/`. Live model calls belong in adapters and API
routes outside the deterministic kernel.

## Determinism Boundary

The kernel must remain replayable and side-effect free. Security fixes must not
add hidden network, clock, randomness or environment dependencies to hashed
output paths.
