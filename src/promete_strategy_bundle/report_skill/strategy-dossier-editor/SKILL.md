---
name: strategy-dossier-editor
description: Viết và biên tập hồ sơ nghiên cứu chiến lược bằng tiếng Việt cho Promete strategy-lab từ kết quả thực nghiệm, với phân tích từng mã, nguồn kiểm chứng và vòng phản biện có giới hạn. Dùng khi soạn hoặc cập nhật báo cáo chiến lược; không dùng để chứng nhận hay triển khai model.
---

# Strategy dossier editor

Tạo báo cáo mà người đọc hiểu chiến lược đã làm gì, kết quả đến từ đâu, và bằng chứng nào còn thiếu để đi tiếp. Viết như chuyên gia nghiên cứu trao đổi với đồng nghiệp: có luận điểm, có đối chiếu, câu chữ tự nhiên và kết luận vừa sức dữ liệu.

## Điểm vào

Đọc `docs/LATEST-REPORT.md` trước. Sau đó đọc [bản đồ nguồn](references/source-map.md) và [form hồ sơ](references/dossier-form.md). Khi phản biện hoặc cập nhật, dùng [rubric và vòng phản hồi](references/review-loop.md).

Đọc cohort và phản hồi hiện tại để xác định số hồ sơ, nguồn và thứ tự. Lô 150926-v2 có chín hồ sơ: sáu ứng viên lịch sử qua G2 nhưng trượt G3 và ba ứng viên Wave 3. Người dùng yêu cầu một lượt Terra riêng cho từng chiến lược, chạy tuần tự đủ chín lượt, không chạy đồng thời các lượt viết. Astra xây form, phản biện và thống nhất biên tập; công việc Astra không thay thế lượt viết Terra. Lần gọi khác tuân theo phạm vi và cách điều phối được người dùng cho phép. Mỗi người viết một thư mục draft riêng; biên tập viên là người duy nhất ghép báo cáo chung. Không chia báo cáo thành phần “tác giả A/B”, “Duy/Huy” hay “Astra/Terra”; dấu vết người viết thuộc hồ sơ kiểm chứng.

## Ràng buộc biên tập

- Giữ nguyên nguồn, model, manifest và HTML lịch sử. Tạo bản dẫn xuất mới tại đích được yêu cầu; không đổi tên provenance cho giống số phiên bản báo cáo.
- Phân biệt model/attempt, cấu hình qua seed/kỳ, gate native và chứng nhận. Có file trong `weights/releases/` không đồng nghĩa được phép dùng thật.
- Phân biệt tỷ trọng vốn, tỷ trọng cuối kỳ và đóng góp lợi nhuận; ghi rõ mẫu số, kỳ đo, phí và giả định benchmark khi cần.
- Phân tích hành vi quan sát được theo từng mã. Không suy ra động cơ mua/bán từ tên feature, gán tính chất doanh nghiệp cho policy hoặc bịa beta/feature importance. Diễn giải mới phải nêu cơ sở và phần cần kiểm chứng.
- Trình bày giới hạn chung một lần ở nơi người đọc cần; dành câu chữ từng mã cho chi tiết thực sự khác nhau. Mã không giao dịch vẫn cần hiện diện, nhưng không cần lặp lại cả đoạn miễn trừ.
- Rút gọn lời diễn giải, không rút gọn bằng chứng: giữ bảng gate, ngưỡng, số đo, trạng thái và dẫn nguồn dễ thấy trong hồ sơ. Chỉ thu gọn bảng từng mã và thông tin bổ sung; không giấu cổng kiểm định chung trong mục “Xem thêm”.
- Không chạy huấn luyện, thay gate, tải dữ liệu mới hoặc thực thi pickle chỉ để hoàn thiện văn bản. Nếu đề xuất nghiên cứu ngoài bộ nguồn, tách nó thành công việc tiếp theo.

## Thực hiện

1. Khóa danh tính và nguồn theo catalog/metadata; ghi hash file thực đọc vào `review.json`.
2. Viết gọn, tự nhiên; thường 300–450 từ văn xuôi cộng bảng cần thiết, có thể ngắn hơn nếu ít bằng chứng. Mở bằng điểm đáng chú ý rồi trả lời “Vì sao chọn rổ này?”. Tách cơ sở chọn rổ ban đầu với quyết định mua/bán của model. Bao phủ toàn bộ rổ trong bảng và phân tích đủ từng mã, ưu tiên độ sâu cho nguồn lãi, nguồn lỗ và vị thế tập trung.
3. Nộp `dossier.html` và `review.json` vào thư mục riêng. HTML là fragment có một phần tử gốc, ID có tiền tố slug, không script hoặc CSS toàn cục.
4. Phản biện dữ liệu, lập luận, văn phong và khả năng ghép. Sửa tối đa hai vòng trong mỗi lần gọi skill; giữ lại vấn đề chưa giải quyết và insight cần kiểm tra.
5. Chỉ ghép fragment không còn lỗi chặn xuất bản. Sau ghép, kiểm tra link, số liệu, trùng ID, trạng thái chứng nhận và giọng văn toàn báo cáo. Báo rõ phần hoàn tất và giới hạn còn lại; không hứa vòng tự chạy nền.
