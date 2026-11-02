# Source and modifications

This skill includes material adapted from [garrytan/gstack](https://github.com/garrytan/gstack)
under the MIT license. Keep [LICENSE.gstack](LICENSE.gstack) with a copy of this
skill directory. Orion's modifications remain covered by the collection's license;
this notice preserves upstream attribution.

Verified comparison revision: `4f435e45c517822014a852804c3da57bab121516`
(2026-03-26). [Source skill](https://github.com/garrytan/gstack/blob/4f435e45c517822014a852804c3da57bab121516/investigate/SKILL.md).
Files with upstream lineage: `SKILL.md`, `references/preamble.md`.
The comparison revision is a reproducible source reference; the exact revision
used during the original port was not recorded and is not inferred from similarity.

Orion import: `c6bc3fff94a4a79cc7133141ad34758262a1d780` (2026-07-06).
The port removed fabricated persona endorsements, extracted supporting references,
and adapted the internal workflow for portable use. Follow-up commits
`59dd9652a4842941e2ac21cb73c5b387d0fd9560`,
`5db495335107fc08b037db610443ef61c81e334c`, and
`92ee5f0d7a81dfa9b084527e743bc6ea90c7dad6` record subsequent review,
portability and state-handling repairs across these families.

## Additional diagnosing-bugs lineage

The reproduction discipline in Phase 1 and `scripts/hitl-loop.template.sh` are
adapted from Matt Pocock's **diagnosing-bugs**, separately from gstack.
Verified source revision: `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`.
[Source skill](https://github.com/mattpocock/skills/blob/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/engineering/diagnosing-bugs/SKILL.md)
and [HITL template](https://github.com/mattpocock/skills/blob/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/engineering/diagnosing-bugs/scripts/hitl-loop.template.sh).
The port concentrates the feedback-loop discipline into the root-cause gate and
bundles the HITL template. This is a comparison reference, not a claim that the
original import pinned that revision. Keep
[LICENSE.diagnosing-bugs](LICENSE.diagnosing-bugs) with this directory as well.
