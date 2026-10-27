"""Authenticated attach/readback orchestration, separate from model import v1."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
import uuid
import zipfile

import httpx

from .reports import ReportError, report_binding, validate_import_report, validate_source_binding

MAX_ZIP_BYTES = 32 * 1024**2
MAX_EXPANDED_BYTES = 128 * 1024**2


class ReportWorkflowError(ReportError):
    """Model receipt remains available when report completion fails."""

    def __init__(self, message: str, details: dict):
        super().__init__(message, 'report_incomplete')
        self.details = details


def _api_origin(base: str) -> str:
    parts = urlsplit(base)
    if (parts.username or parts.password or parts.query or parts.fragment
            or parts.path != '/api/admin/sample-strategy-imports'
            or (parts.scheme != 'https' and not (parts.scheme == 'http' and parts.hostname in {'localhost', '127.0.0.1', '::1'}))):
        raise ReportError('expected HTTPS API origin with /api/admin/sample-strategy-imports')
    return f'{parts.scheme}://{parts.netloc}'


def _json_response(response: httpx.Response) -> dict:
    if response.is_error or response.is_redirect:
        raise ReportError(f'Report API HTTP {response.status_code}', 'report_api_failed')
    try:
        value = response.json()
    except ValueError as exc:
        raise ReportError('Report API returned invalid JSON', 'report_api_failed') from exc
    if not isinstance(value, dict):
        raise ReportError('Report API returned a non-object', 'report_api_failed')
    return value


def _check_receipt(receipt: dict, manifest: dict, pdf_sha: str) -> None:
    if (receipt.get('status') != 'ready' or not all(isinstance(receipt.get(k), str) and receipt[k]
            for k in ['sampleId', 'reportId', 'modelVersionId', 'backtestRunId'])
            or not re.fullmatch('[A-Za-z0-9_-]{1,128}', receipt['sampleId'])):
        raise ReportError('Report API did not return a ready, bound report receipt', 'report_readback_failed')
    if receipt.get('packageDigest') != manifest['packageDigest']:
        raise ReportError('Report receipt package digest mismatch', 'report_readback_failed')
    if receipt.get('pdfSha256') != pdf_sha:
        raise ReportError('Report receipt PDF hash mismatch', 'report_readback_failed')
    if receipt.get('importFingerprint') != manifest['binding']['bundleFingerprint']:
        raise ReportError('Report receipt import binding mismatch', 'report_readback_failed')


def attach_report(client: httpx.Client, base: str, import_id: str, packet: Path) -> dict:
    """Attach to a COMPLETED import, then verify authorized metadata and PDF bytes.

    The server derives sample/model/backtest IDs from the import; the caller
    cannot select a different target sample. A lost POST response can be retried
    with the same package digest; no report failure reimports the model.
    """
    origin = _api_origin(base)
    try:
        normalized_id = str(uuid.UUID(import_id))
    except (ValueError, AttributeError) as exc:
        raise ReportError('import id must be a UUID') from exc
    if normalized_id != import_id:
        raise ReportError('import id must be a canonical UUID')
    packet = Path(packet)
    validate_import_report(packet, require_binding=True)
    manifest = json.loads((packet / 'manifest.json').read_text(encoding='utf-8'))
    pdf = packet / 'report.pdf'
    pdf_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    files = sorted([packet / 'manifest.json', *[packet / e['path'] for e in manifest['files']]])
    if sum(p.stat().st_size for p in files) > MAX_EXPANDED_BYTES:
        raise ReportError('report packet exceeds 128 MiB expanded limit')
    with tempfile.TemporaryDirectory(prefix='report-upload-') as temp:
        archive = Path(temp) / 'report.zip'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            for path in files:
                zipped.write(path, str(path.relative_to(packet)))
        if archive.stat().st_size > MAX_ZIP_BYTES:
            raise ReportError('report ZIP exceeds 32 MiB limit')
        with archive.open('rb') as stream:
            response = client.post(f'{base}/{import_id}/report', content=stream,
                headers={'Content-Type': 'application/zip', 'Content-Length': str(archive.stat().st_size),
                         'Idempotency-Key': manifest['packageDigest']}, follow_redirects=False)
        receipt = _json_response(response)
    _check_receipt(receipt, manifest, pdf_sha)
    metadata = _json_response(client.get(f'{origin}/api/sample-strategies/{receipt["sampleId"]}/report', follow_redirects=False))
    _check_receipt(metadata, manifest, pdf_sha)
    for field in ['sampleId', 'reportId', 'modelVersionId', 'backtestRunId']:
        if metadata[field] != receipt[field]:
            raise ReportError(f'Report readback identity mismatch: {field}', 'report_readback_failed')
    response = client.get(f'{origin}/api/sample-strategies/{receipt["sampleId"]}/report/pdf',
                          params={'reportId': receipt['reportId']}, follow_redirects=False)
    if response.status_code != 200 or response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower() != 'application/pdf':
        raise ReportError('Authorized report PDF readback failed', 'report_readback_failed')
    if not response.content.startswith(b'%PDF-') or hashlib.sha256(response.content).hexdigest() != pdf_sha:
        raise ReportError('Authorized report PDF readback hash mismatch', 'report_readback_failed')
    if response.headers.get('ETag') != f'"{pdf_sha}"' or response.headers.get('X-Report-Id') != receipt['reportId']:
        raise ReportError('Authorized report PDF identity/header mismatch', 'report_readback_failed')
    cache = {part.strip().lower() for part in response.headers.get('Cache-Control', '').split(',')}
    if not {'private', 'no-store'} <= cache:
        raise ReportError('Authorized report PDF lacks private/no-store cache policy', 'report_readback_failed')
    return {'workflowStatus': 'COMPLETE', 'report': metadata, 'pdfReadbackVerified': True}


def import_with_report(client: httpx.Client, base: str, bundle: Path, packet: Path, *, commit: bool = True) -> dict:
    """Preflight before model upload; COMPLETE only after report attach/readback."""
    from .cli import import_bundle
    from .contract import artifact_path, verify_bundle
    canonical = verify_bundle(bundle)
    validate_import_report(packet, expected_binding=report_binding(canonical), require_binding=True)
    evidence = None
    for artifact in canonical.artifacts:
        if artifact.role == 'research' and Path(artifact.path).name == 'source-evidence.json':
            evidence = json.loads(artifact_path(bundle, artifact.path).read_text(encoding='utf-8'))
    validate_source_binding(packet, canonical, source_evidence=evidence)
    model = import_bundle(client, base, bundle, commit=commit)
    if not commit:
        return {'workflowStatus': 'VALIDATED_REPORT_PENDING', 'modelImport': model, 'reportAttached': False}
    if model.get('status') != 'COMPLETED':
        raise ReportWorkflowError('Model import is not complete; report was not attached',
                                  {'workflowStatus': 'MODEL_IMPORT_INCOMPLETE', 'modelImport': model})
    try:
        attached = attach_report(client, base, model['id'], packet)
    except (ReportError, OSError, httpx.HTTPError) as exc:
        raise ReportWorkflowError(f'Model imported; report remains incomplete: {exc}',
            {'workflowStatus': 'MODEL_IMPORTED_REPORT_PENDING', 'modelImport': model,
             'retry': f'report attach <packet> --import-id {model["id"]} --api <origin>'}) from exc
    return {**attached, 'modelImport': model}
