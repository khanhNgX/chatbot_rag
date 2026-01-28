# GIẢI PHÁP TOÀN DIỆN: RAG CHATBOT CHO THỦ TỤC HÀNH CHÍNH

## 📋 TỔNG QUAN KIẾN TRÚC

Hệ thống được chia thành 5 PHASE chính:
- **PHASE 1**: Document Processing & Chunking
- **PHASE 2**: Embedding & Storage
- **PHASE 3**: Query Processing & Retrieval
- **PHASE 4**: Prompt Engineering
- **PHASE 5**: LLM Generation & Post-processing

---

## 🔄 PHASE 1: DOCUMENT PROCESSING & CHUNKING

### Mục tiêu
Chia document thành các chunks có ý nghĩa thay vì split cố định theo token.

### Quy trình chi tiết

#### Bước 1: Parse Document Structure
```
Input: File TXT thủ tục nhập học
Output: Structured data với hierarchy rõ ràng

Phân tích:
- Nhận diện các PHẦN (1, 2, 3, 4)
- Nhận diện các bước (B1, B2, B3, B4)
- Tách các thông tin chi tiết (học phí, lịch, hồ sơ)
```

#### Bước 2: Extract Metadata
Trích xuất từ mỗi document:
- **Năm học**: 2024, 2025
- **Deadlines**: Tất cả các mốc thời gian
- **URLs**: Các link tra cứu, nộp hồ sơ
- **Contact info**: Email, phone, địa chỉ
- **Fees**: Các khoản phí chi tiết
- **Schedules**: Lịch nhập học theo ngành

#### Bước 3: Chunking Strategy (4 Levels)

**LEVEL 1: OVERVIEW CHUNK**
```json
{
  "chunk_id": "admission_2025_overview",
  "type": "overview",
  "year": 2025,
  "title": "Thủ tục nhập học 2025 - Tổng quan",
  "content": "Tóm tắt toàn bộ quy trình gồm 4 phần chính...",
  "total_sections": 4,
  "key_deadlines": ["30/8/2025", "28/8/2025"],
  "total_fee": 7019750
}
```

**LEVEL 2: SECTION CHUNKS**
```json
{
  "chunk_id": "admission_2025_section_1",
  "type": "section",
  "year": 2025,
  "section_number": 1,
  "title": "PHẦN 1: Tra cứu danh sách trúng tuyển",
  "content": "Tra cứu danh sách trúng tuyển (sau ngày 22/8/2025)...",
  "url": "https://tuyensinh.hus.vnu.edu.vn/tra-cuu-dai-hoc.html",
  "deadline": "sau ngày 22/8/2025",
  "parent_id": "admission_2025_overview",
  "next_section_id": "admission_2025_section_2"
}
```

**LEVEL 3: STEP CHUNKS**
```json
{
  "chunk_id": "admission_2025_section_4_step_1",
  "type": "step",
  "year": 2025,
  "section_number": 4,
  "step_number": 1,
  "title": "B1: Chuẩn bị hồ sơ",
  "content": "Chuẩn bị hồ sơ để thực hiện tạo file...",
  "required_documents": [
    "Giấy chứng nhận kết quả thi tốt nghiệp THPT năm 2025",
    "Giấy chứng nhận tốt nghiệp THPT",
    "Học bạ THPT"
  ],
  "deadline": "trước 17 giờ ngày 28/8/2025",
  "parent_id": "admission_2025_section_4",
  "next_step_id": "admission_2025_section_4_step_2",
  "tools_needed": ["Camscanner", "Microsoft Lens"]
}
```

**LEVEL 4: DETAIL CHUNKS**

*Fee Information Chunk:*
```json
{
  "chunk_id": "admission_2025_fees",
  "type": "fee_info",
  "year": 2025,
  "content": "Chi tiết các khoản phí sinh viên cần nộp",
  "fees": {
    "hồ sơ tài liệu": 50000,
    "sức khỏe": 180000,
    "bảo hiểm y tế": 789750,
    "học phí tạm thu": 6000000
  },
  "total_required": 7019750,
  "payment_period": {
    "start": "25/8/2025",
    "end": "05/9/2025"
  },
  "parent_id": "admission_2025_section_3"
}
```

*Schedule Chunk (per major):*
```json
{
  "chunk_id": "admission_2025_schedule_math",
  "type": "schedule",
  "year": 2025,
  "date": "28/8/2025",
  "day_of_week": "Thứ Năm",
  "time_slot": "morning",
  "time_range": "7:30-11:00",
  "major": "Toán học",
  "location": "Trường ĐH Khoa học Tự nhiên, 334 Nguyễn Trãi",
  "parent_id": "admission_2025_section_4"
}
```

*Document List Chunk:*
```json
{
  "chunk_id": "admission_2025_docs_immediate",
  "type": "document_list",
  "year": 2025,
  "submission_timing": "ngày nhập học",
  "documents": [
    {
      "name": "Giấy báo kết quả thi tốt nghiệp THPT năm 2025",
      "type": "bản chính",
      "required": true
    },
    {
      "name": "Giấy chứng nhận tốt nghiệp tạm thời",
      "type": "bản chính",
      "required": true,
      "note": "đối với thí sinh tốt nghiệp năm 2025"
    }
  ],
  "parent_id": "admission_2025_section_4"
}
```

### Lợi ích của Chunking Strategy này:
✅ Giữ nguyên ngữ cảnh logic
✅ Dễ filter theo năm, loại thông tin
✅ Trả lời được cả câu hỏi tổng quan lẫn chi tiết
✅ Có thể truy xuất parent/sibling để bổ sung ngữ cảnh

---

## 🎯 PHASE 2: EMBEDDING & STORAGE

### Quy trình Embedding

#### Bước 1: Prepare Content for Embedding
```
Cho mỗi chunk, tạo text để embed bằng cách kết hợp:

Template:
"[TYPE: {type}] [YEAR: {year}] {title}
{content}
Metadata: {key_metadata}"

Ví dụ:
"[TYPE: fee_info] [YEAR: 2025] Chi tiết học phí
Tiền làm hồ sơ: 50.000đ
Sức khỏe: 180.000đ
Bảo hiểm y tế: 789.750đ
Học phí học kỳ 1: 6.000.000đ
Tổng: 7.019.750đ
Metadata: payment_period=25/8/2025-05/9/2025"
```

#### Bước 2: Generate Embeddings
```
Sử dụng Embedding Model:
- OpenAI: text-embedding-3-small (1536 dims)
- OpenAI: text-embedding-3-large (3072 dims)
- Cohere: embed-multilingual-v3.0
- Local: Vietnamese-sbert

Input: Prepared text
Output: Vector embedding [0.123, -0.456, ...]
```

#### Bước 3: Store in Vector Database

**Lựa chọn Vector DB:**
- **ChromaDB**: Local, dễ setup, phù hợp POC
- **Pinecone**: Cloud, managed, scalable
- **Qdrant**: Open-source, performance cao
- **Weaviate**: GraphQL support, hybrid search built-in

**Schema lưu trữ:**
```python
{
  # Vector DB fields
  "id": "admission_2025_fees",
  "embedding": [0.123, -0.456, ...],  # Vector 1536 dims
  
  # Metadata for filtering
  "year": 2025,
  "type": "fee_info",
  "section_number": 3,
  
  # Full content
  "content": "Chi tiết các khoản phí...",
  "title": "Học phí năm 2025",
  
  # Structured data
  "fees": {...},
  "deadlines": [...],
  
  # Relationships
  "parent_id": "admission_2025_section_3",
  "sibling_ids": [],
  
  # Search optimization
  "keywords": ["học phí", "tiền", "nộp", "2025"],
  "summary": "Tổng học phí: 7.019.750đ"
}
```

---

## 🔍 PHASE 3: QUERY PROCESSING & RETRIEVAL

### Bước 1: Query Analysis

**Extract Intent:**
```python
Query: "Học phí năm 2025 là bao nhiêu?"

Intent Classification:
- Contains ["học phí", "tiền"] → Intent: FEE_INFO
- Contains ["2025", "năm 2025"] → Year: 2025

Result:
{
  "intent": "fee_info",
  "year": 2025,
  "keywords": ["học phí", "bao nhiêu"]
}
```

**Intent Categories:**
1. **FEE_INFO**: học phí, tiền, phí, nộp bao nhiêu
2. **SCHEDULE**: lịch, ngày nào, khi nào, thời gian
3. **DOCUMENT**: hồ sơ, giấy tờ, cần mang gì
4. **PROCEDURE**: thủ tục, các bước, làm thế nào
5. **GENERAL**: câu hỏi tổng quát

### Bước 2: Hybrid Search Strategy

**Component 1: Semantic Search (Vector Similarity)**
```
1. Embed query → vector
2. Tính cosine similarity với tất cả chunks
3. Lấy top_k=10 chunks có similarity cao nhất

Ưu điểm: Tìm được ý nghĩa tương tự
Nhược điểm: Có thể miss exact keywords
```

**Component 2: Metadata Filter**
```
Filter conditions:
- year = 2025  (từ query analysis)
- type = "fee_info"  (từ intent)

Ưu điểm: Lọc chính xác theo năm và loại
Nhược điểm: Cứng nhắc, cần intent đúng
```

**Component 3: Keyword Search (BM25)**
```
1. Tokenize query → ["học", "phí", "năm", "2025"]
2. BM25 scoring trên content text
3. Lấy top_k=10

Ưu điểm: Tìm exact match keywords
Nhược điểm: Không hiểu ngữ nghĩa
```

**Kết hợp 3 components:**
```python
# Pseudo-logic
semantic_results = vector_search(query_embedding, top_k=10)
filtered_results = filter_by_metadata(semantic_results, year=2025, type="fee_info")
keyword_results = bm25_search(query_text, top_k=10)

# Merge và remove duplicates
combined_results = merge([filtered_results, keyword_results])

# Lấy ra top 15 candidates
candidates = combined_results[:15]
```

### Bước 3: Reranking

**Tại sao cần rerank?**
- Semantic search có thể rank sai
- Cần xem xét context đầy đủ query + chunk

**Cross-encoder Reranking:**
```
Model: ms-marco-MiniLM-L-6-v2 hoặc bge-reranker

Input: 
- Query: "Học phí năm 2025 là bao nhiêu?"
- Candidate chunks (15 cái)

Process:
- Đưa từng cặp (query, chunk) vào cross-encoder
- Score relevance: 0.0 - 1.0

Output:
- Top 5 chunks có điểm relevance cao nhất
```

### Bước 4: Context Enrichment

**Mục tiêu**: Bổ sung ngữ cảnh để LLM hiểu đầy đủ

**Strategy:**

1. **Thêm Parent Context**
```
Nếu retrieved chunk là "step":
→ Lấy thêm parent "section" để có ngữ cảnh tổng quan

Nếu retrieved chunk là "fee_info":
→ Lấy thêm parent "section_3" để biết deadline nộp
```

2. **Thêm Sibling Context**
```
Nếu retrieved chunk là "step_2":
→ Lấy thêm step_1 (bước trước) và step_3 (bước sau)
→ User hiểu được trình tự logic
```

3. **Deduplication**
```
Loại bỏ các chunks trùng lặp hoặc quá giống nhau
Giữ lại 5-10 chunks đại diện nhất
```

**Final Context:**
```
Context gồm 5-10 chunks với:
- Retrieved chunks (3-5 cái)
- Parent chunks (1-2 cái)
- Sibling chunks (1-3 cái)

Sắp xếp theo thứ tự logic:
1. Overview/Parent
2. Main retrieved chunks
3. Related siblings
```

---

## 📝 PHASE 4: PROMPT ENGINEERING

### System Prompt
```
Bạn là trợ lý tư vấn thủ tục nhập học của Trường Đại học Khoa học Tự nhiên.

NHIỆM VỤ:
- Trả lời câu hỏi của sinh viên dựa HOÀN TOÀN trên ngữ cảnh được cung cấp
- Trích dẫn chính xác nguồn (PHẦN, Bước, Năm)
- Trả lời ngắn gọn, rõ ràng, dễ hiểu
- Nếu không có thông tin, nói rõ "Không tìm thấy thông tin trong tài liệu"

LƯU Ý:
- Luôn đề cập năm học để tránh nhầm lẫn
- Highlight các deadline quan trọng
- Format số tiền dễ đọc (VD: 7.019.750đ)
- Nếu có nhiều bước, liệt kê rõ ràng
```

### Context Prompt
```
----- NGỮ CẢNH TỪ TÀI LIỆU -----

[CHUNK 1 - Type: fee_info, Year: 2025]
Tiêu đề: Học phí năm 2025
Nội dung:
1. Tiền làm hồ sơ, tài liệu: 50.000đ
2. Hồ sơ sức khỏe, khám sức khỏe: 180.000đ
3. Bảo hiểm Y tế (bắt buộc): 789.750đ
4. Tạm thu học phí học kì 1 năm 2025-2026: 6.000.000đ
Tổng cộng: 7.019.750đ
Thời gian nộp: từ ngày 25/8/2025 đến 05/9/2025
Nguồn: PHẦN 3

[CHUNK 2 - Type: section, Year: 2025]
Tiêu đề: PHẦN 3: Nộp học phí tạm thu
Nội dung: Thí sinh nộp học phí theo hình thức chuyển khoản...
Nguồn: PHẦN 3

----- HẾT NGỮ CẢNH -----
```

### User Prompt
```
CÂU HỎI: Học phí năm 2025 là bao nhiêu?

Hãy trả lời dựa trên ngữ cảnh trên. Nhớ trích dẫn nguồn.
```

### Optimization Tips
- **Temperature**: 0.1-0.3 (cần chính xác, không sáng tạo)
- **Max tokens**: 500-1000 (đủ cho câu trả lời chi tiết)
- **Stop sequences**: ["\n\nNguồn:", "---"]

---

## 🤖 PHASE 5: LLM GENERATION & POST-PROCESSING

### Bước 1: Call LLM API

**Lựa chọn Model:**
- **GPT-4**: Chất lượng tốt nhất, đắt
- **GPT-4o-mini**: Cân bằng giá/chất lượng
- **Claude 3.5 Sonnet**: Tốt cho tiếng Việt
- **Gemini 1.5 Pro**: Google, tốt, giá rẻ
- **Local LLM**: Viettel-LLM, Vinallama (privacy)

**API Call:**
```python
response = llm.generate(
    system_prompt=system_prompt,
    messages=[
        {"role": "user", "content": context_prompt + user_prompt}
    ],
    temperature=0.3,
    max_tokens=800
)
```

### Bước 2: Response Validation

**Check 1: Có trả lời không?**
```python
if response.empty or len(response) < 10:
    return "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại."
```

**Check 2: Có hallucination không?**
```python
# Kiểm tra xem response có chứa thông tin không có trong context
if contains_info_not_in_context(response, context):
    flag_for_review()
```

**Check 3: Có đầy đủ thông tin không?**
```python
# Với intent FEE_INFO, response phải chứa số tiền
if intent == "FEE_INFO" and not contains_amount(response):
    retry_with_better_prompt()
```

### Bước 3: Add Citation

**Format:**
```
[Response từ LLM]

📚 Nguồn: PHẦN 3 - Nộp học phí, Thủ tục nhập học năm 2025
⏰ Deadline: 25/8/2025 - 05/9/2025
```

### Bước 4: Format Output

**Markdown Formatting:**
```markdown
## Học phí năm 2025

Tổng số tiền cần nộp là **7.019.750đ**, bao gồm:

1. 💼 Tiền làm hồ sơ, tài liệu: 50.000đ
2. 🏥 Hồ sơ sức khỏe, khám sức khỏe: 180.000đ
3. 🏥 Bảo hiểm Y tế (bắt buộc): 789.750đ
4. 📚 Tạm thu học phí học kỳ 1: 6.000.000đ

⏰ **Thời gian nộp**: Từ ngày 25/8/2025 đến 05/9/2025

📍 **Hình thức**: Chuyển khoản

---
📚 Nguồn: PHẦN 3, Thủ tục nhập học 2025
```

### Bước 5: Fallback Handling

**Khi không tìm thấy thông tin:**
```markdown
Xin lỗi, tôi không tìm thấy thông tin về [chủ đề] trong tài liệu.

Gợi ý:
- Kiểm tra lại năm học bạn đang hỏi
- Liên hệ trực tiếp: 024.38581283
- Email: ctsv@hus.edu.vn
```

---

## 📊 MONITORING & IMPROVEMENT

### User Feedback Loop

**Thu thập feedback:**
- 👍 Thumbs up: Câu trả lời hữu ích
- 👎 Thumbs down: Câu trả lời không đúng
- 📝 Comment: User ghi chú vấn đề

**Phân tích:**
```python
# Identify problematic queries
low_rated_queries = queries.filter(rating <= 2)

# Analyze patterns
common_failures = analyze_intent(low_rated_queries)
- Intent: FEE_INFO → 15% failure rate
- Intent: SCHEDULE → 30% failure rate

# Improve
- Thêm training examples cho SCHEDULE intent
- Cải thiện chunking cho schedule data
- Điều chỉnh reranking weights
```

### Continuous Improvement

**A/B Testing:**
- Test different chunking strategies
- Test different prompt templates
- Test different LLM models

**Metrics to track:**
- Response accuracy
- Response time
- User satisfaction (NPS)
- Retrieval precision/recall

---

## 🎯 KẾT LUẬN

### Điểm mạnh của giải pháp này:

✅ **Chunking thông minh**: Không split cố định token, giữ nguyên ngữ cảnh logic
✅ **Metadata filtering**: Lọc chính xác theo năm, tránh nhầm lẫn
✅ **Hybrid search**: Kết hợp semantic + keyword + filter
✅ **Context enrichment**: Tự động bổ sung parent/sibling chunks
✅ **Structured data**: Dễ truy vấn thông tin chi tiết (học phí, lịch, hồ sơ)

### So sánh với fixed-token chunking:

| Tiêu chí | Fixed Token | Smart Chunking |
|----------|-------------|----------------|
| Giữ ngữ cảnh | ❌ Bị cắt giữa câu | ✅ Hoàn chỉnh |
| Filter theo năm | ⚠️ Khó | ✅ Dễ |
| Trả lời chi tiết | ⚠️ Thiếu context | ✅ Đầy đủ |
| Setup | ✅ Đơn giản | ⚠️ Phức tạp hơn |
| Performance | ✅ Nhanh | ⚠️ Cần tối ưu |

### Next Steps:

1. Implement chunking strategy
2. Setup vector database
3. Build retrieval pipeline
4. Test với real queries
5. Iterate based on feedback
