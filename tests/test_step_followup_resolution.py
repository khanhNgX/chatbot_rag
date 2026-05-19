# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from automation_retriever import AutomationRetriever


class _DummyVectorStorage:
    def query(self, *args, **kwargs):
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


class TestStepFollowupResolution(unittest.TestCase):
    def setUp(self):
        self._patch_vs = patch('automation_retriever.VectorStorage', return_value=_DummyVectorStorage())
        self._patch_vs.start()
        self.addCleanup(self._patch_vs.stop)
        self._patch_ai = patch('automation_retriever.AIAutomation.process_user_query', side_effect=lambda query: {'refined_query': query, 'detected_topic': 'general'})
        self._patch_ai.start()
        self.addCleanup(self._patch_ai.stop)
        self.retriever = AutomationRetriever()

    def test_buoc_dau_global_maps_to_section_1(self):
        analysis = self.retriever.analyze("bước đầu của thủ tục nhập học", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_next_step_global_from_section1_maps_to_section2(self):
        history = [
            {"role": "user", "content": "bước đầu của thủ tục nhập học"},
            {"role": "assistant", "content": "PHẦN 1: Tra cứu danh sách trúng tuyển"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo là gì", chat_history=history)
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_prev_step_global_from_section3_maps_to_section2(self):
        history = [
            {"role": "assistant", "content": "PHẦN 3: Nộp học phí"}
        ]
        analysis = self.retriever.analyze("bước trước đó là gì", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_next_step_local_from_b1_maps_to_b2(self):
        history = [
            {"role": "assistant", "content": "B1: Chuẩn bị hồ sơ"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo của phần 4 là gì", chat_history=history)
        self.assertEqual(analysis.get("intent"), "step")
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_prev_step_local_clamped_at_1(self):
        history = [
            {"role": "assistant", "content": "B1: Chuẩn bị hồ sơ"}
        ]
        analysis = self.retriever.analyze("bước trước đó của phần 4", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 1)

    def test_next_step_global_clamped_at_4(self):
        history = [
            {"role": "assistant", "content": "PHẦN 4: Chuẩn bị hồ sơ"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo là gì", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 4)

    def test_prev_step_global_clamped_at_1(self):
        history = [
            {"role": "assistant", "content": "PHẦN 1: Tra cứu"}
        ]
        analysis = self.retriever.analyze("bước trước đó là gì", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_global_next_without_history_defaults_to_section2(self):
        analysis = self.retriever.analyze("bước tiếp theo là gì", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_global_prev_without_history_defaults_to_section1(self):
        analysis = self.retriever.analyze("bước trước đó là gì", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_explicit_global_buoc_3_maps_to_section3(self):
        analysis = self.retriever.analyze("cho tôi bước 3 của thủ tục nhập học", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)

    def test_explicit_global_buoc_thu_2_maps_to_section2(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_explicit_global_buoc_thu_3_maps_to_section3(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)

    def test_explicit_local_buoc_thu_2_maps_to_step2(self):
        analysis = self.retriever.analyze("bước thứ 2 của phần 4 nộp hồ sơ", chat_history=[])
        self.assertEqual(analysis.get("intent"), "step")
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_explicit_local_buoc_thu_3_maps_to_step3(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual(analysis.get("intent"), "step")
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_query_frame_global_buoc_thu_2_targets_phan_2(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("nav_target_type"), "section")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "phan_2")

    def test_query_frame_global_buoc_thu_3_targets_phan_3(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("nav_target_type"), "section")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "phan_3")

    def test_query_frame_local_buoc_thu_2_targets_b2(self):
        analysis = self.retriever.analyze("bước thứ 2 của phần 4 nộp hồ sơ", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("nav_target_type"), "local_step")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b2_phan_4")

    def test_query_frame_local_buoc_thu_3_targets_b3(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("nav_target_type"), "local_step")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b3_phan_4")

    def test_where_filter_global_buoc_thu_2_is_phan_2(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertEqual(where, {"section_id": "phan_2"})

    def test_where_filter_global_buoc_thu_3_is_phan_3(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertEqual(where, {"section_id": "phan_3"})

    def test_where_filter_local_buoc_thu_2_is_b2(self):
        analysis = self.retriever.analyze("bước thứ 2 của phần 4 nộp hồ sơ", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertEqual(where, {"canonical_nav_id": "b2_phan_4"})

    def test_where_filter_local_buoc_thu_3_is_b3(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertEqual(where, {"canonical_nav_id": "b3_phan_4"})

    def test_global_buoc_thu_2_does_not_fall_back_to_phan_1(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertNotEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_global_buoc_thu_3_does_not_fall_back_to_phan_1(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertNotEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_local_buoc_thu_2_does_not_map_to_global_section(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertIsNone(entities.get("section_number"))
        self.assertEqual(entities.get("step_number"), 2)

    def test_local_buoc_thu_3_does_not_map_to_global_section(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertIsNone(entities.get("section_number"))
        self.assertEqual(entities.get("step_number"), 3)

    def test_intent_global_buoc_thu_2_is_admission_procedure(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_intent_local_buoc_thu_2_is_step(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertEqual(analysis.get("intent"), "step")

    def test_intent_global_buoc_thu_3_is_admission_procedure(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_intent_local_buoc_thu_3_is_step(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual(analysis.get("intent"), "step")

    def test_buoc_thu_hai_nop_ho_so_maps_to_b2(self):
        analysis = self.retriever.analyze("bước thứ hai nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "step")
        self.assertEqual(entities.get("step_number"), 2)
        self.assertEqual(frame.get("nav_target_type"), "local_step")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b2_phan_4")

    def test_cac_buoc_nop_ho_so_returns_steps_overview_not_b1_only(self):
        analysis = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertTrue(entities.get("ask_steps_overview_local"))
        self.assertIsNone(entities.get("step_number"))
        self.assertEqual(frame.get("nav_target_type"), "unknown")
        self.assertEqual(frame.get("nav_target_candidates"), [])

    def test_where_filter_none_for_cac_buoc_nop_ho_so(self):
        analysis = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertIsNone(where)

    def test_buoc_thu_hai_nop_ho_so_not_fallback_b1(self):
        analysis = self.retriever.analyze("bước thứ hai nộp hồ sơ", chat_history=[])
        self.assertNotEqual((analysis.get("entities") or {}).get("step_number"), 1)

    def test_cac_buoc_nop_ho_so_not_lock_to_b1_nav(self):
        analysis = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertNotIn("b1_phan_4", frame.get("nav_target_candidates") or [])

    def test_buoc_thu_hai_nop_ho_so_with_accentless_text(self):
        analysis = self.retriever.analyze("buoc thu hai nop ho so", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_cac_buoc_nop_ho_so_with_accentless_text(self):
        analysis = self.retriever.analyze("cac buoc nop ho so", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("ask_steps_overview_local"))

    def test_typo_ac_buoc_nop_ho_so_still_overview_local(self):
        analysis = self.retriever.analyze("ác bước nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertTrue(entities.get("ask_steps_overview_local"))
        self.assertIsNone(entities.get("step_number"))
        self.assertEqual(frame.get("nav_target_type"), "unknown")
        self.assertEqual(frame.get("nav_target_candidates"), [])
        self.assertEqual(frame.get("scope"), "local_section")

    def test_tom_tat_thu_tuc_nhap_hoc_maps_to_global_overview(self):
        analysis = self.retriever.analyze("tóm tắt thủ tục nhập học", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertTrue(entities.get("ask_steps_overview_global"))
        self.assertEqual(frame.get("nav_target_type"), "unknown")
        self.assertEqual(frame.get("scope"), "global")

    def test_tong_quan_thu_tuc_nhap_hoc_maps_to_global_overview(self):
        analysis = self.retriever.analyze("cho tôi tổng quan thủ tục nhập học", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertTrue(entities.get("ask_steps_overview_global"))
        self.assertEqual(frame.get("nav_target_type"), "unknown")
        self.assertEqual(frame.get("scope"), "global")

    def test_tom_tat_nop_ho_so_keeps_local_overview(self):
        analysis = self.retriever.analyze("tóm tắt các bước nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertTrue(entities.get("ask_steps_overview_local"))
        self.assertFalse(bool(entities.get("ask_steps_overview_global")))
        self.assertEqual(frame.get("scope"), "local_section")

    def test_phan_3_cua_phan_nop_ho_so_maps_to_local_step_b3(self):
        analysis = self.retriever.analyze("viết chi tiết phần 3 của phần nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "step")
        self.assertEqual(entities.get("step_number"), 3)
        self.assertIsNone(entities.get("section_number"))
        self.assertEqual(frame.get("nav_target_type"), "local_step")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b3_phan_4")
        self.assertEqual(frame.get("scope"), "local_section")

    def test_phan_3_cua_thu_tuc_nhap_hoc_keeps_global_section_3(self):
        analysis = self.retriever.analyze("viết chi tiết phần 3 của thủ tục nhập học", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertEqual(entities.get("section_number"), 3)
        self.assertEqual(frame.get("nav_target_type"), "section")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "phan_3")
        self.assertEqual(frame.get("scope"), "global")

    def test_buoc_thu_hai_nop_hoc_phi_maps_to_b2_local_flow(self):
        analysis = self.retriever.analyze("bước thứ hai nộp học phí", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "step")
        self.assertEqual(entities.get("step_number"), 2)
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b2_phan_4")

    def test_cac_buoc_nop_hoc_phi_returns_overview_not_b1_only(self):
        analysis = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "admission_procedure")
        self.assertTrue(entities.get("ask_steps_overview_local"))
        self.assertIsNone(entities.get("step_number"))
        self.assertEqual(frame.get("nav_target_candidates"), [])

    def test_where_filter_none_for_cac_buoc_nop_hoc_phi(self):
        analysis = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertIsNone(where)

    def test_cac_buoc_nop_hoc_phi_not_lock_to_b1_nav(self):
        analysis = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertNotIn("b1_phan_4", frame.get("nav_target_candidates") or [])

    def test_buoc_thu_hai_nop_hoc_phi_not_fallback_b1(self):
        analysis = self.retriever.analyze("bước thứ hai nộp học phí", chat_history=[])
        self.assertNotEqual((analysis.get("entities") or {}).get("step_number"), 1)

    def test_buoc_thu_hai_nop_hoc_phi_accentless(self):
        analysis = self.retriever.analyze("buoc thu hai nop hoc phi", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_cac_buoc_nop_hoc_phi_accentless(self):
        analysis = self.retriever.analyze("cac buoc nop hoc phi", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("ask_steps_overview_local"))

    def test_overview_queries_keep_local_scope(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertTrue((a1.get("entities") or {}).get("local_step_scope"))
        self.assertTrue((a2.get("entities") or {}).get("local_step_scope"))

    def test_overview_queries_do_not_set_explicit_step(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertIsNone((a1.get("entities") or {}).get("step_number"))
        self.assertIsNone((a2.get("entities") or {}).get("step_number"))

    def test_overview_queries_are_navigation_task_type(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertEqual((a1.get("query_frame") or {}).get("task_type"), "ask_navigation")
        self.assertEqual((a2.get("query_frame") or {}).get("task_type"), "ask_navigation")

    def test_overview_queries_not_misclassified_as_step_intent(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertNotEqual(a1.get("intent"), "step")
        self.assertNotEqual(a2.get("intent"), "step")

    def test_buoc_thu_hai_queries_are_step_intent(self):
        a1 = self.retriever.analyze("bước thứ hai nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("bước thứ hai nộp học phí", chat_history=[])
        self.assertEqual(a1.get("intent"), "step")
        self.assertEqual(a2.get("intent"), "step")

    def test_buoc_thu_hai_queries_have_local_nav(self):
        a1 = self.retriever.analyze("bước thứ hai nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("bước thứ hai nộp học phí", chat_history=[])
        self.assertEqual((a1.get("query_frame") or {}).get("nav_target_type"), "local_step")
        self.assertEqual((a2.get("query_frame") or {}).get("nav_target_type"), "local_step")

    def test_overview_queries_have_unknown_nav_target(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertEqual((a1.get("query_frame") or {}).get("nav_target_type"), "unknown")
        self.assertEqual((a2.get("query_frame") or {}).get("nav_target_type"), "unknown")

    def test_overview_queries_where_filter_none_even_with_local_scope(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        w1 = self.retriever._build_where_filter(a1.get("intent") or "general", a1.get("entities") or {}, query_frame=a1.get("query_frame") or {})
        w2 = self.retriever._build_where_filter(a2.get("intent") or "general", a2.get("entities") or {}, query_frame=a2.get("query_frame") or {})
        self.assertIsNone(w1)
        self.assertIsNone(w2)

    def test_overview_queries_do_not_set_section_number(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertIsNone((a1.get("entities") or {}).get("section_number"))
        self.assertIsNone((a2.get("entities") or {}).get("section_number"))

    def test_overview_queries_stable_across_repeated_calls(self):
        q1 = "các bước nộp hồ sơ"
        q2 = "các bước nộp học phí"
        for _ in range(2):
            a1 = self.retriever.analyze(q1, chat_history=[])
            a2 = self.retriever.analyze(q2, chat_history=[])
            self.assertTrue((a1.get("entities") or {}).get("ask_steps_overview_local"))
            self.assertTrue((a2.get("entities") or {}).get("ask_steps_overview_local"))

    def test_buoc_thu_hai_queries_stable_across_repeated_calls(self):
        q1 = "bước thứ hai nộp hồ sơ"
        q2 = "bước thứ hai nộp học phí"
        for _ in range(2):
            a1 = self.retriever.analyze(q1, chat_history=[])
            a2 = self.retriever.analyze(q2, chat_history=[])
            self.assertEqual((a1.get("entities") or {}).get("step_number"), 2)
            self.assertEqual((a2.get("entities") or {}).get("step_number"), 2)

    def test_overview_queries_debug_reason_not_explicit_local_step(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertNotIn("explicit_local_step_mention", (a1.get("query_frame") or {}).get("debug_reason", ""))
        self.assertNotIn("explicit_local_step_mention", (a2.get("query_frame") or {}).get("debug_reason", ""))

    def test_buoc_thu_hai_queries_debug_reason_explicit_local_step(self):
        a1 = self.retriever.analyze("bước thứ hai nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("bước thứ hai nộp học phí", chat_history=[])
        self.assertIn("explicit_local_step_mention", (a1.get("query_frame") or {}).get("debug_reason", ""))
        self.assertIn("explicit_local_step_mention", (a2.get("query_frame") or {}).get("debug_reason", ""))

    def test_overview_queries_candidates_empty(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertEqual((a1.get("query_frame") or {}).get("nav_target_candidates"), [])
        self.assertEqual((a2.get("query_frame") or {}).get("nav_target_candidates"), [])

    def test_buoc_thu_hai_queries_candidates_are_b2(self):
        a1 = self.retriever.analyze("bước thứ hai nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("bước thứ hai nộp học phí", chat_history=[])
        self.assertEqual(((a1.get("query_frame") or {}).get("nav_target_candidates") or [None])[0], "b2_phan_4")
        self.assertEqual(((a2.get("query_frame") or {}).get("nav_target_candidates") or [None])[0], "b2_phan_4")

    def test_overview_queries_do_not_enable_relative_followup_flag(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertFalse((a1.get("entities") or {}).get("relative_followup", False))
        self.assertFalse((a2.get("entities") or {}).get("relative_followup", False))

    def test_buoc_thu_hai_queries_do_not_enable_relative_followup_flag(self):
        a1 = self.retriever.analyze("bước thứ hai nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("bước thứ hai nộp học phí", chat_history=[])
        self.assertFalse((a1.get("entities") or {}).get("relative_followup", False))
        self.assertFalse((a2.get("entities") or {}).get("relative_followup", False))

    def test_overview_queries_keep_section_id_phan4_context(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertEqual((a1.get("entities") or {}).get("section_id"), "phan_4")
        self.assertEqual((a2.get("entities") or {}).get("section_id"), "phan_4")

    def test_buoc_thu_hai_queries_keep_section_id_phan4_context(self):
        a1 = self.retriever.analyze("bước thứ hai nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("bước thứ hai nộp học phí", chat_history=[])
        self.assertEqual((a1.get("entities") or {}).get("section_id"), "phan_4")
        self.assertEqual((a2.get("entities") or {}).get("section_id"), "phan_4")

    def test_overview_queries_do_not_set_global_section_nav(self):
        a1 = self.retriever.analyze("các bước nộp hồ sơ", chat_history=[])
        a2 = self.retriever.analyze("các bước nộp học phí", chat_history=[])
        self.assertFalse((a1.get("entities") or {}).get("global_section_nav", False))
        self.assertFalse((a2.get("entities") or {}).get("global_section_nav", False))

    def test_relative_next_after_buoc_thu_2_global_goes_to_phan_3(self):
        history = [{"role": "assistant", "content": "- Xác nhận nhập học\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 2, Năm 2025)"}]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)

    def test_relative_next_after_buoc_thu_2_local_goes_to_b3(self):
        history = [{"role": "assistant", "content": "B2: Chụp ảnh\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_relative_prev_after_buoc_thu_3_global_goes_to_phan_2(self):
        history = [{"role": "assistant", "content": "- Nộp học phí\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 3, Năm 2025)"}]
        analysis = self.retriever.analyze("bước trước đó", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_relative_prev_after_buoc_thu_3_local_goes_to_b2(self):
        history = [{"role": "assistant", "content": "B3: Upload\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}]
        analysis = self.retriever.analyze("bước trước đó", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_chain_global_buoc_thu_1_to_2_to_3(self):
        a1 = self.retriever.analyze("bước thứ 1 của thủ tục nhập học", chat_history=[])
        self.assertEqual((a1.get("entities") or {}).get("section_number"), 1)
        h = [{"role": "assistant", "content": "- PHẦN 1\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 1, Năm 2025)"}]
        a2 = self.retriever.analyze("bước tiếp theo", chat_history=h)
        self.assertEqual((a2.get("entities") or {}).get("section_number"), 2)
        h2 = h + [{"role": "assistant", "content": "- PHẦN 2\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 2, Năm 2025)"}]
        a3 = self.retriever.analyze("bước tiếp theo", chat_history=h2)
        self.assertEqual((a3.get("entities") or {}).get("section_number"), 3)

    def test_chain_local_buoc_thu_1_to_2_to_3(self):
        a1 = self.retriever.analyze("bước thứ 1 nộp hồ sơ", chat_history=[])
        self.assertEqual((a1.get("entities") or {}).get("step_number"), 1)
        h = [{"role": "assistant", "content": "B1: Chuẩn bị hồ sơ\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}]
        a2 = self.retriever.analyze("bước tiếp theo", chat_history=h)
        self.assertEqual((a2.get("entities") or {}).get("step_number"), 2)
        h2 = h + [{"role": "assistant", "content": "B2: Chụp ảnh\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}]
        a3 = self.retriever.analyze("bước tiếp theo", chat_history=h2)
        self.assertEqual((a3.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_query_frame_confidence_high(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertGreaterEqual(frame.get("confidence", 0), 0.9)

    def test_buoc_thu_local_query_frame_scope_local(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("scope"), "local_section")

    def test_buoc_thu_global_query_frame_scope_global(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("scope"), "global")

    def test_buoc_thu_global_debug_reason_explicit_section(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        reason = (analysis.get("query_frame") or {}).get("debug_reason", "")
        self.assertIn("explicit", reason)

    def test_buoc_thu_local_debug_reason_explicit_local(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        reason = (analysis.get("query_frame") or {}).get("debug_reason", "")
        self.assertIn("local", reason)

    def test_buoc_thu_global_with_accentless_text(self):
        analysis = self.retriever.analyze("buoc thu 3 cua thu tuc nhap hoc", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)

    def test_buoc_thu_local_with_accentless_text(self):
        analysis = self.retriever.analyze("buoc thu 2 nop ho so", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_buoc_thu_global_uppercase_text(self):
        analysis = self.retriever.analyze("BƯỚC THỨ 2 CỦA THỦ TỤC NHẬP HỌC", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_uppercase_text(self):
        analysis = self.retriever.analyze("BƯỚC THỨ 3 NỘP HỒ SƠ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_no_history_stable(self):
        analysis1 = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        analysis2 = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis1.get("entities") or {}).get("section_number"), (analysis2.get("entities") or {}).get("section_number"))

    def test_buoc_thu_local_no_history_stable(self):
        analysis1 = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        analysis2 = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis1.get("entities") or {}).get("step_number"), (analysis2.get("entities") or {}).get("step_number"))

    def test_buoc_thu_global_does_not_set_local_scope(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertFalse((analysis.get("entities") or {}).get("local_step_scope", False))

    def test_buoc_thu_local_sets_local_scope(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("local_step_scope"))

    def test_buoc_thu_global_sets_section_id(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_id"), "phan_3")

    def test_buoc_thu_local_does_not_set_section_id(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertIsNone((analysis.get("entities") or {}).get("section_id"))

    def test_buoc_thu_global_nav_candidate_is_single(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        cands = (analysis.get("query_frame") or {}).get("nav_target_candidates") or []
        self.assertEqual(len(cands), 1)

    def test_buoc_thu_local_nav_candidate_is_single(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        cands = (analysis.get("query_frame") or {}).get("nav_target_candidates") or []
        self.assertEqual(len(cands), 1)

    def test_buoc_thu_global_top_candidate_exact(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual(((analysis.get("query_frame") or {}).get("nav_target_candidates") or [None])[0], "phan_2")

    def test_buoc_thu_local_top_candidate_exact(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual(((analysis.get("query_frame") or {}).get("nav_target_candidates") or [None])[0], "b3_phan_4")

    def test_buoc_thu_global_task_type_navigation(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("task_type"), "ask_navigation")

    def test_buoc_thu_local_task_type_navigation(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("task_type"), "ask_navigation")

    def test_buoc_thu_global_retrieve_where_not_none(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        where = self.retriever._build_where_filter(analysis.get("intent") or "general", analysis.get("entities") or {}, query_frame=analysis.get("query_frame") or {})
        self.assertIsNotNone(where)

    def test_buoc_thu_local_retrieve_where_not_none(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        where = self.retriever._build_where_filter(analysis.get("intent") or "general", analysis.get("entities") or {}, query_frame=analysis.get("query_frame") or {})
        self.assertIsNotNone(where)

    def test_buoc_thu_global_not_marked_as_count(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertFalse(entities.get("ask_section_count", False))

    def test_buoc_thu_local_not_marked_as_count(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertFalse(entities.get("ask_step_count_local", False))

    def test_buoc_thu_global_relative_axis_not_local(self):
        history = [{"role": "assistant", "content": "- PHẦN 2\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 2, Năm 2025)"}]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertNotEqual((analysis.get("entities") or {}).get("resolved_axis"), "local")

    def test_buoc_thu_local_relative_axis_local(self):
        history = [{"role": "assistant", "content": "B2: Chụp ảnh\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("resolved_axis"), "local")

    def test_buoc_thu_global_prev_from_2_to_1(self):
        history = [{"role": "assistant", "content": "- PHẦN 2\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 2, Năm 2025)"}]
        analysis = self.retriever.analyze("bước trước đó", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_buoc_thu_local_prev_from_3_to_2(self):
        history = [{"role": "assistant", "content": "B3: Upload\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}]
        analysis = self.retriever.analyze("bước trước đó", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_buoc_thu_global_prev_clamped_1(self):
        history = [{"role": "assistant", "content": "- PHẦN 1\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 1, Năm 2025)"}]
        analysis = self.retriever.analyze("bước trước đó", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_buoc_thu_local_prev_clamped_1(self):
        history = [{"role": "assistant", "content": "B1: Chuẩn bị hồ sơ\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}]
        analysis = self.retriever.analyze("bước trước đó", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 1)

    def test_buoc_thu_global_next_clamped_4(self):
        history = [{"role": "assistant", "content": "- PHẦN 4\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 4)

    def test_buoc_thu_local_next_clamped_4(self):
        history = [{"role": "assistant", "content": "B4: Nộp hồ sơ\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 4)

    def test_buoc_thu_global_cache_independent_of_query_variant(self):
        a = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        b = self.retriever.analyze("bước 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((a.get("entities") or {}).get("section_number"), (b.get("entities") or {}).get("section_number"))

    def test_buoc_thu_local_cache_independent_of_query_variant(self):
        a = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        b = self.retriever.analyze("bước 2 nộp hồ sơ", chat_history=[])
        self.assertEqual((a.get("entities") or {}).get("step_number"), (b.get("entities") or {}).get("step_number"))

    def test_buoc_thu_global_debug_has_explicit_section(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        reason = (analysis.get("query_frame") or {}).get("debug_reason", "")
        self.assertTrue(bool(reason))

    def test_buoc_thu_local_debug_has_explicit_local(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        reason = (analysis.get("query_frame") or {}).get("debug_reason", "")
        self.assertTrue(bool(reason))

    def test_buoc_thu_global_entities_has_section_number(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertIn("section_number", (analysis.get("entities") or {}))

    def test_buoc_thu_local_entities_has_step_number(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertIn("step_number", (analysis.get("entities") or {}))

    def test_buoc_thu_global_query_frame_has_nav(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertTrue(bool((analysis.get("query_frame") or {}).get("nav_target_candidates")))

    def test_buoc_thu_local_query_frame_has_nav(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertTrue(bool((analysis.get("query_frame") or {}).get("nav_target_candidates")))

    def test_buoc_thu_global_section_id_consistency(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertEqual(entities.get("section_id"), "phan_2")

    def test_buoc_thu_global_section3_id_consistency(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertEqual(entities.get("section_id"), "phan_3")

    def test_buoc_thu_local_step2_nav_consistency(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b2_phan_4")

    def test_buoc_thu_local_step3_nav_consistency(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b3_phan_4")

    def test_buoc_thu_global_intent_consistency(self):
        qs = ["bước thứ 2 của thủ tục nhập học", "bước thứ 3 của thủ tục nhập học", "buoc thu 2 cua thu tuc nhap hoc"]
        for q in qs:
            analysis = self.retriever.analyze(q, chat_history=[])
            self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_buoc_thu_local_intent_consistency(self):
        qs = ["bước thứ 2 nộp hồ sơ", "bước thứ 3 nộp hồ sơ", "buoc thu 2 nop ho so"]
        for q in qs:
            analysis = self.retriever.analyze(q, chat_history=[])
            self.assertEqual(analysis.get("intent"), "step")

    def test_buoc_thu_global_no_prev_next_flags(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertFalse(entities.get("next_step", False))
        self.assertFalse(entities.get("prev_step", False))

    def test_buoc_thu_local_no_prev_next_flags(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertFalse(entities.get("next_step", False))
        self.assertFalse(entities.get("prev_step", False))

    def test_buoc_thu_global_with_question_mark(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học là gì?", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_question_mark(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ là gì?", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_extra_spaces(self):
        analysis = self.retriever.analyze("  bước   thứ   2   của   thủ tục nhập học  ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_extra_spaces(self):
        analysis = self.retriever.analyze("  bước   thứ   3   nộp hồ sơ  ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_synonym_quy_trinh(self):
        analysis = self.retriever.analyze("bước thứ 2 của quy trình nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_global_with_synonym_thu_tuc(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)

    def test_buoc_thu_local_with_synonym_ho_so(self):
        analysis = self.retriever.analyze("bước thứ 2 của hồ sơ nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_buoc_thu_local_with_synonym_nop_ho_so(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_priority_over_history_local_when_query_explicit_global(self):
        history = [{"role": "assistant", "content": "B2: Chụp ảnh"}]
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)
        self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_buoc_thu_local_priority_over_history_global_when_query_explicit_local(self):
        history = [{"role": "assistant", "content": "PHẦN 2: Xác nhận"}]
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)
        self.assertEqual(analysis.get("intent"), "step")

    def test_buoc_thu_global_history_irrelevant_not_affect(self):
        history = [{"role": "assistant", "content": "Xin chào"}]
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_history_irrelevant_not_affect(self):
        history = [{"role": "assistant", "content": "Xin chào"}]
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_repeated_calls_same_result(self):
        q = "bước thứ 2 của thủ tục nhập học"
        vals = [ (self.retriever.analyze(q, chat_history=[]).get("entities") or {}).get("section_number") for _ in range(3) ]
        self.assertEqual(vals, [2,2,2])

    def test_buoc_thu_local_repeated_calls_same_result(self):
        q = "bước thứ 3 nộp hồ sơ"
        vals = [ (self.retriever.analyze(q, chat_history=[]).get("entities") or {}).get("step_number") for _ in range(3) ]
        self.assertEqual(vals, [3,3,3])

    def test_buoc_thu_global_with_unicode_variation(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_unicode_variation(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_frame_not_ambiguous(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertNotEqual((analysis.get("query_frame") or {}).get("scope"), "ambiguous")

    def test_buoc_thu_local_query_frame_not_ambiguous(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertNotEqual((analysis.get("query_frame") or {}).get("scope"), "ambiguous")

    def test_buoc_thu_global_reason_not_empty(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertTrue(bool((analysis.get("query_frame") or {}).get("debug_reason")))

    def test_buoc_thu_local_reason_not_empty(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertTrue(bool((analysis.get("query_frame") or {}).get("debug_reason")))

    def test_buoc_thu_global_entities_keys_present(self):
        entities = (self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[]).get("entities") or {})
        self.assertTrue('section_number' in entities and 'section_id' in entities)

    def test_buoc_thu_local_entities_keys_present(self):
        entities = (self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[]).get("entities") or {})
        self.assertTrue('step_number' in entities)

    def test_buoc_thu_global_when_query_contains_colon(self):
        analysis = self.retriever.analyze("bước thứ 2: thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_when_query_contains_colon(self):
        analysis = self.retriever.analyze("bước thứ 3: nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_wording_buoc_so(self):
        analysis = self.retriever.analyze("bước số 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_wording_buoc_so(self):
        analysis = self.retriever.analyze("bước số 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_wording_buoc_thu_tu(self):
        analysis = self.retriever.analyze("bước thứ tự 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_wording_buoc_thu_tu(self):
        analysis = self.retriever.analyze("bước thứ tự 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_short_query(self):
        analysis = self.retriever.analyze("bước 2 thủ tục", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_short_query(self):
        analysis = self.retriever.analyze("bước 3 hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_noise_text(self):
        analysis = self.retriever.analyze("ờ cho mình hỏi bước thứ 2 của thủ tục nhập học với", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_noise_text(self):
        analysis = self.retriever.analyze("ờ cho mình hỏi bước thứ 3 nộp hồ sơ với", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_deterministic_against_style(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("nav_target_type"), "section")

    def test_buoc_thu_local_deterministic_against_style(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("nav_target_type"), "local_step")

    def test_buoc_thu_global_readable_reason(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        reason = (analysis.get("query_frame") or {}).get("debug_reason", "")
        self.assertTrue(isinstance(reason, str))

    def test_buoc_thu_local_readable_reason(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        reason = (analysis.get("query_frame") or {}).get("debug_reason", "")
        self.assertTrue(isinstance(reason, str))

    def test_buoc_thu_global_candidate_prefix(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        cand = ((analysis.get("query_frame") or {}).get("nav_target_candidates") or [""])[0]
        self.assertTrue(cand.startswith("phan_"))

    def test_buoc_thu_local_candidate_prefix(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        cand = ((analysis.get("query_frame") or {}).get("nav_target_candidates") or [""])[0]
        self.assertTrue(cand.startswith("b"))

    def test_buoc_thu_global_section_number_bounds(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        s = (analysis.get("entities") or {}).get("section_number")
        self.assertTrue(1 <= s <= 4)

    def test_buoc_thu_local_step_number_bounds(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        s = (analysis.get("entities") or {}).get("step_number")
        self.assertTrue(1 <= s <= 4)

    def test_buoc_thu_global_after_local_history_explicit_query_still_global(self):
        history = [{"role": "assistant", "content": "B2: Chụp ảnh"}]
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_after_global_history_explicit_query_still_local(self):
        history = [{"role": "assistant", "content": "PHẦN 2: Xác nhận"}]
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_frame_has_parent_context_flag(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertTrue((analysis.get("query_frame") or {}).get("needs_parent_context"))

    def test_buoc_thu_local_query_frame_has_parent_context_flag(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertTrue((analysis.get("query_frame") or {}).get("needs_parent_context"))

    def test_buoc_thu_global_metadata_filter_enabled(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertTrue((analysis.get("query_frame") or {}).get("should_apply_metadata_filter"))

    def test_buoc_thu_local_metadata_filter_enabled(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertTrue((analysis.get("query_frame") or {}).get("should_apply_metadata_filter"))

    def test_buoc_thu_global_language_vi(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("language"), "vi")

    def test_buoc_thu_local_language_vi(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("language"), "vi")

    def test_buoc_thu_global_not_followup_no_history(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertFalse((analysis.get("query_frame") or {}).get("is_followup"))

    def test_buoc_thu_local_not_followup_no_history(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertFalse((analysis.get("query_frame") or {}).get("is_followup"))

    def test_buoc_thu_global_followup_true_with_history(self):
        history = [{"role": "assistant", "content": "PHẦN 1: Tra cứu"}]
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=history)
        self.assertTrue((analysis.get("query_frame") or {}).get("is_followup"))

    def test_buoc_thu_local_followup_true_with_history(self):
        history = [{"role": "assistant", "content": "B1: Chuẩn bị hồ sơ"}]
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=history)
        self.assertTrue((analysis.get("query_frame") or {}).get("is_followup"))

    def test_buoc_thu_global_topical_task_navigation(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("task_type"), "ask_navigation")

    def test_buoc_thu_local_topical_task_navigation(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("task_type"), "ask_navigation")

    def test_buoc_thu_global_candidate_not_empty(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertTrue(len((analysis.get("query_frame") or {}).get("nav_target_candidates") or []) > 0)

    def test_buoc_thu_local_candidate_not_empty(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertTrue(len((analysis.get("query_frame") or {}).get("nav_target_candidates") or []) > 0)

    def test_buoc_thu_global_section_2_consistency_again(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_global_section_3_consistency_again(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)

    def test_buoc_thu_local_step_2_consistency_again(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_buoc_thu_local_step_3_consistency_again(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_where_filter_stable(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        where = self.retriever._build_where_filter(analysis.get("intent") or "general", analysis.get("entities") or {}, query_frame=analysis.get("query_frame") or {})
        self.assertEqual(where, {"section_id": "phan_2"})

    def test_buoc_thu_local_where_filter_stable(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        where = self.retriever._build_where_filter(analysis.get("intent") or "general", analysis.get("entities") or {}, query_frame=analysis.get("query_frame") or {})
        self.assertEqual(where, {"canonical_nav_id": "b3_phan_4"})

    def test_buoc_thu_global_query_frame_target_type(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("nav_target_type"), "section")

    def test_buoc_thu_local_query_frame_target_type(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("nav_target_type"), "local_step")

    def test_buoc_thu_global_intent_not_step(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertNotEqual(analysis.get("intent"), "step")

    def test_buoc_thu_local_intent_not_admission_procedure(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertNotEqual(analysis.get("intent"), "admission_procedure")

    def test_buoc_thu_global_section_id_prefix(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        sid = (analysis.get("entities") or {}).get("section_id")
        self.assertTrue(str(sid).startswith("phan_"))

    def test_buoc_thu_local_step_id_absent_in_entities(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertFalse('step_id' in (analysis.get("entities") or {}))

    def test_buoc_thu_global_no_local_step_scope(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertFalse((analysis.get("entities") or {}).get("local_step_scope", False))

    def test_buoc_thu_local_yes_local_step_scope(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("local_step_scope", False))

    def test_buoc_thu_global_entity_resolved_axis_absent_non_relative(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertFalse('resolved_axis' in (analysis.get("entities") or {}))

    def test_buoc_thu_local_entity_resolved_axis_absent_non_relative(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertFalse('resolved_axis' in (analysis.get("entities") or {}))

    def test_buoc_thu_global_normalized_numeric_token(self):
        analysis = self.retriever.analyze("bước thứ 2 thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_normalized_numeric_token(self):
        analysis = self.retriever.analyze("bước thứ 3 hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_punctuation(self):
        analysis = self.retriever.analyze("bước thứ 2, của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_punctuation(self):
        analysis = self.retriever.analyze("bước thứ 3, nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_trailing_text(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học giúp mình", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_trailing_text(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ giúp mình", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_prefix_text(self):
        analysis = self.retriever.analyze("cho mình hỏi bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_prefix_text(self):
        analysis = self.retriever.analyze("cho mình hỏi bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_inference_not_overridden_by_default(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)

    def test_buoc_thu_local_inference_not_overridden_by_default(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_buoc_thu_global_frame_candidates_exact(self):
        analysis = self.retriever.analyze("bước thứ 3 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("nav_target_candidates"), ["phan_3"])

    def test_buoc_thu_local_frame_candidates_exact(self):
        analysis = self.retriever.analyze("bước thứ 2 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("nav_target_candidates"), ["b2_phan_4"])

    def test_buoc_thu_global_frame_needs_parent_context_true(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertTrue((analysis.get("query_frame") or {}).get("needs_parent_context"))

    def test_buoc_thu_local_frame_needs_parent_context_true(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertTrue((analysis.get("query_frame") or {}).get("needs_parent_context"))

    def test_buoc_thu_global_query_frame_should_apply_filter_true(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertTrue((analysis.get("query_frame") or {}).get("should_apply_metadata_filter"))

    def test_buoc_thu_local_query_frame_should_apply_filter_true(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertTrue((analysis.get("query_frame") or {}).get("should_apply_metadata_filter"))

    def test_buoc_thu_global_rewritten_query_not_empty(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertTrue(bool((analysis.get("query_frame") or {}).get("rewritten_query")))

    def test_buoc_thu_local_rewritten_query_not_empty(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertTrue(bool((analysis.get("query_frame") or {}).get("rewritten_query")))

    def test_buoc_thu_global_with_very_short_scope_text(self):
        analysis = self.retriever.analyze("bước thứ 2 thủ tục", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_very_short_scope_text(self):
        analysis = self.retriever.analyze("bước thứ 3 hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_stop_words(self):
        analysis = self.retriever.analyze("cho em hỏi bước thứ 2 của thủ tục nhập học là gì ạ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_stop_words(self):
        analysis = self.retriever.analyze("cho em hỏi bước thứ 3 nộp hồ sơ là gì ạ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_with_typo_minor(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tuc nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_with_typo_minor(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hso", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_frame_confidence_not_low(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertGreater((analysis.get("query_frame") or {}).get("confidence", 0), 0.5)

    def test_buoc_thu_local_query_frame_confidence_not_low(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertGreater((analysis.get("query_frame") or {}).get("confidence", 0), 0.5)

    def test_buoc_thu_global_entity_type_int(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertIsInstance((analysis.get("entities") or {}).get("section_number"), int)

    def test_buoc_thu_local_entity_type_int(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertIsInstance((analysis.get("entities") or {}).get("step_number"), int)

    def test_buoc_thu_global_top_candidate_string(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertIsInstance(((analysis.get("query_frame") or {}).get("nav_target_candidates") or [""])[0], str)

    def test_buoc_thu_local_top_candidate_string(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertIsInstance(((analysis.get("query_frame") or {}).get("nav_target_candidates") or [""])[0], str)

    def test_buoc_thu_global_query_frame_contains_keys(self):
        frame = (self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[]).get("query_frame") or {})
        for k in ["scope", "nav_target_type", "nav_target_candidates", "task_type"]:
            self.assertIn(k, frame)

    def test_buoc_thu_local_query_frame_contains_keys(self):
        frame = (self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[]).get("query_frame") or {})
        for k in ["scope", "nav_target_type", "nav_target_candidates", "task_type"]:
            self.assertIn(k, frame)

    def test_buoc_thu_global_entities_contains_keys(self):
        entities = (self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[]).get("entities") or {})
        self.assertIn("section_number", entities)

    def test_buoc_thu_local_entities_contains_keys(self):
        entities = (self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[]).get("entities") or {})
        self.assertIn("step_number", entities)

    def test_buoc_thu_global_result_structure(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertIn("intent", analysis)
        self.assertIn("entities", analysis)
        self.assertIn("query_frame", analysis)

    def test_buoc_thu_local_result_structure(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertIn("intent", analysis)
        self.assertIn("entities", analysis)
        self.assertIn("query_frame", analysis)

    def test_buoc_thu_global_explicit_query_resists_history_axis(self):
        history = [{"role": "assistant", "content": "B3: Upload hồ sơ"}]
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_explicit_query_resists_history_axis(self):
        history = [{"role": "assistant", "content": "PHẦN 3: Học phí"}]
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_emojis(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học 😊", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_emojis(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ 😊", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_newline(self):
        analysis = self.retriever.analyze("bước thứ 2\ncủa thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_newline(self):
        analysis = self.retriever.analyze("bước thứ 3\nnộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_tab(self):
        analysis = self.retriever.analyze("bước thứ 2\tcủa thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_tab(self):
        analysis = self.retriever.analyze("bước thứ 3\tnộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_multiple_punctuations(self):
        analysis = self.retriever.analyze("bước thứ 2??? của thủ tục nhập học!!!", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_multiple_punctuations(self):
        analysis = self.retriever.analyze("bước thứ 3??? nộp hồ sơ!!!", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_quotes(self):
        analysis = self.retriever.analyze("\"bước thứ 2\" của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_quotes(self):
        analysis = self.retriever.analyze("\"bước thứ 3\" nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_parentheses(self):
        analysis = self.retriever.analyze("(bước thứ 2) của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_parentheses(self):
        analysis = self.retriever.analyze("(bước thứ 3) nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_slashes(self):
        analysis = self.retriever.analyze("bước thứ 2/4 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_slashes(self):
        analysis = self.retriever.analyze("bước thứ 3/4 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_english_noise(self):
        analysis = self.retriever.analyze("please cho mình bước thứ 2 của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_english_noise(self):
        analysis = self.retriever.analyze("please cho mình bước thứ 3 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_numbers_words_mix(self):
        analysis = self.retriever.analyze("bước thứ 2 (hai) của thủ tục nhập học", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_numbers_words_mix(self):
        analysis = self.retriever.analyze("bước thứ 3 (ba) nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_with_long_sentence(self):
        q = "anh/chị cho em hỏi giúp: bước thứ 2 của thủ tục nhập học năm 2025 là gì ạ"
        analysis = self.retriever.analyze(q, chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_buoc_thu_local_query_with_long_sentence(self):
        q = "anh/chị cho em hỏi giúp: bước thứ 3 nộp hồ sơ năm 2025 là gì ạ"
        analysis = self.retriever.analyze(q, chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_buoc_thu_global_query_consistent_across_cases(self):
        qs = ["Bước thứ 2 của thủ tục nhập học", "bước THỨ 2 của thủ tục nhập học", "BƯỚC thứ 2 của thủ tục nhập học"]
        vals = [((self.retriever.analyze(q, chat_history=[]).get("entities") or {}).get("section_number")) for q in qs]
        self.assertEqual(vals, [2, 2, 2])

    def test_buoc_thu_local_query_consistent_across_cases(self):
        qs = ["Bước thứ 3 nộp hồ sơ", "bước THỨ 3 nộp hồ sơ", "BƯỚC thứ 3 nộp hồ sơ"]
        vals = [((self.retriever.analyze(q, chat_history=[]).get("entities") or {}).get("step_number")) for q in qs]
        self.assertEqual(vals, [3, 3, 3])

    def test_buoc_thu_global_final_guard(self):
        analysis = self.retriever.analyze("bước thứ 2 của thủ tục nhập học", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(entities.get("section_number"), 2)
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "phan_2")

    def test_buoc_thu_local_final_guard(self):
        analysis = self.retriever.analyze("bước thứ 3 nộp hồ sơ", chat_history=[])
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(entities.get("step_number"), 3)
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b3_phan_4")

    def test_explicit_local_buoc_3_maps_to_step3(self):
        analysis = self.retriever.analyze("cho tôi bước 3 của phần 4 nộp hồ sơ", chat_history=[])
        self.assertEqual(analysis.get("intent"), "step")
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_ask_section_count_for_global_query(self):
        analysis = self.retriever.analyze("thủ tục nhập học có mấy bước", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("ask_section_count"))

    def test_ask_step_count_local_for_section4_query(self):
        analysis = self.retriever.analyze("phần 4 nộp hồ sơ có mấy bước", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("ask_step_count_local"))

    def test_frame_nav_targets_section_for_global_next(self):
        history = [
            {"role": "assistant", "content": "PHẦN 1: Tra cứu"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo là gì", chat_history=history)
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("nav_target_type"), "section")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "phan_2")

    def test_frame_nav_targets_local_step_for_local_next(self):
        history = [
            {"role": "assistant", "content": "B1: Chuẩn bị hồ sơ"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo của phần 4", chat_history=history)
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("nav_target_type"), "local_step")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b2_phan_4")

    def test_where_filter_uses_section_for_global_nav(self):
        analysis = self.retriever.analyze("bước đầu của thủ tục nhập học", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertEqual(where, {"section_id": "phan_1"})

    def test_where_filter_uses_canonical_nav_for_local_step(self):
        analysis = self.retriever.analyze("bước 2 của phần 4", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertEqual(where, {"canonical_nav_id": "b2_phan_4"})

    def test_intent_keeps_admission_procedure_for_global_step_wording(self):
        analysis = self.retriever.analyze("bước tiếp theo của thủ tục nhập học", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_intent_is_step_for_local_step_wording(self):
        analysis = self.retriever.analyze("bước tiếp theo của phần 4", chat_history=[])
        self.assertEqual(analysis.get("intent"), "step")

    def test_query_frame_reason_for_global_relative(self):
        history = [
            {"role": "assistant", "content": "PHẦN 2: Xác nhận nhập học trực tuyến"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        reason = (analysis.get("query_frame") or {}).get("debug_reason", "")
        self.assertIn("relative_section_from_history", reason)

    def test_query_frame_reason_for_local_relative(self):
        history = [
            {"role": "assistant", "content": "B2: Chụp ảnh chân dung"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo của phần 4", chat_history=history)
        reason = (analysis.get("query_frame") or {}).get("debug_reason", "")
        self.assertIn("relative_local_step_from_history", reason)

    def test_global_buoc_dau_with_history_section3_still_maps_section1_when_explicit(self):
        history = [
            {"role": "assistant", "content": "PHẦN 3: Nộp học phí"}
        ]
        analysis = self.retriever.analyze("bước đầu của thủ tục nhập học", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_local_buoc_dau_with_section4_scope_maps_step1(self):
        analysis = self.retriever.analyze("bước đầu của phần 4", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 1)

    def test_global_buoc_2_phrase_maps_section2(self):
        analysis = self.retriever.analyze("bước 2 của thủ tục nhập học là gì", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_local_buoc_2_phrase_maps_step2(self):
        analysis = self.retriever.analyze("bước 2 nộp hồ sơ", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_global_next_after_section4_clamped(self):
        history = [{"role": "assistant", "content": "PHẦN 4: Chuẩn bị hồ sơ"}]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 4)

    def test_local_next_after_b4_clamped(self):
        history = [{"role": "assistant", "content": "B4: Nộp hồ sơ bản giấy"}]
        analysis = self.retriever.analyze("bước tiếp theo của phần 4", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 4)

    def test_global_prev_before_section1_clamped(self):
        history = [{"role": "assistant", "content": "PHẦN 1: Tra cứu"}]
        analysis = self.retriever.analyze("bước trước đó", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_local_prev_before_b1_clamped(self):
        history = [{"role": "assistant", "content": "B1: Chuẩn bị hồ sơ"}]
        analysis = self.retriever.analyze("bước trước đó của phần 4", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 1)

    def test_section_number_sets_section_id(self):
        analysis = self.retriever.analyze("phần 3 là gì", chat_history=[])
        entities = analysis.get("entities") or {}
        self.assertEqual(entities.get("section_number"), 3)
        self.assertEqual(entities.get("section_id"), "phan_3")

    def test_local_scope_flag_present_for_ho_so_queries(self):
        analysis = self.retriever.analyze("bước tiếp theo nộp hồ sơ", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("local_step_scope"))

    def test_global_scope_flag_present_for_thu_tuc_queries(self):
        analysis = self.retriever.analyze("bước tiếp theo của thủ tục nhập học", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("global_section_nav"))

    def test_query_frame_needs_parent_context_for_section_nav(self):
        analysis = self.retriever.analyze("bước đầu của thủ tục nhập học", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertTrue(frame.get("needs_parent_context"))

    def test_query_frame_confidence_high_for_explicit_section(self):
        analysis = self.retriever.analyze("phần 2 của thủ tục", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertGreaterEqual(frame.get("confidence", 0), 0.9)

    def test_query_frame_scope_global_for_section_nav(self):
        analysis = self.retriever.analyze("bước đầu của thủ tục nhập học", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("scope"), "global")

    def test_query_frame_scope_local_for_local_step_nav(self):
        analysis = self.retriever.analyze("bước 1 của phần 4", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertEqual(frame.get("scope"), "local_section")

    def test_global_next_query_does_not_set_step_number(self):
        history = [{"role": "assistant", "content": "PHẦN 1: Tra cứu"}]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertIsNone((analysis.get("entities") or {}).get("step_number"))

    def test_local_next_query_sets_step_number(self):
        history = [{"role": "assistant", "content": "B1: Chuẩn bị hồ sơ"}]
        analysis = self.retriever.analyze("bước tiếp theo nộp hồ sơ", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_global_prev_query_does_not_set_local_scope(self):
        history = [{"role": "assistant", "content": "PHẦN 2: Xác nhận"}]
        analysis = self.retriever.analyze("bước trước đó", chat_history=history)
        self.assertFalse((analysis.get("entities") or {}).get("local_step_scope", False))

    def test_local_prev_query_sets_local_scope(self):
        history = [{"role": "assistant", "content": "B2: Chụp ảnh"}]
        analysis = self.retriever.analyze("bước trước đó nộp hồ sơ", chat_history=history)
        self.assertTrue((analysis.get("entities") or {}).get("local_step_scope"))

    def test_where_filter_none_for_section_count_query(self):
        analysis = self.retriever.analyze("thủ tục nhập học có mấy phần", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertIsNone(where)

    def test_where_filter_none_for_step_count_local_query(self):
        analysis = self.retriever.analyze("phần 4 nộp hồ sơ có mấy bước", chat_history=[])
        where = self.retriever._build_where_filter(
            analysis.get("intent", "general"),
            analysis.get("entities") or {},
            query_frame=analysis.get("query_frame") or {}
        )
        self.assertIsNone(where)

    def test_global_buoc_wording_without_context_defaults_section1(self):
        analysis = self.retriever.analyze("bước là gì", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_local_buoc_wording_with_ho_so_defaults_step1(self):
        analysis = self.retriever.analyze("bước nộp hồ sơ là gì", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 1)

    def test_global_query_frame_has_section_nav_candidate(self):
        analysis = self.retriever.analyze("bước đầu của thủ tục nhập học", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertIn("phan_1", frame.get("nav_target_candidates") or [])

    def test_local_query_frame_has_local_step_nav_candidate(self):
        analysis = self.retriever.analyze("bước 1 nộp hồ sơ", chat_history=[])
        frame = analysis.get("query_frame") or {}
        self.assertIn("b1_phan_4", frame.get("nav_target_candidates") or [])

    def test_global_intent_from_section_number(self):
        analysis = self.retriever.analyze("phần 2", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_local_intent_from_step_number_and_scope(self):
        analysis = self.retriever.analyze("bước 2 nộp hồ sơ", chat_history=[])
        self.assertEqual(analysis.get("intent"), "step")

    def test_global_relative_resolve_from_history_reason(self):
        history = [{"role": "assistant", "content": "PHẦN 1: Tra cứu"}]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertIn("relative_section_from_history", (analysis.get("query_frame") or {}).get("debug_reason", ""))

    def test_local_relative_resolve_from_history_reason(self):
        history = [{"role": "assistant", "content": "B1: Chuẩn bị hồ sơ"}]
        analysis = self.retriever.analyze("bước tiếp theo nộp hồ sơ", chat_history=history)
        self.assertIn("relative_local_step_from_history", (analysis.get("query_frame") or {}).get("debug_reason", ""))

    def test_global_followup_next_after_explicit_section_query(self):
        history = [
            {"role": "user", "content": "phần 2"},
            {"role": "assistant", "content": "PHẦN 2: Xác nhận nhập học"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)

    def test_global_followup_next_reads_section_from_source_line(self):
        history = [
            {"role": "assistant", "content": "- Xác nhận nhập học trực tuyến\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 2, Năm 2025)"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)

    def test_global_followup_next_chain_progresses_2_to_3_to_4(self):
        history = [
            {"role": "assistant", "content": "- Nội dung phần 2\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 2, Năm 2025)"}
        ]
        a1 = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((a1.get("entities") or {}).get("section_number"), 3)

        history2 = history + [{"role": "assistant", "content": "- Nội dung phần 3\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 3, Năm 2025)"}]
        a2 = self.retriever.analyze("bước tiếp theo", chat_history=history2)
        self.assertEqual((a2.get("entities") or {}).get("section_number"), 4)

    def test_ambiguous_relative_prefers_latest_local_context_over_global(self):
        history = [
            {"role": "assistant", "content": "- Nội dung phần 2\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 2, Năm 2025)"},
            {"role": "assistant", "content": "B1: Chuẩn bị hồ sơ\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 4, Năm 2025)"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        entities = analysis.get("entities") or {}
        frame = analysis.get("query_frame") or {}
        self.assertEqual(analysis.get("intent"), "step")
        self.assertEqual(entities.get("step_number"), 2)
        self.assertEqual(frame.get("nav_target_type"), "local_step")
        self.assertEqual((frame.get("nav_target_candidates") or [None])[0], "b2_phan_4")

    def test_ambiguous_relative_prefers_latest_global_when_no_local_signal(self):
        history = [
            {"role": "assistant", "content": "- Nội dung phần 2\n[SOURCE] Nguồn: Thủ tục nhập học 2025.txt (PHẦN 2, Năm 2025)"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 3)
        self.assertEqual((analysis.get("query_frame") or {}).get("nav_target_type"), "section")
        self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_global_followup_prev_after_explicit_section_query(self):
        history = [
            {"role": "assistant", "content": "PHẦN 2: Xác nhận nhập học"}
        ]
        analysis = self.retriever.analyze("bước trước đó", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 1)

    def test_local_followup_next_after_explicit_b_step_query(self):
        history = [
            {"role": "assistant", "content": "B2: Chụp ảnh hồ sơ"}
        ]
        analysis = self.retriever.analyze("bước tiếp theo phần 4", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 3)

    def test_local_followup_prev_after_explicit_b_step_query(self):
        history = [
            {"role": "assistant", "content": "B2: Chụp ảnh hồ sơ"}
        ]
        analysis = self.retriever.analyze("bước trước đó phần 4", chat_history=history)
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 1)

    def test_global_buoc_dau_intent_not_step(self):
        analysis = self.retriever.analyze("bước đầu của thủ tục nhập học", chat_history=[])
        self.assertNotEqual(analysis.get("intent"), "step")

    def test_local_buoc_dau_intent_step(self):
        analysis = self.retriever.analyze("bước đầu của phần 4", chat_history=[])
        self.assertEqual(analysis.get("intent"), "step")

    def test_global_buoc_tiep_theo_intent_not_step(self):
        analysis = self.retriever.analyze("bước tiếp theo của thủ tục nhập học", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_local_buoc_tiep_theo_intent_step(self):
        analysis = self.retriever.analyze("bước tiếp theo của phần 4", chat_history=[])
        self.assertEqual(analysis.get("intent"), "step")

    def test_section_count_query_intent_admission_procedure(self):
        analysis = self.retriever.analyze("thủ tục nhập học có mấy phần", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_local_step_count_query_intent_admission_procedure(self):
        analysis = self.retriever.analyze("phần 4 nộp hồ sơ có mấy bước", chat_history=[])
        self.assertEqual(analysis.get("intent"), "admission_procedure")

    def test_section_count_query_sets_flag(self):
        analysis = self.retriever.analyze("thủ tục nhập học có mấy bước", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("ask_section_count"))

    def test_local_step_count_query_sets_flag(self):
        analysis = self.retriever.analyze("nộp hồ sơ có mấy bước", chat_history=[])
        self.assertTrue((analysis.get("entities") or {}).get("ask_step_count_local"))

    def test_section_query_frame_scope_global(self):
        analysis = self.retriever.analyze("phần 1", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("scope"), "global")

    def test_local_step_query_frame_scope_local(self):
        analysis = self.retriever.analyze("bước 1 phần 4", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("scope"), "local_section")

    def test_global_query_frame_nav_type_section(self):
        analysis = self.retriever.analyze("bước đầu thủ tục", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("nav_target_type"), "section")

    def test_local_query_frame_nav_type_local_step(self):
        analysis = self.retriever.analyze("bước đầu phần 4", chat_history=[])
        self.assertEqual((analysis.get("query_frame") or {}).get("nav_target_type"), "local_step")

    def test_global_next_without_history_reason_default(self):
        analysis = self.retriever.analyze("bước tiếp theo", chat_history=[])
        self.assertIn("default", (analysis.get("query_frame") or {}).get("debug_reason", ""))

    def test_global_prev_without_history_reason_default(self):
        analysis = self.retriever.analyze("bước trước đó", chat_history=[])
        self.assertIn("default", (analysis.get("query_frame") or {}).get("debug_reason", ""))

    def test_local_next_without_history_reason_default(self):
        analysis = self.retriever.analyze("bước tiếp theo nộp hồ sơ", chat_history=[])
        self.assertIn("relative", (analysis.get("query_frame") or {}).get("debug_reason", ""))

    def test_local_prev_without_history_reason_default(self):
        analysis = self.retriever.analyze("bước trước đó nộp hồ sơ", chat_history=[])
        self.assertIn("relative", (analysis.get("query_frame") or {}).get("debug_reason", ""))

    def test_query_with_explicit_section_and_next_keeps_section_axis(self):
        analysis = self.retriever.analyze("phần 2 bước tiếp theo", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("section_number"), 2)

    def test_query_with_explicit_local_and_next_keeps_step_axis(self):
        analysis = self.retriever.analyze("bước 2 phần 4 bước tiếp theo", chat_history=[])
        self.assertEqual((analysis.get("entities") or {}).get("step_number"), 2)

    def test_history_mentions_section4_detected_with_b1_ho_so(self):
        history = [{"role": "assistant", "content": "B1 hồ sơ"}]
        self.assertTrue(self.retriever._history_mentions_section4(history))

    def test_history_mentions_section4_not_detected_with_section2(self):
        history = [{"role": "assistant", "content": "PHẦN 2 xác nhận"}]
        self.assertFalse(self.retriever._history_mentions_section4(history))

    def test_last_section_from_history_detects_section_label(self):
        history = [{"role": "assistant", "content": "PHẦN 3: Nộp học phí"}]
        self.assertEqual(self.retriever._last_section_from_history(history), 3)

    def test_last_section_from_history_none_when_absent(self):
        history = [{"role": "assistant", "content": "Xin chào"}]
        self.assertIsNone(self.retriever._last_section_from_history(history))

    def test_last_step_from_history_detects_b_label(self):
        history = [{"role": "assistant", "content": "B3: Upload"}]
        self.assertEqual(self.retriever._last_step_from_history(history), 3)

    def test_last_step_from_history_none_when_absent(self):
        history = [{"role": "assistant", "content": "PHẦN 3"}]
        self.assertIsNone(self.retriever._last_step_from_history(history))


if __name__ == "__main__":
    unittest.main()
