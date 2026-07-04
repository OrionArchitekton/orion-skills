---
name: prove-deploy-is-live
description: 'Use when about to declare a deploy, restart, redeploy, cutover, promote/flip, or config push "live"/"done"/"fixed", or when verifying someone else''s "it''s deployed" claim. Symptoms: green CI, exit 0, docker "Up (healthy)", /health 200, "PR merged", "reload fired", "should be live now". For containers, serverless (Vercel), systemd units, and SPAs.'
---

# prove-deploy-is-live

## Overview

**A deploy is proven live only when you have watched the running artifact serve correct behavior on its real route. Every cheaper signal is necessary-at-most, never sufficient.**

The dominant silent-prod-regression shape: every proxy signal is green (CI passed, `docker ps` healthy, `/health` 200, PR merged) and the change still is not live, because the container runs the *old* image, the real route 500s while `/health` stays 200, or a promote/flip updated `current/` but never recreated the container. One such gap silently froze a production service for over a week. "Deployed" updates source control and process state; it does not prove execution.

## When to use

Before you (or you accept someone else's claim that you) say a deploy/restart/cutover/flip/config-push is **live, done, fixed, or proven**. Also when a feature "should work" but the runtime DEFERs/errors/404s.

**When NOT:** pre-deploy readiness checks (before you ship); validating a local code change you have not shipped yet. This skill is the *post-deploy runtime proof*.

## The three proofs (do all three; none substitutes for another)

| # | Proof | What it rules out | How |
|---|-------|-------------------|-----|
| 1 | **Version identity**: the running artifact IS the new build | restart of the OLD image; merged-but-never-rebuilt; stale `current/` | `docker exec <c> python -c "import <newmodule>"`; compare running image digest / baked build-SHA to the **merge SHA** (not "PR merged"); or hit a `/version` route. For containers also check fresh `Created` timestamp + mount source. |
| 2 | **Route serves**: the declared route answers, by HTTP class | `/health` green while the real route is dead | Probe the service's **declared main route** (from `/openapi.json` or route decorators), **never `/health`, never bare `/`**. **Served** = `2xx/3xx/401/403/405/429` (app router answered). **Regression** = `404/5xx/connection-refused`. **Non-HTTP consumer** (worker/queue/cron): the equivalent of "serves" is reaching its **consume-success terminus**, so push a real item through and watch it drain/produce, never "process is up". |
| 3 | **End-to-end correct behavior**: a real request reaches the success terminus | a middle gate in a multi-gate lane failing closed invisibly; a 200 shell over data that 502s | Reproduce the original failing case and watch it succeed. Multi-gate/authority lane: run the real **ALLOW proof** to the success terminus. SPA/dashboard: browser-render + read console/network errors (`playwright` `browser_console_messages level=error`) and probe the real **data** endpoints (`/api/<resource>`), not the shell. |

**Apply all three proofs PER artifact.** A deploy spanning multiple surfaces (frontend + worker, or N services) needs the full proof set for *each*; one surface proven live says nothing about the others.

**If you cannot run a proof, the status is "wired but unproven", never "live".**

## Necessary-at-most, never sufficient (do not close on these)

`redeploy exited 0` · `docker ps` -> `Up N (healthy)` · `/health` / `/ready` 200 · bare `/` 200 · "PR merged to main" · "promote + flip ran" · "reload fired" · a public 200 (not proof an auth gate is enforced).

A healthcheck hits a path that imports cleanly; the container can be the prior image; the SPA shell renders 200 while every XHR 502s. **Healthy is not route-healthy is not data-rendering.**

## Platform trapdoors (reference; check the ones that apply)

| Platform | Trapdoor | Guard |
|---|---|---|
| Docker / compose | a promote step updates the `current/` symlink but does **not** recreate containers | `--force-recreate`; verify `Created` timestamp + mount source are new |
| Docker / compose | scoped recreate via a wrapper loading a **subset** + `--remove-orphans` deletes services not in the loaded subset | scoped `--no-deps --force-recreate` over the **full** deployed set; verify the full service count survives |
| Image pin | a shell `export` of the image tag is reverted by the next re-deploy | pin by **immutable digest** in the durable env layer the deploy actually reads (e.g. a secrets manager) |
| uvicorn | `--reload` watches the workdir, not the `PYTHONPATH` mount, so edits do not reload | restart the process / verify the mount is what is watched |
| Vercel | prebuilt-deploy truth trapdoor; prod-branch drift silently freezes the preview as "prod" | verify the prod alias resolves to the new deployment, not a frozen preview |
| systemd | the unit runs the **deployed copy**, not your canonical checkout | edit/verify the path the unit actually `ExecStart`s |
| SPA | soft-404 returns **200** but self-canonicals to root | require the page's own `rel=canonical`, not a 200 |
| Multi-PR | sequential merges can redden main after each PR was green | verify main CI green on the **actual deploy SHA** at arm + exec |

## Rationalizations, STOP

| Excuse | Reality |
|--------|---------|
| "CI's green and it merged, so it's live" | Merge updates source control. The running image is built separately and may be stale. Prove version identity. |
| "`docker ps` says healthy" | The healthcheck hits a path that imports cleanly while real routes crash. Probe the declared route. |
| "`/health` returns 200" | `/health` stayed 200 through an entire incident while the real route never served. Never probe `/health`. |
| "It's late / the lead is waiting, confirm so we can close" | A false "live" gets you paged at 3am and ships a silent regression. 2 minutes of proof beats reopening. |
| "I redeployed, the script exited 0" | Exit 0 means the command ran, not that the new image is serving. |

## Red flags (you are about to skip the proof)
- About to type "deploy is live / fixed / done" without having hit the **real route** this turn.
- Leaning on `docker ps`, `/health`, or "merged" as the closing evidence.
- Verifying a feature by **re-reading the repo** instead of inspecting the running artifact.
- Declaring a multi-gate lane "live" off the front-door transition alone.

## Related

Siblings in this collection: **prove-control-binds** (prove an existing gate/monitor
fires); **design-fail-closed-gate** (author a gate that fails closed).

## Boundary

This is the post-deploy proof discipline, not a deploy tool. The concrete probes
(how you read the running image digest, which route is "the declared main route",
how you reach a worker's consume terminus) are your stack's mechanics; the invariant
is the three proofs. Defer secret access, branch, and rollback mechanics to your own
repo doctrine.
