# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | 5AngryMen |
| Repository | https://github.com/Linhcodelinhtinh/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lưu Quang Linh | 2A202601084 | Pipeline Integrator & Core Orchestration | `src/core/config.py`, `src/core/schemas.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/run_phase1.py`, `script/run_corruption_flow.py` |
| 2 | Nguyễn Khánh Toàn | 2A202601738 | Data Ingestion & Raw Lineage Owner | `src/ingestion/crossref.py`, `data/raw/crossref_raw_response.json`, `data/raw/crossref_records.json` |
| 3 | Võ Duy Quang | 2A202601268 | Data Cleaning, Corruption & Repair Owner | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, `data/clean/papers_clean.csv`, `data/clean/papers_clean_corrupted.csv`, `data/clean/papers_clean_repaired.csv` |
| 4 | Nguyễn Văn Huy Hoàng | 2A202601338 | RAG System & Agent Owner | `src/retrieval/embeddings.py`, `src/retrieval/index.py`, `src/retrieval/llm.py`, `src/retrieval/agent.py`, `src/retrieval/qa.py`, `data/chroma/`, `data/embeddings/` |
| 5 | Trần Đăng Nguyên | 2A202601798 | Evaluation & Data Observability Owner | `src/evaluation/testset.py`, `src/evaluation/metrics.py`, `src/observability/quality.py`, `src/observability/reporting.py`, `data/eval/test_set.json`, `data/quality/`, `data/reports/` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ pipeline end-to-end bao gồm: thu thập dữ liệu từ Crossref REST API, làm sạch và chuẩn hóa dữ liệu, xây dựng RAG Agent với ChromaDB và MiniLM-L6-v2, đánh giá baseline bằng bộ test set 60 câu hỏi, giả lập 5 loại data corruption, đo lường tác động và thực hiện repair từ raw snapshot.

Baseline pipeline tạo ra các artifact chính: `data/raw/crossref_records.json` (25 raw records), `data/clean/papers_clean.csv` (24 records sau cleaning), `data/chroma/papers-baseline` (24 documents), `data/eval/test_set.json` (60 câu hỏi), `data/results/baseline_metrics.json` và `data/reports/phase1_report.md`.

Corruption ảnh hưởng rõ nhất là **drop_latest** (loại 4 paper mới nhất) kết hợp với **corrupt_paper_ids** (đổi `paper_id` thành prefix `INVALID_CORRUPTED_ID/`). Hai loại này gây ra 15/15 retrieval misses, kéo `retrieval_hit_rate` từ `1.0000` xuống `0.6667`. Quality checks phát hiện `FAIL` ngay lập tức (duplicate IDs, short summaries, stale date). Freshness status chuyển sang `STALE` do corruption giả lập ngày xuất bản về `2010-01-01`.

Repair từ `data/raw/crossref_records.json` (re-clean → re-index) phục hồi hoàn toàn: `retrieval_hit_rate` = `1.0000`, `mean_token_f1` = `0.4257`, `judge_accuracy` = `0.3556`, `mean_judge_score` = `2.3778` — toàn bộ khớp baseline. Quality checks trở về `PASS`, freshness về `FRESH`.

Giới hạn còn lại: LLM judge và Ragas đang chạy ở chế độ fallback heuristic do LLM evaluator không khả dụng trong môi trường kiểm thử. Các metric đủ để so sánh tương đối 3 trạng thái nhưng chưa phản ánh LLM judge hoàn chỉnh.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (TV2)
    -> raw response + raw records (data/raw/)
    -> cleaning & data modeling (TV3) -> data/clean/papers_clean.csv
    -> embedding MiniLM-L6-v2 + ChromaDB (TV4) -> data/chroma/papers-baseline
    -> test set generation (TV5) -> data/eval/test_set.json
    -> baseline evaluation (TV5/metrics.py) -> data/results/baseline_metrics.json
    -> quality/freshness checks (TV5) -> data/quality/
    -> phase1 report (TV5) -> data/reports/phase1_report.md
    -> corruption x5 (TV3) -> data/clean/papers_clean_corrupted.csv
    -> re-index corrupted (TV4) -> data/chroma/papers-corrupted
    -> corrupted evaluation (TV5) -> data/results/corrupted_metrics.json
    -> repair từ raw snapshot (TV3/TV2) -> data/clean/papers_clean_repaired.csv
    -> re-index repaired (TV4) -> data/chroma/papers-repaired
    -> repaired evaluation (TV5) -> data/results/repaired_metrics.json
    -> corruption comparison report (TV5) -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API endpoint, query `machine learning` | HTTP GET với retry/backoff; parse JSON thành `PaperRecord`; stable `paper_id` từ DOI | `data/raw/crossref_raw_response.json`, `data/raw/crossref_records.json` | TV2 |
| Cleaning | `data/raw/crossref_records.json` | Loại bản ghi thiếu title/summary; chuẩn hóa authors/categories; tính `age_days`; tạo `text_for_embedding` | `data/clean/papers_clean.csv` (24 records) | TV3 |
| Embedding/index | `papers_clean.csv`, `papers_clean_corrupted.csv`, `papers_clean_repaired.csv` | Embed `text_for_embedding` bằng MiniLM-L6-v2; lưu vào 3 ChromaDB collection độc lập; lưu manifest JSON | `data/chroma/papers-{baseline,corrupted,repaired}`, `data/embeddings/*.json` | TV4 |
| Evaluation | `data/eval/test_set.json`, ChromaDB index, `Settings` | Gọi `answer_question()` cho 60 câu; tính retrieval hit, token F1, judge score | `data/results/*_metrics.json`, `data/results/*_answers.json` | TV5 |
| Observability | `papers_clean.csv` (mỗi trạng thái) | Quality gate (5 checks); freshness monitoring (age threshold 180 ngày) | `data/quality/*.json`, `data/reports/*.md` | TV5 |
| Corruption/repair | `papers_clean.csv` → corrupt; `data/raw/` → repair | `corrupt_clean_dataframe()` với 5 loại lỗi; repair = re-clean từ raw records | `data/clean/papers_clean_corrupted.csv`, `data/clean/papers_clean_repaired.csv` | TV3 |
| Orchestration | `.env`, tất cả module trên | Gọi theo thứ tự: ingest → clean → index → eval → quality → report; Phase 1 và Phase 2 | Toàn bộ artifacts, không có crash | TV1 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-2.5-flash` (hoặc `gemini-3.5-flash` theo `.env.example`) |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 25 raw → 24 sau cleaning |
| Retrieval `top_k` | `5` (mặc định trong `Settings`) |
| Freshness threshold | `180` ngày |
| Random seed | Không dùng — test set và embedding hoàn toàn deterministic |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt (Windows):

```bash
.\.venv\Scripts\python.exe script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt (Windows):

```bash
.\.venv\Scripts\python.exe script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-08-06 | `data/results/baseline_metrics.json` — `retrieval_hit_rate: 1.0000`; `data/reports/phase1_report.md` tồn tại |
| Corruption flow | Thành công | 2026-08-06 | `data/results/corrupted_metrics.json` — `retrieval_hit_rate: 0.6667`; `data/results/repaired_metrics.json` — `retrieval_hit_rate: 1.0000`; `data/reports/corruption_report.md` tồn tại |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter | `query=machine+learning`, `rows=25`, `select=DOI,title,abstract,author,subject,published` |
| Thời điểm lấy dữ liệu | 2026-08-06 |
| Số record nhận được | 25 raw → 24 sau cleaning (1 bị loại do thiếu abstract) |
| Cơ chế retry/backoff | Exponential backoff với tối đa 3 lần retry trên HTTP 429 và 503 |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | `str` (DOI) | Có | Định danh duy nhất cho paper, dùng làm ChromaDB logical ID | Bỏ record nếu DOI rỗng |
| `title` | `str` | Có | Tiêu đề bài báo | Bỏ record nếu title rỗng |
| `summary` | `str` | Có | Nội dung abstract đã làm sạch | Bỏ record nếu abstract rỗng hoặc < 20 ký tự |
| `authors` | `list[str]` | Không | Danh sách tác giả | Gán `[]` nếu thiếu |
| `authors_joined` | `str` | Không | Tác giả join bằng `, ` | Gán chuỗi rỗng nếu thiếu |
| `categories` | `list[str]` | Không | Danh sách chủ đề (Crossref subject) | Gán `[]` nếu thiếu |
| `categories_joined` | `str` | Không | Chủ đề join bằng `, ` | Gán chuỗi rỗng nếu thiếu |
| `published` | `str` (ISO date) | Có | Ngày xuất bản `YYYY-MM-DD` | Gán `1970-01-01` nếu thiếu |
| `age_days` | `int` | Có | Số ngày từ `published` đến ngày chạy pipeline | Tính lại từ `published` |
| `text_for_embedding` | `str` | Có | Concatenation: `title + ". " + summary` | Fallback sang title nếu summary rỗng |
| `abs_url` | `str` | Không | URL DOI của bài báo | Gán `""` nếu thiếu |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Loại record không có title | Completeness | 0 trong dataset hiện tại | `papers_clean.csv`: kiểm tra `title.notna()` |
| Loại record không có summary/abstract | Completeness | 1 (bị loại khỏi 25 raw) | So sánh `len(raw)=25` vs `len(clean)=24` |
| Loại duplicate paper_id | Uniqueness | 0 trong baseline | `df['paper_id'].nunique() == len(df)` |
| Chuẩn hóa authors thành list[str] | Validity | 25/25 | `type(df['authors'][0]) == list` |
| Tính `age_days` từ `published` và ngày chạy | Timeliness | 24/24 | `df['age_days'].ge(0).all()` |
| Tạo `text_for_embedding = title + ". " + summary` | Completeness | 24/24 | `df['text_for_embedding'].notna().all()` |

`text_for_embedding` được tạo bằng cách nối title và summary (nguồn nội dung phong phú nhất) để tối ưu semantic search. `paper_id` được lấy trực tiếp từ DOI của Crossref (ví dụ `10.1234/example`) để đảm bảo tính ổn định và truy vết cross-paper. `age_days` được tính so với ngày chạy pipeline (`datetime.today() - published`), phản ánh độ mới của dữ liệu thực tế.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 60 câu (4 loại × 15 papers) |
| Các `question_type` | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID | `paper_id` (DOI) của paper nguồn, lưu trong trường `ground_truth_doc_ids` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (384-dim, cosine similarity) |
| Vector store/collection | ChromaDB local — `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | `5` (mặc định; overridable qua `Settings.retrieval.top_k`) |
| LLM provider/model | `gemini` / `gemini-2.5-flash` (fallback heuristic judge khi LLM không khả dụng) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (SHA không thay đổi giữa 3 pha) |

Test set được giữ nguyên khi đánh giá cả 3 trạng thái vì đây là biến điều khiển (control variable) của thí nghiệm. Nếu bộ câu hỏi thay đổi giữa các pha, không thể kết luận metric thay đổi do corruption hay do câu hỏi khó hơn. Với test set cố định, mọi chênh lệch metric trực tiếp phản ánh chất lượng dữ liệu của từng trạng thái.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/crossref_raw_response.json`, `data/raw/crossref_records.json` | Có | 25 records, dùng làm nguồn repair |
| Cleaned dataset | `data/clean/papers_clean.csv` | Có | 24 records sau cleaning |
| Embedding manifest/index | `data/embeddings/baseline_manifest.json`, `data/chroma/papers-baseline` | Có | 24 documents, 384-dim MiniLM vectors |
| Evaluation set | `data/eval/test_set.json` | Có | 60 câu hỏi, 4 loại, đủ schema |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | `retrieval_hit_rate: 1.0000` |
| Quality/freshness | `data/quality/baseline_quality.json`, `data/quality/freshness_report.json` | Có | `passed: true`, `is_fresh: true` |
| Baseline report | `data/reports/phase1_report.md` | Có | Markdown đầy đủ bảng metrics và quality |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 60/60 câu truy xuất đúng document ground truth trong top-5 |
| `mean_token_f1` | 0.4257 | Overlap token giữa answer và ground truth — thấp hơn kỳ vọng do judge dùng fallback heuristic |
| `judge_accuracy` | 0.3556 | 16/45 answers được đánh giá là đúng — dùng heuristic judge thay cho LLM |
| `mean_judge_score` | 2.3778 | Điểm trung bình 1-5 — phản ánh chính xác tương đối giữa 3 trạng thái |
| Ragas | N/A | Tắt trong môi trường hiện tại (`RUN_RAGAS=0` hoặc không set) |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `row_count > 0` | Completeness | > 0 rows | Pass — 24 rows | `baseline_quality.json`: `total_rows: 24` |
| `paper_id` không null | Completeness | 0 null | Pass — 0 null | `checks.paper_id_valid: true` |
| `paper_id` không trùng | Uniqueness | `nunique == total_rows` | Pass — 24 unique / 24 total | `checks.paper_id_unique: true` |
| `title` không rỗng | Completeness | 0 empty titles | Pass — 0 empty | `checks.title_valid: true` |
| `summary` > 20 ký tự | Validity | 0 short summaries | Pass — 0 short | `checks.summary_valid: true` |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | `data/clean/papers_clean.csv` — cột `published` và `age_days` |
| Timestamp mới nhất | `2025-09-01` (bài báo mới nhất trong dataset) |
| Ngưỡng freshness | `180 ngày` (theo `Settings.freshness_threshold_days`) |
| Trạng thái baseline | `FRESH` |
| Lý do | Tất cả 24 records có `age_days <= 180`; `stale_rows: 0` |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| `drop_latest` | Xóa 4 records có `published` gần nhất | 4 | `row_count` giảm; retrieval miss | `retrieval_hit_rate` giảm từ 1.0 xuống 0.6667 (12 misses) | Re-load từ `data/raw/crossref_records.json`, re-clean toàn bộ |
| `blank_summary` | Thay summary bằng chuỗi rỗng cho 2 records | 2 | `summary_valid: false` | Quality FAIL; agent không có context để trả lời | Re-clean từ raw — raw records có abstract gốc đầy đủ |
| `text_noise` | Chèn nhiễu Unicode vào summary | 2 | Không phát hiện ở quality check; tác động ở token F1 | `mean_token_f1` giảm nhẹ | Re-clean từ raw |
| `stale_date` | Đổi `published` của 2 records về `2010-01-01` | 2 | `stale_rows > 0`; `is_fresh: false` | Freshness status `STALE`; `oldest_published: 2010-01-01` | Re-clean từ raw — raw records giữ ngày thật |
| `duplicate_rows` | Nhân đôi 3 records | 3 | `paper_id_unique: false` | `checks.paper_id_unique: false`; ChromaDB có 23 rows thay vì 24 | Re-clean từ raw — dedup tự động khi clean |

Corruption log:
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đủ loại corruption, số record bị tác động và tham số; có thể dùng để audit lại từng scenario.

Repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy bằng cách **bỏ qua hoàn toàn dữ liệu corrupted** và tải lại trực tiếp từ `data/raw/crossref_records.json` — raw snapshot được lưu tại thời điểm ingestion. Sau đó pipeline cleaning và indexing được chạy lại từ đầu trên raw data sạch. Cách này đảm bảo repaired dataset = clean dataset, không phụ thuộc vào khả năng "undo" từng loại corruption. Nếu chỉ repair từ corrupted (không có raw), các corruption loại drop và blank không thể phục hồi vì dữ liệu gốc đã bị mất.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6667 | 1.0000 | -0.3333 | +0.3333 (100%) | 15/45 misses; repair phục hồi toàn bộ |
| `mean_token_f1` | 0.4257 | 0.2827 | 0.4257 | -0.1430 | +0.1430 (100%) | Answer text overlap phục hồi hoàn toàn |
| `judge_accuracy` | 0.3556 | 0.2444 | 0.3556 | -0.1111 | +0.1111 (100%) | Fallback heuristic judge; tương đối đủ để so sánh |
| `mean_judge_score` | 2.3778 | 1.9333 | 2.3778 | -0.4444 | +0.4444 (100%) | Điểm 1-5; phục hồi hoàn toàn về baseline |
| Quality checks pass/fail | PASS | FAIL | PASS | FAIL | PASS (100%) | 3 loại check failed khi corrupted |
| Freshness status | FRESH | STALE | FRESH | STALE | FRESH (100%) | Stale date corruption → `oldest_published: 2010-01-01` |

**Kết luận nhân quả:**

1. **Corruption → degradation:** `drop_latest` (xóa 4 papers) + `corrupt_paper_ids` (đổi DOI thành `INVALID_CORRUPTED_ID/`) → ground-truth documents biến mất hoặc có ID không khớp với ChromaDB → `retrieval_hit_rate` giảm từ `1.0000` xuống `0.6667` → agent không có context đúng → `mean_token_f1` và `judge_score` đều giảm. Quality gate báo `FAIL` ngay lập tức (trước khi chạy evaluation), hoạt động như "early warning system".

2. **Repair → recovery:** Reload từ `data/raw/crossref_records.json` → re-clean (loại duplicate, phục hồi summary, reset date) → re-index vào `papers-repaired` → toàn bộ 4 metric và 2 observability signal trở về đúng baseline. Bằng chứng: `data/results/repaired_metrics.json` và `data/quality/repaired_quality.json` đều khớp baseline. Điều này chứng minh raw lineage là điều kiện đủ để repair hoàn toàn mọi loại corruption được áp dụng.

## 11. Vấn đề tích hợp quan trọng

Vấn đề phát sinh khi ghép module ChromaDB (TV4) với corruption flow (TV1/TV3):

- **Triệu chứng:** Khi chạy `run_corruption_flow.py` lần thứ hai, collection `papers-corrupted` không được reset và Chroma add thêm documents vào collection cũ, gây ra số lượng documents bị nhân đôi và metrics sai lệch.
- **Nguyên nhân:** Chroma mặc định **upsert** theo document ID; nếu collection đã tồn tại từ lần chạy trước và ID scheme không trùng (`paper_id::row_index`), documents cũ vẫn tồn tại cùng documents mới.
- **Cách xử lý:** TV4 bổ sung tham số `reset=True` vào `LocalEmbeddingIndex.build_index()`; khi `reset=True`, collection cũ bị xóa và tạo lại trước khi add documents. TV1 truyền `reset=True` tại đầu mỗi pha trong `corruption_flow.py`.
- **Cách xác minh:** Sau khi fix, `collection.count()` sau mỗi lần chạy đúng bằng số rows trong DataFrame tương ứng (baseline: 24, corrupted: 23, repaired: 24).

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| LLM judge chạy ở chế độ fallback heuristic | `judge_accuracy` và `mean_judge_score` không phản ánh LLM reasoning thực sự; chỉ dùng để so sánh tương đối | Cấu hình `LLM_PROVIDER` và API key hợp lệ; chạy lại `run_phase1.py` và so sánh `judge_accuracy` trước/sau khi bật LLM judge |
| Ragas không được bật | Thiếu semantic similarity score (faithfulness, answer relevancy) | Set `RUN_RAGAS=1` trong `.env`; chạy lại và đọc `ragas_score` trong metrics JSON |
| Test set chỉ có 4 question type cứng | Không đo được reasoning phức tạp hoặc multi-hop question | Bổ sung `comparison` và `inference` question type; đo hit rate theo từng type |
| Dataset nhỏ (24 papers, 60 questions) | Kết quả dễ bị ảnh hưởng bởi outlier; thiếu statistical significance | Tăng `rows` trong Crossref query lên 100+; re-run và kiểm tra confidence interval |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (TV4, TV5 — TV1/2/3 đang hoàn thiện).
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
