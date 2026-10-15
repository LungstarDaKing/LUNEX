# LUNEX

The assistant for **LSDKChat**. It chats like WhatsApp's bots: short replies, streams as it types, and can

- **answer questions about the app** (built-in help guide: `src/lunex/knowledge/lsdkchat.md`, edit it as the app grows)
- **research** a topic on the web and answer with sources (`/research ...`, or asking for "latest news about...")
- **summarize** a link, pasted text, or a chat the user chooses to share (`/summarize`)
- translate, rewrite, explain, quick maths (`/calc`), time zones (`/time`), and general chat
- keep your free AI quotas safe: login check, per-person and daily limits, and automatic fallback between providers

It is a small web service (Python / FastAPI). The LSDKChat app talks to it with `client/lunex.js`.
**To connect it to the app, follow `INTEGRATION.md`.**

## Try it on your computer (5 minutes)
```
python -m venv .venv
.venv\Scripts\activate            (Mac/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
copy .env.example .env            (then put at least ONE AI key in .env, see below)
python -m lunex
```
Open http://localhost:8000/demo and chat. `python -m pytest` runs the tests (no keys or internet needed).

## Getting an AI key (free options)
LUNEX tries the providers in `LUNEX_PROVIDERS` in order and moves to the next if one is busy or out of quota.
Free tiers exist at **Groq**, **Google Gemini (AI Studio)** and **OpenRouter** (free models): create an account, make an API key, paste it in `.env`.
Free limits and model names change often, so check each site; if one stops working LUNEX falls back to the next.
Anthropic and OpenAI are paid (add `anthropic` / `openai` to `LUNEX_PROVIDERS`). **Ollama** runs models on your own PC for free (`ollama` in `LUNEX_PROVIDERS`), but only while your PC is on.

## Putting it online (so everyone can use it)
LUNEX must run somewhere that is always on. Options (check each site's current free terms):
- **Render** (Docker, free web service): connect your GitHub repo, set the environment variables from `.env.example`. The free service sleeps when idle, so the first message after a quiet period is slow.
- **Hugging Face Spaces** (Docker) or any VPS: use the included `Dockerfile`.
- **Your own PC + Cloudflare Tunnel**: free, but LUNEX is only available while your PC is on, and quick-tunnel links change each time.

In production set: `LUNEX_ENV=production`, `LUNEX_AUTH=supabase`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `LUNEX_ALLOWED_ORIGINS=https://lungstardaking.github.io`, and your AI keys. Never put AI keys in the app's code or in GitHub.

## Safety built in
- Only signed-in LSDKChat users can use it (their login is checked with Supabase); `LUNEX_AUTH=off` is ignored outside development.
- Limits per person (per minute and per day) and a global daily cap; one question at a time per person.
- Web pages and shared chats are treated as untrusted data (they cannot give LUNEX instructions); links to private/internal addresses are blocked.
- CORS only for your site; request size limits; no message content is stored or logged by LUNEX.

## Layout
`src/lunex/ai` providers + fallback router · `bot` skills, personality, FAQ search · `web` safe fetch + search · `api` the web service · `client` files for the app · `tests`.
