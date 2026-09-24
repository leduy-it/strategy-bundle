"""Export a pinned research-model-package-v1 without training or replacing data.

Source checkpoints and traces are hash checked. Pickle conversion is opt-in and
only for a trusted local VecNormalize; the network bundle contains JSON stats.
"""
from __future__ import annotations
import csv
import gzip
import json
import math
import shutil
from collections import defaultdict, deque
from pathlib import Path
from .contract import Bundle, sha256_file


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2))


def canvas(recipe, algorithm):
    """The same node/data contract used by the platform training canvas."""
    env, windows = recipe['env_kwargs'], recipe['windows']
    nodes = [
      {'id':'start-node','type':'dataNode','position':{'x':80,'y':160},'data':{
        'label':'Bắt đầu','nodeType':'startNode','selectedStocks':recipe['symbols'],
        'trainingRange':{'start':windows['train_start'],'end':windows['train_end']},
        'tradingRange':{'start':windows['trade_start'],'end':windows['trade_end']},
        'initialCapital':env['initial_amount'],'hmax':env['hmax'],
        'executionParameters':{k:(v['uniform'] if isinstance(v,dict) and set(v)=={'uniform','n'} else v)
                               for k,v in env.items() if k not in ('tech_indicator_list','num_stock_shares')},
      }},
      {'id':'import-features','type':'dataRetrievalNode','position':{'x':430,'y':160},'data':{
        'label':'Truy xuất dữ liệu','nodeType':'dataRetrievalNode','selectedTechnical':recipe['features'],
      }},
      {'id':'import-agent','type':'agentNode','position':{'x':780,'y':160},'data':{
        'label':'Mô hình '+algorithm.upper(),'nodeType':'agentNode','selectedModel':algorithm,
        'modelNotSet':False,'hyperparameters':recipe['hyperparams'],
        'trainingParameters':{'timesteps':recipe['timesteps'], **recipe.get('training_observation',{})},
      }},
    ]
    edges=[{'id':f'import-edge-{i}','source':a,'target':b,'type':'default'} for i,(a,b) in enumerate([('start-node','import-features'),('import-features','import-agent')])]
    return {'nodes':nodes,'edges':edges,'provenance':'DERIVED_FROM_RESOLVED_CONFIG'}


def evaluation_data(trace, recipe, *, source_row=None):
    import numpy as np
    symbols=recipe["symbols"]; env=recipe["env_kwargs"]; initial=float(env["initial_amount"])
    snapshots=trace["snapshots"]; dates=[s["date"] for s in snapshots]
    nav=np.asarray([s["nav"] for s in snapshots],dtype=float); hmax=env["hmax"]
    # Full FIFO realized returns and per-fill costs from the recorded executions.
    buy_rate=env['buy_cost_pct']['uniform'];sell_rate=env['sell_cost_pct']['uniform']
    lots=defaultdict(deque);trades=[];actions={d:[0.0]*len(symbols) for d in dates}
    flows=defaultdict(lambda:defaultdict(float));closed=[]
    for t in trace['trades']:
        symbol=t['symbol'];day=t['execution_date'];qty=int(t['shares']);price=float(t['price'])
        if qty != t['shares']:raise ValueError('Fractional share execution unsupported')
        notional=qty*price;cost=float(t['fee_amount_from_config']);buy=t['side']=='buy'
        # Source recipe explicitly separates .15% broker fee and .10% sell tax.
        buy_rate=env['buy_cost_pct']['uniform'];sell_rate=env['sell_cost_pct']['uniform']
        fee=notional*buy_rate;tax=cost-fee if not buy else 0.0
        if tax < -.001:raise ValueError('Source costs do not fit fee/tax contract')
        pnl=pnl_pct=pnl_net=None
        if buy:lots[symbol].append([qty,price+cost/qty])
        else:
            remaining=qty;basis=0.0
            while remaining:
                if not lots[symbol]:raise ValueError('Source sells exceed recorded inventory')
                lot=lots[symbol][0];used=min(remaining,lot[0]);basis+=used*lot[1];remaining-=used;lot[0]-=used
                if not lot[0]:lots[symbol].popleft()
            pnl_net=notional-cost-basis;pnl=pnl_net+cost;pnl_pct=pnl_net/basis*100;closed.append(pnl_net)
        trades.append({'date':day,'symbol':symbol,'action':'BUY' if buy else 'SELL','quantity':qty,'price':price,
          'priceClose':price,'pnl':pnl,'pnlNet':pnl_net,'pnlPercent':pnl_pct,'fee':fee,'tax':max(0,tax),'slippageCost':0.0,
          'grossValue':notional,'netValue':notional+cost if buy else notional-cost})
        actions[day][symbols.index(symbol)]+=qty if buy else -qty
        flows[day][symbol]+=(notional if buy else -notional)+cost
    # Same-window exact marked P&L contributions, including fees and pending shares.
    xrows=[];contributions=defaultdict(float);previous={};previous_nav=initial
    for i,snap in enumerate(snapshots):
        values={p['symbol']:p['value'] for p in snap['positions']}
        flow=flows[dates[i-1]] if i else {}
        rps=[values.get(sym,0)-previous.get(sym,0)-flow.get(sym,0) for sym in symbols]
        reward=float(nav[i]-previous_nav)
        if abs(sum(rps)-reward)>.1:raise ValueError(f'Per-stock NAV reconciliation failed on {snap["date"]}')
        for sym,pnl in zip(symbols,rps):contributions[sym]+=pnl
        xrows.append({'step':i,'date':snap['date'],'action_executed':actions[snap['date']],
          'reward':reward,'port_value':float(nav[i]),'reward_per_stock':rps,
          'constraints':{'blocked_orders':bool(snap.get('session_diagnostics',{}).get('last_step_blocked_orders',[]))}})
        previous,previous_nav=values,float(nav[i])
    returns=nav[1:]/nav[:-1]-1;mean=float(returns.mean());std=float(returns.std(ddof=1))
    downside=float(np.sqrt(np.mean(np.minimum(returns,0)**2)))
    total=float(nav[-1]/initial-1);mdd=float((1-nav/np.maximum.accumulate(nav)).max())
    cagr=float((nav[-1]/initial)**(252/len(returns))-1)
    wins=[p for p in closed if p>0];losses=[p for p in closed if p<0]
    nulls={};metrics={'totalReturn':total,'maxDrawdown':mdd,'sharpeRatio':float(source_row['by_regime']['regime.always_on']['sharpe']) if source_row else (mean/std*math.sqrt(252) if std else None),
      'sortinoRatio':mean/downside*math.sqrt(252) if downside else None,'cagr':cagr,'calmarRatio':cagr/mdd if mdd else None,
      'winRate':len(wins)/len(closed) if closed else None,'totalTrades':len(trades),'closedTrades':len(closed),'profitableTrades':len(wins),
      'profitFactor':sum(wins)/abs(sum(losses)) if losses else None,'avgWin':float(np.mean(wins)) if wins else 0.,
      'avgLoss':float(np.mean(losses)) if losses else 0.,'riskFreeRate':0.,'nullReasons':nulls}
    for k,v in metrics.items():
        if v is None:nulls[k]='No observations or zero denominator in this recorded evaluation'
    if source_row and (abs(total-source_row['by_regime']['regime.always_on']['total_return'])>1e-6 or abs(mdd+source_row['by_regime']['regime.always_on']['max_drawdown'])>1e-6):
        raise ValueError('Computed primary metrics differ from source report')
    baselines={}
    for key,source_key in [('buyHold','supplemental'),('vnindex','primary')]:
        series=recipe['baselines'][source_key]['nav']
        if len(series)!=len(dates):raise ValueError('Baseline dates do not align')
        baselines[key]=[{'date':d,'value':v} for d,v in zip(dates,series)]
    benchmark=np.asarray(recipe['baselines']['primary']['nav']);br=benchmark[1:]/benchmark[:-1]-1
    beta=float(np.cov(returns,br,ddof=1)[0,1]/np.var(br,ddof=1))
    var=max(0.,-float(np.quantile(returns,.05)));cvar=max(0.,-float(returns[returns<=np.quantile(returns,.05)].mean()))
    vol=std*math.sqrt(252);risk={'var_95':var,'expected_shortfall_95':cvar,'beta':beta}
    return {'trades': trades, 'actions': actions, 'xrows': xrows, 'contributions': contributions, 'closed': closed, 'total': total, 'mdd': mdd, 'metrics': metrics, 'baselines': baselines, 'vol': vol, 'var': var, 'cvar': cvar, 'risk': risk, 'buy_rate': buy_rate, 'sell_rate': sell_rate, 'cagr': cagr}


def export_lab(source: Path, output: Path, lab_root: Path, *, trusted_normalizer=False, replay_dir: Path | None = None):
    import numpy as np
    import pandas as pd
    source, output, lab_root = source.resolve(), output.resolve(), lab_root.resolve()
    if output.exists():
        raise ValueError('Output already exists; export to a new immutable directory')
    meta, recipe, row = [read(source/f) for f in ('metadata.json','recipe.json','source-row.json')]
    if meta['schema_version'] != 'research-model-package-v1':
        raise ValueError('Unsupported source metadata')
    for role, filename in [('model','model.zip'),('vecnorm','vecnorm.pkl')]:
        if sha256_file(source/filename) != meta['artifact_pair'][role]['sha256']:
            raise ValueError(f'Source hash mismatch: {filename}')
    raw_trace = gzip.decompress((source/'trace.json.gz').read_bytes())
    import hashlib
    if hashlib.sha256(raw_trace).hexdigest() != meta['trace']['uncompressed_sha256']:
        raise ValueError('Source trace hash mismatch')
    trace=json.loads(raw_trace)
    if trace['status'] != 'complete' or trace['errors']:
        raise ValueError('Source trace is incomplete')
    symbols, features = meta['ordered_symbols'], meta['ordered_features']
    if symbols != recipe['symbols'] or features != recipe['features']:
        raise ValueError('Source metadata and resolved recipe disagree')
    if not trusted_normalizer:
        raise ValueError('Trusted local normalizer conversion requires --trust-local-normalizer')
    import pickle
    with (source/'vecnorm.pkl').open('rb') as f:
        normalizer=pickle.load(f)
    stats=normalizer.obs_rms
    normalizer_json={'mean':stats.mean.tolist(),'var':stats.var.tolist(),'count':float(stats.count),
                     'epsilon':float(normalizer.epsilon),'clip_obs':float(normalizer.clip_obs)}
    snapshots=trace['snapshots'];dates=[s['date'] for s in snapshots]
    nav=np.asarray([s['nav'] for s in snapshots],dtype=float)
    if dates != row['nav_dates'] or not np.allclose(nav,row['nav'],rtol=0,atol=.01):
        raise ValueError('Source evaluation and trace NAV disagree')
    env=recipe['env_kwargs'];initial=float(env['initial_amount']);algo=meta['identity']['algo']
    windows=recipe['windows'];hmax=env['hmax']
    # Read only pinned historical price files; no market API or current-price fallback.
    frames=[]
    for pin in meta['price_and_data']['snapshot']['files']:
        if '/gold_eod-' not in pin['path']:
            continue
        year=int(Path(pin['path']).stem.split('-')[-1])
        if not int(dates[0][:4]) <= year <= int(dates[-1][:4]):
            continue
        path=lab_root/pin['path']
        if sha256_file(path) != pin['sha256']:
            raise ValueError(f'Source snapshot hash mismatch: {pin["path"]}')
        frame=pd.read_parquet(path);frame['date']=frame['date'].dt.strftime('%Y-%m-%d')
        frames.append(frame[frame.symbol.isin(symbols)&frame.date.isin(dates)])
    prices=pd.concat(frames).sort_values(['date','symbol'])
    ohlcv=prices[['symbol','date','open','high','low','close','volume']].to_dict('records')
    evaluated = evaluation_data(trace, recipe, source_row=row)
    trades, actions, xrows, contributions, closed, total, mdd, metrics, baselines, vol, var, cvar, risk, buy_rate, sell_rate, cagr = (evaluated[key] for key in ['trades', 'actions', 'xrows', 'contributions', 'closed', 'total', 'mdd', 'metrics', 'baselines', 'vol', 'var', 'cvar', 'risk', 'buy_rate', 'sell_rate', 'cagr'])
    config={'stocks':symbols,'algorithm':algo,'hyperparameters':recipe['hyperparams'],'envConfig':env,
      'trainingConfig':{'trainingStartDate':windows['train_start'],'trainingEndDate':windows['train_end'],
        'tradingStartDate':windows['trade_start'],'tradingEndDate':windows['trade_end'],'initialCapital':initial,
        'hmax':hmax,'h_min':env['h_min'],'totalTimesteps':recipe['timesteps'],'algorithm':algo,
        'hyperparameters':recipe['hyperparams'],'normalizeEnv':True},
      'workflow':canvas(recipe,algo),'normalization':normalizer_json|{'mean':'stored in normalizer artifact','var':'stored in normalizer artifact'},
      'dataSnapshot':meta['price_and_data']['snapshot'],'executionContract':recipe.get('session_protocol',{}),
      'evaluationRegime':'regime.always_on'}
    identity=meta['identity'];run_id=meta['model_id'].replace('attempt:','lab_')
    active=sum(any(a for a in v) for v in actions.values())/len(actions)
    magnitudes=[min(1,abs(a)/hmax) for v in actions.values() for a in v]
    conviction=float(np.mean(magnitudes));radar={'speed':active*100,'conviction':conviction*100,
      'resilience':(1-mdd)*100,'patience':(1-active)*100,'diversification':float(np.mean([s['stock_count']/len(symbols) for s in snapshots]))*100}
    test_metrics={'sharpe':metrics['sharpeRatio'],'sortino':metrics['sortinoRatio'],'calmar':metrics['calmarRatio'],
      'max_drawdown':mdd,'vol_annual':vol,'var_95':var,'cvar_95':cvar,'total_return':total,'cagr':cagr,'n_bars':len(nav)}
    scores={sym:float(value/max(sum(abs(r['reward']) for r in xrows),1)) for sym,value in contributions.items()}
    card={'run_id':run_id,'global_explanation':{'run_id':run_id,'kind':'rl','algo_or_strategy':algo.upper(),'window':'test',
      'universe':meta['basket'],'test_metrics':test_metrics,'crisis_performance':[],
      'fingerprint':{'trading_frequency':active,'conviction':conviction,'stock_scores':scores,
        'plugin_data':{'turnover_gross':sum(s['turnover_fraction'] for s in trace['steps'])}},
      'archetype':{'archetype':'Recorded portfolio policy','tagline':f'{algo.upper()} · {meta["basket"]}',
        'personality_radar':radar,'suitable_for':[],'not_suitable_for':[],'risk_tolerance_required':'research'},
      'elevator_pitch':f'{algo.upper()} · {len(symbols)} mã · {len(dates)} phiên · {len(trades)} lệnh khớp. Lợi nhuận {total*100:.2f}%, drawdown {mdd*100:.2f}%.',
      'how_it_works':f'Mô hình {algo.upper()} sử dụng {len(features)} đặc trưng, phát lệnh theo từng mã. Đồ thị lấy từ NAV, lệnh và vị thế gốc đã ghi nhận.',
      'when_it_wins':'Đóng góp lãi/lỗ từng mã được đối chiếu từ biến động giá trị vị thế, dòng tiền mua bán và chi phí thực tế.',
      'when_it_loses':f'Mức sụt giảm lớn nhất ghi nhận trong cửa sổ này là {mdd*100:.2f}%.',
      'risk_warning':'Kết quả nghiên cứu đã dùng trong tuyển chọn; chưa được chứng nhận phát hành.',
      'vn_market_fit':f'Lô {env["h_min"]} cổ phiếu; thanh toán T+{env["settlement_delay"]}; giữ đúng phí và dữ liệu giá của lần đánh giá gốc.',
      'algorithm_explanation':f'{algo.upper()}; tín hiệu thể hiện số cổ phiếu đã khớp, không phải xác suất dự đoán.',
      'train_period':windows['train_start']+' → '+windows['train_end'],'test_period':dates[0]+' → '+dates[-1],
      'timesteps':recipe['timesteps'],'seed':identity['seed']},
      'galaxy_point':{'run_id':run_id,'radar':radar,'crisis_depths':{},'algo':algo.upper(),'window':'test'},
      'visualization_spec':{'supports_local_explain':True,'supports_signal_flow':True,'supports_crisis_theater':False}}
    xmanifest={'run_id':run_id,'kind':'rl','status':'ok','config':{'run_id':run_id,'algo':algo,'universe':symbols,
      'train_start':windows['train_start'],'train_end':windows['train_end'],'test_start':dates[0],'test_end':dates[-1],
      'hmax':hmax,'initial_capital':initial,'timesteps':recipe['timesteps'],'seed':identity['seed'],
      'action_semantics':'executed_shares','reward_semantics':'marked_NAV_delta_VND'},'result':{'backtests':{'test':test_metrics}}}
    runtime_env={k:([v['uniform']]*v['n'] if isinstance(v,dict) and set(v)=={'uniform','n'} else v) for k,v in env.items()}
    training_meta={'data':{'symbols':symbols,**windows},'features':{'feature_list':features},
      'hyperparameters':{**recipe['hyperparams'],'algorithm':algo,'normalize_env':True},'env_config':runtime_env,
      'normalization':{'epsilon':normalizer_json['epsilon'],'clip_obs':normalizer_json['clip_obs']},
      'source_metadata':meta}
    terminal={k:v for k,v in snapshots[-1].items() if k in ('nav','cash_liquid','cash_in_settlement','stock_count','positions')}
    for pos in terminal['positions']:
        for k in list(pos):
            if k not in ('symbol','shares','shares_in_settlement','price','value','weight_fraction'):pos.pop(k)
    realized=sum(closed);unrealized=sum(contributions.values())-realized
    bundle={'schemaVersion':'sample-strategy-bundle/v1','provenance':{'repository':'promete-strategy-lab',
      'revision':meta['source']['capture_sha256'],'runId':run_id,'modelRef':source.name,'seed':identity['seed'],
      'trainedAt':meta['completed_at'],'evidence':'ORIGINAL'},'strategy':{'name':source.name,
      'description':f'{algo.upper()} trên rổ {meta["basket"]}, {len(features)} đặc trưng. Kết quả của đúng checkpoint seed {identity["seed"]}.',
      'config':config,'riskLevel':'HIGH' if mdd>.2 else 'MEDIUM','horizon':'POSITION','universe':meta['basket'],
      'authorLabel':'Duy · Strategy Lab','research':{'certified':False,'review':meta['review'],'metricsScope':'single checkpoint, regime.always_on',
      'sourceReport':'Wave 3 v7','sourceHashes':meta['artifact_pair']}},
      'model':{'algorithm':algo,'symbols':symbols,'features':features,'timesteps':recipe['timesteps'],'normalization':'obs_rms',
        'observationSize':env['state_space'],'actionSize':env['action_space'],'libraryVersions':recipe['runtime'],'envContract':runtime_env},
      'evaluation':{'role':'test','ratioUnit':'fraction','startDate':dates[0],'endDate':dates[-1],'initialCapital':initial,
        'transactionFee':buy_rate,'taxRate':sell_rate-buy_rate,'slippage':0.,'settlementDays':env['settlement_delay'],
        'metrics':metrics,'computedMetrics':{'volatility':vol*100},'riskProfile':risk,
        'realizedPnl':realized,'unrealizedPnl':unrealized,'dividendIncome':0.,'resultFidelity':'exact','executionTimeSec':row['seconds'],
        'nav':[{'date':d,'balance':float(v)} for d,v in zip(dates,nav)],'trades':trades,
        'actions':[{'date':d,'actions':a} for d,a in actions.items()],'terminalPositions':terminal,'baselines':baselines},'artifacts':[]}
    if replay_dir is not None:
        replay_test = json.loads(gzip.decompress((replay_dir/'test-trace.json.gz').read_bytes()))
        if (replay_test.get('status') != 'complete' or replay_test.get('errors')
                or [s['date'] for s in replay_test['snapshots']] != dates
                or not np.allclose([s['nav'] for s in replay_test['snapshots']], nav, rtol=0, atol=.01)
                or replay_test.get('trades') != trace['trades']):
            raise ValueError('Out-of-sample replay does not reproduce the original source trace')
        replay = json.loads(gzip.decompress((replay_dir/'train-trace.json.gz').read_bytes()))
        provenance = replay.get('replay_provenance', {})
        if (provenance.get('source_model_sha256') != meta['artifact_pair']['model']['sha256']
                or provenance.get('window') != 'train' or not provenance.get('oos_verified_against_original')
                or replay.get('status') != 'complete' or replay.get('errors')):
            raise ValueError('In-sample replay must be complete and verified against the original checkpoint')
        primary, supplemental = read(replay_dir/'train-baselines.json')
        replay_recipe = recipe | {'baselines': {'primary': {'nav': primary}, 'supplemental': {'nav': supplemental}}}
        data = evaluation_data(replay, replay_recipe)
        first, last = replay['snapshots'][0], replay['snapshots'][-1]
        if first['date'] < windows['train_start'] or last['date'] > windows['train_end']:
            raise ValueError('In-sample replay exceeds the recorded training window')
        train_realized = sum(data['closed'])
        bundle['inSample'] = {
            'role':'train','ratioUnit':'fraction','startDate':first['date'],'endDate':last['date'],
            'initialCapital':initial,'transactionFee':buy_rate,'taxRate':sell_rate-buy_rate,
            'slippage':0.,'settlementDays':env['settlement_delay'],'metrics':data['metrics'],
            'realizedPnl':train_realized,'unrealizedPnl':sum(data['contributions'].values())-train_realized,
            'dividendIncome':0.,'resultFidelity':'exact',
            'nav':[{'date':s['date'],'balance':s['nav']} for s in replay['snapshots']],
            'trades':data['trades'],'actions':[{'date':d,'actions':a} for d,a in data['actions'].items()],
            'terminalPositions':{k:last[k] for k in ('nav','cash_liquid','cash_in_settlement','stock_count','positions')},
            'baselines':data['baselines'],
        }
        bundle['strategy']['research']['inSampleReplay'] = provenance
    output.mkdir(parents=True)
    files={'normalizer.json':('normalizer',normalizer_json),'training_metadata.json':('training_metadata',training_meta),
      'investor_card.json':('xai_card',card),'MANIFEST.json':('xai_manifest',xmanifest),'ohlcv.json':('ohlcv',ohlcv),
      'source-evidence.json':('research',{'metadata':meta,'recipe':recipe,'performance':read(source/'performance.json')})}
    for filename,(_,data) in files.items():write(output/filename,data)
    shutil.copyfile(source/'model.zip',output/'model.zip')
    (output/'trace_test.jsonl').write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in xrows))
    roles={'model.zip':'model','trace_test.jsonl':'xai_trace',**{k:v[0] for k,v in files.items()}}
    for i,(filename,role) in enumerate(roles.items()):
        p=output/filename;bundle['artifacts'].append({'id':f'artifact-{i}','role':role,'path':filename,'size':p.stat().st_size,'sha256':sha256_file(p)})
    validated=Bundle.model_validate(bundle)
    (output/'manifest.json').write_text(validated.model_dump_json())
    from .contract import load_bundle
    load_bundle(output/'manifest.json')
    return {'path':str(output),'modelRef':source.name,'navRows':len(nav),'trades':len(trades),'symbols':len(symbols),'totalReturn':total}
