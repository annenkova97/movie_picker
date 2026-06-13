"""Unit tests for the shared text-matching helpers (no network, pure logic)."""

from __future__ import annotations

from backend.services.text_match import extract_year, normalize_title, title_score


# ── normalize_title ──────────────────────────────────────────────────────────


def test_normalize_unifies_yo_and_strips_punctuation():
    # ё/Ё → е/Е, пунктуация → пробелы, регистр снят.
    assert normalize_title("Ёлки-палки!") == normalize_title("елки палки")
    assert normalize_title("  Дюна:  Часть   вторая ") == "дюна часть вторая"


def test_normalize_handles_empty():
    assert normalize_title(None) == ""
    assert normalize_title("   ") == ""


# ── title_score ──────────────────────────────────────────────────────────────


def test_title_score_exact_is_one():
    assert title_score("Дюна", "Дюна") == 1.0
    # отличается только пунктуацией/ё/регистром → всё равно точное.
    assert title_score("Ёлки!", "елки") == 1.0


def test_title_score_substring_beats_unrelated():
    sub = title_score("Дюна", "Дюна: Пророчество")
    unrelated = title_score("Дюна", "Криминальное чтиво")
    assert sub >= 0.85
    assert unrelated < 0.5
    assert sub > unrelated


def test_title_score_empty_is_zero():
    assert title_score("", "Дюна") == 0.0
    assert title_score("Дюна", None) == 0.0


# ── extract_year ─────────────────────────────────────────────────────────────


def test_extract_year_only_parenthesized():
    assert extract_year("Ирония судьбы (1975)") == ("Ирония судьбы", 1975)
    # Голые числа в названии — НЕ год релиза (иначе фильтр навредит).
    assert extract_year("Бегущий по лезвию 2049") == ("Бегущий по лезвию 2049", None)
    assert extract_year("2001: A Space Odyssey") == ("2001: A Space Odyssey", None)
    assert extract_year("Дюна") == ("Дюна", None)
