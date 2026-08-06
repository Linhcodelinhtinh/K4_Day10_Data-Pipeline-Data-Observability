# Báo cáo vai trò cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Văn Huy Hoàng |
| MSSV | 2A202601338 |
| Khóa/Lớp | K4 |
| Tên nhóm | 5AngryMen |
| Vai trò chính | Thành viên 4 — RAG System & Agent Owner |
| Repository | https://github.com/Linhcodelinhtinh/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Embedding backend | `src/retrieval/embeddings.py`: `MiniLMEmbeddings`, `load_embedding_model()`, `embed_texts()`, `embed_query()` | Danh sách `text_for_embedding`, model name và batch size | Vector embedding đã normalize, cùng dimension; deterministic fallback khi model không khả dụng | Hoàn thành |
| ChromaDB index và retrieval | `src/retrieval/index.py`: `LocalEmbeddingIndex`, `SearchResult` | DataFrame clean/corrupted/repaired và `Settings` | Ba collection độc lập, embedding manifest, semantic search và exact lookup | Hoàn thành |
| Multi-provider LLM | `src/retrieval/llm.py`: `build_llm()`, `generate()` | Provider, model, credential, prompt và generation settings | Interface chung cho Gemini, OpenAI, Anthropic, OpenRouter, Ollama và custom endpoint | Hoàn thành |
| RAG agent | `src/retrieval/agent.py`: `build_agent()`, `run_agent_question()` | `Settings`, một `LocalEmbeddingIndex` cố định và câu hỏi | Agent có semantic-search/lookup tools, câu trả lời kèm evidence `paper_id` | Hoàn thành |
| QA contract | `src/retrieval/qa.py`: `AnswerResult`, `answer_question()` | Question, settings, index và `top_k` | Answer, retrieved IDs/contexts/titles, provider, latency và collection | Hoàn thành |
| Retrieval tests | `tests/test_embeddings.py`, `test_retrieval.py`, `test_qa.py`, `test_agent.py` | Fake embedding/LLM, temporary ChromaDB và 10 corrupted datasets | 31 automated tests | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp collection reset | TV1 — `src/pipelines/phase1.py`, `corruption_flow.py` | Các pipeline truyền `reset=True`, có thể chạy lại mà không ghi nhầm collection khác |
| Tương thích pandas 3 | TV1/TV3 — corruption flow | Ưu tiên clean JSON thay vì CSV để giữ `authors` và `categories` ở kiểu list khi tạo corruption |
| Tích hợp với evaluator | TV5 — `src/evaluation/metrics.py` | Giữ nguyên contract `answer_question(question, settings, index, top_k=None)`, không yêu cầu TV5 sửa cách gọi |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Cache và batch MiniLM embeddings | `src/retrieval/embeddings.py` | Model chỉ load một lần/process, batch mặc định 32, kiểm tra text rỗng và dimension | `python -m pytest tests/test_embeddings.py -v` |
| Tạo persistent vector index | `src/retrieval/index.py`, `data/chroma/` | `papers-baseline`, `papers-corrupted`, `papers-repaired` tách biệt | Load manifest rồi kiểm tra `collection.count()` |
| Semantic search và lookup | `LocalEmbeddingIndex.search()`, `lookup_by_paper_id()`, `lookup_by_title()` | Kết quả có rank, cosine distance, similarity score, paper ID và metadata | `python -m pytest tests/test_retrieval.py -v` |
| Multi-provider abstraction | `src/retrieval/llm.py` | Sáu provider dùng chung validation, timeout, max tokens và error handling | Provider-mapping tests trong `test_agent.py` |
| Agent có nguồn chứng minh | `src/retrieval/agent.py` | Prompt giới hạn theo corpus/collection và bắt buộc citation `paper_id` | Gemini agent smoke test trả evidence `10.55041/isjem07213` |
| QA ổn định cho evaluation | `src/retrieval/qa.py` | Deterministic mode mặc định; agent mode tùy chọn; deduplicate retrieved logical IDs | `python -m pytest tests/test_qa.py -v` |

Output cụ thể của phần việc là ba embedding manifest trong `data/embeddings/` và persistent ChromaDB trong `data/chroma/`. Lần xác minh tích hợp ghi nhận 24 documents ở baseline, 23 ở corrupted và 24 ở repaired. Commit bàn giao chính là `43a8314` với 31/31 tests pass.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần biến trường `text_for_embedding` của TV3 thành vector, lưu vector và metadata vào ChromaDB, sau đó cung cấp một contract retrieval ổn định cho QA, agent và evaluator. Hệ thống phải tách biệt ba trạng thái dữ liệu để corrupted index không ghi đè baseline, đồng thời vẫn chạy được với dữ liệu rỗng một phần, metadata null, paper ID lỗi hoặc duplicate rows.

### Cách triển khai

Embedding sử dụng `sentence-transformers/all-MiniLM-L6-v2`, normalize vector và xử lý theo batch. Model được cache bằng `lru_cache`; khi model không tải được, hệ thống dùng deterministic 384-dimensional fallback để pipeline offline vẫn có thể smoke test. Text rỗng được xử lý tại index theo thứ tự `text_for_embedding → title → skip + warning`, nhờ đó retrieval không tự xây lại cleaning logic.

Mỗi row được lưu vào Chroma với record ID `paper_id::row_index`. `paper_id` gốc tiếp tục nằm trong metadata để evaluator đối chiếu ground-truth document IDs. Cách này cho phép scenario duplicate có nhiều document vật lý nhưng cùng logical paper ID. Search sử dụng cosine distance, trả rank và score được giới hạn trong `[0, 1]`. QA deduplicate theo logical paper ID trước khi trả context cho evaluator.

Agent được tạo với đúng một `LocalEmbeddingIndex`; tools đóng trên index đó nên agent không thể tự chuyển sang collection khác. System prompt yêu cầu chỉ dùng retrieved context, nói rõ khi thiếu evidence và trả kết quả theo format `Answer`/`Evidence` có `paper_id`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | DataFrame có `paper_id`, `title`, `summary`, `text_for_embedding`, `authors_joined`, `categories_joined`, `published`, `age_days`, `abs_url`, `pdf_url` |
| Output | Persistent Chroma collection, embedding manifest JSON, `SearchResult` và `AnswerResult` |
| Module phụ thuộc | `core.config`, clean/corrupted/repaired artifacts của TV3, Sentence Transformers, ChromaDB và LangChain |
| Module sử dụng output | Baseline/corruption pipelines của TV1; evaluation metrics và reports của TV5 |
| Điều kiện lỗi cần xử lý | Empty text/query, null metadata, duplicate paper ID, collection đã tồn tại, thiếu API key, provider timeout và model không khả dụng |

### Cách xác minh

```bash
source .venv/bin/activate
python -m pytest -q
python -m pip check
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Tests pass; ba collection độc lập; semantic search trả paper ID; agent trả answer có evidence; pipeline sinh metrics cho cả ba trạng thái.
- **Kết quả thực tế:** `31 passed`, không có dependency bị hỏng; baseline/corrupted/repaired lần lượt có 24/23/24 documents; retrieval hit rate lần lượt là `1.0000/0.6667/1.0000`.
- **Artifact/log:** `data/embeddings/`, `data/chroma/`, `data/results/*_metrics.json`, `data/results/*_answers.json` và commit `43a8314`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chroma yêu cầu document ID duy nhất, trong khi corruption flow cố ý tạo duplicate rows có cùng `paper_id`.
- **Các phương án đã cân nhắc:** Dùng trực tiếp `paper_id` làm Chroma ID; loại duplicate trước khi index; hoặc tạo physical record ID riêng nhưng giữ logical ID trong metadata.
- **Phương án đã chọn:** Dùng `record_id = paper_id::row_index`, đồng thời lưu `paper_id` gốc trong metadata.
- **Lý do:** Dùng trực tiếp `paper_id` làm collection add thất bại khi duplicate; loại duplicate sẽ che mất corruption mà observability cần phát hiện. Physical ID riêng giữ được toàn bộ dữ liệu lỗi, còn logical ID vẫn phục vụ retrieval-hit và lineage.
- **Bằng chứng quyết định phù hợp:** Test `duplicate_rows` index đủ 28 records dù có 4 logical ID trùng; toàn bộ 10 corruption scenario build/search không crash.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Gemini trả `404 NOT_FOUND` với thông báo model `gemini-2.5-flash` không còn khả dụng cho user mới.
- **Lệnh hoặc bước tái hiện:** Gọi `generate()` với `LLM_PROVIDER=gemini`, model `gemini-2.5-flash` và một prompt smoke test ngắn.
- **Nguyên nhân gốc:** Model ID trong `.env` local đã cũ so với model mà tài khoản hiện tại được Google cấp quyền sử dụng.
- **Cách xử lý:** Đồng bộ `.env` local sang `gemini-3.5-flash` theo `.env.example`; không thay đổi hoặc commit API key. Đồng thời giữ lỗi provider được bọc dưới dạng `RuntimeError` dễ đọc.
- **Cách xác minh sau khi sửa:** `generate()` trả `GEMINI_SMOKE_OK`; RAG agent gọi semantic-search tool và trả evidence `paper_id: 10.55041/isjem07213`.
- **Điều học được:** Credential hợp lệ chưa đảm bảo model ID còn được provider hỗ trợ; smoke test cần kiểm tra cả authentication, model availability và output token budget.

## 7. Hiểu biết về luồng end-to-end

1. Crossref trả metadata paper; TV2 lưu raw response và raw records. TV3 chuẩn hóa thành clean DataFrame và tạo `text_for_embedding`. Role 4 embed trường này bằng MiniLM, lưu vector cùng metadata vào ChromaDB, sau đó cung cấp search/lookup cho QA và agent.
2. Evaluation set chứa question, ground truth và `ground_truth_doc_ids`. Với mỗi câu hỏi, evaluator kiểm tra retrieved IDs có chứa ID đúng hay không để tính retrieval hit, đồng thời so sánh answer với ground truth bằng token F1 và judge.
3. Quality checks đo tính đầy đủ, hợp lệ và duy nhất của dữ liệu như null, summary ngắn và duplicate ID. Freshness monitoring tập trung vào tuổi dữ liệu, ngày mới nhất/cũ nhất và số row vượt ngưỡng 180 ngày.
4. Baseline, corrupted và repaired phải dùng cùng test set, top-k và evaluator để thay đổi metric phản ánh thay đổi dữ liệu, không phải do câu hỏi hoặc cấu hình đánh giá thay đổi.
5. Repair thành công khi dữ liệu được tái tạo từ raw snapshot, quality/freshness trở lại PASS/FRESH và các metric retrieval/answer phục hồi về baseline. Trong artifact hiện tại, repaired khôi phục đủ 24 rows và toàn bộ bốn metric chính trở về đúng baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6667 | 1.0000 | Corruption làm mất 15/45 retrieval hits; repair phục hồi toàn bộ |
| `mean_token_f1` | 0.4257 | 0.2827 | 0.4257 | Answer overlap giảm 0.1429 rồi trở lại baseline |
| `judge_accuracy` | 0.3556 | 0.2444 | 0.3556 | Giảm 0.1111; hiện dùng fallback heuristic judge |
| `mean_judge_score` | 2.3778 | 1.9333 | 2.3778 | Giảm khoảng 0.44 điểm rồi phục hồi |
| Quality checks | PASS | FAIL | PASS | Corrupted có 3 duplicate IDs, 2 summary ngắn và 2 stale rows |
| Freshness status | FRESH | STALE | FRESH | Corrupted có ngày cũ nhất `2010-01-01`; repair đưa stale rows về 0 |

### Kết luận từ số liệu

1. Drop latest records và corrupt paper IDs → ground-truth documents biến mất hoặc không còn khớp ID → retrieval hit rate giảm từ `1.0000` xuống `0.6667`, kéo token F1 và judge metrics giảm theo.
2. Reload raw snapshot và chạy cleaning/index lại → duplicate, short summary và stale rows được loại bỏ → quality/freshness trở lại PASS/FRESH và toàn bộ metric repaired bằng baseline.

Corruption ảnh hưởng rõ nhất là `drop_latest`: bốn paper bị xóa tương ứng 12/15 retrieval misses vì mỗi paper có ba câu hỏi summary/authors/date. Ba misses còn lại liên quan một paper có `paper_id` bị đổi thành tiền tố `INVALID_CORRUPTED_ID/`. Đây là bằng chứng trực tiếp rằng document identity và availability tác động mạnh hơn các lỗi metadata không tham gia câu hỏi cụ thể.

Kết quả khác kỳ vọng là baseline retrieval hit đạt `1.0` nhưng answer metrics vẫn khá thấp (`token_f1=0.4257`, `judge_accuracy=0.3556`). Kiểm tra answer artifacts cho thấy cả 45 samples ở mỗi trạng thái dùng fallback heuristic judge do LLM evaluator không khả dụng, và Ragas đang bị tắt. Vì vậy các metric này đủ để so sánh tương đối ba trạng thái nhưng chưa đại diện cho một LLM judge hoàn chỉnh.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data contract giữa cleaning và retrieval quan trọng hơn việc gọi model: chỉ cần sai kiểu metadata, rỗng `text_for_embedding` hoặc trùng document ID là index có thể lỗi hoặc cho kết quả sai.
2. Tách collection và giữ manifest theo từng trạng thái giúp truy vết, chạy lại và chứng minh corruption/repair mà không làm mất baseline.
3. Retrieval đúng document chưa đảm bảo answer tốt; cần đánh giá riêng retrieval hit, answer quality, judge status và xem evaluator có đang fallback hay không.

### Nếu có thêm thời gian

Tôi sẽ bổ sung hybrid retrieval (dense embedding + lexical DOI/title search), reranker và evaluation riêng cho từng corruption type. Cải thiện được đo bằng retrieval hit theo từng question type, MRR/nDCG, latency p95 và chênh lệch metric khi bật LLM judge/Ragas thật thay cho fallback heuristic.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Huy Hoàng
**Ngày xác nhận:** 2026-08-06
