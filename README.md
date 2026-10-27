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
CLI không deserialize pickle hay chạy code trong bundle.

Đổi vị trí repo không thay identity; thay nội dung model/config/evidence tạo
identity mới. Giữ cùng `artifact.id` khi di chuyển đường dẫn.

## Phát triển

```bash
python -m pip install -e '.[test]'
python -m pytest
python -m build
```

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
v0.2.1 (`836a16a`) đi trước main bốn commit. **Cần tích hợp prerequisite đó trước
khi phát hành** để giữ các chức năng export/replay mới; thay đổi report này không
merge/cherry-pick tag hoặc sửa logic model/export sẵn có. Phiên bản package hiện
vẫn là phiên bản base, chưa phải bản release mới.

`report` là bộ lệnh local. `strategy-bundle import` v1 vẫn là **legacy model-only**:
`COMPLETED` của lệnh đó không có nghĩa report đã được attach hay toàn bộ quy trình
model + report hoàn tất. Luồng mới yêu cầu tạo/kiểm report sau train và trước import,
rồi attach/readback theo contract backend được thống nhất. Package này chưa triển
khai API attach/generate, orchestration `import --with-reports`, server hay tab UI;
cài Python package không tự triển khai các thành phần ấy.
