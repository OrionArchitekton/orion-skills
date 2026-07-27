# Codex Verification Skills

## Purpose

Make Orion's three verification disciplines directly usable in Codex while
preserving one canonical copy of each skill and the repository's marketplace
boundary.

This feature establishes a narrow, verified Codex starter set. It does not
claim that every skill in the library is Codex-compatible, create a plugin,
configure a marketplace, install anything into an operator environment, or
submit anything to a public directory.

## Domain language

- **Source skill**: the canonical public skill maintained by this library.
- **Verification discipline**: one of stale-premise re-probing, control-binding
  proof, or live-deploy proof.
- **Codex starter set**: the three verification disciplines validated and
  documented for direct use in Codex.
- **Local skill installation**: copying or downloading a source skill into a
  Codex user skill location.
- **Plugin publication**: a separate distribution path that requires an
  external marketplace or public-directory action.

Use these terms consistently. "Codex starter set" does not imply library-wide
compatibility.

## Constraints

- The starter set contains exactly the three verification disciplines.
- Each skill remains canonical in its existing source directory; no
  distribution copy is introduced.
- Every starter-set skill has portable Agent Skills frontmatter accepted by the
  official OpenAI validator.
- This feature adds no connector, MCP server, hook implementation, command
  definition, application, credential, runtime service, or telemetry.
- The repository contains no plugin manifest or marketplace configuration and
  performs no operator-state mutation.
- Installation and availability claims remain precise: direct local skill
  installation is documented, while plugin-directory availability is not
  claimed.

## Scenario 1: A source skill is portable

Given the three canonical verification disciplines,
when a maintainer validates their Agent Skills frontmatter,
then each skill has a valid matching name and nonempty description and passes
the official OpenAI skill validator.

### Acceptance criteria

- All three source skills pass the official validator.
- The compatibility contract fails when a selected skill has malformed
  frontmatter or a name that differs from its directory.
- A selected skill contains no private estate path, credential, or
  harness-specific control metadata.

## Scenario 2: A Codex user can install the starter set

Given a Codex user viewing the public project documentation,
when they choose the verified starter set,
then they receive three independent installer requests and one non-overwriting
manual local-install fallback for the same three source skills.

### Acceptance criteria

- Documentation names exactly the three verified skills.
- Each installer request identifies the public repository and one source path.
- An existing skill cannot prevent either missing skill from being installed.
- The manual fallback targets Codex's documented user skill location.
- Documentation shows explicit invocation using Codex skill syntax.
- Installation requires no marketplace, plugin, hook, credential, or
  estate-local path.

## Scenario 3: Compatibility claims stay narrow

Given that the wider library includes host-specific workflows,
when a maintainer changes the README or starter-set skills,
then the contract suite rejects an expanded or inconsistent Codex claim.

### Acceptance criteria

- The README distinguishes the Codex starter set from the wider library.
- The contract suite binds the documented set to the validated set.
- Plugin-directory listing or installability is not claimed.
- Adding another Codex-compatible skill requires deliberately adding it to the
  validated set and its public documentation.

## Test seams

The feature uses two seams:

1. One repository contract suite checks frontmatter shape, matching names,
   portable source boundaries, exact README-to-starter-set agreement, and the
   extracted manual fallback in an isolated user home.
2. The official OpenAI skill validator exercises each selected source skill
   directly before handoff.

The first seam is the durable CI seam. The second is the current external
format-authority seam.
