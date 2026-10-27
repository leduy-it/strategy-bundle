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
