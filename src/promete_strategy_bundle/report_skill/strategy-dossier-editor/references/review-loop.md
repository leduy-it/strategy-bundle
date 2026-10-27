# Phản biện và vòng cải thiện

## Tiêu chí

**Chặn ghép:** sai danh tính/nguồn hoặc số liệu; thiếu mã (thiếu metrics từng mã trong nguồn lịch sử được nêu rõ không tính là thiếu roster); bịa lý do policy hoặc thông tin doanh nghiệp; đổi screening thành chứng nhận; đánh đồng đóng góp lãi và trọng số; mất trạng thái gate chưa chạy; sửa nguồn bất biến; link nguồn hỏng khiến claim trọng yếu không kiểm được.

**Cần sửa biên tập:** mở đầu chung chung, các mã lặp cùng lời, nhiều bảng không có nhận định, dùng thuật ngữ không giải thích, luận điểm vượt sức bằng chứng, thiếu điểm riêng của chiến lược, giọng văn giữa hồ sơ không thống nhất.

**Insight đáng giữ:** chỉ ra quan hệ mới từ dữ liệu có sẵn, phản chứng hoặc câu hỏi có thể kiểm thử; phải ghi claim/evidence và hành động nghiên cứu. Không chấm insight bằng độ mới lạ nếu thiếu nguồn.

## Cách chạy một lần gọi

1. Writer nộp draft + review.json. Editor kiểm danh tính, toàn rổ, các số chủ chốt/gate và đọc lập luận từng mã. Phản hồi phải trỏ tới đoạn, sai khác và nguồn mong đợi; tránh “viết hay hơn” mà không chỉ ra vấn đề.
2. Lưu từng nhận xét: `id`, `round`, `severity`, `location`, `issue`, `requested_change`, `evidence`, `status`; có thể dùng `feedback.json` cạnh draft. Writer trả `resolution` + vị trí thay đổi, hoặc lý do còn thiếu bằng chứng.
3. Tối đa hai lượt sửa sau bản đầu. Editor xác minh lại phần thay đổi và kiểm lỗi liên quan; không mở vòng vô hạn. Lỗi chặn chưa sửa thì giữ draft chưa ghép; phần còn thiếu nghiên cứu ghi rõ trong hồ sơ và `unresolved_items`.
4. Editor ghép các hồ sơ đạt vào báo cáo chung, rà phần tổng hợp để kết luận không mâu thuẫn với các hồ sơ. Lưu trạng thái cuối và việc còn lại. Đây là vòng trong phiên hiện tại, không phải lịch tự chạy hay dịch vụ nền.

Lần gọi tiếp theo đọc phản hồi chưa đóng trước khi viết mới. Chỉ cải thiện skill khi người dùng yêu cầu cập nhật skill hoặc phản hồi hiện tại cho phép; không viết memory hệ thống như một hệ quả của vòng phản biện. Giữ insight riêng cho từng model và chỉ nâng thành kết luận chung khi đã đối chiếu đủ các nguồn liên quan trong cohort.

Khi review lô lịch sử, kiểm riêng ba lỗi dễ lọt: ghép return và drawdown từ hai seed thành một model; gọi số Validation là Test chỉ vì config có cửa sổ Test; kết luận rổ removal 2/3 phải PASS hoặc ticker removal đóng góp một mức lãi chưa lưu. Bản trích không đủ để tự xét lại gate, chỉ đủ báo cáo trạng thái và đặt câu hỏi kiểm chứng.

## Bài học biên tập từ các hồ sơ đã phản biện

- Trong phần dành cho người đọc, ưu tiên “rổ con”, “chi tiết xét điều kiện”, “lệnh đã khớp”, “lãi/lỗ”, “nhóm khởi tạo” thay cho child, adjudication, fills, P&L, cohort khi thuật ngữ tiếng Anh không giúp hiểu hơn. Giữ tên thuật toán, mã trạng thái và trường dữ liệu ở phần bằng chứng. Với chỉ số cần thiết, giải thích ngắn khi xuất hiện lần đầu; bỏ chỉ số phụ nếu không đóng góp vào lập luận.
- Khi nguồn chỉ cung cấp danh sách mã, nhóm các mã có cùng mức thiếu bằng chứng trong một hàng hoặc một đoạn, vẫn gọi đủ từng ticker. Dành dòng riêng cho mã có phép removal hoặc dữ kiện khác biệt; không dựng sự khác biệt giả chỉ để đủ số đoạn.
- Chú thích bảng chính nên nói dữ liệu đo gì, ở kỳ nào và seed nào. Việc catalog gộp cột từ nhiều seed, cách giải nén nguồn và dấu vết biên tập thuộc ghi chú nguồn hoặc review.json, trừ khi cần giải thích một sai lệch số liệu mà người đọc sẽ gặp.

Áp dụng theo nội dung thực có; không biến các bài học này thành một đoạn văn giống nhau cho mọi chiến lược. Khi chỉnh câu, giữ nguyên độ chắc chắn: “chưa biết đóng góp lợi nhuận” không được biến thành “không tạo lợi nhuận”.

## Ưu tiên mới của người dùng

Viết ngắn gọn, giống một chuyên gia đang giải thích trực tiếp. Thường chỉ cần vài nhận định chính và bảng số; không lặp cảnh báo hay kể quy trình làm báo cáo. Phần “Vì sao chọn rổ này?” phải trả lời việc chọn tập cổ phiếu ban đầu, không thay bằng lợi suất hậu kiểm hay lý do model giao dịch chưa được lưu. Khoảng 300–450 từ văn xuôi là gợi ý, không phải chỉ tiêu cần điền.
