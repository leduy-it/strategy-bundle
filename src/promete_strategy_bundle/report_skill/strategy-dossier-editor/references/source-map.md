# Bản đồ nguồn

Các đường dẫn dưới đây tính từ gốc repo. Đây là bản đồ cho lô hiện tại; lần cập nhật sau phải đọc lại `docs/LATEST-REPORT.md` và xác định catalog được người dùng chọn.

## Cohort và nguồn lịch sử

Đọc `docs/strategy-editorial/150926-v2/cohort.json` và `feedback.md` trước khi giao việc. Cohort có 9 mục; sáu mục `strategy-<id>` lấy từ HTML lịch sử, ba mục còn lại lấy từ PACKAGE bên dưới.

Với sáu hồ sơ lịch sử, dùng `extracted_html` đã giải nén từ `#strategy-detail-archive` của bản 140926 và `catalog_fields` trong cohort; kiểm hash bản trích và source HTML. Giữ ID, thuật toán, cửa sổ Validation, roster, kết quả từng seed, mã bị removal và kết quả G3. Có thể dùng selector HTML hoặc tên bảng/hàng trong evidence thay JSON pointer. G2 pass / G3 fail là ngữ nghĩa riêng, không đổi thành sáu basic checks của Wave 3. Removal lịch sử đã chạy không phải STAR chưa chạy. Khi không có P&L/trọng số/lệnh từng mã, ghi thiếu dữ liệu và phân tích ở mức bằng chứng sẵn có, không tạo bảng số giả hoặc buộc có metrics như Wave 3.

## Nguồn Wave 3 hiện tại

- Báo cáo chính: `docs/LATEST-REPORT.md`, Wave 3 v7, 432 training attempts. Thư mục `v6` giữ thiết kế/lượt chạy gốc.
- Gói nghiên cứu: `weights/releases/wave_3/v6/20260909T160929Z/v2/` (gọi là `PACKAGE` bên dưới). Đọc `README.vi.md`, `catalog.json`, `manifest.json`.
- Ba thư mục trong `PACKAGE/models/`: `lowbeta-default-crossq-s3`, `lowbeta-stationary-ppo-s3`, `top40-default-crossq-s7`.
- Đích biên tập được yêu cầu: `sample_strategy/17-tong-hop-cap-nhat-260911/REPORT_strategy_lab_merge_duy_huy_updated_150926_v2.html`. Đây là bản tổng hợp dẫn xuất, không thay thế báo cáo chính Wave 3 v7.
- Draft hiện tại: `docs/strategy-editorial/150926-v2/<slug>/`.

## File và mục đích

| File trong thư mục model | Dùng cho |
|---|---|
| `metadata.json` | attempt/model ID, basket, ordered_symbols, ordered_features, windows, scan_started_at, hash cặp artifact, review |
| `recipe.json` | rổ được chọn thế nào, đầu vào, thuật toán/reward, phí, lô, T+2, giới hạn phân bổ |
| `model-card.vi.md`, `investment-thesis.vi.md` | lời giải thích đã có; đối chiếu số liệu với JSON trước khi dùng lại |
| `stocks.json` | LOWBETA: `stocks` là object theo ticker, `ordered_roster`, `max_weight_fraction`. TOP40: `stocks` là list, mỗi phần tử có `symbol`, `action_index_zero_based`, `peak_weight_fraction`; lấy rổ chuẩn từ metadata `ordered_symbols`. Kiểm thứ tự và schema thực đọc trước khi so số liệu |
| `performance.json` | benchmarks, comparison, benchmark_assumptions, convergence, periods, portfolio_pnl, fills, holdings |
| `gates.json` | model_review, configuration_gate, configuration_stability, native_family_gate, star, certified |
| `configuration-all-seeds-folds.json` | độ ổn định trong cấu hình; không trộn với riêng seed đang viết |
| `report/`, `source-row.json` | CSV/dossier và dòng kết quả gốc để kiểm chứng chi tiết khi cần |

Gắn claim với đường dẫn tương đối + JSON pointer hoặc dòng/khóa CSV. Hash nguồn hiện tại bằng SHA-256; không chép hash cũ rồi ghi là đã kiểm lại. Giữ cả timestamp scan, kỳ train/test, snapshot và ngày biên tập; chúng không thay thế nhau.

## Các nhầm lẫn cần chặn ở lô này

`catalog.json` hiện có 3 ứng viên, `certified_count=0`, `ready_for_live_use=false`. Sáu kiểm tra cơ bản và bộ lọc đóng góp lãi dưới 50% là screening; bộ lọc thêm sau quan sát không biến thành gate native đã đăng ký. DSR native loại ứng viên và STAR chưa chạy. Đọc lại `gates.json` để nêu chính xác từng trạng thái, không suy rộng từ catalog.

Baseline cùng rổ là chia đều lúc đầu, không phí/lô/tái cân bằng; VNINDEX là chỉ số giá. `net_pnl_vnd` có thể gồm lãi đã và chưa thực hiện. “Không còn vị thế cuối kỳ” không có nghĩa chưa từng giao dịch; “không giao dịch” không giải thích tại sao policy tránh mã. LOWBETA20 là tên rổ, không chứng minh beta từng mã hoặc rủi ro thấp của danh mục tập trung.

## Lưu ý đã kiểm trên sáu bản trích lịch sử

- Bảng catalog có thể tổng hợp các cột từ những seed khác nhau. Ví dụ `strategy-993869802f1a23c5`: return 38,75% thuộc seed 3 nhưng drawdown −10,39% thuộc seed 7. A2C `strategy-a4959ef87cc205b1`: return 35,91% thuộc seed 5, Sharpe 2,429 thuộc seed 3. Không mô tả một hàng catalog như hành trình của một model. Ưu tiên bảng từng seed; nếu dùng tóm tắt, ghi rõ từng đại lượng lấy từ đâu. Không tự đặt tên “trung vị” cho công thức chưa xác minh từ nguồn tạo catalog.
- Bảng lịch sử đo Validation 29/08/2025–05/03/2026. Config có thêm cửa sổ Test 06/03/2026–14/08/2026 nhưng không có nghĩa số liệu đang hiển thị là kết quả Test hoặc đã đo Test thành công.
- G1 nguồn ghi cả “at least 3 seeds” và “60% of cohort”. Không rút gọn thành “chỉ cần 2/3”. Các rổ removal IDC/TNG lưu 2/3 seed đạt G1 nhưng vẫn `REMOVAL_PERFORMANCE_FAIL`; giữ nguyên trạng thái và nêu thiếu chi tiết tiêu chí khi không có hồ sơ rổ con.
- G2 là kết luận cấp cấu hình về bằng chứng PSR trong cohort qua G1. Không gọi mọi seed đều đạt một ngưỡng PSR, không tự điền ngưỡng chưa có. PSR ghi 1,000 là số đã làm tròn; không diễn giải thành chắc chắn thắng tương lai. Không chuyển MinTRL thành ngày lịch nếu nguồn chưa xác nhận đơn vị/quy ước.
- G0 là upstream audit PASS do caller cung cấp theo bản trích, không phải kiểm chứng độc lập mới do người biên tập thực hiện.
- `removal_sources` rỗng nghĩa không có hồ sơ chi tiết các child ID trong kho trích hiện tại. Chỉ nêu ticker removal, child ID, trạng thái và số seed đã lưu. Không suy ra lợi suất rổ con, mức mất lãi, tỷ trọng hay P&L trực tiếp của ticker; removal làm thay đổi bài toán policy, không phải phép trừ P&L cổ phiếu khỏi danh mục.
- Recipe lịch sử chỉ có một phần hyperparameter và features kỹ thuật. Không tự bổ sung phí/T+2/reward/trần vị thế hoặc cơ chế chọn rổ từ tên `quality`, `liquidity`, `calm`, `turbulent`; ghi giới hạn nguồn nếu không tìm được nguồn tương ứng.

## Nguồn gốc rổ lịch sử đã khôi phục

Đọc `docs/strategy-editorial/150926-v2/inputs/basket-origin/provenance.json`, `campaign-manifest.json` và `build_baskets_campaign.py`. Sáu roster đã đối chiếu khớp chính xác. Manifest `ro` chứa basket_id/layer/seed hoặc tier; mã tạo rổ xác nhận lọc độ phủ theo ngưỡng 70%, đủ giá/chỉ báo/adv20 dương, xếp theo độ phủ và sinh cụm T rời nhau hoặc phân hoạch P với seed cố định. Dùng nguồn này trả lời vì sao rổ được chọn; không giữ kết luận “chưa có nguồn gốc rổ” khi đã đọc thấy bằng chứng.

Kỳ sàng lọc rổ 05/09/2022–16/08/2025 khác kỳ fit 03/01/2023–28/08/2025 trong kết quả đánh giá. Nhóm được lọc qua `group-review.json` có ý kiến LLM, không phải chứng cứ thẩm định độc lập doanh nghiệp. Chưa kiểm toán tính đúng thời điểm của phân nhóm hoặc xác nhận mọi yêu cầu xử lý ngoại lệ đã thực hiện. Quy tắc P/T giải thích cách tạo biến thể nghiên cứu, không chứng minh đây là các cổ phiếu tốt nhất hay danh sách nên mua.
