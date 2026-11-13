# Testing Infrastructure

This directory contains the test automation for the OpenConfig Ansible Collection.

## Workflows

- `ci.yml` - the test suites of `../test-matrix.yml` for pull requests, pushes and weekly
- `docs.yml` - builds the MkDocs site and publishes it to GitHub Pages
- `release.yml` - builds, smoke-tests and publishes the collection for a GitHub release

`ci.yml`, `../scripts/matrix.py`, `../scripts/summary.py` and `../../tests/run.sh` are copied
unchanged from the nokia-steward test pattern (version 1, maintained in nokia-steward-validator).
Change the test matrix, not these files.

## Test matrix

`../test-matrix.yml` lists suites, cases and versions (see the file header). Each case runs
`make test-setup` and `make test-<suite>` with `ANSIBLE_VERSION`, `SROS_VERSION`,
`SRL_VERSION` and `REGISTRY` where applicable. To add a version, add a row under `cases`.
`make test` runs lab-free suites locally.

The integration suites test one platform each, in a single-node lab with its own playbook list:
`integration-sros` uses `tests/sros.clab.yml` and `tests/playbooks-sros.yml`,
`integration-srlinux` uses `tests/srlinux.clab.yml` and `tests/playbooks-srlinux.yml`.
They need containerlab 0.83.0 or newer.

Each integration case names the image path it pulls, without the tag, as `registry` (for
example `ghcr.io/nokia/srlinux` or `registry.srlinux.dev/pub/nokia_srsim`). A release without a
patch number, such as `26.10`, runs the newest patch release in that registry at test time:
`tools/resolve_image.py` reads the registry's tag list, and the job log shows the image it picked
(`Lab image: ...`). Run locally with, for example,
`make test-integration-srlinux SRL_VERSION=26.7 REGISTRY=ghcr.io/nokia/srlinux`. GitHub runners
cannot reach `registry.srlinux.dev`, so the SR Linux cases use `ghcr.io/nokia/srlinux`.

## Where the integration cases run

`integration-srlinux` runs on GitHub, as the SR Linux image needs no license.

`integration-sros` needs the SR OS simulator license. GitHub runs it only when the repository
has an `SRSIM_LICENSE` secret. Otherwise the job summary lists those cases as "not run on
GitHub, needs srsim", and a maintainer runs them with nokia-steward-validator, which posts the
results to the pull request (after the `ready-for-validation` label; the result shows as
`validation-passed` or `validation-failed`) or to an issue for `main`.
