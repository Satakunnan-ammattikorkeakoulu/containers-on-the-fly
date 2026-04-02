"""Tests for container server api_client.py."""

from unittest.mock import patch, MagicMock
import requests

from api_client import DaemonApiClient


class TestDaemonApiClientInit:

    def test_http_base_url(self):
        client = DaemonApiClient("example.com", False, "key123", "srv1")
        assert client.base == "http://example.com/api/daemon"

    def test_https_base_url(self):
        client = DaemonApiClient("example.com", True, "key123", "srv1")
        assert client.base == "https://example.com/api/daemon"

    def test_auth_headers_set(self):
        client = DaemonApiClient("example.com", False, "key123", "srv1")
        assert client.session.headers["X-Daemon-Api-Key"] == "key123"
        assert client.session.headers["X-Daemon-Server-Name"] == "srv1"

    def test_server_name_stored(self):
        client = DaemonApiClient("example.com", False, "key123", "srv1")
        assert client.server_name == "srv1"


class TestRequest:

    def _make_client(self):
        return DaemonApiClient("localhost", False, "key", "srv")

    @patch.object(requests.Session, "request")
    def test_successful_request(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": True, "data": {}}
        mock_resp.raise_for_status = MagicMock()
        mock_request.return_value = mock_resp

        client = self._make_client()
        result = client._request("GET", "/tasks")
        assert result == {"status": True, "data": {}}

    @patch("api_client.time.sleep")
    @patch.object(requests.Session, "request")
    def test_retries_on_connection_error(self, mock_request, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": True}
        mock_resp.raise_for_status = MagicMock()
        mock_request.side_effect = [
            requests.exceptions.ConnectionError("refused"),
            mock_resp,
        ]

        client = self._make_client()
        result = client._request("GET", "/tasks", retries=3)
        assert result == {"status": True}
        assert mock_request.call_count == 2

    @patch("api_client.time.sleep")
    @patch.object(requests.Session, "request")
    def test_returns_none_after_all_retries_exhausted(self, mock_request, mock_sleep):
        mock_request.side_effect = requests.exceptions.ConnectionError("refused")

        client = self._make_client()
        result = client._request("GET", "/tasks", retries=2)
        assert result is None
        assert mock_request.call_count == 2

    @patch.object(requests.Session, "request")
    def test_returns_none_on_http_error(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_request.return_value = mock_resp

        client = self._make_client()
        result = client._request("GET", "/tasks")
        assert result is None


class TestGetTasks:

    def _make_client(self):
        return DaemonApiClient("localhost", False, "key", "srv")

    @patch.object(DaemonApiClient, "_request")
    def test_returns_data_on_success(self, mock_req):
        mock_req.return_value = {"status": True, "data": {"toStart": [], "toStop": []}}
        client = self._make_client()
        result = client.get_tasks()
        assert result == {"toStart": [], "toStop": []}

    @patch.object(DaemonApiClient, "_request")
    def test_returns_none_on_failure(self, mock_req):
        mock_req.return_value = None
        client = self._make_client()
        assert client.get_tasks() is None

    @patch.object(DaemonApiClient, "_request")
    def test_returns_none_on_status_false(self, mock_req):
        mock_req.return_value = {"status": False, "message": "error"}
        client = self._make_client()
        assert client.get_tasks() is None


class TestGetOrphanCheck:

    def _make_client(self):
        return DaemonApiClient("localhost", False, "key", "srv")

    @patch.object(DaemonApiClient, "_request")
    def test_returns_container_names(self, mock_req):
        mock_req.return_value = {
            "status": True,
            "data": {"runningContainerNames": ["cont1", "cont2"]},
        }
        client = self._make_client()
        assert client.get_orphan_check() == ["cont1", "cont2"]

    @patch.object(DaemonApiClient, "_request")
    def test_returns_empty_list_on_failure(self, mock_req):
        mock_req.return_value = None
        client = self._make_client()
        assert client.get_orphan_check() == []


class TestGetComputerId:

    def _make_client(self):
        return DaemonApiClient("localhost", False, "key", "srv")

    @patch.object(DaemonApiClient, "_request")
    def test_returns_computer_id(self, mock_req):
        mock_req.return_value = {"status": True, "data": {"computerId": 5}}
        client = self._make_client()
        assert client.get_computer_id("srv1") == 5

    @patch.object(DaemonApiClient, "_request")
    def test_returns_none_on_failure(self, mock_req):
        mock_req.return_value = None
        client = self._make_client()
        assert client.get_computer_id("srv1") is None


class TestReportMethods:

    def _make_client(self):
        return DaemonApiClient("localhost", False, "key", "srv")

    @patch.object(DaemonApiClient, "_request")
    def test_report_started_success(self, mock_req):
        mock_req.return_value = {"status": True}
        client = self._make_client()
        assert client.report_started(1, {"containerDockerName": "c1"}) is True

    @patch.object(DaemonApiClient, "_request")
    def test_report_started_failure(self, mock_req):
        mock_req.return_value = None
        client = self._make_client()
        assert client.report_started(1, {}) is False

    @patch.object(DaemonApiClient, "_request")
    def test_report_stopped_success(self, mock_req):
        mock_req.return_value = {"status": True}
        client = self._make_client()
        assert client.report_stopped(1) is True

    @patch.object(DaemonApiClient, "_request")
    def test_report_start_failed(self, mock_req):
        mock_req.return_value = {"status": True}
        client = self._make_client()
        assert client.report_start_failed(1, "error msg") is True
        mock_req.assert_called_once_with(
            "POST", "/reservation/1/start-failed",
            json={"errorMessage": "error msg"},
        )

    @patch.object(DaemonApiClient, "_request")
    def test_report_paused(self, mock_req):
        mock_req.return_value = {"status": True}
        client = self._make_client()
        assert client.report_paused(1, "ubuntu", "srv1") is True

    @patch.object(DaemonApiClient, "_request")
    def test_report_restarted(self, mock_req):
        mock_req.return_value = {"status": True}
        client = self._make_client()
        assert client.report_restarted(1, True) is True

    @patch.object(DaemonApiClient, "_request")
    def test_submit_monitoring(self, mock_req):
        mock_req.return_value = {"status": True}
        client = self._make_client()
        assert client.submit_monitoring({"cpuUsagePercent": 50.0}) is True

    @patch.object(DaemonApiClient, "_request")
    def test_reset_stale_builds(self, mock_req):
        mock_req.return_value = {"status": True}
        client = self._make_client()
        assert client.reset_stale_builds() is True

    @patch.object(DaemonApiClient, "_request")
    def test_update_image_sizes_batch(self, mock_req):
        mock_req.return_value = {"status": True}
        client = self._make_client()
        assert client.update_image_sizes_batch([{"imageName": "img", "imageSize": 100}]) is True
