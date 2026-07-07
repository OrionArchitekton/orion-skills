#!/usr/bin/env bash
# Human-in-the-loop reproduction loop (vendored from mattpocock/skills
# diagnosing-bugs). Last resort when a human must click but the loop should
# still be STRUCTURED: the agent runs the script, the user follows prompts,
# captured output feeds back to the agent.
#
# Copy this file, edit the steps below, and run it:
#   bash hitl-loop.template.sh
#
# Helpers:
#   step "<instruction>"        show instruction, wait for Enter
#   capture VAR "<question>"    show question, read response into VAR
#
# Captured values print as KEY=VALUE at the end for the agent to parse.

set -euo pipefail

step() {
  printf '\n>>> %s\n' "$1"
  read -r -p "    [Enter when done] " _
}

capture() {
  local var="$1" question="$2" answer
  printf '\n>>> %s\n' "$question"
  read -r -p "    > " answer
  printf -v "$var" '%s' "$answer"
}

# --- edit below ---------------------------------------------------------

step "Open the app and reproduce the reported scenario."

capture ERRORED "Did the failure occur? (y/n)"

capture ERROR_MSG "Paste the exact error / wrong output (or 'none'):"

# --- edit above ---------------------------------------------------------

printf '\n--- Captured ---\n'
printf 'ERRORED=%s\n' "$ERRORED"
printf 'ERROR_MSG=%s\n' "$ERROR_MSG"
