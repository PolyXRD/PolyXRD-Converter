# -*- coding: utf-8 -*-
"""registration.py 核心逻辑自测（纯 stdlib，无需 PySide6）。

移植自 PolyXRD-Reg 项目的 tests/test_registration.py（家族统一注册机制的
同一套用例），import 路径改为本包 polyxrd_converter.registration。

用法::

    python tests/test_registration.py        # 全部通过时退出码 0
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from polyxrd_converter.registration import (  # noqa: E402
    CODE_PREFIX,
    RegistrationState,
    default_state_path,
    generate_code,
    load_state,
    save_state,
    set_language,
    verify_code,
)


class TestRoundTrip(unittest.TestCase):
    def test_chinese_unit(self) -> None:
        unit = "清华大学材料学院"
        self.assertEqual(verify_code(generate_code(unit)), unit)

    def test_english_unit(self) -> None:
        unit = "Department of Materials Science, Tsinghua University"
        self.assertEqual(verify_code(generate_code(unit)), unit)

    def test_long_unit(self) -> None:
        unit = "某" * 100
        self.assertEqual(verify_code(generate_code(unit)), unit)

    def test_code_prefix_and_grouping(self) -> None:
        code = generate_code("测试单位")
        self.assertTrue(code.startswith(CODE_PREFIX + "-"))
        body = code[len(CODE_PREFIX) + 1:]
        for group in body.split("-"):
            self.assertLessEqual(len(group), 4)
        self.assertNotIn("1", body)  # Base32 字符集 A-Z2-7，不含 1

    def test_whitespace_collapsed(self) -> None:
        unit = "  清华大学   材料学院  "
        self.assertEqual(verify_code(generate_code(unit)), "清华大学 材料学院")


class TestInputTolerance(unittest.TestCase):
    def setUp(self) -> None:
        self.code = generate_code("北京大学化学学院")

    def test_lowercase_and_spaces(self) -> None:
        messy = "  " + self.code.lower().replace("-", " ") + "\n"
        self.assertEqual(verify_code(messy), "北京大学化学学院")

    def test_fullwidth_dash(self) -> None:
        self.assertEqual(verify_code(self.code.replace("-", "－")), "北京大学化学学院")

    def test_without_prefix(self) -> None:
        body = self.code[len(CODE_PREFIX) + 1:]
        self.assertEqual(verify_code(body), "北京大学化学学院")

    def test_prefix_lowercase(self) -> None:
        self.assertEqual(verify_code(self.code.lower()), "北京大学化学学院")


class TestInvalidCodes(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(verify_code(""))

    def test_garbage(self) -> None:
        for bad in ("hello", "PXRD1-ABCD", "12345678", "PXRD1-" + "A" * 8, "本软件未注册"):
            self.assertIsNone(verify_code(bad), bad)

    def test_tampered_payload(self) -> None:
        code = generate_code("测试单位")
        # 改一个字符（保持 Base32 合法）→ 必须校验失败
        body = list(code[len(CODE_PREFIX) + 1:].replace("-", ""))
        body[0] = "B" if body[0] != "B" else "C"
        self.assertIsNone(verify_code(CODE_PREFIX + "-" + "".join(body)))

    def test_swapped_units(self) -> None:
        # A 单位的码不等于 B 单位的码（HMAC 绑定单位名）
        self.assertNotEqual(generate_code("单位甲"), generate_code("单位乙"))

    def test_invalid_unit_name(self) -> None:
        for bad in ("", "   ", "x" * 101, "bad\x00name"):
            with self.assertRaises(ValueError):
                generate_code(bad)


class TestStateFile(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "registration.json"
            self.assertEqual(load_state(path), RegistrationState(False))
            state = save_state(path, generate_code("中科院物理所"))
            self.assertTrue(state.registered)
            self.assertEqual(state.unit, "中科院物理所")
            self.assertEqual(load_state(path), state)

    def test_tampered_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registration.json"
            save_state(path, generate_code("某大学"))
            data = json.loads(path.read_text(encoding="utf-8"))
            data["unit"] = "篡改后的单位"  # 手改 JSON 伪造 → 必须失效
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertFalse(load_state(path).registered)

    def test_corrupt_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registration.json"
            path.write_text("not json at all", encoding="utf-8")
            self.assertFalse(load_state(path).registered)

    def test_invalid_code_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registration.json"
            with self.assertRaises(ValueError):
                save_state(path, "PXRD1-GARBAGE")

    def test_default_state_path(self) -> None:
        path = default_state_path("PolyXRD-Converter")
        self.assertEqual(path.name, "PolyXRD_Converter.json")  # 非字母数字 → _
        self.assertTrue(path.suffix == ".json")
        self.assertEqual(default_state_path("XinMatch").name, "XinMatch.json")


class TestI18n(unittest.TestCase):
    def test_status_text(self) -> None:
        set_language("zh")
        self.assertEqual(RegistrationState(True, "某大学", "code").status_text, "已注册：某大学")
        self.assertEqual(RegistrationState(False).status_text, "未注册")
        set_language("en")
        self.assertEqual(RegistrationState(False).status_text, "Unregistered")
        set_language("ja")
        self.assertEqual(RegistrationState(False).status_text, "未登録")
        set_language("zh")

    def test_unregistered_notice_is_fixed_chinese(self) -> None:
        # 需求固定文案: 不随语言切换
        from polyxrd_converter.registration import CONTACT_EMAIL, UNREGISTERED_NOTICE
        self.assertIn("本软件未注册，版权所有，禁止用于商业用途", UNREGISTERED_NOTICE)
        self.assertIn(CONTACT_EMAIL, UNREGISTERED_NOTICE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
