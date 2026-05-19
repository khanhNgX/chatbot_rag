# PROMPT_CONTRACTS.md

> Prompt contracts chuẩn hóa cho các vai trò LLM trong hệ thống chatbot RAG hỏi đáp thủ tục nhập học.
> Mục tiêu: đảm bảo output có cấu trúc, dễ validate, dễ debug, giảm hallucination và nhất quán giữa các lần gọi model.

---

## 1. General Principles

### 1.1. Core Rules

Tất cả prompt trong hệ thống phải tuân thủ các nguyên tắc sau:

- Output phải ưu tiên **JSON có schema cố định** khi là task trung gian.
- Không cho model tự tạo nhãn mới ngoài ontology đã định nghĩa.
- Không cho model suy luận quá phạm vi tài liệu khi task chỉ là tagging / rewriting / retrieval planning.
- Luôn tách:
  - **instruction**
  - **input data**
  - **output contract**
  - **failure behavior**
- Luôn có bước validate output sau khi model trả về.

### 1.2. Model Roles

Hệ thống có 3 vai trò LLM chính:

- **LLM-A**: Metadata Labeler cho chunk ingestion
- **LLM-B**: Query Rewriter + Query Framer cho runtime
- **LLM-C**: Answer Generator cho runtime

> Có thể dùng cùng một model backend cho nhiều vai trò, nhưng prompt contract phải tách riêng theo nhiệm vụ.

---

## 2. Prompt Contract — LLM-A Metadata Labeler

### 2.1. Purpose

Dùng để đọc một chunk đã được tách từ tài liệu và gán metadata semantic từ tập ontology có sẵn.

### 2.2. Input

Input tối thiểu cho model:

- `document_context`
- `chunk_metadata_basic`
- `chunk_text`
- `allowed_topic_keywords`
- `allowed_action_keywords`
- `allowed_time_entities`
- `allowed_nav_aliases`

### 2.3. Responsibilities

Model phải:

1. Đọc nội dung chunk.
2. Chọn các nhãn phù hợp từ ontology.
3. Tạo `micro_summary` ngắn, trung tính, chính xác.
4. Xác định đây có phải chunk chứa:
   - deadline
   - actionable steps
   - payment info
   - location info
   - document requirement
5. Không được phát minh nhãn ngoài danh sách cho phép.

### 2.4. Hard Constraints

Model **must not**:

- tạo label ngoài ontology
- tự dịch hay đổi canonical ID
- suy ra metadata không có căn cứ trong chunk
- trả text dài tự do thay vì JSON
- bịa ngày, số tiền, địa điểm nếu chunk không có

### 2.5. Output JSON Schema

```json
{
  "topic_tags": ["string"],
  "action_tags": ["string"],
  "time_tags": ["string"],
  "nav_aliases": ["string"],
  "micro_summary": "string",
  "has_deadline": true,
  "has_actionable_steps": false,
  "has_payment_info": false,
  "has_location_info": false,
  "has_document_requirements": false,
  "entities": {
    "dates": ["string"],
    "money": ["string"],
    "locations": ["string"],
    "programs": ["string"],
    "people_or_units": ["string"]
  },
  "confidence": {
    "topic_tags": 0.0,
    "action_tags": 0.0,
    "time_tags": 0.0,
    "overall": 0.0
  }
}
```

### 2.6. Recommended System Prompt

```text
You are a metadata labeling engine for hierarchical enrollment-procedure documents.

Your task is to assign metadata to exactly one chunk.
You MUST only choose labels from the provided ontology lists.
You MUST return valid JSON only.
Do not invent new labels.
Do not explain your reasoning.
Do not infer facts not supported by the chunk text.

When confidence is low, return fewer labels rather than guessing.
```

### 2.7. Recommended User Prompt Template

```text
DOCUMENT CONTEXT:
{document_context}

BASIC CHUNK METADATA:
{chunk_metadata_basic}

CHUNK TEXT:
{chunk_text}

ALLOWED TOPIC KEYWORDS:
{allowed_topic_keywords}

ALLOWED ACTION KEYWORDS:
{allowed_action_keywords}

ALLOWED TIME ENTITIES:
{allowed_time_entities}

ALLOWED NAV ALIASES:
{allowed_nav_aliases}

Return JSON with the exact schema.
```

### 2.8. Validation Rules

Sau khi model trả về:

- tất cả tag phải thuộc ontology
- `micro_summary` không quá 2 câu
- `confidence` phải nằm trong `[0,1]`
- loại bỏ tag trùng lặp
- nếu JSON lỗi -> retry tối đa 1 lần với prompt repair

### 2.9. Fallback Strategy

Nếu model fail:

1. retry với prompt repair
2. nếu vẫn fail -> dùng rule-based fallback:
   - regex ngày tháng
   - regex số tiền
   - alias match
   - keyword exact/near match
3. đánh dấu `labeling_source = fallback_rule`

---

## 3. Prompt Contract — LLM-B Query Rewriter + Query Framer

### 3.1. Purpose

Tổng hợp `chat history + previous assistant answer + current user query` để:

1. viết lại câu hỏi thành standalone query rõ nghĩa
2. sinh `QueryFrame` phục vụ retrieval

### 3.2. Responsibilities

Model phải:

- hiểu tham chiếu hội thoại như:
  - `bước 1`
  - `phần này`
  - `mục kia`
  - `hạn nộp là khi nào`
  - `nó ở đâu`
- phân biệt:
  - global process step
  - local step in a section
  - section-level question
  - free-topic question
- đề xuất candidates, không ép chắc chắn nếu còn ambiguity

### 3.3. Important Domain Rule

Trong dự án này:

- `Phần 1`, `Phần 2`, `Phần 3`, `Phần 4` là **top-level sections**
- `B1`, `B2`, `B3`, `B4` là **local steps bên trong Phần 4**
- Cụm `Bước 1 của thủ tục nhập học` thường map tới **global step = phan_1**
- Cụm `Bước 1 của phần 4` map tới **local step = b1_phan_4**

Model không được tự ý collapse 2 ngữ cảnh này thành một nếu query/history không hỗ trợ.

### 3.4. Input

- `chat_history`
- `last_assistant_message` (optional)
- `current_user_query`
- `allowed_navigation_ids`
- `allowed_topic_keywords`
- `allowed_action_keywords`
- `allowed_time_entities`

### 3.5. Output JSON Schema

```json
{
  "rewritten_query": "string",
  "language": "vi",
  "is_followup": true,
  "scope": "global | local_section | followup_from_history | ambiguous",
  "task_type": "ask_what | ask_how | ask_when | ask_where | ask_payment | ask_documents | ask_navigation | ask_contact | ask_schedule",
  "nav_target_type": "section | global_process_step | local_step | free_topic | unknown",
  "nav_target_candidates": ["string"],
  "topic_candidates": ["string"],
  "action_candidates": ["string"],
  "time_candidates": ["string"],
  "needs_parent_context": true,
  "should_apply_metadata_filter": true,
  "ambiguity_notes": ["string"],
  "confidence": 0.0
}
```

### 3.6. Recommended System Prompt

```text
You are a query rewriting and query framing engine for a Vietnamese enrollment-procedure RAG chatbot.

Your job is to rewrite the user's latest message into a standalone query using chat history, then produce a structured query frame.

Important:
- Return JSON only.
- Preserve the user's intended meaning.
- Do not answer the question.
- Do not invent facts.
- Prefer candidate lists when ambiguity exists.
- Respect the navigation ontology:
  - top-level process sections: phan_1, phan_2, phan_3, phan_4
  - local steps inside section 4: b1_phan_4, b2_phan_4, b3_phan_4, b4_phan_4
```

### 3.7. Recommended User Prompt Template

```text
CHAT HISTORY:
{chat_history}

LAST ASSISTANT MESSAGE:
{last_assistant_message}

CURRENT USER QUERY:
{current_user_query}

ALLOWED NAVIGATION IDS:
{allowed_navigation_ids}

ALLOWED TOPIC KEYWORDS:
{allowed_topic_keywords}

ALLOWED ACTION KEYWORDS:
{allowed_action_keywords}

ALLOWED TIME ENTITIES:
{allowed_time_entities}

Return JSON using the exact schema.
```

### 3.8. Special Handling Examples

#### Example A

History:
- User hỏi về `Phần 4`

Current query:
- `Bước 1 là làm gì?`

Expected framing:
- `is_followup = true`
- `scope = local_section`
- `nav_target_candidates = ["b1_phan_4"]`

#### Example B

No history

Current query:
- `Bước 1 của thủ tục nhập học là gì?`

Expected framing:
- `scope = global`
- `nav_target_type = global_process_step`
- `nav_target_candidates = ["phan_1"]`

#### Example C

Current query:
- `Hạn nộp hồ sơ online là khi nào?`

Expected framing:
- `task_type = ask_when`
- `topic_candidates` includes `ho_so_so`
- `time_candidates` may include `deadline_upload_ho_so`

### 3.9. Fallback Strategy

Nếu JSON lỗi hoặc confidence thấp:

1. retry 1 lần
2. fallback:
   - standalone query = current_user_query
   - candidates từ rule-based alias + keyword matcher
   - `scope = ambiguous`

---

## 4. Prompt Contract — Retrieval Planner (Optional Lightweight LLM or Rule-Guided)

> Thành phần này có thể không cần LLM nếu resolver code đủ tốt.
> Nếu dùng LLM, phải ép rất chặt và chỉ dùng như assistant cho retrieval planning.

### 4.1. Purpose

Nhận `QueryFrame` và gợi ý retrieval strategy.

### 4.2. Output JSON Schema

```json
{
  "primary_retrieval_mode": "metadata_first | hybrid_balanced | bm25_first | vector_first | navigation_direct",
  "target_levels": [1, 2, 3],
  "metadata_filters": {
    "topic_tags": ["string"],
    "action_tags": ["string"],
    "time_tags": ["string"],
    "canonical_nav_id": ["string"]
  },
  "should_expand_parent": true,
  "should_expand_siblings": false,
  "top_k_before_rerank": 20,
  "top_k_after_rerank": 8,
  "reason_short": "string"
}
```

### 4.3. Use Rule

Chỉ dùng nếu bạn thật sự muốn mô hình hóa strategy bằng LLM.
Nếu đã có resolver deterministic, ưu tiên resolver code.

---

## 5. Prompt Contract — LLM-C Answer Generator

### 5.1. Purpose

Sinh câu trả lời cuối cùng dựa trên:

- rewritten query
- retrieved chunks
- parent chunks
- retrieval trace tóm tắt

### 5.2. Responsibilities

Model phải:

- trả lời đúng trọng tâm query
- bám sát context được cung cấp
- không bịa thông tin ngoài nguồn
- khi thiếu dữ liệu phải nói rõ chưa thấy trong tài liệu
- ưu tiên trả lời rõ ràng, tiếng Việt tự nhiên, dễ đọc
- nếu có nhiều bước, trình bày tuần tự

### 5.3. Hard Constraints

Model **must not**:

- suy diễn ngoài context
- đưa khuyến nghị không có trong tài liệu
- trả lời sai scope do nhầm giữa section và step
- nói chắc chắn nếu retrieval có ambiguity cao

### 5.4. Input

- `rewritten_query`
- `original_user_query`
- `query_frame`
- `retrieved_chunks`
- `parent_chunks`
- `retrieval_trace_summary`
- `answer_style_guide`

### 5.5. Output Format

Có thể trả về text thuần hoặc JSON có cấu trúc tùy backend.
Khuyến nghị JSON nội bộ rồi render ra text ở tầng API.

#### Internal JSON

```json
{
  "answer": "string",
  "used_chunk_ids": ["string"],
  "grounded": true,
  "uncertainty_note": "string",
  "followup_suggestions": ["string"]
}
```

### 5.6. Recommended System Prompt

```text
You are the final answer generator for a Vietnamese enrollment-procedure chatbot.

Answer only from the provided context.
If the answer is not fully supported by the context, say so clearly.
Do not invent missing details.
Prefer concise, direct, user-friendly Vietnamese.
Respect the retrieval scope and the query frame.
```

### 5.7. Recommended User Prompt Template

```text
ORIGINAL USER QUERY:
{original_user_query}

REWRITTEN QUERY:
{rewritten_query}

QUERY FRAME:
{query_frame}

RETRIEVED CHUNKS:
{retrieved_chunks}

PARENT CHUNKS:
{parent_chunks}

RETRIEVAL TRACE SUMMARY:
{retrieval_trace_summary}

ANSWER STYLE GUIDE:
{answer_style_guide}

Return grounded answer only.
```

### 5.8. Answer Style Guide

- Trả lời ngắn gọn nhưng đủ ý.
- Nếu là câu hỏi về thủ tục nhiều bước:
  - liệt kê theo thứ tự
- Nếu là câu hỏi về thời gian:
  - nêu mốc thời gian rõ ràng
- Nếu là câu hỏi về giấy tờ:
  - liệt kê đúng tài liệu
- Nếu có ambiguity:
  - nêu ngắn gọn cách hiểu hiện tại
- Không dùng văn phong quá dài dòng

---

## 6. Prompt Versioning Rules

### 6.1. Version Naming

Mọi prompt phải có version:

- `metadata_labeler_v1`
- `query_rewriter_v1`
- `answer_generator_v1`

Khi sửa prompt, phải tăng version nếu thay đổi logic đáng kể.

### 6.2. Required Metadata

Mỗi lần gọi model nên log:

- prompt_version
- model_name
- latency_ms
- token_usage
- validation_pass
- retry_count

---

## 7. Testing Prompt Contracts

### 7.1. Metadata Labeler Tests

Phải có test cases cho:

- chunk về học phí
- chunk về hồ sơ
- chunk về deadline
- chunk về địa điểm
- chunk về step navigation

### 7.2. Query Rewriter Tests

Phải có test cases cho:

- follow-up query
- mơ hồ `bước 1`
- explicit `phần 4`
- query hỏi deadline
- query hỏi địa điểm
- query hỏi ngành học theo buổi

### 7.3. Answer Generator Tests

Phải có test cases cho:

- grounded answer
- thiếu dữ liệu
- ambiguity
- nhiều chunk cùng chủ đề
- parent expansion cases

---

## 8. Implementation Notes

- Không hard-code prompt string trực tiếp trong business logic file.
- Đặt prompt ở thư mục `app/llm/prompts/`.
- Tạo helper render prompt bằng template engine đơn giản hoặc format thuần.
- Tạo validator riêng cho từng output schema.

---

## 9. Minimal Build Order

1. Viết prompt contract cho Metadata Labeler
2. Viết validator cho output Metadata Labeler
3. Viết prompt contract cho Query Rewriter
4. Viết validator cho QueryFrame
5. Viết prompt contract cho Answer Generator
6. Viết eval fixtures cho từng prompt
7. Chạy test prompt với 20 case đầu tiên
