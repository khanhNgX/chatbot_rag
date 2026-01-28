# 🌐 Web Chatbot - Thủ Tục Nhập Học 2025

Ứng dụng web chatbot với giao diện đẹp để tư vấn thủ tục nhập học.

## 🎨 Tính năng

- ✅ Giao diện web hiện đại, responsive
- ✅ Chat realtime với Gemini AI
- ✅ Quick questions (câu hỏi nhanh)
- ✅ Typing indicator
- ✅ Session management
- ✅ Reset chat
- ✅ Emoji support

## 🚀 Cài đặt và chạy

### 1. Cài đặt Flask

```bash
pip install flask google-generativeai
```

Hoặc:

```bash
pip install -r requirements_web.txt
```

### 2. Chạy web server

```bash
python app.py
```

### 3. Mở trình duyệt

Truy cập: **http://localhost:5000**

## 📱 Giao diện

- **Header**: Tiêu đề và logo trường
- **Quick Questions**: 5 câu hỏi nhanh phổ biến
- **Chat Area**: Khu vực chat với avatar và bubble
- **Input**: Ô nhập tin nhắn với nút Gửi và Làm mới

## 💬 Cách sử dụng

1. Mở trình duyệt tại http://localhost:5000
2. Chọn quick question hoặc gõ câu hỏi
3. Nhấn Enter hoặc nút "Gửi"
4. Đợi chatbot trả lời
5. Nút "Làm mới" để bắt đầu hội thoại mới

## 🎯 Quick Questions

- 💰 **Học phí** - Hỏi về học phí năm 2025
- 📋 **Thủ tục** - Các bước nhập học
- 📅 **Lịch nhập học** - Lịch theo ngành
- 📄 **Hồ sơ** - Giấy tờ cần chuẩn bị
- 📞 **Liên hệ** - Thông tin liên lạc

## 🔧 Cấu trúc

```
project/
├── app.py                  # Flask server
├── templates/
│   └── index.html         # Giao diện web
├── data/
│   └── Thủ tục nhập học 2025.txt
└── requirements_web.txt   # Dependencies
```

## ⚙️ API Endpoints

- **GET /** - Trang chủ
- **POST /chat** - Send message
- **POST /reset** - Reset chat session

## 🎨 Customization

Để thay đổi màu sắc, chỉnh sửa CSS trong `templates/index.html`:

```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

## 📞 Liên hệ hỗ trợ

- **Điện thoại**: 024.38581283
- **Email**: ctsv@hus.edu.vn
- **Địa chỉ**: 334 Nguyễn Trãi, Thanh Xuân, Hà Nội

## 📄 License

MIT License
