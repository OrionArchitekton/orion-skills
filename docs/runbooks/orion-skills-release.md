---
verified: 2026-11-02
review_after: 2027-02-02
topics: [orion-skills, source-release, archives, rollback]
references:
  - README.md
  - CHANGELOG.md
  - THIRD_PARTY_NOTICES.md
  - requirements-test.txt
  - .github/workflows/tests.yml
  - tests/test_distribution_contract.py
  - tests/fixtures/distribution/required-files.json
  - skills/orion-deep-research/PROVENANCE.md
---

# Orion Skills source release

This runbook prepares and verifies the public source collection. Merge, tag,
GitHub release, website changes and local skill installation are separate actions
requiring explicit operator authority. No command here grants that authority.

## Preconditions and version choice

Refresh the default branch, open PRs and tags. Work in a clean worktree and
preserve newer source changes. Bind review, tests and disclosure inspection to
one exact commit. Keep a private decision packet outside this repository with
the commit/tree, selected changes, review dispositions, test logs, archive hashes,
destinations, rollback and remaining approvals. Do not publish private receipts.

The collection uses SemVer: a new skill is MINOR, compatible repairs are PATCH,
and breaking/removing supported behavior is MAJOR. Documentation/navigation alone
does not need a new skill version. Preserve historical changelog entries and tags.
The research `package.json` version is a private test helper, not the collection
version; do not bump it or add per-skill versions for a collection release.

The current maintenance proposal is 0.6.1. It is not publication-ready until
compatibility is accepted and the research origin question in PROVENANCE.md is
resolved with author/source evidence. Delegate retains its existing absolute-PATH
selection behavior; it does not authenticate executable identity. The stricter
installation policy is separated from this maintenance candidate because it rejects
previously accepted platforms/layouts. It needs a repair or an explicit scope/version
decision before adoption; unchanged argv alone is not proof of compatibility. Do not infer rights from tests,
remove research to evade the hold, or replace an existing tag.

## Source qualification

Use Python 3.12 and the exact `requirements-test.txt` pins in an isolated
environment. Inspect test entrypoints before running them. The CI workflow lists
the Python contract suites, bundled X/Gist selftests, research Python and Node
tests, and shell syntax check. Run them with disposable HOME/config/ledger paths
and no inherited credentials. Publishing, authentication, delegation and research
tests use fakes/stubs; no provider call, send, user install or native research
execution is part of release qualification.
Git-based fixtures must bound discovery to their disposable root, even when
HOME or TMPDIR lies beneath a real checkout; isolation must not depend on `/tmp`
being outside Git.

Run the full checks again after any source repair. Review the actual nonempty
diff for correctness, compatibility and security; record exact reviewed SHA and
any coverage limitation. Check every changed file for private paths, secrets,
unlicensed material and retained notices. Require scanner exit zero and a parsed
empty findings array, with a fresh report. A missing/error report is not clean.

`tests/test_distribution_contract.py` checks source IDs against both README
surfaces, duplicate rows, packaged mandatory files and relative Markdown links.
The retained-file manifest intentionally requires notice/helper retention. When
adding a skill later, update that contract with its reviewed mandatory files.

For the owned site, capture its exact source commit and `constants.ts` separately,
record UTC observation time, source URL and content hash, then compare command IDs
and advertised count with the source candidate. Label source evidence as source;
it does not prove deployment. Offline unit tests must not fetch changing websites.
Only prepare a site diff if released metadata actually changes, under separately
allocated source ownership. An unreleased candidate does not update the stable site.

## Candidate archives

From the exact clean reviewed commit, create local Git tar and zip candidates
with a single safe top-level prefix. Record SHA256 for each and the full commit
and tree IDs. These are local candidates, not GitHub's eventual post-tag archives.

Before extraction, reject absolute paths, parent traversal, unexpected top-level
names, duplicate file names, links, devices and special members. Extract only into
new disposable directories. Compare every member's bytes and executable flag with
the commit's tracked blobs/modes; require all 27 retained skill folders, root and
standalone notices, and mandatory relative files. Run the distribution contracts
against both extracted trees. Copy each skill alone into another disposable root;
verify its mandatory files/relative references without relying on sibling skills.
Exercise representative standalone X/Gist selftests and the readonly hook from
those copies, in temporary state. No user skill directory is an extraction target.

Do not infer executable-bit preservation by Windows extractors from Git zip mode
metadata. Verify the actual intended extractor/platform before advertising support.

## Approved publication and consumer verification

Before any later merge or publication, refresh the exact candidate and approval
scope. A reviewed draft source PR is not merge/release approval. After an approved
merge, verify the protected default branch contains the intended tree and passing
required checks. Bind any separately approved tag/version and GitHub release to
that verified commit. Stop on divergence or unresolved provenance/compatibility.

After an approved tag/release, resolve the remote tag (peeling an annotated tag),
download GitHub's tar and zip through their public URLs, and repeat member safety,
bytes, modes, notices, mandatory references and standalone checks. Compression
hashes may differ from local candidates; compare content to the tagged commit.
Record public URLs, tag/commit IDs, hashes and UTC verification time. Confirm the
public release and representative install paths at their real consumer boundary,
under separate installation authority. Do not treat tag creation as proof that a
download works or that an installed runtime adopted it.

If a separately approved site source change is deployed later, verify the public
version, skill IDs, real routes and supported installer links from the served
page. A source build or READY deployment alone is insufficient.

## Monitoring and rollback

After publication, review concrete reports of installation, denylist/ledger,
executable-layout or missing-file regressions. Preserve affected state bytes and
uncertain-send reservations; never resend to test a report. This runbook starts
no watcher, timer, provider task or background session.

Before merge, preserve the task branch/evidence and abandon or close the candidate
under operator direction. After an approved merge, use a reviewed corrective or
revert PR. After publication, retain historical tags/releases, explain the defect
and prepare an approved corrective version; never reset shared history or replace
an old tag. Website rollback requires its own approved source/deploy change. Local
user state and installed skills remain untouched by source rollback.
