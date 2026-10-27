# Lời văn: giọng chuyên gia của "Báo cáo chiến lược mẫu"

Giữ giọng của mẫu số 1: một chuyên gia đầu tư giải thích cho nhà đầu tư/đối tác,
kết luận trước, số đi kèm đối chứng, đọc như người viết chứ không như máy
(mục "Giọng người viết"). Nhưng tỉ mỉ hơn mẫu ở phần bằng
chứng: mọi con số truy được về nguồn, mọi giới hạn nói đúng mức, không có câu
nào hứa quá dữ liệu.

## Người đọc là nhà đầu tư

Báo cáo mặc định gửi nhà đầu tư, không phải hồ sơ nội bộ của lab. Trung thực
nhưng nói bằng ngôn ngữ đầu tư: số xấu vẫn nêu đủ, chỉ đổi cách gọi.

| Không viết (nội bộ) | Viết (nhà đầu tư) |
|---|---|
| seed 3, seed xấu nhất, trung vị 3 seed | lần huấn luyện 1/2/3 (giải thích một lần: cùng cấu hình, khởi tạo ngẫu nhiên khác nhau); cột "Lần 1 (trình bày)" |
| ứng viên nghiên cứu, chưa chứng nhận, chưa dùng cho vốn thật | câu miễn trừ chuẩn: mô phỏng trên dữ liệu lịch sử, đã tính phí; chọn từ nhiều cấu hình nên tương lai có thể thấp hơn; quá khứ không bảo đảm tương lai |
| cổng, gate, phễu 432/74, Deflated Sharpe, STAR, attempt ID | bảng "Kết quả kiểm định": tiêu chí nhà đầu tư hiểu được, Đạt / Chưa đạt kèm số |
| bộ lọc thêm sau khi xem kết quả; phép bỏ mã chưa chạy | bỏ; rủi ro tập trung nêu thẳng bằng số ở mục rủi ro |
| giả thuyết thiết kế, chưa đo; production; nhánh đối chứng; luật | "vai trò kỳ vọng"; "bộ chỉ báo chuẩn đang vận hành"; "quy tắc định lượng" |
| NAV (trong lời văn) | danh mục, giá trị danh mục |
| lãi chưa thực hiện, giá đánh dấu | lãi chưa được chốt, phụ thuộc diễn biến giá sau kỳ báo cáo |

Bìa đúng 4 dòng như mẫu: Mã định danh (rổ · bộ chỉ báo · thuật toán + "Version
<slug>"), Danh mục đầu tư, Giai đoạn huấn luyện, Giai đoạn kiểm định. Không dòng
"Trạng thái".

Tóm tắt kết thúc bằng đoạn "phù hợp với nhà đầu tư có khẩu vị rủi ro …" và rủi ro
lớn nhất. Khi kết quả không lặp lại qua các lần huấn luyện, nói ngay trong tóm tắt
("chỉ lần được trình bày có lãi"; "coi +37% là kịch bản thuận lợi, trung vị gần với
kỳ vọng hợp lý hơn"). Không gọi chiến lược là "yếu nhất" hay "để đối chiếu".

Hồ sơ nội bộ (gửi team, reviewer) mới dùng từ vựng cột trái; khi đó ghi rõ trong
yêu cầu, hoặc dùng strategy-dossier-editor.

## Nhịp của từng mục

**Tóm tắt điều hành.** Câu đầu là kết quả, đặt cạnh hai đối chứng, kèm kỳ đo:
"Trên giai đoạn kiểm định (…), chiến lược **X** đạt lợi suất quy năm **+38,75%**,
trong khi VN-Index tăng +7,51% và mua và nắm giữ chính rổ này lỗ −4,97%."
Đoạn hai: chiến lược là gì trong một hơi (thuật toán nói bằng tiếng Việt, tên
tiếng Anh trong ngoặc lần đầu), rổ, số tín hiệu, cách ra quyết định, và câu chốt
"rổ là phạm vi được phép giao dịch, không phải danh mục nắm giữ bắt buộc".
Rồi biểu đồ + bảng chỉ tiêu (ba lần huấn luyện). Kết bằng đoạn "phù hợp
với ai" và **rủi ro lớn nhất**, nói luôn phần nào đã kiểm soát và phần nào chưa
kiểm soát. Một câu về xử lý sự cố.

**1. Điểm khác biệt.** Đặt khung trước khi vào số: vì sao đánh giá chiến lược AI
khác đánh giá danh mục quỹ. Một phép đối lập rõ ("Quỹ truyền thống đi từ luận
điểm… Chiến lược mẫu đi theo chiều ngược lại…"), rồi bảng so sánh, rồi đoạn định
nghĩa chiến lược = trọng số + toàn bộ điều kiện đi kèm, đổi một mã là chiến lược mới.

**2. Mô tả danh mục.** Cấu trúc rổ (vốn hóa, sàn), cách rổ được tạo (quy tắc lấy
mẫu có nguồn, không phải chọn tay), rồi nhóm mã theo vai trò với ticker in đậm.
Nhóm ngành là mô tả rổ, không phải lý do policy mua/bán.

**3. Tín hiệu đầu vào.** Danh sách đánh số có nhãn đậm kết thúc bằng dấu hai chấm
("**Giữ bộ tín hiệu đủ gọn…:** …"), mỗi ý có một lý do định lượng (31 × 10 = 310
giá trị mỗi phiên). Bảng nhóm chỉ báo đủ mọi dòng. Kết bằng hành vi phòng thủ
nhưng chỉ ở mức cơ chế cho phép, không khẳng định policy đã làm nếu chưa có sổ lệnh.

**4. Hiệu quả thực tế.** Bối cảnh bất lợi trước ("giai đoạn kiểm định diễn ra
đúng vào lúc rổ suy yếu"), rồi cơ chế giải thích bằng một cụm in đậm ("**hệ thống
không bắt buộc phải mua**"), rồi câu giới hạn ("tỷ lệ tiền mặt thực tế vẫn cần
xác nhận bằng sổ giao dịch"). Bảng huấn luyện ↔ kiểm định.

**5. Quản trị rủi ro và vận hành.** Tiểu mục ngắn: sự cố mã (hai bước: ngoài mô
hình / trong mô hình), thanh khoản (đã quan sát gì, chưa giới hạn gì, cần chạy lại
gì trước khi triển khai), và **kết quả kiểm định**: bảng tiêu chí Đạt / Chưa đạt
kèm số, rồi câu miễn trừ chuẩn. Mục cuối này bắt buộc; mẫu gốc bỏ sót.

## Gọn nhưng giá trị hơn mẫu

Mẫu số 1 dài bằng lời giải thích chung; bản tốt hơn dài bằng phát hiện riêng.
Mỗi đoạn phải trả lời một câu người đọc sẽ hỏi, bằng số của chính chiến lược:

- **Lãi đến từ đâu?** Bảng từng mã (lệnh, lãi/lỗ, tỷ trọng tối đa/cuối kỳ) + hai
  đoạn: mã dẫn lãi, và mã ngược kỳ vọng (vị thế lớn mà lỗ).
- **Mô hình thực sự làm gì?** Tiền mặt trung vị, số mã nắm giữ, số phiên một mã
  trên 50% NAV. Không viết "ưu tiên về tiền mặt" nếu số cho thấy luôn đầy vốn.
- **Kết quả có lặp lại không?** Lần huấn luyện khác, năm khác. Nói rõ kỳ báo cáo là điển
  hình hay nằm ở phía tốt.
- **Vì sao chọn rổ/chỉ báo này?** Luật và câu hỏi thiết kế, rồi "mô hình được
  biết gì" và "vai trò kỳ vọng" cho từng nhóm chỉ báo. Phê bình kỹ thuật của bộ
  (đơn vị giá, cột trùng) thuộc hồ sơ nội bộ, không đưa vào báo cáo nhà đầu tư.

Cắt: đoạn định nghĩa lặp giữa các báo cáo (mục 1 tối đa một đoạn + bảng), danh
sách 31 tên chỉ báo không kèm lý do. Mục tiêu 6–8 trang A4.

## Câu chữ

- Kết luận trước, chi tiết sau. Mỗi đoạn một ý, 2–5 câu.
- Nối bằng đối lập có thông tin: "trong khi", "tuy nhiên", "nhờ đó", "vì vậy".
  Không mở đoạn bằng "Có thể thấy rằng", "Nhìn chung", "Đáng chú ý là".
- In đậm tiết kiệm: tên chiến lược, con số chủ đạo, ticker, cụm cơ chế then chốt.
  Tối đa vài cụm mỗi trang.
- Thuật ngữ: tiếng Việt trước, tiếng Anh trong ngoặc lần đầu (học tăng cường
  (Reinforcement Learning), nhiễu (noise)). Tên chỉ báo giữ tiếng Anh.
- Giới hạn viết như một bước vận hành, không như lời xin lỗi: "Trước khi triển
  khai, cần chạy lại theo các bậc vốn thực tế với giới hạn % ADV, trượt giá và tỷ
  lệ không khớp."
- Không tính từ quảng cáo không đo được: bỏ "bứt phá mạnh", "vượt trội tuyệt
  đối", "đã chứng minh hiệu quả". Để con số tự nói.

## Giọng người viết, không giọng máy

Khoa học ở số liệu và cách lập luận, nhưng câu chữ phải như một chuyên viên phân
tích đang giải thích cho khách hàng. Đọc to lên nghe phải tự nhiên.

- **Có người đứng sau:** dùng "chúng tôi" cho việc nhóm đã làm và đánh giá của
  nhóm ("Chúng tôi huấn luyện lại cùng cấu hình ba lần…", "Chúng tôi xem +37% là
  kịch bản thuận lợi"). Không lạm dụng: vài lần mỗi mục là đủ.
- **Kể theo lý do:** nói vì sao làm trước khi nói kết quả ("Một năm tốt chưa nói
  lên nhiều, nên chúng tôi…"). Nối các câu bằng quan hệ nhân quả thật.
- **Câu dài ngắn xen nhau.** Một câu ngắn chốt ý ("SBT thì khác.") sau một câu
  dài chứa số. Tránh chuỗi câu cùng khuôn "Chủ ngữ + là + … : …".
- **Ít dấu hai chấm, ít in đậm.** Dấu hai chấm chỉ dùng trước danh sách hoặc một
  lời giải thích thật sự. In đậm tên chiến lược, con số chủ đạo và ticker chủ
  lực; không in đậm cụm nhận xét chung.
- **Nói việc cụ thể, bằng động từ thường:** "mua", "chốt lãi", "giữ suốt kỳ",
  "chưa lần nào được mua", thay cho "được giải ngân", "hành xử", "vận hành".
- **Lời khuyên là của nhóm:** "Chúng tôi khuyến nghị chỉ dùng chiến lược cho một
  phần nhỏ của danh mục tổng", không lặp "Nhà đầu tư nên…" ở mọi mục.

Dấu hiệu văn máy, gặp là viết lại:

| Kiểu văn máy | Viết lại |
|---|---|
| "Đổi lại, …", "Ngược lại, …", "Lưu ý rằng …" mở đầu liên tục | Nối bằng nội dung: "Cái giá phải trả là…", "KDC lại là trường hợp ngược lại." |
| "Rủi ro lớn nhất là **X**: …" | "Điều cần cân nhắc kỹ là mức tập trung, vì…" |
| "không chỉ … mà còn …", "không phải X, mà là Y" | Nói thẳng điều đúng |
| Bộ ba tính từ, câu kết khái quát ("mang lại sự linh hoạt, hiệu quả và bền vững") | Bỏ, để con số nói |
| Mỗi đoạn kết bằng một câu bài học | Chỉ kết khi câu đó thêm thông tin mới |
| Cùng một khuôn câu lặp giữa ba báo cáo | Mỗi báo cáo kể theo điểm riêng của chiến lược đó |
| Giải thích lý do không có trong dữ liệu ("vì tín hiệu chưa đủ thuận lợi") | Chỉ nói điều quan sát được ("chưa lần nào được mua") |

## Chuẩn số liệu

- Dấu thập phân phẩy, nghìn chấm: +38,75%, 2,774, 2,5 năm, 1.000 tỷ. Không trộn
  kiểu Anh (bộ dựng cảnh báo `38.75%`). Biểu đồ cũng dùng dấu phẩy.
- Dấu âm là "−" (U+2212) trong bảng/số; dấu cộng cho lợi suất và chênh lệch dương.
- "đpt" = điểm phần trăm cho chênh lệch giữa hai tỷ lệ; ghi chú một lần dưới bảng.
- Ghi rõ kỳ đo ở câu đầu và ở chú thích hình. Gọi đúng tên kỳ: số Validation là
  "giai đoạn kiểm định", không gọi là Test.
- "Trung vị 3 lần huấn luyện" chỉ dùng khi đã kiểm từng chỉ tiêu lấy trung vị
  riêng qua bảng từng lần; ghi chú điều đó dưới bảng. Nếu catalog gộp cột từ nhiều seed,
  không kể nó như hành trình một model.

## Tỉ mỉ hơn mẫu: lỗi đã gặp ở mẫu số 1, không lặp lại

| Mẫu gốc | Vấn đề | Cách viết đúng |
|---|---|---|
| Không nhắc G3 (bản import 14/09: FAIL; phễu v3: PASS) | Người đọc không biết trạng thái, cũng không biết nó đổi theo phiên bản phễu | Mục "Kết quả kiểm định" ghi từng tiêu chí Đạt / Chưa đạt kèm số; phiên bản phễu ghi ở facts/README |
| "đã chứng minh tính hiệu quả khi kiểm định thực tế" | Nói quá, backtest ≠ thực tế | "Bảng dưới đặt hai giai đoạn cạnh nhau để thấy kết quả đến trong điều kiện nào" |
| "vốn hóa vừa và nhỏ nên có rủi ro thanh khoản thấp" | Ngược nghĩa | "…nên thanh khoản là rủi ro cần theo dõi sát" |
| `38.75%` trong biểu đồ, `2.5 năm`, `+38.75%` trong bảng | Trộn dấu thập phân | Dấu phẩy mọi nơi |
| Ô trống cột "Quỹ đầu tư" | Bảng thiếu vế so sánh | Điền nội dung hoặc "không áp dụng" |
| "Tiêu chỉ", "Chiến lược mẫu số này" | Lỗi gõ | Soát chính tả trước khi dựng |
| Không nói một mã góp 98–113% lãi (nhãn P-3) | Giấu rủi ro tập trung | Nêu trong tóm tắt hoặc mục rủi ro |
| Placeholder đỏ "Phân tích XAI…" | Bản nháp lọt ra PDF | Bỏ, hoặc viết khi đã có số; bộ dựng cảnh báo TODO/TBD |
| "mức xấu nhất giữa ba phiên bản là 10,39%" | Thiếu dấu âm, "phiên bản" mơ hồ | "lần huấn luyện kém nhất sụt −10,39%" |
| "Cơ chế … bỏ mã" không có bằng chứng | Bỏ phí dữ kiện removal đã chạy | Dẫn kết quả removal kèm phiên bản phễu |

Kiểm tra cuối cùng bằng hai câu hỏi: nhà đầu tư có gặp từ nào chỉ người trong lab
mới hiểu không (grep: seed, NAV, gate, phễu, chứng nhận, ứng viên, giả thuyết,
production)? Người đọc có thể tưởng chiến lược đã giao dịch thật, kết quả chắc
chắn lặp lại, hay đã kiểm sức chứa vốn không? Nếu có, sửa câu.
