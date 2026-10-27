---
name: strategy-sample-report
description: Soạn "Báo cáo chiến lược mẫu" tiếng Việt cho từng chiến lược của Promete strategy-lab và xuất DOCX → PDF đúng layout mẫu số 1 (bìa, mục lục, tóm tắt điều hành, biểu đồ, bảng cam–kem, logo PROMETE), giọng chuyên gia, số liệu kiểm từ nguồn. Dùng khi cần báo cáo PDF/DOCX gửi nhà đầu tư, đối tác hay nội bộ cho một chiến lược; hồ sơ nghiên cứu HTML dùng strategy-dossier-editor.
---

# Báo cáo chiến lược mẫu (DOCX → PDF)

Mẫu tham chiếu: "Báo cáo chiến lược mẫu số 1 — Linh hoạt Tấn công - Phòng thủ"
(`strategy-993869802f1a23c5`). Bản tái tạo đã sửa lỗi nằm ở
[examples/chien-luoc-mau-so-1.json](examples/chien-luoc-mau-so-1.json); dùng nó
làm khuôn cho cả layout lẫn lời văn.

Giữ layout và giọng văn của mẫu, nhưng kỷ luật bằng chứng của
[strategy-dossier-editor](../strategy-dossier-editor/SKILL.md) vẫn áp dụng đầy đủ:
phân biệt screening với chứng nhận, không trộn số giữa các seed, không bịa lý do
mua/bán, không gọi Validation là Test.

Người đọc mặc định là **nhà đầu tư**: không dùng từ vựng nội bộ (seed, gate,
phễu, chứng nhận, ứng viên, attempt ID, NAV); số xấu vẫn nêu đủ bằng ngôn ngữ đầu
tư. Bảng đổi từ ở [references/voice.md](references/voice.md#người-đọc-là-nhà-đầu-tư).
Lời văn khoa học nhưng giọng người: "chúng tôi", kể theo lý do, câu dài ngắn xen
nhau, ít dấu hai chấm và in đậm; xem mục "Giọng người viết" trong voice.md.

## Đọc trước

1. [references/source-map.md](references/source-map.md): lấy số từ gói Wave 3 của
   strategy lab (`scripts/wave3_facts.py`) và từ training kit của Huy (nhánh
   `research-rl` của `promete_fintech_backend`), cùng các bẫy phiên bản phễu.
2. [references/voice.md](references/voice.md): nhịp từng mục, chuẩn câu chữ và số,
   nguyên tắc "gọn nhưng giá trị hơn", lỗi của mẫu gốc không được lặp lại.
3. [references/layout-spec.md](references/layout-spec.md): JSON đầu vào, các block, lệnh dựng.

Ví dụ: [mẫu số 1](examples/chien-luoc-mau-so-1.json) (hồ sơ lịch sử, ít dữ liệu
hành vi) và [mẫu số 2](examples/chien-luoc-mau-so-2.json) (Wave 3, đủ dữ liệu:
lãi từng mã, tiền mặt, độ bền 6 năm, lý do chọn chỉ báo).

## Quy trình

1. **Khóa số liệu.** Wave 3: chạy `scripts/wave3_facts.py`. Hồ sơ lịch sử: đọc
   `strategy-data/strategy-<id>.js` và `canonical-funnel-results.json` trên nhánh
   `research-rl`, ghi `funnel_config.id`. Số của cả ba lần huấn luyện (seed); VN-Index và mua & giữ cùng kỳ; gate, removal, nhãn tập trung lãi.
   Chạy `scripts/feature_digest.py --features …` để lấy lý do thiết kế của bộ chỉ báo.
2. **Viết JSON nội dung** theo dàn: Tóm tắt điều hành (kết quả, chiến lược là gì,
   biểu đồ lũy kế, bảng ba lần huấn luyện, phù hợp với ai, rủi ro lớn nhất);
   1. Điểm khác biệt (ngắn); 2. Mô tả danh mục; 3. Tín hiệu đầu vào (bảng nhóm ×
   "thông tin cung cấp cho mô hình" × "vai trò kỳ vọng"); 4. Hiệu quả thực tế (lợi nhuận
   đến từ đâu theo từng mã; độ bền qua các năm); 5. Rủi ro và vận hành (tập trung,
   thanh khoản và chi phí, sự cố mã, kết quả kiểm định + miễn trừ). Bỏ tiểu mục nào nguồn
   không có dữ liệu thay vì viết chung chung. Tên chiến lược đặt theo hành vi quan
   sát được, không hứa hẹn.
3. **Dựng**: `$PY scripts/build_report.py report.json --out-dir OUT --strict`
   (`PY=/home/duyle/miniconda3/envs/duylv/bin/python`). Sửa mọi cảnh báo lint.
4. **Soát bản PDF**: xem ảnh từng trang (pdftoppm), kiểm mục lục, trang lẻ, bảng
   vỡ; `pdftotext` rồi đối chiếu từng con số với bảng ở bước 1. Đọc lại theo câu
   hỏi cuối trong voice.md.
5. **Bàn giao** theo bộ: `docs/strategy-reports/<đợt>/0N-<slug>/` chứa `report.json`,
   `facts.json`, `build.json`, DOCX, PDF; ở gốc bộ có `README.md` (bảng so sánh),
   `manifest.json` (chỉ số, SHA-256) và `build.sh` dựng lại toàn bộ. Mẫu hoàn chỉnh:
   [docs/strategy-reports/wave3-v7/](../../../docs/strategy-reports/wave3-v7/README.md).
   Nguồn, trạng thái gate nội bộ và phần chưa kiểm ghi ở README của bộ (nội bộ),
   không ở PDF.

## Không làm

- Không bỏ mục kết quả kiểm định hay đổi "Chưa đạt" thành "Đạt" để báo cáo "đẹp" hơn.
- Không ngụ ý chứng nhận, giao dịch thật hay lợi nhuận bảo đảm.
- Không để placeholder, ô trống, số kiểu `38.75%` lọt vào PDF.
- Không chỉnh font nhỏ lại để nhét vừa trang; rút gọn lời.
- Không sửa nguồn, gate hay chạy lại huấn luyện để hoàn thiện báo cáo.
