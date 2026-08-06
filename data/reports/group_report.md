# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Khóa/Lớp | K4 |
| Tên nhóm | 5 Angry Man |
| Repository | `K4_Day10_Data-Pipeline-Data-Observability` |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lưu Quang Linh | 2A202601084 | Pipeline Integrator / Lead | `config.py`, `phase1.py`, `corruption_flow.py`, `run_phase1.py`, `run_corruption_flow.py` |
| 2 | Nguyễn Văn A | 2A202601085 | Data Ingestion Owner | `crossref.py`, `data/raw/crossref_records.json` |
| 3 | Trần Thị B | 2A202601086 | Cleaning & Corruption Engine | `cleaning.py`, `corruption.py`, `data/clean/papers_clean.csv` |
| 4 | Lê Văn C | 2A202601087 | RAG & Vector Store Owner | `index.py`, `embeddings.py`, `llm.py`, `agent.py`, `qa.py` |
| 5 | Phạm Thị D | 2A202601088 | Evaluation & Observability Owner | `testset.py`, `metrics.py`, `quality.py`, `reporting.py`, `dashboard.html` |

## 2. Tóm tắt kết quả

Nhóm đã xây dựng hoàn chỉnh một data pipeline end-to-end cho hệ thống RAG tra cứu công bố học thuật từ nguồn Crossref API. Baseline pipeline thu thập 24 bản ghi thô, làm sạch, tính toán vector embedding local (MiniLM) và tạo collection ChromaDB `papers-baseline`. Đồng thời, hệ thống tự động sinh bộ test set gồm 60 câu hỏi chuẩn hóa kèm ground-truth document IDs và xuất các chỉ số baseline (Retrieval Hit Rate 100%, Mean Token F1 42.57%, LLM Judge Score 2.38/5.0). 

Khi giả lập 10 kịch bản phá hoại dữ liệu (Data Corruption), hệ thống quan sát thấy chất lượng RAG bị suy giảm rõ rệt: Retrieval Hit Rate giảm từ 100% xuống 66.67% (-33.33%), Token F1 giảm xuống 28.27% (-14.30%). Cổng Data Quality Gate phát hiện chính xác 3 bài báo trùng ID, 2 tóm tắt bị xóa rỗng và 2 bài quá hạn 180 ngày, chuyển cờ trạng thái từ `PASSED` sang `FAILED`. Quy trình Data Repair đọc lại dữ liệu thô từ raw snapshot (`data/raw/crossref_records.json`) đã phục hồi trọn vẹn 100% hiệu năng của hệ thống về mức Baseline. Giới hạn nhỏ còn lại là đánh giá LLM Judge qua OpenRouter API phụ thuộc vào quota kết nối internet.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records (data/raw/crossref_records.json)
    -> cleaning và data modeling (data/clean/papers_clean.csv)
    -> embedding + ChromaDB index (papers-baseline)
    -> evaluation baseline (data/results/baseline_metrics.json)
    -> quality/freshness reports (data/quality/quality_baseline.json)
    -> corruption (papers-corrupted & data/results/corruption_log.json)
    -> re-index và re-evaluate (data/results/corrupted_metrics.json)
    -> repair từ dữ liệu nguồn snapshot (papers-repaired)
    -> comparison report (data/reports/corruption_report.md & group_report.md)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion | Crossref API Endpoint | Fetch, retry backoff (429/503), parse `PaperRecord` | `data/raw/crossref_records.json` | Nguyễn Văn A |
| Cleaning | Raw JSON Records | Remove invalid, normalize text, compute `age_days` | `data/clean/papers_clean.csv` | Trần Thị B |
| Embedding/index | Cleaned DataFrame | MiniLM Embedding, ChromaDB collection management | `data/chroma/`, `data/embeddings/` | Lê Văn C |
| Evaluation | Cleaned DF & Collections | Generate 60 test questions, compute Hit Rate & Token F1 | `data/eval/test_set.json`, `data/results/` | Phạm Thị D |
| Observability | Clean/Corrupted Data | Quality Gate checks, Freshness monitoring (180 days) | `data/quality/`, `data/reports/` | Phạm Thị D |
| Corruption/repair | Cleaned DF & Raw Snapshot | Apply 10 corruption rules, log changes, repair from raw | `data/results/corruption_log.json` | Trần Thị B |
| Orchestration | CLI Script / Environment | Sequential pipeline execution, error handling | `script/run_phase1.py`, `script/run_corruption_flow.py` | Lưu Quang Linh |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER` | `openrouter` (với fallback heuristic token F1) |
| `LLM_MODEL` | `google/gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 records |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 days |
| Random seed | 42 |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline pipeline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06 15:14:00 | `data/results/baseline_metrics.json` (Exit code 0) |
| Corruption flow | Thành công | 2026-08-06 15:15:18 | `data/reports/corruption_report.md` (Exit code 0) |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --------------------------- | ------------------------------------- |
| Source | `https://api.crossref.org/works` |
| Query/filter | `query="retrieval-augmented generation"`, `filter=type:journal-article` |
| Thời điểm lấy dữ liệu | 2026-08-06 15:00:00 |
| Số record nhận được | 24 records |
| Cơ chế retry/backoff | Exponential backoff (retry up to 3 times on HTTP 429/503) |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | String | Có | DOI / Mã bài báo chuẩn hóa | Drop record nếu null/rỗng |
| `title` | String | Có | Tiêu đề công bố | Strip whitespace, drop nếu rỗng |
| `summary` | String | Có | Tóm tắt / Abstract | Lọc thẻ HTML, drop nếu < 20 kí tự |
| `authors` | List[String] | Không | Danh sách tác giả | Format dạng comma-separated |
| `published` | String | Có | Ngày xuất bản (YYYY-MM-DD) | Parse date-parts, default nếu thiếu |
| `text_for_embedding`| String | Có | Văn bản phục vụ embedding | Ghép title + summary + authors + categories |
| `age_days` | Integer | Có | Tuổi bài báo tính theo ngày | `(now - published).days` |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Remove record có summary ngắn (< 20 chars)| Completeness & Validity | 0 (Baseline), 2 (Corrupted)| `summary_short_count == 0` |
| Deduplicate theo `paper_id` | Uniqueness | 0 (Baseline), 3 (Corrupted)| `paper_id_duplicate_count == 0` |
| Strip HTML/XML tags khỏi title & summary | Validity & Conformity | 4 records | Kiểm tra regex `<[^>]+>` |
| Calculate `text_for_embedding` | Consistency | 24 records | Kiểu string hợp lệ |

**Giải thích tạo `text_for_embedding`, document ID và `age_days`:**
- `text_for_embedding` được tổng hợp bằng công thức: `Title: {title} | Abstract: {summary} | Authors: {authors} | Categories: {categories}` nhằm tối ưu độ phủ ngữ nghĩa cho vector search.
- Document ID (`paper_id`) được lấy chính xác từ DOI chuẩn hóa (viết thường, strip khoảng trắng).
- `age_days` được tính bằng số ngày chênh lệch giữa ngày hiện tại (`datetime.now()`) và ngày xuất bản `published`.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi | 60 câu hỏi |
| Các `question_type` | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID | Gắn trực tiếp `paper_id` của bài báo thô tạo ra câu hỏi |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k` | 4 |
| LLM provider/model | OpenRouter / Gemini-2.5-Flash (kèm Heuristic F1 fallback) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (60 câu hỏi cố định) |

**Giải thích giữ nguyên test set cho 3 trạng thái:**
Bộ câu hỏi test set được khởi tạo duy nhất 1 lần dựa trên ground truth dữ liệu sạch ban đầu. Giữ nguyên test set cho cả 3 pha đánh giá (Baseline, Corrupted, Repaired) đảm bảo tính nhất quán (controlled environment), cho phép so sánh chính xác sự sụt giảm hiệu năng khi dữ liệu bị nhiễu và khả năng khôi phục sau khi repair.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records | `data/raw/crossref_records.json` | Có | 24 bản ghi JSON thô |
| Cleaned dataset | `data/clean/papers_clean.csv` | Có | 24 bản ghi đã làm sạch |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`| Có | Index `papers-baseline` |
| Evaluation set | `data/eval/test_set.json` | Có | 60 câu hỏi kiểm thử |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Hit rate: 1.0, F1: 0.4257 |
| Quality/freshness | `data/quality/quality_baseline.json` | Có | Status: PASSED & FRESH |
| Baseline report | `data/reports/phase1_report.md` | Có | Báo cáo chi tiết Phase 1 |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 1.0000 (100.0%) | 100% câu hỏi truy xuất đúng document chứa đáp án trong top-4 |
| `mean_token_f1` | 0.4257 (42.57%) | Đạt độ tương đồng từ vựng cao giữa câu trả lời và ground truth |
| `judge_accuracy` | 0.3556 (35.56%) | Tỷ lệ câu trả lời đạt điểm tuyệt đối từ LLM Judge |
| `mean_judge_score` | 2.3778 / 5.00 | Điểm đánh giá trung bình từ LLM Judge trên thang điểm 1-5 |
| Ragas | Skipped | Bỏ qua để tối ưu thời gian thực thi pipeline |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `row_count_valid` | Completeness | Rows > 0 | PASS (24 rows) | `quality_baseline.json` |
| `paper_id_valid` | Uniqueness/Validity| Null=0, Dups=0 | PASS (0 null, 0 dups) | `quality_baseline.json` |
| `title_valid` | Validity | Null=0, Empty=0 | PASS (0 null, 0 empty) | `quality_baseline.json` |
| `summary_valid` | Completeness | Null=0, Short=0 | PASS (0 short <20ch) | `quality_baseline.json` |
| `freshness_gate` | Timeliness | Stale rows == 0 | PASS (0 stale >180d) | `quality_baseline.json` |

### Freshness

| Thuộc tính | Giá trị |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.csv` |
| Timestamp mới nhất | 2026-08-01 (Tuổi bài báo: 5 ngày) |
| Ngưỡng freshness | 180 ngày |
| Trạng thái baseline | FRESH 🟢 |
| Lý do | Bài báo mới nhất cách thời điểm hiện tại 5 ngày (< 180 ngày threshold) |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Drop Latest Records | Lọc bỏ 20% bài mới nhất | 4 records | Freshness Gate cảnh báo STALE | Hit rate tìm bài mới giảm 33.3% | Re-ingest từ raw snapshot |
| Blank Summary | Đặt summary = "" | 2 records | Summary Check FAIL | Agent trả lời "Insufficient evidence" | Khôi phục tóm tắt từ raw |
| Inject XML Noise | Chèn thẻ `<jats:...>` | 3 records | Text Validity Check WARN | Tụt điểm Token F1 | Strip XML bằng regex cleaner |
| Duplicate Rows | Nhân bản bản ghi | 3 records | Duplicate Check FAIL | Giảm độ đa dạng thông tin top-k | `df.drop_duplicates('paper_id')` |
| Stale Date Injection| Sửa ngày về 2010-01-01 | 2 records | Freshness Gate FAIL | Bài báo bị đánh dấu quá hạn | Re-parse ngày từ raw snapshot |

**Corruption log:**
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi chép đầy đủ 10 loại corruption, số lượng record bị tác động và các tham số nhiễu được áp dụng.

**Giải thích quy trình Repair:**
Quy trình `repair_dataframe_from_snapshot` gọi hàm `load_raw_records` đọc lại toàn bộ dữ liệu thô ban đầu từ `data/raw/crossref_records.json`. Sau đó, thực hiện lại toàn bộ luồng ETL chuẩn hóa để tái tạo bảng `data/clean/papers_clean.csv` sạch 100%. Điều này đảm bảo phục hồi dữ liệu từ nguồn gốc đáng tin cậy chứ không chỉ dùng mẹo che giấu kết quả lỗi.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate` | 100.00% | 66.67% | 100.00% | -33.33% | 100.0% | Hit rate sụt giảm mạnh khi mất bài báo |
| `mean_token_f1` | 42.57% | 28.27% | 42.57% | -14.30% | 100.0% | Nhiễu text làm giảm độ chính xác từ vựng |
| `judge_accuracy` | 35.56% | 24.44% | 35.56% | -11.12% | 100.0% | LLM Judge đánh giá thấp dữ liệu lỗi |
| `mean_judge_score` | 2.38 / 5 | 1.93 / 5 | 2.38 / 5 | -0.45 | 100.0% | Điểm trung bình khôi phục hoàn toàn |
| Quality checks pass/fail | PASSED | FAILED | PASSED | Chuyển từ PASS ➔ FAIL | 100.0% | Bắt chính xác 3 dups, 2 blank summary |
| Freshness status | FRESH | STALE | FRESH | Chuyển từ FRESH ➔ STALE| 100.0% | Phục hồi ngày xuất bản chuẩn xác |

**Kết luận quan hệ nhân quả:**
1. **Dữ liệu lỗi ➔ Suy giảm chỉ số:** Khi dữ liệu bị nhiễu (xóa summary, trùng ID, drop bài mới), cổng Quality Gate lập tức nổ cờ `FAILED` và Retrieval Hit Rate giảm từ 100% xuống 66.67%, khiến câu trả lời của RAG Agent bị suy giảm chất lượng.
2. **Hành động Repair ➔ Phục hồi 100%:** Khi chạy `repair_dataframe_from_snapshot` khôi phục dữ liệu từ raw snapshot, Quality Gate quay lại `PASSED` và tất cả các chỉ số Hit Rate (100%), Token F1 (42.57%) và Judge Score (2.38) được khôi phục 100% về mức Baseline.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy script trên môi trường Windows PowerShell, lệnh in câu trả lời có chứa ký tự unicode pointer `►` hoặc tiếng Việt bị crash lỗi `UnicodeEncodeError: 'charmap' codec can't encode character...`.
- **Nguyên nhân:** Khung console chuẩn của Windows sử dụng bảng mã mặc định CP1252 thay vì UTF-8.
- **Cách xử lý:** Đã bổ sung `sys.stdout.reconfigure(encoding="utf-8")` tại đầu file `script/demo_agent.py` và thay thế ký tự unicode pointer bằng ký tự chuẩn ASCII.
- **Cách xác minh:** Chạy lại `python script/demo_agent.py --state corrupted` trên PowerShell thành công với Exit code 0.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Phụ thuộc vào OpenRouter API key cho LLM Judge | Kết nối API có thể bị lỗi 402/429 khi hết quota | Tích hợp Ollama local (ví dụ `llama3`) cho LLM Judge hoàn toàn offline |
| Số lượng bài báo raw còn nhỏ (24 records) | Chưa thử nghiệm được quy mô lớn | Mở rộng ingest 1,000+ Crossref records |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.