#!/usr/bin/env python3
"""Gom lý do thiết kế của bộ feature một chiến lược theo nhóm, để viết mục "Tín hiệu đầu vào".

    python feature_digest.py --features rsi,momentum_composite,...   # hoặc
    python feature_digest.py --config-json path/to/config.json        # đọc khóa "features"/"ordered_features"

In ra, cho từng nhóm: tên cột, "thông tin đưa cho mô hình", "kỳ vọng hưởng lợi"
và lưu ý triển khai, lấy từ data/feature-rationale.json. Người viết nén mỗi nhóm
thành một hàng bảng; đây là giả thuyết thiết kế, không phải đóng góp đã đo.
Cột nào không có trong catalog sẽ bị báo thiếu (không tự bịa lý do).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "feature-rationale.json"


def load_features(a) -> list[str]:
    if a.features:
        return [f.strip() for f in a.features.split(",") if f.strip()]
    cfg = json.loads(Path(a.config_json).read_text(encoding="utf-8"))
    for key in ("features", "ordered_features"):
        if key in cfg:
            return list(cfg[key])
        for v in cfg.values():
            if isinstance(v, dict) and key in v:
                return list(v[key])
    sys.exit("không tìm thấy khóa features/ordered_features")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--features")
    g.add_argument("--config-json")
    ap.add_argument("--json", action="store_true", help="in JSON thay vì markdown")
    a = ap.parse_args()

    cat = json.loads(DATA.read_text(encoding="utf-8"))
    by_name = {f["name"]: f for f in cat["features"]}
    wanted = load_features(a)
    missing = [f for f in wanted if f not in by_name]
    groups: dict[str, list[dict]] = {}
    for i, name in enumerate(wanted, 1):
        if name in by_name:
            groups.setdefault(by_name[name]["group"], []).append({"order": i, **by_name[name]})

    if a.json:
        print(json.dumps({"missing": missing, "groups": groups}, ensure_ascii=False, indent=1))
        return 1 if missing else 0

    print(f"# {len(wanted)} feature, {len(groups)} nhóm — nguồn {cat['source']['file']}")
    print(f"> {cat['status']}\n")
    for gk, feats in groups.items():
        gi = cat["groups"].get(gk, {})
        print(f"## {gi.get('name', gk)} ({len(feats)})")
        if gi.get("intro"):
            print(f"_{gi['intro']}_\n")
        for f in feats:
            print(f"- [{f['order']:02d}] `{f['name']}` — {f['full_name']}")
            print(f"  - Thông tin: {f['information']}")
            print(f"  - Kỳ vọng: {f['expected_benefit']}")
            if f.get("caveat"):
                print(f"  - Lưu ý: {f['caveat']}")
        print()
    if missing:
        print("THIẾU trong catalog (không viết lý do cho các cột này khi chưa có nguồn): " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
