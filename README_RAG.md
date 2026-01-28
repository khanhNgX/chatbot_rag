# 🎓 RAG Chatbot - Thủ Tục Nhập Học

Hệ thống RAG (Retrieval-Augmented Generation) Chatbot hoàn chỉnh cho tư vấn thủ tục nhập học, được xây dựng theo kiến trúc 5 PHASE.

## 📋 Kiến trúc hệ thống

### PHASE 1: Document Processing & Chunking
- ✅ Parse document thành structured data
- ✅ Chia thành chunks thông minh theo 4 levels (Overview, Section, Step, Detail)
- ✅ Extract metadata (năm, deadlines, URLs, học phí, lịch nhập học)

### PHASE 2: Embedding & Storage
- ✅ Generate embeddings với Gemini Embedding API
- ✅ Lưu trữ vectors trong ChromaDB
- ✅ Metadata filtering support

### PHASE 3: Query Processing & Retrieval
- ✅ Query analysis và intent classification
- ✅ Hybrid search (Semantic + Metadata filter)
- ✅ Context enrichment với parent/sibling chunks

### PHASE 4: Prompt Engineering
- ✅ System prompt tối ưu cho RAG
- ✅ Context prompt với citations
- ✅ Template formatting

### PHASE 5: LLM Generation & Post-processing
- ✅ Gemini 1.5 Flash integration
- ✅ Response validation
- ✅ Citation và formatting

## 🚀 Cài đặt và sử dụng

### 1. Cài đặt dependencies

```bash
pip install google-generativeai chromadb numpy
```

Hoặc:

```bash
pip install -r requirements_rag.txt
```

### 2. Chạy từng PHASE

#### PHASE 1: Document Processing
```bash
python phase1_chunking.py
```
Output: `chunks.json` (tất cả chunks với metadata)

#### PHASE 2: Embedding & Storage
```bash
python phase2_embedding.py
```
Output: ChromaDB collection với embeddings

#### PHASE 3: Query Processing & Retrieval (Test)
```bash
python phase3_retrieval.py
```
Test retrieval với các câu hỏi mẫu

#### PHASE 4 & 5: RAG Chatbot (Hoàn chỉnh)
```bash
python rag_chatbot.py
```
Chạy chatbot tương tác hoàn chỉnh

### 3. Hoặc chạy toàn bộ pipeline một lần

```bash
python run_full_pipeline.py
```

## 💬 Sử dụng Chatbot

### Chế độ tương tác:

```bash
python rag_chatbot.py
```

### Ví dụ câu hỏi:

```
🧑‍🎓 Bạn: Học phí năm 2025 là bao nhiêu?
🤖 Trợ lý: Tổng số tiền cần nộp là 7.019.750đ, bao gồm:
1. 💼 Tiền làm hồ sơ: 50.000đ
2. 🏥 Sức khỏe: 180.000đ
3. 🏥 Bảo hiểm y tế: 789.750đ
4. 📚 Học phí tạm thu học kỳ 1: 6.000.000đ

⏰ Thời gian nộp: 25/8/2025 - 05/9/2025
📚 Nguồn: PHẦN 3, Thủ tục nhập học năm 2025
```

Các câu hỏi khác:
- "Thủ tục nhập học gồm những bước nào?"
- "Lịch nhập học ngành Toán học?"
- "Cần chuẩn bị hồ sơ gì?"
- "Hạn chót nộp hồ sơ là khi nào?"
- "Địa chỉ liên hệ của trường?"

### Lệnh trong chatbot:

- **Đặt câu hỏi bình thường**: Gõ và Enter
- **`thoat`** / **`quit`** / **`exit`**: Thoát
- **`xoa`** / **`clear`**: Xóa lịch sử chat

## 📁 Cấu trúc dự án

```
project/
├── data/
│   └── Thủ tục nhập học 2025.txt      # Data gốc
├── phase1_chunking.py                  # PHASE 1: Chunking
├── phase2_embedding.py                 # PHASE 2: Embedding & Storage
├── phase3_retrieval.py                 # PHASE 3: Retrieval
├── rag_chatbot.py                      # PHASE 4&5: RAG Chatbot
├── run_full_pipeline.py                # Chạy toàn bộ pipeline
├── chunks.json                         # Generated chunks
├── requirements_rag.txt                # Dependencies
├── README_RAG.md                       # This file
└── solution_detailed_explanation.md    # Tài liệu kiến trúc chi tiết
```

## 🔧 Cấu hình

### API Key

API key Gemini được cấu hình trong các file:
- `phase2_embedding.py`: Embedding generation
- `phase3_retrieval.py`: Query embedding
- `rag_chatbot.py`: LLM generation

Để thay đổi API key, sửa biến `GEMINI_API_KEY` trong file main của từng phase.

### ChromaDB

ChromaDB sử dụng local storage. Data được lưu tự động khi chạy PHASE 2.

Collection name: `admission_chunks`

### Hyperparameters

Trong `rag_chatbot.py`:
- **Model**: `gemini-1.5-flash` (nhanh, rẻ)
- **Temperature**: Default (~0.7 từ model)
- **Top K**: 5 chunks mặc định
- **Embedding model**: `models/embedding-001`

## 🎯 Điểm mạnh của hệ thống

✅ **Chunking thông minh**: Không split cố định, giữ ngữ cảnh hoàn chỉnh  
✅ **Metadata filtering**: Lọc chính xác theo năm, loại thông tin  
✅ **Hybrid search**: Semantic + metadata filter  
✅ **Context enrichment**: Tự động bổ sung parent/sibling  
✅ **Structured data**: Dễ truy vấn học phí, lịch, hồ sơ  
✅ **RAG pipeline**: Retrieval-augmented để giảm hallucination  

## 🔍 So sánh với Chatbot đơn giản

| Tính năng | Simple Chatbot | RAG Chatbot |
|-----------|----------------|-------------|
| Trả lời chính xác | ⚠️ Có thể hallucinate | ✅ Dựa trên data thật |
| Update data | ❌ Phải retrain | ✅ Chỉ cần update chunks |
| Trích dẫn nguồn | ❌ Không có | ✅ Có citation |
| Lọc theo năm | ⚠️ Khó | ✅ Metadata filter |
| Chi phí | ✅ Rẻ | ⚠️ Đắt hơn (embedding + LLM) |

## 📞 Liên hệ

Nếu chatbot không trả lời được, sinh viên liên hệ:

- **Phòng**: Công tác sinh viên & truyền thông
- **Địa chỉ**: 334 Nguyễn Trãi, Thanh Xuân, Hà Nội
- **Điện thoại**: 024.38581283
- **Email**: ctsv@hus.edu.vn
- **Fanpage**: https://www.facebook.com/CTSVHUS

## 📝 License

MIT License
