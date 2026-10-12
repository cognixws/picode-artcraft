# ADR-0001: Verified, serialized app lifecycle

Status: accepted — owner approved the Office/GUI evolution plan on 2026-10-12.
Boundary: process coordination and control-protocol readiness in the extension.

## Context

Page requests and separate agent MCP servers can concurrently open the same app.
A TCP listener was previously enough to reuse it, even when it belonged to a
foreign process. Losing a tool response could replay a mutation. Office apps
also introduce port collisions and WordCraft's different key protocol.

## Decision

Use a bounded, per-app file lock with a reentrant thread lock across extension
callers. Verify listener identity on Windows, upstream MCP identity and a
read-only live probe before reusing a connection. Keep existing root handling,
refuse recorded live workspace mismatches, and never replace a human-opened
window. Use distinct Office ports and the upstream WordCraft key reader.
Bound bridge reads, reap owned subprocesses and never replay an uncertain call.

## Consequences

Repeated calls incur verification overhead; correctness takes priority over an
unmeasured cached connection. Cross-process locks coordinate extension callers,
not unrelated native programs. POSIX readiness is protocol-tested but native
window identity/screen-follow is Windows/WSL-specific. No OS sandbox or broader
file authority is claimed. No new PiCode core decision or door is required.
