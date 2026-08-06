# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Lưu Quang Linh |
| MSSV | 2A202601084 |
| Khóa/Lớp | K4 |
| Tên nhóm | 5 Angry Man |
| Vai trò chính | Pipeline Integrator & Team Lead |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Core Config & Settings | `src/core/config.py` (`load_settings`, `ensure_directories`) | `.env`, environment variables | Settings object & directory structure | Hoàn thành |
| Baseline Pipeline Orchestration | `src/pipelines/phase1.py`, `script/run_phase1.py` | Raw data, settings | Clean CSV, baseline Chroma index, metrics & report | Hoàn thành |
| Corruption & Repair Pipeline | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean CSV, raw snapshot | Corrupted index, repaired index, comparison report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Debug RAG LLM Provider Fallback | TV4 (`src/retrieval/llm.py`, `agent.py`) | Thêm lazy import và heuristic token F1 fallback tránh crash API |
| Sửa lỗi Encoding Windows Terminal | TV5 (`script/demo_agent.py`, `qa.py`) | Bổ sung `sys.stdout.reconfigure(encoding='utf-8')` sửa lỗi Unicode |
| Thiết kế UI Dashboard | TV5 (`dashboard.html`, `serve_dashboard.py`) | Xây dựng giao diện dashboard HTML tương tác với Chart.js |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập cấu hình hệ thống & thư mục | `src/core/config.py` | `ensure_directories()` tự động khởi tạo các thư mục `data/` | Run `python -c "from core.config import load_settings, ensure_directories; s=load_settings(); ensure_directories(s)"` |
| Điều phối Baseline Flow Phase 1 | `src/pipelines/phase1.py`, `script/run_phase1.py` | Sinh ra `papers_clean.csv`, index `papers-baseline`, `baseline_metrics.json` | Run `python script/run_phase1.py` (Exit code 0) |
| Điều phối Corruption & Repair Flow | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Sinh ra `papers-corrupted`, `papers-repaired`, `corruption_report.md` | Run `python script/run_corruption_flow.py` (Exit code 0) |

**Mô tả output cụ thể:**
Đã tích hợp thành công toàn bộ luồng pipeline 2 pha chạy hoàn toàn tự động từ CLI thông qua 2 entrypoint `script/run_phase1.py` và `script/run_corruption_flow.py`. Hệ thống tự động tạo bộ test set 60 câu hỏi, chấm điểm, chạy quality checks và tạo báo cáo markdown đối chiếu số liệu mượt mà.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Điều phối luồng dữ liệu liên tục và nhất quán giữa các module độc lập (Ingestion -> Cleaning -> Vector Store -> Evaluation -> Observability), đảm bảo không bị ngắt quãng hoặc crash ngay cả khi môi trường thiếu gói phụ thuộc hoặc gặp lỗi kết nối API LLM.

### Cách triển khai

- Sử dụng mô hình `Settings` tập trung với dataclass `Paths` tính toán tự động tất cả đường dẫn thư mục trong dự án (`data/raw`, `clean`, `chroma`, `eval`, `results`, `quality`, `reports`).
- Viết hàm `ensure_directories(settings)` khởi tạo sẵn cấu trúc thư mục trước khi thực thi ETL.
- Xây dựng luồng tuần tự trong `phase1.py` và `corruption_flow.py` có cơ chế try-except bọc các bước tùy chọn (Ragas evaluation, LLM Judge API call) để ưu tiên chạy thành công pipeline.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | Environment settings, Raw Crossref JSON Snapshot |
| Output | Vector Index collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`), JSON metrics & Markdown Reports |
| Module phụ thuộc | `src/ingestion/`, `src/retrieval/`, `src/evaluation/`, `src/observability/` |
| Module sử dụng output | CLI Scripts (`script/run_phase1.py`, `script/run_corruption_flow.py`) & UI Dashboard |
| Điều kiện lỗi cần xử lý | Lỗi kết nối HTTP 429/503 Crossref, lỗi thiếu API Key OpenRouter/Gemini, lỗi UTF-8 encoding console |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả 2 script thực thi mượt mà từ đầu đến cuối, trả về `Exit code 0`.
- **Kết quả thực tế:** Cả 2 script đều hoàn tất 100% không gặp lỗi, tạo ra đầy đủ các file metrics và report trong `data/`.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi đánh giá RAG bằng LLM Judge qua OpenRouter API, đôi khi key bị hết quota (trả về lỗi HTTP `402 Payment Required`), dẫn đến nguy cơ crash toàn bộ script pipeline.
- **Các phương án đã cân nhắc:**
  1. *Phương án 1:* Dừng pipeline và báo lỗi yêu cầu người dùng nạp tiền / đổi API key.
  2. *Phương án 2 (Được chọn):* Bổ sung cơ chế Heuristic Token F1 Fallback trong `metrics.py` & `llm.py`.
- **Phương án đã chọn:** Phương án 2. Khi LLM API gặp lỗi, hệ thống tự động suy ra điểm số Judge từ độ tương đồng Token F1 mà không ngắt pipeline.
- **Lý do:** Đảm bảo tính ổn định và khả năng tái hiện (reproducibility) của pipeline trên mọi môi trường thử nghiệm.
- **Bằng chứng quyết định phù hợp:** Script `run_corruption_flow.py` vẫn chạy thành công 100% với Exit code 0 ngay cả khi không có kết nối internet hoặc thiếu LLM API Key.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u25ba' in position 0: character maps to <undefined>`
- **Lệnh hoặc bước tái hiện:** Chạy `python script/demo_agent.py` trên môi trường Windows PowerShell.
- **Nguyên nhân gốc:** Bảng mã mặc định của Windows console là CP1252, không hỗ trợ hiển thị các ký tự unicode pointer `►` hoặc tiếng Việt có dấu.
- **Cách xử lý:** Thêm `sys.stdout.reconfigure(encoding='utf-8')` ở đầu entrypoint script và thay các ký tự pointer unicode bằng ký tự chuẩn ASCII.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/demo_agent.py --state corrupted` thành công với Exit code 0.
- **Điều học được:** Luôn chú ý đến tính tương thích bảng mã I/O trên đa nền tảng (Windows/Linux/macOS) khi phát triển CLI script.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** Crossref API trả về JSON thô ➔ `parse_crossref_payload` chuẩn hóa thành `PaperRecord` lưu tại `data/raw/` ➔ `build_clean_dataframe` lọc bài ngắn, chuẩn hóa text và tạo `text_for_embedding` lưu tại `data/clean/` ➔ `LocalEmbeddingIndex.build` mã hóa vector bằng MiniLM và nạp vào ChromaDB collection.
2. **Evaluation set và ground-truth IDs:** `testset.py` sinh 60 câu hỏi từ tập clean gốc, lưu câu hỏi kèm `ground_truth_doc_ids` vào `data/eval/test_set.json`. Khi đánh giá, hệ thống kiểm tra xem bài báo mà RAG Agent tìm được có chứa `ground_truth_doc_ids` hay không để tính Retrieval Hit Rate.
3. **Quality checks vs Freshness monitoring:** Quality checks đo đạc tính toàn vẹn (completeness, uniqueness, validity) của các cột dữ liệu; trong khi Freshness monitoring đo tính thời sự (`age_days`) so với ngưỡng 180 ngày.
4. **Vì sao phải dùng cùng test set cho 3 pha:** Giữ nguyên test set 60 câu hỏi giúp tạo ra môi trường kiểm thử cố định (controlled environment), chứng minh chính xác sự suy giảm hiệu năng do nhiễu dữ liệu và mức độ phục hồi sau khi repair.
5. **Repair được xem là thành công khi:** Quality Gate chuyển lại trạng thái `PASSED`, Freshness chuyển lại `FRESH`, và các chỉ số Hit Rate (100%), Token F1 (42.57%) khôi phục 100% về mức Baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 100.00% | 66.67% | 100.00% | Hit rate giảm 33.33% khi mất bài báo và phục hồi 100% |
| `mean_token_f1` | 42.57% | 28.27% | 42.57% | Token F1 giảm do tóm tắt bị rỗng hoặc nhiễu text |
| `judge_accuracy` | 35.56% | 24.44% | 35.56% | Đánh giá của Judge khôi phục trọn vẹn sau khi repair |
| `mean_judge_score` | 2.38 / 5 | 1.93 / 5 | 2.38 / 5 | Điểm trung bình tăng lại 0.45 điểm sau khi khôi phục |
| Quality checks | PASSED | FAILED | PASSED | Bắt chính xác 3 bài trùng ID và 2 bài rỗng tóm tắt |
| Freshness status | FRESH | STALE | FRESH | Phát hiện chính xác bài báo quá hạn 180 ngày |

### Kết luận từ số liệu

1. **[Data corruption] ➔ [Quality FAILED / STALE] ➔ [Retrieval Hit Rate giảm từ 100% ➔ 66.67%]**: Sự cố dữ liệu tác động trực tiếp khiến RAG Agent truy xuất sai bài báo.
2. **[Repair action] ➔ [Quality PASSED / FRESH] ➔ [Retrieval Hit Rate khôi phục 100%]**: Quy trình đọc từ raw snapshot đã phục hồi hoàn hảo hiệu năng hệ thống.

**Corruption ảnh hưởng rõ nhất:** Kịch bản *Drop Latest Records* và *Blank Summary* ảnh hưởng lớn nhất vì khiến Agent không thể tìm được context hoặc trả lời câu lệnh mặc định "Insufficient evidence".

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Kiến trúc modular và việc duy trì Raw Snapshot (`data/raw/`) là yếu tố quyết định để hệ thống có khả năng tự phục hồi.
2. **Về Data Quality/Observability:** Cần chủ động giám sát dữ liệu bằng Quality Gates thay vì chờ phàn nàn từ phía người dùng RAG.
3. **Về ảnh hưởng dữ liệu tới RAG:** Chất lượng dữ liệu quyết định giới hạn trên (upper bound) chất lượng câu trả lời của LLM Agent.

### Nếu có thêm thời gian

Tích hợp mô hình LLM Local hoàn toàn offline (dùng Ollama `llama3`) cho bước Judge Evaluation để loại bỏ hoàn toàn sự phụ thuộc vào internet và API key bên ngoài.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lưu Quang Linh  
**Ngày xác nhận:** 2026-08-06