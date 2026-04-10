# 📖 Hướng dẫn biên dịch Báo cáo LaTeX

Báo cáo này được cấu trúc chuyên nghiệp để trình bày dự án **Chatbot RAG HUS 2025**.

## 🛠 Yêu cầu hệ thống
- Một trình biên dịch LaTeX (Khuyên dùng: **Texmaker**, **TeXstudio**, hoặc **Overleaf**).
- Các Package cần thiết: `babel`, `inputenc`, `fontenc`, `listings`, `hyperref`, `titlesec`, `graphicx`.

## 🚀 Cách biên dịch
### 1. Trên máy cá nhân (Local)
Nếu bạn đã cài MikTeX hoặc TeX Live:
```bash
pdflatex main.tex
```
*Lưu ý: Bạn có thể cần chạy 2-3 lần để cập nhật Mục lục và các liên kết Hyperlink.*

### 2. Trên Overleaf (Khuyên dùng)
1. Tạo một dự án mới trên [Overleaf](https://www.overleaf.com/).
2. Tải file `main.tex` lên.
3. Nhấn **Compile**.
4. Chọn **Menu -> Compiler -> pdfLaTeX**.

## 📂 Giải thích các chương
- **Chương 1**: Giới thiệu về bối cảnh thực tế tại HUS.
- **Chương 2**: Giải thích kỹ thuật về luồng 5 pha (RAG Pipeline).
- **Chương 3**: Chi tiết các phần "Automation" đặc biệt (Semantic Chunking, Hierarchical Retrieval).
- **Chương 4**: Mô tả giao diện người dùng và trải nghiệm sinh viên.
- **Chương 5**: Đánh giá thực nghiệm về độ chính xác và tốc độ.
- **Chương 6**: Tổng kết và hướng mở rộng.

## 🖼 Thêm hình ảnh
Để chèn hình ảnh, hãy copy file ảnh vào cùng thư mục `report_latex` và sử dụng lệnh:
```latex
\begin{figure}[h]
    \centering
    \includegraphics[width=0.8\textwidth]{ten_file_anh.png}
    \caption{Mô tả hình ảnh}
    \label{fig:label_anh}
\end{figure}
```

---
💡 *Mẹo: Bạn có thể thay đổi thông tin tác giả và tiêu đề trong phần khai báo (Preamble) của file `main.tex`.*
