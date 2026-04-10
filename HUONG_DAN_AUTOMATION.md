# 🚀 HƯỚNG DẪN CHẠY HỆ THỐNG AI-AUTOMATION RAG CHATBOT

Chào mừng bạn đến với hệ thống RAG nâng cao. Hệ thống này sử dụng **Groq (Llama 3.1 8B)** để tự động hóa hoàn toàn quy trình xử lý dữ liệu và tìm kiếm thông minh.

---

## 🛠 1. Cấu hình (.env)
Đảm bảo file `.env` của bạn có đầy đủ 2 loại Key (Dùng Groq cho AI và Gemini cho Embedding):
```env
# Dùng để Suy luận (Generation) & Gán nhãn AI (Groq)
GROQ_API_KEY=gsk_... 

# Dùng để Tạo Vector (Embedding - Gemini)
GEMINI_API_KEY=AIza... 

# Năm nhập học
ADMISSION_YEAR=2025
```

---

## 📂 2. Quy trình "Bơm" dữ liệu tự động (Automation Scan)
Bất cứ khi nào bạn có tài liệu mới (PDF, Word, TXT) hãy thả vào thư mục `data/` và chạy:

```bash
python automation_full_pipeline.py
```

**Hệ thống sẽ tự động làm gì?**
1.  **AI Semantic Chunking:** Dùng LLM chia đoạn theo logic ngữ nghĩa (không còn chia máy móc).
2.  **AI Tagging:** Tự gán nhãn chủ đề (`topic`) như: học phí, hồ sơ, lịch trình... cho từng đoạn.
3.  **Vector DB:** Tạo vector và lưu vào `vector_db.json`.

---

## 💬 3. Chạy Chatbot thông minh
Khởi động giao diện Web để bắt đầu trò chuyện:

```bash
python app.py
```

**Tính năng nổi bật:**
- **AI Query Rewrite:** Tự viết lại câu hỏi người dùng cho rõ ý.
- **AI Query Tagging:** Nhận diện người dùng đang hỏi về chủ đề gì (vd: hỏi về tiền -> gắn tag `fee`).
- **Metadata Filtering:** Chỉ tìm kiếm trong các đoạn tài liệu có nhãn tương ứng (tăng độ chính xác tuyệt đối).

---

## 📂 4. Các file quan trọng nhất
- `automation_ai_rag.py`: "Bộ não" xử lý các tác vụ AI thông minh.
- `automation_full_pipeline.py`: Quy trình nạp dữ liệu rảnh tay (Automation).
- `automation_retriever.py`: Bộ tìm kiếm thông minh 99% chính xác.
- `app.py`: Giao diện chatbot (Flask).

---
💡 *Mẹo: Nếu kết quả AI bận hoặc hết Quota, hệ thống sẽ tự động chuyển sang giải pháp "Smart Search" tìm kiếm bằng Regex để không làm gián đoạn câu trả lời!*
