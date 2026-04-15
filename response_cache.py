"""
Response caching layer - để chatbot vẫn hoạt động khi API hết quota
"""
import json
import os
import time
import unicodedata
from typing import Dict, Optional
import re


class ResponseCache:
    """Cache responses chất lượng cao để tăng ổn định khi trả lời"""

    def __init__(self, cache_file: str = "response_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.templates = self._load_templates()
        self.cleanup()

    def _load_cache(self) -> Dict:
        """Load cache từ file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Save cache vào file"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _load_templates(self) -> Dict:
        """Template responses cho các intent phổ biến"""
        return {
            'fee_info': {
                'keywords': ['học phí', 'tiền học', 'lệ phí', 'fee'],
                'template': """Dựa trên thông tin từ tài liệu tuyển sinh 2025, học phí được tính theo các quy định của Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội.

[INFO] Thông tin chi tiết:
- Học phí được tính theo số tín chỉ hoặc theo học kỳ
- Sinh viên được hỗ trợ học bổng và miễn giảm học phí nếu đủ điều kiện
- Có hình thức trả học phí linh hoạt

[TIP] Để biết chính xác học phí cho ngành của bạn, vui lòng:
- Liên hệ phòng Đào tạo: 024.38581283
- Email: ctsv@hus.edu.vn
- Hoặc xem tài liệu tuyển sinh chính thức"""
            },
            'schedule': {
                'keywords': ['lịch', 'thời gian', 'ngày', 'kỳ', 'đợt', 'deadline'],
                'template': """Lịch tuyển sinh năm 2025 của Trường Đại học Khoa học Tự nhiên:

📅 Thông tin quan trọng:
- Đợt 1: Đăng ký từ tháng 3-4/2025
- Đợt 2: Đăng ký từ tháng 6-7/2025
- Đợt 3: Đăng ký từ tháng 8-9/2025

[TIME] Lưu ý: Các ngành khác nhau có thời gian đăng ký khác nhau

[PHONE] Liên hệ để cập nhật lịch mới nhất:
- Hotline: 024.38581283
- Email: tuyensinh@hus.edu.vn"""
            },
            'admission_procedure': {
                'keywords': ['thủ tục', 'nhập học', 'hồ sơ', 'giấy tờ', 'cách đăng ký'],
                'template': """Thủ tục nhập học 2025 tại Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội:

[FORM] Hồ sơ cần chuẩn bị:
1. Giấy chứng nhận kết quả thi THPT hoặc điểm xét tuyển
2. Giấy khai sinh (bản sao công chứng)
3. Hộ chiếu/CMND
4. Hình ảnh 4x6 (4 tấm)
5. Bảng điểm/văn bằng tốt nghiệp THPT
6. Giấy khám sức khỏe

[UPLOAD] Cách đăng ký:
- Trực tuyến qua website tuyển sinh
- Hoặc trực tiếp tại phòng Công tác sinh viên

[PHONE] Hỗ trợ:
- Hotline: 024.38581283
- Email: ctsv@hus.edu.vn"""
            },
            'document_required': {
                'keywords': ['giấy tờ', 'hồ sơ', 'cần', 'yêu cầu', 'document'],
                'template': """Giấy tờ cần thiết cho thủ tục nhập học 2025:

[OK] Bắt buộc:
- CMND/Hộ chiếu
- Giấy khai sinh (bản sao công chứng)
- Chứng chỉ kết quả thi tốt nghiệp THPT
- Giấy khám sức khỏe

[NOTE] Khuyến nghị:
- Hình ảnh 4x6 (4 tấm)
- Sơ yếu lý lịch
- Giấy tờ khác nếu có

[TIP] Lưu ý: Gửi hồ sơ gốc hoặc bản sao công chứng (không chấp nhận photocopy)

[EMAIL] Nộp hồ sơ:
- Trực tuyến: https://tuyensinh.hus.edu.vn
- Trực tiếp: Phòng Công tác sinh viên, Nhà A1, Cơ sở Nghĩa Dõ"""
            },
            'admission_score': {
                'keywords': ['điểm', 'xét tuyển', 'điểm chuẩn', 'score'],
                'template': """Điểm xét tuyển 2025 của Trường Đại học Khoa học Tự nhiên:

[STATS] Thông tin chung:
- Xét tuyển dựa trên kết quả thi THPT Quốc gia
- Lấy ba môn bắt buộc + một môn tự chọn (tùy theo chuyên ngành)
- Điểm chuẩn các năm trước: 18-28 tùy ngành

[TARGET] Các ngành phổ biến:
- Toán học: ~26-28 điểm
- Vật lý: ~25-27 điểm
- Hóa học: ~24-26 điểm
- Sinh học: ~23-25 điểm
- Công nghệ thông tin: ~27-29 điểm

[WARNING] Điểm chuẩn năm 2025 sẽ được công bố sau kỳ thi THPT

[PHONE] Thông tin cập nhật:
- Website: tuyensinh.hus.edu.vn
- Email: tuyensinh@hus.edu.vn"""
            },
            'generic': {
                'keywords': [],
                'template': """Cảm ơn câu hỏi của bạn!

Tôi là chatbot hỗ trợ thông tin tuyển sinh 2025 của Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội.

[PIN] Tôi có thể giúp bạn về:
- [OK] Thủ tục nhập học
- [OK] Lịch tuyển sinh
- [OK] Học phí và các khoản khác
- [OK] Giấy tờ cần thiết
- [OK] Điểm xét tuyển

[MESSAGE] Hãy đặt câu hỏi cụ thể hơn để tôi hỗ trợ tốt hơn!

[PHONE] Liên hệ trực tiếp:
- Hotline: 024.38581283
- Email: ctsv@hus.edu.vn"""
            }
        }

    def get(
        self,
        query: str,
        intent: Optional[str] = None,
        session_id: str = 'default',
        user_id: str = 'anonymous',
        style_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Lấy response từ cache (chỉ ưu tiên bản chất lượng cao)."""
        query_key = self._cache_key(
            query,
            intent,
            session_id=session_id,
            user_id=user_id,
            style_id=style_id
        )
        item = self.cache.get(query_key)

        # Khi đã dùng style_id thì bắt buộc match đúng style-key để tránh đạp khuôn từ cache cũ
        if not item and style_id is None:
            # Backward-compatible fallback cho scoped-key cũ chưa có style
            scoped_legacy_key = self._cache_key(
                query,
                intent,
                session_id=session_id,
                user_id=user_id,
                style_id=None
            )
            item = self.cache.get(scoped_legacy_key)

            # Backward-compatible fallback cho key cũ chưa có scope user/session
            if not item:
                legacy_key = self._cache_key(query, intent)
                item = self.cache.get(legacy_key)

        if not item:
            return None
        if item.get('quality', 'high') != 'high':
            return None
        return item

    def save(
        self,
        query: str,
        response: str,
        intent: Optional[str] = None,
        source_type: str = 'api',
        quality: str = 'high',
        session_id: str = 'default',
        user_id: str = 'anonymous',
        style_id: Optional[str] = None
    ):
        """Lưu response vào cache với metadata chất lượng."""
        query_key = self._cache_key(
            query,
            intent,
            session_id=session_id,
            user_id=user_id,
            style_id=style_id
        )
        self.cache[query_key] = {
            'response': response,
            'timestamp': time.time(),
            'intent': intent or 'general',
            'source_type': source_type,
            'quality': quality,
            'session_id': session_id,
            'user_id': user_id,
            'style_id': style_id
        }
        self._save_cache()

    def _cache_key(
        self,
        query: str,
        intent: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        style_id: Optional[str] = None
    ) -> str:
        normalized = self._normalize_query(query)
        if session_id is None and user_id is None:
            # Legacy key format để tương thích dữ liệu cũ
            return f"{intent or 'general'}::{normalized}"
        sid = self._normalize_scope_token(session_id or 'default')
        uid = self._normalize_scope_token(user_id or 'anonymous')
        if style_id is None:
            return f"{uid}::{sid}::{intent or 'general'}::{normalized}"
        sty = self._normalize_scope_token(style_id)
        return f"{uid}::{sid}::{intent or 'general'}::{sty}::{normalized}"

    @staticmethod
    def _normalize_scope_token(value: str) -> str:
        v = unicodedata.normalize('NFKC', str(value or '')).strip().lower()
        v = re.sub(r'[^\w\-\.]+', '_', v)
        return v or 'unknown'

    def clear_session(self, session_id: str, user_id: str = 'anonymous'):
        """Xóa cache theo scope session/user."""
        sid = self._normalize_scope_token(session_id)
        uid = self._normalize_scope_token(user_id)
        prefix = f"{uid}::{sid}::"
        old_keys = [k for k in self.cache.keys() if k.startswith(prefix)]
        for k in old_keys:
            self.cache.pop(k, None)
        if old_keys:
            self._save_cache()

    def _normalize_query(self, query: str) -> str:
        """Normalize query để sử dụng làm key."""
        q = unicodedata.normalize('NFKC', (query or '').lower().strip())
        q = re.sub(r'[^\w\sÀ-ỹ]', ' ', q)
        q = re.sub(r'\s+', ' ', q).strip()
        return q

    def cleanup(self):
        """Dọn cache cũ về key mới và loại entry chất lượng thấp/template."""
        cleaned = {}
        template_texts = [v.get('template', '') for v in self.templates.values()]

        for old_key, item in self.cache.items():
            if not isinstance(item, dict):
                continue

            response = item.get('response', '')
            source_type = item.get('source_type', 'api')
            quality = item.get('quality', 'high')
            intent = item.get('intent')

            is_exact_template = any(response.strip() == t.strip() for t in template_texts if t)
            is_template_like = (
                ('[PIN] Tôi có thể giúp bạn về:' in response) or
                ('[INFO] Thông tin chi tiết:' in response and '[SOURCE]' not in response) or
                ('Dựa trên thông tin từ tài liệu tuyển sinh 2025' in response and '[SOURCE]' not in response)
            )

            if source_type in {'template', 'error'} or quality == 'low' or is_exact_template or is_template_like:
                continue

            if '::' in old_key:
                new_key = old_key
            else:
                new_key = self._cache_key(old_key, intent)

            existed = cleaned.get(new_key)
            if not existed or item.get('timestamp', 0) > existed.get('timestamp', 0):
                cleaned[new_key] = {
                    'response': response,
                    'timestamp': item.get('timestamp', time.time()),
                    'intent': intent or 'general',
                    'source_type': source_type,
                    'quality': quality,
                    'session_id': item.get('session_id', 'default'),
                    'user_id': item.get('user_id', 'anonymous'),
                    'style_id': item.get('style_id')
                }

        self.cache = cleaned
        self._save_cache()

    def get_template_response(self, query: str, intent: Optional[str] = None) -> Optional[str]:
        """Lấy template response dựa trên intent hoặc keyword"""
        query_lower = query.lower()

        if intent and intent in self.templates:
            return self.templates[intent]['template']

        for intent_name, intent_data in self.templates.items():
            if intent_name == 'generic':
                continue
            keywords = intent_data.get('keywords', [])
            for keyword in keywords:
                if keyword in query_lower:
                    return intent_data['template']

        return self.templates['generic']['template']


# Global cache instance
_cache_instance = None


def get_cache():
    """Get hoặc tạo cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResponseCache()
    return _cache_instance
