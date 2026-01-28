# Chatbot Tư Vấn Thủ Tục Nhập Học 2025

🎓 Hệ thống chatbot AI tư vấn thủ tục nhập học cho Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội

## ✨ Tính năng

- 🌐 **Web Chatbot** - Giao diện web hiện đại với Flask
- 🤖 **AI-powered** - Sử dụng Google Gemini AI
- 📚 **RAG Pipeline** - Hệ thống Retrieval-Augmented Generation đầy đủ
- 💬 **Interactive Chat** - Chat realtime với typing indicator
- 📱 **Responsive** - Hoạt động tốt trên mọi thiết bị

## 🚀 Quick Start

### 1. Clone repository

```bash
git clone https://github.com/YOUR_USERNAME/chatbot-thu-tuc-nhap-hoc.git
cd chatbot-thu-tuc-nhap-hoc
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements_web.txt
```

### 3. Chạy web chatbot

```bash
python app.py
```

### 4. Mở trình duyệt

Truy cập: **http://localhost:5000**

## 📋 Yêu cầu hệ thống

- Python 3.8+
- pip
- Internet connection (lần đầu tải model)

## 🔑 API Key

Cần API key của Google Gemini (miễn phí):
1. Truy cập: https://makersuite.google.com/app/apikey
2. Tạo API key mới
3. Thay API key trong file `app.py` (dòng 9)

## 📂 Cấu trúc dự án

```
project/
├── 🌐 Web Chatbot
│   ├── app.py                      # Flask server
│   ├── templates/
│   │   └── index.html             # Giao diện web
│   └── simple_chatbot.py          # Console version
│
├── 🔬 RAG Pipeline (5 PHASE)
│   ├── phase1_chunking.py         # Document processing
│   ├── phase2_embedding.py        # Embedding & ChromaDB
│   ├── phase3_retrieval.py        # Hybrid retrieval
│   ├── phase4_prompt_engineering.py
│   ├── phase5_llm_generation.py
│   ├── rag_chatbot.py            # RAG chatbot
│   └── run_full_pipeline.py      # Chạy tất cả
│
├── 📊 Data
│   └── data/
│       └── Thủ tục nhập học 2025.txt
│
└── 📚 Documentation
    ├── README.md
    ├── HUONG_DAN_CHAY.md
    ├── README_RAG.md
    └── solution_detailed_explanation.md
```

## 💡 Cách sử dụng

### Web Chatbot (Khuyến nghị)

```bash
python app.py
```

- Mở http://localhost:5000
- Click quick questions hoặc gõ câu hỏi
- Nhấn Enter hoặc nút "Gửi"

### Console Chatbot

```bash
python simple_chatbot.py
```

### RAG Pipeline (Nâng cao)

```bash
# Chạy toàn bộ pipeline
python run_full_pipeline.py

# Hoặc chạy từng phase
python phase1_chunking.py
python phase2_embedding.py
python phase3_retrieval.py
python rag_chatbot.py
```

## 📝 Ví dụ câu hỏi

- 💰 Học phí năm 2025 là bao nhiêu?
- 📋 Thủ tục nhập học gồm những bước nào?
- 📅 Lịch nhập học ngành Toán học?
- 📄 Cần chuẩn bị hồ sơ gì?
- 📞 Thông tin liên hệ của trường?

## 🔬 Công nghệ sử dụng

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Flask (Python)
- **AI/ML**: Google Gemini API
- **Vector DB**: ChromaDB
- **Embedding**: sentence-transformers

## 🎯 RAG Architecture

Hệ thống RAG gồm 5 PHASE:

1. **Document Processing & Chunking** - Chia document thành chunks thông minh
2. **Embedding & Storage** - Tạo embeddings và lưu ChromaDB
3. **Query Processing & Retrieval** - Hybrid search
4. **Prompt Engineering** - Tối ưu prompts
5. **LLM Generation** - Generate và validate response

Chi tiết: Xem [solution_detailed_explanation.md](solution_detailed_explanation.md)

## 📖 Documentation

- [HUONG_DAN_CHAY.md](HUONG_DAN_CHAY.md) - Hướng dẫn chi tiết
- [README_RAG.md](README_RAG.md) - RAG Pipeline
- [README_WEB.md](README_WEB.md) - Web Chatbot
- [solution_detailed_explanation.md](solution_detailed_explanation.md) - Kiến trúc RAG

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - Tự do sử dụng cho mục đích học tập và phi lợi nhuận.

## 📞 Liên hệ

Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội
- **Điện thoại**: 024.38581283
- **Email**: ctsv@hus.edu.vn
- **Địa chỉ**: 334 Nguyễn Trãi, Thanh Xuân, Hà Nội

## 🌟 Demo

![Chatbot Demo](https://via.placeholder.com/800x400?text=Chatbot+Demo)

---

**Made with ❤️ for students**
