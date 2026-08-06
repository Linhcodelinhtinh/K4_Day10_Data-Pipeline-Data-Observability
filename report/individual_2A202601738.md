# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                           |
| ------------------ | --------------------------------------------------- |
| Họ và tên       | Nguyễn Khánh Toàn                                |
| MSSV               | 2A202601738                                         |
| Khóa/Lớp         | K4                                                  |
| Tên nhóm         | 5 Angry Man                                         |
| Vai trò chính    | Data Ingestion & Raw Lineage Owner (Thành viên 2) |
| Ngày hoàn thành | 2026-08-06                                          |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable      | File/hàm phụ trách                                                                                                                     | Input nhận vào                                              | Output bàn giao                                                     | Trạng thái |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | -------------------------------------------------------------------- | ------------ |
| Crossref API Client     | `src/ingestion/crossref.py` (`fetch_source_records`, `_request_with_retry`)                                                         | `Settings.source_query`, `source_filter`, `max_results` | Raw response JSON (`data/raw/crossref_response.json`)              | Hoàn thành |
| Payload Parsing         | `src/ingestion/crossref.py` (`parse_crossref_payload`, `_extract_authors`, `_extract_pdf_url`, `_format_date`, `_clean_text`) | Crossref JSON payload                                         | Danh sách`PaperRecord` chuẩn hóa, `paper_id` ổn định (DOI) | Hoàn thành |
| Raw Snapshot cho Repair | `src/ingestion/crossref.py` (`load_raw_records`)                                                                                      | `data/raw/crossref_records.json`                            | Snapshot tái sử dụng được cho cleaning và repair flow         | Hoàn thành |
| Lưu trữ Raw Lineage   | `data/raw/`                                                                                                                             | Raw API response & parsed records                             | `crossref_response.json`, `crossref_records.json`                | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                                         | Thành viên/module được hỗ trợ                                 | Kết quả                                                                                             |
| -------------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Xác nhận contract`PaperRecord` (paper_id, published, authors...) | TV3 (`cleaning.py`), TV4 (`embeddings.py`)                       | Đảm bảo`build_clean_dataframe` và `text_for_embedding` nhận đúng field từ raw records     |
| Kiểm tra dữ liệu raw dùng cho Repair                             | TV1/TV3 (`corruption_flow.py`, `repair_dataframe_from_snapshot`) | Xác nhận`load_raw_records` đọc đúng 24 bản ghi gốc để phục hồi dữ liệu sau corruption |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                | File/hàm/artifact liên quan | Kết quả bàn giao                                                                                                   | Cách xác minh                                                                                                                 |
| ---------------------------------------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Gọi Crossref API với retry/backoff cho lỗi 429/503      | `_request_with_retry()`     | Request tự động retry tối đa 5 lần, tôn trọng header`Retry-After`                                           | Đọc code; kiểm tra không có exception khi chạy`run_phase1.py`                                                           |
| Parse payload thành`PaperRecord` chuẩn                 | `parse_crossref_payload()`  | 24/24 bản ghi hợp lệ (có DOI, title, abstract) được giữ lại, bản ghi thiếu field bị loại                 | `python -c "import json; print(len(json.load(open('data/raw/crossref_records.json', encoding='utf-8'))))"` → `24`          |
| Lưu raw response & raw records để phục vụ repair      | `fetch_source_records()`    | `data/raw/crossref_response.json` (payload gốc) và `data/raw/crossref_records.json` (records đã parse)        | Kiểm tra 2 file tồn tại trong`data/raw/`                                                                                   |
| Cung cấp hàm nạp lại snapshot cho pipeline khác dùng | `load_raw_records()`        | Được`phase1.py` và `corruption_flow.py` gọi lại để tránh fetch API nhiều lần và để repair dữ liệu | Grep`load_raw_records` trong `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/ingestion/cleaning.py` |

**Mô tả output cụ thể:**
Đã lấy được 24 bản ghi bài báo học thuật từ Crossref (query `"agentic retrieval augmented generation large language model"`, filter theo ngày xuất bản gần đây và `has-abstract:true`). Mỗi bản ghi có `paper_id` là DOI ổn định, dùng xuyên suốt toàn bộ pipeline (clean, embedding, evaluation, corruption, repair) làm document identity.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Lấy dữ liệu bài báo học thuật từ một API bên ngoài không ổn định (rate limit, lỗi tạm thời), chuẩn hóa thành cấu trúc dữ liệu nội bộ nhất quán, đồng thời lưu lại snapshot thô để các thành viên khác có thể tái tạo (repair) dữ liệu sạch mà không cần gọi lại API mỗi lần chạy pipeline.

### Cách triển khai

- `_request_with_retry()`: gọi `GET https://api.crossref.org/works`, chỉ retry khi status code thuộc `{429, 503}`; dùng header `Retry-After` nếu server trả về, nếu không thì exponential backoff (`1s → 2s → 4s ...`); các lỗi khác raise ngay để không che giấu lỗi thật.
- `parse_crossref_payload()`: duyệt `message.items`, loại bỏ item không có DOI/title/abstract, chuẩn hóa HTML tag và khoảng trắng thừa trong text (`_clean_text`), chọn ngày xuất bản theo thứ tự ưu tiên `published → published-print → published-online → created` (`_format_date`).
- `fetch_source_records()`: ghi raw response gốc (không chỉnh sửa) vào `data/raw/crossref_response.json` trước, sau đó mới parse và ghi records chuẩn hóa vào `data/raw/crossref_records.json` — thứ tự này đảm bảo raw response luôn được lưu kể cả khi parse có lỗi.
- `load_raw_records()`: đọc lại snapshot JSON và ánh xạ về `PaperRecord`, dùng chung bởi `phase1.py` (tránh fetch lại API nếu đã có snapshot và không bật `refresh_source`), `corruption_flow.py` và `cleaning.repair_dataframe_from_snapshot()` (phục hồi dữ liệu sau corruption).

### Input, output và contract

| Thành phần                   | Mô tả                                                                                                                                                                                   |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                          | `Settings.source_query`, `source_filter`, `max_results` (từ `config.py`, không chứa secret)                                                                                    |
| Output                         | `data/raw/crossref_response.json` (raw payload), `data/raw/crossref_records.json` (24 `PaperRecord`)                                                                                |
| Module phụ thuộc             | `requests`, `src/core/config.py` (Settings)                                                                                                                                           |
| Module sử dụng output        | `src/ingestion/cleaning.py` (`build_clean_dataframe`, `repair_dataframe_from_snapshot`), `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/retrieval/qa.py` |
| Điều kiện lỗi cần xử lý | HTTP 429/503 (retry), thiếu DOI/title/abstract (loại bản ghi), payload không có`message.items` (trả về list rỗng thay vì crash)                                                |

### Cách xác minh

```bash
python script/run_phase1.py
```

- **Kết quả mong đợi:** `data/raw/crossref_response.json` và `data/raw/crossref_records.json` được tạo/refresh, không có exception khi fetch hoặc parse.
- **Kết quả thực tế:** Cả 2 file tồn tại trong `data/raw/`, `crossref_records.json` chứa 24 bản ghi hợp lệ, mỗi bản ghi có `paper_id` là DOI không rỗng và không trùng lặp.
- **Artifact/log:** `data/raw/crossref_records.json`, `data/raw/crossref_response.json`, `data/quality/quality_baseline.json` (`paper_id_duplicate_count: 0`, `title_valid: true`, `summary_valid: true`).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần một document identity ổn định cho từng bài báo, dùng xuyên suốt clean/embedding/evaluation/corruption/repair, để có thể đối chiếu cùng một bài báo qua nhiều lần chạy pipeline.
- **Các phương án đã cân nhắc:**
  1. *Phương án 1:* Sinh `paper_id` bằng hash tuần tự (index trong danh sách kết quả trả về từ API).
  2. *Phương án 2 (Được chọn):* Dùng trực tiếp DOI (`item["DOI"]`) làm `paper_id`.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** DOI là định danh duy nhất, ổn định và không đổi giữa các lần gọi API (khác với index theo vị trí, có thể thay đổi nếu Crossref trả kết quả theo thứ tự khác). Điều này đảm bảo `ground_truth_doc_ids` trong evaluation set (TV5) và các collection Chroma (TV4) luôn tham chiếu đúng cùng một bài báo giữa baseline, corrupted và repaired.
- **Bằng chứng quyết định phù hợp:** `data/quality/quality_baseline.json` cho thấy `paper_id_duplicate_count: 0` trên toàn bộ 24 bản ghi; corruption log (`data/results/corruption_log.json`) vẫn tham chiếu chính xác các DOI gốc (ví dụ `10.3390/buildings16132637`) khi mô phỏng lỗi trùng lặp, chứng tỏ `paper_id` giữ tính nhất quán xuyên suốt pipeline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Một số bản ghi trả về từ Crossref không có trường `abstract` hoặc `title` (ví dụ preprint mới index), nếu không lọc sẽ tạo ra `PaperRecord` với `summary=""`, làm hỏng bước tạo `text_for_embedding` phía sau.
- **Lệnh hoặc bước tái hiện:** Chạy `fetch_source_records(settings)` với query gốc trả về danh sách item không đồng nhất từ Crossref.
- **Nguyên nhân gốc:** Crossref API không đảm bảo mọi item đều có đủ `DOI`, `title`, `abstract` — một số record chỉ có metadata cơ bản.
- **Cách xử lý:** Thêm điều kiện lọc trong `parse_crossref_payload()`: `if not doi or not title or not abstract: continue`, đảm bảo chỉ record đủ 3 trường bắt buộc mới được đưa vào `data/raw/crossref_records.json`.
- **Cách xác minh sau khi sửa:** Toàn bộ 24 bản ghi trong `crossref_records.json` đều có `paper_id`, `title`, `summary` không rỗng; `data/quality/quality_baseline.json` xác nhận `title_empty_count: 0`, `summary_short_count: 0`, `summary_valid: true`.
- **Điều học được:** Không nên giả định API bên ngoài luôn trả về dữ liệu đầy đủ — bước lọc dữ liệu không hợp lệ phải nằm ngay tại lớp ingestion (raw lineage), trước khi dữ liệu đi vào cleaning, để các bước sau không phải tự phòng thủ lại cùng một loại lỗi.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** `fetch_source_records()` gọi Crossref API (có retry cho 429/503) ➔ lưu payload thô vào `data/raw/crossref_response.json` ➔ `parse_crossref_payload()` chuẩn hóa thành `PaperRecord` (DOI làm `paper_id`) lưu vào `data/raw/crossref_records.json` ➔ TV3 dùng `build_clean_dataframe()` để lọc, chuẩn hóa `title/summary/authors`, tính `age_days` và tạo `text_for_embedding`, ghi vào `data/clean/` ➔ TV4 dùng `LocalEmbeddingIndex` mã hóa bằng `sentence-transformers/all-MiniLM-L6-v2` và nạp vào ChromaDB collection tương ứng (baseline/corrupted/repaired).
2. **Evaluation set và ground-truth IDs:** TV5 sinh câu hỏi trong `build_test_set()` từ `data/clean/papers_clean.csv`, gắn `ground_truth_doc_ids` chính là các DOI (`paper_id`) mà tôi đã trích xuất ở bước ingestion — vì vậy tính ổn định của DOI ảnh hưởng trực tiếp đến độ chính xác của phép đo `retrieval_hit_rate`.
3. **Quality checks vs Freshness monitoring:** Quality checks (`data/quality/quality_baseline.json`) đo tính toàn vẹn của dữ liệu (null/duplicate/short trên `paper_id`, `title`, `summary`); Freshness monitoring đo `age_days` tính từ trường `published` mà tôi đã parse từ Crossref, so với ngưỡng tuổi cho phép.
4. **Vì sao raw snapshot quan trọng cho Repair:** `data/raw/crossref_records.json` là nguồn duy nhất không bị corrupt — khi TV3 chạy `repair_dataframe_from_snapshot()`, hàm này gọi lại `load_raw_records()` mà tôi viết để đọc đúng 24 bản ghi gốc và build lại `clean_dataframe` từ đầu, thay vì cố "vá" dữ liệu đã bị lỗi.
5. **Repair được xem là thành công khi:** Dữ liệu sau repair khớp lại với `data/raw/crossref_records.json` gốc (không còn `duplicated_paper_ids`, `blank_summary`, `stale_date` như trong `corruption_log.json`), Quality Gate và Freshness quay lại `PASSED`/`FRESH`, và các metric RAG (`retrieval_hit_rate`, `mean_token_f1`) khôi phục về đúng giá trị baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal                          | Baseline |                                               Corrupted |                 Repaired | Nhận xét của cá nhân                                                                                                                            |
| -------------------------------------- | -------: | ------------------------------------------------------: | -----------------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Số raw records lấy được           |       24 |                                24 (dùng lại snapshot) | 24 (dùng lại snapshot) | `max_results=24` theo cấu hình; toàn bộ 3 trạng thái đều dựa trên cùng 1 lần fetch từ Crossref, đảm bảo phép so sánh công bằng |
| `paper_id_duplicate_count` (quality) |        0 | > 0 (do corruption cố ý tạo`duplicated_paper_ids`) |                        0 | Corruption chỉ tác động ở tầng dữ liệu clean/corrupted, không ảnh hưởng snapshot raw gốc mà tôi lưu trữ                             |
| `retrieval_hit_rate`                 |  100.00% |                                                  66.67% |                  100.00% | Vì`paper_id` (DOI) ổn định xuyên suốt, repair từ raw snapshot khôi phục đúng 100% hit rate                                              |

### Kết luận từ số liệu

1. **[Raw snapshot được giữ nguyên, không bị corrupt]** ➔ **[Repair đọc lại đúng 24 bản ghi gốc qua `load_raw_records()`]** ➔ **[Quality PASSED, Freshness FRESH, retrieval_hit_rate khôi phục 100%]**: việc tách riêng raw lineage (`data/raw/`) khỏi clean dataset (`data/clean/`) là điều kiện tiên quyết để pipeline có khả năng tự phục hồi hoàn toàn sau corruption.
2. **[DOI làm `paper_id` ổn định]** ➔ **[`ground_truth_doc_ids` trong test set và collection Chroma luôn tham chiếu đúng bài báo]** ➔ **[So sánh baseline/corrupted/repaired có ý nghĩa vì cùng một tập ID xuyên suốt]**.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Lớp ingestion phải là nơi lọc dữ liệu không hợp lệ đầu tiên (thiếu DOI/title/abstract) — dồn việc này xuống các bước sau sẽ khiến lỗi lan rộng khó truy vết.
2. **Về Raw Lineage:** Lưu raw response gốc (chưa qua parse) là bước rẻ nhưng quan trọng — nó cho phép debug lại logic parse mà không cần gọi lại API bên ngoài.
3. **Về ảnh hưởng tới RAG:** Một document identity (`paper_id`) không ổn định sẽ làm hỏng toàn bộ chuỗi đánh giá phía sau (test set, retrieval, quality), dù bản thân nội dung dữ liệu không có lỗi gì.

### Nếu có thêm thời gian

Bổ sung retry/backoff riêng cho lỗi timeout mạng (không chỉ 429/503) và log số lần retry thực tế vào một file riêng trong `data/raw/` để quan sát độ ổn định của Crossref API qua nhiều lần chạy.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [X] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [X] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [X] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [X] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [X] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [X] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Điền họ tên]
**Ngày xác nhận:** 2026-08-06
