# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from phase5_llm_generation import LLMGenerator, ResponseFormatter


class TestGoldenAnswers(unittest.TestCase):
    def setUp(self):
        self.formatter = ResponseFormatter()

    def test_golden_fee_info_answer_keeps_amounts_total_and_source(self):
        chunks = [
            {
                "chunk_id": "fee_1",
                "content": "Tiền làm hồ sơ, tài liệu: 50.000đ",
                "metadata": {"intent_key": "fee_info", "subtype": "fee_item", "item_no": 1, "amount": 50000, "section_id": "phan_3", "year": 2025, "source": "Thủ tục nhập học 2025.txt"},
                "source": "Thủ tục nhập học 2025.txt",
            },
            {
                "chunk_id": "fee_2",
                "content": "Hồ sơ sức khỏe, khám sức khỏe: 180.000đ",
                "metadata": {"intent_key": "fee_info", "subtype": "fee_item", "item_no": 2, "amount": 180000, "section_id": "phan_3", "year": 2025, "source": "Thủ tục nhập học 2025.txt"},
                "source": "Thủ tục nhập học 2025.txt",
            },
            {
                "chunk_id": "fee_3",
                "content": "Bảo hiểm Y tế bắt buộc: 789.750đ",
                "metadata": {"intent_key": "fee_info", "subtype": "fee_item", "item_no": 3, "amount": 789750, "section_id": "phan_3", "year": 2025, "source": "Thủ tục nhập học 2025.txt"},
                "source": "Thủ tục nhập học 2025.txt",
            },
        ]

        answer = self.formatter.deterministic_answer("học phí bao nhiêu", chunks, intent="fee_info")

        self.assertIn("Các khoản phí cần nộp", answer)
        self.assertIn("50,000đ", answer)
        self.assertIn("180,000đ", answer)
        self.assertIn("789,750đ", answer)
        self.assertIn("Tổng cộng: 1,019,750đ", answer)
        self.assertIn("[SOURCE]", answer)
        self.assertIn("PHẦN 3", answer)

    def test_golden_local_steps_overview_answer_keeps_b1_to_b4(self):
        chunks = [
            {
                "chunk_id": "steps_group",
                "content": "B1: Chuẩn bị hồ sơ B2: Chụp ảnh chân dung B3: Tải ảnh/hồ sơ lên hệ thống B4: Nộp hồ sơ bản giấy trực tiếp",
                "metadata": {"intent_key": "admission_procedure", "subtype": "steps_group", "section_id": "phan_4", "year": 2025, "source": "Thủ tục nhập học 2025.txt"},
                "source": "Thủ tục nhập học 2025.txt",
            }
        ]
        analysis = {"entities": {"ask_steps_overview_local": True}}

        answer = self.formatter.deterministic_answer("các bước nộp hồ sơ", chunks, intent="admission_procedure", analysis=analysis)

        self.assertIn("Các bước nộp hồ sơ gồm", answer)
        for label in ["B1", "B2", "B3", "B4"]:
            self.assertIn(label, answer)
        self.assertIn("[SOURCE]", answer)

    def test_golden_global_procedure_overview_answer_keeps_four_sections(self):
        chunks = [
            {
                "chunk_id": "overview",
                "content": "PHẦN 1: Tra cứu danh sách trúng tuyển\nPHẦN 2: Xác nhận nhập học trực tuyến\nPHẦN 3: Nộp học phí/lệ phí\nPHẦN 4: Chuẩn bị và nộp hồ sơ",
                "metadata": {"intent_key": "admission_procedure", "subtype": "procedure_overview", "year": 2025, "source": "Thủ tục nhập học 2025.txt"},
                "source": "Thủ tục nhập học 2025.txt",
            }
        ]
        analysis = {"entities": {"ask_steps_overview_global": True}}

        answer = self.formatter.deterministic_answer("tóm tắt thủ tục nhập học", chunks, intent="admission_procedure", analysis=analysis)

        self.assertIn("Tóm tắt thủ tục nhập học", answer)
        for label in ["PHẦN 1", "PHẦN 2", "PHẦN 3", "PHẦN 4"]:
            self.assertIn(label, answer)
        self.assertIn("[SOURCE]", answer)

    def test_golden_schedule_by_major_answer_keeps_major_slot_date(self):
        chunks = [
            {
                "chunk_id": "sched_toan",
                "content": "Toán học nhập học buổi sáng ngày 27/8/2025",
                "metadata": {"intent_key": "schedule_by_major", "subtype": "schedule_major", "major": "Toán học", "major_norm": "toan hoc", "time_slot": "sáng", "date": "27/8/2025", "year": 2025, "source": "Thủ tục nhập học 2025.txt"},
                "source": "Thủ tục nhập học 2025.txt",
            }
        ]
        analysis = {"raw_query": "ngành toán học nhập học lúc nào", "entities": {"major_norm": "toan hoc"}}

        answer = self.formatter.deterministic_answer("ngành toán học nhập học lúc nào", chunks, intent="schedule_by_major", analysis=analysis)

        self.assertIn("Lịch nộp hồ sơ bản giấy theo ngành", answer)
        self.assertIn("Toán học", answer)
        self.assertIn("sáng", answer)
        self.assertIn("27/8/2025", answer)
        self.assertIn("[SOURCE]", answer)

    def test_golden_section_navigation_answer_is_short_by_default(self):
        chunks = [
            {
                "chunk_id": "section_3",
                "content": "PHẦN 3: Nộp học phí tạm thu, lệ phí nhập học theo hình thức chuyển khoản. Các khoản tiền: 1. Tiền làm hồ sơ: 50.000đ",
                "metadata": {"intent_key": "admission_procedure", "subtype": "section_3", "section_id": "phan_3", "year": 2025, "source": "Thủ tục nhập học 2025.txt"},
                "source": "Thủ tục nhập học 2025.txt",
            }
        ]
        analysis = {"raw_query": "phần 3 là gì", "query_frame": {"nav_target_candidates": ["phan_3"]}}

        answer = self.formatter.deterministic_answer("phần 3 là gì", chunks, intent="admission_procedure", analysis=analysis)

        self.assertIn("Nộp học phí", answer)
        self.assertNotIn("Các khoản tiền", answer)
        self.assertIn("[SOURCE]", answer)

    def test_naturalized_global_overview_keeps_facts_and_sounds_friendlier(self):
        original = "Tóm tắt thủ tục nhập học (ngắn gọn) như sau:\n- PHẦN 1: Tra cứu danh sách trúng tuyển.\n- PHẦN 2: Xác nhận nhập học trực tuyến.\n- PHẦN 3: Nộp học phí/lệ phí.\n- PHẦN 4: Chuẩn bị và nộp hồ sơ.\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (Năm 2025)"

        answer = LLMGenerator._safe_style_variation(original, "friendly_v0")

        self.assertIn("Mình tóm tắt", answer)
        for label in ["PHẦN 1", "PHẦN 2", "PHẦN 3", "PHẦN 4"]:
            self.assertIn(label, answer)
        self.assertIn("[SOURCE]", answer)

    def test_naturalized_schedule_keeps_date_and_source(self):
        original = "Lịch nộp hồ sơ bản giấy theo ngành:\n- Toán học: sáng ngày 27/8/2025\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (Năm 2025)"

        answer = LLMGenerator._safe_style_variation(original, "formal_v0")

        self.assertIn("Theo tài liệu", answer)
        self.assertIn("Toán học", answer)
        self.assertIn("sáng", answer)
        self.assertIn("27/8/2025", answer)
        self.assertIn("[SOURCE]", answer)

    def test_naturalized_single_line_section_keeps_section_and_source(self):
        original = "- Nộp học phí tạm thu, lệ phí nhập học.\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 3, Năm 2025)"

        answer = LLMGenerator._safe_style_variation(original, "friendly_v0")

        self.assertIn("Bạn cần lưu ý", answer)
        self.assertIn("Nộp học phí", answer)
        self.assertIn("PHẦN 3", answer)
        self.assertIn("[SOURCE]", answer)

    def test_gemini_naturalizer_accepts_safe_rewrite(self):
        generator = LLMGenerator(api_key="")
        original = "Lịch nộp hồ sơ bản giấy theo ngành:\n- Toán học: sáng ngày 27/8/2025\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (Năm 2025)"
        generator._call_gemini_naturalizer = lambda answer, style_id: {
            "status": "ok",
            "text": "Theo tài liệu, ngành Toán học nộp hồ sơ bản giấy vào buổi sáng ngày 27/8/2025.\n\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (Năm 2025)"
        }

        answer, trace = generator._naturalize_answer(original, "friendly_v0")

        self.assertIn("Theo tài liệu", answer)
        self.assertIn("Toán học", answer)
        self.assertIn("27/8/2025", answer)
        self.assertIn("[SOURCE]", answer)
        self.assertTrue(trace.get("gemini_applied"))

    def test_gemini_naturalizer_rejects_missing_date(self):
        generator = LLMGenerator(api_key="")
        original = "Lịch nộp hồ sơ bản giấy theo ngành:\n- Toán học: sáng ngày 27/8/2025\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (Năm 2025)"
        generator._call_gemini_naturalizer = lambda answer, style_id: {
            "status": "ok",
            "text": "Theo tài liệu, ngành Toán học nộp hồ sơ bản giấy vào buổi sáng.\n\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (Năm 2025)"
        }

        answer, trace = generator._naturalize_answer(original, "friendly_v0")

        self.assertIn("27/8/2025", answer)
        self.assertIn("gemini_rejected", trace)

    def test_gemini_naturalizer_rejects_new_money(self):
        generator = LLMGenerator(api_key="")
        original = "Các khoản phí cần nộp:\n- Tiền làm hồ sơ, tài liệu: 50,000đ\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (Năm 2025)"
        generator._call_gemini_naturalizer = lambda answer, style_id: {
            "status": "ok",
            "text": "Bạn cần nộp tiền làm hồ sơ, tài liệu là 50,000đ và thêm khoản 10,000đ.\n\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (Năm 2025)"
        }

        answer, trace = generator._naturalize_answer(original, "friendly_v0")

        self.assertIn("50,000đ", answer)
        self.assertNotIn("10,000đ", answer)
        self.assertEqual(trace.get("gemini_rejected"), "added_new_fact_tokens")

    def test_gemini_naturalizer_disabled_keeps_rule_based_output(self):
        generator = LLMGenerator(api_key="")
        original = "Tóm tắt thủ tục nhập học (ngắn gọn) như sau:\n- PHẦN 1: Tra cứu danh sách trúng tuyển.\n- PHẦN 2: Xác nhận nhập học trực tuyến.\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (Năm 2025)"
        generator._call_gemini_naturalizer = lambda answer, style_id: {"status": "disabled", "reason": "missing_GEMINI_API_KEY"}

        answer, trace = generator._naturalize_answer(original, "friendly_v0")

        self.assertIn("Mình tóm tắt", answer)
        self.assertEqual(trace.get("gemini_status"), "disabled")
        self.assertEqual(trace.get("gemini_reason"), "missing_GEMINI_API_KEY")


if __name__ == "__main__":
    unittest.main()
