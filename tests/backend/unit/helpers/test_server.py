"""Tests for helpers/server.py — api_response and orm_to_dict."""

from helpers.server import api_response


class TestApiResponse:

    def test_success_response(self):
        result = api_response(True, "OK")
        assert result == {"status": True, "message": "OK"}

    def test_failure_response(self):
        result = api_response(False, "Error")
        assert result == {"status": False, "message": "Error"}

    def test_with_extra_data(self):
        result = api_response(True, "OK", {"key": "value"})
        assert result["status"] is True
        assert result["message"] == "OK"
        assert result["data"] == {"key": "value"}

    def test_no_data_key_when_none(self):
        result = api_response(True, "OK")
        assert "data" not in result

    def test_data_can_be_list(self):
        result = api_response(True, "OK", [1, 2, 3])
        assert result["data"] == [1, 2, 3]

    def test_data_can_be_nested(self):
        data = {"users": [{"id": 1}], "count": 1}
        result = api_response(True, "OK", data)
        assert result["data"]["users"][0]["id"] == 1
