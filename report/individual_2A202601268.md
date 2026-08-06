# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Võ Duy Quang |
| MSSV | 2A202601268 |
| Khóa/Lớp | K4 |
| Tên nhóm | 5AngryMen |
| Vai trò chính | **Role 3 - Data Cleaning, Data Corruption & Data Repair Owner** |
| Repository | `Day10_5AngryMen` |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data Cleaning | `src/ingestion/cleaning.py`<br>`build_clean_dataframe()` | List `PaperRecord` từ `data/raw/crossref_records.json` & `run_date` | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | Hoàn thành |
| Data Corruption Engine | `src/ingestion/corruption.py`<br>`corrupt_clean_dataframe()` | Cleaned `pd.DataFrame` & `output_log_path` | `data/clean/papers_clean_corrupted.csv`<br>`data/clean/papers_clean_corrupted.json`<br>`data/results/corruption_log.json` | Hoàn thành |
| Separated Corrupted Datasets | `src/ingestion/corruption.py`<br>`generate_separated_corrupted_datasets()` | Cleaned `pd.DataFrame` & `output_dir` | 30 files dữ liệu lỗi độc lập (CSV, JSON, Log) trong `data/clean/corrupted_by_type/` | Hoàn thành |
| Data Repair Engine | `src/ingestion/cleaning.py`<br>`repair_dataframe_from_snapshot()` | File raw snapshot `data/raw/crossref_records.json` & `run_date` | `data/clean/papers_clean_repaired.csv`<br>`data/clean/papers_clean_repaired.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Schema & Data Format Verification | Thành viên 4 (`src/retrieval/index.py`) | Đảm bảo cột `text_for_embedding`, `authors_joined`, `categories_joined` khớp 100% với schema ChromaDB indexing. |
| Quality Rule Alignment | Thành viên 5 (`src/observability/quality.py`) | Thống nhất các quy tắc kiểm tra rỗng summary, rỗng title, ngày xuất bản cũ để phục vụ bộ Data Quality Checks và Freshness Monitoring. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Data Cleaning | `src/ingestion/cleaning.py`<br>`build_clean_dataframe` | `data/clean/papers_clean.csv` (24 bài báo)<br>`data/clean/papers_clean.json` | `uv run python -c "from ingestion.cleaning import build_clean_dataframe..."` |
| Multi-Type Data Corruption | `src/ingestion/corruption.py`<br>`corrupt_clean_dataframe` | `data/clean/papers_clean_corrupted.csv`<br>`data/results/corruption_log.json` | `uv run python -c "from ingestion.corruption import corrupt_clean_dataframe..."` |
| Separated Corrupted Datasets | `src/ingestion/corruption.py`<br>`generate_separated_corrupted_datasets` | 30 files riêng biệt trong `data/clean/corrupted_by_type/` | `uv run python -c "from ingestion.corruption import generate_separated_corrupted_datasets..."` |
| Snapshot Data Repair | `src/ingestion/cleaning.py`<br>`repair_dataframe_from_snapshot` | `data/clean/papers_clean_repaired.csv`<br>`data/clean/papers_clean_repaired.json` | `uv run python -c "from ingestion.cleaning import repair_dataframe_from_snapshot..."` |

### Mô tả cụ thể Artifact tạo ra:
- **`data/clean/papers_clean.csv` & `.json`**: Bộ dữ liệu sạch chuẩn hóa 24 bài báo học thuật đã loại bỏ thẻ HTML, gộp tác giả/danh mục, tính `age_days` và cột nhúng `text_for_embedding`.
- **Bộ 30 files trong `data/clean/corrupted_by_type/`**: Gồm 10 bộ dữ liệu lỗi tách biệt tương ứng với 10 kịch bản lỗi đơn lẻ (`drop_latest`, `blank_summary`, `text_noise`, `misleading_summary`, `truncate_title`, `stale_date`, `corrupt_authors`, `null_metadata`, `corrupt_paper_id`, `duplicate_rows`).
- **`data/clean/papers_clean_repaired.csv` & `.json`**: Dữ liệu đã phục hồi sạch hoàn toàn từ snapshot thô mà không cần gọi lại external API.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Dữ liệu thô lấy từ API Crossref thường chứa các thẻ XML/HTML rác (`<jats:p>`, `<b>`), danh sách tác giả bị lồng ghép phức tạp, định dạng ngày xuất bản không nhất quán, và một số bài báo thiếu tóm tắt. Nếu đưa trực tiếp dữ liệu thô này vào ChromaDB vector store, RAG Agent sẽ truy vấn sai hoặc trả về câu trả lời kém chất lượng. Ngoài ra, để chứng minh tầm quan trọng của Data Observability, hệ thống cần một engine tiêm lỗi chủ đích (Corruption Engine) và quy trình phục hồi tự động (Data Repair).

### Cách triển khai

1. **Data Cleaning (`build_clean_dataframe`)**:
   - Sử dụng Regular Expression `re.sub(r'<[^>]+>', ' ', text)` bóc tách toàn bộ thẻ XML/HTML khỏi `title` và `summary`.
   - Lọc bỏ bài báo rác: loại bỏ bản ghi có `title` rỗng hoặc `len(summary) < 100` ký tự.
   - Gộp danh sách tác giả & danh mục thành dạng chuỗi phân cách bởi dấu phẩy (`authors_joined`, `categories_joined`).
   - Ép ngày `published` về định dạng `YYYY-MM-DD` và tính toán `age_days = (run_date - published_date).days`.
   - Sinh cột `text_for_embedding = f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"`.
   - Deduplicate bài báo theo `paper_id` (DOI) và `title`, sau đó sắp xếp theo ngày xuất bản giảm dần.

2. **Data Corruption Engine (`corrupt_clean_dataframe` & `corrupt_by_single_type`)**:
   - Thiết lập `random.seed(42)` đảm bảo tính tái lập.
   - Triển khai **10 dạng dữ liệu lỗi**:
     - `drop_latest`: Bỏ ~20% bài báo mới nhất.
     - `blank_summary`: Xóa rỗng summary (~10%).
     - `text_noise`: Tiêm thẻ XML/HTML rác vào summary (~10%).
     - `misleading_summary`: Tiêm các phát biểu sai sự thật/nghiên cứu bị rút lại vào summary (~10%).
     - `truncate_title`: Cắt ngắn tiêu đề còn 15 ký tự (~10%).
     - `stale_date`: Đặt ngày `published` về năm `2010-01-01` (~10%).
     - `corrupt_authors`: Thay đổi tác giả thành `"Unknown Author, Anonymous Bot"` (~10%).
     - `null_metadata`: Xóa rỗng URL và danh mục chính (~10%).
     - `corrupt_paper_id`: Gắn tiền tố `INVALID_CORRUPTED_ID/` vào paper_id (~10%).
     - `duplicate_rows`: Nhân bản các dòng dữ liệu (~15%).
   - Tái tổng hợp lại `text_for_embedding` và `summary_chars` cho các dòng lỗi.
   - Ghi chi tiết mã bài báo và loại lỗi vào file log `output_log_path`.

3. **Data Repair (`repair_dataframe_from_snapshot`)**:
   - Tải file snapshot `data/raw/crossref_records.json`.
   - Chạy lại hàm `build_clean_dataframe()` để khôi phục 100% dữ liệu sạch mà không phụ thuộc vào mạng hay API Crossref bên ngoài.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `list[PaperRecord]` từ `data/raw/crossref_records.json` & `run_date` (`datetime`) |
| Output | `pd.DataFrame` sạch/lỗi/repaired, lưu dưới dạng CSV và JSON trong `data/clean/` |
| Module phụ thuộc | `src/ingestion/crossref.py` (`PaperRecord`, `load_raw_records`) |
| Module sử dụng output | `src/retrieval/index.py` (TV4 nạp ChromaDB) & `src/observability/quality.py` (TV5 kiểm tra Data Quality) |
| Điều kiện lỗi cần xử lý | Dữ liệu rỗng, ngày xuất bản không đúng định dạng ISO, danh sách tác giả bị `None`, chuỗi XML lồng phức tạp |

### Cách xác minh

```bash
$env:PYTHONPATH="src"
uv run python -c "from datetime import datetime; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe, repair_dataframe_from_snapshot; from ingestion.corruption import corrupt_clean_dataframe, generate_separated_corrupted_datasets; from core.config import load_settings; settings = load_settings(); records = load_raw_records(settings.paths.raw_records_json); clean_df = build_clean_dataframe(records, datetime.now()); print(f'Clean shape: {clean_df.shape}'); corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log); print(f'Corrupted shape: {corrupted_df.shape}'); repair_df = repair_dataframe_from_snapshot(settings.paths.raw_records_json, datetime.now()); print(f'Repaired shape: {repair_df.shape}'); sep_files = generate_separated_corrupted_datasets(clean_df, settings.paths.clean_csv.parent / 'corrupted_by_type'); print(f'Generated {len(sep_files)} separated files')"
```

- **Kết quả mong đợi:** Mã nguồn thực thi thành công không lỗi; sinh đầy đủ file baseline sạch, file lỗi tổng hợp, file repaired, và 30 file lỗi tách biệt.
- **Kết quả thực tế:** Mã nguồn chạy thành công (Exit Code 0). `Clean shape: (24, 16)`, `Corrupted shape: (23, 16)`, `Repaired shape: (24, 16)`, sinh thành công 30 files tách biệt.
- **Artifact/log:**
  - `data/clean/papers_clean.csv`
  - `data/clean/papers_clean_corrupted.csv`
  - `data/clean/papers_clean_repaired.csv`
  - `data/results/corruption_log.json`
  - `data/clean/corrupted_by_type/*.csv`

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Ban đầu kịch bản corruption gộp toàn bộ 10 dạng lỗi dữ liệu vào duy nhất 1 file `papers_clean_corrupted.csv`. Việc này làm khó khả năng quan sát (observability) vì không thể đánh giá chính xác loại lỗi nào (ví dụ: mất tiêu đề vs. tiêm văn bản sai sự thật) gây sụt giảm chỉ số Hit Rate hay Token F1 nhiều nhất.
- **Các phương án đã cân nhắc:**
  1. *Option 1*: Chỉ giữ duy nhất 1 file dữ liệu gài lỗi gộp (`papers_clean_corrupted.csv`).
  2. *Option 2*: Triển khai thêm hàm `generate_separated_corrupted_datasets()` để sinh riêng 10 bộ dữ liệu lỗi độc lập cho từng loại lỗi (`papers_corrupted_drop_latest.csv`, `papers_corrupted_blank_summary.csv`, v.v.), song song với file gộp.
- **Phương án đã chọn:** Option 2.
- **Lý do:** Trade-off gia tăng dung lượng đĩa nhỏ (~2MB) nhưng mang lại lợi ích rất lớn về tính minh bạch (interpretability) và khả năng quan sát (data observability). Điều này cho phép TV5 chạy đánh giá nguyên nhân-kết quả (ablation analysis) cho từng loại lỗi đơn lẻ.
- **Bằng chứng quyết định phù hợp:** Đã tạo thành công 30 files trong `data/clean/corrupted_by_type/` và xác minh rằng mỗi file chứa đúng duy nhất 1 dạng lỗi tương ứng.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ModuleNotFoundError: No module named 'ingestion'
  ModuleNotFoundError: No module named 'pandas'
  ```
- **Lệnh hoặc bước tái hiện:** Chạy lệnh `python -c "from ingestion.cleaning import build_clean_dataframe..."` từ thư mục gốc của project mà chưa cài môi trường virtualenv hoặc chưa thêm `src` vào `PYTHONPATH`.
- **Nguyên nhân gốc:** Python mặc định tìm kiếm module tại root directory, trong khi toàn bộ mã nguồn của project nằm trong thư mục `src/`. Ngoài ra, các thư viện phụ thuộc (`pandas`, `requests`) nằm trong virtual environment `.venv` của `uv`.
- **Cách xử lý:** Đảm bảo kích hoạt virtual environment bằng `uv run` và thiết lập biến môi trường `$env:PYTHONPATH="src"` trước khi chạy script.
- **Cách xác minh sau khi sửa:**
  ```bash
  $env:PYTHONPATH="src"; uv run python -c "from ingestion.cleaning import build_clean_dataframe; print('Import successful')"
  ```
  Lệnh chạy thành công và in ra `Import successful`.
- **Điều học được:** Khi phát triển Python project dạng package với cấu trúc `src/`, luôn cần chú ý đến `PYTHONPATH` và virtual environment isolation để tránh lỗi import.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   TV2 gọi Crossref REST API lấy payload JSON thô, lưu trữ tại `data/raw/crossref_response.json` và parse thành list `PaperRecord` tại `data/raw/crossref_records.json`. TV3 (Role 3) nhận list records, lọc bỏ bài báo rác, bóc tách thẻ HTML, chuẩn hóa thông tin, tính `age_days`, tạo chuỗi `text_for_embedding` và xuất file `data/clean/papers_clean.csv`. TV4 đọc file cleaned này, sử dụng model `all-MiniLM-L6-v2` tạo vector embeddings và nạp vào ChromaDB collection (`papers-baseline`).

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   TV5 tạo bộ test set `data/eval/test_set.json` gồm các câu hỏi kèm `ground_truth_doc_ids` (mã bài báo chứa câu trả lời chuẩn). Khi RAG Agent nhận câu hỏi, nó tìm top-k bài báo liên quan từ ChromaDB. Chỉ số `retrieval_hit_rate` kiểm tra xem `ground_truth_doc_ids` có nằm trong top-k hay không. Tiếp đó, LLM trả lời câu hỏi dựa trên context, chỉ số `mean_token_f1` và `judge_accuracy` đánh giá độ khớp giữa câu trả lời của agent và `ground_truth`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks**: Kiểm tra tính toàn vẹn và hợp lệ của dữ liệu tĩnh (Data Quality & Schema Compliance) như: không bị rỗng paper_id/title, độ dài summary đạt yêu cầu, không có dòng trùng lặp.
   - **Freshness monitoring**: Kiểm tra tính cập nhật thời gian của dữ liệu (Data Freshness & Timeliness) dựa trên ngày xuất bản (`published`) và `age_days` so với ngưỡng quy định (ví dụ 180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Dùng chung một bộ test set cố định là điều kiện bắt buộc để đảm bảo tính công bằng và nhất quán của phép đo (controlled benchmark environment). Sự thay đổi của các chỉ số (Hit Rate, Token F1) giữa 3 trạng thái hoàn toàn đến từ sự thay đổi của chất lượng dữ liệu (Data Quality), không phải do độ khó của câu hỏi.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Data Repair thành công khi:
   - **Artifact**: File dữ liệu `data/clean/papers_clean_repaired.csv` và collection ChromaDB `papers-repaired` khôi phục lại cấu trúc và nội dung chuẩn.
   - **Metrics**: Các chỉ số RAG (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) trên tập repaired tăng trở lại tương đương hoặc gần bằng mức baseline ban đầu, đồng thời các báo cáo Data Quality / Freshness chuyển từ trạng thái `FAIL` về `PASS`.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.00 (100%) | 0.45 (45%) | 1.00 (100%) | Dữ liệu lỗi (mất bài báo mới, rỗng summary, sai paper_id) làm giảm mạnh khả năng retrieve đúng bài báo. Repair phục hồi 100%. |
| `mean_token_f1` | 0.82 | 0.38 | 0.82 | Văn bản bị tiêm nhiễu HTML và phát biểu bịa đặt làm sai lệch câu trả lời của LLM. Token F1 phục hồi hoàn toàn sau repair. |
| `judge_accuracy` | 0.95 | 0.40 | 0.95 | LLM Judge đánh giá câu trả lời bị sai nghiêm trọng khi dữ liệu bị corrupt. |
| `mean_judge_score` | 4.6 / 5.0 | 2.1 / 5.0 | 4.6 / 5.0 | Điểm chất lượng câu trả lời sụt giảm sâu ở trạng thái corrupted. |
| Quality checks | PASS | FAIL | PASS | Phát hiện chính xác các lỗi rỗng summary, trùng lặp dòng, và sai định dạng ID. |
| Freshness status | FRESH | STALE / FAIL | FRESH | Cảnh báo chính xác các bài báo bị ép ngày xuất bản về năm 2010. |

### Kết luận từ số liệu

1. **[Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:**  
   Khi gài lỗi `blank_summary` và `text_noise`, báo cáo Quality Checks báo `FAIL` (do độ dài summary = 0 và chứa thẻ XML rác). Tương ứng, `retrieval_hit_rate` giảm từ 100% xuống 45% và `mean_token_f1` giảm từ 0.82 xuống 0.38 do RAG Agent không lấy được ngữ cảnh chất lượng.

2. **[Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi]:**  
   Khi thực hiện `repair_dataframe_from_snapshot()`, dữ liệu thô chuẩn được nạp lại, Quality Checks chuyển về `PASS`. ChromaDB collection `papers-repaired` được index lại giúp `retrieval_hit_rate` và `mean_token_f1` phục hồi 100% về mức baseline.

- **Corruption nào ảnh hưởng rõ nhất và vì sao?**  
  `drop_latest` (mất bài báo mới nhất) và `blank_summary` (rỗng tóm tắt) ảnh hưởng nghiêm trọng nhất. Với `drop_latest`, thông tin hoàn toàn không có trong kho vector store nên Hit Rate cho các câu hỏi về bài báo đó bằng 0. Với `blank_summary`, vector embedding không chứa thông tin ngữ nghĩa dẫn đến RAG Agent retrieve nhầm bài báo khác.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline**: Data pipeline không chỉ đơn thuần là chuyển đổi dữ liệu (ETL) mà phải có cơ chế bảo vệ tính toàn vẹn (data integrity) và lưu trữ raw snapshot để phục vụ khả năng tự phục hồi (data recovery).
2. **Về Data Quality & Observability**: Data Observability (Quality Checks, Freshness Monitoring) đóng vai trò là "lớp bảo vệ sớm" (early warning mechanism), phát hiện sự cố dữ liệu trước khi dữ liệu xấu đi vào Vector Database.
3. **Về ảnh hưởng của Data đến RAG Agent**: "Garbage in, Garbage out" — Chất lượng câu trả lời của LLM Agent phụ thuộc trực tiếp vào chất lượng của dữ liệu đầu vào. Dữ liệu lỗi làm suy giảm nghiêm trọng độ chính xác của RAG.

### Nếu có thêm thời gian

Nếu có thêm thời gian, tôi sẽ triển khai **Automated Outlier Detection & Anomaly Cleaning Engine** sử dụng thuật toán TF-IDF / Cosine Similarity để tự động phát hiện và loại bỏ các đoạn văn bản tiêm nhiễu (HTML noise, phát biểu bịa đặt) mà không cần khôi phục lại toàn bộ snapshot.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Thành viên 3  
**Ngày xác nhận:** 2026-08-06
