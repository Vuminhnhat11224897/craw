# Realtime crawl theo URL

API nhận một URL bài báo và trả file JSON UTF-8 chứa dữ liệu của `articles`,
`article_images`, `article_videos`. Mặc định API chỉ crawl và xuất file, không
đọc hoặc ghi PostgreSQL. `save_to_db=true` bật lưu DB; `download_images=true`
chỉ dùng cùng `save_to_db=true` và chỉ tải ảnh cho bài mới.

## Cấu hình

Từ thư mục gốc, sao chép `craw_real_times/.env.sample` thành
`craw_real_times/.env`, rồi đặt `INTERNAL_API_KEY` và
`ARTICLE_UUIDV5_NAMESPACE`. Nếu `.env` đã tồn tại, chỉ thêm hoặc cập nhật
các biến còn thiếu; giữ nguyên các secret hiện có. Namespace phải trùng với
`crawl_lastest_news` để ID của cùng một URL nhất quán. Đặt `DATABASE_URL`
khi dùng `save_to_db=true`.

Tất cả thông số vận hành của realtime nằm trong `.env.sample`: thời gian chờ,
giới hạn dung lượng, đồng thời, retry, nhịp request, thư mục ảnh, endpoint
MOHA/MOF, địa chỉ lắng nghe và cổng Docker. Cấu hình selector/URL của từng báo
trong `config/sites` và `extractor/site_configs` là quy tắc trích xuất của
nguồn tin.

## Chạy

Yêu cầu Python 3.10+ và PostgreSQL chỉ khi bật lưu DB.

```powershell
python -m pip install -r craw_real_times/requirements.txt
python -m craw_real_times
```

Chạy container từ thư mục gốc:

```powershell
docker compose --env-file craw_real_times/.env.sample --env-file craw_real_times/.env -f craw_real_times/compose.yml up -d --build
```

Chạy trực tiếp sẽ lắng nghe ở `REALTIME_LISTEN_HOST` (mẫu là loopback).
Compose chỉ bind cổng host theo `REALTIME_BIND_ADDRESS` (cũng là loopback)
và mount ảnh từ `craw_real_times/realtime_images` vào
`REALTIME_CONTAINER_IMAGES_FOLDER`.
API chạy một worker vì giới hạn đồng thời và nhịp theo domain được giữ trong
bộ nhớ của tiến trình.

## Gọi API

```powershell
curl.exe -X POST "http://127.0.0.1:8000/internal/v1/articles/crawl" -H "Content-Type: application/json" -H "X-API-Key: <key-trong-env>" -d '{"url":"https://vnexpress.net/duong-dan-bai-bao.html","save_to_db":false}' -o article.json
```

Các endpoint khác: `GET /internal/v1/sites` và `GET /internal/openapi.json`
cũng cần `X-API-Key`; `GET /health/live` và `GET /health/ready` không cần key.
`/health/ready` kiểm tra cấu hình và danh sách nguồn, không phụ thuộc DB vì
chế độ xuất file vẫn hoạt động khi DB không được cấu hình.
