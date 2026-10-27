# Lấy số liệu từ đâu

Hai kho nguồn. Luôn ghi rõ nguồn và phiên bản phễu cho mỗi con số; khi hai nguồn
lệch nhau, nêu cả hai, không chọn bản đẹp hơn.

## A. Strategy lab: gói Wave 3 (đủ dữ liệu hành vi nhất)

`PKG = weights/releases/wave_3/v6/<scan>/v2/models/<slug>/`. Chạy trước:

```bash
$PY .agents/skills/strategy-sample-report/scripts/wave3_facts.py $PKG --out facts.json
```

Script in ra toàn bộ số đã định dạng kiểu Việt. Chép số từ đây, không gõ lại.

| Mục báo cáo | File / trường |
|---|---|
| Kết quả chính và đối chứng | `performance.json /benchmarks /comparison`; giả định benchmark: `/benchmark_assumptions` (mua & giữ chia đều, không phí; VN-Index là chỉ số giá) |
| Biểu đồ lũy kế | `report/equity.csv`, `baseline-primary.csv` (VN-Index), `baseline-supplemental.csv` (mua & giữ); dùng block `chart` `kind: line` với `csv`, `y: equity`, `rebase: true` |
| Bảng seed | `configuration-all-seeds-folds.json /recent/seed_rows` |
| Độ bền qua năm | `configuration-all-seeds-folds.json /coverage/folds` (6 năm × 3 seed); biểu đồ cột nhóm |
| Rổ và lý do chọn | `stocks.json /roster_rule_vi`; luật: `configs/wave_3/v6/baskets.yml` (`rationale`, `ranking`, `as_of`) |
| Hành vi từng mã | `stocks.json /stocks` (lệnh, lãi/lỗ đã/chưa thực hiện, tỷ trọng tối đa/cuối kỳ, số phiên giữ); TOP40 dùng schema list khác: kiểm `net_profit_contribution_fraction`, `peak_weight_fraction` |
| Tiền mặt, tập trung, phí | `report/holdings.csv` (cash_weight_fraction), `positions.csv`, `steps.csv`, `trades.csv`, `drawdowns.csv` |
| Chỉ báo đầu vào | `metadata.json /ordered_features`; định nghĩa `configs/wave_3/v6/features.yml`; lý do: `data/feature-rationale.json` qua `scripts/feature_digest.py` |
| Thực thi | `recipe.json /env_kwargs` (phí, lô `h_min`, `hmax`, T+2, vốn), `/tuning/max_position_weight`, `/session_protocol/point_in_time_snapshot_verified` |
| Cổng | `gates.json /model_review/checks` (6 kiểm tra cơ bản), `/concentration_review` (bộ lọc 50%, thêm sau khi xem kết quả), `/configuration_stability`, `/native_family_gate/rungs` (phễu gốc, cấp cả đợt, không gắn riêng model), `/star`, `/certified` |

Không có trong gói: phân ngành/sàn, beta từng mã, lý do từng lệnh, quy công
theo chỉ báo, hiệu suất trong mẫu huấn luyện, mô phỏng sức chứa vốn. Ghi "chưa
lưu", không ước lượng.

## B. Training kit của Huy: `promete_fintech_backend`, nhánh `research-rl`

Đọc bằng `git show origin/research-rl:<path>`, không checkout. Gốc:
`research/rl/strategy-selection-study/`.

| Mục | Đường dẫn |
|---|---|
| Hồ sơ từng chiến lược lịch sử | `sample_strategy/17-tong-hop-cap-nhat-260911/strategy-data/strategy-<id>.js` (bảng seed Validation, gate, config: symbols, features, windows) |
| Phễu và nhãn mô tả | `sample_strategy/17-…/canonical-funnel-results.json`: `funnel_config.id`, `results[].funnel.gates` (bằng chứng G1–G3, PSR, rổ con), `results[].classification.labels` (drawdown, sharpe, seed_dispersion, profit_concentration; cash/turnover/sector thường UNMEASURED) |
| Danh mục chiến lược | `sample_strategy/17-…/strategy-catalog.json` |
| Cấu hình phễu | `training-kit/configs/evaluation/funnel.*.json`, `docs/psr-g2-release-threshold.md` |
| Trạng thái lượt chạy | `training-kit/docs/activation-status.md` (lượt `breadth-all96` chỉ 512 bước/job, là bằng chứng vận hành, không dùng để xếp hạng) |
| Pipeline | `training-kit/README.md`, `UNIFIED-KIT.md`; `1-data-prep/build_baskets.py`, `build_feature_panels.py`; `5-evaluate/*` |
| Lý do chọn 31/46 feature | `data/feature-rationale.json` của skill (trích từ catalog 46 feature, hợp nhất nhánh Huy 31 + nhánh Duy 23) |

Bẫy đã gặp:
- Cùng một chiến lược có kết quả cổng khác nhau theo phiên bản phễu. Mẫu số 1:
  bản import 14/09 ghi G3 FAIL, `catalog-funnel-psr90-vnindex-g1-v3` ghi G3 PASS.
  Luôn ghi `funnel_config.id`.
- Kiểm số bước huấn luyện (`recipe.timesteps` hoặc manifest lượt chạy) trước khi
  trình bày kết quả; lượt kỹ thuật ngắn không phải bằng chứng hiệu quả.
- Ngưỡng 50% lãi ròng có hai nghĩa khác nhau, đừng lẫn:
  - Kit Huy, G3 `profit_concentration` (`gates/concentration.py`): không loại thẳng.
    Mã > 50% ở seed được khóa (Sharpe trung vị trong nhóm qua PSR) → huấn luyện lại
    rổ bỏ mã đó một seed; PASS nếu rổ con vượt B&H và momentum
    (`require_child_concentration_clear: false`, rổ con vẫn có thể tập trung).
  - Wave 3 strategy lab: bộ lọc rà soát thêm sau khi xem kết quả, loại thẳng chiến lược có một mã
    ≥ 50% (`gates.json /model_review/concentration_review`), không phải gate native.
  - Nhãn `classification.labels.profit_concentration` (P-1..P-3) chỉ mô tả, không
    quyết định PASS/FAIL. Mức tập trung vẫn phải nêu trong báo cáo.
- Hồ sơ lịch sử có cửa sổ Test sau Validation. Chỉ báo cáo số Test khi đọc được
  giá trị thật; danh sách trường trong `derived_metrics` không phải số.
