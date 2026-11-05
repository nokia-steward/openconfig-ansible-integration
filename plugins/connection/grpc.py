# (c) 2020-2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
---
author:
  - "Hans Thienpondt (@HansThienpondt)"
  - "Sven Wisotzky (@wisotzky)"
name: grpc
short_description: Persistent gRPC connection for OpenConfig gRPC services
description:
  - Provides a persistent gRPC channel, including TLS, to devices that
    implement OpenConfig gRPC services.
  - Binds the gNMI service (Capabilities, Get, Set, Subscribe) as defined by
    gNMI specification 0.10.0, including the Depth, Commit (commit confirmed)
    and ConfigSubscription extensions.
  - Binds OpenConfig gNOI services supported on Nokia SR OS and SR Linux
    (System, File, OS, FactoryReset, Healthz, BGP and Packet Link Qualification).
  - Binds OpenConfig gNSI services supported on Nokia SR Linux
    (Authz, Certz, Pathz and Credentialz).
  - OpenConfig gNMI specification
    U(https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)
  - Option names follow P(ansible.netcommon.grpc#connection) and the persistent
    connection conventions of C(ansible.netcommon).
version_added: 2.0.0
requirements:
  - grpcio >= 1.59.0
  - protobuf >= 3.20.3 (>= 5.29.0 on Python 3.14)
options:
  host:
    description:
      - Target host FQDN or IP address to establish gRPC connection.
      - IPv6 addresses can be given with or without brackets, for example C(2001:db8::1) or C([2001:db8::1]).
    default: inventory_hostname
    vars:
      - name: inventory_hostname
      - name: ansible_host
  port:
    type: int
    description:
      - TCP port of the gRPC server on the remote device.
    default: 57400
    ini:
      - section: defaults
        key: remote_port
    env:
      - name: ANSIBLE_REMOTE_PORT
    vars:
      - name: ansible_port
  remote_user:
    description:
      - Username used for gRPC authentication (metadata C(username)).
      - Can be configured from the CLI via the C(--user) or C(-u) options.
    ini:
      - section: defaults
        key: remote_user
    env:
      - name: ANSIBLE_REMOTE_USER
    vars:
      - name: ansible_user
  password:
    description:
      - Password used for gRPC authentication (metadata C(password)).
    vars:
      - name: ansible_password
      - name: ansible_ssh_pass
  private_key_file:
    type: path
    description:
      - PEM encoded private key used for mutual TLS client authentication.
    ini:
      - section: grpc_connection
        key: private_key_file
    env:
      - name: ANSIBLE_PRIVATE_KEY_FILE
    vars:
      - name: ansible_private_key_file
  root_certificates_file:
    type: path
    description:
      - PEM encoded root certificates used to verify the server certificate.
      - If no certificate option is set, an insecure (plain text) channel is
        used.
    ini:
      - section: grpc_connection
        key: root_certificates_file
    env:
      - name: ANSIBLE_ROOT_CERTIFICATES_FILE
    vars:
      - name: ansible_root_certificates_file
  certificate_chain_file:
    type: path
    description:
      - PEM encoded client certificate chain used for mutual TLS.
    ini:
      - section: grpc_connection
        key: certificate_chain_file
    env:
      - name: ANSIBLE_CERTIFICATE_CHAIN_FILE
    vars:
      - name: ansible_certificate_chain_file
  ssl_target_name_override:
    description:
      - Overrides the host name used to verify the server certificate
        (gRPC channel option C(grpc.ssl_target_name_override)).
      - Needed when the address used to connect differs from the subject or
        subjectAltName in the device certificate.
    ini:
      - section: grpc_connection
        key: ssl_target_name_override
    env:
      - name: ANSIBLE_GRPC_SSL_TARGET_NAME_OVERRIDE
    vars:
      - name: ansible_grpc_ssl_target_name_override
  validate_certs:
    type: boolean
    description:
      - When C(false), the server TLS certificate is trusted without a local CA
        (certificate pinning at connect time). A secure channel is still used.
      - Use only in lab environments. When C(true) (default), set
        C(root_certificates_file) to your CA bundle for production.
    default: true
    ini:
      - section: grpc_connection
        key: validate_certs
    env:
      - name: ANSIBLE_GRPC_VALIDATE_CERTS
    vars:
      - name: ansible_grpc_validate_certs
  gnmi_encoding:
    description:
      - Default gNMI encoding for Get, Set and Subscribe requests, either
        C(JSON) or C(JSON_IETF) (case-insensitive).
      - If not set, a Capabilities request is sent when the connection is
        established and JSON_IETF is preferred over JSON.
    ini:
      - section: grpc_connection
        key: gnmi_encoding
    env:
      - name: ANSIBLE_GNMI_ENCODING
    vars:
      - name: ansible_gnmi_encoding
  gnmi_origin:
    description:
      - Default origin of the gNMI paths of M(nokia.openconfig.gnmi_get),
        M(nokia.openconfig.gnmi_set) and M(nokia.openconfig.gnmi_subscribe),
        for example C(openconfig) or C(rfc7951).
      - Used when the task does not set the C(origin) option. Paths that name
        their origin, as in C(openconfig:/system), keep it.
      - Not set by default, so paths are sent without origin.
    version_added: 2.0.1
    ini:
      - section: grpc_connection
        key: gnmi_origin
    env:
      - name: ANSIBLE_GNMI_ORIGIN
    vars:
      - name: ansible_gnmi_origin
  grpc_channel_options:
    description:
      - Key/value pairs (dict) of gRPC channel options.
      - gRPC reference
        U(https://grpc.github.io/grpc/core/group__grpc__arg__keys.html)
      - A string is parsed as YAML/JSON, so the value can be set in ansible.cfg.
      - For responses larger than the gRPC default of 4 MB, set
        C(grpc.max_receive_message_length) to the limit in bytes, for example
        C(67108864) for 64 MB.
    ini:
      - section: grpc_connection
        key: grpc_channel_options
    vars:
      - name: ansible_grpc_channel_options
  grpc_environment:
    description:
      - Key/value pairs (dict) of environment variables to set for the process
        that holds the gRPC channel. A value of C(0), C(null) or empty string
        removes the variable.
      - The standard Ansible C(environment) keyword cannot be used, because it
        is not passed to the persistent connection process.
      - Use C(GRPC_VERBOSITY) and C(GRPC_TRACE) for gRPC logging,
        C(HTTPS_PROXY) for proxy settings, and C(GRPC_SSL_CIPHER_SUITES) if the
        default TLS ciphers do not match the server.
      - A string is parsed as YAML/JSON, so the value can be set in ansible.cfg.
    ini:
      - section: grpc_connection
        key: grpc_environment
    vars:
      - name: ansible_grpc_environment
  persistent_connect_timeout:
    type: int
    description:
      - Time in seconds to wait for the persistent connection to be
        established.
    default: 5
    ini:
      - section: persistent_connection
        key: connect_timeout
    env:
      - name: ANSIBLE_PERSISTENT_CONNECT_TIMEOUT
    vars:
      - name: ansible_connect_timeout
  persistent_command_timeout:
    type: int
    description:
      - Time in seconds to wait for a gRPC response. Also used as gRPC
        deadline for Capabilities, Get and Set.
    default: 300
    ini:
      - section: persistent_connection
        key: command_timeout
    env:
      - name: ANSIBLE_PERSISTENT_COMMAND_TIMEOUT
    vars:
      - name: ansible_command_timeout
  persistent_log_messages:
    type: boolean
    description:
      - Log gRPC requests and responses to the Ansible C(log_path).
      - Messages are not redacted.
    default: false
    ini:
      - section: persistent_connection
        key: log_messages
    env:
      - name: ANSIBLE_PERSISTENT_LOG_MESSAGES
    vars:
      - name: ansible_persistent_log_messages
"""

import os
import re
import socket
import ssl
import stat
import sys
import tempfile
import threading

import yaml

# Keep in sync with requirements.txt. protobuf releases before 5.29 cannot
# be imported on Python 3.14.
GRPCIO_MIN = '1.59.0'
PROTOBUF_MIN = '5.29.0' if sys.version_info >= (3, 14) else '3.20.3'

# Broken installations raise more than ImportError (for example TypeError
# from protobuf C extensions), so every failure is kept for the error message.
GRPC_IMPORT_ERROR = None
try:
    import grpc
except Exception as exc:  # pylint: disable=broad-exception-caught
    GRPC_IMPORT_ERROR = exc

PROTOBUF_IMPORT_ERROR = None
try:
    from google.protobuf import __version__ as PROTOBUF_VERSION
    from google.protobuf import json_format
except Exception as exc:  # pylint: disable=broad-exception-caught
    PROTOBUF_IMPORT_ERROR = exc

GNMI_PB2_IMPORT_ERROR = None
try:
    from ansible_collections.nokia.openconfig.plugins.module_utils.proto import gnmi_pb2
    from ansible_collections.nokia.openconfig.plugins.module_utils.proto import gnmi_pb2_grpc
except Exception as exc:  # pylint: disable=broad-exception-caught
    GNMI_PB2_IMPORT_ERROR = exc

GNOI_IMPORT_ERROR = None
try:
    from ansible_collections.nokia.openconfig.plugins.module_utils import gnoi as gnoi_util
except Exception as exc:  # pylint: disable=broad-exception-caught
    GNOI_IMPORT_ERROR = exc

GNSI_IMPORT_ERROR = None
try:
    from ansible_collections.nokia.openconfig.plugins.module_utils import gnsi as gnsi_util
except Exception as exc:  # pylint: disable=broad-exception-caught
    GNSI_IMPORT_ERROR = exc

try:
    from cryptography import x509
    HAS_CRYPTOGRAPHY = True
except Exception:  # pylint: disable=broad-exception-caught
    HAS_CRYPTOGRAPHY = False

HAS_GRPC = GRPC_IMPORT_ERROR is None
HAS_PROTOBUF = PROTOBUF_IMPORT_ERROR is None
HAS_GNMI_PB2 = GNMI_PB2_IMPORT_ERROR is None
HAS_GNOI = GNOI_IMPORT_ERROR is None
HAS_GNSI = GNSI_IMPORT_ERROR is None

from ansible.errors import AnsibleConnectionFailure, AnsibleError
from ansible.module_utils.common.text.converters import to_text
from ansible.plugins.connection import NetworkConnectionBase
from ansible.plugins.connection import ensure_connect

from ansible_collections.nokia.openconfig.plugins.module_utils import gnmi
from ansible_collections.nokia.openconfig.plugins.module_utils import gnmi_ext


def _as_dict(value, name):
    if value in (None, ''):
        return {}
    if isinstance(value, str):
        try:
            value = yaml.safe_load(value)
        except yaml.YAMLError as exc:
            raise AnsibleConnectionFailure("%s is not valid YAML/JSON: %s" % (name, exc))
    if not isinstance(value, dict):
        raise AnsibleConnectionFailure("%s must be a dict" % name)
    return value


def _version(text):
    return tuple(int(part) for part in re.findall(r'\d+', text)[:3])


def dependency_error():
    """Returns why the Python requirements are unusable, or None."""
    problems = []
    if not HAS_GRPC:
        problems.append('grpcio cannot be imported (%s)' % GRPC_IMPORT_ERROR)
    elif _version(grpc.__version__) < _version(GRPCIO_MIN):
        problems.append('grpcio %s is too old' % grpc.__version__)
    if not HAS_PROTOBUF:
        problems.append('protobuf cannot be imported (%s)' % PROTOBUF_IMPORT_ERROR)
    elif _version(PROTOBUF_VERSION) < _version(PROTOBUF_MIN):
        problems.append('protobuf %s is too old' % PROTOBUF_VERSION)
    if problems:
        return ("The nokia.openconfig.grpc connection requires grpcio>=%s and protobuf>=%s: %s. Install them "
                "into the Python that runs Ansible: %s -m pip install 'grpcio>=%s' 'protobuf>=%s'"
                % (GRPCIO_MIN, PROTOBUF_MIN, '; '.join(problems), sys.executable, GRPCIO_MIN, PROTOBUF_MIN))
    if not HAS_GNMI_PB2:
        missing = getattr(GNMI_PB2_IMPORT_ERROR, 'name', None) or ''
        if isinstance(GNMI_PB2_IMPORT_ERROR, ImportError) and missing.endswith(('_pb2', '_pb2_grpc')):
            return ("The generated gNMI protobuf modules are missing from nokia.openconfig (%s). Install a "
                    "released collection, or run tools/build_openconfig_protos.sh in a checkout." % GNMI_PB2_IMPORT_ERROR)
        return ("The gNMI protobuf modules of nokia.openconfig cannot be imported with protobuf %s and "
                "grpcio %s: %s" % (PROTOBUF_VERSION, grpc.__version__, GNMI_PB2_IMPORT_ERROR))
    if not HAS_GNOI:
        missing = getattr(GNOI_IMPORT_ERROR, 'name', None) or ''
        if isinstance(GNOI_IMPORT_ERROR, ImportError) and missing.endswith(('_pb2', '_pb2_grpc')):
            return ("The generated gNOI protobuf modules are missing from nokia.openconfig (%s). Run "
                    "tools/build_openconfig_protos.sh in a checkout." % GNOI_IMPORT_ERROR)
        return ("The gNOI modules of nokia.openconfig cannot be imported: %s" % GNOI_IMPORT_ERROR)
    if not getattr(gnoi_util, 'HAS_GNOI_PROTOS', True):
        return ("The generated gNOI protobuf modules are missing from nokia.openconfig. Install a "
                "released collection, or run tools/build_openconfig_protos.sh in a source checkout.")
    if not HAS_GNSI:
        missing = getattr(GNSI_IMPORT_ERROR, 'name', None) or ''
        if isinstance(GNSI_IMPORT_ERROR, ImportError) and missing.endswith(('_pb2', '_pb2_grpc')):
            return ("The generated gNSI protobuf modules are missing from nokia.openconfig (%s). Run "
                    "tools/build_openconfig_protos.sh in a checkout." % GNSI_IMPORT_ERROR)
        return ("The gNSI modules of nokia.openconfig cannot be imported: %s" % GNSI_IMPORT_ERROR)
    if not getattr(gnsi_util, 'HAS_GNSI_PROTOS', True):
        return ("The generated gNSI protobuf modules are missing from nokia.openconfig. Install a "
                "released collection, or run tools/build_openconfig_protos.sh in a source checkout.")
    return None


def _read_file(path, name):
    if not path:
        return None
    path = os.path.expanduser(path)
    try:
        with open(path, 'rb') as f:
            return f.read()
    except (IOError, OSError) as exc:
        raise AnsibleConnectionFailure("Failed to read %s '%s': %s" % (name, path, exc))


def _wildcard_target(name):
    """Converts a valid left-most wildcard DNS name (*.example.com) into a concrete host name."""
    if name.startswith('*.') and len(name) > 2 and '*' not in name[2:]:
        return 'host.' + name[2:]
    return None


def _cert_target_name(der):
    """Extracts a target name from a DER X.509 certificate for ssl_target_name_override."""
    if not der or not HAS_CRYPTOGRAPHY:
        return None
    try:
        cert = x509.load_der_x509_certificate(der)
    except ValueError:
        return None
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        dns_names = [n for n in san.get_values_for_type(x509.DNSName) if n]
        for name in dns_names:
            if '*' not in name:
                return name
        for name in dns_names:
            target = _wildcard_target(name)
            if target and '.' in name[2:]:
                return target
        for name in dns_names:
            target = _wildcard_target(name)
            if target:
                return target
        for addr in san.get_values_for_type(x509.IPAddress):
            return str(addr)
    except x509.ExtensionNotFound:
        pass
    for attr in cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME):
        val = attr.value
        if val:
            if '*' not in val:
                return val
            target = _wildcard_target(val)
            if target:
                return target
    return None


def _peer_certificate_pem(host, port, server_name, timeout):
    """Returns PEM and target name from the TLS server without verifying the chain."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, int(port)), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=server_name or host) as ssock:
            der = ssock.getpeercert(True)
            if not der:
                return None, None
            pem = ssl.DER_cert_to_PEM_cert(der)
            cn = _cert_target_name(der)
            if not cn:
                for rdn in (ssock.getpeercert() or {}).get('subject', ()):
                    for key, value in rdn:
                        if key == 'commonName':
                            cn = value
                            break
            return pem, cn


class Connection(NetworkConnectionBase):
    """
    Persistent gRPC connection for OpenConfig gRPC services.

    A single gRPC channel is shared by all service stubs. Modules call the
    public methods (gnmiCapabilities, gnmiGet, gnmiSet, gnmiSubscribe)
    through the persistent connection socket.
    """

    transport = "nokia.openconfig.grpc"
    has_pipelining = True

    def __init__(self, play_context, new_stdin=None, *args, **kwargs):
        super(Connection, self).__init__(play_context, new_stdin, *args, **kwargs)

        self._task_uuid = to_text(kwargs.get("task_uuid", ""))

        error = dependency_error()
        if error:
            raise AnsibleError(error)

        self._connected = False
        self._channel = None
        self._stubs = {}
        self._encoding = None
        self._gnmi_version = None

    # -------------------------------------------------------------------------

    def _connect(self):
        """
        Establishes the gRPC channel and binds the service stubs.

        If no gnmi_encoding is configured, a Capabilities request determines
        the encoding (JSON_IETF preferred, JSON as fallback).
        """
        if self._connected:
            self.queue_message('vvvv', 'gRPC connection to host %s already exists' % self._target)
            return

        for key, value in _as_dict(self.get_option('grpc_environment'), 'grpc_environment').items():
            if value:
                os.environ[key] = str(value)
            else:
                os.environ.pop(key, None)

        self._login_credentials = [
            ('username', self.get_option('remote_user') or ''),
            ('password', self.get_option('password') or ''),
        ]

        host = self.get_option('host').strip('[]')
        port = self.get_option('port') or 57400
        self._target = ('[%s]:%d' if ':' in host else '%s:%d') % (host, port)

        certs = {}
        root = _read_file(self.get_option('root_certificates_file'), 'root_certificates_file')
        chain = _read_file(self.get_option('certificate_chain_file'), 'certificate_chain_file')
        key = _read_file(self.get_option('private_key_file'), 'private_key_file')
        validate_certs = self.get_option('validate_certs')
        if validate_certs is None:
            validate_certs = True

        options = _as_dict(self.get_option('grpc_channel_options'), 'grpc_channel_options')
        override = self.get_option('ssl_target_name_override')

        if not validate_certs and not root:
            timeout = self.get_option('persistent_connect_timeout') or 5
            try:
                pem, cn = _peer_certificate_pem(host, port, override or host, timeout)
            except (OSError, ssl.SSLError) as exc:
                raise AnsibleConnectionFailure("Failed to read TLS certificate from %s:%s: %s" % (host, port, exc))
            root = pem.encode() if isinstance(pem, str) else pem
            self.queue_message('vvv', 'Trusting server TLS certificate for %s (validate_certs=false)' % self._target)
            if not override and cn:
                override = cn
                self.queue_message('vvv', 'Using grpc.ssl_target_name_override=%s from server certificate' % cn)

        if root:
            certs['root_certificates'] = root
        if chain:
            certs['certificate_chain'] = chain
        if key:
            certs['private_key'] = key

        if override:
            options['grpc.ssl_target_name_override'] = override
        options = list(options.items()) or None

        if certs or not validate_certs:
            if not certs.get('root_certificates') and not validate_certs:
                raise AnsibleConnectionFailure("validate_certs=false could not obtain a server certificate")
            self.queue_message('vvv', 'Starting secure gRPC connection to %s' % self._target)
            creds = grpc.ssl_channel_credentials(**certs)
            self._channel = grpc.secure_channel(self._target, creds, options=options)
        else:
            self.queue_message('vvv', 'Starting insecure gRPC connection to %s' % self._target)
            self._channel = grpc.insecure_channel(self._target, options=options)

        try:
            grpc.channel_ready_future(self._channel).result(timeout=self.get_option('persistent_connect_timeout'))
        except grpc.FutureTimeoutError:
            self._channel.close()
            raise AnsibleConnectionFailure("Failed to connect to gRPC server %s within %ss" % (
                self._target, self.get_option('persistent_connect_timeout')))

        self._stubs['gnmi'] = gnmi_pb2_grpc.gNMIStub(self._channel)

        self._encoding = self.get_option('gnmi_encoding')
        if self._encoding:
            self._encoding = self._encoding.upper()
            if self._encoding not in ('JSON_IETF', 'JSON'):
                raise AnsibleConnectionFailure("Incompatible encoding '%s' requested (JSON or JSON_IETF)" % self._encoding)
        else:
            self.queue_message('vvvv', 'Run CapabilityRequest()')
            response = self._call('Capabilities', gnmi_pb2.CapabilityRequest())
            self._gnmi_version = response.gNMI_version
            if gnmi_pb2.Encoding.Value('JSON_IETF') in response.supported_encodings:
                self._encoding = 'JSON_IETF'
            elif gnmi_pb2.Encoding.Value('JSON') in response.supported_encodings:
                self._encoding = 'JSON'
            else:
                raise AnsibleConnectionFailure("No compatible supported encoding found (JSON or JSON_IETF)")

        self._connected = True
        self.queue_message('vvv', 'gRPC connection to %s established (encoding %s)' % (self._target, self._encoding))

    @property
    def _timeout(self):
        return self.get_option('persistent_command_timeout')

    def close(self):
        """Closes the gRPC channel."""
        if getattr(self, '_channel', None) is not None:
            self.queue_message('vvvv', "Closing gRPC connection to target host")
            self._channel.close()
            self._channel = None
        super(Connection, self).close()

    # -------------------------------------------------------------------------

    def _rpc_error(self, exc):
        if hasattr(exc, 'code') and hasattr(exc, 'details'):
            return AnsibleConnectionFailure("gRPC %s: %s" % (exc.code().name, exc.details()))
        return AnsibleConnectionFailure(to_text(exc))

    def _call(self, method, request):
        if self.get_option('persistent_log_messages'):
            self.queue_message('log', 'gNMI %s request: %s' % (method, json_format.MessageToJson(request)))
        try:
            response = getattr(self._stubs['gnmi'], method)(
                request, metadata=self._login_credentials, timeout=self._timeout)
        except grpc.RpcError as exc:
            raise self._rpc_error(exc)
        if self.get_option('persistent_log_messages'):
            self.queue_message('log', 'gNMI %s response: %s' % (method, json_format.MessageToJson(response)))
        return response

    def _parse(self, data, message):
        try:
            return json_format.ParseDict(data, message)
        except json_format.ParseError as exc:
            raise AnsibleConnectionFailure("Invalid gNMI request: %s" % exc)

    @staticmethod
    def _extensions(*items):
        return [item for item in items if item]

    def _origin(self, origin):
        """The origin of the task, or the gnmi_origin of the connection. An
        empty string sends paths without origin."""
        if origin is None:
            return self.get_option('gnmi_origin') or None
        return origin or None

    # -------------------------------------------------------------------------

    @ensure_connect
    def gnmiCapabilities(self):
        """
        Executes a gNMI Capabilities request.

        Returns:
            dict: CapabilityResponse in JSON (camelCase) form
        """
        response = self._call('Capabilities', gnmi_pb2.CapabilityRequest())
        return json_format.MessageToDict(response)

    @ensure_connect
    def gnmiGet(self, path=None, prefix=None, target=None, model=None, type=None,
                encoding=None, depth=None, values_only=False, origin=None):
        """
        Executes a gNMI Get request.

        Returns:
            dict: output (merged object tree, or list of values for
                  values_only) and extensions
        """
        try:
            data = gnmi.build_get_request(path=path, prefix=prefix, target=target, model=model,
                                          type=type, encoding=encoding or self._encoding,
                                          origin=self._origin(origin))
            data['extension'] = self._extensions(gnmi_ext.depth(depth))
        except gnmi.GnmiError as exc:
            raise AnsibleConnectionFailure(to_text(exc))

        response = json_format.MessageToDict(self._call('Get', self._parse(data, gnmi_pb2.GetRequest())))
        notifications = response.get('notification', [])
        try:
            if values_only:
                output = gnmi.notification_values(notifications)
            else:
                output = gnmi.merge_notifications(notifications)
        except gnmi.GnmiError as exc:
            raise AnsibleConnectionFailure(to_text(exc))
        return {'output': output, 'extensions': gnmi_ext.parse_extensions(response.get('extension'))}

    @ensure_connect
    def gnmiSet(self, prefix=None, target=None, update=None, replace=None, delete=None,
                encoding=None, commit_id=None, commit_request=False, commit_confirm=False,
                commit_cancel=False, rollback_duration=None, dry_run=False, origin=None):
        """
        Executes a gNMI Set request.

        Confirmed commit uses the Commit extension, built from commit_id,
        commit_request, commit_confirm, commit_cancel and rollback_duration.

        Returns:
            dict: output (SetResponse) and extensions, or request if dry_run
        """
        try:
            data = gnmi.build_set_request(prefix=prefix, target=target, update=update, replace=replace,
                                          delete=delete, encoding=encoding or self._encoding,
                                          origin=self._origin(origin))
            data['extension'] = self._extensions(gnmi_ext.commit_extension(
                commit_id, commit_request, commit_confirm, commit_cancel, rollback_duration))
        except gnmi.GnmiError as exc:
            raise AnsibleConnectionFailure(to_text(exc))

        request = self._parse(data, gnmi_pb2.SetRequest())
        if dry_run:
            return {'request': json_format.MessageToDict(request, preserving_proto_field_name=True)}

        response = json_format.MessageToDict(self._call('Set', request))
        return {
            'output': gnmi.simplify_set_response(response),
            'extensions': gnmi_ext.parse_extensions(response.get('extension')),
        }

    @ensure_connect
    def gnmiSubscribe(self, path=None, subscription=None, prefix=None, target=None, model=None,
                      mode='STREAM', stream_mode=None, sample_interval=None, heartbeat_interval=None,
                      suppress_redundant=None, updates_only=None, allow_aggregation=None, qos=None,
                      encoding=None, depth=None, config_subscription=False, duration=None, origin=None):
        """
        Executes a gNMI Subscribe request.

        ONCE returns the merged object tree. STREAM collects updates until
        duration (seconds) expires; with config_subscription and no duration
        it stops when the target reports sync-done with done set after the
        initial synchronization. POLL sends one Poll after the initial sync
        and returns both rounds.

        Returns:
            dict: output and extensions
        """
        mode = (mode or 'STREAM').upper()
        try:
            data = {
                'subscribe': gnmi.build_subscription_list(
                    path=path, subscription=subscription, prefix=prefix, target=target, model=model,
                    mode=mode, stream_mode=stream_mode, sample_interval=sample_interval,
                    heartbeat_interval=heartbeat_interval, suppress_redundant=suppress_redundant,
                    updates_only=updates_only, allow_aggregation=allow_aggregation, qos=qos,
                    encoding=encoding or self._encoding, origin=self._origin(origin)),
                'extension': self._extensions(
                    gnmi_ext.depth(depth),
                    gnmi_ext.config_subscription_start() if config_subscription else None),
            }
        except gnmi.GnmiError as exc:
            raise AnsibleConnectionFailure(to_text(exc))
        request = self._parse(data, gnmi_pb2.SubscribeRequest())

        until_done = duration is None and config_subscription and mode == 'STREAM'
        if duration is None:
            duration = max(self._timeout - 1, 1) if until_done else 20

        stop = threading.Event()
        poll = threading.Event()

        def requests():
            yield request
            if mode == 'POLL':
                poll.wait()
                if not stop.is_set():
                    yield gnmi_pb2.SubscribeRequest(poll=gnmi_pb2.Poll())
            stop.wait()

        if self.get_option('persistent_log_messages'):
            self.queue_message('log', 'gNMI Subscribe request: %s' % json_format.MessageToJson(request))

        raw = []
        extensions = []
        syncs = 0
        call = self._stubs['gnmi'].Subscribe(requests(), timeout=duration, metadata=self._login_credentials)
        try:
            for message in call:
                entry = json_format.MessageToDict(message)
                if entry.get('extension'):
                    extensions.extend(gnmi_ext.parse_extensions(entry['extension']))
                if until_done and syncs:
                    done = gnmi_ext.sync_done(entry.get('extension'))
                    if done and done.get('done'):
                        call.cancel()
                        break
                if entry.get('syncResponse'):
                    syncs += 1
                    if mode == 'ONCE' or (mode == 'POLL' and syncs == 2):
                        call.cancel()
                        break
                    if mode == 'POLL':
                        poll.set()
                    continue
                raw.append(entry)
        except grpc.RpcError as exc:
            if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                if mode != 'STREAM':
                    raise AnsibleConnectionFailure("gNMI %s subscription timed out after %ss" % (mode, duration))
            elif exc.code() != grpc.StatusCode.CANCELLED:
                raise self._rpc_error(exc)
        finally:
            stop.set()
            poll.set()

        try:
            if mode == 'ONCE':
                output = gnmi.merge_notifications(raw)
            else:
                output = [u for u in (gnmi.simplify_notification(e) for e in raw) if u]
        except gnmi.GnmiError as exc:
            raise AnsibleConnectionFailure(to_text(exc))
        return {'output': output, 'extensions': extensions}

    # -------------------------------------------------------------------------
    # gNOI
    # -------------------------------------------------------------------------

    def _gnoi_stub(self, service):
        service = service.replace('-', '_')
        key = 'gnoi.' + service
        if key not in self._stubs:
            if service not in gnoi_util.SERVICES:
                raise AnsibleConnectionFailure("Unknown gNOI service %r" % service)
            self._stubs[key] = gnoi_util.SERVICES[service][1](self._channel)
        return self._stubs[key]

    def _gnoi_stream_client(self, stub, rpc, iterator):
        try:
            if self.get_option('persistent_log_messages'):
                self.queue_message('log', 'gNOI %s client stream started' % rpc)
            response = getattr(stub, rpc)(iterator, metadata=self._login_credentials, timeout=self._timeout)
            if self.get_option('persistent_log_messages'):
                self.queue_message('log', 'gNOI %s response: %s' % (rpc, json_format.MessageToJson(response)))
            return json_format.MessageToDict(response)
        except grpc.RpcError as exc:
            raise self._rpc_error(exc)

    def _gnoi_stream_server(self, stub, rpc, request, save_to=None):
        try:
            if self.get_option('persistent_log_messages'):
                self.queue_message('log', 'gNOI %s request: %s' % (rpc, json_format.MessageToJson(request)))
            call = getattr(stub, rpc)(request, metadata=self._login_credentials, timeout=self._timeout)
        except grpc.RpcError as exc:
            raise self._rpc_error(exc)

        output = []
        digest = None
        handle = None
        tmp_path = None
        target_mode = None
        if save_to:
            save_to = os.path.expanduser(save_to)
            try:
                st = os.stat(save_to)
                if not stat.S_ISDIR(st.st_mode):
                    target_mode = stat.S_IMODE(st.st_mode)
            except OSError:
                umask = os.umask(0o077)
                os.umask(umask)
                target_mode = 0o666 & ~umask
            save_dir = os.path.dirname(os.path.abspath(save_to))
            try:
                handle = tempfile.NamedTemporaryFile(dir=save_dir, prefix='.gnoi_get_', delete=False)
                tmp_path = handle.name
            except (IOError, OSError) as exc:
                raise AnsibleConnectionFailure("Failed to open temporary file for '%s': %s" % (save_to, exc))

        try:
            for message in call:
                if self.get_option('persistent_log_messages'):
                    self.queue_message('log', 'gNOI %s stream: %s' % (rpc, json_format.MessageToJson(message)))
                field = message.WhichOneof('response') if message.DESCRIPTOR.oneofs_by_name.get('response') else None
                if handle is not None and field == 'contents':
                    handle.write(message.contents)
                if field == 'hash':
                    digest = json_format.MessageToDict(message.hash)
                elif 'hash' in message.DESCRIPTOR.fields_by_name and message.HasField('hash'):
                    digest = json_format.MessageToDict(message.hash)
                output.append(json_format.MessageToDict(message))
            if handle is not None:
                handle.close()
                handle = None
                if target_mode is not None:
                    os.chmod(tmp_path, target_mode)
                os.replace(tmp_path, save_to)
                tmp_path = None
        except grpc.RpcError as exc:
            raise self._rpc_error(exc)
        except (IOError, OSError) as exc:
            raise AnsibleConnectionFailure("Failed to write '%s': %s" % (save_to, exc))
        finally:
            if handle is not None:
                handle.close()
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        result = {'output': output}
        if digest is not None:
            result['hash'] = digest
        if save_to is not None:
            result['local_path'] = save_to
        return result

    def _gnoi_stream_both(self, stub, rpc, iterator):
        try:
            call = getattr(stub, rpc)(iterator, metadata=self._login_credentials, timeout=self._timeout)
            output = [json_format.MessageToDict(message) for message in call]
            return {'output': output}
        except grpc.RpcError as exc:
            raise self._rpc_error(exc)

    @ensure_connect
    def invokeGnoi(self, service, rpc, request=None, local_path=None, remote_path=None,
                   permissions=None, package_filename=None, package_version=None,
                   package_activate=False, os_version='', standby_supervisor=False, save_to=None):
        """
        Invokes a gNOI RPC on the target.

        Streams are built and drained here, so callers pass plain values:
        File.Put, System.SetPackage and OS.Install stream local_path in
        chunks; File.Get and other server-streaming RPCs return every
        response message (File.Get can also write the contents to save_to).

        service:
            system, file, os, factory_reset, healthz, bgp
        rpc:
            Proto RPC name (Ping, Time, Get, Put, ...)
        request:
            Request fields as a dict (protobuf JSON names).
        local_path / remote_path:
            Used by File.Put, File.Get, System.SetPackage and OS.Install.
        save_to:
            For File.Get, write streamed contents to this local path.
        """
        service = service.replace('-', '_')
        stub = self._gnoi_stub(service)
        key = (service, rpc)

        if key == ('file', 'Put'):
            if not local_path or not remote_path:
                raise AnsibleConnectionFailure("gNOI File.Put requires local_path and remote_path")
            iterator = gnoi_util.file_put_requests(remote_path, local_path, permissions=permissions)
            return {'output': self._gnoi_stream_client(stub, rpc, iterator)}

        if key == ('system', 'SetPackage'):
            if not local_path:
                raise AnsibleConnectionFailure("gNOI System.SetPackage requires local_path")
            iterator = gnoi_util.set_package_requests(
                local_path, package_name=package_filename, version=package_version, activate=package_activate)
            return {'output': self._gnoi_stream_client(stub, rpc, iterator)}

        if key == ('os', 'Install'):
            if not local_path:
                raise AnsibleConnectionFailure("gNOI OS.Install requires local_path")
            iterator = gnoi_util.os_install_requests(
                local_path, version=os_version, standby_supervisor=standby_supervisor)
            return self._gnoi_stream_both(stub, rpc, iterator)

        if key == ('file', 'Get'):
            if not remote_path and not (request or {}).get('remoteFile'):
                raise AnsibleConnectionFailure("gNOI File.Get requires remote_path or request.remoteFile")
            data = dict(request or {})
            if remote_path:
                data['remoteFile'] = remote_path
            message = gnoi_util.request_message(service, rpc, data)
            return self._gnoi_stream_server(stub, rpc, message, save_to=save_to)

        if key in gnoi_util.SERVER_STREAMING:
            message = gnoi_util.request_message(service, rpc, request or {})
            return self._gnoi_stream_server(stub, rpc, message)

        message = gnoi_util.request_message(service, rpc, request or {})
        try:
            if self.get_option('persistent_log_messages'):
                self.queue_message('log', 'gNOI %s request: %s' % (rpc, json_format.MessageToJson(message)))
            response = getattr(stub, rpc)(message, metadata=self._login_credentials, timeout=self._timeout)
        except grpc.RpcError as exc:
            raise self._rpc_error(exc)
        except gnoi_util.GnoiError as exc:
            raise AnsibleConnectionFailure(to_text(exc))
        if self.get_option('persistent_log_messages'):
            self.queue_message('log', 'gNOI %s response: %s' % (rpc, json_format.MessageToJson(response)))
        return {'output': json_format.MessageToDict(response)}

    # -------------------------------------------------------------------------
    # gNSI
    # -------------------------------------------------------------------------

    def _gnsi_stub(self, service):
        service = service.replace('-', '_')
        key = 'gnsi.' + service
        if key not in self._stubs:
            if service not in gnsi_util.SERVICES:
                raise AnsibleConnectionFailure("Unknown gNSI service %r" % service)
            self._stubs[key] = gnsi_util.SERVICES[service][1](self._channel)
        return self._stubs[key]

    @ensure_connect
    def invokeGnsi(self, service, rpc, request=None, stream=None):
        """
        Invokes a gNSI RPC (Authz, Certz, Pathz, Credentialz).

        request:
            Unary request fields (protobuf JSON names).
        stream:
            Request messages (protobuf JSON dicts) of a Rotate* RPC, sent in
            order. All server messages are collected until the RPC ends; the
            client sequence cannot depend on intermediate responses.
        """
        service = service.replace('-', '_')
        stub = self._gnsi_stub(service)
        key = (service, rpc)

        if stream is not None:
            iterator = gnsi_util.stream_messages(service, rpc, stream)
            if key in gnsi_util.BIDI_STREAMING:
                return self._gnoi_stream_both(stub, rpc, iterator)
            try:
                response = getattr(stub, rpc)(iterator, metadata=self._login_credentials, timeout=self._timeout)
            except grpc.RpcError as exc:
                raise self._rpc_error(exc)
            return {'output': json_format.MessageToDict(response)}

        message = gnsi_util.request_message(service, rpc, request or {})
        try:
            if self.get_option('persistent_log_messages'):
                self.queue_message('log', 'gNSI %s request: %s' % (rpc, json_format.MessageToJson(message)))
            response = getattr(stub, rpc)(message, metadata=self._login_credentials, timeout=self._timeout)
        except grpc.RpcError as exc:
            raise self._rpc_error(exc)
        except gnsi_util.GnsiError as exc:
            raise AnsibleConnectionFailure(to_text(exc))
        if self.get_option('persistent_log_messages'):
            self.queue_message('log', 'gNSI %s response: %s' % (rpc, json_format.MessageToJson(response)))
        return {'output': json_format.MessageToDict(response)}
