# Realtime crawl theo URL

API nhận URL một bài báo, crawl ngay lúc gọi và trả về một file JSON UTF-8 gồm
ba phần `articles`, `article_images` và `article_videos`. Service không dùng
database. Hỗ trợ **97 nguồn** (xem [Nguồn được hỗ trợ](#nguồn-được-hỗ-trợ)).

Mặc định API chỉ crawl rồi trả JSON. Gửi thêm `download_images=true` thì
service tải **ảnh** về `IMAGES_FOLDER` và ghi **metadata video** vào
`VIDEOS_FOLDER`. Video không được tải về, chỉ lưu link (xem
[Lưu ảnh và video](#lưu-ảnh-và-video)).

`articles.id` dùng cùng namespace UUIDv5 với luồng cũ `crawl_lastest_news`, nên
cùng một URL ra cùng ID ở cả hai luồng (xem [ID bài báo](#id-bài-báo)).

## Trên máy chủ hiện tại

| Mục | Giá trị |
|---|---|
| Cách chạy | Docker, container `craw-real-times`, image `craw-real-times:latest` |
| Địa chỉ | `http://127.0.0.1:8101` (chỉ truy cập được từ chính máy chủ) |
| Thư mục ảnh | `/data/crawl_realtime_articles_nhat/realtime_images` |
| Thư mục metadata video | `/data/crawl_realtime_articles_nhat/realtime_videos` |
| Namespace ID | `3681377d-f509-4554-9d2e-2ee156a60cc0` |
| Tự khởi động lại | có (`restart: unless-stopped`), kể cả khi reboot máy |

Không dùng cổng `8000` (service khác đang chiếm). Cổng `8100` là cổng của bản
chạy `nohup` cũ, đã bỏ.

## Cấu hình

Sao chép `.env.sample` thành `.env` trong thư mục `craw_real_times`, đặt
`INTERNAL_API_KEY` và **giữ nguyên** `ARTICLE_UUIDV5_NAMESPACE`:

| Biến | Bắt buộc | Mặc định | Ý nghĩa |
|---|---|---|---|
| `INTERNAL_API_KEY` | có | | Key cho header `X-API-Key` |
| `ARTICLE_UUIDV5_NAMESPACE` | có | `3681377d-f509-4554-9d2e-2ee156a60cc0` | Namespace sinh ID bài báo, phải trùng `crawl_lastest_news` |
| `IMAGES_FOLDER` | không | `./crawl_realtime_articles_nhat/realtime_images` | Thư mục lưu ảnh và metadata ảnh |
| `VIDEOS_FOLDER` | không | `./crawl_realtime_articles_nhat/realtime_videos` | Thư mục lưu metadata video |
| `REALTIME_LISTEN_HOST` | không | `127.0.0.1` | Địa chỉ server lắng nghe |
| `REALTIME_LISTEN_PORT` | không | `8101` | Cổng server lắng nghe |
| `REALTIME_WORKERS` | không | `1` | Chỉ được là `1` |
| `REALTIME_BIND_ADDRESS` | không | `127.0.0.1` | Chỉ dùng cho Docker: địa chỉ host publish cổng |
| `REALTIME_HOST_PORT` | không | `8101` | Chỉ dùng cho Docker: cổng trên host |

Nếu đã có `.env` thì chỉ thêm các biến còn thiếu, giữ nguyên secret hiện có.
Các thông số vận hành khác (timeout, giới hạn dung lượng, đồng thời, retry, nhịp
request theo domain, User-Agent, endpoint MOHA/MOF) đều nằm trong `.env.sample`
và có giá trị mặc định hợp lý. Selector và URL của từng báo nằm trong
`config/sites` và `extractor/site_configs`.

Sửa `.env` hoặc code xong phải khởi động lại service mới có hiệu lực.

## Chạy bằng Docker (khuyến nghị)

Các lệnh chạy **trong** thư mục `craw_real_times`:

```bash
docker compose up -d --build    # build image và chạy (lần đầu hoặc sau khi sửa code)
docker compose up -d            # áp dụng lại sau khi sửa .env
docker compose ps               # trạng thái, cột STATUS phải là "healthy"
docker compose logs -f          # xem log
docker compose restart          # khởi động lại
docker compose down             # dừng và xoá container
curl http://127.0.0.1:8101/health/ready
```

Các file liên quan:

| File | Nội dung |
|---|---|
| [Dockerfile](Dockerfile) | `python:3.11-slim`, cài `requirements.txt`, chạy `python -m craw_real_times` |
| [compose.yml](compose.yml) | Service `realtime-news`, container `craw-real-times`, port, volume, healthcheck |
| [.dockerignore](.dockerignore) | Loại `.env`, `tests`, `.git`, thư mục ảnh khỏi image |

Cách container được cấu hình:

- **Cổng**: server trong container nghe `0.0.0.0:8101`, publish ra host ở
  `REALTIME_BIND_ADDRESS:REALTIME_HOST_PORT`, mặc định `127.0.0.1:8101`. Muốn
  máy khác hoặc container khác gọi được thì đặt `REALTIME_BIND_ADDRESS=0.0.0.0`.
- **Thư mục ảnh/video**: `/data/crawl_realtime_articles_nhat` được mount vào
  container ở **cùng đường dẫn**, nên đường dẫn trong response và
  `metadata.json` dùng được luôn trên host. `compose.yml` đặt cố định
  `IMAGES_FOLDER`/`VIDEOS_FOLDER` vào thư mục này, giá trị trong `.env` bị bỏ qua.
- **Quyền file**: container chạy với uid `1000:1000`, nên ảnh thuộc user
  `admin1`, không phải `root`.
- **Secret**: `.env` không nằm trong image, chỉ được nạp lúc chạy qua
  `env_file`. Image có thể chia sẻ mà không lộ key.
- **Healthcheck**: gọi `/health/ready` mỗi 30 s. Hỏng 3 lần liên tiếp thì
  Docker đánh dấu `unhealthy`.
- **Tài nguyên**: khoảng 70 MB RAM khi nhàn rỗi, khoảng 110 MB sau một đợt tải
  ảnh. CPU tối đa khoảng 1 core.

## Chạy trực tiếp bằng Python

Dùng khi phát triển. Không chạy song song với container vì cùng cổng `8101`.

Yêu cầu Python 3.10+. Chạy **từ thư mục cha** của `craw_real_times` vì đây là
một package:

```bash
cd /home/admin1
python -m pip install -r craw_real_times/requirements.txt
python -m craw_real_times                                   # chạy foreground
nohup python -m craw_real_times > realtime.log 2>&1 &       # chạy nền
curl http://127.0.0.1:8101/health/ready
pkill -f "bin/python -m craw_real_times"                    # dừng
```

- `IMAGES_FOLDER`/`VIDEOS_FOLDER` nếu là đường dẫn tương đối thì tính theo thư
  mục đang đứng khi khởi động. `.env` trên máy chủ đặt đường dẫn tuyệt đối
  `/data/crawl_realtime_articles_nhat/...`.
- **Chỉ chạy một worker.** Giới hạn đồng thời và nhịp request theo domain được
  giữ trong bộ nhớ của tiến trình, nhiều worker sẽ vượt giới hạn.

Chạy test:

```bash
cd /home/admin1
python -m unittest discover -s craw_real_times/tests -t .
```

## Endpoint

| Method | Path | Cần `X-API-Key` | Mục đích |
|---|---|---|---|
| `POST` | `/internal/v1/articles/crawl` | có | Crawl một bài theo URL |
| `GET` | `/internal/v1/sites` | có | Danh sách báo được hỗ trợ |
| `GET` | `/internal/openapi.json` | có | Schema OpenAPI |
| `GET` | `/health/live` | không | Tiến trình còn sống |
| `GET` | `/health/ready` | không | Cấu hình hợp lệ, trả số nguồn đã cấu hình |

Mọi response đều có header `X-Request-ID` và `Cache-Control: no-store`.

```bash
curl http://127.0.0.1:8101/health/ready
# {"status":"ready","configured_sources":97}

curl -H "X-API-Key: <key-trong-env>" http://127.0.0.1:8101/internal/v1/sites
# {"sites":[{"site_key":"24h","base_url":"https://www.24h.com.vn","article_name":"24h"}, …]}
```

### `POST /internal/v1/articles/crawl`

Request body:

| Trường | Kiểu | Mặc định | Ghi chú |
|---|---|---|---|
| `url` | string | bắt buộc | 1–2000 ký tự, phải thuộc một báo trong `/internal/v1/sites` |
| `download_images` | bool | `false` | Tải ảnh và ghi metadata ảnh/video ra đĩa |

Trường lạ trong body sẽ bị từ chối (kể cả `save_to_db` cũ).

```bash
curl -X POST "http://127.0.0.1:8101/internal/v1/articles/crawl" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key-trong-env>" \
  -d '{"url":"https://vnexpress.net/duong-dan-bai-bao.html","download_images":true}' \
  -o article.json
```

Response `200` là file JSON (`Content-Disposition: attachment; filename="article_<id>.json"`):

```json
{
  "schema_version": "1.0",
  "request_id": "…",
  "status": "success",
  "exported_at": "2026-09-23T09:11:59.594234Z",
  "generated_timestamp_timezone": "Asia/Ho_Chi_Minh",
  "duration_ms": 352,
  "data": {
    "articles": [{ "id": "…", "title": "…", "description": "…", "content": "…",
                   "category_id": "…", "category_name": "…", "comments": null, "tags": "…",
                   "url": "…", "publish_date": "…", "created_at": "…", "updated_at": "…",
                   "article_name": "…" }],
    "article_images": [{ "id": "…", "article_id": "…", "image_path": "…",
                         "status": "…", "sequence_number": 1, "created_at": "…" }],
    "article_videos": [{ "id": "…", "article_id": "…", "video_path": "…",
                         "sequence_number": 1, "created_at": "…" }]
  },
  "media": {
    "images_folder": "/data/crawl_realtime_articles_nhat/realtime_images/<article_id>",
    "images_metadata": "/data/crawl_realtime_articles_nhat/realtime_images/<article_id>/metadata.json",
    "videos_metadata": "/data/crawl_realtime_articles_nhat/realtime_videos/<article_id>/metadata.json"
  },
  "warnings": []
}
```

`media` chỉ có khi gửi `download_images=true`. Trường nào là `null` thì bài
không có ảnh/video tương ứng (hoặc ghi đĩa lỗi, xem `MEDIA_SAVE_FAILED`).

- `warnings` có thể gồm `CATEGORY_MISSING` (trang không có chuyên mục),
  `IMAGE_DOWNLOAD_FAILED` (một ảnh tải lỗi, có `sequence_number`) hoặc
  `MEDIA_SAVE_FAILED` (không ghi được file/metadata ra đĩa).
- `image_path`: `status=pending` khi không tải ảnh, là URL gốc. Khi đã tải
  (`status=downloaded`) là đường dẫn file local. Ảnh tải lỗi có `status=failed`
  và giữ URL gốc.
- `video_path` luôn là URL gốc vì video không được tải về.

Luồng xử lý:

1. Xác định báo từ URL (`UNSUPPORTED_SITE` nếu không hỗ trợ) rồi chuẩn hoá URL.
2. Tải HTML và trích xuất tiêu đề, nội dung, chuyên mục, tag, ảnh, video.
3. Nếu `download_images=true`: tải ảnh và ghi metadata như mục dưới.

### Lưu ảnh và video

Mỗi bài có một thư mục, tên là `article_id`, tức UUIDv5 tính từ URL bài (xem
[ID bài báo](#id-bài-báo)). Cùng một URL luôn ra cùng một thư mục. ID này trùng
với `data.articles[0].id` trong response.

```text
/data/crawl_realtime_articles_nhat/
  realtime_images/
    60b89257-08e8-53e8-8dc8-1f9507694e03/
      img_1.jpg
      img_2.jpg
      metadata.json
  realtime_videos/
    60b89257-08e8-53e8-8dc8-1f9507694e03/
      metadata.json        # chỉ có link video, không có file video
```

`metadata.json` của ảnh:

```json
{
  "article_id": "60b89257-…", "url": "https://vnexpress.net/…-5123580.html",
  "title": "…", "article_name": "vnexpress", "publish_date": "…",
  "crawled_at": "2026-09-23T16:51:27+07:00", "request_id": "…",
  "images": [
    { "sequence_number": 1, "source_url": "https://…jpg", "status": "downloaded",
      "file_name": "img_1.jpg", "local_path": "/data/crawl_realtime_articles_nhat/realtime_images/…/img_1.jpg",
      "content_type": "image/jpeg", "size_bytes": 334020 },
    { "sequence_number": 2, "source_url": "https://…", "status": "failed" }
  ]
}
```

`metadata.json` của video có cùng phần đầu, thay `images` bằng
`"videos": [{ "sequence_number": 1, "video_url": "https://…m3u8" }]`. Số video
tối đa theo `MAX_VIDEOS_PER_ARTICLE`.

- Bài không có ảnh thì không tạo thư mục ảnh. Bài không có video thì không tạo
  thư mục video.
- Chỉ nhận response có `Content-Type` là ảnh (jpeg, png, webp, gif, avif, svg,
  bmp, tiff) và không quá `MAX_IMAGE_BYTES`.
- Crawl lại cùng link thì **thay toàn bộ** thư mục cũ. Ảnh được tải vào một thư
  mục tạm `.<tên>.<hex>.tmp` rồi mới đổi tên vào chỗ, nên không bao giờ thấy thư
  mục dở dang. Nếu crawl lỗi giữa chừng (ví dụ timeout) thì thư mục cũ giữ nguyên.
- Không có dọn dẹp tự động. Cần xoá bớt thì tự xoá thư mục theo nhu cầu.

### Giới hạn và nhịp request

| Cơ chế | Mặc định | Hành vi |
|---|---|---|
| Số crawl đồng thời | `MAX_CONCURRENT_CRAWLS=16` | Request vượt số này sẽ xếp hàng chờ (đến trước phục vụ trước). |
| Hàng chờ | `MAX_QUEUED_CRAWLS=200` | Hàng chờ đầy thì request mới nhận ngay `503 BUSY` kèm header `Retry-After`. |
| Thời gian chờ tối đa trong hàng | `QUEUE_TIMEOUT_SECONDS=180` | Chờ quá lâu thì nhận `503 BUSY`. Thời gian chờ không tính vào `CRAWL_TIMEOUT_SECONDS`, nên phía gọi nên đặt timeout HTTP ≥ 210s. |
| Giãn cách theo domain | `DEFAULT_DOMAIN_DELAY_SECONDS=0.5` | Các request vào cùng một báo chạy lần lượt, cách nhau ít nhất 0.5s. Các báo khác nhau chạy song song. |
| Thời gian tối đa mỗi crawl | `CRAWL_TIMEOUT_SECONDS=30` | Quá thời gian thì trả `504 CRAWL_TIMEOUT` |
| Cache | không có | Gọi lại cùng URL sẽ crawl lại từ báo |

Đo thực tế trên máy chủ (2026-09-23):

- Không tải ảnh: khoảng 250–600 ms mỗi bài.
- Có tải ảnh: 1–5 s với vài ảnh, 9–13 s với 11–16 ảnh. Thời gian tải ảnh vẫn
  tính trong `CRAWL_TIMEOUT_SECONDS`.
- 12 bài của 4 báo, gửi 8 bài song song, có tải ảnh: xong hết sau 13.6 s.
  Các bài cùng báo chạy lần lượt do giãn cách theo domain.

### Lỗi

Mọi lỗi có dạng:

```json
{ "request_id": "…", "status": "error",
  "error": { "code": "BUSY", "message": "…", "retryable": true } }
```

| HTTP | `code` | Retry được | Nguyên nhân |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | không | Thiếu hoặc sai `X-API-Key` |
| 422 | `INVALID_OPTIONS` | không | Body sai (có thêm `details`) |
| 422 | `UNSUPPORTED_SITE` | không | Báo chưa được hỗ trợ |
| 422 | `INVALID_URL` | không | URL không thuộc host của báo đó |
| 422 | `NOT_AN_ARTICLE` | không | URL không phải bài báo (kể cả trang chủ) hoặc không đọc được nội dung |
| 404 | `ARTICLE_NOT_FOUND` | không | Báo trả 404/410, hoặc redirect về trang chủ/trang 404 (vnexpress trả `302 → /404.html`) |
| 429 | `RATE_LIMITED` | có | Báo đang chặn tần suất |
| 502 | `UPSTREAM_ERROR` | có | Không kết nối được, báo trả lỗi, quá nhiều redirect, trang quá lớn… |
| 503 | `BUSY` | có | Hàng chờ đầy, hoặc chờ quá `QUEUE_TIMEOUT_SECONDS` |
| 504 | `CRAWL_TIMEOUT` | có | Báo phản hồi chậm hoặc vượt thời gian tối đa |
| 500 | `INTERNAL_ERROR` | không | Lỗi không lường trước, xem log theo `request_id` |

## ID bài báo

`articles.id` là **UUIDv5** tính từ URL bài báo đã chuẩn hoá:

```python
id = uuid.uuid5(ARTICLE_UUIDV5_NAMESPACE, normalized_url)
```

UUIDv5 lấy SHA-1 của `namespace + URL`, giữ 128 bit và đặt version là 5, nên
**cùng một URL luôn ra cùng một ID**. Không cần tra DB mới biết ID, và crawl lại
nhiều lần vẫn ra ID cũ. Hàm sinh ID là `article_id_from_url` trong
[db/models.py](db/models.py). Chuỗi đưa vào UUIDv5 phải đúng bằng giá trị lưu ở
cột `articles.url`.

Namespace chuẩn là **`3681377d-f509-4554-9d2e-2ee156a60cc0`**, đặt trong
`.env` ở biến `ARTICLE_UUIDV5_NAMESPACE`. Đây là namespace luồng cũ
`crawl_lastest_news` đang dùng, nên cùng một URL sẽ ra cùng `articles.id` ở cả
hai luồng. Đổi namespace thì mọi ID (và tên thư mục ảnh/video) đều đổi theo.

### Chuẩn hoá URL

Hàm `_normalize_internal_url` trong [article_crawler.py](article_crawler.py)
chạy trước khi sinh ID:

1. Bỏ khoảng trắng hai đầu và nối với `base_url` của báo.
2. Chỉ nhận host của báo: `x.vn`, `www.x.vn` hoặc subdomain `*.x.vn`.
3. Bỏ `#fragment`.
4. Bỏ query `?...`, trừ các báo có `keep_query_params=True` trong cấu hình.
5. Bỏ port mặc định (`:443` với https, `:80` với http).

Kết quả với cùng một bài (namespace minh hoạ):

| URL đầu vào | URL sau chuẩn hoá | Cùng ID? |
|---|---|---|
| `https://vnexpress.net/a-123.html` | `https://vnexpress.net/a-123.html` | gốc |
| `https://vnexpress.net/a-123.html?utm=x#top` | `https://vnexpress.net/a-123.html` | có |
| `https://vnexpress.net:443/a-123.html` | `https://vnexpress.net/a-123.html` | có |
| `https://www.vnexpress.net/a-123.html` | giữ nguyên | **khác** |
| `http://vnexpress.net/a-123.html` | giữ nguyên | **khác** |
| `https://VNEXPRESS.net/a-123.html` | giữ nguyên | **khác** |
| `https://vnexpress.net/a-123.html/` | giữ nguyên | **khác** |

Bước chuẩn hoá **không** gộp `www`/không `www`, `http`/`https`, chữ hoa trong
host hay dấu `/` cuối. Phía gọi API nên gửi URL đúng dạng mà báo và
`crawl_lastest_news` dùng. Nếu không, cùng một bài có thể nhận hai ID khác nhau.

Kiểm tra ID của một file export:

```python
import json, uuid
a = json.load(open("article.json"))["data"]["articles"][0]
assert a["id"] == str(uuid.uuid5(uuid.UUID("3681377d-f509-4554-9d2e-2ee156a60cc0"), a["url"]))
```

### Các ID khác

| Trường | Cách sinh | Ổn định giữa các lần crawl? |
|---|---|---|
| `articles.id` | UUIDv5(namespace, URL) | có |
| `article_images.id`, `article_videos.id` | UUIDv7 (ngẫu nhiên, có gắn thời gian) | không |
| `request_id` | UUIDv4 ngẫu nhiên, trả trong body và header `X-Request-ID` | không |
| `category_id` | Lấy từ trang hoặc URL chuyên mục. Nếu không có thì là slug của tên chuyên mục (`thoi_su`). Slug dài hơn 100 ký tự thì cắt bớt và thêm 8 ký tự hex SHA-1. | có |

## Nguồn được hỗ trợ

97 cấu hình, lấy từ `GET /internal/v1/sites` ngày 2026-09-23. URL gửi lên phải
thuộc host của một nguồn dưới đây (có hoặc không `www`, hoặc subdomain), nếu
không sẽ nhận `422 UNSUPPORTED_SITE`. `article_name` là giá trị ghi vào
`articles.article_name`.

<details>
<summary>Báo, tạp chí (79)</summary>

| Domain | `site_key` | `article_name` |
|---|---|---|
| 24h.com.vn | `24h` | `24h` |
| anninhthudo.vn | `anninhthudo` | `anninhthudo` |
| baobacninhtv.vn | `baobacninhtv` | `baobacninhtv` |
| baobinhduong.vn | `baobinhduong` | `baobinhduong` |
| baocamau.vn | `baocamau` | `baocamau` |
| baocantho.com.vn | `baocantho` | `baocantho` |
| baocaobang.vn | `baocaobang` | `baocaobang` |
| baodaklak.vn | `baodaklak` | `baodaklak` |
| baodanang.vn | `baodanang` | `baodanang` |
| baodautu.vn | `baodautu` | `baodautu` |
| baodienbienphu.vn | `baodienbienphu` | `baodienbienphu` |
| baodongnai.com.vn | `baodongnai` | `baodongnai` |
| baodongthap.vn | `baodongthap` | `baodongthap` |
| baogialai.com.vn | `baogialai` | `baogialai` |
| baohaiphong.vn | `baohaiphong` | `baohaiphong` |
| baohatinh.vn | `baohatinh` | `baohatinh` |
| baohaugiang.com.vn | `baohaugiang` | `baohaugiang` |
| baohungyen.vn | `baohungyen` | `baohungyen` |
| baokhanhhoa.vn | `baokhanhhoa` | `baokhanhhoa` |
| baolaichau.vn | `baolaichau` | `baolaichau` |
| baolamdong.vn | `baolamdong` | `baolamdong` |
| baolangson.vn | `baolangson` | `baolangson` |
| baolaocai.vn | `baolaocai` | `baolaocai` |
| baonghean.vn | `baonghean` | `baonghean` |
| baoninhbinh.org.vn | `baoninhbinh` | `baoninhbinh` |
| baophapluat.vn | `baophapluat` | `baophapluat` |
| baophutho.vn | `baophutho` | `baophutho` |
| baoquangngai.vn | `baoquangngai` | `baoquangngai` |
| baoquangninh.vn | `baoquangninh` | `baoquangninh` |
| baoquangtri.vn | `baoquangtri` | `baoquangtri` |
| baosonla.vn | `baosonla` | `baosonla` |
| baotayninh.vn | `baotayninh` | `baotayninh` |
| baothainguyen.vn | `baothainguyen` | `baothainguyen` |
| baothanhhoa.vn | `baothanhhoa` | `baothanhhoa` |
| baotuyenquang.com.vn | `baotuyenquang` | `baotuyenquang` |
| baovinhlong.com.vn | `baovinhlong` | `baovinhlong` |
| baoxaydung.vn | `baoxaydung` | `baoxaydung` |
| bnews.vn | `bnews` | `bnews` |
| cafebiz.vn | `cafebiz` | `cafebiz` |
| cafef.vn | `cafef` | `cafef` |
| cand.com.vn | `cand` | `cand` |
| congly.vn | `congly` | `congly` |
| daibieunhandan.vn | `daibieunhandan` | `daibieunhandan` |
| dantri.com.vn | `dantri` | `dantri` |
| dongkhoi.baovinhlong.vn | `baodongkhoi` | `baodongkhoi` |
| dongkhoi.baovinhlong.vn | `dongkhoi_baovinhlong` | `dongkhoi_baovinhlong` |
| eva.vn | `eva` | `eva` |
| genk.vn | `genk` | `genk` |
| giadinh.suckhoedoisong.vn | `giadinh_suckhoedoisong` | `giadinh_suckhoedoisong` |
| hanoimoi.vn | `hanoimoi` | `hanoimoi` |
| huengaynay.vn | `huengaynay` | `huengaynay` |
| kenh14.vn | `kenh14` | `kenh14` |
| khoahocphattrien.vn | `khoahocphattrien` | `khoahocphattrien` |
| laodong.vn | `laodong` | `laodong` |
| nguoiquansat.vn | `nguoiquansat` | `nguoiquansat` |
| nhandan.vn | `nhandan` | `nhandan` |
| nld.com.vn | `nguoilaodong` | `nguoilaodong` |
| nongnghiepmoitruong.vn | `nongnghiepmoitruong` | `nongnghiepmoitruong` |
| plo.vn | `plo` | `plo` |
| qdnd.vn | `qdnd` | `qdnd` |
| sggp.org.vn | `sggp` | `sggp` |
| soha.vn | `soha` | `soha` |
| tapchitoaan.vn | `tapchitoaan` | `tapchitoaan` |
| thanhnien.vn | `thanhnien` | `thanhnien` |
| tienphong.vn | `tienphong` | `tienphong` |
| tinnhanhchungkhoan.vn | `tinnhanhchungkhoan` | `tinnhanhchungkhoan` |
| travinh.baovinhlong.vn | `travinh_baovinhlong` | `travinh_baovinhlong` |
| tuoitre.vn | `tuoitre` | `tuoitre` |
| vietbao.vn | `vietbao` | `vietbao` |
| vietnambiz.vn | `vietnambiz` | `vietnambiz` |
| vietnamfinance.vn | `vietnamfinance` | `vietnamfinance` |
| vietnamnet.vn | `vietnamnet` | `vietnamnet` |
| vietnamplus.vn | `vietnamplus` | `vietnamplus` |
| vneconomy.vn | `vneconomy` | `vneconomy` |
| vnexpress.net | `vnexpress` | `vnexpress` |
| vov.vn | `vov` | `vov` |
| vtcnews.vn | `vtcnews` | `vtcnews` |
| vtv.vn | `vtv` | `vtv` |
| znews.vn | `znews` | `znews` |

</details>

<details>
<summary>Cơ quan nhà nước (18)</summary>

| Domain | `site_key` | `article_name` |
|---|---|---|
| bocongan.gov.vn | `bocongan` | `bocongan` |
| bvhttdl.gov.vn | `bvhttdl` | `bvhttdl` |
| cema.gov.vn | `cema` | `cema` |
| mae.gov.vn | `mae` | `mae` |
| mard.gov.vn | `mard` | `mard` |
| mattran.org.vn | `mattran` | `mattran` |
| mod.gov.vn | `modgov` | `modgov` |
| moet.gov.vn | `moet` | `moet` |
| mof.gov.vn | `mof` | `mof` |
| mofa.gov.vn | `mofa` | `mofa` |
| moh.gov.vn | `moh` | `moh` |
| moha.gov.vn | `moha` | `moha` |
| moit.gov.vn | `moit` | `moit` |
| moj.gov.vn | `moj` | `moj` |
| mst.gov.vn | `mst` | `mst` |
| thanhtra.gov.vn | `thanhtra` | `thanhtra` |
| vpcp.chinhphu.vn | `vpcp` | `vpcp` |
| vtv.gov.vn | `vtvgov` | `vtv` |

</details>

Đã kiểm tra crawl thật (có tải ảnh) ngày 2026-09-23 với vnexpress, tuoitre,
cafef, thanhnien. Các nguồn khác dùng cấu hình chung với `crawl_lastest_news`
nhưng chưa được kiểm tra riêng qua API này.

Thêm hoặc sửa nguồn:

- `config/sites/<site>.py`: `base_url`, host được phép, quy tắc URL bài báo.
- `extractor/site_configs/<domain>.yml`: selector nội dung, ảnh, và
  `category_extractors` (hàm trích chuyên mục trong `extractor/article.py`).
- Sửa xong chạy `docker compose up -d --build`.

## Cấu trúc thư mục

```text
craw_real_times/
  __main__.py          # điểm khởi động, đọc .env, chạy uvicorn
  app.py               # FastAPI: route, xác thực, định dạng lỗi
  service.py           # luồng crawl một bài, lưu ảnh/metadata
  article_crawler.py   # tải HTML, chuẩn hoá URL, kiểm tra bài báo, trích xuất
  http_client.py       # HTTP có giới hạn thời gian, dung lượng, redirect
  runtime.py           # giới hạn đồng thời, giãn cách theo domain, deadline
  serializers.py       # dựng JSON export
  settings.py          # đọc biến môi trường
  site_resolver.py     # URL -> nguồn
  db/models.py         # hàm sinh ID article_id_from_url
  config/sites/        # cấu hình từng nguồn
  extractor/           # bộ trích xuất nội dung, site_configs/*.yml
  tests/               # unit test
  Dockerfile, compose.yml, .dockerignore
  .env.sample          # mẫu cấu hình, .env thật không commit
```

