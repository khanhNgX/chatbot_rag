# -*- coding: utf-8 -*-
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from phase2_embedding import EmbeddingGenerator
from automation_ai_rag import AIAutomation
from phase5_llm_generation import LLMGenerator


load_dotenv()


def _preview(text: str, limit: int = 500) -> str:
    t = (text or "").replace("\n", " ").strip()
    if len(t) <= limit:
        return t
    return t[:limit] + " ..."


def _print_section(title: str):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def _load_sample_chunks(max_items: int = 8) -> List[Dict[str, Any]]:
    if not os.path.exists("all_chunks.json"):
        return []
    try:
        with open("all_chunks.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data[:max_items]
    except Exception as e:
        print(f"[WARN] Không đọc được all_chunks.json: {e}")
    return []


def check_embedding_flow() -> Dict[str, Any]:
    _print_section("FLOW 1/3 - EMBEDDING (Gemini)")

    samples = _load_sample_chunks(max_items=1)
    if not samples:
        print("[FAIL] Không có all_chunks.json hoặc file rỗng.")
        return {"ok": False, "reason": "missing_chunks"}

    chunk = samples[0]
    emb = EmbeddingGenerator()

    prepared_text = emb.prepare_text_for_embedding(chunk)
    print("[INPUT] prepare_text_for_embedding")
    print(f"- chunk_id: {chunk.get('chunk_id')}")
    print(f"- text_len: {len(prepared_text)}")
    print(f"- preview: {_preview(prepared_text)}")

    vector = emb.generate_embedding(prepared_text)
    all_zero = bool(vector) and not any(abs(float(v)) > 1e-12 for v in vector)

    print("[OUTPUT] generate_embedding")
    print(f"- vector_dim: {len(vector)}")
    print(f"- all_zero_vector: {all_zero}")
    if vector:
        print(f"- first_8_values: {vector[:8]}")

    input_ok = len(prepared_text.strip()) > 20
    output_ok = len(vector) > 0 and not all_zero

    print("[ASSESSMENT]")
    print(f"- input_ok: {input_ok}")
    print(f"- output_ok: {output_ok}")

    return {
        "ok": input_ok and output_ok,
        "input_ok": input_ok,
        "output_ok": output_ok,
        "vector_dim": len(vector),
        "all_zero": all_zero,
    }


def check_query_rewrite_flow() -> Dict[str, Any]:
    _print_section("FLOW 2/3 - QUERY REWRITE/AUTOMATION (Groq)")

    auto = AIAutomation()
    query = "Bước 1 của phần 4 là gì và cần giấy tờ nào?"

    original_call = auto.ai.call

    def wrapped_call(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        print("[INPUT] AIService.call")
        print(f"- json_mode: {json_mode}")
        print(f"- system_prompt_len: {len(system_prompt or '')}")
        print(f"- system_prompt_preview: {_preview(system_prompt, 400)}")
        print(f"- user_prompt_len: {len(user_prompt or '')}")
        print(f"- user_prompt_preview: {_preview(user_prompt, 400)}")

        raw = original_call(system_prompt, user_prompt, json_mode)
        print("[RAW OUTPUT] AIService.call")
        print(f"- raw_len: {len(raw or '')}")
        print(f"- raw_preview: {_preview(raw, 500)}")
        return raw

    auto.ai.call = wrapped_call

    result = auto.process_user_query(query)

    print("[OUTPUT] process_user_query")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    input_ok = len(query.strip()) > 5
    output_ok = isinstance(result, dict) and bool(result.get("refined_query")) and bool(result.get("detected_topic"))

    print("[ASSESSMENT]")
    print(f"- input_ok: {input_ok}")
    print(f"- output_ok: {output_ok}")

    return {
        "ok": input_ok and output_ok,
        "input_ok": input_ok,
        "output_ok": output_ok,
        "detected_topic": result.get("detected_topic"),
    }


def check_generation_flow() -> Dict[str, Any]:
    _print_section("FLOW 3/3 - ANSWER GENERATION (Groq)")

    key = (os.getenv("GROQ_API_KEY") or "").strip()
    generator = LLMGenerator(key)

    chunks = _load_sample_chunks(max_items=8)
    if not chunks:
        print("[FAIL] Không có chunk để test generation.")
        return {"ok": False, "reason": "missing_chunks"}

    query = f"Hãy giải thích tổng quan thủ tục nhập học 2025 theo ngôn ngữ dễ hiểu (debug {datetime.now().strftime('%H%M%S')})"
    analysis = {
        "raw_query": query,
        "intent": "general",
        "entities": {},
        "query_frame": {},
    }
    os.environ["DEBUG_FORCE_LLM"] = "1"
    os.environ["DEBUG_DISABLE_CACHE"] = "1"
    print("[NOTE] Force generation path: intent=general (để đi nhánh LLM thay vì deterministic)")

    context_prompt = generator.prompt_engineer.create_context_prompt(chunks)
    full_prompt = generator.prompt_engineer.create_full_prompt(query, chunks)

    print("[INPUT] prompt_engineer")
    print(f"- chunks_count: {len(chunks)}")
    print(f"- context_prompt_len: {len(context_prompt)}")
    print(f"- context_prompt_preview: {_preview(context_prompt, 500)}")
    print(f"- full_prompt_len: {len(full_prompt)}")
    print(f"- full_prompt_preview: {_preview(full_prompt, 500)}")

    original_call = generator._call_llm

    def wrapped_call(unified_prompt: str) -> Dict[str, Any]:
        print("[INPUT] _call_llm")
        print(f"- llm_prompt_len: {len(unified_prompt or '')}")
        print(f"- llm_prompt_preview: {_preview(unified_prompt, 700)}")

        out = original_call(unified_prompt)
        print("[RAW OUTPUT] _call_llm")
        print(f"- status: {out.get('status')}")
        if out.get("text"):
            print(f"- text_preview: {_preview(out.get('text'), 700)}")
        if out.get("error"):
            print(f"- error: {out.get('error')}")
        return out

    generator._call_llm = wrapped_call

    result = generator.generate(
        query=query,
        chunks=chunks,
        intent="deadlines_summary",
        chat_history=[],
        analysis=analysis,
        session_id="debug_session",
        user_id="debug_user",
        style_id="formal",
        force_llm=True,
    )

    print("[OUTPUT] generate")
    print(f"- success: {result.get('success')}")
    print(f"- source: {result.get('source')}")
    print(f"- answer_len: {len(result.get('answer') or '')}")
    print(f"- answer_preview: {_preview(result.get('answer') or '', 700)}")

    input_ok = len(full_prompt.strip()) > 20
    output_ok = bool(result.get("success")) and len((result.get("answer") or "").strip()) > 20

    print("[ASSESSMENT]")
    print(f"- input_ok: {input_ok}")
    print(f"- output_ok: {output_ok}")

    return {
        "ok": input_ok and output_ok,
        "input_ok": input_ok,
        "output_ok": output_ok,
        "source": result.get("source"),
    }


def main():
    tests_dir = os.path.dirname(__file__)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(tests_dir, f"llm_pipeline_io_debug_{ts}.txt")

    class _Tee:
        def __init__(self, *streams):
            self.streams = streams

        def write(self, data):
            for s in self.streams:
                s.write(data)
            return len(data)

        def flush(self):
            for s in self.streams:
                s.flush()

    original_stdout = sys.stdout
    with open(output_path, "w", encoding="utf-8") as out_file:
        sys.stdout = _Tee(original_stdout, out_file)
        try:
            print("[NOTE] Script này gọi API thật (Groq/Gemini), có thể tốn quota.")
            print(f"[NOTE] Log output file: {output_path}")

            summary = {}
            try:
                summary["embedding"] = check_embedding_flow()
            except Exception as e:
                print(f"[ERROR] embedding flow crash: {e}")
                summary["embedding"] = {"ok": False, "error": str(e)}

            try:
                summary["rewrite"] = check_query_rewrite_flow()
            except Exception as e:
                print(f"[ERROR] rewrite flow crash: {e}")
                summary["rewrite"] = {"ok": False, "error": str(e)}

            try:
                summary["generation"] = check_generation_flow()
            except Exception as e:
                print(f"[ERROR] generation flow crash: {e}")
                summary["generation"] = {"ok": False, "error": str(e)}

            _print_section("FINAL SUMMARY")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        finally:
            sys.stdout = original_stdout

    print(f"[OK] Saved debug log to: {output_path}")


if __name__ == "__main__":
    main()
