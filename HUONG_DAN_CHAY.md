# 🚀 HƯỚNG DẪN CHẠY - CHATBOT THỦ TỤC NHẬP HỌC 2025

## 📋 Tổng quan dự án

Dự án gồm 2 phần chính:
1. **RAG Chatbot** - Hệ thống RAG đầy đủ 5 PHASE (nâng cao)
2. **Web Chatbot** - Giao diện web đơn giản (khuyến nghị)

---

## ⚡ CÁCH NHANH NHẤT - WEB CHATBOT

### Bước 1: Cài đặt thư viện
```bash
pip install flask google-generativeai
```

### Bước 2: Chạy web server
```bash
python app.py
```

### Bước 3: Mở trình duyệt
Truy cập: **http://localhost:5000**

✅ **XONG!** - Bạn đã có chatbot web với giao diện đẹp!

---

## 🎓 PHIÊN BẢN CONSOLE (Simple Chatbot)

### Chạy chatbot console đơn giản
```bash
python simple_chatbot.py
```

**Tính năng:**
- ✅ Chat trực tiếp trong terminal
- ✅ Tự động kiểm tra model Gemini có sẵn
- ✅ Không cần embedding phức tạp

**Lệnh trong chatbot:**
- Gõ câu hỏi và Enter để hỏi
- `thoat` / `quit` - Thoát
- `xoa` / `clear` - Bắt đầu hội thoại mới

---

## 🔬 RAG PIPELINE ĐẦY ĐỦ (Nâng cao)

Để chạy hệ thống RAG hoàn chỉnh theo 5 PHASE:

### Bước 1: Cài đặt dependencies
```bash
pip install google-generativeai chromadb numpy
```

### Bước 2: Chạy từng PHASE

#### PHASE 1: Document Processing & Chunking
```bash
python phase1_chunking.py
```
- **Output**: `chunks.json` (39 chunks)
- **Thời gian**: ~2 giây

#### PHASE 2: Embedding & Storage
```bash
python phase2_embedding.py
```
- **Output**: ChromaDB collection với embeddings
- **Thời gian**: ~1-2 phút (download model lần đầu)

#### PHASE 3: Query Processing & Retrieval (Test)
```bash
python phase3_retrieval.py
```
- **Chức năng**: Test retrieval với 4 câu hỏi mẫu
- **Output**: Top 3 chunks cho mỗi query

#### PHASE 4: Prompt Engineering (Test)
```bash
python phase4_prompt_engineering.py
```
- **Chức năng**: Test các prompts
- **Output**: System prompt, context prompt examples

#### PHASE 5: LLM Generation (Test)
```bash
python phase5_llm_generation.py
```
- **Chức năng**: Test LLM generation
- **Output**: Generated answer với validation

### Bước 3: Chạy RAG Chatbot hoàn chỉnh
```bash
python rag_chatbot.py
```

**Hoặc chạy toàn bộ pipeline một lần:**
```bash
python run_full_pipeline.py
```

---

## 📁 Cấu trúc Files

```
project/
├── 🌐 WEB CHATBOT (KHUYẾN NGHỊ)
│   ├── app.py                      # Flask server
│   ├── templates/
│   │   └── index.html             # Giao diện web
│   └── simple_chatbot.py          # Console version
│
├── 🔬 RAG PIPELINE (5 PHASE)
│   ├── phase1_chunking.py         # Document processing
│   ├── phase2_embedding.py        # Embedding & ChromaDB
│   ├── phase3_retrieval.py        # Hybrid retrieval
│   ├── phase4_prompt_engineering.py
│   ├── phase5_llm_generation.py
│   ├── rag_chatbot.py            # RAG chatbot hoàn chỉnh
│   └── run_full_pipeline.py      # Chạy tất cả
│
├── 📊 DATA
│   ├── data/
│   │   └── Thủ tục nhập học 2025.txt
│   └── chunks.json               # Generated chunks
│
└── 📚 DOCUMENTATION
    ├── README.md
    ├── README_RAG.md
    ├── README_WEB.md
    ├── HUONG_DAN_CHAY.md        # File này
    └── solution_detailed_explanation.md
```

---

## 💬 Ví dụ câu hỏi

```
✅ Học phí năm 2025 là bao nhiêu?
✅ Thủ tục nhập học gồm những bước nào?
✅ Lịch nhập học ngành Toán học?
✅ Cần chuẩn bị hồ sơ gì?
✅ Hạn chót nộp hồ sơ là khi nào?
✅ Địa chỉ và số điện thoại liên hệ?
✅ Làm sao để tra cứu kết quả trúng tuyển?
```

---

## 🔧 Troubleshooting

### Lỗi: Module not found

**Giải pháp:**
```bash
pip install flask google-generativeai chromadb numpy
```

### Lỗi: API key không hoạt động

**Dấu hiệu:**
```
404 models/gemini-pro is not found...
```

**Giải pháp:**
1. Kiểm tra API key tại: https://makersuite.google.com/app/apikey
2. Thay API key mới trong các file:
   - `app.py` (dòng 9)
   - `simple_chatbot.py` (dòng 9)
   - `phase5_llm_generation.py` (dòng 171)

### Lỗi: Port 5000 đã được sử dụng

**Giải pháp:**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Hoặc đổi port trong app.py
app.run(debug=True, host='0.0.0.0', port=8080)
```

### ChromaDB download model chậm

**Lần đầu chạy PHASE 2 sẽ tải model ~79MB**
- Chờ đợi hoàn thành (1-2 phút)
- Các lần sau sẽ không cần tải lại

---

## 🎯 So sánh các phiên bản

| Tính năng | Web Chatbot | Simple Console | RAG Pipeline |
|-----------|-------------|----------------|--------------|
| **Dễ sử dụng** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Giao diện** | Web đẹp | Terminal | Terminal |
| **Cài đặt** | 1 lệnh | 1 lệnh | 3 lệnh |
| **Chính xác** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Tốc độ** | Nhanh | Nhanh | Chậm hơn |
| **Embedding** | Không | Không | ChromaDB local |
| **Retrieval** | Không | Không | Hybrid search |
| **Phù hợp** | Demo, Production | Testing | Research, Learning |

**Khuyến nghị:**
- 👉 **Người dùng cuối**: Dùng **Web Chatbot** (`python app.py`)
- 👉 **Testing nhanh**: Dùng **Simple Console** (`python simple_chatbot.py`)
- 👉 **Nghiên cứu RAG**: Dùng **RAG Pipeline** (`python run_full_pipeline.py`)

---

## 📞 Hỗ trợ

Nếu gặp vấn đề, liên hệ:
- **Email**: ctsv@hus.edu.vn
- **Điện thoại**: 024.38581283

---

## 📝 Notes

- ✅ API key Gemini miễn phí có giới hạn request
- ✅ ChromaDB lưu local, không cần internet sau khi download model
- ✅ Web server mặc định chạy ở port 5000
- ✅ Tất cả chatbot đều sử dụng cùng data từ `data/Thủ tục nhập học 2025.txt`

---

## 🎓 Học thêm về RAG

Đọc file `solution_detailed_explanation.md` để hiểu chi tiết về:
- 📚 Chunking strategy (4 levels)
- 🔍 Hybrid retrieval
- 💡 Prompt engineering
- 🤖 LLM generation & validation

---

**Chúc bạn sử dụng thành công! 🎉**
