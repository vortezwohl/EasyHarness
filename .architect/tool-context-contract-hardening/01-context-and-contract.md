# Context and Contract

## Metadata
- Document Type: Context and Contract
- Document ID: CONTEXT
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Observed Facts
- The Context tuple branch treats an empty generic alias as an unconstrained tuple.
- One Agent owns a mutable Strands session; the dependency rejects concurrency but EasyHarness does not expose a stable busy error.
- The configured Ruff command reports source and test violations.

## Approved Input Limits
- Reject tuple[()] while preserving the approved Context grammar.
- Permit exactly one active Agent invocation and reject reentry immediately.
- Make ruff check easyharness tests pass without configuration changes.

## Compatibility Intent
- Preserve valid Context forms, hidden schemas, cancel, stream, and session reuse.
- Add a root-exported AgentBusyError.

## Functional Boundary
- Requested Functionality: registration-time rejection, busy gate, and full Ruff repair.
- Protected Functionality: valid Context binding, per-call maps, single-call events, and cancellation.
- Explicit Non-Goals: queueing, parallelism, coercion, grammar expansion, and lint relaxation.
- Compatibility Guarantees: existing public methods and successful paths remain stable; only one new exception type is exported.
- Mandatory Stop Condition: stop if implementation requires a Strands concurrency-model change, a scheduler, or unapproved typing support.
