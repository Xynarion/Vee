# Milestones

| Milestone | Goal | Outcome | State |
|---|---|---|---|
| **M1 — Foundation: Vee & Company Progress Memory** | Vee's backend foundation and the company's central progress memory are established in PostgreSQL. | SQLAlchemy models, PostgreSQL schema, Alembic migrations, and persistence tests. From a clean database, work, history, users, channels, and messages can be stored and retrieved. | Completed |
| **M2 — Communication: Telegram Bot** | Vee can receive messages and send replies through Telegram. | Telegram bot, webhook, message persistence, and reply path work end to end; relevant integration tests pass. | Completed |
| **M3 — Interaction State Assembly** | The backend prepares the context Vee needs for each interaction decision. | Current message, recent conversation turns, active work items, and system-prompt context are assembled and tested. | Completed |
| **M4 — Vee's Central Decision-Making** | Build Vee's central decision-making component, capable of making judgements, generating a tool execution plan, and deciding what to say, all in a single LLM invocation. | The Judge–Plan–Say contract is defined; a single Qwen3.5-9B invocation receives the assembled interaction state and produces a structured judgement, tool execution plan (if needed), and proposed reply; validation, rejection, clarification, and safe failure paths are tested. | Completed |
| **M5 — Execute Decisions & Maintain Progress Memory** | The backend safely executes validated tool plans and returns explicit execution results for downstream reply formatting. | Only allowlisted `add_item`, `update_item`, and `search_items` actions execute; target item IDs are resolved; database writes and history are verified; execution success/failure and no-tool-call paths produce reliable structured results. | In progress |
| **M6 — Recall & Testify About Progress** | Vee retrieves relevant company progress records to answer orientation and reflection questions, without inventing facts or offering unsolicited guidance. | Date-scope, intent, item selection and ordering are tested against the database; search and retrieval return grounded records and IDs for the same decision, optional tools, and reply-formatter pipeline; empty and ambiguous results are handled safely. | Todo |
| **M7 — Reply Formatter & Complete Telegram Interaction** | Deterministic reply formatting converts Vee's validated decision and tool execution results into accurate, readable Telegram replies across brain-dumping and remembering. | After tool execution — or directly when no tools are needed — the Reply Formatter resolves target IDs into readable item names, appends the reply text and results, applies guardrails (including never confirming unexecuted changes), uses Bullet Journal task, event, and status symbols, and outputs the final message. The reply is stored and sent via Telegram. Acknowledgement, clarification, silence, failure, and end-to-end paths are tested. | Todo |
| **M8 — Validate Vee V1** | Vee V1 is evaluated across the complete receive → store → assemble state → single LLM invocation → validate → optional tool execution → reply formatter → store reply → Telegram workflow. | End-to-end latency and cost are measured. Record changes, ID resolution, faithful recall, Bullet Journal formatting, and persisted confirmations are checked. Ambiguity, duplicates, failures, silence boundaries, no-tool calls, long messages, security, and duplication are tested. | Todo |

## Progress

- [x] M1 — Foundation: Vee & Company Progress Memory
- [x] M2 — Communication: Telegram Bot
- [x] M3 — Interaction State Assembly
- [x] M4 — Vee's Central Decision-Making
- [ ] M5 — Execute Decisions & Maintain Progress Memory
- [ ] M6 — Recall & Testify About Progress
- [ ] M7 — Reply Formatter & Complete Telegram Interaction
- [ ] M8 — Validate Vee V1
