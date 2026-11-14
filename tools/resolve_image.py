# (c) 2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

"""Picks the image tag for a lab node and prints it.

Usage:
  python tools/resolve_image.py REGISTRY VERSION

REGISTRY is the image path without a tag, e.g. ghcr.io/nokia/srlinux. A VERSION without a patch
release, e.g. 26.10, picks the newest patch release in the registry (26.10.1 for SR Linux,
26.10.R1 for SR OS); any other VERSION is used as is. The chosen image goes to stderr, the tag to
stdout.
"""

import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

MINOR_RE = re.compile(r'^\d+\.\d+$')
CHALLENGE_RE = re.compile(r'(\w+)="([^"]*)"')
NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')
TIMEOUT = 30
# Verify like docker and curl do: Python 3.13+ also rejects TLS-inspecting proxy CAs
# that lack the critical Basic Constraints extension.
CONTEXT = ssl.create_default_context()
CONTEXT.verify_flags &= ~getattr(ssl, 'VERIFY_X509_STRICT', 0)


def split_image(registry):
    """(host, repository) of an image path; Docker Hub when the path has no registry host."""
    first, slash, rest = registry.partition('/')
    if slash and ('.' in first or ':' in first or first == 'localhost'):
        return first, rest
    return 'registry-1.docker.io', registry if '/' in registry else 'library/' + registry


def _token(challenge):
    """Anonymous pull token for a 'Bearer realm=...,service=...,scope=...' challenge."""
    params = dict(CHALLENGE_RE.findall(challenge))
    realm = params.pop('realm')
    url = realm + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=TIMEOUT, context=CONTEXT) as response:
        body = json.load(response)
    return body.get('token') or body['access_token']


def list_tags(registry):
    host, repository = split_image(registry)
    url = 'https://%s/v2/%s/tags/list?n=1000' % (host, repository)
    headers, tags = {}, []
    while url:
        request = urllib.request.Request(url, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=TIMEOUT, context=CONTEXT)
        except urllib.error.HTTPError as e:
            challenge = e.headers.get('WWW-Authenticate', '')
            if e.code != 401 or headers or not challenge.startswith('Bearer '):
                raise
            headers = {'Authorization': 'Bearer ' + _token(challenge[len('Bearer '):])}
            continue
        with response:
            tags += json.load(response).get('tags') or []
            link = NEXT_RE.search(response.headers.get('Link', ''))
        url = urllib.parse.urljoin(url, link.group(1)) if link else None
    return tags


def newest_patch(tags, version):
    """Newest '<version>.<n>' or '<version>.R<n>' tag, None when there is none."""
    patch_re = re.compile(r'^%s\.R?(\d+)$' % re.escape(version))
    patches = [(int(m.group(1)), tag) for tag in tags for m in [patch_re.match(tag)] if m]
    return max(patches)[1] if patches else None


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    registry, version = argv
    if not MINOR_RE.match(version):
        print('Lab image: %s:%s' % (registry, version), file=sys.stderr)
        print(version)
        return 0
    try:
        tag = newest_patch(list_tags(registry), version)
    except (OSError, ValueError, KeyError) as e:
        sys.exit('Cannot list the tags of %s: %s' % (registry, e))
    if tag is None:
        sys.exit('No %s patch release in %s' % (version, registry))
    print('Lab image: %s:%s (newest %s patch release)' % (registry, tag, version), file=sys.stderr)
    print(tag)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
