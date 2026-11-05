# (c) 2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

"""In-process OpenConfig gNxI mock server (gNMI, gNOI, gNSI) for connection unit tests.

gNOI/gNSI servicers implement exactly the RPCs in tools/nokia_grpc_modules.yaml;
test_grpc_manifest.py fails when a handler is missing or not in the manifest.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import hashlib
import json
import time
from concurrent import futures

import grpc

from ansible_collections.nokia.openconfig.plugins.module_utils.proto import gnmi_ext_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto import gnmi_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto import gnmi_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import bgp_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import bgp_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import factory_reset_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import factory_reset_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import file_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import file_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import healthz_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import healthz_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import os_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import os_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import system_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import system_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnoi import types_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnsi import authz_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnsi import authz_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnsi import certz_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnsi import certz_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnsi import credentialz_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnsi import credentialz_pb2_grpc
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnsi import pathz_pb2
from ansible_collections.nokia.openconfig.plugins.module_utils.proto.gnsi import pathz_pb2_grpc

_MOCK_TIME_NS = 1700000000000000000
_MOCK_AUTHZ_POLICY = '{"allowRules":[],"denyRules":[]}'
_MOCK_PATHZ_POLICY = pathz_pb2.AuthorizationPolicy()


def _json(value):
    return gnmi_pb2.TypedValue(json_ietf_val=json.dumps(value).encode())


def _path(*names, **keys):
    elems = [gnmi_pb2.PathElem(name=n) for n in names]
    if keys:
        elems[-1].key.update(keys)
    return gnmi_pb2.Path(elem=elems)


def _sha256(data):
    return types_pb2.HashType(method=types_pb2.HashType.SHA256, hash=hashlib.sha256(data).digest())


def _check_hash(received, digest, context):
    if received.method != types_pb2.HashType.SHA256 or received.hash != digest.digest():
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, 'Hash mismatch')


class RequestRegistry(object):

    def __init__(self):
        self.calls = []

    def record(self, protocol, service, rpc, request, context):
        self.calls.append({
            'protocol': protocol,
            'service': service,
            'rpc': rpc,
            'request': request,
            'metadata': dict(context.invocation_metadata()),
        })


class _GnxiRpcServicerBase(object):

    protocol = 'gnoi'
    service = ''

    def __init__(self, registry):
        self._registry = registry

    def _record(self, rpc, request, context):
        self._registry.record(self.protocol, self.service, rpc, request, context)


class GnmiServicer(gnmi_pb2_grpc.gNMIServicer):

    def __init__(self, registry=None):
        self.requests = []
        self.metadata = []
        self._registry = registry

    def _record(self, rpc, request, context):
        self.requests.append(request)
        self.metadata.append(dict(context.invocation_metadata()))
        if self._registry is not None:
            self._registry.record('gnmi', 'gnmi', rpc, request, context)

    def Capabilities(self, request, context):
        self._record('Capabilities', request, context)
        return gnmi_pb2.CapabilityResponse(
            supported_models=[gnmi_pb2.ModelData(name='openconfig-interfaces', organization='OpenConfig', version='3.0.0')],
            supported_encodings=[gnmi_pb2.JSON, gnmi_pb2.JSON_IETF, gnmi_pb2.ASCII],
            gNMI_version='0.10.0',
        )

    def Get(self, request, context):
        self._record('Get', request, context)
        notification = gnmi_pb2.Notification(
            timestamp=_MOCK_TIME_NS,
            update=[
                gnmi_pb2.Update(path=_path('interface', name='ethernet-1/1'),
                                val=_json({'description': 'uplink', 'admin-state': 'enable'})),
            ],
        )
        extension = [gnmi_ext_pb2.Extension(depth=e.depth) for e in request.extension if e.HasField('depth')]
        return gnmi_pb2.GetResponse(notification=[notification], extension=extension)

    def Set(self, request, context):
        self._record('Set', request, context)
        response = gnmi_pb2.SetResponse(timestamp=_MOCK_TIME_NS)
        for path in request.delete:
            response.response.add(path=path, op=gnmi_pb2.UpdateResult.DELETE)
        for upd in request.replace:
            response.response.add(path=upd.path, op=gnmi_pb2.UpdateResult.REPLACE)
        for upd in request.update:
            response.response.add(path=upd.path, op=gnmi_pb2.UpdateResult.UPDATE)
        if any(e.HasField('commit') and e.commit.id == 'reject' for e in request.extension):
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, 'commit reject in progress')
        response.extension.extend(request.extension)
        return response

    def Subscribe(self, request_iterator, context):
        request = next(request_iterator, None)
        if request is None:
            return
        self._record('Subscribe', request, context)
        config = any(e.HasField('config_subscription') for e in request.extension)

        def update(n):
            return gnmi_pb2.SubscribeResponse(update=gnmi_pb2.Notification(
                timestamp=_MOCK_TIME_NS + n,
                prefix=_path('interface', name='ethernet-1/1'),
                update=[gnmi_pb2.Update(path=_path('description'), val=gnmi_pb2.TypedValue(string_val='uplink-%d' % n))],
            ))

        def done(commit_id, final):
            return gnmi_pb2.SubscribeResponse(extension=[gnmi_ext_pb2.Extension(
                config_subscription=gnmi_ext_pb2.ConfigSubscription(
                    sync_done=gnmi_ext_pb2.ConfigSubscriptionSyncDone(
                        commit_confirm_id=commit_id, server_commit_id='srv-1', done=final)))])

        yield update(0)
        if config:
            yield done('', True)
        yield gnmi_pb2.SubscribeResponse(sync_response=True)

        mode = request.subscribe.mode
        if mode == gnmi_pb2.SubscriptionList.POLL:
            poll = next(request_iterator, None)
            if poll is None:
                return
            self.requests.append(poll)
            yield update(1)
            yield gnmi_pb2.SubscribeResponse(sync_response=True)
        elif mode == gnmi_pb2.SubscriptionList.STREAM:
            n = 1
            while context.is_active():
                time.sleep(0.05)
                yield update(n)
                if config and n == 3:
                    yield done('c1', True)
                n += 1


class GnoiSystemServicer(_GnxiRpcServicerBase, system_pb2_grpc.SystemServicer):
    service = 'system'

    def Ping(self, request, context):
        self._record('Ping', request, context)
        yield system_pb2.PingResponse(sent=1, received=1, avg_time=1)
        yield system_pb2.PingResponse(sent=1, received=1, avg_time=1)

    def Traceroute(self, request, context):
        self._record('Traceroute', request, context)
        yield system_pb2.TracerouteResponse()

    def Time(self, request, context):
        self._record('Time', request, context)
        return system_pb2.TimeResponse(time=_MOCK_TIME_NS)

    def SetPackage(self, request_iterator, context):
        digest = hashlib.sha256()
        for request in request_iterator:
            self._record('SetPackage', request, context)
            if request.HasField('contents'):
                digest.update(request.contents)
            elif request.HasField('hash'):
                _check_hash(request.hash, digest, context)
        return system_pb2.SetPackageResponse()

    def SwitchControlProcessor(self, request, context):
        self._record('SwitchControlProcessor', request, context)
        return system_pb2.SwitchControlProcessorResponse()

    def Reboot(self, request, context):
        self._record('Reboot', request, context)
        return system_pb2.RebootResponse()

    def RebootStatus(self, request, context):
        self._record('RebootStatus', request, context)
        return system_pb2.RebootStatusResponse()

    def CancelReboot(self, request, context):
        self._record('CancelReboot', request, context)
        return system_pb2.CancelRebootResponse()

    def KillProcess(self, request, context):
        self._record('KillProcess', request, context)
        return system_pb2.KillProcessResponse()


class GnoiFileServicer(_GnxiRpcServicerBase, file_pb2_grpc.FileServicer):
    service = 'file'

    def Get(self, request, context):
        self._record('Get', request, context)
        if request.remote_file == '/missing':
            context.abort(grpc.StatusCode.NOT_FOUND, 'file not found')
        if request.remote_file == '/partial':
            yield file_pb2.GetResponse(contents=b'partial-chunk')
            context.abort(grpc.StatusCode.INTERNAL, 'stream interrupted')
        payload = b'mock-file-data'
        yield file_pb2.GetResponse(contents=payload)
        yield file_pb2.GetResponse(hash=_sha256(payload))

    def TransferToRemote(self, request, context):
        self._record('TransferToRemote', request, context)
        return file_pb2.TransferToRemoteResponse(hash=_sha256(b''))

    def Put(self, request_iterator, context):
        digest = hashlib.sha256()
        for request in request_iterator:
            self._record('Put', request, context)
            if request.HasField('contents'):
                digest.update(request.contents)
            elif request.HasField('hash'):
                _check_hash(request.hash, digest, context)
        return file_pb2.PutResponse()

    def Stat(self, request, context):
        self._record('Stat', request, context)
        return file_pb2.StatResponse(
            stats=[file_pb2.StatInfo(path=request.path or '/', last_modified=_MOCK_TIME_NS, permissions=644, size=3)],
        )

    def Remove(self, request, context):
        self._record('Remove', request, context)
        return file_pb2.RemoveResponse()


class GnoiOSServicer(_GnxiRpcServicerBase, os_pb2_grpc.OSServicer):
    service = 'os'

    def Install(self, request_iterator, context):
        for request in request_iterator:
            self._record('Install', request, context)
            if request.HasField('transfer_request'):
                yield os_pb2.InstallResponse(transfer_ready=os_pb2.TransferReady())
        yield os_pb2.InstallResponse(validated=os_pb2.Validated())

    def Activate(self, request, context):
        self._record('Activate', request, context)
        return os_pb2.ActivateResponse()

    def Verify(self, request, context):
        self._record('Verify', request, context)
        return os_pb2.VerifyResponse(version='mock-os-1.0')


class GnoiFactoryResetServicer(_GnxiRpcServicerBase, factory_reset_pb2_grpc.FactoryResetServicer):
    service = 'factory_reset'

    def Start(self, request, context):
        self._record('Start', request, context)
        response = factory_reset_pb2.StartResponse()
        response.reset_success.SetInParent()
        return response


class GnoiHealthzServicer(_GnxiRpcServicerBase, healthz_pb2_grpc.HealthzServicer):
    service = 'healthz'

    def Get(self, request, context):
        self._record('Get', request, context)
        return healthz_pb2.GetResponse()

    def List(self, request, context):
        self._record('List', request, context)
        return healthz_pb2.ListResponse()

    def Acknowledge(self, request, context):
        self._record('Acknowledge', request, context)
        return healthz_pb2.AcknowledgeResponse()

    def Artifact(self, request, context):
        self._record('Artifact', request, context)
        yield healthz_pb2.ArtifactResponse()

    def Check(self, request, context):
        self._record('Check', request, context)
        return healthz_pb2.CheckResponse()


class GnoiBGPServicer(_GnxiRpcServicerBase, bgp_pb2_grpc.BGPServicer):
    service = 'bgp'

    def ClearBGPNeighbor(self, request, context):
        self._record('ClearBGPNeighbor', request, context)
        return bgp_pb2.ClearBGPNeighborResponse()


class GnsiAuthzServicer(_GnxiRpcServicerBase, authz_pb2_grpc.AuthzServicer):
    protocol = 'gnsi'
    service = 'authz'

    def Rotate(self, request_iterator, context):
        for request in request_iterator:
            self._record('Rotate', request, context)
            if request.HasField('upload_request'):
                yield authz_pb2.RotateAuthzResponse(upload_response=authz_pb2.UploadResponse())
            else:
                yield authz_pb2.RotateAuthzResponse()

    def Probe(self, request, context):
        self._record('Probe', request, context)
        return authz_pb2.ProbeResponse(action=authz_pb2.ProbeResponse.Action.ACTION_PERMIT)

    def Get(self, request, context):
        self._record('Get', request, context)
        return authz_pb2.GetResponse(version='mock-authz-1', created_on=1700000000, policy=_MOCK_AUTHZ_POLICY)


class GnsiCertzServicer(_GnxiRpcServicerBase, certz_pb2_grpc.CertzServicer):
    protocol = 'gnsi'
    service = 'certz'

    def Rotate(self, request_iterator, context):
        for request in request_iterator:
            self._record('Rotate', request, context)
            if request.HasField('generate_csr'):
                yield certz_pb2.RotateCertificateResponse(
                    generated_csr=certz_pb2.GenerateCSRResponse(certificate_signing_request=b'mock-csr'))
            elif request.HasField('certificates'):
                yield certz_pb2.RotateCertificateResponse(certificates=certz_pb2.UploadResponse())
            else:
                yield certz_pb2.RotateCertificateResponse()

    def AddProfile(self, request, context):
        self._record('AddProfile', request, context)
        return certz_pb2.AddProfileResponse()

    def DeleteProfile(self, request, context):
        self._record('DeleteProfile', request, context)
        return certz_pb2.DeleteProfileResponse()

    def GetProfileList(self, request, context):
        self._record('GetProfileList', request, context)
        return certz_pb2.GetProfileListResponse(ssl_profile_ids=['default'])

    def CanGenerateCSR(self, request, context):
        self._record('CanGenerateCSR', request, context)
        return certz_pb2.CanGenerateCSRResponse(can_generate=True)


class GnsiPathzServicer(_GnxiRpcServicerBase, pathz_pb2_grpc.PathzServicer):
    protocol = 'gnsi'
    service = 'pathz'

    def Rotate(self, request_iterator, context):
        for request in request_iterator:
            self._record('Rotate', request, context)
            if request.HasField('upload_request'):
                yield pathz_pb2.RotateResponse(upload=pathz_pb2.UploadResponse())
            else:
                yield pathz_pb2.RotateResponse()

    def Probe(self, request, context):
        self._record('Probe', request, context)
        return pathz_pb2.ProbeResponse(action=pathz_pb2.ACTION_PERMIT)

    def Get(self, request, context):
        self._record('Get', request, context)
        return pathz_pb2.GetResponse(version='mock-pathz-1', created_on=1700000000, policy=_MOCK_PATHZ_POLICY)


class GnsiCredentialzServicer(_GnxiRpcServicerBase, credentialz_pb2_grpc.CredentialzServicer):
    protocol = 'gnsi'
    service = 'credentialz'

    def RotateAccountCredentials(self, request_iterator, context):
        for request in request_iterator:
            self._record('RotateAccountCredentials', request, context)
            yield credentialz_pb2.RotateAccountCredentialsResponse()

    def RotateHostParameters(self, request_iterator, context):
        for request in request_iterator:
            self._record('RotateHostParameters', request, context)
            yield credentialz_pb2.RotateHostParametersResponse()

    def CanGenerateKey(self, request, context):
        self._record('CanGenerateKey', request, context)
        return credentialz_pb2.CanGenerateKeyResponse(can_generate=True)

    def GetPublicKeys(self, request, context):
        self._record('GetPublicKeys', request, context)
        return credentialz_pb2.GetPublicKeysResponse()


class OpenConfigMockServer(object):

    def __init__(self, address='127.0.0.1', credentials=None):
        self.registry = RequestRegistry()
        self.gnmi = GnmiServicer(self.registry)
        self.gnoi = {
            'system': GnoiSystemServicer(self.registry),
            'file': GnoiFileServicer(self.registry),
            'os': GnoiOSServicer(self.registry),
            'factory_reset': GnoiFactoryResetServicer(self.registry),
            'healthz': GnoiHealthzServicer(self.registry),
            'bgp': GnoiBGPServicer(self.registry),
        }
        self.gnsi = {
            'authz': GnsiAuthzServicer(self.registry),
            'certz': GnsiCertzServicer(self.registry),
            'pathz': GnsiPathzServicer(self.registry),
            'credentialz': GnsiCredentialzServicer(self.registry),
        }
        self._grpc = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
        gnmi_pb2_grpc.add_gNMIServicer_to_server(self.gnmi, self._grpc)
        system_pb2_grpc.add_SystemServicer_to_server(self.gnoi['system'], self._grpc)
        file_pb2_grpc.add_FileServicer_to_server(self.gnoi['file'], self._grpc)
        os_pb2_grpc.add_OSServicer_to_server(self.gnoi['os'], self._grpc)
        factory_reset_pb2_grpc.add_FactoryResetServicer_to_server(self.gnoi['factory_reset'], self._grpc)
        healthz_pb2_grpc.add_HealthzServicer_to_server(self.gnoi['healthz'], self._grpc)
        bgp_pb2_grpc.add_BGPServicer_to_server(self.gnoi['bgp'], self._grpc)
        authz_pb2_grpc.add_AuthzServicer_to_server(self.gnsi['authz'], self._grpc)
        certz_pb2_grpc.add_CertzServicer_to_server(self.gnsi['certz'], self._grpc)
        pathz_pb2_grpc.add_PathzServicer_to_server(self.gnsi['pathz'], self._grpc)
        credentialz_pb2_grpc.add_CredentialzServicer_to_server(self.gnsi['credentialz'], self._grpc)
        bind = '[%s]:0' % address if ':' in address else '%s:0' % address
        if credentials is not None:
            self.port = self._grpc.add_secure_port(bind, credentials)
        else:
            self.port = self._grpc.add_insecure_port(bind)

    def __enter__(self):
        self._grpc.start()
        return self

    def __exit__(self, *args):
        self._grpc.stop(0)
