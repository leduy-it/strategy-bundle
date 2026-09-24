"""Evaluate a trusted local research checkpoint without updating its weights."""
from __future__ import annotations
import gzip
import json
import os
import pickle
import sys
from datetime import date
from pathlib import Path
from .contract import sha256_file


def replay_lab(source: Path, output: Path, lab_root: Path, backend_root: Path, *, trusted_model=False):
    if not trusted_model:
        raise ValueError('Loading local model code requires --trust-local-model')
    source, output, lab_root, backend_root = (p.resolve() for p in (source, output, lab_root, backend_root))
    if output.exists():
        raise ValueError('Output already exists; replay to a new immutable directory')
    recipe = json.loads((source/'recipe.json').read_bytes())
    meta = json.loads((source/'metadata.json').read_bytes())
    for role, filename in [('model','model.zip'), ('vecnorm','vecnorm.pkl')]:
        if sha256_file(source/filename) != meta['artifact_pair'][role]['sha256']:
            raise ValueError(f'Source hash mismatch: {filename}')
    import hashlib
    trace_bytes = gzip.decompress((source/'trace.json.gz').read_bytes())
    if hashlib.sha256(trace_bytes).hexdigest() != meta['trace']['uncompressed_sha256']:
        raise ValueError('Original trace checksum mismatch')
    original = json.loads(trace_bytes)
    if original['status'] != 'complete' or original['errors']:
        raise ValueError('Original evaluation trace is incomplete')
    if not (lab_root/'strategy_lab/local/train_cell.py').is_file():
        raise ValueError('A complete strategy-lab checkout is required')
    if not (backend_root/'promete_fintech_backend_fastapi/app/core/finrl/agents/stablebaselines3/models.py').is_file():
        raise ValueError('The requested backend checkout is missing its policy loader')
    os.environ['PROMETE_BACKEND'] = str(backend_root)
    sys.path.insert(0, str(lab_root))
    import numpy as np
    import torch
    from strategy_lab.local import dataset as DS, train_cell as T
    from strategy_lab.report.traces import predict_with_trace, expand_env_kwargs
    snapshot = meta['price_and_data']['snapshot']
    data_source = DS.resolve(require_full=True, data_directory=snapshot['directory'])
    if data_source.snapshot_identity != snapshot:
        raise ValueError('Historical data snapshot differs from the original evaluation')
    agent, env_type = T._import_backend()
    from app.core.finrl.agents.stablebaselines3.models import load_policy_model
    torch.set_num_threads(2)
    model = load_policy_model(meta['identity']['algo'], str(source/'model.zip'), device='cpu')
    with (source/'vecnorm.pkl').open('rb') as stream:
        rms = pickle.load(stream).obs_rms
    output.mkdir(parents=True)
    counts = {}
    for window, keys in [('test', ('trade_start','trade_end')), ('train', ('train_start','train_end'))]:
        panel = DS.load_panel(data_source, recipe['features'],
            *[date.fromisoformat(recipe['windows'][key]) for key in keys], recipe['symbols'])
        environment = env_type(df=panel, mode='trade', **expand_env_kwargs(recipe['env_kwargs']))
        _, _, trace = predict_with_trace(agent, model=model, environment=environment, obs_rms=rms)
        if trace['status'] != 'complete' or trace['errors']:
            raise ValueError(f'{window} replay is incomplete')
        nav = [s['nav'] for s in trace['snapshots']]
        if window == 'test':
            expected = [s['nav'] for s in original['snapshots']]
            if (len(nav) != len(expected) or not np.allclose(nav, expected, rtol=0, atol=.01)
                    or trace['trades'] != original['trades']):
                raise ValueError('Original OOS NAV or executed trades diverged; refusing in-sample replay')
        trace['replay_provenance'] = {'mode':'frozen_checkpoint_evaluation', 'window':window,
            'source_model_sha256':meta['artifact_pair']['model']['sha256'], 'oos_verified_against_original':True,
            'source_normalizer_sha256':meta['artifact_pair']['vecnorm']['sha256'],
            'adapter_sha256':sha256_file(Path(__file__))}
        (output/f'{window}-trace.json.gz').write_bytes(gzip.compress(json.dumps(trace, allow_nan=False).encode()))
        baselines = T.session_baseline_curves(data_source, panel, [s['date'] for s in trace['snapshots']])
        (output/f'{window}-baselines.json').write_text(json.dumps(baselines, allow_nan=False,
            default=lambda v: v.tolist() if hasattr(v, 'tolist') else str(v)))
        counts[window] = {'navRows':len(nav), 'executions':len(trace['trades'])}
    return {'output':str(output), 'modelRef':source.name, 'windows':counts}
