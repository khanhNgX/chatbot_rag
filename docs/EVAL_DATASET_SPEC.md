# EVAL_DATASET_SPEC.md

> Đặc tả bộ dữ liệu đánh giá cho hệ thống chatbot RAG hỏi đáp thủ tục nhập học.
> Mục tiêu: đo được chất lượng của từng tầng hệ thống thay vì chỉ chấm câu trả lời cuối.

---

## 1. Evaluation Goals

Bộ eval phải giúp trả lời được các câu hỏi sau:

1. Chunking có giữ đúng cấu trúc section / step không?
2. Metadata labeling có gán đúng ontology không?
3. Query rewriting có phục hồi đúng ngữ cảnh hội thoại không?
4. Navigation resolver có phân biệt đúng:
   - `Phần 1`
   - `Bước 1 của toàn quy trình`
   - `Bước 1 của phần 4`
5. Retrieval có lấy đúng chunk và parent không?
6. Answer generator có grounded, đúng scope, không hallucinate không?

---

## 2. Evaluation Layers

Hệ thống phải được đánh giá theo 6 lớp:

1. **Chunking Eval**
2. **Metadata Labeling Eval**
3. **Query Rewrite Eval**
4. **Navigation Resolution Eval**
5. **Retrieval Eval**
6. **Answer Eval**

Không chỉ chấm answer cuối vì sẽ khó debug lỗi gốc.

---

## 3. Dataset Splits

### 3.1. Required Splits

- **dev_small**: 20–30 case để debug nhanh
- **dev_full**: 80–150 case để tuning
- **test_locked**: 50–100 case cố định, không dùng tune prompt thường xuyên
- **regression_cases**: các case từng lỗi trong quá khứ

### 3.2. Conversation Types

Bộ eval phải gồm cả:

- one-turn questions
- multi-turn conversations
- ambiguous follow-up
- explicit navigation queries
- topic-based factual questions
- schedule/time/location questions
- document requirement questions

---

## 4. Recommended File Structure

```text
data/eval/
├─ dev_small/
│  ├─ conversations.jsonl
│  ├─ retrieval_labels.jsonl
│  └─ answer_labels.jsonl
├─ dev_full/
│  ├─ conversations.jsonl
│  ├─ retrieval_labels.jsonl
│  └─ answer_labels.jsonl
├─ test_locked/
│  ├─ conversations.jsonl
│  ├─ retrieval_labels.jsonl
│  └─ answer_labels.jsonl
└─ regression_cases/
   └─ ambiguity_cases.jsonl
```

---

## 5. Example Record Types

## 5.1. Conversation Record

Mỗi mẫu hội thoại nên có format:

```json
{
  "conversation_id": "conv_0001",
  "turns": [
    {"role": "user", "text": "Phần 4 là gì?"},
    {"role": "assistant", "text": "Phần 4 là phần chuẩn bị hồ sơ..."},
    {"role": "user", "text": "Bước 1 là làm gì?"}
  ],
  "current_turn_index": 2,
  "language": "vi",
  "difficulty": "medium",
  "tags": ["followup", "local_step_resolution"]
}
```

## 5.2. Query Rewrite Label

```json
{
  "conversation_id": "conv_0001",
  "expected_rewritten_query": "Trong phần 4 của thủ tục nhập học, bước 1 cần chuẩn bị hồ sơ gì?",
  "acceptable_variants": [
    "Bước 1 trong phần 4 của thủ tục nhập học yêu cầu chuẩn bị hồ sơ nào?",
    "Trong phần hồ sơ nhập học, bước 1 cần làm gì?"
  ],
  "expected_query_frame": {
    "scope": "local_section",
    "nav_target_type": "local_step",
    "nav_target_candidates": ["b1_phan_4"],
    "task_type": "ask_documents"
  }
}
```

## 5.3. Retrieval Label

```json
{
  "conversation_id": "conv_0001",
  "expected_primary_chunk_ids": ["hus2025_phan4_b1"],
  "expected_parent_chunk_ids": ["hus2025_phan4"],
  "acceptable_alternative_chunk_ids": [],
  "must_include_metadata": {
    "canonical_nav_id": ["b1_phan_4"],
    "topic_tags": ["ho_so_so"]
  }
}
```

## 5.4. Answer Label

```json
{
  "conversation_id": "conv_0001",
  "must_cover_points": [
    "cần chuẩn bị file PDF duy nhất",
    "gồm giấy chứng nhận kết quả thi",
    "gồm giấy tốt nghiệp hoặc giấy chứng nhận tốt nghiệp",
    "gồm học bạ",
    "gồm giấy tờ ưu tiên nếu có"
  ],
  "must_not_say": [
    "nộp trực tiếp ở bước 1",
    "chụp ảnh ở bước 1"
  ],
  "answer_style": "direct_list"
}
```

---

## 6. Chunking Evaluation Spec

### 6.1. What to Check

- chunk có đúng `level` không
- `parent_id` có chính xác không
- `ancestor_ids` có đầy đủ không
- `canonical_nav_id` có đúng không
- chunk boundaries có hợp lý không

### 6.2. Suggested Metrics

- section boundary accuracy
- step boundary accuracy
- parent link accuracy
- chunk schema validity rate

### 6.3. Minimum Required Cases

Ít nhất phải có case cho:

- `phan_1`
- `phan_2`
- `phan_3`
- `phan_4`
- `b1_phan_4`
- `b2_phan_4`
- `b3_phan_4`
- `b4_phan_4`
- leaf chunks chứa timeline / note / địa điểm

---

## 7. Metadata Labeling Evaluation Spec

### 7.1. What to Check

- topic tags đúng
- action tags đúng
- time tags đúng
- nav_aliases hợp lệ
- micro_summary có đúng nội dung chính

### 7.2. Metrics

- exact match rate per label group
- precision / recall / F1 for:
  - topic_tags
  - action_tags
  - time_tags
- schema validity rate
- over-tag rate
- under-tag rate

### 7.3. Error Categories

- wrong topic
- missing topic
- wrong action
- wrong time
- invented label
- invalid JSON
- micro-summary misleading

---

## 8. Query Rewrite Evaluation Spec

### 8.1. What to Check

- rewritten query có self-contained không
- có khôi phục đúng referent từ history không
- có giữ đúng scope không
- có gán đúng nav candidates không

### 8.2. Metrics

- standalone completeness score
- nav target accuracy
- scope accuracy
- task_type accuracy
- ambiguity handling correctness

### 8.3. Critical Test Patterns

Phải có test cases cho:

1. `Bước 1 là gì?` sau khi nói về `Phần 4`
2. `Bước 1 là gì?` không có history
3. `Phần đó nộp khi nào?`
4. `Nó ở đâu?` sau câu trả lời về nộp hồ sơ trực tiếp
5. `Có cần học bạ không?`
6. `Nộp online trước hay trực tiếp trước?`

---

## 9. Navigation Resolution Evaluation Spec

### 9.1. What to Check

- resolver chọn đúng target
- có phân biệt global step và local step
- khi ambiguity cao có trả candidate list đúng không

### 9.2. Metrics

- top-1 nav target accuracy
- top-3 nav target recall
- ambiguity classification accuracy
- parent expansion correctness

### 9.3. Golden Ambiguity Cases

Các case bắt buộc phải có:

- `Bước 1 của thủ tục nhập học`
- `Bước 1 của phần 4`
- `Bước 1`
- `Phần 1`
- `Mục hồ sơ`
- `Bước cuối là gì?`
- `Sau khi nộp online thì làm gì tiếp?`

---

## 10. Retrieval Evaluation Spec

### 10.1. What to Check

- chunk đúng có nằm trong top-k không
- parent đúng có được expand không
- metadata filter có làm mất chunk đúng không
- hybrid search có cải thiện hơn bm25-only / vector-only không

### 10.2. Metrics

- Recall@1
- Recall@3
- Recall@5
- MRR
- NDCG@k
- parent inclusion rate
- metadata filter hit rate

### 10.3. Slice Metrics

Phải report theo lát cắt:

- by task type
- by ambiguity
- by navigation query
- by topic query
- by follow-up query
- by short query (<= 4 tokens)
- by long query

---

## 11. Answer Evaluation Spec

### 11.1. What to Check

- câu trả lời đúng nguồn
- không hallucinate
- đúng scope được hỏi
- đủ ý tối thiểu
- không nhầm giữa section và step

### 11.2. Metrics

- groundedness score
- faithfulness
- answer completeness
- scope correctness
- citation usefulness (nếu có citation)
- harmful hallucination rate

### 11.3. Human Review Rubric

Chấm 1–5 cho các tiêu chí:

- correctness
- completeness
- groundedness
- clarity
- scope alignment

---

## 12. Recommended Initial Test Set

## 12.1. One-Turn Cases

Ít nhất 15 case đầu tiên nên gồm:

1. Học phí kỳ 1 là bao nhiêu?
2. Hạn xác nhận nhập học là khi nào?
3. Nộp hồ sơ trực tiếp ở đâu?
4. Có cần học bạ không?
5. Ảnh thẻ yêu cầu như thế nào?
6. Có cần giấy khai sinh không?
7. Khi nào bắt đầu học?
8. Có đăng ký ký túc xá không?
9. Liên hệ hỗ trợ ở đâu?
10. Hạn upload hồ sơ là khi nào?
11. Bước 1 của thủ tục nhập học là gì?
12. Phần 4 là gì?
13. Bước 3 của phần 4 là gì?
14. Có cần giấy nghĩa vụ quân sự không?
15. Lịch nộp hồ sơ của ngành Toán học là khi nào?

## 12.2. Multi-Turn Cases

Ít nhất 10 case nhiều lượt:

1. User hỏi `Phần 4 là gì?` -> follow-up `Bước 1 là gì?`
2. User hỏi `Phần 3 là gì?` -> follow-up `Nộp bằng cách nào?`
3. User hỏi `Nộp online trước hay trực tiếp trước?` -> follow-up `Hạn online là khi nào?`
4. User hỏi `Có cần giấy tờ ưu tiên không?` -> follow-up `Nộp ở bước nào?`
5. User hỏi `Bắt đầu học khi nào?` -> follow-up `Trước đó có hoạt động gì không?`

---

## 13. Regression Suite Rules

Mỗi khi hệ thống fail một case thực tế:

1. thêm case đó vào `regression_cases`
2. ghi rõ:
   - symptom
   - root cause
   - fixed version
3. không đóng issue nếu chưa thêm regression test

Format gợi ý:

```json
{
  "case_id": "reg_0012",
  "query": "Bước 1 là gì?",
  "history_summary": "Earlier turns discussed phan_4",
  "expected_nav_target": "b1_phan_4",
  "bug_type": "wrong_global_vs_local_resolution",
  "fixed_in_version": "retrieval_logic_v3"
}
```

---

## 14. Annotation Guidelines

Người gán nhãn phải tuân thủ:

- bám vào ontology canonical IDs
- không gán theo cảm tính ngoài ontology
- nếu có nhiều cách diễn đạt đúng, dùng `acceptable_variants`
- nếu case mơ hồ thực sự, annotate ambiguity thay vì ép một đáp án duy nhất

---

## 15. Success Thresholds for MVP

Khuyến nghị ngưỡng tối thiểu cho MVP:

- metadata schema validity: >= 95%
- query rewrite scope accuracy: >= 85%
- navigation top-1 accuracy: >= 90%
- retrieval Recall@5: >= 90%
- answer groundedness: >= 90%
- hallucination rate: <= 5%

---

## 16. Recommended Implementation Order

1. Tạo `dev_small` 20–30 case
2. Viết evaluator cho rewrite + resolver
3. Viết evaluator cho retrieval
4. Viết evaluator cho answer
5. Chạy baseline lần đầu
6. Ghi report lỗi
7. Mở rộng `dev_full`
8. Khóa `test_locked`
