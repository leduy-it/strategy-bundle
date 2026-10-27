"""Offline facade over the pinned, unmodified strategy-sample-report skill.

This module imports only the standard library. It never trains, authors prose,
contacts an API, loads model weights, or certifies financial claims.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import importlib.util
from importlib import resources
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


class ReportError(ValueError):
    """Machine-readable failure shared by Python and the report CLI."""

    def __init__(self, message: str, code: str = 'invalid_input'):
        super().__init__(message)
        self.code = code


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _json(path: Path) -> dict:
    _no_symlinks(path)
    try:
        data = json.loads(path.read_text(encoding='utf-8'), parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    except (ValueError, OSError) as exc:
        raise ReportError(f'Cannot read JSON {path.name}: {exc}') from exc
    if not isinstance(data, dict):
        raise ReportError(f'{path.name} must contain a JSON object')
    return data


def _write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def _no_symlinks(path: Path) -> None:
    cursor = Path(path.absolute().anchor)
    for part in path.absolute().parts[1:]:
        cursor /= part
        if cursor.is_symlink():
            raise ReportError(f'symlink input/output is forbidden: {cursor}')


def _file(root: Path, relative: str, *, allow_parent: bool = False) -> Path:
    if not isinstance(relative, str) or not relative or '\\' in relative or '\x00' in relative:
        raise ReportError('file path must be a nonempty POSIX relative path')
    rel = Path(relative)
    if rel.is_absolute():
        raise ReportError('absolute file paths are forbidden')
    if '..' in rel.parts and not allow_parent:
        raise ReportError(f'path outside report packet: {relative}')
    candidate = root / rel
    _no_symlinks(candidate)
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ReportError(f'path outside trusted source root: {relative}')
    if not resolved.is_file():
        raise ReportError(f'file does not exist or is not regular: {relative}')
    return resolved


def _entry(path: Path, relative: str, role: str | None = None) -> dict:
    data = path.read_bytes()
    result = {'path': relative, 'size': len(data), 'sha256': _sha(data)}
    if role:
        result['role'] = role
    return result


def _verify_entry(root: Path, entry: dict) -> Path:
    if not isinstance(entry, dict):
        raise ReportError('manifest file entry must be an object')
    path = _file(root, entry.get('path'))
    actual = _entry(path, entry['path'])
    if actual['size'] != entry.get('size') or actual['sha256'] != entry.get('sha256'):
        raise ReportError(f'hash/size mismatch: {entry["path"]}')
    return path


@contextmanager
def _output(destination: Path):
    destination = Path(destination).absolute()
    _no_symlinks(destination)
    if destination.exists():
        raise ReportError(f'output already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.report-', dir=destination.parent) as temporary:
        stage = Path(temporary) / 'result'
        stage.mkdir()
        yield stage
        _no_symlinks(destination)
        if destination.exists():
            raise ReportError(f'output already exists: {destination}')
        os.replace(stage, destination)


def _skill_bytes() -> tuple[dict, dict[str, bytes], str]:
    root = resources.files('promete_strategy_bundle').joinpath('report_skill')
    manifest_bytes = root.joinpath('manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    payload = {}
    for entry in manifest['files']:
        rel = entry['path']
        if Path(rel).is_absolute() or '..' in Path(rel).parts or '\\' in rel:
            raise ReportError('unsafe bundled skill manifest', 'skill_integrity')
        data = root.joinpath(rel).read_bytes()
        if len(data) != entry['size'] or _sha(data) != entry['sha256']:
            raise ReportError(f'bundled skill hash mismatch: {rel}', 'skill_integrity')
        payload[rel] = data
    payload['manifest.json'] = manifest_bytes
    return manifest, payload, _sha(manifest_bytes)


def export_report_skill(destination: Path) -> dict:
    """Export the exact skill and its evidence-policy sibling; never overwrite."""
    manifest, payload, digest = _skill_bytes()
    with _output(destination) as stage:
        for rel, data in payload.items():
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        guide = resources.files('promete_strategy_bundle').joinpath('report_skill', 'PORTABLE.md').read_text()
        (stage / 'PORTABLE.md').write_text(guide, encoding='utf-8')
    return {'skillPath': str(Path(destination).absolute() / 'strategy-sample-report' / 'SKILL.md'),
            'skillManifestSha256': digest, 'files': len(manifest['files']), 'source': manifest['source']}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReportError(message)


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _numbers(values, count=None) -> bool:
    return (isinstance(values, list) and bool(values) and (count is None or len(values) == count)
            and all(type(v) in (int, float) and math.isfinite(v) for v in values))


def _structure(spec: dict, stem: str) -> list[tuple[dict, str]]:
    """Check the existing renderer format and return only files it consumes."""
    name = spec.get('output_name', stem)
    _require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', name) is not None
             and name not in ('.', '..'), 'output_name must be a safe filename stem')
    cover = spec.get('cover')
    _require(isinstance(cover, dict) and all(_text(cover.get(k)) for k in ('title', 'number_line')),
             'cover.title and cover.number_line are required')
    _require(isinstance(cover.get('facts', []), list) and all(isinstance(r, list) and len(r) == 2
             and all(isinstance(v, str) for v in r) for r in cover.get('facts', [])), 'cover.facts must be text pairs')
    _require(isinstance(spec.get('toc', {}), dict) and isinstance(spec.get('options', {}), dict),
             'toc/options must be objects')
    sections = spec.get('sections')
    _require(isinstance(sections, list) and bool(sections), 'sections must be a nonempty list')
    references = []
    for section in sections:
        _require(isinstance(section, dict) and _text(section.get('title'))
                 and isinstance(section.get('blocks', []), list), 'each section requires title and blocks')
        for block in section.get('blocks', []):
            _require(isinstance(block, dict), 'block must be an object')
            kind = block.get('type')
            _require(kind in {'p', 'h2', 'bullets', 'numbered', 'table', 'chart', 'image', 'note', 'page_break'},
                     f'unsupported block type: {kind}')
            if kind in {'p', 'h2', 'note'}:
                _require(_text(block.get('text')), f'{kind}.text is required')
            elif kind in {'bullets', 'numbered'}:
                _require(isinstance(block.get('items'), list) and all(_text(t) for t in block['items']),
                         f'{kind}.items must contain text')
            elif kind == 'image':
                _require(_text(block.get('path')), 'image.path is required')
                references.append((block, 'path'))
            elif kind == 'table':
                columns = block.get('columns')
                _require(isinstance(columns, list) and bool(columns) and all(_text(c) for c in columns),
                         'table.columns must contain text')
                _require(isinstance(block.get('rows'), list) and all(isinstance(r, list) and len(r) == len(columns)
                         and all(isinstance(v, str) for v in r) for r in block['rows']), 'table row width/text mismatch')
            elif kind == 'chart':
                chart_kind = block.get('kind', 'bar')
                _require(chart_kind in {'bar', 'line'}, 'chart.kind must be bar or line')
                if chart_kind == 'line':
                    _require(isinstance(block.get('series'), list) and bool(block['series']), 'line.series is required')
                    for series in block['series']:
                        _require(isinstance(series, dict) and _text(series.get('name')), 'line series requires name')
                        if 'csv' in series:
                            _require(all(_text(series.get(k)) for k in ('csv', 'x', 'y')), 'CSV series requires csv/x/y')
                            references.append((series, 'csv'))
                        else:
                            _require(isinstance(series.get('x'), list) and all(_text(x) for x in series['x'])
                                     and _numbers(series.get('y'), len(series['x'])), 'line x/y arrays must match')
                else:
                    labels = block.get('labels')
                    _require(isinstance(labels, list) and bool(labels) and all(_text(x) for x in labels), 'bar.labels required')
                    if 'series' in block:
                        _require(isinstance(block['series'], list) and bool(block['series']) and all(
                            isinstance(s, dict) and _text(s.get('name')) and _numbers(s.get('values'), len(labels))
                            for s in block['series']), 'bar series values must match labels')
                    else:
                        _require(_numbers(block.get('values'), len(labels)), 'bar values must match labels')
    return references


def _lint(spec: dict) -> list[str]:
    # Execute only the original trusted lint function, unchanged. Importing the
    # renderer module would eagerly require python-docx even for offline checks.
    # This keeps one editorial rule implementation and a dependency-light CLI.
    _, payload, _ = _skill_bytes()
    source = payload['strategy-sample-report/scripts/build_report.py'].decode('utf-8')
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'lint')
    module = ast.Module(body=[function], type_ignores=[])
    with tempfile.TemporaryDirectory(prefix='report-lint-') as temp:
        assets = Path(temp) / 'assets'
        (assets / 'fonts').mkdir(parents=True)
        (assets / 'fonts' / 'Lexend-Light.ttf').write_bytes(payload['strategy-sample-report/assets/fonts/Lexend-Light.ttf'])
        namespace = {'json': json, 're': re, 'ASSETS': assets}
        exec(compile(module, '<pinned strategy-sample-report lint>', 'exec'), namespace)
        return namespace['lint'](spec)


def _subject(value: dict) -> dict:
    _require(isinstance(value, dict), 'source subject must be an object')
    for key in ('repository', 'revision', 'runId', 'modelRef'):
        _require(_text(value.get(key)), f'source subject.{key} is required')
    _require(type(value.get('seed')) is int, 'source subject.seed must be an integer')
    _require(isinstance(value.get('evaluationFingerprint'), str)
             and re.fullmatch('[0-9a-f]{64}', value['evaluationFingerprint']) is not None,
             'source subject.evaluationFingerprint must be a SHA-256')
    return value


def _sources(path: Path, *, root: Path | None = None, allow_parent: bool = False) -> dict:
    data = _json(path)
    _require(data.get('schemaVersion') == 'strategy-report-source/v1', 'unsupported source manifest schemaVersion')
    _subject(data.get('subject'))
    _require(isinstance(data.get('files'), list) and bool(data['files']), 'source manifest requires source files')
    seen = set()
    for item in data['files']:
        _require(isinstance(item, dict) and isinstance(item.get('path'), str)
                 and item['path'] not in seen, 'duplicate or malformed source file')
        file = _file(root or path.parent, item.get('path'), allow_parent=allow_parent)
        actual = _entry(file, item['path'])
        _require(actual['sha256'] == item.get('sha256') and actual['size'] == item.get('size'),
                 f'source hash/size mismatch: {item["path"]}')
        seen.add(item['path'])
    return data


def _validate(spec_path: Path, *, trusted_root: Path | None = None) -> tuple[dict, list[tuple[dict, str]], dict]:
    spec_path = Path(spec_path).absolute()
    _no_symlinks(spec_path)
    _require(spec_path.is_file(), f'report spec does not exist: {spec_path}')
    root = Path(trusted_root).absolute() if trusted_root is not None else spec_path.parent
    _no_symlinks(root)
    _require(spec_path.resolve().is_relative_to(root.resolve()), 'report spec outside trusted source root')
    spec = _json(spec_path)
    references = _structure(spec, spec_path.stem)
    files = []
    for owner, key in references:
        rel = owner[key]
        # Resolve relative to the spec while enforcing the explicitly selected root.
        _require(isinstance(rel, str) and not Path(rel).is_absolute() and '\\' not in rel, 'absolute/non-POSIX asset path')
        candidate = spec_path.parent / rel
        _no_symlinks(candidate)
        _require(candidate.resolve().is_relative_to(root.resolve()), f'asset outside trusted source root: {rel}')
        if trusted_root is None:
            _require('..' not in Path(rel).parts, f'asset outside report packet: {rel}')
        file = _file(root, str(candidate.resolve().relative_to(root.resolve())))
        files.append(_entry(file, rel, 'asset'))
    issues = _lint(spec)
    if issues:
        raise ReportError('Editorial lint: ' + '; '.join(issues))
    return spec, references, {'valid': True, 'scope': 'structure-files-editorial-lint',
                              'financialClaimsVerified': False, 'assets': files,
                              'glyphCheck': importlib.util.find_spec('fontTools') is not None,
                              'skillManifestSha256': _skill_bytes()[2]}


def validate_report(spec: Path) -> dict:
    """Validate a local, contained content spec, without requiring render extras."""
    return _validate(Path(spec))[2]


def prepare_report(source: Path, output: Path, *, source_root: Path | None = None) -> dict:
    """Copy existing content/facts; authoring remains the exported skill's job.

    Legacy specs can refer outside their own directory only with an explicit
    trusted source_root. All consumed bytes are then copied and paths rebased.
    source-manifest paths are relative to source_root (or the spec directory).
    """
    source = Path(source)
    _no_symlinks(source)
    spec_path = source / 'report.json' if source.is_dir() else source
    spec, references, _ = _validate(spec_path, trusted_root=source_root)
    base = spec_path.absolute().parent
    trusted = Path(source_root).absolute() if source_root is not None else base
    source_manifest = base / 'source-manifest.json'
    sources = _sources(source_manifest, root=trusted) if source_manifest.exists() else None
    facts_path = base / 'facts.json'
    if facts_path.exists():
        _no_symlinks(facts_path)
        _json(facts_path)
    original_sha = _sha(spec_path.read_bytes())
    with _output(output) as stage:
        for owner, key in references:
            file = (base / owner[key]).resolve()
            relative = 'assets/' + _sha(file.read_bytes()) + file.suffix.lower()
            (stage / 'assets').mkdir(exist_ok=True)
            shutil.copyfile(file, stage / relative)
            owner[key] = relative
        _write(stage / 'report.json', spec)
        if facts_path.exists():
            shutil.copyfile(facts_path, stage / 'facts.json')
        if sources:
            for index, item in enumerate(sources['files']):
                file = _file(trusted, item['path'])
                relative = f'sources/{index:04d}-' + item['sha256'] + file.suffix.lower()
                (stage / 'sources').mkdir(exist_ok=True)
                shutil.copyfile(file, stage / relative)
                item['path'] = relative
            _write(stage / 'source-manifest.json', sources)
        preparation = {'schemaVersion': 'strategy-report-preparation/v1', 'status': 'draft',
                       'sourceSpecSha256': original_sha, 'skillManifestSha256': _skill_bytes()[2]}
        _write(stage / 'preparation.json', preparation)
    return {**preparation, 'spec': str(Path(output).absolute() / 'report.json')}


def _input_entries(spec: Path, *, required: bool = False) -> list[dict]:
    _, _, checked = _validate(spec)
    root = spec.absolute().parent
    entries = [_entry(spec, spec.name, 'report_spec')]
    for item in checked['assets']:
        entries.append(_entry(_file(root, item['path']), item['path'], 'asset'))
    for name, role in [('facts.json', 'facts'), ('source-manifest.json', 'source_manifest')]:
        path = root / name
        if required:
            _require(path.is_file(), f'import-ready report requires {name}')
        if path.exists():
            _no_symlinks(path)
            _json(path)
            entries.append(_entry(path, name, role))
    if (root / 'source-manifest.json').exists():
        source = _sources(root / 'source-manifest.json')
        for item in source['files']:
            entries.append(_entry(_file(root, item['path']), item['path'], 'source'))
        if (root / 'facts.json').exists():
            identity = _json(root / 'facts.json').get('identity', {})
            _require(isinstance(identity, dict), 'facts.identity must be an object')
            for fk, sk in [('model_id', 'modelRef'), ('seed', 'seed')]:
                if fk in identity:
                    _require(identity[fk] == source['subject'][sk], f'facts identity/subject mismatch: {fk}')
    # Shared chart sources can appear more than once; seal each path once.
    return sorted({e['path']: e for e in entries}.values(), key=lambda e: e['path'])


def _render_dependencies() -> None:
    missing = [name for name in ['docx', 'matplotlib', 'fontTools'] if importlib.util.find_spec(name) is None]
    tools = [name for name in ['soffice', 'fc-list', 'fc-cache', 'pdfinfo', 'pdftotext', 'pdffonts']
             if shutil.which(name) is None]
    if missing or tools:
        raise ReportError('Rendering requires pip install "promete-strategy-bundle[report]"; '
                          f'missing Python modules: {", ".join(missing) or "none"}; '
                          f'missing system tools: {", ".join(tools) or "none"} '
                          '(install LibreOffice, poppler-utils, fontconfig)', 'missing_dependency')


def render_report(spec: Path, output: Path) -> dict:
    """Run the exact upstream renderer; outputs carry an input-bound receipt.

    The rendering procedure is pinned, but PDF/DOCX binary timestamps depend on
    LibreOffice/python-docx. This is not a byte-reproducibility guarantee.
    """
    _render_dependencies()
    spec = Path(spec).absolute()
    inputs = _input_entries(spec)
    with _output(output) as stage, tempfile.TemporaryDirectory(prefix='report-skill-') as temporary:
        skill = Path(temporary) / 'skill'
        exported = export_report_skill(skill)
        command = [sys.executable, str(skill / 'strategy-sample-report/scripts/build_report.py'),
                   str(spec), '--out-dir', str(stage), '--strict']
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=900)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ReportError(f'Pinned renderer failed: {exc}', 'render_failed') from exc
        if process.returncode:
            raise ReportError(f'Pinned renderer exited {process.returncode}: '
                              f'{process.stderr[-4000:]} {process.stdout[-2000:]}', 'render_failed')
        try:
            result = json.loads(process.stdout)
        except ValueError as exc:
            raise ReportError('Pinned renderer returned invalid JSON', 'render_failed') from exc
        _require(not result.get('lint') and not result.get('non_lexend_fonts'),
                 f'Rendered document requires review: {result}')
        _require(inputs == _input_entries(spec), 'report input changed while rendering')
        artifacts = []
        for role in ['pdf', 'docx']:
            path = Path(result[role])
            _require(path.is_file() and path.parent == stage, 'renderer output escaped destination')
            artifacts.append(_entry(path, path.name, role))
            result[role] = str(Path(output).absolute() / path.name)
        receipt = {'schemaVersion': 'strategy-report-render/v1',
                   'skillManifestSha256': exported['skillManifestSha256'],
                   'inputs': inputs, 'artifacts': artifacts,
                   'lint': result['lint'], 'non_lexend_fonts': result['non_lexend_fonts']}
        _write(stage / 'render.json', receipt)
    return {**result, 'receipt': str(Path(output).absolute() / 'render.json'),
            'skillManifestSha256': exported['skillManifestSha256']}


def _pdf(path: Path) -> None:
    data = path.read_bytes()
    _require(data.startswith(b'%PDF-') and b'%%EOF' in data[-1024:], 'report PDF signature/trailer invalid')


def _receipt(path: Path, inputs: list[dict]) -> dict:
    receipt = _json(path)
    _require(receipt.get('schemaVersion') == 'strategy-report-render/v1', 'unsupported render receipt')
    _require(receipt.get('skillManifestSha256') == _skill_bytes()[2], 'render receipt skill version mismatch')
    _require(receipt.get('inputs') == inputs, 'render receipt input hash mismatch; render again')
    _require(receipt.get('lint') == [] and receipt.get('non_lexend_fonts') == [], 'render receipt failed quality checks')
    _require(isinstance(receipt.get('artifacts'), list) and {e.get('role') for e in receipt['artifacts']} == {'pdf', 'docx'}
             and len(receipt['artifacts']) == 2, 'render receipt requires PDF and DOCX')
    for entry in receipt['artifacts']:
        file = _verify_entry(path.parent, entry)
        if entry['role'] == 'pdf':
            _pdf(file)
    return receipt


def pack_report(prepared: Path, rendered: Path, output: Path) -> dict:
    """Seal rendered PDF + content + facts + checked sources into a local packet."""
    prepared, rendered = Path(prepared).absolute(), Path(rendered).absolute()
    _no_symlinks(prepared)
    _no_symlinks(rendered)
    inputs = _input_entries(prepared / 'report.json', required=True)
    receipt_path = _file(rendered, 'render.json')
    receipt = _receipt(receipt_path, inputs)
    subject = _sources(prepared / 'source-manifest.json')['subject']
    with _output(output) as stage:
        files = []
        for entry in inputs:
            relative = entry['path']
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_file(prepared, relative), target)
            files.append(_entry(target, relative, entry['role']))
        for entry in receipt['artifacts']:
            relative = 'report.' + entry['role']
            target = stage / relative
            _require(not target.exists(), f'packet artifact collision: {relative}')
            shutil.copyfile(_file(rendered, entry['path']), target)
            files.append(_entry(target, relative, entry['role']))
        # Preserve original output filenames so receipt can still verify them.
        # Packet receipt uses its own artifact paths, with unchanged byte hashes.
        packet_receipt = {**receipt, 'artifacts': [e for e in files if e['role'] in {'pdf', 'docx'}]}
        _write(stage / 'render.json', packet_receipt)
        files.append(_entry(stage / 'render.json', 'render.json', 'render_receipt'))
        manifest = {'schemaVersion': 'strategy-report-package/v1', 'subject': subject,
                    'skillManifestSha256': _skill_bytes()[2],
                    'checks': {'fileIntegrity': True, 'financialClaimsVerified': False, 'humanReview': 'required'},
                    'files': sorted(files, key=lambda e: e['path'])}
        manifest['packageDigest'] = _sha(_canonical(manifest))
        _write(stage / 'manifest.json', manifest)
        checked = validate_import_report(stage)
    return {**checked, 'path': str(Path(output).absolute())}


def validate_import_report(packet: Path, *, expected_subject: dict | None = None,
                           expected_binding: dict | None = None, require_binding: bool = False) -> dict:
    """Check transport readiness, never investment approval or backend import.

    A backend must compare expected_subject to its canonical model/evaluation
    binding, enforce authorization and apply its independent review policy.
    """
    packet = Path(packet).absolute()
    _no_symlinks(packet)
    manifest = _json(_file(packet, 'manifest.json'))
    _require(manifest.get('schemaVersion') == 'strategy-report-package/v1', 'unsupported report package schemaVersion')
    subject = _subject(manifest.get('subject'))
    if expected_subject is not None:
        _require(subject == expected_subject, 'report subject does not match expected subject')
    _require(manifest.get('skillManifestSha256') == _skill_bytes()[2], 'report skill version mismatch')
    digest = manifest.get('packageDigest')
    _require(digest == _sha(_canonical({k: v for k, v in manifest.items() if k != 'packageDigest'})),
             'report package digest mismatch')
    files = manifest.get('files')
    _require(isinstance(files, list) and bool(files), 'report package requires files')
    seen = set()
    required = {'report_spec': 'report.json', 'facts': 'facts.json', 'source_manifest': 'source-manifest.json',
                'render_receipt': 'render.json', 'pdf': 'report.pdf', 'docx': 'report.docx'}
    for entry in files:
        _verify_entry(packet, entry)
        _require(entry['path'] not in seen, 'duplicate report package path')
        seen.add(entry['path'])
    for role, path in required.items():
        _require(sum(e.get('role') == role for e in files) == 1
                 and any(e.get('role') == role and e['path'] == path for e in files),
                 f'import-ready package requires {role}: {path}')
    actual_paths = set()
    for path in packet.rglob('*'):
        _no_symlinks(path)
        if path.is_file():
            actual_paths.add(str(path.relative_to(packet)))
    _require(actual_paths == seen | {'manifest.json'}, 'undeclared or missing files in report packet')
    inputs = _input_entries(packet / 'report.json', required=True)
    _require({e['path'] for e in inputs} <= seen, 'report inputs not sealed by package manifest')
    source = _sources(packet / 'source-manifest.json')
    _require(source['subject'] == subject, 'source manifest subject mismatch')
    _receipt(packet / 'render.json', inputs)
    binding = manifest.get('binding')
    if require_binding or expected_binding is not None:
        _require(isinstance(binding, dict), 'platform report requires bundle binding')
    if binding is not None:
        _require(isinstance(binding, dict) and all(isinstance(binding.get(k), str)
                 and re.fullmatch('[0-9a-f]{64}', binding[k]) for k in
                 ['bundleFingerprint', 'modelSha256', 'evaluationFingerprint'])
                 and isinstance(binding.get('provenance'), dict), 'invalid report binding')
    if expected_binding is not None:
        _require(binding == expected_binding, 'report binding does not match canonical model/evaluation')
    return {'valid': True, 'importReady': True, 'scope': 'offline-transport-integrity',
            'financialClaimsVerified': False, 'humanReview': 'required', 'subject': subject,
            'packageDigest': digest, 'skillManifestSha256': manifest['skillManifestSha256'],
            'platformBindingReady': binding is not None}


def report_binding(bundle) -> dict:
    """Canonical binding; Path inputs are verified, Bundle inputs must be validated."""
    from .contract import Bundle, fingerprint, verify_bundle
    bundle = verify_bundle(Path(bundle)) if isinstance(bundle, (str, Path)) else bundle
    bundle = Bundle.model_validate(bundle) if isinstance(bundle, dict) else bundle
    models = [a for a in bundle.artifacts if a.role == 'model']
    _require(len(models) == 1, 'bundle requires one model artifact')
    return {'bundleFingerprint': fingerprint(bundle), 'modelSha256': models[0].sha256,
            'evaluationFingerprint': _sha(_canonical(bundle.evaluation.model_dump(mode='json'))),
            'provenance': bundle.provenance.model_dump(mode='json')}


def validate_source_binding(packet: Path, bundle, *, source_evidence: dict | None = None) -> dict:
    """Shared SDK/server lineage check against an independently verified bundle.

    The server supplies source_evidence loaded from its sealed imported research
    artifact, never from a client-selected external path. Source subject identity
    is preserved separately from the normalized model import provenance.
    """
    data = bundle.model_dump(mode='json') if hasattr(bundle, 'model_dump') else bundle
    _require(isinstance(data, dict), 'canonical bundle must be an object')
    packet = Path(packet)
    manifest = _json(_file(packet, 'manifest.json'))
    subject = _subject(manifest.get('subject'))
    provenance = data['provenance']
    binding = report_binding(data)
    source_hashes = data['strategy'].get('research', {}).get('sourceHashes', {})
    original_model = source_hashes.get('model', {}).get('sha256') if isinstance(source_hashes, dict) else None
    if not original_model:
        _require(all(subject.get(k) == provenance[k] for k in ['repository', 'revision', 'runId', 'modelRef', 'seed'])
                 and subject.get('modelSha256') == binding['modelSha256']
                 and subject['evaluationFingerprint'] == binding['evaluationFingerprint'],
                 'source subject/model/evaluation does not match canonical bundle')
        return {'valid': True, 'lineage': 'exact-canonical-provenance'}
    _require(subject.get('modelSha256') == original_model and subject['seed'] == provenance['seed']
             and subject['repository'] == provenance['repository'], 'source checkpoint hash/seed/repository mismatch')
    _require(isinstance(source_evidence, dict) and isinstance(source_evidence.get('metadata'), dict)
             and isinstance(source_evidence.get('performance'), dict), 'canonical source-evidence artifact required')
    metadata, performance = source_evidence['metadata'], source_evidence['performance']
    _require(metadata.get('model_id') == subject['modelRef'], 'source model identity mismatch')
    _require(metadata.get('artifact_pair', {}).get('model', {}).get('sha256') == original_model,
             'source evidence model hash mismatch')
    windows = metadata.get('windows', {})
    _require(windows.get('trade_start') == data['evaluation']['startDate']
             and windows.get('trade_end') == data['evaluation']['endDate'], 'source evaluation window mismatch')
    declared = _sources(packet / 'source-manifest.json')['files']
    documents = []
    for entry in declared:
        path = _file(packet, entry['path'])
        if path.suffix.lower() == '.json':
            documents.append((entry, _json(path)))
    _require(any(document == metadata for _, document in documents), 'packet lacks canonical source metadata')
    _require(any(document == performance and entry['sha256'] == subject['evaluationFingerprint']
                 for entry, document in documents), 'packet source performance/evaluation fingerprint mismatch')
    metrics = performance.get('benchmarks', {}).get('strategy', {})
    expected = data['evaluation']['metrics']
    for source_key, bundle_key, negate in [('return_fraction', 'totalReturn', False),
                                          ('sharpe', 'sharpeRatio', False),
                                          ('max_drawdown_fraction', 'maxDrawdown', True)]:
        value = metrics.get(source_key)
        if value is not None and negate:
            value = -abs(value)
        actual = expected.get(bundle_key)
        _require((value is None and actual is None) or (type(value) in (int, float)
                 and type(actual) in (int, float) and math.isclose(value, actual, abs_tol=1e-8, rel_tol=1e-8)),
                 f'source headline metric does not match canonical evaluation: {bundle_key}')
    return {'valid': True, 'lineage': 'verified-original-model-and-source-evaluation'}


def bind_report(packet: Path, bundle: Path, output: Path) -> dict:
    """Bind a rendered packet to the verified model bundle before any upload."""
    from .contract import artifact_path, verify_bundle
    packet, bundle = Path(packet), Path(bundle)
    validate_import_report(packet)
    canonical = verify_bundle(bundle)
    evidence = None
    for artifact in canonical.artifacts:
        if artifact.role == 'research' and Path(artifact.path).name == 'source-evidence.json':
            evidence = _json(artifact_path(bundle, artifact.path))
    validate_source_binding(packet, canonical, source_evidence=evidence)
    binding = report_binding(canonical)
    with _output(output) as stage:
        for path in packet.rglob('*'):
            if path.is_file():
                target = stage / path.relative_to(packet)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        manifest = _json(stage / 'manifest.json')
        manifest['binding'] = binding
        manifest.pop('packageDigest', None)
        manifest['packageDigest'] = _sha(_canonical(manifest))
        _write(stage / 'manifest.json', manifest)
        result = validate_import_report(stage, expected_binding=binding)
    return {**result, 'path': str(Path(output).absolute())}
