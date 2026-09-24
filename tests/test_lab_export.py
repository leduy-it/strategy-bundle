import copy
import pytest
from promete_strategy_bundle.lab_export import evaluation_data, canvas


def source():
    recipe = {'symbols':['AAA'], 'features':['momentum'], 'timesteps':300000, 'hyperparams':{'learning_rate':.0001},
        'windows':{'train_start':'2024-01-01','train_end':'2024-12-31','trade_start':'2025-01-01','trade_end':'2025-01-03'},
        'env_kwargs':{'initial_amount':1000.,'hmax':100,'buy_cost_pct':{'uniform':.01,'n':1},'sell_cost_pct':{'uniform':.02,'n':1}},
        'baselines':{'primary':{'nav':[1000,1010,1030]},'supplemental':{'nav':[1000,1015,1020]}}}
    trace = {'snapshots':[
        {'date':'2025-01-01','nav':1000.,'positions':[]},
        {'date':'2025-01-02','nav':1009.,'positions':[{'symbol':'AAA','value':110.}]},
        {'date':'2025-01-03','nav':1006.8,'positions':[]}],
        'trades':[
            {'symbol':'AAA','execution_date':'2025-01-01','shares':10,'price':10.,'fee_amount_from_config':1.,'side':'buy'},
            {'symbol':'AAA','execution_date':'2025-01-02','shares':10,'price':11.,'fee_amount_from_config':2.2,'side':'sell'}]}
    return trace, recipe


def test_fills_closed_trades_and_pnl_are_distinct_and_reconcile():
    trace, recipe = source()
    result = evaluation_data(trace, recipe)
    assert result['metrics']['totalTrades'] == 2
    assert result['metrics']['closedTrades'] == 1
    assert result['metrics']['winRate'] == 1
    assert result['closed'] == pytest.approx([6.8])
    assert sum(result['contributions'].values()) == pytest.approx(6.8)
    assert [r['reward'] for r in result['xrows']] == pytest.approx([0,9,-2.2])
    assert result['actions']['2025-01-01'] == [10]
    assert result['actions']['2025-01-02'] == [-10]
    assert result['trades'][1]['tax'] == pytest.approx(1.1)
    assert result['trades'][1]['pnlNet'] == pytest.approx(6.8)


def test_inconsistent_trace_cannot_be_presented_as_exact():
    trace, recipe = source()
    trace['snapshots'][1]['nav'] += 100
    with pytest.raises(ValueError, match='NAV reconciliation'):
        evaluation_data(trace, recipe)


def test_canvas_preserves_resolved_parameters_without_mutating_source():
    _, recipe = source(); original = copy.deepcopy(recipe)
    workflow = canvas(recipe, 'ppo')
    assert workflow['nodes'][0]['data']['executionParameters']['buy_cost_pct'] == .01
    assert workflow['nodes'][2]['data']['hyperparameters']['learning_rate'] == .0001
    assert workflow['provenance'] == 'DERIVED_FROM_RESOLVED_CONFIG'
    assert recipe == original
