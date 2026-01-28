# 📤 Hướng dẫn Upload Code lên GitHub

## 🔧 Chuẩn bị

### Bước 1: Cài đặt Git

**Windows:**
- Tải Git từ: https://git-scm.com/download/win
- Cài đặt với các tùy chọn mặc định

**Kiểm tra cài đặt:**
```bash
git --version
```

### Bước 2: Cấu hình Git (lần đầu)

```bash
git config --global user.name "Tên của bạn"
git config --global user.email "email@example.com"
```

---

## 🌐 Tạo Repository trên GitHub

### Bước 1: Đăng nhập GitHub

Truy cập: https://github.com

### Bước 2: Tạo Repository mới

1. Click nút **"New"** (góc trên bên phải)
2. Hoặc: https://github.com/new

### Bước 3: Điền thông tin

- **Repository name**: `chatbot-thu-tuc-nhap-hoc`
- **Description**: `Chatbot AI tư vấn thủ tục nhập học - ĐHKHTN`
- **Public** hoặc **Private**: Chọn Public
- ❌ **KHÔNG tick** "Add a README file"
- ❌ **KHÔNG tick** "Add .gitignore"
- Click **"Create repository"**

---

## 💻 Upload Code

### Option 1: Upload từ dòng lệnh (Khuyến nghị)

Mở PowerShell/Terminal tại thư mục `D:\VSCode\project`:

```bash
# Bước 1: Khởi tạo Git repository
git init

# Bước 2: Thêm tất cả files
git add .

# Bước 3: Commit
git commit -m "Initial commit: Chatbot thủ tục nhập học 2025"

# Bước 4: Thêm remote repository
git remote add origin https://github.com/YOUR_USERNAME/chatbot-thu-tuc-nhap-hoc.git

# Bước 5: Push lên GitHub
git push -u origin main
```

**Lưu ý**: Thay `YOUR_USERNAME` bằng username GitHub của bạn!

### Option 2: Upload qua GitHub Desktop

1. Tải GitHub Desktop: https://desktop.github.com
2. Đăng nhập GitHub
3. File → Add Local Repository
4. Chọn thư mục `D:\VSCode\project`
5. Publish repository

### Option 3: Upload trực tiếp trên web

1. Vào repository vừa tạo
2. Click **"uploading an existing file"**
3. Kéo thả tất cả files vào
4. Click **"Commit changes"**

---

## 🔐 Xử lý API Key

**⚠️ QUAN TRỌNG**: Không upload API key lên GitHub!

### Bước 1: Tạo file `.env`

Tạo file `.env` trong project:

```
GEMINI_API_KEY=AIzaSyAEPKOsnGnArFYckGojz-s4ymfvyhzj4Ic
```

### Bước 2: Cập nhật code

**File `app.py`:**

```python
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
```

### Bước 3: Thêm `.env` vào `.gitignore`

File `.gitignore` đã có sẵn:
```
.env
*.env
```

### Bước 4: Tạo file `.env.example`

```
GEMINI_API_KEY=your_api_key_here
```

---

## 📝 Cập nhật README.md

Thêm hướng dẫn về API key:

```markdown
## 🔑 API Key Setup

1. Tạo file `.env` trong thư mục project
2. Thêm API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
3. Lấy API key tại: https://makersuite.google.com/app/apikey
```

---

## 🔄 Cập nhật Code sau này

```bash
# Thêm files mới hoặc đã sửa
git add .

# Commit với message
git commit -m "Mô tả thay đổi"

# Push lên GitHub
git push
```

---

## 📋 Checklist trước khi Push

- ✅ Đã tạo `.gitignore`
- ✅ Đã xóa API key khỏi code
- ✅ Đã tạo file `.env.example`
- ✅ README.md đầy đủ
- ✅ Không có file nhạy cảm (password, keys...)
- ✅ Code đã test chạy được

---

## 🎯 Sau khi Upload

### Thêm Topics (Tags)

Vào repository → Settings → Topics, thêm:
- `chatbot`
- `ai`
- `gemini`
- `flask`
- `python`
- `rag`
- `education`
- `vietnamese`

### Tạo Release

1. Vào tab **Releases**
2. Click **"Create a new release"**
3. Tag version: `v1.0.0`
4. Title: `Chatbot v1.0.0 - Initial Release`
5. Mô tả tính năng
6. Click **"Publish release"**

### Thêm GitHub Pages (Optional)

Nếu muốn demo online:
1. Settings → Pages
2. Source: Deploy from a branch
3. Branch: `main` → `/ (root)`
4. Save

---

## 🌟 URL Repository

Sau khi upload xong, repository sẽ ở:

```
https://github.com/YOUR_USERNAME/chatbot-thu-tuc-nhap-hoc
```

---

## ❓ Troubleshooting

### Lỗi: Permission denied

**Giải pháp**: Dùng Personal Access Token thay vì password

1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Chọn scopes: `repo`
4. Copy token
5. Khi git push hỏi password, paste token vào

### Lỗi: Repository already exists

```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/chatbot-thu-tuc-nhap-hoc.git
git push -u origin main
```

### Lỗi: Branch 'master' vs 'main'

```bash
git branch -M main
git push -u origin main
```

---

## 📚 Resources

- Git documentation: https://git-scm.com/doc
- GitHub Guides: https://guides.github.com
- Markdown Guide: https://www.markdownguide.org

---

**Chúc bạn upload thành công! 🎉**
