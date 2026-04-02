"""Tests for validate_script_path from endpoints/responses/user.py."""

from endpoints.responses.user import validate_script_path


class TestValidateScriptPath:

    def test_valid_absolute_path(self):
        assert validate_script_path("/usr/local/bin/start.sh") is None

    def test_valid_path_with_dots(self):
        assert validate_script_path("/home/user/scripts/v1.2/run.sh") is None

    def test_valid_path_with_hyphens_underscores(self):
        assert validate_script_path("/opt/my-app/start_script") is None

    def test_relative_path_rejected(self):
        error = validate_script_path("relative/path.sh")
        assert error is not None
        assert "absolute path" in error

    def test_path_over_500_chars_rejected(self):
        long_path = "/" + "a" * 500
        error = validate_script_path(long_path)
        assert error is not None
        assert "500" in error

    def test_exactly_500_chars_accepted(self):
        path = "/" + "a" * 499
        assert validate_script_path(path) is None

    def test_invalid_characters_rejected(self):
        error = validate_script_path("/path/with spaces/script.sh")
        assert error is not None

    def test_special_chars_rejected(self):
        error = validate_script_path("/path/script;rm -rf /")
        assert error is not None

    def test_empty_looking_path_rejected(self):
        error = validate_script_path("")
        assert error is not None
