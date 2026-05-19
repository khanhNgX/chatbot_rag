# INSTRUCTIONS.md

> Rulebook triển khai **Chatbot RAG hỏi đáp thủ tục nhập học** với kiến trúc hierarchical chunking + metadata filtering + conversational query rewriting + hybrid retrieval.
>
> Tài liệu này được viết để dùng trực tiếp trong **Cursor**, **Claude Code**, hoặc các **AI Coding Agent** tương tự. Agent phải xem đây là tài liệu chỉ đạo chính.

---

## 1. Project Identity

- **Project Name:** `Enrollment Procedure RAG Assistant`
- **Domain:** Hỏi đáp thủ tục nhập học đại học
- **Primary Language:** Tiếng Việt
- **Target Users:** thí sinh / tân sinh viên / phụ huynh / cán bộ hỗ trợ
- **Primary Objective:** xây dựng chatbot RAG có khả năng trả lời chính xác, có căn cứ, hiểu được ngữ cảnh hội thoại nhiều lượt, và xử lý đúng các tham chiếu điều hướng kiểu `Phần 1`, `Bước 1`, `B1 của Phần 4`, `hạn nộp`, `nộp ở đâu`, `cần giấy tờ gì`.

### 1.1. Project-Specific Context

Dữ liệu trung tâm hiện tại là tài liệu thủ tục nhập học 2025, có cấu trúc rõ ràng:

- **Level 0**: tóm tắt toàn bộ quy trình
- **Level 1**: section lớn, ví dụ `PHẦN 1`, `PHẦN 2`, `PHẦN 3`, `PHẦN 4`
- **Level 2**: step bên trong section, ví dụ `B1`, `B2`, `B3`, `B4` trong `PHẦN 4`
- **Level 3**: các leaf chunks chứa thông tin tự do, lưu ý, mốc thời gian, khoản phí, giấy tờ, địa điểm, điều kiện

Ví dụ cấu trúc hiện tại của tài liệu gốc:

- `PHẦN 1`: Tra cứu danh sách trúng tuyển
- `PHẦN 2`: Xác nhận nhập học trực tuyến
- `PHẦN 3`: Nộp học phí, lệ phí, bảo hiểm, khám sức khỏe
- `PHẦN 4`: Chuẩn bị và nộp hồ sơ
  - `B1`: Chuẩn bị hồ sơ scan PDF
  - `B2`: Chuẩn bị ảnh chân dung
  - `B3`: Upload hồ sơ / ảnh
  - `B4`: Nộp hồ sơ trực tiếp tại trường

### 1.2. Core Problem to Solve

Hệ thống phải xử lý đúng những truy vấn nhập nhằng về điều hướng, ví dụ:

- `Phần 1 của thủ tục nhập học là gì?`
- `Bước 1 của thủ tục nhập học là gì?`
- `Bước 1 của phần 4 là gì?`
- `Ở bước 1 cần làm gì?`
- `Hạn upload hồ sơ là khi nào?`
- `Em cần nộp giấy tờ gì khi nhập học?`

Trong đó:

- `Bước 1 của toàn bộ thủ tục nhập học` phải map sang **section-level** `phan_1`
- `Bước 1 của phần 4` phải map sang **local step** `b1_phan_4`

=> Hệ thống bắt buộc phải có:

- **hierarchical chunk tree**
- **metadata taxonomy**
- **navigation ontology**
- **query rewrite từ chat history**
- **hybrid retrieval**
- **parent expansion**
- **grounded answer generation**

---

## 2. Final Product Goal

### 2.1. Functional Goal

Xây dựng một chatbot backend có thể:

1. ingest tài liệu thủ tục nhập học
2. chunk theo cấu trúc phân cấp
3. gán metadata có kiểm soát
4. index để hỗ trợ hybrid retrieval
5. rewrite câu hỏi dựa trên history hội thoại
6. resolve đúng scope điều hướng `global section` vs `local step`
7. retrieve chunk phù hợp sau đó lấy parent chunk (loại bỏ những parent bị trùng) vào context
8. sinh câu trả lời đủ ý tường minh, đúng scope, grounded vào tài liệu
9. có khả năng trace/debug từng bước retrieval

### 2.2. Non-Functional Goal

- dễ debug
- dễ mở rộng cho tài liệu năm 2026, 2027...
- dễ đánh giá offline
- không phụ thuộc hoàn toàn vào phán đoán tự do của LLM
- đủ cấu trúc để agent có thể code theo phase nhỏ

---

## 3. Tech Stack

### 3.1. Core Backend

- **Python 3.11+**
- **FastAPI**
- **Pydantic v2**
- **Uvicorn**
- **Poetry** hoặc **uv**

### 3.2. Retrieval & RAG

- **Qdrant** hoặc **pgvector** cho vector store
- **BM25** qua:
  - OpenSearch / Elasticsearch, hoặc
  - local BM25 cho giai đoạn PoC
- **Hybrid retrieval** = BM25 + vector + metadata filter
- **Reciprocal Rank Fusion (RRF)** hoặc weighted fusion cho hợp nhất điểm
- **Reranker**: optional nhưng rất khuyến khích ở Phase sau

### 3.3. LLM Roles

Hệ thống nên có 3 vai trò LLM online/offline rõ ràng:

- **LLM-Chunk-Metadata**
  - đọc chunk đã tách
  - gán metadata semantic từ ontology
  - chạy **offline / batch**

- **LLM-Query-Rewriter**
  - nhận history + user query mới
  - rewrite thành standalone query
  - sinh `QueryFrame`
  - chạy **online**

- **LLM-Answer-Generator**
  - nhận retrieved chunks + parent chunks + rewritten query
  - sinh answer grounded
  - chạy **online**

> Navigation resolver không được giao toàn bộ cho LLM. Đây là logic deterministic + rule-based + alias-aware.

### 3.4. Storage

- **PostgreSQL**:
  - session logs
  - query traces
  - eval records
  - chunk registry metadata
- **Redis**: optional cache
- **Local/Object storage** cho raw docs, processed docs, chunks, eval fixtures

### 3.5. Observability & Evaluation

- structured logging JSON
- trace per request
- optional Langfuse / Helicone
- custom evaluation scripts

---

## 4. System Architecture

### 4.1. High-Level Flow

```text
Raw Documents
 -> Parser
 -> Hierarchical Chunker
 -> Metadata Labeler (LLM offline)
 -> Chunk Store + BM25 Index + Vector Index

Chat History + New Query
 -> Query Rewriter (LLM)
 -> QueryFrame Builder
 -> Navigation Resolver
 -> Metadata Filter Builder
 -> Hybrid Retrieval
 -> Parent Expansion
 -> Context Builder
 -> Answer Generator (LLM)
 -> Response + Citation + Debug Trace
```

### 4.2. Runtime Data Flow

#### A. Ingestion Flow

1. Nạp tài liệu gốc
2. Parse theo heading / section / step / list / note
3. Tạo chunk tree
4. Gắn quan hệ parent-child
5. Gán metadata structure
6. Gọi LLM gán metadata semantic
7. Validate output
8. Sinh embeddings
9. Index vào BM25 + vector store

#### B. Online Query Flow

1. nhận `chat_history + user_query`
2. gọi **LLM-Query-Rewriter**
3. lấy `rewritten_query + QueryFrame`
4. gọi **Navigation Resolver**
5. build `RetrievalPlan`
6. chạy hybrid retrieval
7. chọn top chunks
8. expand parent level 1 nếu cần
9. build context package
10. gọi **LLM-Answer-Generator**
11. trả answer + references + trace

---

## 5. Source-Aware Design from Current Enrollment Document

### 5.1. Known Canonical Navigation Targets

```text
root
├─ lv0_summary
├─ phan_1                # tra cứu danh sách trúng tuyển
├─ phan_2                # xác nhận nhập học
├─ phan_3                # nộp học phí / lệ phí / BHYT
└─ phan_4                # chuẩn bị và nộp hồ sơ
   ├─ b1_phan_4          # chuẩn bị hồ sơ scan PDF
   ├─ b2_phan_4          # chuẩn bị ảnh chân dung
   ├─ b3_phan_4          # upload hồ sơ
   └─ b4_phan_4          # nộp hồ sơ trực tiếp
```

### 5.2. Known Metadata Groups

Hệ thống hiện phải hỗ trợ ít nhất các nhóm sau:

- `TOPIC_KEYWORDS`
- `ACTION_KEYWORDS`
- `TIME_ENTITIES`
- `NAV_ALIASES`

Ví dụ canonical topic IDs:

- `tra_cuu_ket_qua`
- `xac_nhan_nhap_hoc`
- `hoc_phi`
- `bao_hiem_y_te`
- `kham_suc_khoe`
- `ho_so_so`
- `anh_the`
- `giay_to_tot_nghiep`
- `hoc_ba`
- `giay_to_uu_tien`
- `giay_to_ca_nhan`
- `ho_so_quan_su`
- `ho_so_dang_doan`
- `tai_khoan_bidv`
- `lich_nop_ho_so`
- `dia_diem_nop`
- `ky_tuc_xa`
- `tuan_sinh_hoat`
- `thoi_khoa_bieu`
- `chuong_trinh_dac_biet`
- `lien_he_ho_tro`

Ví dụ canonical action IDs:

- `tra_cuu`
- `xac_nhan`
- `chuyen_khoan`
- `scan_tai_lieu`
- `upload_ho_so`
- `nop_truc_tiep`
- `chup_anh`
- `dang_ki_ktx`
- `cong_chung`

Ví dụ canonical time IDs:

- `deadline_xac_nhan_nhap_hoc`
- `deadline_nop_hoc_phi`
- `deadline_upload_ho_so`
- `ngay_nop_truc_tiep`
- `ngay_bat_dau_hoc`
- `tuan_sinh_hoat_dau_nam`
- `deadline_bo_sung_ho_so`
- `thoi_gian_nop_chinh_thuc`

### 5.3. Required Navigation Rules

Bắt buộc encode rule sau:

- `bước 1 của thủ tục nhập học` -> `phan_1`
- `bước 2 của thủ tục nhập học` -> `phan_2`
- `bước 3 của thủ tục nhập học` -> `phan_3`
- `bước 4 của thủ tục nhập học` -> `phan_4`

Đồng thời:

- `bước 1 của phần 4` -> `b1_phan_4`
- `b1 phần hồ sơ` -> `b1_phan_4`
- `upload hồ sơ` -> ưu tiên `b3_phan_4`
- `nộp trực tiếp` -> ưu tiên `b4_phan_4`

Resolver phải dùng đồng thời:

1. alias match
2. recent chat state
3. explicit section mention
4. fallback to global process rule

---

## 6. Repository Structure

```text
project-root/
├─ app/
│  ├─ api/
│  │  └─ v1/
│  │     ├─ endpoints/
│  │     │  ├─ chat.py
│  │     │  ├─ ingest.py
│  │     │  ├─ retrieval.py
│  │     │  └─ eval.py
│  │     └─ router.py
│  │
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ constants.py
│  │  ├─ exceptions.py
│  │  └─ logging.py
│  │
│  ├─ domain/
│  │  ├─ schemas/
│  │  │  ├─ chunk.py
│  │  │  ├─ query_frame.py
│  │  │  ├─ retrieval_plan.py
│  │  │  ├─ retrieved_context.py
│  │  │  └─ answer.py
│  │  └─ enums/
│  │     ├─ levels.py
│  │     ├─ nav_types.py
│  │     └─ task_types.py
│  │
│  ├─ ingestion/
│  │  ├─ parsers/
│  │  │  ├─ base.py
│  │  │  ├─ txt_parser.py
│  │  │  ├─ pdf_parser.py
│  │  │  └─ docx_parser.py
│  │  ├─ chunking/
│  │  │  ├─ hierarchical_chunker.py
│  │  │  ├─ section_extractor.py
│  │  │  ├─ step_extractor.py
│  │  │  └─ chunk_tree_builder.py
│  │  ├─ metadata/
│  │  │  ├─ ontology.py
│  │  │  ├─ labeler.py
│  │  │  ├─ alias_registry.py
│  │  │  ├─ validators.py
│  │  │  └─ normalizers.py
│  │  └─ pipelines/
│  │     └─ ingest_pipeline.py
│  │
│  ├─ retrieval/
│  │  ├─ bm25/
│  │  │  └─ searcher.py
│  │  ├─ vector/
│  │  │  └─ searcher.py
│  │  ├─ hybrid/
│  │  │  ├─ rank_fusion.py
│  │  │  ├─ hybrid_retriever.py
│  │  │  └─ scoring.py
│  │  ├─ filters/
│  │  │  └─ metadata_filter_builder.py
│  │  ├─ resolver/
│  │  │  ├─ navigation_resolver.py
│  │  │  ├─ scope_resolver.py
│  │  │  ├─ retrieval_strategy.py
│  │  │  └─ parent_expander.py
│  │  └─ pipelines/
│  │     └─ retrieval_pipeline.py
│  │
│  ├─ llm/
│  │  ├─ clients/
│  │  │  ├─ base.py
│  │  │  └─ openai_client.py
│  │  ├─ prompts/
│  │  │  ├─ metadata_labeler.md
│  │  │  ├─ query_rewriter.md
│  │  │  └─ answer_generator.md
│  │  ├─ tasks/
│  │  │  ├─ metadata_label_task.py
│  │  │  ├─ query_rewrite_task.py
│  │  │  └─ answer_generation_task.py
│  │  └─ parsers/
│  │     ├─ json_output_parser.py
│  │     └─ schema_validators.py
│  │
│  ├─ chat/
│  │  ├─ history_manager.py
│  │  ├─ session_state.py
│  │  └─ turn_builder.py
│  │
│  ├─ evaluation/
│  │  ├─ datasets/
│  │  ├─ metrics/
│  │  ├─ runners/
│  │  └─ reports/
│  │
│  └─ main.py
│
├─ data/
│  ├─ raw/
│  ├─ processed/
│  ├─ chunks/
│  ├─ metadata/
│  ├─ indexes/
│  └─ eval/
│
├─ scripts/
│  ├─ bootstrap_ontology.py
│  ├─ ingest_documents.py
│  ├─ build_indexes.py
│  ├─ run_local_eval.py
│  └─ export_debug_cases.py
│
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ e2e/
│  └─ fixtures/
│
├─ docs/
│  ├─ architecture.md
│  ├─ ontology.md
│  ├─ retrieval_rules.md
│  ├─ prompt_contracts.md
│  └─ evaluation_plan.md
│
├─ .env.example
├─ pyproject.toml
├─ README.md
└─ INSTRUCTIONS.md
```

---

## 7. Canonical Schemas

### 7.1. Chunk Schema

```json
{
  "chunk_id": "hus2025_phan4_b1_leaf_01",
  "doc_id": "hus_nhaphoc_2025",
  "level": 3,
  "parent_id": "hus2025_phan4_b1",
  "ancestor_ids": ["hus2025_root", "hus2025_phan4", "hus2025_phan4_b1"],
  "order_path": [4, 1, 1],
  "canonical_nav_id": "b1_phan_4",
  "nav_type": "local_step_leaf",
  "section_id": "phan_4",
  "step_id": "b1_phan_4",
  "title": "Chuẩn bị hồ sơ scan PDF",
  "content": "...",
  "topic_tags": ["ho_so_so", "giay_to_tot_nghiep", "hoc_ba", "giay_to_uu_tien"],
  "action_tags": ["scan_tai_lieu"],
  "time_tags": ["deadline_upload_ho_so"],
  "nav_aliases": ["b1 phần 4", "bước 1 phần hồ sơ"],
  "micro_summary": "Chuẩn bị một file PDF duy nhất chứa giấy tờ theo đúng thứ tự.",
  "has_deadline": true,
  "has_actionable_steps": true,
  "entities": {
    "dates": ["2025-08-28T17:00:00+07:00"],
    "money": [],
    "locations": [],
    "programs": []
  }
}
```

### 7.2. QueryFrame Schema

```json
{
  "rewritten_query": "Trong phần 4 của thủ tục nhập học, bước 1 cần chuẩn bị hồ sơ gì?",
  "language": "vi",
  "is_followup": true,
  "scope": "local_section",
  "task_type": "ask_documents",
  "nav_target_type": "local_step",
  "nav_target_candidates": ["b1_phan_4"],
  "topic_candidates": ["ho_so_so", "giay_to_tot_nghiep", "hoc_ba"],
  "action_candidates": ["scan_tai_lieu"],
  "time_candidates": ["deadline_upload_ho_so"],
  "needs_parent_context": true,
  "confidence": 0.93
}
```

### 7.3. RetrievalPlan Schema

```json
{
  "mode": "hybrid",
  "bm25_enabled": true,
  "vector_enabled": true,
  "metadata_filters": {
    "section_id": ["phan_4"],
    "step_id": ["b1_phan_4"],
    "topic_tags": ["ho_so_so"]
  },
  "preferred_levels": [2, 3],
  "top_k": 8,
  "parent_expansion": {
    "enabled": true,
    "target_parent_levels": [1, 2],
    "max_parent_chunks": 2
  },
  "ambiguity_mode": false,
  "debug_reason": "explicit local step detected from rewritten query"
}
```

### 7.4. Answer Payload Schema

```json
{
  "answer": "string",
  "citations": [
    {
      "chunk_id": "string",
      "title": "string"
    }
  ],
  "used_parent_chunks": ["string"],
  "confidence": 0.0,
  "needs_human_review": false
}
```

---

## 8. Prompt Contracts

### 8.1. LLM-Chunk-Metadata Prompt Contract

#### Purpose

Đọc **một chunk đã tách sẵn**, sau đó:

- chọn metadata labels từ ontology có sẵn
- gán `topic_tags`, `action_tags`, `time_tags`, `nav_aliases`
- tạo `micro_summary`
- không được phát minh label ngoài ontology

#### Required Input

- raw chunk text
- structural metadata hiện có
- ontology label lists
- optional parent title / section title

#### Required Output

- JSON hợp lệ theo schema
- labels chỉ lấy từ ontology
- confidence per group

#### Hard Rules

- không được thêm label mới ngoài ontology
- nếu không chắc, trả mảng rỗng và confidence thấp
- không rewrite nội dung chunk
- không suy diễn ngoài nội dung chunk và structural hints

#### Prompt Skeleton

```text
You are a metadata labeling engine.
Given a chunk and the allowed ontology labels, assign the best matching labels.
Only choose labels from the ontology.
Return valid JSON only.
```

### 8.2. LLM-Query-Rewriter Prompt Contract

#### Purpose

Nhận:

- chat history gần nhất
- câu hỏi mới của user

Sau đó:

- rewrite câu hỏi thành standalone query đầy đủ nghĩa
- suy ra `QueryFrame`
- phát hiện follow-up, scope, nav target candidates, topic candidates

#### Required Input

- last N turns chat history
- latest user query
- optional ontology aliases

#### Required Output

- JSON hợp lệ theo `QueryFrame`

#### Hard Rules

- phải ưu tiên giữ đúng ý định user hiện tại
- không bịa thêm yêu cầu mà user không hỏi
- nếu query mơ hồ, vẫn phải đưa candidate hợp lý + giảm confidence
- phải phân biệt global process step và local section step nếu history đủ mạnh

#### Prompt Skeleton

```text
You are a conversational query rewriting engine for an enrollment RAG system.
Rewrite the user's latest question into a standalone Vietnamese query.
Then produce a structured QueryFrame JSON.
Use chat history to resolve references like "bước 1", "phần này", "mục trên", "ở đâu", "hạn nộp".
Do not answer the question.
Return valid JSON only.
```

### 8.3. LLM-Answer-Generator Prompt Contract

#### Purpose

Nhận:

- rewritten query
- retrieved chunks
- parent chunks
- retrieval trace ngắn

Sau đó:

- sinh câu trả lời grounded
- ưu tiên ngắn gọn, đúng scope
- nêu rõ thiếu dữ liệu nếu context không đủ

#### Required Input

- query
- list retrieved chunks
- list parent chunks
- citation identifiers

#### Required Output

- JSON hoặc structured answer object

#### Hard Rules

- chỉ trả lời dựa trên context được cung cấp
- không suy diễn ngoài nguồn
- nếu có nhiều bước hoặc nhiều giấy tờ, trình bày có cấu trúc
- nếu câu hỏi hỏi một bước cụ thể, không lan man sang toàn bộ quy trình
- nếu context không đủ, nói rõ chưa đủ thông tin

#### Prompt Skeleton

```text
You are the final answer generator for an enrollment procedure RAG chatbot.
Answer only from the provided retrieved context.
Prefer concise Vietnamese answers.
If the query asks about a specific section or step, stay within that scope.
If information is insufficient, say so explicitly.
```

---

## 9. Retrieval Rules

### 9.1. Retrieval Priority Rules

1. Nếu query có `nav_target_type = section` rõ ràng:
   - retrieve trực tiếp chunk level 1 tương ứng
2. Nếu query có `nav_target_type = local_step` rõ ràng:
   - retrieve chunk level 2 tương ứng
   - kéo parent level 1
3. Nếu query hỏi một topic cụ thể như `học phí`, `BHYT`, `ký túc xá`:
   - filter theo metadata tags trước
   - retrieve ở level 2/3
   - promote section parent nếu cần
4. Nếu query hỏi overview toàn bộ:
   - ưu tiên level 0 và level 1
5. Nếu query mơ hồ:
   - nới filter
   - retrieve top-k hybrid
   - expand parent có kiểm soát

### 9.2. Parent Expansion Rules

- chỉ expand parent nếu:
  - query là follow-up
  - query target là leaf/local step
  - answer cần hiểu section context
- không bơm quá nhiều parent chunk
- mặc định tối đa:
  - `max_parent_chunks = 2`
  - `max_total_context_chunks = 8`

### 9.3. Ambiguity Rules

Nếu query là `bước 1 là gì?`:

- nếu history gần nhất đang nói về `phan_4` -> `b1_phan_4`
- nếu history không rõ -> fallback `phan_1`
- phải đánh dấu `ambiguity_mode = true` nếu confidence thấp

Nếu query là `phần này cần giấy tờ gì?`:

- history phải quyết định `phần này` là section nào
- nếu history chưa đủ, retrieve broader section candidates

### 9.4. Ranking Rules

Nên log riêng các thành phần điểm:

- `bm25_score`
- `vector_score`
- `metadata_match_score`
- `fusion_score`
- `parent_bonus`

---

## 10. Milestones

# Phase 0 — Bootstrap & Project Skeleton

## Goal

Khởi tạo bộ khung repo, config, logging, schema foundation.

## Tasks

- [ ] Khởi tạo repo và dependency manager
- [ ] Tạo cấu trúc thư mục chuẩn
- [ ] Tạo `.env.example`
- [ ] Tạo `app/main.py`
- [ ] Tạo health check endpoint
- [ ] Tạo `config.py`, `logging.py`, `exceptions.py`
- [ ] Thiết lập formatter + linter + pre-commit
- [ ] Tạo README run local

## Definition of Done

- server chạy local
- lint pass
- health endpoint hoạt động
- cấu trúc repo đúng như tài liệu này

### Refactor tracking (legacy Flask codebase)

- [x] Baseline gap check against `docs/ONTOLOGY.md`, `docs/PROMPT_CONTRACTS.md`, `docs/EVAL_DATASET_SPEC.md`
  - note: sử dụng kiến trúc hiện tại (`app.py` + `phase*.py`), không rewrite sang skeleton FastAPI.
- [x] Chốt phạm vi refactor theo thứ tự Phase 0 -> Phase 1 -> Phase 2...
  - note: mọi thay đổi ontology/schema/contract sẽ làm theo hướng additive + backward-compatible.

---

# Phase 1 — Ontology, Canonical IDs & Schema Contracts

## Goal

Chốt schema và ontology để mọi phần còn lại bám vào.

## Tasks

- [ ] Tạo `app/ingestion/metadata/ontology.py`
- [ ] Khai báo toàn bộ topic/action/time/nav IDs hiện tại
- [ ] Tạo alias registry cho `phan_1..phan_4` và `b1_phan_4..b4_phan_4`
- [ ] Tạo enum cho `level`, `nav_type`, `task_type`, `scope`
- [ ] Tạo schema `ChunkMetadata`
- [ ] Tạo schema `QueryFrame`
- [ ] Tạo schema `RetrievalPlan`
- [ ] Tạo validator cho labels ngoài ontology
- [ ] Viết fixtures cho 30 câu query mẫu
- [ ] Tạo docs/ontology.md

## Definition of Done

- schema compile được
- ontology import được trong code
- query fixtures cover các case `Phần 1`, `Bước 1`, `B1 Phần 4`, `upload hồ sơ`, `học phí`, `KTX`
- mọi canonical IDs đã được version hóa rõ ràng

---

# Phase 2 — Hierarchical Chunking Pipeline

## Goal

Xây parser và chunker tạo chunk tree bám sát tài liệu nhập học hiện tại.

## Tasks

- [ ] Tạo parser TXT
- [ ] Xây section extractor nhận diện `PHẦN X`
- [ ] Xây step extractor nhận diện `B1`, `B2`, ...
- [ ] Tạo `chunk_tree_builder.py`
- [ ] Tạo level 0 summary chunk
- [ ] Tạo level 1 section chunks
- [ ] Tạo level 2 step chunks
- [ ] Tạo level 3 leaf chunks cho bullet/note/list/details
- [ ] Gắn parent/ancestor/order_path
- [ ] Xuất chunk JSONL để inspect
- [ ] Viết unit tests cho parser/chunker

## Definition of Done

- tài liệu mẫu được parse đúng thành cây chunk
- `phan_4` có đúng `b1_phan_4..b4_phan_4`
- chunk tree inspect được bằng JSONL
- tests pass

---

# Phase 3 — Offline Metadata Labeling

## Goal

Dùng LLM gán metadata semantic cho chunk.

## Tasks

- [ ] Tạo prompt `metadata_labeler.md`
- [ ] Tạo task `metadata_label_task.py`
- [ ] Ép output JSON schema
- [ ] Validate labels chỉ thuộc ontology
- [ ] Gắn confidence per field
- [ ] Tạo `micro_summary`
- [ ] Thêm retry giới hạn nếu parse output lỗi
- [ ] Log raw prompt + raw response cho debug
- [ ] Chạy labeling batch cho tài liệu mẫu
- [ ] Manual review ít nhất 50 chunk quan trọng
- [ ] Tạo report precision sơ bộ

## Definition of Done

- >95% output parse được
- labels trọng yếu hợp lý
- không có label lạ ngoài ontology
- có report lỗi labeling

---

# Phase 4 — Indexing & Hybrid Search Base

## Goal

Index chunk vào BM25 + vector store và hỗ trợ hybrid search.

## Tasks

- [ ] Tạo embedding generator
- [ ] Tạo vector indexing pipeline
- [ ] Tạo BM25 indexing pipeline
- [ ] Gắn metadata filterable fields
- [ ] Tạo `bm25/searcher.py`
- [ ] Tạo `vector/searcher.py`
- [ ] Tạo `rank_fusion.py`
- [ ] Tạo `hybrid_retriever.py`
- [ ] Log score breakdown
- [ ] Tạo smoke test search query

## Definition of Done

- search được bằng BM25, vector, hybrid
- filter metadata hoạt động
- top-k trả về có score breakdown
- smoke tests pass

---

# Phase 5 — Query Rewrite & QueryFrame Generation

## Goal

Viết lại query theo history chat và sinh QueryFrame đúng schema.

## Tasks

- [ ] Tạo prompt `query_rewriter.md`
- [ ] Tạo task `query_rewrite_task.py`
- [ ] Gắn schema parser cho `QueryFrame`
- [ ] Support references: `phần này`, `bước này`, `mục trên`, `ở đâu`, `hạn nộp`
- [ ] Support follow-up questions
- [ ] Tạo confidence score
- [ ] Viết fallback nếu query rewrite fail
- [ ] Tạo test set multi-turn conversations
- [ ] Đánh giá thủ công ít nhất 50 case
- [ ] Log `original_query -> rewritten_query`

## Definition of Done

- QueryFrame tạo hợp lệ
- follow-up resolution hoạt động chấp nhận được
- case `bước 1` có thể dùng history để resolve
- logs đầy đủ

### Refactor tracking (legacy Flask codebase)

- [x] Enforce `answer_generator_v1` JSON contract trong `phase5_llm_generation.py`
  - added strict parser/validator cho schema: `answer`, `used_chunk_ids`, `grounded`, `uncertainty_note`, `followup_suggestions`.
- [x] Thêm repair retry 1 lần + fallback deterministic có trace
  - implemented `_repair_answer_contract_once(...)` và return `trace` trong `LLMGenerator.generate(...)`.

---

# Phase 6 — Navigation Resolver & RetrievalPlan Builder

## Goal

Giải đúng ambiguity global/local và build retrieval plan có kiểm soát.

## Tasks

- [ ] Tạo `scope_resolver.py`
- [ ] Tạo `navigation_resolver.py`
- [ ] Tạo `retrieval_strategy.py`
- [ ] Xây alias matching
- [ ] Encode rules `buoc_1_toan_quy_trinh -> phan_1`
- [ ] Encode rules `b1_phan_4 -> local step`
- [ ] Tạo `RetrievalPlan`
- [ ] Xây `metadata_filter_builder.py`
- [ ] Tạo ambiguity mode
- [ ] Ghi `debug_reason` cho mọi decision
- [ ] Regression tests cho ambiguity cases

## Definition of Done

- resolve đúng phần lớn case `Phần 1` vs `Bước 1`
- RetrievalPlan giải thích được bằng `debug_reason`
- metadata filter builder tạo filter hợp lệ
- regression tests pass

---

# Phase 7 — Parent Expansion & Context Builder

## Goal

Tạo context package gọn nhưng đủ thông tin cho model answer.

## Tasks

- [ ] Tạo `parent_expander.py`
- [ ] Xác định max parent chunks
- [ ] Xác định khi nào cần parent
- [ ] Tạo `retrieved_context.py`
- [ ] Gộp retrieved chunks + parent chunks
- [ ] Loại bỏ chunk trùng nội dung
- [ ] Giới hạn token budget
- [ ] Tạo unit tests cho parent expansion

## Definition of Done

- context builder không phình quá mức
- leaf chunk có thể kéo đúng parent
- không duplicate ngữ cảnh vô ích

---

# Phase 8 — Answer Generator

## Goal

Sinh câu trả lời grounded, đúng scope, có thể trích dẫn.

## Tasks

- [ ] Tạo prompt `answer_generator.md`
- [ ] Tạo task `answer_generation_task.py`
- [ ] Bắt buộc model bám context được cung cấp
- [ ] Tạo answer payload schema
- [ ] Hỗ trợ format answer ngắn gọn, có cấu trúc
- [ ] Hỗ trợ citations theo `chunk_id` / title
- [ ] Xử lý trường hợp thiếu thông tin
- [ ] Xử lý câu hỏi quá mơ hồ
- [ ] Viết integration tests
- [ ] Manual review 50 câu hỏi thường gặp

## Definition of Done

- answer grounded
- không bịa ngoài context
- citations hoạt động
- integration tests pass

---

# Phase 9 — Evaluation Harness

## Goal

Đo chất lượng từng lớp thay vì chỉ nhìn answer cuối.

## Tasks

- [ ] Tạo bộ eval queries
- [ ] Gắn expected nav target
- [ ] Gắn expected metadata labels
- [ ] Gắn expected retrieved chunk ids
- [ ] Tạo metrics cho rewrite
- [ ] Tạo metrics cho resolver
- [ ] Tạo metrics cho retrieval
- [ ] Tạo metrics cho answer grounding
- [ ] Tạo `run_local_eval.py`
- [ ] Xuất report CSV/JSON
- [ ] Phân loại lỗi theo nhóm

## Definition of Done

- có thể chạy eval lặp lại
- biết pipeline hỏng ở bước nào
- so sánh được nhiều phiên bản prompt / retrieval logic

---

# Phase 10 — Production Readiness

## Goal

Chuẩn bị staging/production.

## Tasks

- [ ] timeout cho mọi external call
- [ ] retry chiến lược cho LLM API
- [ ] rate limiting
- [ ] caching nếu cần
- [ ] structured monitoring
- [ ] Dockerfile
- [ ] CI lint + tests
- [ ] staging deploy guide
- [ ] smoke tests sau deploy

## Definition of Done

- chạy staging ổn định
- có monitoring cơ bản
- lỗi external call được kiểm soát

---

## 11. File-by-File Build Order for AI Agent

Agent nên triển khai theo đúng thứ tự sau, không nhảy cóc nếu chưa hoàn tất phần nền.

### Step Group A — Foundations

1. `app/core/config.py`
2. `app/core/logging.py`
3. `app/domain/enums/*.py`
4. `app/domain/schemas/chunk.py`
5. `app/domain/schemas/query_frame.py`
6. `app/domain/schemas/retrieval_plan.py`
7. `app/ingestion/metadata/ontology.py`

### Step Group B — Ingestion

8. `app/ingestion/parsers/base.py`
9. `app/ingestion/parsers/txt_parser.py`
10. `app/ingestion/chunking/section_extractor.py`
11. `app/ingestion/chunking/step_extractor.py`
12. `app/ingestion/chunking/chunk_tree_builder.py`
13. `app/ingestion/chunking/hierarchical_chunker.py`

### Step Group C — Metadata

14. `app/ingestion/metadata/alias_registry.py`
15. `app/ingestion/metadata/validators.py`
16. `app/llm/prompts/metadata_labeler.md`
17. `app/llm/tasks/metadata_label_task.py`
18. `app/ingestion/metadata/labeler.py`

### Step Group D — Retrieval

19. `app/retrieval/bm25/searcher.py`
20. `app/retrieval/vector/searcher.py`
21. `app/retrieval/hybrid/rank_fusion.py`
22. `app/retrieval/filters/metadata_filter_builder.py`
23. `app/retrieval/resolver/scope_resolver.py`
24. `app/retrieval/resolver/navigation_resolver.py`
25. `app/retrieval/resolver/retrieval_strategy.py`
26. `app/retrieval/resolver/parent_expander.py`
27. `app/retrieval/pipelines/retrieval_pipeline.py`

### Step Group E — Query & Answer

28. `app/llm/prompts/query_rewriter.md`
29. `app/llm/tasks/query_rewrite_task.py`
30. `app/llm/prompts/answer_generator.md`
31. `app/llm/tasks/answer_generation_task.py`
32. `app/chat/history_manager.py`
33. `app/api/v1/endpoints/chat.py`

### Step Group F — Evaluation

34. `tests/fixtures/*`
35. `evaluation datasets`
36. `scripts/run_local_eval.py`

---

## 12. Coding Standards

### 12.1. General Rules

- code phải ưu tiên rõ nghĩa, dễ debug
- không nhồi quá nhiều logic vào một file
- mọi service phải có input/output schema rõ ràng
- mọi quyết định retrieval quan trọng phải có trace/debug_reason
- tránh hidden coupling giữa prompt và code mà không được tài liệu hóa

### 12.2. Python Rules

- PEP 8
- type hints cho mọi public function
- docstring cho class/service quan trọng
- pure functions khi hợp lý
- tránh side effects khó kiểm soát

### 12.3. Naming Rules

#### Functions

- `build_chunk_tree()`
- `label_chunk_metadata()`
- `rewrite_query_from_history()`
- `resolve_navigation_target()`
- `build_metadata_filters()`
- `generate_answer_from_context()`

#### Classes

- `ChunkMetadata`
- `QueryFrame`
- `RetrievalPlan`
- `HybridRetriever`
- `NavigationResolver`

#### Constants

- `DEFAULT_TOP_K`
- `MAX_PARENT_EXPANSION`
- `DEFAULT_QUERY_REWRITE_TIMEOUT_SEC`

### 12.4. Error Handling Rules

- cấm `except Exception: pass`
- mọi lỗi phải log có context
- với LLM output:
  - validate schema
  - nếu fail parse, retry giới hạn
  - nếu vẫn fail, fallback có kiểm soát
- với retrieval:
  - log query, filter, retrieved ids, scores
- với API:
  - trả lỗi sạch, không rò rỉ secrets

### 12.5. Testing Rules

- unit tests cho parser, resolver, metadata validators
- integration tests cho retrieval pipeline
- regression tests cho ambiguity cases
- prompt thay đổi phải chạy lại eval mini

---

## 13. Agent Instructions

### 13.1. Agent Must Treat This File as Source of Truth

Agent phải:

1. đọc file này trước khi code
2. bám phase hiện tại
3. không bỏ qua checklist
4. không đánh dấu task hoàn thành nếu chưa có bằng chứng
5. cập nhật tiến độ ngay trong checklist hoặc changelog tương ứng

### 13.2. Required Working Pattern

Khi làm việc, agent phải đi theo chu trình:

1. xác định Phase hiện tại
2. chọn **một task nhỏ cụ thể**
3. xác định file cần tạo/sửa
4. triển khai thay đổi tối thiểu đủ chạy
5. chạy test/lint liên quan
6. cập nhật checklist
7. ghi note ngắn về phần đã làm

### 13.3. Checklist Update Rule

Sau khi hoàn thành task:

- đổi `- [ ]` thành `- [x]`
- thêm note 1-2 dòng nếu task quan trọng

Ví dụ:

```md
- [x] Tạo `navigation_resolver.py`
  - implemented alias matching cho `phan_x` và `b1_phan_4`
  - added 14 regression tests for ambiguity cases
```

### 13.4. Change Safety Rule

Nếu sửa một trong các phần sau, agent bắt buộc phải kiểm tra tác động dây chuyền:

- ontology
- canonical IDs
- chunk schema
- query frame schema
- retrieval plan schema
- prompt contracts
- tests fixtures
- eval datasets

### 13.5. Do Not Do These Things

- không hardcode logic trong endpoint nếu đáng lẽ thuộc service/resolver
- không trộn prompt text trực tiếp vào business logic file
- không để label ngoài ontology lọt vào index
- không bỏ qua ambiguity cases `Phần 1` vs `Bước 1`
- không tối ưu performance quá sớm khi chưa ổn logic

---

## 14. Initial Backlog for Cursor / AI Agent

Agent nên bắt đầu ngay bằng backlog sau:

### Sprint A

- [ ] Tạo `app/domain/schemas/chunk.py`
- [ ] Tạo `app/domain/schemas/query_frame.py`
- [ ] Tạo `app/domain/schemas/retrieval_plan.py`
- [ ] Tạo `app/ingestion/metadata/ontology.py`
- [ ] Tạo `tests/fixtures/query_examples.json`

### Sprint B

- [ ] Tạo `txt_parser.py`
- [ ] Tạo `section_extractor.py`
- [ ] Tạo `step_extractor.py`
- [ ] Tạo `chunk_tree_builder.py`
- [ ] Tạo script export chunk JSONL

### Sprint C

- [ ] Tạo `metadata_labeler.md`
- [ ] Tạo `metadata_label_task.py`
- [ ] Tạo metadata validator
- [ ] Chạy thử labeling trên 10 chunk đầu tiên

### Sprint D

- [ ] Tạo `query_rewriter.md`
- [ ] Tạo `query_rewrite_task.py`
- [ ] Tạo `navigation_resolver.py`
- [ ] Tạo 20 test cases ambiguity

---

## 15. Definition of Success

Dự án được coi là thành công khi:

1. chatbot trả lời đúng phần lớn câu hỏi phổ biến về thủ tục nhập học
2. follow-up questions được rewrite đúng ngữ cảnh
3. case `Phần 1` vs `Bước 1` không còn gây sai retrieval nghiêm trọng
4. retrieval trace đủ rõ để debug
5. metadata filtering giúp giảm nhiễu thật sự
6. agent có thể tiếp tục phát triển codebase dựa trên file này mà không bị mơ hồ

---

## 16. Recommended Next Documents

Sau file này, nên tạo tiếp:

- `PROMPT_CONTRACTS.md`
- `ONTOLOGY.md`
- `RETRIEVAL_RULES.md`
- `EVAL_DATASET_SPEC.md`
- `API_SPEC.md`

