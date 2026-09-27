# ADR-003: AI Provider Abstraction

## Status

Accepted for the existing agent-generation layer; provider coverage is limited.

## Current implementation

`backend/app/ai/base.py` defines a provider interface. The active factory in `factory.py` selects Gemini when configured and otherwise uses the deterministic mock provider. Settings mention other providers, but the active factory does not implement OpenRouter or Mistral integrations.

## Target considerations

Keep provider calls behind a service boundary and make errors explicit. Tavily/web search is a distinct research retrieval integration; it is not provided by the current LLM provider abstraction. Provider and search capabilities must not fabricate sources or convert unavailable services into success-shaped evidence.
