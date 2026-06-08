"""Tests for helpers/docker_registry.py — mocked HTTP calls, no DB."""

from unittest.mock import patch, MagicMock

import requests

from helpers.docker_registry import image_exists_in_registry


def _mock_response(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    return resp


class TestImageExistsInRegistry:

    def test_returns_true_on_200(self):
        with patch("helpers.docker_registry.requests.head",
                   return_value=_mock_response(200)) as mock_head:
            with patch("helpers.docker_registry.settings_handler.get_setting",
                       side_effect=lambda k: "localhost:5000" if k == "docker.registryAddress"
                       else ("http" if k == "docker.registryScheme" else None)):
                assert image_exists_in_registry("my-image") is True
        url = mock_head.call_args.args[0]
        assert url == "http://localhost:5000/v2/my-image/manifests/latest"

    def test_returns_false_on_404(self):
        with patch("helpers.docker_registry.requests.head",
                   return_value=_mock_response(404)):
            with patch("helpers.docker_registry.settings_handler.get_setting",
                       side_effect=lambda k: "localhost:5000" if k == "docker.registryAddress"
                       else ("http" if k == "docker.registryScheme" else None)):
                assert image_exists_in_registry("my-image") is False

    def test_returns_none_on_500(self):
        with patch("helpers.docker_registry.requests.head",
                   return_value=_mock_response(500)):
            with patch("helpers.docker_registry.settings_handler.get_setting",
                       side_effect=lambda k: "localhost:5000" if k == "docker.registryAddress"
                       else ("http" if k == "docker.registryScheme" else None)):
                assert image_exists_in_registry("my-image") is None

    def test_returns_none_on_401(self):
        with patch("helpers.docker_registry.requests.head",
                   return_value=_mock_response(401)):
            with patch("helpers.docker_registry.settings_handler.get_setting",
                       side_effect=lambda k: "localhost:5000" if k == "docker.registryAddress"
                       else ("http" if k == "docker.registryScheme" else None)):
                assert image_exists_in_registry("my-image") is None

    def test_returns_none_on_connection_error(self):
        with patch("helpers.docker_registry.requests.head",
                   side_effect=requests.ConnectionError("boom")):
            with patch("helpers.docker_registry.settings_handler.get_setting",
                       side_effect=lambda k: "localhost:5000" if k == "docker.registryAddress"
                       else ("http" if k == "docker.registryScheme" else None)):
                assert image_exists_in_registry("my-image") is None

    def test_returns_none_on_timeout(self):
        with patch("helpers.docker_registry.requests.head",
                   side_effect=requests.Timeout("slow")):
            with patch("helpers.docker_registry.settings_handler.get_setting",
                       side_effect=lambda k: "localhost:5000" if k == "docker.registryAddress"
                       else ("http" if k == "docker.registryScheme" else None)):
                assert image_exists_in_registry("my-image") is None

    def test_returns_none_on_empty_name(self):
        assert image_exists_in_registry("") is None
        assert image_exists_in_registry(None) is None

    def test_returns_none_on_invalid_name(self):
        # Contains characters that are not allowed — must not hit the network
        with patch("helpers.docker_registry.requests.head") as mock_head:
            assert image_exists_in_registry("../etc/passwd") is None
            assert image_exists_in_registry("Has Capitals") is None
            assert image_exists_in_registry("has spaces") is None
            assert mock_head.call_count == 0

    def test_returns_none_when_registry_not_configured(self):
        with patch("helpers.docker_registry.requests.head") as mock_head:
            with patch("helpers.docker_registry.settings_handler.get_setting",
                       return_value=""):
                assert image_exists_in_registry("my-image") is None
            assert mock_head.call_count == 0

    def test_uses_https_when_scheme_is_https(self):
        with patch("helpers.docker_registry.requests.head",
                   return_value=_mock_response(200)) as mock_head:
            with patch("helpers.docker_registry.settings_handler.get_setting",
                       side_effect=lambda k: "registry.example.com" if k == "docker.registryAddress"
                       else ("https" if k == "docker.registryScheme" else None)):
                image_exists_in_registry("my-image")
        url = mock_head.call_args.args[0]
        assert url.startswith("https://registry.example.com/")

    def test_defaults_to_http_when_scheme_missing(self):
        with patch("helpers.docker_registry.requests.head",
                   return_value=_mock_response(200)) as mock_head:
            with patch("helpers.docker_registry.settings_handler.get_setting",
                       side_effect=lambda k: "localhost:5000" if k == "docker.registryAddress"
                       else None):
                image_exists_in_registry("my-image")
        url = mock_head.call_args.args[0]
        assert url.startswith("http://")
