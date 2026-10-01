# Realtime News Crawler — Production

Service nội bộ crawl một bài báo theo URL, trả JSON để bên gọi lưu bài và
video. API ảnh riêng ghi ảnh và job vào PostgreSQL; worker tải ảnh, upload lên
MinIO rồi cập nhật trạng thái từng ảnh trong DB. Hai API chỉ nhận `url`.

Hiện có **97 cấu hình nguồn**. Lấy danh sách đang được service sử dụng qua
`GET /internal/v1/sites`.

## Luồng production

```text
Bên gọi → API crawl → JSON bài + URL ảnh/video → bên gọi lưu bài/video
        → API ảnh  → article_images + image_download_jobs
                                           ↓
                                     image-worker
                                           ↓
                                      MinIO → cập nhật article_images
```

1. Gọi `POST /internal/v1/articles/crawl` để lấy nội dung. API này không ghi
   bài, ảnh, video hoặc job vào DB.
2. Bên gọi lưu `articles` và `article_videos`. Nếu bảng ảnh có khóa ngoại đến
   `articles`, phải lưu bài trước khi gọi API ảnh.
3. Khi cần tải ảnh, gọi `POST /internal/v1/articles/images` với cùng URL.
   API crawl lại bài, ghi ảnh và job trong cùng transaction, trả `202` sau
   khi commit. API này không lưu bài hoặc video.
4. Worker upload ảnh rồi cập nhật `article_images.status/image_path`.
5. Bên gọi đọc DB theo `article_id` hoặc `image_ids` trong response API ảnh.
   Service không có endpoint tra trạng thái job.

Nếu bên gọi/cron đã lưu dòng ảnh, API ảnh tái dùng ID theo
`article_id + sequence_number`. Ảnh `downloaded` được giữ nguyên; ảnh `failed`
được đưa lại vào queue khi gọi API ảnh. Cron lưu ảnh không tự tạo job tải ảnh.
Khi lưu lại metadata, bên gọi cần giữ đường dẫn/trạng thái ảnh đã tải xong,
tránh ghi đè chúng bằng dữ liệu `pending` từ JSON crawl.

## Hạ tầng

| Thành phần | Cấu hình production |
|---|---|
| API | Compose service `realtime-news`, container `craw-real-times` |
| Worker | Compose service `image-worker`, profile `images` |
| Image chung | `craw-real-times:latest`, Python 3.11 |
| API trên host | `http://127.0.0.1:8101` mặc định |
| PostgreSQL | `100.91.202.88:5432`, database `person_articles`, schema `public` |
| Bảng ảnh và queue | `public.article_images`, `public.image_download_jobs` |
| MinIO S3 API | `http://100.91.202.88:9002` |
| MinIO console | `http://100.91.202.88:9001` |
| Bucket | `news-article-images` |
| Namespace bài | `3681377d-f509-4554-9d2e-2ee156a60cc0` |

Máy triển khai cần Docker Engine, Docker Compose v2 và kết nối tới PostgreSQL,
MinIO, DNS/HTTP(S) của các nguồn báo. Compose này chạy API và worker;
PostgreSQL/MinIO là dịch vụ có sẵn.

`article_images` phải có các cột `id`, `article_id`, `image_path`, `status`,
`sequence_number`, `created_at`. Migration queue không tạo các bảng bài/ảnh/video;
chúng do hệ thống lưu bài quản lý. Tài khoản DB của API/worker cần quyền
`SELECT`, `INSERT`, `UPDATE` trên bảng ảnh và queue. Tài khoản migration cần
quyền tạo/sửa bảng và index trong `public`.

Bucket phải tồn tại và tài khoản MinIO phải có quyền upload object. Service
không tự tạo bucket hoặc đổi quyền truy cập.

## Cấu hình

Các lệnh triển khai chạy trong thư mục chứa [compose.yml](compose.yml):

```bash
cd /home/ad/crawl_bao/craw_real_times
# Chỉ thực hiện khi chưa có .env:
cp -n .env.sample .env
chmod 600 .env
```

Sửa `.env` để điền key, tài khoản DB và MinIO. Nếu đã có `.env`, thêm các biến
còn thiếu và giữ secret hiện có. Không dùng nguyên key/password mẫu để chạy.

| Biến | Giá trị mẫu/mặc định | Ý nghĩa |
|---|---|---|
| `INTERNAL_API_KEY` | cần điền | Key gửi qua header `X-API-Key` |
| `ARTICLE_UUIDV5_NAMESPACE` | `3681377d-f509-4554-9d2e-2ee156a60cc0` | Giữ nguyên để ID trùng với hệ thống lưu bài |
| `ARTICLE_DATABASE_URL` | cần điền tài khoản | SQLAlchemy URL của DB ảnh/queue |
| `MINIO_ENDPOINT` | `http://100.91.202.88:9002` | S3 API; không dùng console hoặc `/browser/...` |
| `MINIO_BUCKET` | `news-article-images` | Bucket ảnh |
| `MINIO_ACCESS_KEY` | cần điền | Access key MinIO |
| `MINIO_SECRET_KEY` | cần điền | Secret key MinIO |
| `MINIO_REGION` | `us-east-1` | Region ký request upload |
| `IMAGE_WORKERS` | `4` | Số ảnh tải đồng thời, từ `1` đến `16` |
| `COMPOSE_PROFILES` | `images` trong file mẫu | Bật worker trong các lệnh Compose thông thường |
| `RECORD_TIMEZONE` | `Asia/Ho_Chi_Minh` | Múi giờ timestamp bản ghi export |

URL DB mẫu đặt schema production rõ ràng:

```dotenv
ARTICLE_DATABASE_URL=postgresql+psycopg2://user:password@100.91.202.88:5432/person_articles?options=-csearch_path%3Dpublic
COMPOSE_PROFILES=images
```

Thay `user/password` bằng tài khoản thực. URL-encode credentials có ký tự đặc
biệt như `@`, `:`, `/`, `#`, `%`. Prefix `postgresql+psycopg2://` dành cho
SQLAlchemy; lệnh `psql` ở dưới dùng tham số kết nối riêng.

### Listener và cổng Docker

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `REALTIME_BIND_ADDRESS` | `127.0.0.1` | IP host Docker publish cổng |
| `REALTIME_HOST_PORT` | `8101` | Cổng API trên host |
| `REALTIME_LISTEN_HOST` | `127.0.0.1` | Listener Python; Compose override thành `0.0.0.0` trong container |
| `REALTIME_LISTEN_PORT` | `8101` | Listener Python; Compose cố định cổng container `8101` |
| `REALTIME_WORKERS` | `1` | Chỉ chấp nhận `1` vì giới hạn crawl/nhịp domain là process-local |

Mặc định chỉ máy chủ gọi được API qua `127.0.0.1:8101`. Để gọi qua Tailscale,
đặt `REALTIME_BIND_ADDRESS` thành IP Tailscale của máy triển khai rồi dùng IP
đó trong URL bên gọi. `0.0.0.0` publish cổng trên mọi interface của host.
Khi truy cập qua mạng ngoài vùng tin cậy, dùng reverse proxy HTTPS và giới hạn
truy cập cổng API.

`.env` không được commit/copy vào image. Compose nạp secret qua `env_file` khi
tạo container. [.env.sample](.env.sample) phải được giữ trong image vì
`settings.py` và entrypoint đọc nó để lấy giá trị mặc định.

### Giới hạn crawl và HTTP

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `MAX_CONCURRENT_CRAWLS` | `16` | Crawl chạy đồng thời, dùng chung cho hai API |
| `MAX_QUEUED_CRAWLS` | `200` | Request tối đa đợi slot crawl |
| `QUEUE_TIMEOUT_SECONDS` | `180` | Thời gian tối đa đợi trong queue |
| `CRAWL_TIMEOUT_SECONDS` | `30` | Ngân sách tác vụ sau khi có slot |
| `CONNECT_TIMEOUT_SECONDS` | `3` | Timeout kết nối nguồn |
| `READ_TIMEOUT_SECONDS` | `10` | Timeout đọc HTTP |
| `HTTP_MAX_RETRIES` | `1` | Retry HTTP, còn bị giới hạn bởi cấu hình nguồn |
| `MAX_HTML_BYTES` | `5242880` | HTML/JSON nguồn tối đa 5 MiB |
| `MAX_IMAGE_BYTES` | `20971520` | Mỗi ảnh tối đa 20 MiB |
| `MAX_VIDEOS_PER_ARTICLE` | `5` | URL video tối đa trong export |
| `BLOCKED_IMAGE_URLS` | `https://bqn.1cdn.vn/assets/images/grey.gif` | URL ảnh bị loại, phân cách bằng dấu phẩy |
| `DEFAULT_DOMAIN_DELAY_SECONDS` | `0.5` | Khoảng nghỉ cùng host, có thể được cấu hình nguồn override |
| `HTTP_MAX_REDIRECTS` | `6` | Số redirect tối đa |
| `HTTP_CHUNK_BYTES` | `4096` | Kích thước chunk đọc response |
| `RETRY_BACKOFF_CAP_SECONDS` | `1` | Giới hạn backoff HTTP; `Retry-After` nguồn có thể dài hơn |
| `RETRY_AFTER_SECONDS` | `1` | Header gợi ý retry cho lỗi API retryable có HTTP `429/503` |

Request chờ theo thứ tự đến khi hết slot. Queue đầy hoặc chờ quá hạn trả
`503 BUSY`. Chờ queue không tính vào ngân sách crawl; client/reverse proxy nên
đặt timeout lớn hơn `210` giây với cấu hình mặc định. Service không cache bài.

| Biến header/API nguồn | Giá trị mẫu/mặc định |
|---|---|
| `HTTP_USER_AGENT` | Chuỗi trình duyệt trong `.env.sample` |
| `HTTP_ACCEPT` | `text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8` |
| `HTTP_JSON_ACCEPT` | `application/json` |
| `HTTP_IMAGE_ACCEPT` | `image/*,*/*;q=0.8` |
| `HTTP_ACCEPT_LANGUAGE` | `vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7` |
| `MOHA_API_BASE` | `https://api-portal.moha.gov.vn/api/Public` |
| `MOF_API_BASE` | `https://www.mof.gov.vn/api` |

Hai biến API nguồn phục vụ fallback nội dung từ Bộ Nội vụ và Bộ Tài chính.

## Migration và khởi động

Thứ tự: cấu hình `.env` → kiểm tra bảng ảnh/bucket → migration queue → chạy
API và worker.

Áp dụng [migration queue](db/migrations/20260928_image_download_jobs.sql) bằng
tài khoản có quyền DDL. Thay `<db-user>`; `-W` hỏi password:

```bash
psql -h 100.91.202.88 -p 5432 -U '<db-user>' -d person_articles -W \
  -v ON_ERROR_STOP=1 --single-transaction \
  -c 'SET search_path TO public;' \
  -f db/migrations/20260928_image_download_jobs.sql
```

Migration tạo queue/index và cập nhật constraint queue cũ để giữ được job
hoàn tất. Chạy trước khi bật API ảnh/worker; service không tự chạy migration.

```bash
docker compose --profile images config --quiet
docker compose --profile images up -d --build
docker compose --profile images ps
curl --fail --max-time 5 http://127.0.0.1:8101/health/ready
```

Thay địa chỉ `curl` nếu đã đổi IP/cổng publish. `COMPOSE_PROFILES=images` trong
`.env` giúp lệnh Compose thông thường cũng chạy worker; các lệnh dưới đây giữ
rõ `--profile images` để luôn bao gồm cả hai service.

API phải `healthy`; worker phải `Up`, không lặp lỗi DB/MinIO trong log. Hai
service chạy UID/GID `1000:1000`, có `restart: unless-stopped`. Không cần volume
media; dữ liệu bền vững nằm ở PostgreSQL và MinIO.

## API

| Method | Endpoint | `X-API-Key` | Kết quả |
|---|---|---|---|
| `POST` | `/internal/v1/articles/crawl` | có | `200`, file JSON bài/ảnh/video |
| `POST` | `/internal/v1/articles/images` | có | `202`, ghi ảnh và job |
| `GET` | `/internal/v1/sites` | có | Nguồn đang được cấu hình |
| `GET` | `/internal/openapi.json` | có | Schema OpenAPI hiện hành |
| `GET` | `/health/live` | không | `{"status":"alive"}` |
| `GET` | `/health/ready` | không | `{"status":"ready","configured_sources":97}` |

Response do ứng dụng xử lý có `X-Request-ID`, `Cache-Control: no-store`.
Không có UI `/docs` hoặc ReDoc. Trong Postman, chọn body `raw / JSON` và gửi
`Content-Type: application/json`, `X-API-Key: <key>`.

Thiết lập key cho các ví dụ và thay URL mẫu bằng URL bài thực:

```bash
export REALTIME_API_KEY='<key-trong-.env>'
```

### Crawl bài

```bash
curl --fail-with-body --max-time 240 \
  -X POST http://127.0.0.1:8101/internal/v1/articles/crawl \
  -H "X-API-Key: $REALTIME_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://vnexpress.net/duong-dan-bai-bao.html"}'
```

Body chỉ có `url`, chuỗi từ 1 đến 2000 ký tự. Trường khác bị từ chối với `422 INVALID_OPTIONS`. URL phải HTTP(S), thuộc
nguồn được hỗ trợ, không có credentials/cổng tùy chỉnh. Đích tải và redirect
được kiểm tra để chặn IP private/reserved.

Response `200` là JSON UTF-8 có header
`Content-Disposition: attachment; filename="article_<article_id>.json"`.
Để lưu ở phía gọi, thêm `-o article_<article_id>.json`; server không lưu JSON.
Ví dụ cấu trúc đầy đủ, các ID là placeholder:

```json
{
  "schema_version": "1.0",
  "request_id": "<request_id>",
  "status": "success",
  "exported_at": "2026-09-28T07:00:00Z",
  "generated_timestamp_timezone": "Asia/Ho_Chi_Minh",
  "duration_ms": 352,
  "data": {
    "articles": [{
      "id": "<article_id>", "title": "Tiêu đề bài báo",
      "description": "Mô tả", "content": "Nội dung bài báo",
      "category_id": "thoi_su", "category_name": "Thời sự",
      "comments": null, "tags": "Thời sự, Tin tức",
      "url": "https://vnexpress.net/duong-dan-bai-bao.html",
      "publish_date": "2026-09-28T13:30:00+07:00",
      "created_at": "2026-09-28T14:00:00",
      "updated_at": "2026-09-28T14:00:00", "article_name": "vnexpress"
    }],
    "article_images": [{
      "id": "<image_id>", "article_id": "<article_id>",
      "image_path": "https://cdn.example.com/anh.jpg", "status": "pending",
      "sequence_number": 1, "created_at": "2026-09-28T14:00:00"
    }],
    "article_videos": [{
      "id": "<video_id>", "article_id": "<article_id>",
      "video_path": "https://cdn.example.com/video.mp4",
      "sequence_number": 1, "created_at": "2026-09-28T14:00:00"
    }]
  },
  "warnings": []
}
```

`articles` có một bài; không có media thì mảng ảnh/video rỗng. `tags` là chuỗi
phân cách bằng dấu phẩy, `comments` hiện luôn `null`. Thiếu chuyên mục có thể
trả warning `CATEGORY_MISSING`. Thiếu ngày xuất bản thì dùng thời điểm hiện tại.

`exported_at` là UTC. `publish_date` chuyển về `RECORD_TIMEZONE`, có offset;
`created_at/updated_at` là giờ địa phương không kèm offset, tương ứng timestamp
không timezone của schema bài. Timestamp export được tạo lại mỗi lần crawl,
không phải ngày tạo bản ghi gốc trong DB.

Ảnh trong JSON crawl giữ URL nguồn và `pending`, chỉ là metadata export. Video
giữ URL nguồn và không được tải. ID ảnh/video export được sinh mới mỗi lần;
lấy `image_ids` từ API ảnh để tra những dòng đã lưu trong DB.

### Yêu cầu tải ảnh

```bash
curl --fail-with-body --max-time 240 \
  -X POST http://127.0.0.1:8101/internal/v1/articles/images \
  -H "X-API-Key: $REALTIME_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://vnexpress.net/duong-dan-bai-bao.html"}'
```

Response `202`:

```json
{"status":"accepted","article_id":"<article_id>","image_ids":["<image_id>"]}
```

`accepted` nghĩa là ảnh/job cần tạo đã được commit hoặc ảnh có sẵn được tái
dùng; chưa có nghĩa tải ảnh thành công. Bài không có ảnh trả `image_ids: []`
và không ghi job.

### Danh sách nguồn và OpenAPI

```bash
curl --fail -H "X-API-Key: $REALTIME_API_KEY" \
  http://127.0.0.1:8101/internal/v1/sites
curl --fail -H "X-API-Key: $REALTIME_API_KEY" \
  http://127.0.0.1:8101/internal/openapi.json
```

Mỗi nguồn trả `site_key`, `base_url`, `article_name`. `97` là số cấu hình,
không phải cam kết mọi nguồn luôn truy cập được. Hai cấu hình có thể cùng
domain; resolver chọn identity `baodongkhoi` cho `dongkhoi.baovinhlong.vn`.

## Worker ảnh, trạng thái và retry

| Nơi đọc | Trạng thái | Ý nghĩa |
|---|---|---|
| `article_images` | `pending` | Chờ hoặc đang tải |
| `article_images` | `downloaded` | Đã upload MinIO, `image_path` là đường dẫn object |
| `article_images` | `failed` | Tải thất bại, giữ URL nguồn |
| `image_download_jobs` | `pending` | Chờ claim hoặc chờ lần retry kế tiếp |
| `image_download_jobs` | `processing` | Worker đang giữ lease |
| `image_download_jobs` | `downloaded` | Job hoàn tất, được giữ lại |
| `image_download_jobs` | `failed` | Hết lần thử, lỗi kết thúc sớm hoặc dòng ảnh bị thay đổi/xóa |

Worker claim bằng `FOR UPDATE SKIP LOCKED`, lease `120` giây. Mỗi ảnh có ngân
sách tải/upload `60` giây, tối đa `5` lần xử lý. Lỗi retryable lên lịch sau
`30`, `120`, `600`, `1800` giây; ảnh rỗng, MIME không hỗ trợ hoặc URL không
hợp lệ có thể kết thúc ngay. Nếu worker dừng khi đang xử lý, job được claim
lại sau khi lease hết; lần thử cuối hết lease được chuyển thành `failed`.

Ảnh được upload nguyên bản, không resize/nén lại, giữ `Content-Type`. MIME hỗ
trợ: JPEG, PNG, WebP, GIF, AVIF, SVG, BMP, TIFF. Dung lượng không vượt
`MAX_IMAGE_BYTES`.

Object key dùng ngày đưa ảnh vào queue theo `RECORD_TIMEZONE`, ID bài và thứ
tự ảnh. Ngày được giữ trong job để retry qua ngày khác không đổi thư mục.
Đuôi file được xác định từ `Content-Type` thực tế khi tải ảnh:

```text
Bucket:     news-article-images
Object key: <ngày>_<tháng>_<năm>/<article_id>_img_<sequence_number>.<extension>
DB path:    /news-article-images/<ngày>_<tháng>_<năm>/<article_id>_img_<sequence_number>.<extension>
Ví dụ:      /news-article-images/1_9_2026/ff5fde6b-860b-53e9-ada1-9ba2a98cc40a_img_7.avif
```

`image_path` khi tải xong là **đường dẫn tương đối gồm bucket**, có đuôi ảnh
và không có host. Trong queue, key mới giữ tên chưa có đuôi cho tới lúc worker
xác định MIME; khi hoàn tất, job lưu key đầy đủ đã upload. Job đang chờ dùng
key cũ `articles/...` được worker đổi sang dạng ngày/ID bài/thứ tự khi xử lý;
object đã tải xong trước đó được giữ nguyên. Hệ thống hiển thị ghép path với
host phục vụ media của mình. Bucket private cần backend tạo presigned URL
hoặc proxy ảnh; không đưa
secret MinIO cho trình duyệt.

Tra ảnh/job của một bài bằng `psql` hoặc công cụ quản trị DB:

```sql
SELECT i.id, i.sequence_number, i.status AS image_status, i.image_path,
       j.status AS job_status, j.attempts, j.next_attempt_at,
       j.locked_until, j.last_error
FROM public.article_images AS i
LEFT JOIN public.image_download_jobs AS j ON j.image_id = i.id
WHERE i.article_id = '<article_id>'
ORDER BY i.sequence_number;
```

Theo dõi backlog:

```sql
SELECT status, count(*) AS jobs
FROM public.image_download_jobs
GROUP BY status
ORDER BY status;
```

Sau khi sửa lỗi nguồn/MinIO, gọi lại API ảnh bằng URL bài để requeue ảnh
`failed` và reset số lần thử của job thất bại. Job `pending/processing` được
giữ; ảnh `downloaded` không bị tải lại. Chưa có cơ chế tự xóa lịch sử job.

## Vận hành và cập nhật

```bash
# Trạng thái và log:
docker compose --profile images ps
docker compose logs -f realtime-news
docker compose --profile images logs -f image-worker

# Áp dụng thay đổi code/dependency:
docker compose --profile images up -d --build

# Nạp thay đổi .env bằng cách tạo lại container:
docker compose --profile images up -d --force-recreate

# Khởi động lại với cấu hình container hiện có:
docker compose --profile images restart

# Dừng / chạy lại container:
docker compose --profile images stop
docker compose --profile images start

# Dừng và xóa container/network của service:
docker compose --profile images down
```

`restart` không nạp `.env` mới; dùng `up -d --force-recreate` sau khi sửa env.
`down` không xóa DB hoặc object MinIO vì chúng nằm ngoài Compose này.

Healthcheck gọi `/health/ready` mỗi `30` giây, timeout `5` giây, đánh dấu API
`unhealthy` sau `3` lần lỗi liên tiếp. Ready phản ánh ứng dụng đã khởi động và
số cấu hình nguồn; **không kiểm tra DB, MinIO hay khả năng crawl từng nguồn**.
Worker không có healthcheck riêng: kiểm tra container, log và backlog DB.
`restart: unless-stopped` xử lý tiến trình thoát; Docker không tự restart chỉ
vì container bị đánh dấu `unhealthy`.

Log API ghi `request_id`, path, HTTP status, thời gian; đối chiếu bằng request
ID trong header/body. Log worker dùng `image_id`.

## Lỗi và xử lý sự cố

Lỗi nghiệp vụ/validation có dạng:

```json
{
  "request_id": "<request_id>", "status": "error",
  "error": {"code": "BUSY", "message": "...", "retryable": true}
}
```

| HTTP | Code | Retry | Cách xử lý |
|---|---|---|---|
| `401` | `UNAUTHORIZED` | không | Kiểm tra `X-API-Key` và key trong env container |
| `422` | `INVALID_OPTIONS` | không | Chỉ gửi `url`; xem `error.details` |
| `422` | `UNSUPPORTED_SITE` | không | Đối chiếu `/internal/v1/sites` |
| `422` | `INVALID_URL` | không | Dùng URL hợp lệ của nguồn, bỏ credentials/cổng tùy chỉnh |
| `422` | `NOT_AN_ARTICLE` | không | Gửi trang bài có nội dung, không gửi trang chủ/danh mục |
| `404` | `ARTICLE_NOT_FOUND` | không | Nguồn trả 404/410 hoặc redirect về trang chủ/trang 404 |
| `429` | `RATE_LIMITED` | có | Giảm tần suất, tuân thủ `Retry-After` |
| `502` | `UPSTREAM_ERROR` | tùy lỗi | Kiểm tra nguồn, DNS, kết nối, redirect, dung lượng |
| `503` | `BUSY` | có | Đợi theo `Retry-After`, giảm request đồng thời |
| `503` | `IMAGE_QUEUE_NOT_CONFIGURED` | không | Điền DB URL, tạo lại API container |
| `503` | `MEDIA_STORAGE_NOT_CONFIGURED` | không | Điền endpoint/key MinIO, tạo lại container |
| `503` | `IMAGE_QUEUE_UNAVAILABLE` | có | Kiểm tra kết nối DB rồi retry API ảnh |
| `504` | `CRAWL_TIMEOUT` | có | Retry sau hoặc kiểm tra nguồn chậm |
| `500` | `INTERNAL_ERROR` | không | Xem log theo request ID, kiểm tra schema/migration |

Dùng `error.retryable` thực tế để quyết định retry. Một số lỗi upstream như
JSON nguồn không hợp lệ hoặc response quá lớn không được đánh dấu retryable.

API ảnh trả `202` nhưng ảnh chưa tải: kiểm tra profile worker, `job_status`,
`next_attempt_at`, `last_error`. Ảnh `downloaded` nhưng không hiển thị: kiểm tra
cách ghép host với đường dẫn tương đối, quyền đọc bucket/presigned URL. Thiếu
bảng ảnh/queue có thể gây `500`; áp dụng đúng migration/schema.

## ID và cấu hình nguồn

`articles.id` là UUIDv5 từ namespace cố định và URL chuẩn hóa:

```python
uuid.uuid5(uuid.UUID("3681377d-f509-4554-9d2e-2ee156a60cc0"), normalized_url)
```

Cùng namespace và cùng chuỗi URL cho cùng ID. Chuẩn hóa bỏ khoảng trắng hai
đầu, fragment, query trừ nguồn đặt `keep_query_params=True`, và port mặc định
`80/443`. Không gộp `www` với host gốc, `http` với `https` hay dấu `/` cuối;
URL khác chuỗi có thể ra ID khác. Redirect sang bài khác vẫn giữ ID từ URL
yêu cầu đã chuẩn hóa. ID ảnh/video export dùng UUIDv7, request ID dùng UUIDv4.

Sửa/thêm nguồn trong `config/sites/<site>.py` cho host/quy tắc URL và
`extractor/site_configs/<domain>.yml` cho selector. Một số nguồn dùng heuristic
chung khi không có YAML riêng. Build lại cả API và worker sau khi thay đổi.

## File phục vụ production

| File/thư mục | Vai trò |
|---|---|
| `__main__.py`, `app.py` | Khởi động API, route, xác thực và lỗi |
| `schemas.py`, `errors.py` | Body request, lỗi nghiệp vụ |
| `service.py`, `article_crawler.py` | Crawl URL, dựng kết quả; helper upload cho worker |
| `http_client.py`, `runtime.py` | HTTP deadline/giới hạn, queue crawl, nhịp domain |
| `serializers.py`, `db/models.py` | JSON export, cấu trúc cột và sinh ID |
| `image_registration.py`, `image_jobs.py` | Ghi ảnh/job trong transaction |
| `image_worker.py` | Claim, tải/upload, retry và cập nhật kết quả |
| `db/migrations/` | Migration queue trước khi chạy API ảnh/worker |
| `settings.py`, `.env.sample` | Cấu hình và giá trị mặc định runtime |
| `config/`, `site_resolver.py` | Registry nguồn, nhận diện/kiểm tra URL |
| `extractor/` | Trích xuất nội dung, selector từng nguồn |
| `requirements.txt` | Dependency pin phiên bản |
| `Dockerfile`, `compose.yml`, `.dockerignore` | Build/chạy production |
| `.gitignore` | Loại secret, bytecode, JSON export phía gọi khỏi Git |

`.env` thật được quản lý trên máy triển khai. Sao lưu PostgreSQL và MinIO theo
quy trình vận hành của hai hệ thống đó.
