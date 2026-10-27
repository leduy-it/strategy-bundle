#!/usr/bin/env python3
"""Trích số liệu cho báo cáo chiến lược mẫu từ một thư mục model Wave 3.

    python wave3_facts.py weights/releases/wave_3/v6/<scan>/v2/models/<slug> [--out facts.json]

Mọi con số in ra đều đọc từ file trong gói (performance.json, stocks.json,
gates.json, configuration-all-seeds-folds.json, recipe.json, report/*.csv), đã
định dạng kiểu Việt (dấu phẩy thập phân, dấu − ). Người viết chép số từ đây,
không gõ lại từ trí nhớ. Khóa `source` ghi file + trường cho từng nhóm số.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path


def pct(x: float | None, digits: int = 2, sign: bool = True) -> str:
    if x is None:
        return "chưa lưu"
    s = f"{x * 100:+.{digits}f}%" if sign else f"{x * 100:.{digits}f}%"
    return s.replace(".", ",").replace("-", "−")


def pp(x: float, digits: int = 2) -> str:
    return (f"{x * 100:+.{digits}f} đpt").replace(".", ",").replace("-", "−")


def num(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}".replace(".", ",").replace("-", "−")


def vnd_m(x: float) -> str:
    """Triệu đồng, dấu chấm nghìn."""
    v = x / 1e6
    s = f"{v:+,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s.replace("-", "−") + " tr"


def dmy(d: str | None) -> str:
    return "" if not d else f"{d[8:10]}/{d[5:7]}/{d[:4]}"


def rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model_dir", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    M = a.model_dir
    meta = json.loads((M / "metadata.json").read_text())
    perf = json.loads((M / "performance.json").read_text())
    gates = json.loads((M / "gates.json").read_text())
    stocks = json.loads((M / "stocks.json").read_text())
    recipe = json.loads((M / "recipe.json").read_text())
    conf = json.loads((M / "configuration-all-seeds-folds.json").read_text())
    ident = meta["identity"]
    w = meta["windows"]
    b = perf["benchmarks"]
    c = perf["comparison"]

    facts: dict = {"identity": {
        "slug": M.name, "model_id": meta["model_id"], "algo": ident["algo"], "seed": ident["seed"],
        "fold": ident["fold"], "feature_set": ident["feature_set_id"], "basket": meta["basket"],
        "roster": meta["ordered_symbols"], "features": meta["ordered_features"],
        "train": f"{dmy(w['train_start'])} - {dmy(w['train_end'])}",
        "trade": f"{dmy(w['trade_start'])} - {dmy(w['trade_end'])}",
        "status": meta.get("status"), "ready_for_live_use": meta.get("ready_for_live_use"),
        "scan_started_at": meta.get("scan_started_at"),
        "source": "metadata.json"}}

    facts["headline"] = {
        "strategy_return": pct(b["strategy"]["return_fraction"]), "vnindex_return": pct(b["vnindex"]["return_fraction"]),
        "hold_return": pct(b["hold"]["return_fraction"]), "sharpe": num(b["strategy"]["sharpe"]),
        "vnindex_sharpe": num(b["vnindex"]["sharpe"]), "hold_sharpe": num(b["hold"]["sharpe"]),
        "max_drawdown": pct(b["strategy"]["max_drawdown_fraction"]),
        "vnindex_max_drawdown": pct(b["vnindex"]["max_drawdown_fraction"]),
        "hold_max_drawdown": pct(b["hold"]["max_drawdown_fraction"]),
        "excess_vs_vnindex": pp(c["excess_vs_vnindex_fraction"]), "excess_vs_hold": pp(c["excess_vs_hold_fraction"]),
        "pnl": vnd_m(b["strategy"]["pnl_vnd"]),
        "chart_values": [round(b[k]["return_fraction"] * 100, 2) for k in ("strategy", "vnindex", "hold")],
        "assumptions": {k: v.get("assumptions_as_recorded") or v.get("cost_semantics")
                        for k, v in perf["benchmark_assumptions"].items()},
        "source": "performance.json /benchmarks /comparison /benchmark_assumptions"}

    seeds = []
    for r in conf["recent"]["seed_rows"]:
        bb = r["benchmarks"]
        seeds.append({"seed": r["seed"], "return": pct(bb["strategy"]["return_fraction"]),
                      "sharpe": num(bb["strategy"]["sharpe"]), "max_dd": pct(bb["strategy"]["max_drawdown_fraction"]),
                      "excess_vs_vnindex": pp(r["comparison"]["excess_vs_vnindex_fraction"]),
                      "excess_vs_hold": pp(r["comparison"]["excess_vs_hold_fraction"]),
                      "dominant_symbol": r.get("dominant_symbol"),
                      "dominant_share_of_net_profit": pct(r.get("net_profit_share"), sign=False),
                      "_ret": bb["strategy"]["return_fraction"]})
    rets = [s["_ret"] for s in seeds]
    worst = min(seeds, key=lambda s: s["_ret"])
    rec = conf["recent"]
    facts["seeds"] = {"rows": [{k: v for k, v in s.items() if not k.startswith("_")} for s in seeds],
                      "median_return": pct(st.median(rets)), "worst_seed": worst["seed"],
                      "median_excess_vs_vnindex": pp(rec["median_excess_fraction"]),
                      "worst_drawdown": pct(rec["worst_drawdown_fraction"]),
                      "above_vnindex": f"{rec['above_vnindex_count']}/{rec['rows']}",
                      "note": "Số seed đang viết lấy từ performance.json; hàng các seed khác từ configuration-all-seeds-folds.json",
                      "source": "configuration-all-seeds-folds.json /recent"}

    folds = []
    for f in conf["coverage"]["folds"]:
        sr = f["seed_rows"]
        vni = sr[0]["benchmarks"]["vnindex"]["return_fraction"]
        hold = sr[0]["benchmarks"]["hold"]["return_fraction"]
        folds.append({"fold": f["fold"], "window": f"{dmy(f['dates'][0])} - {dmy(f['dates'][1])}",
                      "median_return": pct(f["median_return_fraction"]), "vnindex": pct(vni), "hold": pct(hold),
                      "median_excess_vs_vnindex": pp(f["median_excess_fraction"]),
                      "seeds_above_vnindex": f"{f['above_vnindex_rows']}/{len(sr)}",
                      "worst_seed_drawdown": pct(min(s["benchmarks"]["strategy"]["max_drawdown_fraction"] for s in sr)),
                      "_chart": (round(f["median_return_fraction"] * 100, 1), round(vni * 100, 1))})
    facts["folds"] = {"rows": [{k: v for k, v in x.items() if not k.startswith("_")} for x in folds],
                      "median_beats_vnindex": f"{sum(x['_chart'][0] > x['_chart'][1] for x in folds)}/{len(folds)}",
                      "chart": {"labels": [x["window"][6:10] + "–" + x["window"][-2:] for x in folds],
                                "median_config": [x["_chart"][0] for x in folds],
                                "vnindex": [x["_chart"][1] for x in folds]},
                      "reason_vi": conf.get("reason_vi"),
                      "source": "configuration-all-seeds-folds.json /coverage/folds"}

    # hành vi: từng mã
    st_rows, never = [], []
    items = stocks["stocks"].items() if isinstance(stocks["stocks"], dict) else \
        [(x["symbol"], x) for x in stocks["stocks"]]
    for t, v in items:
        if not v.get("buy_fills"):
            never.append(t)
            continue
        st_rows.append({"symbol": t, "buys": v.get("buy_fills"), "sells": v.get("sell_fills"),
                        "net_pnl": vnd_m(v.get("net_pnl_vnd") or 0),
                        # LOWBETA và TOP40 dùng hai schema khác tên trường
                        "max_weight": pct(v.get("max_weight_fraction", v.get("peak_weight_fraction")), 1, False),
                        "terminal_weight": pct(v.get("terminal_weight_fraction"), 1, False),
                        "held_sessions": v.get("held_sessions", v.get("held_valuation_snapshots")),
                        "first_buy": dmy(v.get("first_buy_date") or v.get("first_execution_date")),
                        "unrealized": vnd_m(v.get("unrealized_pnl_vnd") or 0),
                        "_pnl": v.get("net_pnl_vnd") or 0})
    st_rows.sort(key=lambda r: -r["_pnl"])
    total = sum(r["_pnl"] for r in st_rows)
    for r in st_rows:
        r["share_of_net_pnl"] = pct(r["_pnl"] / total, 1, False) if total else "—"
    facts["stocks"] = {"traded": [{k: v for k, v in r.items() if not k.startswith("_")} for r in st_rows],
                       "never_bought": never, "traded_count": f"{len(st_rows)}/{len(st_rows) + len(never)}",
                       "sum_net_pnl": vnd_m(total),
                       "source": "stocks.json /stocks (net_pnl gồm lãi đã và chưa thực hiện, sau phí phân bổ)"}

    hold = rows(M / "report/holdings.csv")
    cash = [float(x["cash_weight_fraction"]) for x in hold]
    nstock = [int(x["stock_count"]) for x in hold]
    top_w, top_s = defaultdict(float), {}
    for p in rows(M / "report/positions.csv"):
        wf = float(p["weight_fraction"])
        if wf > top_w[p["date"]]:
            top_w[p["date"]], top_s[p["date"]] = wf, p["symbol"]
    tw = list(top_w.values())
    steps = rows(M / "report/steps.csv")
    fees = sum(float(s["fee_amount"] or 0) for s in steps)
    turnover = sum(float(s["turnover_fraction"] or 0) for s in steps)
    trades = len(rows(M / "report/trades.csv"))
    dd = rows(M / "report/drawdowns.csv")
    deepest = min(dd, key=lambda r: float(r["depth_fraction"])) if dd else None
    facts["behavior"] = {
        "sessions": len(hold), "median_cash_weight": pct(st.median(cash), 1, False),
        "sessions_cash_ge_50pct": sum(x >= 0.5 for x in cash), "terminal_cash_weight": pct(cash[-1], 1, False),
        "median_positions": st.median(nstock), "max_positions": max(nstock),
        "median_top_weight": pct(st.median(tw), 1, False),
        "sessions_top_gt_50pct": f"{sum(x > 0.5 for x in tw)}/{len(tw)}",
        "top_gt_50pct_by_symbol": dict(Counter(top_s[d] for d in top_w if top_w[d] > 0.5).most_common()),
        "trades": trades, "fees": vnd_m(fees).lstrip("+"), "turnover_x_nav": num(turnover, 1),
        "deepest_drawdown": None if not deepest else {
            "depth": pct(float(deepest["depth_fraction"])), "peak": dmy(deepest["peak_date"]),
            "trough": dmy(deepest["trough_date"]), "recovery": dmy(deepest["recovery_date"]) or "chưa hồi phục"},
        "source": "report/holdings.csv, positions.csv, steps.csv, trades.csv, drawdowns.csv"}

    mr = gates["model_review"]
    conc = mr.get("concentration_review", {}).get("checks", [{}])[0]
    facts["gates"] = {
        "basic_checks": [{"id": x["id"], "label": x.get("label_vi") or x.get("label"), "state": x["state"],
                          "value": x.get("display_value"), "threshold": x.get("display_threshold")}
                         for x in mr["checks"]],
        "concentration": {"state": conc.get("state"), "detail": conc.get("detail_vi"),
                          "scope": mr.get("concentration_review", {}).get("scope")},
        "configuration_checks": [{"id": x["id"], "state": x["state"], "value": x.get("value"),
                                  "threshold": x.get("threshold")}
                                 for x in gates["configuration_stability"]["configuration_checks"]],
        "blockers": gates["configuration_stability"].get("blockers"),
        "native_rungs": [{"key": r["key"], "state": r["state_as_recorded"], "entered": r["entered"],
                          "survived": r["survived"], "label": r.get("label_as_recorded")}
                         for r in gates["native_family_gate"]["rungs"]],
        "star": gates.get("star"), "certified": gates.get("certified"),
        "source": "gates.json"}

    ek = recipe["env_kwargs"]
    ek_fee = lambda k: ek[k]["uniform"] if isinstance(ek[k], dict) else ek[k]  # noqa: E731
    facts["execution"] = {
        "initial_capital": vnd_m(ek["initial_amount"]).replace("+", ""),
        "buy_fee": pct(ek_fee("buy_cost_pct"), 2, False), "sell_fee": pct(ek_fee("sell_cost_pct"), 2, False),
        "lot": ek.get("h_min"), "max_shares_per_order": ek.get("hmax"), "settlement_delay": ek.get("settlement_delay"),
        "max_position_weight": recipe.get("tuning", {}).get("max_position_weight"),
        "timesteps": recipe.get("timesteps"), "state_space": ek.get("state_space"),
        "reward_mode": recipe.get("tuning", {}).get("reward_mode"),
        "point_in_time_verified": recipe.get("session_protocol", {}).get("point_in_time_snapshot_verified"),
        "source": "recipe.json /env_kwargs /tuning /session_protocol"}
    facts["basket_rule_vi"] = stocks.get("roster_rule_vi") or "chưa lưu trong stocks.json; đọc configs/wave_3/v6/baskets.yml"

    out = json.dumps(facts, ensure_ascii=False, indent=1)
    if a.out:
        a.out.write_text(out, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
