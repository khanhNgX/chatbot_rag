# 🤖 Bộ Prompt Hoàn Chỉnh cho AI Agent – Triển Khai RAG Chatbot
> Dựa trên sơ đồ "4 Phương Án Triển Khai RAG Chatbot"  
> Giả định: Phần RAG (embedding, vector search, retrieval) đã hoàn thiện và test qua API key.  
> Mỗi prompt dưới đây là **system prompt** hoàn chỉnh để nạp vào AI Agent, kèm **code scaffold** tham khảo.

---

## 📌 NGUYÊN TẮC CHUNG (áp dụng cho TẤT CẢ phương án)

```
Mọi phương án đều tuân thủ:
- session_id riêng biệt cho từng user
- LLM call là stateless: không có bộ nhớ giữa các request
- Mỗi request phải gửi TOÀN BỘ messages[] (history đã xử lý + message hiện tại)
- Cấu trúc context = system_prompt + RAG_chunks + history (đã trim/xử lý) + user_message
```

---

## ═══════════════════════════════════════════
## PHƯƠNG ÁN 1 — SLIDING WINDOW
## ═══════════════════════════════════════════

### 🎯 Mô tả
Giữ **N turns gần nhất** trong lịch sử hội thoại. Các turns cũ hơn bị loại bỏ hoàn toàn.  
**Ưu:** Đơn giản, dễ implement, không tốn extra LLM call.  
**Nhược:** Mất context khi hội thoại dài (người dùng hỏi lại vấn đề đã nói từ trước sẽ không nhớ).

---

### 📋 SYSTEM PROMPT – SLIDING WINDOW AGENT

```
SYSTEM PROMPT – RAG CHATBOT (Sliding Window Strategy)
======================================================

Bạn là một AI assistant thông minh, hỗ trợ người dùng dựa trên kiến thức được cung cấp.

## NHIỆM VỤ CỦA BẠN
Mỗi lần được gọi, bạn nhận vào:
1. [SYSTEM]: Hướng dẫn hành vi (prompt này)
2. [RAG_CONTEXT]: Các đoạn văn bản liên quan được truy xuất từ knowledge base
3. [HISTORY]: Tối đa {MAX_TURNS} turns gần nhất của cuộc hội thoại
4. [USER]: Câu hỏi hiện tại của người dùng

## CÁCH XỬ LÝ
- Ưu tiên trả lời dựa trên [RAG_CONTEXT] được cung cấp
- Nếu [RAG_CONTEXT] không đủ, dùng [HISTORY] để suy luận
- Nếu không có thông tin, trả lời trung thực là không biết
- KHÔNG bịa đặt thông tin ngoài context được cung cấp

## QUY TẮC QUAN TRỌNG
- session_id của cuộc hội thoại này: {SESSION_ID}
- Bạn chỉ thấy {MAX_TURNS} turns gần nhất – nếu người dùng nhắc đến điều đã nói từ rất lâu mà bạn không thấy trong history, hãy lịch sự thông báo rằng bạn không còn lưu thông tin đó.
- Trả lời bằng ngôn ngữ của người dùng
- Câu trả lời phải súc tích, chính xác và hữu ích

## FORMAT RAG CONTEXT
Khi được cung cấp ngữ cảnh, nó có dạng:
<rag_context>
[Chunk 1]: {nội dung chunk 1}
[Chunk 2]: {nội dung chunk 2}
...
</rag_context>
```

---

### 💻 Code Scaffold – Python (Sliding Window)

```python
import json
from anthropic import Anthropic

client = Anthropic()

# ── CONFIG ──────────────────────────────────────────────
MAX_TURNS = 10          # Số turns giữ lại (1 turn = 1 cặp user+assistant)
MAX_TOKENS_RESPONSE = 1024
MODEL = "claude-opus-4-5"  # hoặc claude-sonnet-4-5

# ── SESSION STORE (thay bằng Redis/Postgres ở production) ──
sessions: dict[str, list] = {}

def get_history(session_id: str) -> list:
    return sessions.get(session_id, [])

def save_history(session_id: str, history: list):
    sessions[session_id] = history

def trim_history_sliding_window(history: list, max_turns: int) -> list:
    """Giữ N turns gần nhất. 1 turn = [user_msg, assistant_msg]"""
    # Mỗi turn = 2 messages (user + assistant)
    max_messages = max_turns * 2
    if len(history) > max_messages:
        return history[-max_messages:]
    return history

# ── RAG RETRIEVAL (đã có sẵn, gọi vào) ──────────────────
def retrieve_rag_chunks(query: str, session_id: str) -> str:
    """
    Gọi RAG pipeline của bạn ở đây.
    Trả về string đã format sẵn để đưa vào prompt.
    """
    # TODO: thay bằng RAG pipeline thực tế của bạn
    # chunks = your_rag.search(query, top_k=5)
    # return "\n".join([f"[Chunk {i+1}]: {c}" for i, c in enumerate(chunks)])
    return "[Chunk 1]: Đây là nội dung mẫu từ RAG pipeline của bạn."

# ── MAIN CHAT FUNCTION ───────────────────────────────────
def chat(session_id: str, user_message: str) -> str:
    # 1. Lấy history hiện tại
    history = get_history(session_id)
    
    # 2. Trim theo sliding window
    trimmed_history = trim_history_sliding_window(history, MAX_TURNS)
    
    # 3. Retrieve RAG chunks
    rag_context = retrieve_rag_chunks(user_message, session_id)
    
    # 4. Build system prompt
    system_prompt = f"""Bạn là AI assistant hỗ trợ người dùng dựa trên kiến thức được cung cấp.

## NHIỆM VỤ
Trả lời dựa trên RAG context bên dưới. Nếu không có thông tin, nói rõ là không biết.
Bạn chỉ thấy {MAX_TURNS} turns gần nhất – nếu người dùng nhắc điều cũ hơn, lịch sự thông báo.

## RAG CONTEXT
<rag_context>
{rag_context}
</rag_context>

Session ID: {session_id}"""

    # 5. Build messages array (history + message mới)
    messages = trimmed_history + [{"role": "user", "content": user_message}]
    
    # 6. Gọi LLM
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_RESPONSE,
        system=system_prompt,
        messages=messages
    )
    
    assistant_reply = response.content[0].text
    
    # 7. Cập nhật history (lưu FULL history, trim khi đọc)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_reply})
    save_history(session_id, history)
    
    return assistant_reply


# ── USAGE ────────────────────────────────────────────────
if __name__ == "__main__":
    sid = "user_123_session_abc"
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break
        reply = chat(sid, user_input)
        print(f"Bot: {reply}\n")
```

---

## ═══════════════════════════════════════════
## PHƯƠNG ÁN 2 — TOKEN-BUDGET TRIMMING
## ═══════════════════════════════════════════

### 🎯 Mô tả
Phân bổ **ngân sách token cố định** cho từng phần: system (~500t), RAG (~3000t), history (~còn lại). Cắt history từ đầu cho đến khi tổng token nằm trong giới hạn.  
**Ưu:** Kiểm soát chi phí chính xác, không bao giờ vượt context window.  
**Nhược:** Phải đếm token thực tế, phức tạp hơn Sliding Window.

---

### 📋 SYSTEM PROMPT – TOKEN-BUDGET TRIMMING AGENT

```
SYSTEM PROMPT – RAG CHATBOT (Token-Budget Trimming Strategy)
=============================================================

Bạn là một AI assistant thông minh, hoạt động với ngân sách token được quản lý chặt chẽ.

## NHIỆM VỤ
Trả lời câu hỏi của người dùng dựa trên:
1. RAG Context: tài liệu liên quan được truy xuất (ưu tiên cao nhất)
2. Conversation History: lịch sử hội thoại (đã được cắt để đảm bảo token budget)
3. Câu hỏi hiện tại của người dùng

## PHÂN BỔ TOKEN BUDGET (tổng context window: ~8,000 tokens)
- System prompt (prompt này): ~500 tokens
- RAG Context: ~3,000 tokens  
- Conversation History: ~phần còn lại sau khi trừ system + RAG + user message
- User message hiện tại: ~200-500 tokens
- Response: ~1,000-1,500 tokens

## QUY TẮC XỬ LÝ
- Lịch sử hội thoại đã được tự động cắt để không vượt quá budget
- Nếu history bị cắt, một số thông tin từ đầu cuộc trò chuyện có thể bị mất
- Ưu tiên thông tin từ RAG Context hơn thông tin từ history
- Trả lời trung thực nếu không đủ thông tin

## FORMAT RAG CONTEXT
<rag_context>
{Nội dung chunks được truy xuất}
</rag_context>

Session: {SESSION_ID} | Token budget mode: ACTIVE
```

---

### 💻 Code Scaffold – Python (Token-Budget Trimming)

```python
import tiktoken
from anthropic import Anthropic

client = Anthropic()

# ── TOKEN BUDGET CONFIG ─────────────────────────────────
CONTEXT_WINDOW   = 8000   # Tổng context window (tokens)
SYSTEM_BUDGET    = 500    # Dành cho system prompt
RAG_BUDGET       = 3000   # Dành cho RAG chunks
RESPONSE_BUDGET  = 1200   # Dành cho response của model
HISTORY_BUDGET   = CONTEXT_WINDOW - SYSTEM_BUDGET - RAG_BUDGET - RESPONSE_BUDGET  # ~2300t

MODEL = "claude-opus-4-5"
sessions: dict[str, list] = {}

# ── TOKEN COUNTING ──────────────────────────────────────
def count_tokens(text: str) -> int:
    """Đếm token dùng tiktoken (cl100k_base ~ Claude tokenizer)"""
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

def count_messages_tokens(messages: list) -> int:
    total = 0
    for msg in messages:
        total += count_tokens(msg["content"]) + 4  # overhead per message
    return total

def trim_history_by_token_budget(history: list, budget: int) -> list:
    """
    Cắt history từ ĐẦU cho đến khi tổng token <= budget.
    Luôn giữ cặp turns gần nhất (2 messages cuối).
    """
    if not history:
        return history
    
    # Luôn giữ ít nhất 2 messages cuối (1 turn gần nhất)
    trimmed = list(history)
    
    while count_messages_tokens(trimmed) > budget and len(trimmed) > 2:
        # Xóa 2 messages đầu tiên (1 turn cũ nhất)
        trimmed = trimmed[2:]
    
    return trimmed

# ── RAG RETRIEVAL ────────────────────────────────────────
def retrieve_rag_chunks(query: str) -> str:
    # TODO: thay bằng RAG pipeline thực tế
    return "[Chunk 1]: Nội dung từ RAG\n[Chunk 2]: Nội dung từ RAG"

# ── MAIN CHAT FUNCTION ───────────────────────────────────
def chat(session_id: str, user_message: str) -> str:
    history = sessions.get(session_id, [])
    
    # 1. Retrieve RAG (cắt nếu vượt budget)
    rag_raw = retrieve_rag_chunks(user_message)
    rag_tokens = count_tokens(rag_raw)
    if rag_tokens > RAG_BUDGET:
        # Cắt bớt RAG text nếu quá dài
        enc = tiktoken.get_encoding("cl100k_base")
        rag_raw = enc.decode(enc.encode(rag_raw)[:RAG_BUDGET])
    
    # 2. Trim history theo token budget
    user_msg_tokens = count_tokens(user_message)
    available_for_history = HISTORY_BUDGET - user_msg_tokens
    trimmed_history = trim_history_by_token_budget(history, available_for_history)
    
    # 3. Build system prompt
    system_prompt = f"""Bạn là AI assistant hỗ trợ người dùng. Trả lời dựa trên RAG context.
Nếu không có thông tin, nói rõ là không biết. Session: {session_id}

## RAG CONTEXT (budget: {RAG_BUDGET} tokens)
<rag_context>
{rag_raw}
</rag_context>"""

    # 4. Build messages
    messages = trimmed_history + [{"role": "user", "content": user_message}]
    
    # 5. Gọi LLM
    response = client.messages.create(
        model=MODEL,
        max_tokens=RESPONSE_BUDGET,
        system=system_prompt,
        messages=messages
    )
    
    assistant_reply = response.content[0].text
    
    # 6. Lưu FULL history (trim khi đọc)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_reply})
    sessions[session_id] = history
    
    return assistant_reply
```

---

## ═══════════════════════════════════════════
## PHƯƠNG ÁN 3 — SUMMARIZATION
## ═══════════════════════════════════════════

### 🎯 Mô tả
Khi history quá dài, gọi thêm **1 LLM call để tóm tắt** toàn bộ phần cũ (~200 tokens). Kết quả lưu là `[summary]` + giữ nguyên `[N turns chi tiết gần nhất]`.  
**Ưu:** Hội thoại rất dài vẫn hoạt động tốt, không mất thông tin quan trọng.  
**Nhược:** Tốn thêm 1 LLM call mỗi lần trigger summarize, có thể mất chi tiết nhỏ.

---

### 📋 SYSTEM PROMPT – SUMMARIZATION AGENT (2 prompts)

**PROMPT A – Summarization Call (gọi riêng để tóm tắt)**
```
SYSTEM PROMPT – CONVERSATION SUMMARIZER
=========================================

Bạn là một AI chuyên tóm tắt hội thoại. Nhiệm vụ của bạn là tạo ra một bản tóm tắt ngắn gọn, súc tích về một đoạn hội thoại.

## YÊU CẦU TÓM TẮT
- Độ dài: tối đa 200 tokens (khoảng 150-200 từ tiếng Việt)
- Bao gồm: các chủ đề chính đã thảo luận, thông tin quan trọng người dùng đã chia sẻ, quyết định hoặc kết luận đã đưa ra
- KHÔNG bao gồm: những câu hỏi/trả lời không quan trọng, lời chào hỏi xã giao
- Format: văn xuôi, không dùng bullet points
- Ngôn ngữ: cùng ngôn ngữ với hội thoại gốc

## OUTPUT FORMAT
Chỉ trả về bản tóm tắt thuần túy, không có tiêu đề, không có giải thích thêm.
```

**PROMPT B – Main Chat Call (dùng summary + recent turns)**
```
SYSTEM PROMPT – RAG CHATBOT (Summarization Strategy)
=====================================================

Bạn là một AI assistant thông minh với khả năng nhớ hội thoại dài hạn thông qua cơ chế tóm tắt.

## CẤU TRÚC BỘ NHỚ CỦA BẠN
Bạn nhận được:
1. [CONVERSATION SUMMARY]: Tóm tắt phần đầu của cuộc hội thoại (nếu có)
2. [RECENT HISTORY]: {RECENT_TURNS} turns chi tiết gần nhất
3. [RAG CONTEXT]: Tài liệu liên quan được truy xuất
4. [USER MESSAGE]: Câu hỏi hiện tại

## CÁCH SỬ DỤNG BỘ NHỚ
- Summary cung cấp bức tranh tổng thể về những gì đã thảo luận trước đó
- Recent history cung cấp ngữ cảnh chi tiết ngay gần đây
- RAG context cung cấp kiến thức từ knowledge base
- Kết hợp cả ba nguồn để trả lời chính xác nhất

## QUY TẮC
- Ưu tiên RAG context cho thông tin fact
- Ưu tiên recent history cho ngữ cảnh cuộc trò chuyện
- Sử dụng summary để nhớ ý định/thông tin tổng quát từ trước
- Trả lời trung thực nếu thông tin không đủ

Session: {SESSION_ID}
```

---

### 💻 Code Scaffold – Python (Summarization)

```python
from anthropic import Anthropic
import tiktoken

client = Anthropic()
MODEL = "claude-opus-4-5"

# ── CONFIG ──────────────────────────────────────────────
RECENT_TURNS_KEEP = 5       # Số turns chi tiết giữ lại
SUMMARY_TRIGGER_TURNS = 15  # Trigger summarize khi history > N turns
SUMMARY_MAX_TOKENS = 250    # Max tokens cho summary
RESPONSE_MAX_TOKENS = 1024

# ── SESSION STORE ────────────────────────────────────────
sessions: dict[str, dict] = {}
# Format: {session_id: {"history": [...], "summary": "..."}}

def get_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {"history": [], "summary": ""}
    return sessions[session_id]

# ── SUMMARIZATION ────────────────────────────────────────
def summarize_old_turns(turns_to_summarize: list, existing_summary: str) -> str:
    """Gọi LLM để tóm tắt các turns cũ, có thể kết hợp với summary cũ."""
    
    # Format turns thành text
    history_text = ""
    if existing_summary:
        history_text += f"[Tóm tắt trước đó]: {existing_summary}\n\n"
    
    history_text += "[Hội thoại cần tóm tắt]:\n"
    for msg in turns_to_summarize:
        role = "Người dùng" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"
    
    response = client.messages.create(
        model=MODEL,
        max_tokens=SUMMARY_MAX_TOKENS,
        system="""Bạn là AI chuyên tóm tắt hội thoại. Tạo bản tóm tắt ngắn gọn (tối đa 200 tokens) 
về các chủ đề chính, thông tin quan trọng và kết luận. Văn xuôi, không bullet points.""",
        messages=[{"role": "user", "content": f"Tóm tắt hội thoại sau:\n\n{history_text}"}]
    )
    
    return response.content[0].text

def maybe_summarize(session_id: str):
    """Kiểm tra và trigger summarize nếu cần."""
    session = get_session(session_id)
    history = session["history"]
    
    # Chỉ trigger khi history vượt ngưỡng
    total_turns = len(history) // 2  # 2 messages = 1 turn
    if total_turns <= SUMMARY_TRIGGER_TURNS:
        return
    
    # Giữ lại RECENT_TURNS_KEEP * 2 messages cuối
    keep_messages = RECENT_TURNS_KEEP * 2
    old_turns = history[:-keep_messages]
    recent_turns = history[-keep_messages:]
    
    if old_turns:
        # Tóm tắt phần cũ
        new_summary = summarize_old_turns(old_turns, session["summary"])
        session["summary"] = new_summary
        session["history"] = recent_turns  # Chỉ giữ phần recent
        sessions[session_id] = session

# ── RAG RETRIEVAL ────────────────────────────────────────
def retrieve_rag_chunks(query: str) -> str:
    # TODO: thay bằng RAG pipeline thực tế
    return "[Chunk 1]: Nội dung RAG"

# ── MAIN CHAT ────────────────────────────────────────────
def chat(session_id: str, user_message: str) -> str:
    session = get_session(session_id)
    
    # 1. Lấy RAG context
    rag_context = retrieve_rag_chunks(user_message)
    
    # 2. Build system prompt với summary (nếu có)
    summary_section = ""
    if session["summary"]:
        summary_section = f"""
## TÓM TẮT HỘI THOẠI TRƯỚC ĐÓ
<conversation_summary>
{session["summary"]}
</conversation_summary>
"""
    
    system_prompt = f"""Bạn là AI assistant hỗ trợ người dùng. Session: {session_id}
{summary_section}
## RAG CONTEXT
<rag_context>
{rag_context}
</rag_context>

Kết hợp summary (bức tranh tổng thể) + recent history (chi tiết gần đây) + RAG context để trả lời.
Trả lời trung thực nếu không có đủ thông tin."""

    # 3. Recent history + message hiện tại
    messages = session["history"] + [{"role": "user", "content": user_message}]
    
    # 4. Gọi LLM
    response = client.messages.create(
        model=MODEL,
        max_tokens=RESPONSE_MAX_TOKENS,
        system=system_prompt,
        messages=messages
    )
    
    assistant_reply = response.content[0].text
    
    # 5. Cập nhật history
    session["history"].append({"role": "user", "content": user_message})
    session["history"].append({"role": "assistant", "content": assistant_reply})
    sessions[session_id] = session
    
    # 6. Check và trigger summarize nếu cần
    maybe_summarize(session_id)
    
    return assistant_reply
```

---

## ═══════════════════════════════════════════
## PHƯƠNG ÁN 4 — HYBRID RAG + MEMORY
## ═══════════════════════════════════════════

### 🎯 Mô tả
Kết hợp 3 nguồn: **Vector DB** (RAG từ knowledge base) + **Short-term memory** (recent turns, trong RAM/Redis) + **Long-term memory** (summary/facts quan trọng, lưu Postgres). Giống cách hoạt động của ChatGPT/Claude nhất.  
**Ưu:** Trải nghiệm tốt nhất, nhớ cả ngắn hạn và dài hạn.  
**Nhược:** Phức tạp, cần infra nhiều hơn (Vector DB + Redis + Postgres).

---

### 📋 SYSTEM PROMPT – HYBRID RAG + MEMORY AGENT

```
SYSTEM PROMPT – RAG CHATBOT (Hybrid Memory Strategy)
=====================================================

Bạn là một AI assistant thông minh với hệ thống bộ nhớ đa tầng, tương tự như ChatGPT hay Claude.

## HỆ THỐNG BỘ NHỚ 3 TẦNG

### Tầng 1 – RAG Knowledge Base (Vector DB)
Thông tin từ tài liệu/knowledge base của hệ thống, được truy xuất theo semantic similarity.
→ Dùng cho: câu hỏi về thông tin, facts, hướng dẫn

### Tầng 2 – Short-term Memory (Session Memory)
{RECENT_TURNS} turns hội thoại chi tiết gần nhất trong phiên làm việc hiện tại.
→ Dùng cho: ngữ cảnh ngay gần đây, follow-up questions

### Tầng 3 – Long-term Memory (Persistent Memory)  
Thông tin quan trọng về người dùng và sở thích đã được trích xuất từ các phiên trước.
Format: danh sách các facts ngắn gọn.
→ Dùng cho: cá nhân hóa, nhớ preferences, nhớ thông tin user đã chia sẻ

## CÁCH KẾT HỢP BỘ NHỚ
1. Tham khảo Long-term memory để hiểu người dùng (preferences, context cá nhân)
2. Tham khảo RAG context để trả lời chính xác về nội dung
3. Tham khảo Short-term memory để duy trì mạch hội thoại
4. Tổng hợp để đưa ra câu trả lời cá nhân hóa và chính xác nhất

## QUY TẮC TRÍCH XUẤT LONG-TERM MEMORY
Sau mỗi câu trả lời, nếu người dùng chia sẻ thông tin cá nhân quan trọng (tên, nghề nghiệp, sở thích, vấn đề đang gặp phải), hãy ghi nhớ để cập nhật long-term memory.

## QUY TẮC CHUNG
- KHÔNG bịa đặt thông tin
- Trả lời bằng ngôn ngữ của người dùng
- Nếu không có thông tin từ bất kỳ tầng nào, trả lời trung thực

Session: {SESSION_ID} | User: {USER_ID}
```

---

### 💻 Code Scaffold – Python (Hybrid Memory)

```python
import json
from anthropic import Anthropic
# pip install redis psycopg2-binary

client = Anthropic()
MODEL = "claude-opus-4-5"

# ── CONFIG ──────────────────────────────────────────────
SHORT_TERM_TURNS = 8          # Turns giữ trong short-term memory
LONG_TERM_MAX_FACTS = 20      # Số facts tối đa trong long-term memory
RESPONSE_MAX_TOKENS = 1024
MEMORY_EXTRACT_TOKENS = 200   # Tokens cho việc trích xuất memory

# ── STORAGE (simplified - dùng dict thay Redis/Postgres) ─
short_term_store: dict[str, list] = {}   # Redis trong production
long_term_store: dict[str, list] = {}    # Postgres trong production

# ── SHORT-TERM MEMORY ────────────────────────────────────
def get_short_term(session_id: str) -> list:
    return short_term_store.get(session_id, [])

def update_short_term(session_id: str, user_msg: str, assistant_msg: str):
    history = get_short_term(session_id)
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": assistant_msg})
    # Trim to SHORT_TERM_TURNS
    max_msgs = SHORT_TERM_TURNS * 2
    short_term_store[session_id] = history[-max_msgs:]

# ── LONG-TERM MEMORY ─────────────────────────────────────
def get_long_term(user_id: str) -> list:
    return long_term_store.get(user_id, [])

def extract_and_update_long_term(user_id: str, user_message: str, assistant_reply: str):
    """Dùng LLM để trích xuất facts quan trọng từ turn hiện tại."""
    existing_facts = get_long_term(user_id)
    
    extract_prompt = f"""Từ đoạn hội thoại sau, trích xuất thông tin quan trọng về người dùng (nếu có).
Chỉ lấy: tên, nghề nghiệp, sở thích, vấn đề đang gặp, preferences, mục tiêu.
KHÔNG trích xuất những câu hỏi thông thường hoặc câu trả lời của assistant.

Hội thoại:
User: {user_message}
Assistant: {assistant_reply}

Existing facts đã biết: {json.dumps(existing_facts, ensure_ascii=False)}

Trả về JSON array các facts mới cần thêm vào (hoặc [] nếu không có gì mới).
Format: ["fact 1", "fact 2", ...]
Chỉ trả về JSON, không có text khác."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=MEMORY_EXTRACT_TOKENS,
        messages=[{"role": "user", "content": extract_prompt}]
    )
    
    try:
        new_facts = json.loads(response.content[0].text)
        if new_facts:
            all_facts = existing_facts + new_facts
            # Giữ tối đa LONG_TERM_MAX_FACTS facts mới nhất
            long_term_store[user_id] = all_facts[-LONG_TERM_MAX_FACTS:]
    except json.JSONDecodeError:
        pass  # Không update nếu parse lỗi

# ── RAG RETRIEVAL ────────────────────────────────────────
def retrieve_rag_chunks(query: str) -> str:
    # TODO: thay bằng RAG pipeline thực tế
    return "[Chunk 1]: Nội dung từ Vector DB"

def semantic_search_long_term(query: str, user_id: str) -> list:
    """
    Optional: Dùng embedding để tìm facts trong long-term memory liên quan đến query.
    Simplified: trả về tất cả facts.
    """
    return get_long_term(user_id)

# ── BUILD PROMPT BUILDER ─────────────────────────────────
def build_context_prompt(session_id: str, user_id: str, user_message: str) -> tuple[str, list]:
    """Tổng hợp 3 tầng memory vào system prompt + messages."""
    
    # Layer 1: RAG
    rag_context = retrieve_rag_chunks(user_message)
    
    # Layer 2: Short-term memory
    short_term = get_short_term(session_id)
    
    # Layer 3: Long-term memory (filtered by relevance)
    long_term_facts = semantic_search_long_term(user_message, user_id)
    
    # Build long-term section
    long_term_section = ""
    if long_term_facts:
        facts_text = "\n".join([f"- {fact}" for fact in long_term_facts])
        long_term_section = f"""
## 📚 LONG-TERM MEMORY (Thông tin về người dùng)
<long_term_memory>
{facts_text}
</long_term_memory>
"""
    
    system_prompt = f"""Bạn là AI assistant thông minh với bộ nhớ đa tầng.
Session: {session_id} | User: {user_id}
{long_term_section}
## 🔍 RAG KNOWLEDGE BASE
<rag_context>
{rag_context}
</rag_context>

## HƯỚNG DẪN
- Long-term memory: hiểu người dùng, cá nhân hóa câu trả lời
- RAG context: nguồn thông tin chính xác từ knowledge base  
- Short-term memory (trong messages[]): duy trì mạch hội thoại
- Kết hợp cả 3 để đưa ra câu trả lời tốt nhất
- Không bịa đặt thông tin"""

    messages = short_term + [{"role": "user", "content": user_message}]
    
    return system_prompt, messages

# ── MAIN CHAT ────────────────────────────────────────────
def chat(session_id: str, user_id: str, user_message: str) -> str:
    # 1. Build context từ 3 tầng memory
    system_prompt, messages = build_context_prompt(session_id, user_id, user_message)
    
    # 2. Gọi LLM
    response = client.messages.create(
        model=MODEL,
        max_tokens=RESPONSE_MAX_TOKENS,
        system=system_prompt,
        messages=messages
    )
    
    assistant_reply = response.content[0].text
    
    # 3. Cập nhật short-term memory
    update_short_term(session_id, user_message, assistant_reply)
    
    # 4. Async: trích xuất và cập nhật long-term memory
    # Trong production nên dùng background task (Celery, asyncio)
    extract_and_update_long_term(user_id, user_message, assistant_reply)
    
    return assistant_reply
```

---

## ═══════════════════════════════════════════
## STORAGE LAYER – REDIS & POSTGRESQL
## ═══════════════════════════════════════════

### 📦 Redis (Dev / Small Scale – có TTL)

```python
import redis
import json
from datetime import timedelta

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
SESSION_TTL = timedelta(hours=24)  # Session tự hết hạn sau 24h

def redis_get_history(session_id: str) -> list:
    data = r.get(f"session:{session_id}:history")
    return json.loads(data) if data else []

def redis_save_history(session_id: str, history: list):
    r.setex(
        f"session:{session_id}:history",
        SESSION_TTL,
        json.dumps(history, ensure_ascii=False)
    )

def redis_get_summary(session_id: str) -> str:
    return r.get(f"session:{session_id}:summary") or ""

def redis_save_summary(session_id: str, summary: str):
    r.setex(f"session:{session_id}:summary", SESSION_TTL, summary)
```

### 📦 PostgreSQL (Production – durable, persistent)

```sql
-- Schema
CREATE TABLE chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id    VARCHAR(255) NOT NULL,
    history    JSONB DEFAULT '[]',
    summary    TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_long_term_memory (
    user_id    VARCHAR(255) PRIMARY KEY,
    facts      JSONB DEFAULT '[]',
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id ON chat_sessions(user_id);
```

```python
import psycopg2
import json

conn = psycopg2.connect("postgresql://user:pass@localhost/ragdb")

def pg_get_session(session_id: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT history, summary FROM chat_sessions WHERE session_id = %s",
            (session_id,)
        )
        row = cur.fetchone()
        if row:
            return {"history": row[0], "summary": row[1]}
        return {"history": [], "summary": ""}

def pg_save_session(session_id: str, user_id: str, history: list, summary: str = ""):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO chat_sessions (session_id, user_id, history, summary, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (session_id) DO UPDATE 
            SET history = EXCLUDED.history, 
                summary = EXCLUDED.summary,
                updated_at = NOW()
        """, (session_id, user_id, json.dumps(history), summary))
    conn.commit()

def pg_get_long_term(user_id: str) -> list:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT facts FROM user_long_term_memory WHERE user_id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        return row[0] if row else []

def pg_save_long_term(user_id: str, facts: list):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO user_long_term_memory (user_id, facts, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE
            SET facts = EXCLUDED.facts, updated_at = NOW()
        """, (user_id, json.dumps(facts)))
    conn.commit()
```

---

## ═══════════════════════════════════════════
## LỘ TRÌNH KHUYẾN NGHỊ TRIỂN KHAI
## ═══════════════════════════════════════════

```
Bước 1 → Sliding Window
  └── Đơn giản, test nhanh, deploy ngay
  └── Storage: in-memory dict hoặc Redis

Bước 2 → Token-budget Trimming
  └── Khi bạn cần kiểm soát chi phí API chính xác
  └── Storage: Redis với TTL

Bước 3 → + Summarization
  └── Khi users có hội thoại rất dài (>20 turns)
  └── Storage: Redis (short) + Postgres (summary)

Bước 4 → Hybrid Memory
  └── Production scale, cần UX tốt nhất
  └── Storage: Redis + Postgres + Vector DB
```

---

## ═══════════════════════════════════════════
## CHECKLIST TRƯỚC KHI DEPLOY
## ═══════════════════════════════════════════

```
□ session_id là unique per user per conversation
□ Mỗi API call gửi đủ messages[] (không thiếu history)
□ System prompt không thay đổi giữa các turns trong cùng session
□ RAG retrieval chạy trước khi build prompt (không async riêng)
□ Error handling: nếu LLM call lỗi, không update history
□ Token counting được test với dữ liệu thực
□ TTL trên Redis phù hợp với use case (24h? 7 ngày?)
□ Postgres có index trên session_id và user_id
□ Long-term memory extract chạy async (không block response)
□ Logging: log session_id, token count, phương án dùng cho mỗi request
```

---

*Generated for RAG Chatbot Deployment – Phần RAG đã hoàn thiện, prompt này tập trung vào Context & Memory Management.*
