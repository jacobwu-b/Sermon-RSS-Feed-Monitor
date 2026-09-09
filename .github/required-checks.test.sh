#!/bin/sh
# Contract test for #34: required-checks.json's `checks` list must equal the
# set of ENABLED job `name:` values in ci.yml (a job under `if: false`
# reports no check run, so it must be excluded). This is the property
# required-checks.json's own note asserts in prose; this test asserts it as
# code so a future rename of a job or an edit to the checks list can't drift
# from the other silently. See CLAUDE.md §7 (wiring gets a contract test on
# the config's effect) and docs/decisions/0001-consolidate-ci-static-checks.md.
#
# Run directly: sh .github/required-checks.test.sh

set -eu

dir="$(cd "$(dirname "$0")" && pwd)"
checks_json="$dir/required-checks.json"
ci_yml="$dir/workflows/ci.yml"

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

want="$(jq -r '.checks[]' "$checks_json" | sort)"

# Enabled job names: every job's `name:` value, excluding any job whose block
# contains `if: false` before the next top-level (2-space-indented) job key.
got="$(python3 - "$ci_yml" <<'PY'
import re, sys, yaml

with open(sys.argv[1]) as f:
    doc = yaml.safe_load(f)

names = []
for job in doc["jobs"].values():
    if job.get("if") == False:  # noqa: E712 - YAML bool, not Python
        continue
    names.append(job["name"])

print("\n".join(sorted(names)))
PY
)"

if [ "$want" = "$got" ]; then
  assert "required-checks.json matches ci.yml's enabled job names" 0
else
  printf 'want:\n%s\n\ngot:\n%s\n' "$want" "$got" >&2
  assert "required-checks.json matches ci.yml's enabled job names" 1
fi

exit "$fail"
