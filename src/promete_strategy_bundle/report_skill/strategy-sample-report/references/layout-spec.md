# Layout và định dạng JSON đầu vào

Bộ dựng `scripts/build_report.py` tái tạo layout "Báo cáo chiến lược mẫu số 1":
A4, lề trái/phải 1,5 cm, logo PROMETE góc phải trên mọi trang, font Lexend Light
10 pt (đậm dùng Lexend Bold), căn đều hai bên, cam `#E69138`, kem `#FFFBEC`, xám
cột đầu `#F2F3F5`, kẻ `#CCCCCC`. Font và logo nằm trong `assets/` và được cài vào
`~/.local/share/fonts/promete-lexend` khi chưa có.

Trang 1 bìa (dòng nhỏ xám, "Chiến lược mẫu số N" đậm đen, tên chiến lược cam 26 pt,
bảng thông tin nhãn nền kem). Trang 2 mục lục có dấu chấm dẫn và số trang thật,
bấm được trong PDF, là trường TOC trong DOCX. Từ trang 3 là nội dung: tiêu đề mục
cam đậm có gạch chân cam, tiểu mục đen đậm, tự đánh số `1.`, `5.1.`.

```bash
PY=/home/duyle/miniconda3/envs/duylv/bin/python
$PY .agents/skills/strategy-sample-report/scripts/build_report.py report.json --out-dir OUT [--strict] [--no-pdf]
```

In ra JSON: đường dẫn DOCX/PDF, `lint` (cảnh báo trình bày), `toc_pages`,
`non_lexend_fonts` (phải rỗng). `--strict` trả mã 2 nếu còn cảnh báo lint.
Cần `soffice`, `pdftotext`, `pdfinfo`, `pdffonts`.

## Cấu trúc JSON

```json
{
  "output_name": "chien-luoc-mau-so-2",
  "meta": {"title": "…", "source": "đường dẫn nguồn chính"},
  "options": {"page_numbers": false, "logo_width_cm": 3.1, "cover_top_pt": 70},
  "cover": {
    "kicker": "Báo cáo chiến lược mẫu",
    "number_line": "Chiến lược mẫu số 2",
    "title": "Tên dễ hiểu của chiến lược",
    "facts": [["Mã định danh", "ID · ALGO\nVersion …"], ["Danh mục đầu tư", "…"],
              ["Giai đoạn huấn luyện", "dd/mm/yyyy - dd/mm/yyyy"], ["Giai đoạn kiểm định", "…"]]
  },
  "toc": {"title": "Mục lục"},
  "sections": [
    {"title": "Tóm tắt điều hành", "numbered": false, "blocks": []},
    {"title": "Điểm khác biệt …", "new_page": true, "blocks": []}
  ]
}
```

`numbered` mặc định true; `new_page` đưa mục sang trang mới (mẫu: mục 1, 4, 5).
`toc.enabled: false` bỏ trang mục lục.

## Block

| type | Trường | Ghi chú |
|---|---|---|
| `p` | `text`, `after?`, `keep_next?` | `**đậm**`, `*nghiêng*`, `\n` xuống dòng |
| `h2` | `text` | tiểu mục, tự đánh số theo mục cha, vào mục lục |
| `bullets` | `items` | gạch đầu dòng "-" như mẫu |
| `numbered` | `items` | 1. 2. 3.; mở bằng `**Nhãn:**` |
| `table` | `columns`, `rows`, `widths?`, `align?`, `rules?`, `first_col_shade?`, `note?`, `font_pt?` | header nền kem chữ cam, kẻ cam trên/dưới header, cột đầu nền xám, `rules: "dotted"` cho bảng nhiều dòng |
| `chart` bar | `labels`, `values`, `highlight`, `ylabel`, `caption`, `value_format?` | cột cam = chiến lược, xám = đối chứng; nhãn số kiểu Việt |
| `chart` bar nhóm | `labels`, `series: [{name, values, color}]` | vd. trung vị cấu hình vs VN-Index theo năm; `color`: orange, grey, dark, light |
| `chart` line | `series: [{name, csv, x, y, rebase?, scale?, color, width?}]`, `month_step?` | đọc thẳng CSV nguồn (đường dẫn tương đối với file JSON); `rebase` biến chuỗi equity thành lợi suất lũy kế |
| `image` | `path` (tương đối với file JSON), `width_cm?`, `caption?` | biểu đồ khác dựng bằng matplotlib rồi chèn |
| `note` | `text` | nghiêng, căn phải (vd. "đpt: điểm phần trăm") |
| `page_break` | | |

Hình tự đánh số "Hình N." theo thứ tự. Mọi hàng bảng phải đủ số ô; ô trống bị
lint cảnh báo, cũng như ký tự Lexend không có (vd. "→"). Bảng ≤ 14 hàng được giữ
trọn một trang (`keep_together` để ghi đè).

## Kiểm tra sau khi dựng

1. `lint` rỗng, `non_lexend_fonts` rỗng.
2. `pdftoppm -r 80 -png OUT/x.pdf OUT/pg` rồi xem từng trang: không trang chỉ có
   một đoạn lẻ, tiêu đề không nằm cuối trang, bảng không vỡ hàng, mục lục khớp.
   Nếu có trang lẻ, rút gọn lời hoặc bỏ `new_page`, không thu nhỏ font.
3. Đối chiếu lại mọi số trong PDF với nguồn (pdftotext rồi grep từng số).
