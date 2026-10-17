# Milestones

| ID | Name | Outcome | Exit criteria |
|---|---|---|---|
| **M1** | Foundation & Postgres | Backend can persist and retrieve data in Postgres. | Schema/migrations work from a clean DB; persistence tests pass. |
| **M2** | Telegram transport | Telegram message reaches backend and reply returns. | Receive, store and reply path works end to end. |
| **M3** | Build interaction state | Backend assembles context for a decision. | Current message, recent turns, current items and prompt are assembled/tested. |
| **M4** | LLM contract | One model invocation produces a validated structured result. | Model, schema, prompt and safe no-retry fallback tested. |
| **M5** | Maintain memory | Validated decisions safely create/update items. | Allowlisted actions, validation, DB writes, history and uncertainty tests pass. |
| **M6** | Retrieve progress | Questions return useful, correctly scoped progress. | Intent/scope handling, queries, presentation and retrieval tests pass. |
| **M7** | Complete interaction | Both workflows respond through Telegram. | Update and retrieval end-to-end tests pass, including failure paths. |
| **M8** | Validate V1 | Mechanism is evaluated against speed, cost and reliability goals. | Latency/cost measured; long messages and security tested; docs complete. |

## Progress

- [x] M1 — Foundation & Postgres
- [ ] M2 — Telegram transport
- [ ] M3 — Build interaction state
- [ ] M4 — LLM contract
- [ ] M5 — Maintain memory
- [ ] M6 — Retrieve progress
- [ ] M7 — Complete interaction
- [ ] M8 — Validate V1
