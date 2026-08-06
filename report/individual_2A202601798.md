# Báo cáo vai trò cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Đăng Nguyên |
| MSSV | 2A202601798 |
| Khóa/Lớp | K4 |
| Tên nhóm | Team_5_Angry_Man |
| Vai trò chính | Thành viên 5 — Evaluation & Data Observability Owner |
| Repository | https://github.com/Linhcodelinhtinh/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Evaluation Test Set | `src/evaluation/testset.py`: `build_test_set()` | `cleaned_df` (`papers_clean.csv`), `output_path` | `data/eval/test_set.json` — 60 câu hỏi chuẩn hóa theo 4 loại | Hoàn thành |
| Data Quality Checks | `src/observability/quality.py`: `run_data_quality_checks()` | `df`, `settings`, `report_name` | `data/quality/{report_name}.json` — kết quả kiểm tra toàn vẹn dữ liệu | Hoàn thành |
| Freshness Monitoring | `src/observability/quality.py`: `build_freshness_report()` | `df`, `settings`, `report_path` | `data/quality/freshness_report.json` — trạng thái độ tươi mới dữ liệu | Hoàn thành |
| Phase 1 Baseline Report | `src/observability/reporting.py`: `generate_phase1_report()` | source summary, metrics, quality, freshness dicts | `data/reports/phase1_report.md` | Hoàn thành |
| Corruption Comparison Report | `src/observability/reporting.py`: `generate_corruption_report()` | baseline/corrupted/repaired metrics, quality, freshness dicts | `data/reports/corruption_report.md` | Hoàn thành |
| Evaluation & Observability Tests | `tests/test_evalandObser.py` | Fake DataFrames, temp directories | 7 automated test cases | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thêm CLI entrypoint cho testset | TV1 — `src/pipelines/phase1.py` | Bổ sung `if __name__ == "__main__":` vào `testset.py` giúp TV1 chạy test set standalone và debug độc lập không cần chạy toàn bộ pipeline |
| Giải thích contract `answer_question()` | TV4 — `src/retrieval/qa.py` | Xác nhận TV5 dùng đúng contract `answer_question(question, settings, index)` theo output từ TV4, không cần thay đổi `metrics.py` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Sinh bộ đề kiểm thử 60 câu hỏi từ cleaned data | `src/evaluation/testset.py` | `data/eval/test_set.json` (53KB, 60 items) | `.\.venv\Scripts\python.exe src/evaluation/testset.py` |
| Data Quality Gate — kiểm tra null, trùng, rỗng | `src/observability/quality.py` | `data/quality/baseline_quality.json` — `passed: true` | `python -m unittest tests/test_evalandObser.py` |
| Freshness Report — xác định stale_rows, is_fresh | `src/observability/quality.py` | `data/quality/freshness_report.json` — `is_fresh: true` | `python -m unittest tests/test_evalandObser.py` |
| Báo cáo Markdown Phase 1 Baseline | `src/observability/reporting.py` | `data/reports/phase1_report.md` | Kiểm tra file tồn tại và đọc nội dung |
| Báo cáo so sánh 3 trạng thái | `src/observability/reporting.py` | `data/reports/corruption_report.md` | Kiểm tra bảng so sánh metrics và delta values |

Output cụ thể của phần việc là `data/eval/test_set.json` chứa 60 câu hỏi được trích xuất tự động từ 15 bài báo trong `papers_clean.csv`, đảm bảo ground truth 100% chính xác và test set cố định cho toàn bộ 3 pha đánh giá. Toàn bộ 7/7 unit test của module đều PASS (`Ran 7 tests in 0.023s — OK`).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần có một bộ đề kiểm thử (benchmark) cố định và một hệ thống giám sát dữ liệu tự động để trả lời hai câu hỏi: (1) RAG Agent có trả lời đúng không khi dữ liệu sạch? (2) Khi dữ liệu bị hỏng, hệ thống có phát hiện được và chứng minh được mức giảm chất lượng bằng số liệu không? Không có benchmark cố định, không thể so sánh công bằng giữa 3 trạng thái; không có observability checks, lỗi dữ liệu sẽ âm thầm lan vào ChromaDB rồi đến tay người dùng.

### Cách triển khai

`build_test_set` trích xuất trực tiếp metadata từ `cleaned_df` (không dùng LLM) và tạo 4 nhóm câu hỏi cho mỗi paper: `summary` (ground truth = toàn bộ nội dung summary), `authors` (ground truth = danh sách tác giả join bằng dấu phẩy), `date` (ground truth = ngày xuất bản ISO), `categories` (ground truth = chủ đề nghiên cứu). Mỗi item ghi rõ `ground_truth_doc_ids` chứa `paper_id` gốc để evaluator trong `metrics.py` đối chiếu retrieval hit.

`run_data_quality_checks` thực hiện 5 kiểm tra: row count > 0, `paper_id` không null, `paper_id` không trùng (`nunique`), `title` không rỗng, `summary` dài hơn 20 ký tự. Kết quả gộp thành dict `checks` và trường `passed: bool` đánh giá gate tổng thể. `build_freshness_report` tính max/min của cột `published` và đếm số dòng có `age_days > freshness_threshold_days` (mặc định 180 ngày).

Hai hàm reporting nhận metric dict từ `metrics.py`, quality/freshness dict từ `quality.py` và tổng hợp thành Markdown với bảng so sánh và delta (+/-) giữa các trạng thái.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `cleaned_df` (`pd.DataFrame`) có các cột: `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days` |
| Output | `test_set.json` (list[dict]), `quality_report.json`, `freshness_report.json`, `phase1_report.md`, `corruption_report.md` |
| Module phụ thuộc | `core.config.Settings`, `core.utils.write_json/write_text`, cleaned artifacts của TV3 |
| Module sử dụng output | `src/evaluation/metrics.py` dùng `test_set.json`; `src/pipelines/phase1.py` và `corruption_flow.py` gọi cả quality checks và reporting |
| Điều kiện lỗi cần xử lý | `DataFrame` rỗng hoặc None → `ValueError`; thiếu cột `paper_id`/`title` → fallback về 0; file output directory không tồn tại → `write_json`/`write_text` tự tạo qua `ensure_parent()` |

### Cách xác minh

```bash
# Chạy unit test suite
.\.venv\Scripts\python.exe -m unittest tests/test_evalandObser.py -v

# Sinh test_set.json từ cleaned data thực
.\.venv\Scripts\python.exe src/evaluation/testset.py
```

- **Kết quả mong đợi:** 7/7 unit tests PASS; `data/eval/test_set.json` được tạo với 60 items từ `papers_clean.csv`.
- **Kết quả thực tế:** `Ran 7 tests in 0.023s — OK`; file `test_set.json` 53KB với 60 câu hỏi, đầy đủ schema `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
- **Artifact/log:** `data/eval/test_set.json`, `data/quality/`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp sinh test set — dùng LLM để đặt câu hỏi sáng tạo từ summary, hay dùng rule-based extraction trực tiếp từ metadata dữ liệu sạch.
- **Các phương án đã cân nhắc:** (A) Gọi LLM sinh câu hỏi đa dạng từ nội dung summary — câu hỏi tự nhiên hơn nhưng ground truth phụ thuộc vào LLM output, không deterministic và tốn API. (B) Trích xuất metadata trực tiếp thành câu hỏi template — đơn giản, ground truth chính xác 100% bằng dữ liệu thực, reproducible.
- **Phương án đã chọn:** Phương án B — rule-based extraction.
- **Lý do:** Test set đóng vai trò biến điều khiển (control variable) trong thí nghiệm so sánh 3 trạng thái. Nếu ground truth do LLM sinh ra và LLM có thể hallucinate, phép đo sẽ không đáng tin cậy. Phương án B đảm bảo ground truth = sự thật trong dữ liệu, không tốn chi phí API, không cần internet và chạy trong vài mili giây.
- **Bằng chứng quyết định phù hợp:** Test set sinh ra 60 items với `ground_truth_doc_ids` khớp chính xác với `paper_id` trong ChromaDB, không có item thiếu ID; baseline retrieval hit rate đạt `1.0000` xác nhận test set alignment với index.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Chạy `python src/evaluation/testset.py` không có output gì, file `data/eval/test_set.json` không được tạo.
- **Lệnh hoặc bước tái hiện:** `python src/evaluation/testset.py` (với `.venv` đã kích hoạt).
- **Nguyên nhân gốc:** `testset.py` chỉ định nghĩa hàm `build_test_set()` để pipeline gọi, không có khối `if __name__ == "__main__":` để thực thi khi chạy trực tiếp từ CLI. Python chạy file, không tìm thấy lệnh nào để thực thi, exit 0 không có output.
- **Cách xử lý:** Bổ sung khối `if __name__ == "__main__":` vào cuối `testset.py`: kiểm tra `data/clean/papers_clean.csv` tồn tại, nạp DataFrame và gọi `build_test_set(df, settings.paths.eval_testset)`.
- **Cách xác minh sau khi sửa:** `python src/evaluation/testset.py` in ra `Loading cleaned dataset from ... papers_clean.csv` rồi `Successfully generated 60 test questions at ... test_set.json!`.
- **Điều học được:** Module Python cần hỗ trợ cả hai giao diện: hàm để pipeline gọi programmatically và CLI context để debug/standalone execution. Thiếu `if __name__ == "__main__":` là blocker thường gặp khi cần chạy nhanh một bước trong pipeline mà không muốn chạy toàn bộ flow.

## 7. Hiểu biết về luồng end-to-end

1. TV2 gọi Crossref REST API, lưu raw response và raw records vào `data/raw/`. TV3 làm sạch, tính `age_days`, tạo `text_for_embedding` và lưu `data/clean/papers_clean.csv`. TV4 nạp `text_for_embedding` vào MiniLM-L6-v2 tạo vector, lưu vào ChromaDB collection `papers-baseline`. Dữ liệu đi từ JSON thuần túy → DataFrame chuẩn hóa → vector index có thể search.
2. `test_set.json` chứa `ground_truth_doc_ids` là `paper_id` của document đúng. Khi evaluator (`metrics.py`) nhận câu trả lời từ agent, nó kiểm tra `retrieved_doc_ids` có chứa `ground_truth_doc_ids` không để tính `retrieval_hit`. Đồng thời so sánh answer text với `ground_truth` bằng token F1, và gọi LLM judge để cho điểm 1-5 và nhận xét `correct: bool`.
3. Quality checks (`run_data_quality_checks`) đo tính toàn vẹn cấu trúc: null values, duplicate `paper_id`, tiêu đề rỗng, summary quá ngắn — những lỗi schema và dữ liệu thiếu. Freshness monitoring (`build_freshness_report`) đo chiều thời gian: ngày xuất bản mới nhất/cũ nhất, số bản ghi vượt ngưỡng `freshness_threshold_days` — phát hiện dữ liệu lỗi thời.
4. Ba pha phải dùng cùng `test_set.json`, cùng `top_k` và cùng evaluator để thay đổi metrics chỉ đến từ sự khác biệt dữ liệu, không phải từ câu hỏi khó hơn hay cấu hình đánh giá khác nhau. Nếu đổi test set giữa các pha, không thể kết luận dữ liệu hỏng làm giảm chất lượng agent.
5. Repair được xem là thành công khi: (a) `data/quality/repaired_quality.json` trả về `passed: true`; (b) `data/quality/freshness_report.json` (repaired) trả về `is_fresh: true, stale_rows: 0`; (c) `data/results/repaired_metrics.json` có `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` và `mean_judge_score` trở về đúng giá trị baseline. Artifact thực tế: repaired có 24 documents (bằng baseline), `retrieval_hit_rate` = `1.0000` và toàn bộ metric khớp baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6667 | 1.0000 | Corruption làm mất 15/45 retrieval hits do drop latest records và corrupt paper ID; repair phục hồi toàn bộ |
| `mean_token_f1` | 0.4257 | 0.2827 | 0.4257 | Answer text overlap giảm 0.143 khi context thiếu và nhiễu; repair khôi phục về baseline |
| `judge_accuracy` | 0.3556 | 0.2444 | 0.3556 | Fallback heuristic judge đang được dùng vì LLM evaluator chưa khả dụng; tương đối đủ để so sánh 3 trạng thái |
| `mean_judge_score` | 2.3778 | 1.9333 | 2.3778 | Giảm ~0.44 điểm khi corrupted; phục hồi hoàn toàn sau repair |
| Quality checks | PASS | FAIL | PASS | Corrupted có 3 duplicate IDs, 2 summary ngắn và 2 stale rows — quality gate phát hiện đúng |
| Freshness status | FRESH | STALE | FRESH | Stale date corruption đẩy ngày cũ nhất về `2010-01-01`; repair loại bỏ toàn bộ stale rows |

### Kết luận từ số liệu

1. Drop latest records và corrupt paper IDs → ground-truth documents biến mất hoặc có ID không khớp → `retrieval_hit_rate` giảm từ `1.0000` xuống `0.6667`; quality checks báo `FAIL` (duplicate IDs, short summaries); freshness báo `STALE` (stale date corruption) → token F1 và judge score đều giảm theo.
2. Reload raw snapshot → re-clean → re-index → duplicate, short summary và stale rows bị loại bỏ → quality/freshness trở về `PASS/FRESH` → toàn bộ 4 metric repaired bằng đúng baseline.

Corruption ảnh hưởng rõ nhất là `drop_latest`: bốn paper bị xóa tương ứng 12/15 retrieval misses vì mỗi paper có 3 câu hỏi (summary/authors/date). Ba misses còn lại do một paper bị đổi `paper_id` thành `INVALID_CORRUPTED_ID/`. Đây là bằng chứng rõ ràng rằng document availability và identity ảnh hưởng mạnh hơn các lỗi metadata phụ.

Kết quả khác kỳ vọng là `judge_accuracy` baseline chỉ đạt `0.3556` dù `retrieval_hit_rate` = `1.0`. Kiểm tra answer artifacts cho thấy toàn bộ 45 samples dùng fallback heuristic judge do LLM evaluator không khả dụng trong môi trường chạy. Điều này đủ để so sánh tương đối giữa 3 trạng thái nhưng chưa phản ánh judge accuracy thực sự khi có LLM.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Raw lineage (`data/raw/`) là điều kiện tiên quyết để repair hoàn toàn — không có raw snapshot thì không thể tái tạo dữ liệu từ các corruption loại drop/blank.
2. **Về Data Quality & Observability:** Quality checks và freshness monitor phát hiện lỗi dữ liệu ngay khi chạy, trước khi agent trả câu trả lời sai tới người dùng. Đây là "lớp phòng thủ đầu tiên" của hệ thống.
3. **Về ảnh hưởng của Data đến RAG Agent:** Retrieval hit rate nhạy cảm nhất với lỗi document identity (mất record hoặc sai paper_id); answer quality nhạy cảm với lỗi nội dung (blank summary, text noise). Hai nhóm lỗi cần giám sát bằng hai loại check khác nhau.

### Nếu có thêm thời gian

Tôi sẽ thêm evaluation theo từng `question_type` (`summary`, `authors`, `date`, `categories`) để xác định loại câu hỏi nào bị ảnh hưởng nhiều nhất bởi từng corruption type. Cải thiện đo bằng hit rate breakdown theo question_type trước và sau corruption. Ngoài ra sẽ bật Ragas evaluation thật (`RUN_RAGAS=1`) để có semantic similarity score thay cho fallback heuristic judge.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Đăng Nguyên
**Ngày xác nhận:** 2026-08-06
