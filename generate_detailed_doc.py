# -*- coding: utf-8 -*-
"""Generate detailed technical documentation PDF."""

import os
from fpdf import FPDF

MC = {"new_x": "LMARGIN", "new_y": "NEXT"}


def build_doc():
    pdf = FPDF()
    pdf.add_font("DejaVu", fname="C:/Windows/Fonts/DejaVuSans.ttf")
    pdf.set_auto_page_break(auto=True, margin=15)

    def title(text, size=14):
        pdf.set_font("DejaVu", size=size)
        pdf.set_text_color(30, 60, 120)
        pdf.multi_cell(w=0, h=size * 0.8, text=text, **MC)
        pdf.ln(2)
        pdf.set_draw_color(30, 60, 120)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    def subtitle(text):
        pdf.set_font("DejaVu", size=11)
        pdf.set_text_color(40, 40, 40)
        pdf.ln(3)
        pdf.multi_cell(w=0, h=7, text=text, **MC)
        pdf.ln(2)

    def body(text):
        pdf.set_font("DejaVu", size=10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(w=0, h=6, text=text, **MC)
        pdf.ln(2)

    def code(text):
        pdf.set_font("DejaVu", size=8)
        pdf.set_text_color(30, 30, 30)
        pdf.set_fill_color(240, 240, 240)
        pdf.multi_cell(w=0, h=4.5, text=text, fill=True, **MC)
        pdf.ln(3)

    def bullet(text):
        pdf.set_font("DejaVu", size=10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(w=0, h=6, text=f"  *  {text}", **MC)

    # ===== TITLE PAGE =====
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("DejaVu", size=20)
    pdf.set_text_color(30, 60, 120)
    pdf.multi_cell(w=0, h=11, text="RAG Chatbot - Tai Lieu Ky Thuat Chi Tiet\nLuong Hoat Dong Tong The", align="C", **MC)
    pdf.ln(10)
    pdf.set_font("DejaVu", size=12)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(w=0, h=7, text="Chunking - Embedding - Retrieval - Generation", align="C", **MC)
    pdf.ln(10)
    pdf.set_font("DejaVu", size=10)
    pdf.multi_cell(w=0, h=6, text="Truong Dai hoc Khoa hoc Tu nhien - DHQG Ha Noi\nNam 2025", align="C", **MC)

    # ===== PHAN 1: CHUNKING =====
    pdf.add_page()
    title("PHAN 1: CHUNKING (Chia tai lieu thanh chunks)")

    subtitle("1.1. Tong quan")
    body(
        "He thong co 2 che do chunking:\n"
        "A) Rule-based (phase1_chunking.py): Dung cho tai lieu thu tuc nhap hoc - phan tich cau truc PHAN 1-4, B1-B4 bang regex.\n"
        "B) LLM-powered (automation_ai_rag.py): Dung Groq LLM de chunk tai lieu moi/khong co cau truc co dinh."
    )

    subtitle("1.2. Che do A: Rule-based Chunking (phase1_chunking.py)")
    body(
        "EnrollmentProcessor xu ly tai lieu thu tuc nhap hoc theo cau truc 4 cap:\n\n"
        "Level 0: Overview - Tom tat toan bo tai lieu\n"
        "Level 1: Section - Moi PHAN lon (PHAN 1, 2, 3, 4)\n"
        "Level 2: Subsection - Nhom thong tin trong moi phan (fee_overview, steps_group, schedule_group...)\n"
        "Level 3: Detail - Chi tiet cu the (fee_item, step_b1, schedule_major, docs_same_day_item...)"
    )

    subtitle("1.2.1. Metadata duoc gan nhu the nao (Rule-based)")
    body(
        "Moi chunk duoc gan metadata sau:\n"
        "- intent_key: Xac dinh theo vi tri trong cau truc (PHAN 1->lookup, PHAN 2->online_confirmation, PHAN 3->fee_info, PHAN 4->admission_procedure)\n"
        "- subtype: Loai chi tiet (fee_item, step_b1, schedule_major, section_3...)\n"
        "- section_id: phan_1, phan_2, phan_3, phan_4\n"
        "- step_id: b1_phan_4, b2_phan_4... (chi co trong PHAN 4)\n"
        "- canonical_nav_id: ID dieu huong chinh (= section_id hoac step_id)\n"
        "- year: Nam tuyen sinh tu ten file hoac .env\n"
        "- source: Ten file nguon\n"
        "- Cac truong bo sung: dates, links, amount, major, major_norm, time_slot..."
    )

    subtitle("1.2.2. Quy tac xac dinh intent_key")
    body(
        "PHAN 1 -> lookup (tra cuu trung tuyen)\n"
        "PHAN 2 -> online_confirmation (xac nhan nhap hoc truc tuyen)\n"
        "PHAN 3 -> fee_info (hoc phi), fee_payment (hinh thuc nop)\n"
        "PHAN 4:\n"
        "  - Tong quan/buoc -> admission_procedure\n"
        "  - Tung buoc B1-B4 -> step\n"
        "  - Lich theo nganh -> schedule_by_major\n"
        "  - Ho so nop ngay -> docs_same_day\n"
        "  - Ho so nop sau -> docs_later\n"
        "  - Luu y -> notes\n"
        "  - Lien he -> contact\n"
        "Moc thoi gian -> deadlines_summary"
    )

    subtitle("1.3. Che do B: LLM Chunking (automation_ai_rag.py)")
    body(
        "Dung khi tai lieu khong co cau truc PHAN 1-4 co dinh.\n"
        "Goi Groq API voi prompt yeu cau LLM chia tai lieu thanh Parent/Children."
    )

    subtitle("1.3.1. Prompt gui den LLM de chunk")
    code(
        "System prompt (tom tat):\n"
        "\"Ban la chuyen gia boc tach du lieu tuyen sinh.\n"
        "Nhiem vu: Chia tai lieu thanh cac PHAN LON (Parents)\n"
        "va cac Y NHO CHI TIET (Children).\n"
        "Tap hop nhan (topics): [fee, admission_docs, schedule,\n"
        "  procedure, contact, major_info, general, fee_payment]\n\n"
        "QUY TAC PHAN CHIA (BAT BUOC):\n"
        "1. GIU NOI DUNG O PARENT: Parent chunk PHAI chua\n"
        "   DAY DU noi dung goc.\n"
        "2. KHONG CHIA QUA NHO: Gom nhom thong tin lien quan.\n"
        "3. BOC TACH LICH: Gom nhom lich theo NGAY.\n"
        "4. CHI TIET GIAY TO: Khong chia moi giay to thanh 1 Child.\n"
        "5. KHONG DUOC BO SOT: Quet het toan bo van ban.\n\n"
        "Yeu cau dinh dang JSON:\n"
        "{ sections: [{ parent_title, parent_content, topic,\n"
        "  children: [{ child_title, child_content, keywords }] }] }\""
    )

    subtitle("1.3.2. LLM du doan metadata nhu the nao")
    body(
        "LLM tra ve JSON voi cac truong:\n"
        "- parent_title: Tieu de muc lon\n"
        "- parent_content: Noi dung goc day du\n"
        "- topic: Nhan phan loai (fee, schedule, procedure...)\n"
        "- children[].child_title: Tieu de y nho\n"
        "- children[].child_content: Noi dung chi tiet\n"
        "- children[].keywords: Tu khoa\n\n"
        "Code sau do gan them:\n"
        "- chunk_id (tu dong)\n"
        "- level: parent/child\n"
        "- source: ten file\n"
        "- year: tu ADMISSION_YEAR"
    )

    # ===== PHAN 2: EMBEDDING =====
    pdf.add_page()
    title("PHAN 2: EMBEDDING (Tao vector va luu tru)")

    subtitle("2.1. Model embedding")
    body(
        "Model: Gemini Embedding API (gemini-embedding-001)\n"
        "Goi qua REST API:\n"
        "POST https://generativelanguage.googleapis.com/v1beta/models/\n"
        "     gemini-embedding-001:embedContent?key={GEMINI_API_KEY}\n\n"
        "Khong dung SDK, chi dung thu vien requests.\n"
        "Cau hinh trong .env: GEMINI_MODEL_EMBED=gemini-embedding-001"
    )

    subtitle("2.2. Chuan bi text truoc khi embed")
    body(
        "Ham prepare_text_for_embedding(chunk) tao text gom:\n"
        "- Dong 1: [TYPE: ...] [YEAR: ...] title\n"
        "- Dong 2+: Noi dung chunk\n"
        "- Dong cuoi: Metadata bo sung (total, date, major, nav_id, section, step)\n\n"
        "Muc dich: Giup embedding bao gom ca ngu canh metadata, khong chi noi dung thuan."
    )

    subtitle("2.3. Luu tru vector")
    body(
        "File: vector_db.json\n"
        "Cau truc: { \"chunks\": [...], \"embeddings\": [...] }\n"
        "Moi chunk tuong ung 1 embedding vector cung index.\n\n"
        "Truy van: Cosine similarity voi NumPy:\n"
        "  similarities = dot(E_normalized, query_normalized)\n"
        "  Loc theo where filter (metadata match)\n"
        "  Sap xep giam dan similarity\n"
        "  Tra ve top-k ket qua"
    )

    # ===== PHAN 3: TRUY VAN (RETRIEVAL) =====
    pdf.add_page()
    title("PHAN 3: TRUY VAN (Retrieval Pipeline)")

    subtitle("3.1. Tong quan luong truy van")
    code(
        "User query\n"
        "    |\n"
        "    v\n"
        "1. AI Rewrite (Groq) -> refined_query + detected_topic\n"
        "    |\n"
        "    v\n"
        "2. Extract Entities (regex) -> intent, step, section, major...\n"
        "    |\n"
        "    v\n"
        "3. Build Query Frame -> scope, nav_target, task_type\n"
        "    |\n"
        "    v\n"
        "4. Canonical Intent -> intent cuoi cung\n"
        "    |\n"
        "    v\n"
        "5. Build Where Filter -> metadata filter cho vector search\n"
        "    |\n"
        "    v\n"
        "6. Vector Search (filtered + broad)\n"
        "    |\n"
        "    v\n"
        "7. Year Preference -> uu tien chunks dung nam\n"
        "    |\n"
        "    v\n"
        "8. Quality Score -> chon filtered hoac broad\n"
        "    |\n"
        "    v\n"
        "9. Rerank -> scoring + sorting\n"
        "    |\n"
        "    v\n"
        "10. Enrich Hierarchy -> them parent/sibling\n"
        "    |\n"
        "    v\n"
        "11. Dedupe + Cap -> tra ve top_k chunks"
    )

    subtitle("3.2. Co du doan intent tu query khong?")
    body(
        "CO. He thong du doan intent qua 3 nguon:\n\n"
        "1) AI topic detection: Groq LLM phan loai query thanh topic (fee, schedule, procedure...)\n"
        "2) Rule-based entity extraction: Regex phat hien tu khoa (hoc phi, lich, buoc, ho so...)\n"
        "3) Canonical intent mapping: Ket hop AI topic + entities + query_frame de xac dinh intent cuoi cung.\n\n"
        "Thu tu uu tien:\n"
        "- Query frame nav_type (local_step -> step, section -> admission_procedure)\n"
        "- Entity keywords (hoc phi -> fee_info, lich -> schedule_by_major...)\n"
        "- AI topic fallback (neu khong match rule nao)"
    )

    subtitle("3.3. Truy van theo embedding (Vector Search)")
    body(
        "Quy trinh day du:\n"
        "1. Tao embedding cho refined_query (Gemini API)\n"
        "2. Chay 2 luong song song:\n"
        "   a) Filtered search: query + where_filter (metadata match)\n"
        "   b) Broad search: query + khong filter\n"
        "3. Tinh quality score cho moi luong (top-3 grounding score trung binh)\n"
        "4. Chon luong tot hon:\n"
        "   - Dung broad neu: filtered rong HOAC broad_score > filtered_score + 0.10\n"
        "   - NHUNG: neu strict nav lock (section/local_step) -> giu filtered\n"
        "5. Rerank ket qua da chon"
    )

    subtitle("3.4. Truy van theo luat cung (Metadata Filter)")
    body(
        "Where filter duoc xay dung tu intent + entities:\n\n"
        "- Nav target la buoc local (vd: b2_phan_4):\n"
        "  -> where = {canonical_nav_id: 'b2_phan_4'}\n\n"
        "- Nav target la section (vd: phan_3):\n"
        "  -> where = {section_id: 'phan_3'}\n\n"
        "- Intent cu the (fee_info, step, schedule_by_major...):\n"
        "  -> where = {intent_key: intent} + subtype/step_id bo sung\n\n"
        "- Intent chung (general, admission_procedure):\n"
        "  -> where = None (khong filter, dung embedding similarity)"
    )

    subtitle("3.5. Rerank scoring formula")
    body(
        "Cong thuc:\n"
        "  grounding_score = (base * 0.70) + (lexical_score * 0.30) + bonus\n\n"
        "Trong do:\n"
        "- base = cosine similarity tu vector search\n"
        "- lexical_score = (overlap_query * 0.6) + (overlap_refined * 0.4)\n"
        "  (ty le token trung giua query va noi dung chunk)\n"
        "- bonus:\n"
        "  +0.15 neu intent_key khop\n"
        "  +0.25 neu dung step number\n"
        "  +0.30 neu dung major (nganh)\n"
        "  +0.20 neu dung docs subtype\n"
        "  +0.20 neu dung nam tuyen sinh (ADMISSION_YEAR)"
    )

    # ===== PHAN 4: GENERATION =====
    pdf.add_page()
    title("PHAN 4: GENERATION (Tao cau tra loi)")

    subtitle("4.1. Pipeline generation")
    code(
        "Chunks retrieved\n"
        "    |\n"
        "    v\n"
        "1. Check cache -> neu co tra ve ngay\n"
        "    |\n"
        "    v\n"
        "2. Deterministic formatter -> neu intent ro (fee, schedule, step)\n"
        "   |                          tra loi bang template cung\n"
        "   |                          KHONG goi API\n"
        "   |\n"
        "   v (neu khong deterministic duoc)\n"
        "3. Groq LLM generation -> goi API voi system prompt + context + history\n"
        "    |\n"
        "    v\n"
        "4. Naturalize answer:\n"
        "   a) Rule-based style variation\n"
        "   b) Gemini API rewrite (style layer)\n"
        "   c) Fact-lock validation -> rollback neu mat du kien\n"
        "    |\n"
        "    v\n"
        "5. Validate response -> kiem tra dates/money/source\n"
        "    |\n"
        "    v\n"
        "6. Save cache -> luu ket qua\n"
        "    |\n"
        "    v\n"
        "7. Tra ve user"
    )

    subtitle("4.2. Deterministic formatter")
    body(
        "Xu ly cac intent co cau truc ro rang ma KHONG can goi LLM:\n\n"
        "- fee_info: Liet ke tung khoan phi + tinh tong\n"
        "- fee_payment: Hinh thuc va thoi gian nop\n"
        "- admission_procedure: Tom tat PHAN 1-4 hoac buoc B1-B4\n"
        "- step: Noi dung cu the cua buoc Bn\n"
        "- schedule_by_major: Lich theo nganh\n"
        "- docs_same_day: Ho so nop trong ngay\n"
        "- docs_later: Ho so nop sau\n\n"
        "Uu diem: Nhanh (0ms), chinh xac 100%, khong ton quota API."
    )

    subtitle("4.3. LLM Generation (Groq)")
    body(
        "Khi deterministic khong xu ly duoc, goi Groq API:\n\n"
        "System prompt yeu cau:\n"
        "- Tra loi DUA HOAN TOAN tren context\n"
        "- Khong tu suy dien\n"
        "- Tinh toan chinh xac so lieu\n"
        "- Trich dan nguon [SOURCE]\n"
        "- Tra ve JSON: {answer, used_chunk_ids, grounded, uncertainty_note}\n\n"
        "Messages gui di:\n"
        "- system: system_prompt + answer_contract\n"
        "- user: [CHAT_HISTORY] + [CONTEXT] + query"
    )

    subtitle("4.4. Naturalization (Lam tu nhien cau tra loi)")
    body(
        "2 lop naturalization:\n\n"
        "Lop 1 - Rule-based (_safe_style_variation):\n"
        "- Thay doi header theo style (friendly/formal/concise)\n"
        "- VD: 'Tom tat thu tuc...' -> 'Minh tom tat...' (friendly)\n"
        "- Fact-lock: rollback neu mat ngay/tien/URL/PHAN/B1-B4/[SOURCE]\n\n"
        "Lop 2 - Gemini API (_call_gemini_naturalizer):\n"
        "- Gui cau tra loi da rule-based cho Gemini viet lai van phong\n"
        "- Prompt: 'Chi thay doi van phong, KHONG thay doi noi dung cot loi'\n"
        "- Temperature: 0.2 (rat thap de giam sang tao)\n"
        "- Fact-lock validation: kiem tra locked tokens truoc/sau\n"
        "- Neu mat bat ky token nao -> rollback ve ban rule-based\n"
        "- Neu them token moi (ngay/tien/URL) -> rollback\n"
        "- Co the tat: NATURALIZE_ENABLED=false"
    )

    # ===== PHAN 5: HISTORY MANAGEMENT =====
    pdf.add_page()
    title("PHAN 5: QUAN LY HISTORY (Lich su hoi thoai)")

    subtitle("5.1. Luu tru history")
    body(
        "- Luu trong memory (dict): chat_sessions[user_id::session_id]\n"
        "- Format: List[{role: 'user'/'assistant', content: '...'}]\n"
        "- Gioi han: MAX_HISTORY_TURNS = 20 luot gan nhat\n"
        "- Reset: Xoa khi user bam reset hoac doi session"
    )

    subtitle("5.2. History duoc dung o dau?")
    body(
        "1) RETRIEVER (automation_retriever.py):\n"
        "   - Giai quyet follow-up: 'buoc tiep theo' -> xem history de biet dang o buoc nao\n"
        "   - _infer_relative_axis_from_history: xac dinh dang noi global (PHAN) hay local (B)\n"
        "   - _last_step_from_history: tim buoc cuoi cung da tra loi\n"
        "   - _last_section_from_history: tim phan cuoi cung da tra loi\n\n"
        "2) GENERATOR (phase5_llm_generation.py):\n"
        "   - _build_history_context: Dong goi 10 luot gan nhat thanh text\n"
        "   - Dinh dang:\n"
        "     [CHAT_HISTORY]\n"
        "     USER: cau hoi cu\n"
        "     ASSISTANT: cau tra loi cu\n"
        "     [END_CHAT_HISTORY]\n"
        "   - Ghep vao dau prompt gui cho LLM"
    )

    subtitle("5.3. Prompt cuoi cung gui cho LLM gom nhung gi?")
    body(
        "Thu tu trong messages:\n\n"
        "1. System message:\n"
        "   - System prompt (vai tro, nguyen tac tra loi)\n"
        "   - Answer contract (yeu cau JSON output)\n\n"
        "2. User message (ghep theo thu tu):\n"
        "   - [CHAT_HISTORY]...10 luot gan nhat...[END_CHAT_HISTORY]\n"
        "   - [CONTEXT]...chunks retrieved...[END CONTEXT]\n"
        "   - Cau hoi hien tai cua user\n\n"
        "Nhu vay LLM nhan duoc: history + context tu vector DB + query moi\n"
        "de tra loi co ngu canh day du."
    )

    subtitle("5.4. Style rotation theo history")
    body(
        "He thong tu dong xoay van phong tra loi:\n"
        "- 3 style: formal, friendly, concise\n"
        "- Xoay theo so luot assistant da tra loi + hash(session_key)\n"
        "- Moi luot tra loi co style khac -> tranh lap di lap lai\n"
        "- Variant suffix (_v0, _v1, _v2) them da dang cau van"
    )

    # ===== PHAN 6: SO DO TONG THE =====
    pdf.add_page()
    title("PHAN 6: SO DO TONG THE")

    code(
        "USER QUERY\n"
        "    |\n"
        "    v\n"
        "+--[app.py]------------------------------------------+\n"
        "| Load history, resolve user/session                  |\n"
        "| Chon style_id tu history                            |\n"
        "+----------------------------------------------------+\n"
        "    |\n"
        "    v\n"
        "+--[automation_retriever.py]--------------------------+\n"
        "| 1. AI Rewrite (Groq) -> refined query              |\n"
        "| 2. Extract entities (regex)                        |\n"
        "| 3. Resolve follow-up tu history                    |\n"
        "| 4. Build query frame + canonical intent            |\n"
        "| 5. Vector search (Gemini embedding + cosine sim)   |\n"
        "| 6. Year preference + Rerank + Enrich               |\n"
        "+----------------------------------------------------+\n"
        "    |\n"
        "    v  (chunks + analysis)\n"
        "+--[phase5_llm_generation.py]------------------------+\n"
        "| 1. Cache check                                     |\n"
        "| 2. Deterministic format (neu intent ro)            |\n"
        "| 3. HOAC Groq LLM (history + context + query)       |\n"
        "| 4. Naturalize (rule-based + Gemini)                |\n"
        "| 5. Fact-lock validate                              |\n"
        "| 6. Save cache                                      |\n"
        "+----------------------------------------------------+\n"
        "    |\n"
        "    v\n"
        "RESPONSE -> User"
    )

    subtitle("External APIs su dung")
    body(
        "1. Gemini API:\n"
        "   - Embedding (gemini-embedding-001): Tao vector cho chunks va query\n"
        "   - Naturalizer (gemini-1.5-flash): Viet lai van phong cau tra loi\n\n"
        "2. Groq API:\n"
        "   - Query rewrite: Tinh chinh cau hoi user\n"
        "   - Topic detection: Phan loai chu de\n"
        "   - LLM Generation: Tao cau tra loi khi deterministic khong du\n"
        "   - AI Chunking: Chunk tai lieu moi (automation mode)"
    )

    subtitle("Fallback khi API loi")
    body(
        "4 lop fallback:\n"
        "1. Deterministic formatter (khong can API)\n"
        "2. Response cache (cau tra loi cu da luu)\n"
        "3. Template response (cau tra loi mau theo intent)\n"
        "4. Thong bao loi than thien"
    )

    # Output
    os.makedirs("docs", exist_ok=True)
    output_path = os.path.join("docs", "technical_documentation.pdf")
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    build_doc()
