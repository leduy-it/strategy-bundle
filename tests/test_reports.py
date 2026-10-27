"""Offline report contract; synthetic content is never investment evidence."""
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


def reports():
    return importlib.import_module('promete_strategy_bundle.reports')


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def report_source(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'curve.csv').write_text('date,equity\n2026-01-01,100\n2026-01-02,102\n')
    spec = {'output_name': 'synthetic-report',
            'cover': {'number_line': 'Báo cáo thử', 'title': 'Dữ liệu tổng hợp', 'facts': []},
            'toc': {'enabled': False},
            'sections': [{'title': 'Kết quả thử nghiệm', 'blocks': [
                {'type': 'p', 'text': 'Dữ liệu tổng hợp để kiểm thử phần mềm.'},
                {'type': 'chart', 'kind': 'line', 'series': [
                    {'name': 'Thử nghiệm', 'csv': 'curve.csv', 'x': 'date', 'y': 'equity'}]}]}]}
    write_json(root / 'report.json', spec)
    subject = {'repository': 'test://synthetic', 'revision': 'test-v1', 'runId': 'run-test',
               'modelRef': 'model-test', 'seed': 1, 'evaluationFingerprint': 'a' * 64}
    write_json(root / 'facts.json', {'identity': {'model_id': 'model-test', 'seed': 1},
                                    'note': 'Synthetic fixture, no investment evidence'})
    (root / 'evidence.json').write_text('{"synthetic": true}')
    write_json(root / 'source-manifest.json', {
        'schemaVersion': 'strategy-report-source/v1', 'subject': subject,
        'files': [{'path': 'evidence.json', 'size': (root / 'evidence.json').stat().st_size,
                   'sha256': sha(root / 'evidence.json')}]})
    return root


def test_export_carries_complete_exact_source_hashes(tmp_path):
    api = reports()
    result = api.export_report_skill(tmp_path / 'export')
    root = tmp_path / 'export'
    manifest = json.loads((root / 'manifest.json').read_text())
    assert result['skillManifestSha256'] == sha(root / 'manifest.json')
    assert manifest['source']['repository'].endswith('promete-strategy-lab')
    assert manifest['source']['skillTracked'] is False  # original skill is untracked WIP
    paths = {f['path'] for f in manifest['files']}
    for needed in ['strategy-sample-report/SKILL.md', 'strategy-sample-report/scripts/build_report.py',
                   'strategy-sample-report/assets/fonts/Lexend-Light.ttf',
                   'strategy-sample-report/assets/fonts/OFL.txt',
                   'strategy-sample-report/assets/promete-logo.jpg',
                   'strategy-sample-report/data/feature-rationale.json',
                   'strategy-dossier-editor/SKILL.md']:
        assert needed in paths
    for file in manifest['files']:
        assert sha(root / file['path']) == file['sha256']
        assert (root / file['path']).stat().st_size == file['size']
    # Pin to the exact original SKILL, rather than merely trusting its own manifest.
    assert sha(root / 'strategy-sample-report/SKILL.md') == '4b5be47596d1bfe87b766b073907ac3e388e311b6ac36a9ffca64cf4ae1f9a1f'
    digest = subprocess.run([sys.executable, str(root / 'strategy-sample-report/scripts/feature_digest.py'),
                             '--features', 'rsi', '--json'], capture_output=True, text=True)
    assert digest.returncode == 0, digest.stderr
    assert json.loads(digest.stdout)['missing'] == []


def test_export_rejects_symlink_destination(tmp_path):
    (tmp_path / 'real').mkdir()
    (tmp_path / 'link').symlink_to(tmp_path / 'real', target_is_directory=True)
    with pytest.raises(reports().ReportError, match='symlink'):
        reports().export_report_skill(tmp_path / 'link' / 'export')
    assert not (tmp_path / 'real' / 'export').exists()


def test_prepare_is_portable_and_retains_inputs(report_source, tmp_path):
    api = reports()
    result = api.prepare_report(report_source, tmp_path / 'prepared')
    assert result['status'] == 'draft'
    prepared = tmp_path / 'prepared'
    spec = json.loads((prepared / 'report.json').read_text())
    csv_path = prepared / spec['sections'][0]['blocks'][1]['series'][0]['csv']
    assert csv_path.read_bytes() == (report_source / 'curve.csv').read_bytes()
    assert json.loads((prepared / 'facts.json').read_text()) == json.loads((report_source / 'facts.json').read_text())
    assert api.validate_report(prepared / 'report.json')['valid'] is True
    assert result['sourceSpecSha256'] == sha(report_source / 'report.json')
    with pytest.raises(api.ReportError):
        api.validate_import_report(prepared)


def test_trusted_root_allows_legacy_relative_csv_only_when_explicit(report_source, tmp_path):
    nested = report_source / 'nested'
    nested.mkdir()
    spec = json.loads((report_source / 'report.json').read_text())
    spec['sections'][0]['blocks'][1]['series'][0]['csv'] = '../curve.csv'
    write_json(nested / 'report.json', spec)
    api = reports()
    with pytest.raises(api.ReportError, match='outside'):
        api.prepare_report(nested, tmp_path / 'denied')
    result = api.prepare_report(nested, tmp_path / 'allowed', source_root=report_source)
    assert result['status'] == 'draft'
    assert api.validate_report(tmp_path / 'allowed' / 'report.json')['valid']


@pytest.mark.parametrize('kind', ['escape', 'absolute', 'symlink', 'output_escape', 'unknown_block'])
def test_unsafe_report_input_is_rejected(report_source, tmp_path, kind):
    spec = json.loads((report_source / 'report.json').read_text())
    series = spec['sections'][0]['blocks'][1]['series'][0]
    if kind == 'escape':
        (tmp_path / 'outside.csv').write_text('date,equity\n2026-01-01,999')
        series['csv'] = '../outside.csv'
    elif kind == 'absolute':
        series['csv'] = str(report_source / 'curve.csv')
    elif kind == 'symlink':
        (report_source / 'link.csv').symlink_to(report_source / 'curve.csv')
        series['csv'] = 'link.csv'
    elif kind == 'output_escape':
        spec['output_name'] = '../../escaped'
    else:
        spec['sections'][0]['blocks'][0]['type'] = '__getattribute__'
    write_json(report_source / 'report.json', spec)
    with pytest.raises(reports().ReportError):
        reports().prepare_report(report_source, tmp_path / 'prepared')
    assert not (tmp_path / 'prepared').exists()


def test_original_editorial_lint_is_enforced(report_source):
    path = report_source / 'report.json'
    spec = json.loads(path.read_text())
    spec['sections'][0]['blocks'][0]['text'] = 'TODO lợi nhuận 38.75%'
    write_json(path, spec)
    with pytest.raises(reports().ReportError, match='placeholder|thập phân'):
        reports().validate_report(path)


def test_source_manifest_hash_mismatch_is_rejected(report_source, tmp_path):
    (report_source / 'evidence.json').write_text('modified')
    with pytest.raises(reports().ReportError, match='hash|size'):
        reports().prepare_report(report_source, tmp_path / 'prepared')


def test_report_cli_has_json_errors_and_does_not_load_render_dependencies(tmp_path, capsys):
    from promete_strategy_bundle.cli import main
    assert main(['report', 'validate', str(tmp_path / 'missing.json')]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error['error']['code'] == 'invalid_input'
    code = '''
import importlib.abc, sys
class BlockRender(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'docx','matplotlib','fontTools'}:
   raise ImportError('render dependency forbidden during core CLI')
sys.meta_path.insert(0,BlockRender())
from promete_strategy_bundle.cli import main
assert main(['schema']) == 0
assert main(['report','skill',sys.argv[1]]) == 0
assert not any(n in sys.modules for n in ['docx','matplotlib','fontTools'])
'''
    run = subprocess.run([sys.executable, '-c', code, str(tmp_path / 'skill')], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr


def test_missing_render_deps_has_actionable_error(report_source, tmp_path, monkeypatch):
    api = reports()
    original = api.importlib.util.find_spec
    monkeypatch.setattr(api.importlib.util, 'find_spec', lambda name: None if name == 'docx' else original(name))
    with pytest.raises(api.ReportError, match=r'\[report\]') as failure:
        api.render_report(report_source / 'report.json', tmp_path / 'render')
    assert failure.value.code == 'missing_dependency'
    assert not (tmp_path / 'render').exists()


def test_missing_system_tool_names_exact_requirement(report_source, tmp_path, monkeypatch):
    api = reports()
    monkeypatch.setattr(api.shutil, 'which', lambda name: None if name == 'soffice' else '/usr/bin/' + name)
    with pytest.raises(api.ReportError, match='soffice') as failure:
        api.render_report(report_source / 'report.json', tmp_path / 'render')
    assert failure.value.code == 'missing_dependency'


def test_render_pack_and_check_require_bound_inputs(report_source, tmp_path):
    api = reports()
    import importlib.util
    import shutil
    if any(importlib.util.find_spec(n) is None for n in ['docx', 'matplotlib', 'fontTools']) or any(
            shutil.which(n) is None for n in ['soffice', 'fc-list', 'fc-cache', 'pdfinfo', 'pdftotext', 'pdffonts']):
        pytest.skip('optional render integration requires .[report] and LibreOffice/poppler/fontconfig')
    prepared, rendered, packet = [tmp_path / n for n in ['prepared', 'rendered', 'packet']]
    api.prepare_report(report_source, prepared)
    result = api.render_report(prepared / 'report.json', rendered)
    assert Path(result['pdf']).read_bytes().startswith(b'%PDF-')
    assert result['non_lexend_fonts'] == []
    assert (rendered / 'render.json').is_file()
    result = api.pack_report(prepared, rendered, packet)
    assert result['importReady'] is True
    subject = json.loads((report_source / 'source-manifest.json').read_text())['subject']
    checked = api.validate_import_report(packet, expected_subject=subject)
    assert checked['packageDigest'] == result['packageDigest']
    with pytest.raises(api.ReportError, match='subject'):
        api.validate_import_report(packet, expected_subject={**subject, 'modelRef': 'another-model'})
    (packet / 'report.pdf').write_bytes(b'%PDF-1.4\ncorrupt\n%%EOF')
    with pytest.raises(api.ReportError, match='hash|size'):
        api.validate_import_report(packet)
    # An old PDF cannot be attached to newly edited content even if its header is valid.
    spec = json.loads((prepared / 'report.json').read_text())
    spec['cover']['title'] = 'Changed after render'
    write_json(prepared / 'report.json', spec)
    with pytest.raises(api.ReportError, match='receipt|input'):
        api.pack_report(prepared, rendered, tmp_path / 'stale-packet')


def test_source_manifest_itself_must_not_be_a_symlink(report_source, tmp_path):
    manifest = report_source / 'source-manifest.json'
    outside = tmp_path / 'other-manifest.json'
    manifest.rename(outside)
    manifest.symlink_to(outside)
    with pytest.raises(reports().ReportError, match='symlink'):
        reports().prepare_report(report_source, tmp_path / 'prepared')


@pytest.mark.parametrize('bad_path', [None, {}, [], 42])
def test_malformed_source_paths_are_structured_input_errors(report_source, tmp_path, bad_path):
    manifest = report_source / 'source-manifest.json'
    data = json.loads(manifest.read_text())
    data['files'][0]['path'] = bad_path
    write_json(manifest, data)
    with pytest.raises(reports().ReportError):
        reports().prepare_report(report_source, tmp_path / 'prepared')


def test_duplicate_content_source_files_remain_self_contained(report_source, tmp_path):
    duplicate = report_source / 'identical.json'
    duplicate.write_bytes((report_source / 'evidence.json').read_bytes())
    manifest = report_source / 'source-manifest.json'
    data = json.loads(manifest.read_text())
    data['files'].append({**data['files'][0], 'path': 'identical.json'})
    write_json(manifest, data)
    reports().prepare_report(report_source, tmp_path / 'prepared')
    # Both explicitly declared source files must survive relocation.
    rewritten = json.loads((tmp_path / 'prepared' / 'source-manifest.json').read_text())
    assert len({e['path'] for e in rewritten['files']}) == 2
    assert all((tmp_path / 'prepared' / e['path']).is_file() for e in rewritten['files'])


@pytest.fixture
def transport_packet(report_source, bundle_dir, tmp_path):
    """Synthetic transport fixture; rendering itself has a real integration test."""
    import zipfile
    api = reports()
    from promete_strategy_bundle.contract import verify_bundle
    bundle = verify_bundle(bundle_dir)
    source_manifest = report_source / 'source-manifest.json'
    source = json.loads(source_manifest.read_text())
    source['subject'].update({k: getattr(bundle.provenance, k) for k in ['repository', 'revision', 'runId', 'modelRef', 'seed']})
    source['subject']['modelSha256'] = next(a.sha256 for a in bundle.artifacts if a.role == 'model')
    source['subject']['evaluationFingerprint'] = hashlib.sha256(json.dumps(bundle.evaluation.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    write_json(source_manifest, source)
    facts = json.loads((report_source / 'facts.json').read_text())
    facts['identity']['model_id'] = bundle.provenance.modelRef
    write_json(report_source / 'facts.json', facts)
    prepared, rendered, packet = [tmp_path / n for n in ['transport-prepared', 'transport-rendered', 'transport-packet']]
    api.prepare_report(report_source, prepared)
    rendered.mkdir()
    (rendered / 'synthetic.pdf').write_bytes(b'%PDF-1.4\nsynthetic transport test; not a real research report\n%%EOF\n')
    with zipfile.ZipFile(rendered / 'synthetic.docx', 'w') as archive:
        archive.writestr('word/document.xml', '<synthetic-test/>')
    def entry(path, role):
        return {'path': str(path.relative_to(prepared)), 'size': path.stat().st_size, 'sha256': sha(path), 'role': role}
    entries = [entry(prepared / name, role) for name, role in [('report.json', 'report_spec'), ('facts.json', 'facts'), ('source-manifest.json', 'source_manifest')]]
    for folder, role in [('assets', 'asset'), ('sources', 'source')]:
        entries.extend(entry(p, role) for p in (prepared / folder).glob('*'))
    write_json(rendered / 'render.json', {'schemaVersion': 'strategy-report-render/v1',
        'skillManifestSha256': api.validate_report(prepared / 'report.json')['skillManifestSha256'],
        'inputs': sorted(entries, key=lambda e: e['path']),
        'artifacts': [{'path': p.name, 'size': p.stat().st_size, 'sha256': sha(p), 'role': role}
                      for p, role in [(rendered / 'synthetic.pdf', 'pdf'), (rendered / 'synthetic.docx', 'docx')]],
        'lint': [], 'non_lexend_fonts': []})
    api.pack_report(prepared, rendered, packet)
    return packet


def test_bind_report_preserves_source_subject_and_proves_bundle(transport_packet, bundle_dir, tmp_path):
    api = reports()
    original = json.loads((transport_packet / 'manifest.json').read_text())
    bound = tmp_path / 'bound'
    result = api.bind_report(transport_packet, bundle_dir, bound)
    manifest = json.loads((bound / 'manifest.json').read_text())
    from promete_strategy_bundle.contract import verify_bundle, fingerprint
    bundle = verify_bundle(bundle_dir)
    assert manifest['subject'] == original['subject']
    assert manifest['files'] == original['files']
    assert manifest['binding']['bundleFingerprint'] == fingerprint(bundle)
    assert manifest['binding']['modelSha256'] == next(a.sha256 for a in bundle.artifacts if a.role == 'model')
    assert manifest['binding']['provenance'] == bundle.provenance.model_dump(mode='json')
    assert result['platformBindingReady']
    assert api.validate_import_report(bound, expected_binding=api.report_binding(bundle_dir))['platformBindingReady']


def test_bind_rejects_wrong_source_checkpoint(transport_packet, bundle_dir, tmp_path):
    api = reports()
    data = json.loads((bundle_dir / 'manifest.json').read_text())
    data['provenance']['modelRef'] = 'another-model'
    write_json(bundle_dir / 'manifest.json', data)
    with pytest.raises(api.ReportError, match='source|subject'):
        api.bind_report(transport_packet, bundle_dir, tmp_path / 'bound')
    assert not (tmp_path / 'bound').exists()


def report_server(packet, *, bad_pdf=False, bad_digest=False, bad_header=False):
    import httpx
    import io
    import zipfile
    manifest = json.loads((packet / 'manifest.json').read_text())
    calls = []
    receipt = {'sampleId': 'sample-test', 'status': 'ready', 'reportId': 'report-test',
               'title': 'Synthetic transport report', 'fileName': 'report.pdf', 'updatedAt': '2026-10-27T00:00:00Z',
               'modelVersionId': 'model-version-test', 'backtestRunId': 'backtest-test',
               'packageDigest': '0' * 64 if bad_digest else manifest['packageDigest'],
               'pdfSha256': sha(packet / 'report.pdf'), 'importFingerprint': manifest['binding']['bundleFingerprint']}
    def handler(request):
        calls.append((request.method, request.url.path))
        if request.url.path.endswith('/report/pdf'):
            assert request.url.params.get('reportId') == 'report-test'
        else:
            assert not request.url.query
        if request.method == 'POST' and request.url.path.endswith('/report'):
            assert request.headers['content-type'] == 'application/zip'
            with zipfile.ZipFile(io.BytesIO(request.read())) as archive:
                assert json.loads(archive.read('manifest.json')) == manifest
                assert archive.read('report.pdf') == (packet / 'report.pdf').read_bytes()
            return httpx.Response(200, json=receipt)
        if request.url.path.endswith('/report/pdf'):
            return httpx.Response(200, content=b'%PDF-corrupt' if bad_pdf else (packet / 'report.pdf').read_bytes(), headers={'Content-Type': 'application/pdf', 'ETag': '"' + receipt['pdfSha256'] + '"', 'X-Report-Id': 'wrong-report' if bad_header else 'report-test', 'Cache-Control': 'private, no-store'})
        if request.url.path.endswith('/report'):
            return httpx.Response(200, json=receipt)
        if request.url.path.endswith('/sample-strategy-imports'):
            return httpx.Response(200, json={'id': '12345678-1234-1234-1234-123456789abc', 'status': 'COMPLETED'})
        raise AssertionError(str(request.url))
    return handler, calls


def test_attach_requires_verified_readback(transport_packet, bundle_dir, tmp_path):
    import httpx
    api = reports()
    packet = tmp_path / 'bound'
    api.bind_report(transport_packet, bundle_dir, packet)
    client_api = importlib.import_module('promete_strategy_bundle.report_api')
    handler, calls = report_server(packet)
    with httpx.Client(transport=httpx.MockTransport(handler), headers={'Authorization': 'Bearer test'}, follow_redirects=False) as client:
        result = client_api.attach_report(client, 'https://test/api/admin/sample-strategy-imports',
                                          '12345678-1234-1234-1234-123456789abc', packet)
    assert result['workflowStatus'] == 'COMPLETE'
    assert result['report']['sampleId'] == 'sample-test'
    assert calls[-2:] == [('GET', '/api/sample-strategies/sample-test/report'), ('GET', '/api/sample-strategies/sample-test/report/pdf')]


@pytest.mark.parametrize('fault', ['digest', 'pdf', 'header'])
def test_attach_never_completes_on_wrong_readback(transport_packet, bundle_dir, tmp_path, fault):
    import httpx
    api = reports()
    packet = tmp_path / 'bound'
    api.bind_report(transport_packet, bundle_dir, packet)
    client_api = importlib.import_module('promete_strategy_bundle.report_api')
    handler, _ = report_server(packet, bad_digest=fault == 'digest', bad_pdf=fault == 'pdf', bad_header=fault == 'header')
    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        with pytest.raises(api.ReportError, match='digest|hash|identity'):
            client_api.attach_report(client, 'https://test/api/admin/sample-strategy-imports',
                                     '12345678-1234-1234-1234-123456789abc', packet)


def test_import_with_reports_preflights_packet_and_resumes_completed_model(transport_packet, bundle_dir, tmp_path):
    import httpx
    api = reports()
    packet = tmp_path / 'bound'
    api.bind_report(transport_packet, bundle_dir, packet)
    client_api = importlib.import_module('promete_strategy_bundle.report_api')
    handler, calls = report_server(packet)
    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        result = client_api.import_with_report(client, 'https://test/api/admin/sample-strategy-imports', bundle_dir, packet)
    assert result['workflowStatus'] == 'COMPLETE'
    assert result['modelImport']['status'] == 'COMPLETED'
    assert sum(path.endswith('/sample-strategy-imports') for _, path in calls) == 1
    assert not any(path.endswith('/commit') for _, path in calls)
    # Reject a model mismatch locally, before any model upload side effect.
    data = json.loads((bundle_dir / 'manifest.json').read_text())
    data['provenance']['modelRef'] = 'different-checkpoint'
    write_json(bundle_dir / 'manifest.json', data)
    calls.clear()
    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        with pytest.raises(api.ReportError, match='binding'):
            client_api.import_with_report(client, 'https://test/api/admin/sample-strategy-imports', bundle_dir, packet)
    assert calls == []


def test_cli_bind_and_attach_use_same_packet_contract(transport_packet, bundle_dir, tmp_path, monkeypatch, capsys):
    import httpx
    from promete_strategy_bundle.cli import main
    packet = tmp_path / 'bound-cli'
    assert main(['report', 'bind', str(transport_packet), '--bundle', str(bundle_dir), '--output', str(packet)]) == 0
    assert json.loads(capsys.readouterr().out)['platformBindingReady']
    handler, _ = report_server(packet)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.setenv('STRATEGY_BUNDLE_TOKEN', 'secret-test-token')
    assert main(['report', 'attach', str(packet), '--import-id', '12345678-1234-1234-1234-123456789abc', '--api', 'https://test']) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)['workflowStatus'] == 'COMPLETE'
    assert 'secret-test-token' not in output.out + output.err


def test_cli_import_report_failure_preserves_model_receipt(transport_packet, bundle_dir, tmp_path, monkeypatch, capsys):
    import httpx
    from promete_strategy_bundle.cli import main
    packet = tmp_path / 'bound'
    reports().bind_report(transport_packet, bundle_dir, packet)
    handler, _ = report_server(packet, bad_pdf=True)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.setenv('STRATEGY_BUNDLE_TOKEN', 'secret-test-token')
    assert main(['import', str(bundle_dir), '--with-reports', str(packet), '--api', 'https://test']) != 0
    output = capsys.readouterr()
    assert output.out == ''
    error = json.loads(output.err)
    assert error['error']['code'] == 'report_incomplete'
    assert error['details']['workflowStatus'] == 'MODEL_IMPORTED_REPORT_PENDING'
    assert error['details']['modelImport']['id'] == '12345678-1234-1234-1234-123456789abc'
    assert 'secret-test-token' not in output.err


@pytest.fixture
def lab_binding_case(bundle_dir, tmp_path):
    """Minimal trusted imported research artifact and independently hashed packet sources."""
    from promete_strategy_bundle.contract import verify_bundle
    data = verify_bundle(bundle_dir).model_dump(mode='json')
    data['evaluation']['metrics']['maxDrawdown'] = 0.1
    data['evaluation']['endDate'] = '2026-01-03'
    data['evaluation']['nav'] = [{'date': '2026-01-01', 'balance': 1000}, {'date': '2026-01-02', 'balance': 900}, {'date': '2026-01-03', 'balance': 1100}]
    original_model_sha = 'b' * 64
    data['strategy']['research']['sourceHashes'] = {'model': {'sha256': original_model_sha}}
    metadata = {'model_id': 'attempt:original', 'artifact_pair': {'model': {'sha256': original_model_sha}},
                'windows': {'trade_start': '2026-01-01', 'trade_end': '2026-01-03'}}
    performance = {'benchmarks': {'strategy': {'return_fraction': 0.1, 'sharpe': None, 'max_drawdown_fraction': -0.1}}}
    packet = tmp_path / 'source-binding-case'
    packet.mkdir()
    write_json(packet / 'performance.json', performance)
    write_json(packet / 'metadata.json', metadata)
    subject = {**data['provenance'], 'modelRef': 'attempt:original', 'revision': 'original-source',
               'runId': 'original-scan', 'modelSha256': original_model_sha,
               'evaluationFingerprint': sha(packet / 'performance.json')}
    write_json(packet / 'manifest.json', {'subject': subject})
    write_json(packet / 'source-manifest.json', {'schemaVersion': 'strategy-report-source/v1', 'subject': subject,
        'files': [{'path': p.name, 'size': p.stat().st_size, 'sha256': sha(p)}
                  for p in [packet / 'performance.json', packet / 'metadata.json']]})
    return packet, data, {'metadata': metadata, 'performance': performance}


def test_source_binding_uses_imported_evidence_instead_of_subject_claims(lab_binding_case):
    packet, bundle, imported_evidence = lab_binding_case
    api = reports()
    assert api.validate_source_binding(packet, bundle, source_evidence=imported_evidence)['lineage'] == 'verified-original-model-and-source-evaluation'
    # Rehashing attacker-edited source files is insufficient: canonical imported evidence wins.
    edited = json.loads((packet / 'performance.json').read_text())
    edited['benchmarks']['strategy']['return_fraction'] = 0.99
    write_json(packet / 'performance.json', edited)
    source = json.loads((packet / 'source-manifest.json').read_text())
    source['subject']['evaluationFingerprint'] = sha(packet / 'performance.json')
    source['files'][0].update(size=(packet / 'performance.json').stat().st_size, sha256=sha(packet / 'performance.json'))
    write_json(packet / 'source-manifest.json', source)
    write_json(packet / 'manifest.json', {'subject': source['subject']})
    with pytest.raises(api.ReportError, match='performance'):
        api.validate_source_binding(packet, bundle, source_evidence=imported_evidence)


def test_source_binding_rejects_wrong_canonical_window(lab_binding_case):
    packet, bundle, imported_evidence = lab_binding_case
    bundle['evaluation']['endDate'] = '2026-01-04'
    with pytest.raises(reports().ReportError, match='window'):
        reports().validate_source_binding(packet, bundle, source_evidence=imported_evidence)
