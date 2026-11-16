# Approved knowledge workflow

Thư mục `staging/` là nơi đặt tài liệu chờ duyệt. Runtime không đọc thư mục
này. Mỗi tài liệu được phép dùng trong `approved/` phải có một file metadata
cùng tên trong `metadata/`, ví dụ `safety-basics.md` đi với
`metadata/safety-basics.json`.

Runtime chỉ được đọc tài liệu trong `approved/` khi metadata tương ứng đã được
người có thẩm quyền rà soát. Hiện thư mục này không chứa nội dung chuyên môn;
`knowledge_version` vì vậy vẫn là `none-unapproved`.

Quy trình đưa một tài liệu vào sử dụng:

1. Lưu bản nguồn và URL/ấn bản, ngày truy cập, phạm vi sử dụng.
2. Tạo metadata theo `metadata/schema.json`; `approval_status` ban đầu là `draft`.
3. Người rà soát có thẩm quyền ghi tên/vai trò, ngày review và đổi trạng thái
   thành `approved` hoặc `rejected`. Tài liệu sản phẩm không y khoa có thể được
   chủ sở hữu sản phẩm duyệt; tài liệu phục hồi chức năng, dinh dưỡng và an toàn
   y tế phải có chuyên gia phù hợp.
4. Chỉ tài liệu có `approval_status=approved`, chưa hết hạn và đúng phạm vi mới được ingestion.
5. Mỗi thay đổi làm tăng `knowledge_version` và chạy lại regression T10–T13,
   T28–T30, T38 trước khi phát hành.

Bộ truy hồi hiện tại không cần dịch vụ vector database: tài liệu approved được
chia đoạn, chuẩn hóa dấu tiếng Việt và xếp hạng theo độ trùng token. Đây là
đường triển khai an toàn cho bộ tài liệu nhỏ; chỉ cần chuyển sang embedding
database khi corpus thực sự lớn.

Lệnh kiểm tra tài liệu:

```powershell
python -m backend.knowledge.validate
```

Không đặt fixture, tài liệu chưa duyệt hay nội dung do LLM sinh vào `approved/`.

Không đặt fixture, tài liệu chưa duyệt hay nội dung do LLM sinh vào `approved/`.
