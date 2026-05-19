# ONTOLOGY.md

> Ontology và taxonomy chính thức cho hệ thống chatbot RAG hỏi đáp thủ tục nhập học.
> Đây là nguồn canonical IDs để dùng chung cho:
> - metadata labeling
> - query framing
> - navigation resolver
> - metadata filtering
> - evaluation

---

## 1. Ontology Design Principles

### 1.1. Canonical ID First

Mọi thực thể logic trong hệ thống phải được biểu diễn bằng **canonical ID ổn định**, không dùng chuỗi mô tả tự do làm định danh chính.

Ví dụ:

- `phan_1`
- `b1_phan_4`
- `hoc_phi`
- `deadline_upload_ho_so`

### 1.2. Separate Meaning Axes

Không gộp mọi ý nghĩa vào một `intent` duy nhất.
Hệ thống phải tách ít nhất theo các trục:

- navigation
- topic
- action
- time
- task type

### 1.3. Aliases Are Not IDs

Alias chỉ là từ/cụm từ giúp map query hoặc chunk về canonical ID.

---

## 2. Document Navigation Ontology

## 2.1. Root

- `root_nhap_hoc_2025`
  - Tài liệu tổng thể thủ tục nhập học năm 2025

## 2.2. Top-Level Sections

### `phan_1`

- Tên chuẩn: `Tra cứu danh sách trúng tuyển`
- Ý nghĩa: bước toàn cục đầu tiên của quy trình nhập học
- Level: 1

**Vietnamese aliases**
- phần 1
- mục 1
- phần tra cứu
- tra cứu danh sách trúng tuyển
- tra cứu kết quả
- tra cứu kết quả trúng tuyển
- bước 1 của thủ tục nhập học
- bước đầu tiên của thủ tục nhập học
- bước 1 toàn quy trình

### `phan_2`

- Tên chuẩn: `Xác nhận nhập học trực tuyến`
- Ý nghĩa: bước toàn cục thứ hai
- Level: 1

**Vietnamese aliases**
- phần 2
- mục 2
- xác nhận nhập học
- xác nhận nhập học trực tuyến
- xác nhận trên hệ thống bộ
- bước 2 của thủ tục nhập học
- bước 2 toàn quy trình

### `phan_3`

- Tên chuẩn: `Nộp học phí và các khoản tạm thu`
- Ý nghĩa: bước toàn cục thứ ba
- Level: 1

**Vietnamese aliases**
- phần 3
- mục 3
- học phí
- nộp học phí
- chuyển khoản học phí
- lệ phí nhập học
- bước 3 của thủ tục nhập học
- bước 3 toàn quy trình

### `phan_4`

- Tên chuẩn: `Chuẩn bị hồ sơ, nộp hồ sơ trực tuyến và trực tiếp`
- Ý nghĩa: bước toàn cục thứ tư
- Level: 1

**Vietnamese aliases**
- phần 4
- mục 4
- hồ sơ nhập học
- nộp hồ sơ
- phần hồ sơ
- upload hồ sơ
- nộp hồ sơ trực tiếp
- bước 4 của thủ tục nhập học
- bước 4 toàn quy trình

---

## 3. Local Step Ontology Inside Section 4

### `b1_phan_4`

- Tên chuẩn: `Chuẩn bị file hồ sơ PDF`
- Level: 2
- Parent: `phan_4`

**Vietnamese aliases**
- b1 phần 4
- bước 1 phần 4
- bước 1 của phần hồ sơ
- chuẩn bị hồ sơ scan
- tạo file hồ sơ pdf
- scan hồ sơ
- chuẩn bị file dữ liệu

### `b2_phan_4`

- Tên chuẩn: `Chụp ảnh chân dung và lưu file`
- Level: 2
- Parent: `phan_4`

**Vietnamese aliases**
- b2 phần 4
- bước 2 phần 4
- chụp ảnh chân dung
- ảnh 4x6
- ảnh thẻ nhập học
- chuẩn bị ảnh chân dung

### `b3_phan_4`

- Tên chuẩn: `Tải ảnh và hồ sơ lên hệ thống`
- Level: 2
- Parent: `phan_4`

**Vietnamese aliases**
- b3 phần 4
- bước 3 phần 4
- upload hồ sơ
- tải hồ sơ lên
- nộp hồ sơ trực tuyến
- bit ly nhập học
- nộp online

### `b4_phan_4`

- Tên chuẩn: `Nộp hồ sơ bản giấy trực tiếp`
- Level: 2
- Parent: `phan_4`

**Vietnamese aliases**
- b4 phần 4
- bước 4 phần 4
- nộp trực tiếp
- nộp bản giấy
- nộp hồ sơ tại trường
- địa điểm nộp hồ sơ

---

## 4. Topic Taxonomy

## 4.1. Admission Lookup & Confirmation

### `tra_cuu_ket_qua`

- Ý nghĩa: tra cứu kết quả trúng tuyển
- Typical questions:
  - tra cứu trúng tuyển ở đâu
  - xem kết quả trúng tuyển như thế nào

**Aliases**
- tra cứu kết quả
- tra cứu trúng tuyển
- xem kết quả
- danh sách trúng tuyển

### `xac_nhan_nhap_hoc`

- Ý nghĩa: xác nhận nhập học online
- Typical questions:
  - xác nhận nhập học trước khi nào
  - xác nhận ở đâu

**Aliases**
- xác nhận nhập học
- xác nhận online
- xác nhận trên hệ thống bộ
- confirm nhập học

### `ma_sinh_vien`

- Ý nghĩa: mã sinh viên cần lưu lại hoặc sử dụng trong hồ sơ
- Aliases:
  - mã sinh viên
  - mã sv
  - student id

## 4.2. Finance

### `hoc_phi`

- học phí kỳ 1 / tạm thu học phí
- Aliases:
  - học phí
  - học phí học kỳ 1
  - tiền học kỳ đầu

### `le_phi_ho_so`

- lệ phí hồ sơ / tiền tài liệu
- Aliases:
  - lệ phí hồ sơ
  - tiền làm hồ sơ
  - tiền tài liệu

### `bao_hiem_y_te`

- bảo hiểm y tế bắt buộc
- Aliases:
  - bhyt
  - bảo hiểm y tế
  - tiền bảo hiểm y tế

### `bao_hiem_than_the`

- bảo hiểm thân thể tự nguyện
- Aliases:
  - bảo hiểm thân thể
  - bh thân thể
  - bảo hiểm tự nguyện

### `kham_suc_khoe`

- hồ sơ và khám sức khỏe
- Aliases:
  - khám sức khỏe
  - hồ sơ sức khỏe

### `cach_nop_tien`

- phương thức chuyển khoản
- Aliases:
  - chuyển khoản
  - cách nộp tiền
  - nộp tiền như nào

## 4.3. Document Requirements

### `ho_so_so`

- scan và upload hồ sơ số
- Aliases:
  - hồ sơ số
  - file hồ sơ
  - hồ sơ online

### `anh_the`

- ảnh thẻ / ảnh chân dung
- Aliases:
  - ảnh thẻ
  - ảnh 3x4
  - ảnh 4x6
  - ảnh chân dung

### `giay_to_tot_nghiep`

- bằng hoặc giấy chứng nhận tốt nghiệp
- Aliases:
  - giấy tốt nghiệp
  - bằng tốt nghiệp
  - giấy chứng nhận tốt nghiệp

### `hoc_ba`

- học bạ THPT
- Aliases:
  - học bạ
  - học bạ THPT

### `giay_to_uu_tien`

- giấy tờ ưu tiên, cộng điểm
- Aliases:
  - giấy tờ ưu tiên
  - hồ sơ ưu tiên
  - giấy cộng điểm

### `giay_to_ca_nhan`

- CCCD, giấy khai sinh, sơ yếu lý lịch
- Aliases:
  - căn cước
  - cccd
  - giấy khai sinh
  - sơ yếu lý lịch

### `ho_so_quan_su`

- giấy tờ nghĩa vụ quân sự
- Aliases:
  - giấy chuyển nghĩa vụ quân sự
  - hồ sơ quân sự
  - giấy nvqs

### `ho_so_dang_doan`

- giấy chuyển sinh hoạt Đảng, Đoàn
- Aliases:
  - giấy chuyển đoàn
  - giấy chuyển đảng
  - hồ sơ đảng đoàn

### `tai_khoan_bidv`

- tài khoản ngân hàng BIDV
- Aliases:
  - bidv
  - tài khoản ngân hàng
  - mở tài khoản bidv

## 4.4. Schedule & Location

### `lich_nop_ho_so`

- lịch nộp hồ sơ theo buổi / theo ngành
- Aliases:
  - lịch nộp hồ sơ
  - lịch nhập học
  - nộp hồ sơ khi nào

### `nganh_hoc`

- ngành học liên quan đến lịch / nhóm nộp hồ sơ
- Aliases:
  - ngành học
  - ngành của em
  - nhóm ngành

### `dia_diem_nop`

- địa điểm nộp trực tiếp
- Aliases:
  - địa điểm nộp
  - nộp ở đâu
  - địa chỉ trường

### `ky_tuc_xa`

- đăng ký ký túc xá
- Aliases:
  - ký túc xá
  - ktx
  - đăng ký ktx

## 4.5. After Enrollment

### `tuan_sinh_hoat`

- tuần sinh hoạt đầu năm
- Aliases:
  - tuần sinh hoạt
  - sinh hoạt đầu năm
  - orientation week

### `thoi_khoa_bieu`

- thời khóa biểu chính thức
- Aliases:
  - thời khóa biểu
  - tkb
  - bắt đầu học khi nào

### `chuong_trinh_dac_biet`

- tài năng, chất lượng cao
- Aliases:
  - chương trình đặc biệt
  - tài năng
  - chất lượng cao

### `lien_he_ho_tro`

- phòng CTSV, điện thoại, email
- Aliases:
  - liên hệ hỗ trợ
  - phòng ctsv
  - số điện thoại
  - email hỗ trợ

---

## 5. Action Taxonomy

### `tra_cuu`
- tra cứu danh sách / kết quả

### `xac_nhan`
- xác nhận nhập học

### `chuyen_khoan`
- chuyển khoản thanh toán

### `scan_tai_lieu`
- scan tài liệu bằng app / điện thoại

### `upload_ho_so`
- tải file hồ sơ lên hệ thống

### `nop_truc_tiep`
- nộp giấy trực tiếp tại trường

### `chup_anh`
- chụp ảnh chân dung

### `dang_ki_ktx`
- đăng ký ký túc xá

### `cong_chung`
- công chứng bản sao

---

## 6. Time Entity Taxonomy

### `deadline_xac_nhan_nhap_hoc`
- hạn xác nhận nhập học

### `deadline_nop_hoc_phi`
- hạn hoặc khoảng thời gian nộp học phí

### `deadline_upload_ho_so`
- hạn upload hồ sơ online

### `ngay_nop_truc_tiep`
- ngày nộp hồ sơ trực tiếp

### `ngay_bat_dau_hoc`
- ngày bắt đầu học chính thức

### `tuan_sinh_hoat_dau_nam`
- tuần sinh hoạt đầu năm

### `deadline_bo_sung_ho_so`
- hạn bổ sung hồ sơ thiếu

### `thoi_gian_nop_chinh_thuc`
- khoảng thời gian nộp hồ sơ bổ sung / theo lớp

---

## 7. Task Type Taxonomy for Query Framing

### `ask_what`
- hỏi nội dung là gì

### `ask_how`
- hỏi cách làm, quy trình, thao tác

### `ask_when`
- hỏi thời gian, hạn, mốc ngày

### `ask_where`
- hỏi địa điểm, nơi nộp, nơi liên hệ

### `ask_payment`
- hỏi tiền, khoản phí, cách nộp tiền

### `ask_documents`
- hỏi giấy tờ cần nộp / chuẩn bị

### `ask_navigation`
- hỏi về phần, bước, mục

### `ask_contact`
- hỏi thông tin liên hệ

### `ask_schedule`
- hỏi lịch theo buổi / theo ngành / thời khóa biểu

---

## 8. Resolver Priority Rules

## 8.1. Navigation Resolution Priority

Thứ tự ưu tiên khi resolve target điều hướng:

1. explicit navigation mention trong query
2. explicit section mention trong history gần nhất
3. alias exact match
4. alias fuzzy match
5. fallback theo global process assumption

## 8.2. Global vs Local Disambiguation

### Rule A
Nếu query có:
- `bước 1 của thủ tục nhập học`
- `bước đầu tiên nhập học`
=> map ưu tiên `phan_1`

### Rule B
Nếu query có:
- `bước 1 của phần 4`
- `trong phần hồ sơ, bước 1`
- history gần nhất đang tập trung vào `phan_4`
=> map ưu tiên `b1_phan_4`

### Rule C
Nếu query chỉ có:
- `bước 1`
và không có history hữu ích
=> đánh dấu ambiguous, nhưng candidate đầu tiên là `phan_1`

---

## 9. Suggested Machine-Readable Export

Ngoài file Markdown này, nên có thêm:

- `ontology_topics.json`
- `ontology_actions.json`
- `ontology_time.json`
- `ontology_navigation.json`

Mỗi file có thể theo format:

```json
{
  "canonical_id": "phan_1",
  "label_vi": "Tra cứu danh sách trúng tuyển",
  "aliases_vi": [
    "phần 1",
    "bước 1 của thủ tục nhập học"
  ],
  "parent_id": "root_nhap_hoc_2025",
  "level": 1,
  "type": "section"
}
```

---

## 10. Governance Rules

- Không đổi canonical ID sau khi đã index production nếu chưa có migration plan.
- Khi thêm alias mới:
  - cập nhật ontology docs
  - cập nhật machine-readable export
  - cập nhật test cases
- Khi thêm tài liệu cho năm mới:
  - cân nhắc versioned doc IDs
  - không tái sử dụng `doc_id` cũ
