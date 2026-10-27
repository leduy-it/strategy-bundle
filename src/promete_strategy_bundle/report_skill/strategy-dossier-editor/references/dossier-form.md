# Form hồ sơ và hợp đồng bàn giao

Form là dàn ý nghiên cứu, không phải khuôn lặp lại cùng một câu cho mọi chiến lược. Có thể đổi tiêu đề và thứ tự phần giữa để làm rõ đặc trưng riêng; giữ đầy đủ bằng chứng bên dưới.

Với lô hiện tại, ưu tiên khoảng 300–450 từ văn xuôi mỗi hồ sơ, cộng bảng cần thiết; không kéo dài để đủ số từ. Sáu hồ sơ lịch sử chỉ dùng số liệu thực có trong bản trích/cohort; các trường Wave 3 không có không phải điều kiện chặn. Nhóm những mã chưa có bằng chứng riêng, vẫn liệt kê đầy đủ roster và đào sâu mã removal được nêu.

## 1. Nhận định mở đầu

Tên dễ đọc + thuật toán, rổ, bộ đầu vào, seed. Một đến hai đoạn trả lời: điều gì đáng nghiên cứu nhất ở kết quả này; vì sao vẫn chỉ là ứng viên. Nêu điểm riêng, không mở cả ba hồ sơ bằng “Chiến lược này sử dụng…”. Tóm lược kỳ kiểm thử, lợi suất sau phí, drawdown và benchmark bằng bảng nhỏ.

## 2. Vì sao chọn rổ này?

Trả lời cơ sở chọn rổ ban đầu bằng quy tắc có nguồn: phạm vi cổ phiếu, bộ lọc, kỳ dữ liệu và thời điểm lựa chọn. Tên rổ hoặc danh sách thành viên chưa đủ giải thích vì sao rổ được chọn. Nếu thiếu quy tắc, nói thẳng phần nào chưa tìm thấy. Tách việc cổ phiếu được vào rổ với việc model quyết định mua/bán. Chỉ nêu đầu vào và cách phân bổ cần thiết để hiểu kết quả; giữ hyperparameter và chi tiết kỹ thuật ở phần nguồn.

## 3. Lợi nhuận hình thành ra sao

Đặt lợi suất cạnh mức giảm sâu, đường đi theo tháng/kỳ có nguồn, hai baseline và độ tập trung. Lựa chọn vài bằng chứng mạnh để nối thành lập luận. Phân biệt điều quan sát được với giả thuyết: “P&L tập trung vào các giao dịch ở…; cần kiểm lại khi bỏ mã…” có giá trị hơn gán nguyên nhân “model hiểu chu kỳ doanh nghiệp”.

## 4. Vai trò từng cổ phiếu

Có bảng đủ toàn bộ ordered_roster, kể cả không giao dịch. Với Wave 3, các cột tối thiểu: ticker; số lần mua/bán; lãi/lỗ ròng; trọng số tối đa; trọng số cuối kỳ; vai trò/rủi ro bằng một câu cụ thể. Dùng giá trị chưa có như “chưa lưu”, không thay bằng 0.

Nếu nguồn lịch sử chỉ có roster và removal, không bịa mua/bán, P&L hay trọng số từng mã: trình bày nhóm roster chưa có chi tiết, rồi phân tích riêng từng mã removal với kết quả được lưu.

Khi có dữ liệu từng mã, phần diễn giải phải bao phủ từng mã bằng đoạn ngắn hoặc câu bảng có nội dung phân tích, không chỉ chép số. Những mã dẫn lãi, gây lỗ hoặc có vị thế tập trung cần đoạn sâu hơn: khi nào tham gia, nắm giữ bao lâu, thoát chưa, lãi đã/chưa thực hiện, điều đó thay đổi cách đọc kết quả thế nào. Nhóm mã tác động nhỏ có thể viết liền mạch, nhưng phải gọi rõ từng ticker và chứng cứ riêng. Không biến mọi mã thành một luận điểm đầu tư doanh nghiệp thiếu nguồn.

## 5. Sức bền kết quả và điều kiện đi tiếp

Tách kết quả attempt hiện tại với cấu hình qua các seed/kỳ. Bảng gate nêu phạm vi, trạng thái, số đo/ngưỡng có nguồn và ý nghĩa. Kết luận nghiên cứu phải trả lời ưu tiên thử gì tiếp, bằng chứng nào làm thay đổi đánh giá; không gọi chứng nhận khi native gate chưa đạt, STAR chưa chạy hoặc dữ liệu điều chỉnh/PIT còn thiếu.

## 6. Dấu vết bằng chứng

Liên kết nguồn tại đoạn/bảng quan trọng, có thể dùng `<details>` cho danh tính, nguồn và giới hạn chung. Mọi đường dẫn trong HTML phải tính từ vị trí báo cáo đích cuối cùng, không từ thư mục draft. Trong review.json dùng đường dẫn tính từ repo để dễ kiểm tra.

## Đầu ra bắt buộc

`docs/strategy-editorial/150926-v2/<slug>/dossier.html`: một `<section id="<slug>-dossier">` gốc; HTML fragment không `<html>`, `<head>`, script hay CSS toàn cục. ID con dùng tiền tố slug. Dùng HTML ngữ nghĩa và class của báo cáo nếu đã biết. Bản này được ghép trực tiếp sau phản biện.

`review.json`: JSON thuần, theo cấu trúc sau (giá trị minh họa phải được thay bằng dữ liệu thật):

```json
{
  "schema_version": "strategy-editorial-review.v1",
  "model_slug": "lowbeta-default-crossq-s3",
  "identity": {"model_id": "from metadata", "attempt_id": "from source", "basket": "LOWBETA20", "algo": "crossq", "features": "DEFAULT_11", "seed": 3},
  "sources": [{"path": "repo-relative path", "sha256": "computed SHA-256"}],
  "claims": [{"id": "return", "text": "claim as written", "kind": "observed", "evidence": [{"path": "repo-relative path", "pointer": "/return_fraction"}]}],
  "roster_coverage": {"expected": [], "covered": []},
  "gates": {"basic_passed": 6, "certified": false, "ready_for_live_use": false, "evidence": []},
  "review_round": 0,
  "publication_status": "draft",
  "unresolved_items": [],
  "insights": []
}
```

Với hồ sơ lịch sử, `identity` dùng strategy ID, tên, thuật toán và cửa sổ thực có; bỏ trường Wave 3 không áp dụng. `gates` ghi G0–G3 theo nguồn, tối thiểu `g2`/`g3` và bằng chứng, không mang `basic_passed: 6` từ ví dụ sang. Ví dụ JSON trên là Wave 3, không phải số mặc định cho mọi hồ sơ.

`claims.kind`: `observed`, `derived` hoặc `hypothesis`. Với derived, ghi công thức/mẫu số trong `derivation`; với hypothesis, ghi cách kiểm tra trong `validation_needed`. Mục unresolved phải chứa `id`, `severity`, `location`, `issue`, `evidence_needed`, `status`. Không tự nhận đã được phản biện; chỉ biên tập viên đổi publication_status sau review. `dossier.md` là tùy chọn để dễ sửa lời.
