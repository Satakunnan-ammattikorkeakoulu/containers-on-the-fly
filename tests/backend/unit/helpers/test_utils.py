"""Tests for helpers/utils.py."""

from helpers.utils import remove_special_characters


class TestRemoveSpecialCharacters:

    def test_removes_punctuation(self):
        assert remove_special_characters("hello!") == "hello"

    def test_preserves_spaces(self):
        assert remove_special_characters("hello world") == "hello world"

    def test_empty_string(self):
        assert remove_special_characters("") == ""

    def test_all_special_chars(self):
        assert remove_special_characters("@#$%^&*") == ""

    def test_preserves_numbers(self):
        assert remove_special_characters("test123") == "test123"

    def test_mixed_content(self):
        assert remove_special_characters("user@foo.com") == "userfoocom"

    def test_preserves_letters(self):
        assert remove_special_characters("AbCdEf") == "AbCdEf"
