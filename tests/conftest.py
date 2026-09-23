import hashlib
import json
import zipfile
from pathlib import Path
import pytest


def make_bundle(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(root / 'model.zip', 'w') as z:
        z.writestr('data', '{}')
        z.writestr('policy.pth', b'test structural fixture; not an executable model')
    files = {
      'metadata.json': ('training_metadata', {'data': {'symbols':['FPT']}, 'features': {'feature_list':['close']}, 'hyperparameters': {'algorithm':'ppo','normalize_env':False}, 'env_config':{'state_space':4,'action_space':1}}),
      'card.json': ('xai_card', {'run_id':'fixture-source-run', 'raw_metrics':{'total_return':0.1}, 'elevator_pitch':'Synthetic import test — not an investment strategy'}),
      'xai-manifest.json': ('xai_manifest', {'config': {'universe':['FPT'], 'test_start':'2026-01-01', 'test_end':'2026-01-02'}}),
      'ohlcv.json': ('ohlcv', [{'symbol':'FPT','date':'2026-01-01','open':100,'high':101,'low':99,'close':100,'volume':1000}]),
    }
    roles={'model.zip':'model','trace.jsonl':'xai_trace'}
    for name,(role,data) in files.items():
        (root/name).write_text(json.dumps(data));roles[name]=role
    trace=[{'step':0,'date':'2026-01-01','action_executed':[0.0],'port_value':1000,'reward':0}, {'step':1,'date':'2026-01-02','action_executed':[0.0],'port_value':1100,'reward':0.1}]
    (root/'trace.jsonl').write_text('\n'.join(json.dumps(r) for r in trace)+'\n')
    data={
      'schemaVersion':'sample-strategy-bundle/v1',
      'provenance':{'repository':'test://synthetic','revision':'test-v1','runId':'fixture-source-run','modelRef':'fixture-ppo','seed':1,'trainedAt':'2026-01-01T00:00:00Z','evidence':'ORIGINAL'},
      'strategy':{'name':'Synthetic import test','description':'Synthetic test data, not a research result.','config':{'stocks':['FPT'],'algorithm':'ppo','initialCapital':1000},'riskLevel':'MEDIUM','horizon':'SWING','universe':'FPT','authorLabel':'Test fixture','research':{'certified':False,'purpose':'integration test'}},
      'model':{'algorithm':'ppo','symbols':['FPT'],'features':['close'],'timesteps':32,'normalization':'none','observationSize':4,'actionSize':1,'libraryVersions':{'stable-baselines3':'2.7.1'},'envContract':{'state_space':4,'action_space':1}},
      'evaluation':{'role':'test','ratioUnit':'fraction','startDate':'2026-01-01','endDate':'2026-01-02','initialCapital':1000,'transactionFee':0.001,'taxRate':0.001,'slippage':0.0,'settlementDays':2,
        'metrics':{'totalReturn':0.1,'maxDrawdown':0.0,'sharpeRatio':None,'winRate':None,'totalTrades':0,'nullReasons':{'sharpeRatio':'Too few observations','winRate':'No trades'}},
        'nav':[{'date':'2026-01-01','balance':1000},{'date':'2026-01-02','balance':1100}],
        'trades':[],'actions':[{'date':r['date'],'actions':r['action_executed']} for r in trace],
        'terminalPositions':{'nav':1100,'cash_liquid':1100,'cash_in_settlement':0,'stock_count':0,'positions':[]},'baselines':{'buyAndHold':{'totalReturn':0.05},'vnIndex':{'totalReturn':0.02}}},
      'artifacts':[{'id':str(i),'role':roles[name],'path':name,'size':(root/name).stat().st_size,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()} for i,name in enumerate(roles)]
    }
    (root/'manifest.json').write_text(json.dumps(data))
    return data

@pytest.fixture
def bundle_dir(tmp_path):
    make_bundle(tmp_path)
    return tmp_path
