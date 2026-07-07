# Shared preamble (retired)

This file previously held a runtime preamble (session bootstrap, telemetry,
checkpointing, AskUserQuestion formatting, jargon glosses, and related scaffolding)
tied to a toolchain that no longer exists in this installation. It was never
required for the `investigate` skill's core four-phase decision flow (see
`SKILL.md`) and has been removed.

If a lightweight preamble is needed again in the future, design it against the
tools actually installed rather than restoring this file.
