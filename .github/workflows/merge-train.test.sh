#!/bin/sh
# Contract test for #31: merge-train.yml must not poll on a schedule while
# queue:ready sees no real traffic. Re-enabling a schedule (or any trigger)
# is fine once the label is actually adopted as an event trigger — this
# guards the *pairing*, not the trigger forever. See merge-train.yml's
# header for the full rationale (CLAUDE.md §13, bound the ceiling).
#
# Run directly: sh .github/workflows/merge-train.test.sh

set -eu

workflow_dir="$(cd "$(dirname "$0")" && pwd)"
train="$workflow_dir/merge-train.yml"

fail=0

assert() {
  desc="$1"
  cond="$2"
  if [ "$cond" = "0" ]; then
    printf 'ok: %s\n' "$desc"
  else
    printf 'FAIL: %s\n' "$desc"
    fail=1
  fi
}

# 1. No schedule: trigger — the property this issue exists to fix.
if grep -qE '^\s*schedule:' "$train"; then
  assert 'merge-train.yml declares no schedule: trigger' 1
else
  assert 'merge-train.yml declares no schedule: trigger' 0
fi

# 2. workflow_dispatch stays — the mechanism must remain manually testable.
if grep -qE '^\s*workflow_dispatch:' "$train"; then
  assert 'merge-train.yml keeps workflow_dispatch' 0
else
  assert 'merge-train.yml keeps workflow_dispatch' 1
fi

# 3. queue:ready is not (yet) wired to any event trigger elsewhere in
# .github/workflows — the condition under which #1 is allowed to hold. If a
# future PR adds an event-triggered advance (pull_request: types: [labeled],
# push: branches: [main]) that reacts to queue:ready, this line should be
# updated deliberately alongside it, not left to drift silently.
event_triggered=0
for f in "$workflow_dir"/*.yml; do
  case "$(basename "$f")" in
    merge-train.yml|queue-stall-alert.yml) continue ;;
  esac
  if grep -qE '^\s*-?\s*types:\s*\[.*labeled.*\]' "$f" && grep -q 'queue:ready' "$f"; then
    event_triggered=1
    printf 'FAIL: %s wires an event trigger to queue:ready — merge-train.yml assumes it does not\n' "$(basename "$f")"
  fi
done
assert 'queue:ready has no event trigger wired elsewhere' "$event_triggered"

# 4. Live check, best-effort: no open PR currently carries queue:ready. This
# is the actual claim the schedule removal rests on — assert it against the
# real repo, not just the files, per CLAUDE.md §7. Skips cleanly (not a
# failure) when gh isn't available/authenticated, e.g. outside CI.
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  open_labeled="$(gh pr list --state open --label queue:ready --json number --jq 'length' 2>/dev/null || echo '')"
  if [ -n "$open_labeled" ]; then
    assert "no open PR carries queue:ready (found: $open_labeled)" "$([ "$open_labeled" = "0" ] && echo 0 || echo 1)"
  else
    echo "skip: could not query gh pr list (no repo context or API error) — not scored"
  fi
else
  echo "skip: gh not available/authenticated — live queue:ready check not run"
fi

exit "$fail"
