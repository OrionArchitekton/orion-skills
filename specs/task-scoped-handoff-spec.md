# Task-scoped handoff

A **task pack** is durable evidence for one named task in one repository. It is
not an approval, a lease, or project doctrine. A **pickup** is the reader's choice
to continue that same task using verified evidence. "Latest" means recency only;
it does not mean accepted, owned, current, or relevant.

## Constraints

- Record task identity, repository/worktree, owner, accepted baseline with its
  acceptance evidence (or unknown), last verified outcome with proof, unfinished
  step, literal next action, and remaining authority. Unknowns stay explicit.
- Give an explicit immutable task-pack path to the next reader. Use a persistent
  user-selected directory and a separate task namespace; preserve prior packs.
- Re-check the current request, applicable instructions, live ownership and only
  the volatile state needed for the next step. Newer accepted authority wins.
- A legacy latest pointer is usable only when its pack matches the current task
  and repository and there is exactly one eligible continuation. Missing or
  conflicting identity, multiple candidates or unknown selection means stop
  selection and request clarification. Do independent work only when authorized.
- No runtime hooks, private engine, installation, automatic memory writes or
  permission grants are part of this behavior.

## Test seams

Use the documented shell write recipe in temporary HOME and storage locations
as the single automated seam for persistence, task separation and preservation.
Use worked reader decisions for identity/authority/staleness: these are advisory
instructions, not an installed selector. A string-presence test cannot establish
that an agent chooses the correct task or that a runtime has adopted this format.

## Scenarios and acceptance

1. **Capture one task:** After verifying task A's evidence, the writer records
   the fields above, saves its pack under A's namespace and returns that exact
   path. A reader with A's request checks the fields and resumes only the recorded
   authorized step. Acceptance: the returned path exists and its bytes match the
   supplied body; unknown acceptance is not silently filled in.
2. **Two tasks share a directory:** A and B can use the same working directory
   and storage root. Writing B cannot replace A or its evidence. The reader of A
   uses A's explicit path and rejects a pack naming B, even if B is newer.
   Acceptance: both packs survive unchanged and no global latest is the default.
3. **Same task, new checkpoint:** A's replacement pack records which A pack it
   supersedes, and preserves that old file. Acceptance: unique new path, old bytes
   unchanged; B's pack is never superseded as a side effect.
4. **Stale accepted baseline:** A pack records a previously accepted draft, but
   the current request names a newer accepted baseline. Acceptance: the reader
   keeps both evidence references, continues from the newer baseline, verifies
   needed live state and does not repeat a release or other gated action from an
   old next-action line.
5. **Legacy ambiguity:** A global latest pointer names B while the user asks for
   A, or candidates lack task identity. Acceptance: no silent pickup. The reader
   identifies the mismatch and requests the exact task/path if it cannot resolve
   selection from current authority. A verified unique legacy A pack remains
   readable without rewriting or deleting it.
