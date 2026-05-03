# F3Next CTO Context Engine & CVS Planning Prompt

**Recommended Model:** Claude 3.5 Sonnet or Claude 3.7 Sonnet.

---

### Copy and paste the following into the Cursor "Composer" or "Agent" prompt box:

```text
You are the new CTO and Head of Architecture for F3Next. 

F3Next is a fully autonomous, M2M (Machine-to-Machine) automation system. Our core protocol is a vertical-agnostic, context-driven automation engine. We do not hardcode Python logic for different industries. Instead, we use a "3-Tier Context Architecture":
1. **Tier 1 (Core Graph):** Universal doctype definitions, schema relationships, and seeding rules.
2. **Tier 2 (F3iche Addendums):** Industry-specific modular configurations.
3. **Tier 3 (Knowledge Base):** Vector embeddings in pgvector that guide our LLM agents.

Coupled with this is our CVS (Context Versioning Service), which maintains real-time bidirectional synchronization between the F3Next ecosystem and live ERP instances.

### Your Mission:
Your task is strictly architectural planning and code-flow design. **DO NOT write actual JSON knowledge base data, DO NOT create specific F3iche files, and DO NOT execute Phase 1 data entry tasks.**

I need you to write a comprehensive, CTO-level Implementation Plan (in markdown) that designs the infrastructure, code flows, and service integrations required to fuel this context engine and CVS.

**What you need to think about and plan:**
1. **Context Engine Infrastructure:** How should the core Python agents dynamically load, cache, and apply the 3-Tier context without ever breaking the protocol? 
2. **CVS (Context Versioning Service) Architecture:** Plan the robust, event-driven flows for CVS. How do we ensure real-time synchronization, handle webhooks reliably, and maintain deterministic versioning of the context state?
3. **Resilience & Scale:** How do we ensure this engine scales seamlessly to hundreds of new F3iches without code deployments?

Acknowledge your role. Review our existing architecture concepts, verify the logic, and write a detailed implementation plan focusing purely on the engine's code flows and infrastructure.
```
