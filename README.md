# Promete Strategy Bundle

Python package và CLI để kiểm tra, upload và import một model đã train thành
chiến lược mẫu ProfinAI. Python >= 3.11. Không cần cài PyTorch để dùng CLI.

## Cài từ Git

```bash
git clone https://github.com/leduy-it/strategy-bundle.git
cd strategy-bundle
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
strategy-bundle --version
strategy-bundle --help
```

Hoặc `pipx install git+https://github.com/leduy-it/strategy-bundle.git@v0.1.0`. Dùng tag/commit cố định
để tái lập môi trường. Repo private yêu cầu quyền clone; quyền clone code không
đồng nghĩa quyền import vào hệ thống.

## Lấy chiến lược và import

Các bundle chiến lược nằm trực tiếp trong repo dữ liệu, không nằm trong Package
Registry. Nếu repo dùng Git LFS, phải tải file thật trước khi verify.

```bash
git clone git@git.promete.ai:duyle.promete/promete-sample-strategies.git
cd promete-sample-strategies
git lfs pull
strategy-bundle inspect ./bundles/<strategy>
strategy-bundle verify ./bundles/<strategy>

# Lấy access token qua đăng nhập tài khoản ADMIN/SUPER_ADMIN của môi trường đích.
# Dán token bằng read -s để không ghi token vào shell history.
read -rs STRATEGY_BUNDLE_TOKEN
export STRATEGY_BUNDLE_TOKEN
strategy-bundle import ./bundles/<strategy> --api https://app.profinai.vn --validate-only
strategy-bundle commit <import-id> --api https://app.profinai.vn
strategy-bundle status <import-id> --api https://app.profinai.vn
unset STRATEGY_BUNDLE_TOKEN
```

Bỏ `--validate-only` để upload → validate → commit trong một lệnh. Import lại
cùng nội dung trả cùng ID, không tạo mẫu trùng. Khi kết nối bị ngắt, chạy lại
lệnh import hoặc kiểm tra `status` trước. `cancel` chỉ hủy import chưa hoàn tất.

API phải được triển khai ở môi trường đích. Lệnh trên không tự triển khai server
và không bỏ qua xác thực. Kết quả `COMPLETED` tạo mẫu **ẩn**, không tự công khai,
bật giao dịch hoặc chứng nhận chiến lược đạt các gate nghiên cứu.

## Chuẩn bundle

Một thư mục có `manifest.json` và các file tương đối được liệt kê trong manifest.
`strategy-bundle schema > schema.json` xuất JSON Schema chính xác của phiên bản
đang cài. `inspect` chỉ đọc metadata; `verify` đọc toàn bộ file, kiểm SHA-256,
kích thước, đường dẫn, dữ liệu đánh giá và hợp đồng feature/symbol.

Các nhóm bắt buộc: provenance repo/revision/run/modelRef/seed/thời điểm train;
cấu hình đã resolve; symbols/features có thứ tự; runtime và normalization;
NAV, giao dịch, action vectors, phí/thuế, benchmark và vị thế cuối kỳ; weight,
training metadata, XAI card/trace/manifest và OHLCV snapshot. Tỷ lệ dùng fraction
(0.10 = 10%). Metric thiếu dùng null kèm lý do, không điền số 0 giả.

Normalizer v1 nhận JSON `obs_rms` với `mean`, `var`, `count`; server tạo companion
`vecnorm_obs_rms.pkl` từ số đã kiểm tra. Không nhận pickle normalizer từ client. Binary model chỉ đến từ nguồn admin tin cậy.
Các lệnh inspect/verify/import không deserialize pickle hay chạy code trong bundle.

Đổi vị trí repo không thay identity; thay nội dung model/config/evidence tạo
identity mới. Giữ cùng `artifact.id` khi di chuyển đường dẫn.

## Phát triển

```bash
python -m pip install -e '.[test]'
python -m pytest
python -m build
```

## Export checkpoint từ Strategy Lab (0.2.0)

`export-lab` dùng đúng `research-model-package-v1`, kiểm hash weight/normalizer,
đối chiếu NAV với trace gốc, lấy giá từ snapshot đã ghim và dựng workflow canvas
từ cấu hình đã resolve. Không lấy số trung bình nhiều seed để gán cho một model.
`evaluation.metrics.totalTrades` đếm execution; `closedTrades` là mẫu số của win
rate và số giao dịch đóng được hiển thị như training. Hai số được giữ riêng.

```bash
python -m pip install '.[export]'
strategy-bundle replay-lab /path/to/model-package \
  --lab-root /path/to/promete-strategy-lab \
  --backend-root /path/to/promete_fintech_backend \
  --output /path/to/new-replay --trust-local-model
strategy-bundle export-lab /path/to/model-package \
  --lab-root /path/to/promete-strategy-lab \
  --replay-dir /path/to/new-replay \
  --output /path/to/new-bundle --trust-local-normalizer
strategy-bundle verify /path/to/new-bundle
```

Replay dùng checkpoint và thống kê normalization cố định. NAV và toàn bộ lệnh
ngoài kỳ phải khớp lần chạy gốc trước khi tính kết quả trong kỳ. Không train lại.
Cần checkout lab/backend và snapshot dữ liệu gốc tương ứng; dùng môi trường
Python/runtime ghi trong model package. Kết quả trong kỳ được ghi riêng ở
`inSample`, không sao chép kết quả ngoài kỳ.

Hai cờ `--trust-local-*` chỉ dùng với nguồn local đã được tin cậy: model loader
và pickle có thể chạy mã. Các lệnh `inspect`, `verify`, `import` không thực thi
model/pickle. Server nhận normalizer JSON và kiểm hợp đồng XAI bằng chính DTO
của các terminal; chỉ số rủi ro được tính bằng cùng hàm của training.

Exporter này dành cho nguồn Strategy Lab. Weight Huy phải lấy theo đúng
strategy/version/seed và các artifact references trong `result.json` hoặc
`registry.sqlite3`; HTML hay receipt trên Git không thay thế binary model.
