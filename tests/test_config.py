"""Тесты обработки ошибок конфигурации (Этап 1)."""

import os
import tempfile
import unittest

from src.main import ConfigError, load_config

GOOD_CONFIG = {
    "package_name": "express",
    "repo_url": "https://registry.npmjs.org",
    "test_mode": "false",
    "ascii_tree": "true",
    "max_depth": "3",
}


def write_config(params):
    """Записать параметры во временный CSV-файл и вернуть путь к нему."""
    file = tempfile.NamedTemporaryFile(
        "w", suffix=".csv", delete=False, encoding="utf-8"
    )
    file.write("key,value\n")
    for key, value in params.items():
        file.write(f"{key},{value}\n")
    file.close()
    return file.name


class TestConfig(unittest.TestCase):
    """Проверки загрузки конфигурации."""

    def load_with(self, **changes):
        """Загрузить корректный конфиг, заменив часть параметров."""
        params = dict(GOOD_CONFIG, **changes)
        path = write_config(params)
        try:
            return load_config(path)
        finally:
            os.remove(path)

    def test_good_config(self):
        """Корректный конфиг читается без ошибок."""
        config = self.load_with()
        self.assertEqual(config["package_name"], "express")
        self.assertEqual(config["max_depth"], 3)
        self.assertTrue(config["ascii_tree"])

    def test_file_not_found(self):
        """Нет файла конфигурации."""
        with self.assertRaises(ConfigError):
            load_config("no_such_file.csv")

    def test_wrong_encoding(self):
        """Файл сохранён не в UTF-8 (например, Блокнотом в Windows-1251)."""
        path = write_config(dict(GOOD_CONFIG))
        with open(path, "a", encoding="cp1251") as file:
            file.write("comment,да\n")
        with self.assertRaises(ConfigError):
            load_config(path)
        os.remove(path)

    def test_missing_param(self):
        """Не задан обязательный параметр."""
        params = dict(GOOD_CONFIG)
        del params["max_depth"]
        path = write_config(params)
        with self.assertRaises(ConfigError):
            load_config(path)
        os.remove(path)

    def test_empty_package(self):
        """Пустое имя пакета."""
        with self.assertRaises(ConfigError):
            self.load_with(package_name="")

    def test_bad_url(self):
        """URL без http(s)://."""
        with self.assertRaises(ConfigError):
            self.load_with(repo_url="registry.npmjs.org")

    def test_test_file_not_found(self):
        """Тестовый режим, но файла репозитория нет."""
        with self.assertRaises(ConfigError):
            self.load_with(test_mode="true", repo_url="no_such_repo.txt")

    def test_bad_test_mode(self):
        """test_mode не true/false."""
        with self.assertRaises(ConfigError):
            self.load_with(test_mode="maybe")

    def test_bad_ascii_tree(self):
        """ascii_tree не true/false."""
        with self.assertRaises(ConfigError):
            self.load_with(ascii_tree="yes")

    def test_depth_not_number(self):
        """max_depth не число."""
        with self.assertRaises(ConfigError):
            self.load_with(max_depth="abc")

    def test_depth_too_small(self):
        """max_depth меньше 1."""
        with self.assertRaises(ConfigError):
            self.load_with(max_depth="0")


if __name__ == "__main__":
    unittest.main()
