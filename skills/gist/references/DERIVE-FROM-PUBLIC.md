# Derive-from-public: publishing safely to a code surface

`/gist` is the concrete implementation of the doctrine rule **"Gate by artifact
type"** (restated below; if you also installed the sibling `/x` skill, see the
"Gate by artifact type" section of its `references/DOCTRINE.md`): short prose can
auto-publish behind a redactor + cap, but **code/config is a higher-risk surface**
— embedded secrets, real paths, env-var names that map your infra, structural
identifiers — so keep it human-gated and, ideally, publish only material that is
*already* public. This doc is *how* you make "already public" enforceable instead
of a hope.

## The structural guard: the unauthenticated raw fetch

A denylist cannot prove a file is safe to publish — it can only flag the private
nouns you remembered to enumerate. For real source that is the wrong tool. So
`/gist` does not try to *clean* code; it refuses to publish anything that is not
**already world-readable**, and it *proves* that mechanically:

> It fetches each file from `https://raw.githubusercontent.com/OWNER/REPO/REF/PATH`
> with **no authentication**. If that request returns 200, the content is, by
> definition, already readable by anyone on the internet. Re-publishing it as a
> public gist discloses nothing new. A 404 means the path/ref is wrong **or the
> repo is not public** — either way, the publish is refused.

The fetch *is* the guard. It cannot be satisfied by private content, so there is
no path by which estate/internal code reaches a gist.

## The redactor is a backstop here, and it false-positives

The shared `redactor.py` still runs over the fetched content — but on this path a
hit is, by construction, a **false positive**: the content already cleared the
public bar upstream (it is in a public repo). For example, a public skill doc that
legitimately shows `docker login` or a token *prefix* in an example will trip the
secret-shaped patterns. That is the redactor doing its job on prose; it is not a
reason to block already-public content.

So the backstop is **fail-closed by default but human-overridable**:

- Default: any hit → **ABSTAIN**, the create is refused, the hits are printed.
- A human who has **eyeballed each hit** and confirmed it is a benign
  already-public token re-runs with `--ack-public-hits` — an explicit, logged
  decision, well-founded because the raw fetch already proved world-readability.
- **Never ack a hit you have not read.** If a hit looks like a *real* secret, stop:
  that means a leak is already live in the public repo and must be fixed *there*
  first — publishing the gist is the least of your problems.

Hard-blocking instead (no override) would make `/gist` unable to mirror even
legitimate public docs, defeating its purpose. Silently down-grading the redactor
to advisory would weaken the guard with no human in the loop. The ack is the
middle path: fail-closed, with an explicit human gate.

## Ship disarmed — and give the code surface its own arm flag

Like every publisher in this library, `/gist` ships **DISARMED**: the dry-run
constructs and inspects the gist plan without ever creating anything.

Because a gist is a **code** surface — strictly higher-risk than a prose poster —
`/gist` requires **two** arm flags by default, not one: the shared
`~/.claude/state/publishers-armed` **and** the gist-specific
`~/.claude/state/gist-publishers-armed`. A live create needs `--send` plus
**both** flags (`is_gist_armed()`). This is the point: a new, higher-risk surface
must not inherit "armed" from a flag you set for a lower-risk prose surface (e.g.
`/x`) before the code surface existed. Arming `/x` never silently arms `/gist`;
removing the shared flag still disarms everything. The dual-flag requirement lives
in `common.py` (`is_gist_armed()`), and the live `--send` path also enforces the
daily cap (`cap_ledger`) before creating and increments it on success — the cap is
not a separate manual step you can forget.

## Why human-gated (`disable-model-invocation: true`)

A gist is code going to the public internet under your account. The skill carries
`disable-model-invocation: true` so the model never auto-invokes it; a human runs
`/gist`, reads the dry-run, and decides to send. An auto-trigger hook may still
NUDGE ("this file is now public — want an embeddable gist?"), but hooks only
nudge; they never publish.
