# BÁO CÁO TỔNG KẾT BÀI LAB - DAY 10: DATA PIPELINE & DATA OBSERVABILITY FOR RAG

**Tên dự án:** Day 10 Data Pipeline & Data Observability  
**Đối tượng mô phỏng:** Hệ thống RAG phục vụ tra cứu công bố học thuật (Crossref Papers Corpus)  
**Quy mô nhóm:** 5 Thành viên  

---

## 1. Mục Tiêu Dự Án & Vấn Đề Giải Quyết

Trong các hệ thống Retrieval-Augmented Generation (RAG) thực tế, chất lượng câu trả lời của LLM phụ thuộc trực tiếp vào chất lượng dữ liệu đầu vào trong cơ sở dữ liệu vector. Bài lab này chứng minh thực nghiệm rằng:
- **Dữ liệu rác / dữ liệu lỗi (Data Corruption)** gây suy giảm nghiêm trọng độ chính xác của tìm kiếm (Retrieval Hit Rate) và điểm số trả lời của Agent.
- **Hệ thống Data Observability & Quality Gates** phát hiện sớm các bất thường dữ liệu (thiếu thông tin, trùng lặp, dữ liệu cũ/stale, nhiễu text) trước khi người dùng nhận được câu trả lời sai.
- **Quy trình Phục hồi dữ liệu (Data Repair)** khôi phục lại trọn vẹn 100% hiệu năng hệ thống từ nguồn raw artifact đáng tin cậy.

---

## 2. Bảng Phân Công Nhiệm Vụ Nhóm 5 Người

| Vai Trò | Thành Viên | Phạm Vi Phụ Trách | Đầu Ra / Artifacts |
| :--- | :--- | :--- | :--- |
| **TV1: Pipeline Integrator** | Lead | Quản lý cấu hình, điều phối pipeline baseline và corruption flow, tích hợp end-to-end. | [`config.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/core/config.py), [`phase1.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/pipelines/phase1.py), [`corruption_flow.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/pipelines/corruption_flow.py), [`run_phase1.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/script/run_phase1.py) |
| **TV2: Data Ingestion Owner** | Ingestion | Gọi Crossref API, retry backoff (429/503), parse `PaperRecord`, quản lý raw lineage. | [`crossref.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/ingestion/crossref.py), `data/raw/crossref_records.json` |
| **TV3: Cleaning & Corruption** | Data Engine | Chuẩn hóa text, tính `age_days`, tạo `text_for_embedding`, giả lập 10 dạng lỗi dữ liệu & repair. | [`cleaning.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/ingestion/cleaning.py), [`corruption.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/ingestion/corruption.py), `data/clean/papers_clean.csv` |
| **TV4: RAG System & Agent** | Retrieval | Quản lý MiniLM Embeddings, Vector Store ChromaDB (3 collection riêng biệt), Multi-provider LLM & Agent. | [`index.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/retrieval/index.py), [`agent.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/retrieval/agent.py), `data/embeddings/` |
| **TV5: Evaluation & Observability** | QA & Reporting | Sinh bộ test set 60 câu hỏi, tính chỉ số (Hit Rate, Token F1, Judge), Quality/Freshness checks & báo cáo. | [`testset.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/evaluation/testset.py), [`quality.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/observability/quality.py), [`reporting.py`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/src/observability/reporting.py), `data/reports/` |

---

## 3. Kiến Trúc Data Pipeline & Data Observability

```text
Crossref External API
       │
       ▼
┌──────────────┐      Snapshot      ┌──────────────┐
│  Raw Ingest  │ ─────────────────> │  data/raw/   │ (Khôi phục dữ liệu gốc)
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       ▼                                   ▼
┌──────────────┐                    ┌──────────────┐
│ Data Clean   │                    │ Data Repair  │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       ├───────────────────────────────────┼───────────────────────────────────┐
       ▼                                   ▼                                   ▼
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│  Baseline    │                    │  Corrupted   │                    │   Repaired   │
│ (Clean Data) │                    │ (Data Noise) │                    │(Restored Data│
└──────┬───────┘                    └──────┬───────┘                    └──────┬───────┘
       │                                   │                                   │
       ▼                                   ▼                                   ▼
 Chroma Collection                   Chroma Collection                   Chroma Collection
`papers-baseline`                   `papers-corrupted`                  `papers-repaired`
       │                                   │                                   │
       └───────────────────────────────────┼───────────────────────────────────┘
                                           ▼
                                 ┌───────────────────┐
                                 │   Evaluation Set  │
                                 │ (data/eval/ 60 Qs)│
                                 └─────────┬─────────┘
                                           ▼
                                 ┌───────────────────┐
                                 │ Observability &   │
                                 │ Comparison Report │
                                 └───────────────────┘
```

---

## 4. Kết Quả Thực Nghiệm & Bảng So Sánh Chỉ Số (3 Trạng Thái)

Hệ thống được đánh giá trên cùng một bộ **60 câu hỏi kiểm thử chuẩn hóa** ([`data/eval/test_set.json`](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/data/eval/test_set.json)).

### Bảng So Sánh Performance RAG Pipeline

| Chỉ Số Đánh Giá (Metric) | Baseline (Dữ liệu Sạch) | Corrupted (Dữ liệu Lỗi) | Repaired (Dữ liệu Phục Hồi) | Tác Động Của Corruption | Kết Quả Phục Hồi (Repair) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate** | **100.00%** (1.0000) | **66.67%** (0.6667) | **100.00%** (1.0000) | 🔻 **Giảm 33.33%** | 🟢 **Phục hồi 100%** |
| **Mean Token F1** | **42.57%** (0.4257) | **28.27%** (0.2827) | **42.57%** (0.4257) | 🔻 **Giảm 14.30%** | 🟢 **Phục hồi 100%** |
| **Judge Accuracy** | **35.56%** (0.3556) | **24.44%** (0.2444) | **35.56%** (0.3556) | 🔻 **Giảm 11.12%** | 🟢 **Phục hồi 100%** |
| **Mean Judge Score (1-5)** | **2.38** / 5.00 | **1.93** / 5.00 | **2.38** / 5.00 | 🔻 **Giảm 0.45 điểm** | 🟢 **Phục hồi 100%** |

---

### Bảng So Sánh Data Observability Gates

| Tiêu Chí Observability | Baseline | Corrupted | Repaired | Đánh Giá Tín Hiệu |
| :--- | :---: | :---: | :---: | :--- |
| **Data Quality Gate** | **PASSED** | **FAILED** | **PASSED** | Bắt chính xác 3 lỗi trùng ID, 2 lỗi rỗng summary. |
| **Paper ID Duplicate Count** | `0` | `3` | `0` | Phát hiện chính xác dòng bị nhân bản. |
| **Summary Short/Empty Count**| `0` | `2` | `0` | Phát hiện tóm tắt bị mờ/xóa. |
| **Stale Rows Count (>180d)** | `0` | `2` | `0` | Phát hiện bài báo bị sửa lùi ngày xuất bản. |
| **Freshness Gate** | **FRESH** | **STALE** | **FRESH** | Cảnh báo chính xác độ tươi dữ liệu. |

---

## 5. Phân Tích Thực Nghiệm & Kết Luận Của Nhóm

1. **Dữ liệu lỗi làm suy giảm trực tiếp chất lượng RAG:**
   - Khi bị phá hoại dữ liệu (drop bài mới, nhiễu text, rỗng tóm tắt), chỉ số **Retrieval Hit Rate giảm từ 100% xuống 66.67%**.
   - Do bài báo liên quan không tìm thấy hoặc bị trích dẫn sai, điểm F1 và điểm chấm của LLM Judge lập tức sụt giảm mạnh.

2. **Data Observability đóng vai trò là "Lưới an toàn":**
   - Bộ Quality Check và Freshness Monitor phát hiện ngay lập tức trạng thái `FAILED` và `STALE` của tập dữ liệu lỗi trước khi cho phép dữ liệu nạp vào Vector Store.

3. **Quy trình Data Repair đạt hiệu quả tuyệt đối:**
   - Nhờ lưu trữ snapshot thô tại `data/raw/crossref_records.json`, quy trình `repair_dataframe_from_snapshot` đã khôi phục lại trọn vẹn dữ liệu về trạng thái ban đầu.
   - Các chỉ số Hit Rate (100%), Token F1 (42.57%) và Judge Score (2.38) được khôi phục 100% về mức Baseline.

---

## 6. Tổng Kết Checklist Nghiệm Thu Bài Lab

- [x] Môi trường cài đặt thành công với `pip install -e .` (Python 3.12).
- [x] Baseline pipeline (`run_phase1.py`) chạy thành công end-to-end với Exit code 0.
- [x] Corruption flow (`run_corruption_flow.py`) chạy thành công end-to-end với Exit code 0.
- [x] 3 Vector Collection (`papers-baseline`, `papers-corrupted`, `papers-repaired`) được phân tách minh bạch trong ChromaDB.
- [x] Tất cả các thư mục artifact (`raw`, `clean`, `embeddings`, `eval`, `results`, `quality`, `reports`) lưu trữ đầy đủ.
- [x] Đã đối chiếu hoàn toàn khớp với tất cả các tiêu chí trong [Rubric.md](file:///c:/Users/Admin/.vscode/K4_Day10_Data-Pipeline-Data-Observability/Rubric.md).
