#!/usr/bin/env bash
#
# Runs ansible-test against this checkout.
#
# ansible-test needs the collection at .../ansible_collections/nokia/openconfig.
# If the checkout already has that layout (as in CI), tests run in place.
# Otherwise the working tree, including the generated *_pb2.py files, is
# copied to a staging directory first.
#
# Usage: tools/ansible_test.sh units|sanity [ansible-test options]
#   e.g. tools/ansible_test.sh units --python 3.13
#
# Environment:
#   STAGE   staging directory (default: ${TMPDIR:-/tmp}/nokia-openconfig-ansible-test)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 units|sanity [ansible-test options]" >&2
  exit 2
fi

if ! command -v ansible-test >/dev/null; then
  echo "ansible-test not found; install ansible-core and requirements-dev.txt" >&2
  exit 1
fi

if [[ ! -f "$ROOT/plugins/module_utils/proto/gnmi_pb2.py" ]]; then
  echo "Generated protobuf modules missing, running tools/build_openconfig_protos.sh" >&2
  "$ROOT/tools/build_openconfig_protos.sh"
fi

case "$ROOT" in
  */ansible_collections/nokia/openconfig)
    COLLECTION="$ROOT"
    ;;
  *)
    STAGE="${STAGE:-${TMPDIR:-/tmp}/nokia-openconfig-ansible-test}"
    COLLECTION="$STAGE/ansible_collections/nokia/openconfig"
    mkdir -p "$COLLECTION"
    rsync -a --delete \
      --exclude .git --exclude .github --exclude .venv --exclude .tmp --exclude dist --exclude tests/output \
      --exclude '__pycache__' --exclude '*.tar.gz' \
      --exclude 'tests/clab-*' --exclude tests/license.txt \
      "$ROOT/" "$COLLECTION/"
    if [[ "$1" == "sanity" ]]; then
      # Generated code is gitignored, so sanity in a git checkout (CI) never sees it.
      find "$COLLECTION/plugins/module_utils/proto" -name '*_pb2*.py' -delete
    fi
    ;;
esac

cd "$COLLECTION"
status=0
ansible-test "$@" --color no || status=$?

if [[ "$COLLECTION" != "$ROOT" && -d "$COLLECTION/tests/output" ]]; then
  mkdir -p "$ROOT/tests/output"
  rsync -a "$COLLECTION/tests/output/" "$ROOT/tests/output/"
fi
exit $status
