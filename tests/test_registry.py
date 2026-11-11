"""Тесты получения прямых зависимостей из npm-репозитория (Этап 2)."""

import io
import json
import unittest
import urllib.error
from unittest import mock

from src.main import RepositoryError, get_direct_dependencies

REGISTRY = "https://registry.npmjs.org"
URLOPEN = "src.main.urllib.request.urlopen"


def fake_response(data):
    """Сделать поддельный ответ сервера с JSON-данными."""
    return io.BytesIO(json.dumps(data).encode("utf-8"))


class TestRegistry(unittest.TestCase):
    """Проверки получения зависимостей без обращения к интернету."""

    def test_dependencies(self):
        """Зависимости берутся из поля dependencies."""
        data = {"name": "a", "dependencies": {"b": "^1.0.0", "c": "2.0.0"}}
        with mock.patch(URLOPEN, return_value=fake_response(data)) as urlopen:
            result = get_direct_dependencies(REGISTRY, "a")
        self.assertEqual(result, {"b": "^1.0.0", "c": "2.0.0"})
        url = urlopen.call_args[0][0]
        self.assertEqual(url, "https://registry.npmjs.org/a/latest")

    def test_no_dependencies(self):
        """У пакета нет поля dependencies."""
        data = {"name": "a"}
        with mock.patch(URLOPEN, return_value=fake_response(data)):
            self.assertEqual(get_direct_dependencies(REGISTRY, "a"), {})

    def test_package_not_found(self):
        """Сервер ответил 404 — пакета не существует."""
        error = urllib.error.HTTPError(REGISTRY, 404, "Not Found", None, None)
        with mock.patch(URLOPEN, side_effect=error):
            with self.assertRaises(RepositoryError):
                get_direct_dependencies(REGISTRY, "no-such-package")

    def test_no_connection(self):
        """Нет связи с сервером."""
        error = urllib.error.URLError("timed out")
        with mock.patch(URLOPEN, side_effect=error):
            with self.assertRaises(RepositoryError):
                get_direct_dependencies(REGISTRY, "a")

    def test_not_json(self):
        """Сервер вернул не JSON."""
        response = io.BytesIO(b"<html>error</html>")
        with mock.patch(URLOPEN, return_value=response):
            with self.assertRaises(RepositoryError):
                get_direct_dependencies(REGISTRY, "a")


if __name__ == "__main__":
    unittest.main()
