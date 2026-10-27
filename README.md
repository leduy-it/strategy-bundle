# Promete Strategy Bundle

Python package và CLI để kiểm tra, upload và import một model đã train thành
chiến lược mẫu ProfinAI. Python >= 3.11. Không cần cài PyTorch để dùng CLI.

## Cài từ Git

Repo mã nguồn là public; cài thẳng bằng Git, không cần tài khoản GitHub:

```bash
pipx install 'git+https://github.com/leduy-it/strategy-bundle.git@v0.2.1'
strategy-bundle --version
strategy-bundle --help
```

Thay `@v0.2.1` bằng `@main` để cài bản mới nhất sau khi thay đổi ở nhánh main
được merge. Dùng tag hoặc commit cố định để tái lập môi trường. Nếu không dùng
`pipx`, tạo virtualenv rồi chạy `python -m pip install
"git+https://github.com/leduy-it/strategy-bundle.git@v0.2.1"`.

Repo chứa các bundle chiến lược có quyền truy cập riêng và có thể yêu cầu Git
LFS; cài CLI public không tự cấp quyền tải bundle. API đích vẫn yêu cầu JWT của
tài khoản có vai trò phù hợp.

Để cài từ source checkout:

```bash
git clone https://github.com/leduy-it/strategy-bundle.git
cd strategy-bundle
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

## Lấy chiến lược và import

Các bundle chiến lược nằm trực tiếp trong repo dữ liệu, không nằm trong Package
Registry. Nếu repo dùng Git LFS, phải tải file thật trước khi verify.

```bash
git clone git@git.promete.ai:duyle.promete/promete-sample-strategies.git
cd promete-sample-strategies
git lfs pull
strategy-bundle inspect ./bundles/strategy-lab-v6/lowbeta-stationary-ppo-s3
strategy-bundle verify ./bundles/strategy-lab-v6/lowbeta-stationary-ppo-s3

# Đăng nhập platform bằng tài khoản ADMIN/SUPER_ADMIN của môi trường đích.
# Mở DevTools → Network, chọn một request API thành công của platform,
# rồi copy giá trị Request Headers → Authorization (bỏ tiền tố "Bearer ").
mkdir -p ~/.config/strategy-bundle
chmod 700 ~/.config/strategy-bundle
umask 077
read -rsp 'Keycloak access token: ' strategy_bundle_token; printf '\n'
printf '%s' "$strategy_bundle_token" > ~/.config/strategy-bundle/admin.jwt
unset strategy_bundle_token
chmod 600 ~/.config/strategy-bundle/admin.jwt

strategy-bundle import ./bundles/strategy-lab-v6/lowbeta-stationary-ppo-s3 --api https://app.profinai.vn \
  --token-file ~/.config/strategy-bundle/admin.jwt --validate-only
strategy-bundle commit <import-id> --api https://app.profinai.vn \
  --token-file ~/.config/strategy-bundle/admin.jwt
strategy-bundle status <import-id> --api https://app.profinai.vn \
  --token-file ~/.config/strategy-bundle/admin.jwt
```

Token là access token Keycloak có hạn sử dụng; khi hết hạn, đăng nhập lại và thay
token trong file. Token chỉ xác thực với API, không cấp quyền clone repo bundle.
Quyền GitLab và quyền ADMIN/SUPER_ADMIN trên platform là hai quyền riêng. Không
đưa token vào lệnh, shell history, Git hoặc ticket/chat.

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

`model.zip` trong bundle chỉ giữ policy: exporter bỏ optimizer và trạng thái huấn
luyện (`_last_obs`, `ep_info_buffer`, `replay_buffer_class`, `train_freq`…) vì server
từ chối chúng, và ghi danh sách đã bỏ vào `strategy.research.modelArchive`. Weight
policy giữ nguyên; `verify` báo lỗi nếu bundle cũ còn các phần đó (cần export lại).
Bundle export bằng bản trước 0.2.1 không import được.

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

## Báo cáo từ skill hiện có (offline)

Package phân phối nguyên bản skill `strategy-sample-report` của
`promete-strategy-lab`, bao gồm renderer, references, examples, logo, font Lexend
và license, dữ liệu giải thích feature; kèm skill evidence-policy được tham chiếu.
`report skill` xuất cùng một `SKILL.md` cho **Codex, Claude Code và OpenCode**.
Hãy chỉ định rõ agent đọc file được xuất; không cần SDK riêng của ba harness.
Provenance và hash từng file nằm trong `manifest.json` của skill. Skill nguồn là
WIP chưa được Git theo dõi tại snapshot; revision checkout không thay thế hash.

```bash
strategy-bundle report skill ./report-skill
# Yêu cầu Codex / Claude Code / OpenCode đọc:
# ./report-skill/strategy-sample-report/SKILL.md và references của nó.
# Agent dùng nguồn đã kiểm để soạn report.json; không suy ra metric còn thiếu.

strategy-bundle report prepare ./authored-report --output ./prepared
strategy-bundle report validate ./prepared/report.json

# Chỉ máy render cần extra Python và system packages:
python -m pip install '.[report]'
# Ubuntu/Debian: apt-get install libreoffice-writer poppler-utils fontconfig
strategy-bundle report render ./prepared/report.json --output ./rendered
strategy-bundle report pack ./prepared ./rendered --output ./report-packet
strategy-bundle report check ./report-packet --expected-subject ./canonical-subject.json
```

`prepare` nhận file spec hoặc thư mục có `report.json`, sao chép assets và
`facts.json`/`source-manifest.json` nếu được cung cấp, trả **draft**. Nó không tự
viết báo cáo, gọi LLM hoặc chạy train. Muốn pack phải có facts và manifest nguồn
đúng danh tính model/evaluation. `render` dùng đúng renderer gốc và tạo receipt
khóa hash inputs, skill, PDF/DOCX. Sửa nội dung/facts/nguồn phải render lại.
Mỗi output phải là đường dẫn mới; không ghi đè kết quả hay sửa nguồn.

Để tái dựng spec nghiên cứu cũ có CSV nằm ngoài thư mục report, truyền rõ
`--source-root /path/to/trusted-research-root` cho `prepare`. Chỉ đường tương đối
còn nằm trong root này được chấp nhận, mọi asset sẽ được copy/hash và đổi thành
đường dẫn nội bộ. Path tuyệt đối, symlink và path thoát root đều bị từ chối.
Không truyền `/` làm trusted root. Hướng dẫn đầy đủ, source manifest, định nghĩa
packet và exit codes nằm trong `report-skill/PORTABLE.md` sau khi export.

Python dùng cùng giao diện, không cần CLI hay harness runtime:

```python
from promete_strategy_bundle.reports import (
    export_report_skill, prepare_report, validate_report, render_report,
    pack_report, validate_import_report, ReportError,
)
# Các hàm nhận pathlib.Path; prepare có source_root= tùy chọn.
# validate_import_report(packet, expected_subject=canonical_subject)
```

`validate` kiểm cấu trúc, đường dẫn/file và lint nguyên bản; kiểm glyph cần
fonttools, trạng thái này được trả trong JSON. `check` bắt buộc PDF/DOCX, facts,
content, source manifest và render receipt có hash khớp. `importReady` chỉ xác nhận
packet đủ điều kiện kiểm tra integrity offline, không xác nhận số liệu/lời văn,
chứng nhận chiến lược hay quyền publish. Phải soát từng trang PDF và đối chiếu
nguồn theo skill. Backend còn phải bind subject với model/backtest canonical,
kiểm ACL và thực hiện review. Receipt dùng hash, không phải chữ ký tin cậy.

Renderer có quy trình cố định nhưng toolchain và timestamp của DOCX/PDF có thể
làm hash output khác nhau giữa hai lần dựng. Font có thể được renderer cài vào
`~/.local/share/fonts/promete-lexend`. Không có lời hứa PDF tái lập từng byte.

### Ranh giới tích hợp và prerequisite

Nhánh này xuất phát từ public `origin/main` `cb972035` (v0.1.0). Tag đã phát hành
v0.2.1 (`836a16a`) đi trước main bốn commit. Candidate đã merge tag này trong
nhánh cô lập để giữ chức năng export/replay đã phát hành; lịch sử public main và
checkout chính không bị sửa. Phiên bản base v0.2.1 chưa phải bản release report mới.

`report` là bộ lệnh local. `strategy-bundle import` v1 vẫn là **legacy model-only**:
`COMPLETED` của lệnh đó không có nghĩa report đã được attach hay toàn bộ quy trình
model + report hoàn tất. Luồng mới yêu cầu tạo/kiểm report sau train và trước import,
rồi attach/readback theo contract backend được thống nhất. Package này chưa triển
khai API attach/generate, orchestration `import --with-reports`, server hay tab UI;
cài Python package không tự triển khai các thành phần ấy.
