# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from automation_retriever import AutomationRetriever
from phase5_llm_generation import ResponseFormatter


class _DummyVectorStorage:
    def query(self, *args, **kwargs):
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


class TestProcedureStepCountResolution(unittest.TestCase):
    def setUp(self):
        self._patch_vs = patch('automation_retriever.VectorStorage', return_value=_DummyVectorStorage())
        self._patch_vs.start()
        self.addCleanup(self._patch_vs.stop)
        self._patch_ai = patch('automation_retriever.AIAutomation.process_user_query', side_effect=lambda query: {'refined_query': query, 'detected_topic': 'general'})
        self._patch_ai.start()
        self.addCleanup(self._patch_ai.stop)
        self.retriever = AutomationRetriever()
        self.formatter = ResponseFormatter()

    def test_global_procedure_may_buoc_maps_to_section_count(self):
        analysis = self.retriever.analyze("thủ tục nhập học có mấy bước", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        entities = analysis.get("entities") or {}
        self.assertTrue(entities.get("ask_section_count"))
        self.assertFalse(entities.get("ask_step_count_local", False))

    def test_where_filter_not_forced_to_phan1_when_section_count(self):
        entities = {"ask_section_count": True}
        frame = {"nav_target_candidates": ["phan_1"]}
        where = self.retriever._build_where_filter("admission_procedure", entities, query_frame=frame)
        self.assertIsNone(where)

    def test_formatter_returns_section_count_summary(self):
        chunks = [
            {
                "content": "PHẦN 1: Tra cứu\nPHẦN 2: Xác nhận\nPHẦN 3: Học phí\nPHẦN 4: Hồ sơ",
                "metadata": {"subtype": "procedure_overview", "intent_key": "admission_procedure", "source": "Thủ tục nhập học 2025.txt"}
            }
        ]
        analysis = {"entities": {"ask_section_count": True}}
        out = self.formatter.format_admission_procedure(chunks, analysis=analysis)
        self.assertIsNotNone(out)
        self.assertIn("gồm 4 phần lớn", out)

    def test_local_ho_so_may_buoc_maps_to_local_step_count(self):
        analysis = self.retriever.analyze("phần 4 nộp hồ sơ có mấy bước", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertTrue(entities.get("ask_step_count_local"))

    def test_formatter_returns_local_step_count_summary(self):
        chunks = [
            {
                "content": "B1: Chuẩn bị hồ sơ\nB2: Chụp ảnh\nB3: Upload\nB4: Nộp bản giấy",
                "metadata": {"subtype": "steps_overview", "intent_key": "admission_procedure", "source": "Thủ tục nhập học 2025.txt"}
            }
        ]
        analysis = {"entities": {"ask_step_count_local": True}}
        out = self.formatter.format_admission_procedure(chunks, analysis=analysis)
        self.assertIsNotNone(out)
        self.assertIn("Phần nộp hồ sơ gồm 4 bước", out)

    def test_formatter_returns_section_content_without_day_la_phan_prefix(self):
        chunks = [
            {
                "content": "PHẦN 1: Tra cứu danh sách trúng tuyển trên hệ thống",
                "metadata": {
                    "subtype": "section_phan_1",
                    "intent_key": "admission_procedure",
                    "section_id": "phan_1",
                    "source": "Thủ tục nhập học 2025.txt"
                }
            },
            {
                "content": "PHẦN 2: Xác nhận nhập học trực tuyến trước hạn",
                "metadata": {
                    "subtype": "section_phan_2",
                    "intent_key": "admission_procedure",
                    "section_id": "phan_2",
                    "source": "Thủ tục nhập học 2025.txt"
                }
            }
        ]
        analysis = {"query_frame": {"nav_target_candidates": ["phan_1"]}}
        out = self.formatter.format_admission_procedure(chunks, analysis=analysis)
        self.assertIsNotNone(out)
        self.assertIn("Tra cứu danh sách trúng tuyển", out)
        self.assertNotIn("Đây là PHẦN", out)

    def test_formatter_section3_returns_only_first_description_line(self):
        chunks = [
            {
                "content": "Nộp học phí tạm thu, lệ phí nhập học...theo hình thức chuyển khoản (thực hiện từ ngày 25/8/2025 đến hết ngày 05/9/2025)\nCác khoản tiền: 1. Tiền làm hồ sơ...",
                "metadata": {
                    "subtype": "section_3",
                    "intent_key": "admission_procedure",
                    "section_id": "phan_3",
                    "source": "Thủ tục nhập học 2025.txt"
                }
            }
        ]
        analysis = {"query_frame": {"nav_target_candidates": ["phan_3"]}}
        out = self.formatter.format_admission_procedure(chunks, analysis=analysis)
        self.assertIsNotNone(out)
        self.assertIn("Nộp học phí tạm thu, lệ phí nhập học", out)
        self.assertNotIn("Các khoản tiền", out)

    def test_formatter_section4_returns_only_first_description_line(self):
        chunks = [
            {
                "content": "Chuẩn bị hồ sơ; nộp hồ sơ trực tuyến (trước 17 giờ ngày 28/8/2025) và nộp hồ sơ trực tiếp (trong ngày 27-28/8/2025) tại Trường Đại học Khoa học Khoa học Tự nhiên theo hướng dẫn gồm các bước sau:\nB1: Chuẩn bị hồ sơ...\nB2: Chụp ảnh...",
                "metadata": {
                    "subtype": "section_4",
                    "intent_key": "admission_procedure",
                    "section_id": "phan_4",
                    "source": "Thủ tục nhập học 2025.txt"
                }
            }
        ]
        analysis = {"query_frame": {"nav_target_candidates": ["phan_4"]}}
        out = self.formatter.format_admission_procedure(chunks, analysis=analysis)
        self.assertIsNotNone(out)
        self.assertIn("Chuẩn bị hồ sơ; nộp hồ sơ trực tuyến", out)
        self.assertNotIn("B1:", out)
        self.assertNotIn("B2:", out)

    def test_formatter_section3_prefers_shortest_first_line_when_multiple_chunks(self):
        chunks = [
            {
                "content": "Nộp học phí tạm thu, lệ phí nhập học...theo hình thức chuyển khoản (thực hiện từ ngày 25/8/2025 đến hết ngày 05/9/2025)\nChi tiết dài A...",
                "metadata": {
                    "subtype": "section_3",
                    "intent_key": "admission_procedure",
                    "section_id": "phan_3",
                    "source": "Thủ tục nhập học 2025.txt"
                }
            },
            {
                "content": "Nộp học phí theo hình thức chuyển khoản.\nChi tiết dài B...",
                "metadata": {
                    "subtype": "section_3",
                    "intent_key": "admission_procedure",
                    "section_id": "phan_3",
                    "source": "Thủ tục nhập học 2025.txt"
                }
            }
        ]
        analysis = {"query_frame": {"nav_target_candidates": ["phan_3"]}}
        out = self.formatter.format_admission_procedure(chunks, analysis=analysis)
        self.assertIsNotNone(out)
        self.assertIn("Nộp học phí", out)
        self.assertNotIn("Chi tiết dài", out)


if __name__ == "__main__":
    unittest.main()
