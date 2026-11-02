# Admind Deck Builder - documentation

Read in order for the full picture, or jump to what you need.

1. [Overview](01-overview.md) - goals, constraints, the "model decides, code draws" approach, results
2. [Architecture](02-architecture.md) - components, network, request lifecycle, concurrency, data retention
3. [Generation pipeline](03-generation-pipeline.md) - ingest, context budgets, outline, parallel slides, fact check
4. [Slide schema](04-slide-schema.md) - the 16 slide types and the JSON contract
5. [Rendering](05-rendering.md) - template, brand system, text fitting, charts, tables, animations, previews
6. [Model serving](06-model-serving.md) - vLLM, Qwen3.6-35B-A3B NVFP4, measurements, alternatives, rollback
7. [Engine API](07-engine-api.md) - endpoints, authentication, job storage
8. [Web app](08-web-app.md) - Next.js front end, login, direct uploads
9. [Deployment](09-deployment.md) - Docker, Cloudflare tunnel, Vercel, configuration, operations, security
13. [Deploy for your team](13-deploy-for-team.md) - step-by-step checklist (Vercel + tunnel; Render notes)
10. [Testing](10-testing.md) - fixture, smoke, scenarios, end-to-end, review workflow
11. [Code map](11-code-map.md) - every file explained
12. [Extending](12-extending.md) - new slide types, other brands, other models, limitations, next steps

Quick start: see the [project README](../README.md).
