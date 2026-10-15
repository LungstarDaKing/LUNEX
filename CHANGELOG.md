# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Initial project setup
- Created repository structure
- Added README.md and ROADMAP.md
## 0.2.0
- Chat bot service for LSDKChat: streaming replies, conversation history, skills (app help, web research with sources, summaries, translate, calc, time).
- Providers now take full conversations; any OpenAI-compatible service works (Groq, Gemini, OpenRouter, Ollama); automatic fallback between providers.
- Sign-in check (Supabase), rate limits, safe web fetching, JS client for the app.
