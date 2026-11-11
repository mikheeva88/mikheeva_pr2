"""Инструмент визуализации графа зависимостей npm-пакетов."""

import csv
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_CONFIG = "config.csv"
MIN_DEPTH = 1
TIMEOUT = 10
CSV_HEADER = ["key", "value"]
REQUIRED_KEYS = [
    "package_name",
    "repo_url",
    "test_mode",
    "ascii_tree",
    "max_depth",
]


class ConfigError(Exception):
    """Ошибка в конфигурационном файле."""


class RepositoryError(Exception):
    """Ошибка получения данных из репозитория пакетов."""


def read_csv(path):
    """Прочитать CSV-файл и вернуть словарь «параметр -> значение»."""
    if not os.path.isfile(path):
        raise ConfigError(f"файл конфигурации не найден: {path}")
    data = {}
    try:
        with open(path, encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != CSV_HEADER:
                raise ConfigError("первая строка должна быть: key,value")
            for row in reader:
                data[row["key"].strip()] = (row["value"] or "").strip()
    except UnicodeDecodeError:
        raise ConfigError("файл должен быть сохранён в кодировке UTF-8")
    return data


def parse_bool(name, text):
    """Преобразовать строку true/false в логическое значение."""
    if text == "true":
        return True
    if text == "false":
        return False
    raise ConfigError(f"{name} должен быть true или false, получено: '{text}'")


def parse_depth(text):
    """Преобразовать строку в максимальную глубину (целое число >= 1)."""
    try:
        depth = int(text)
    except ValueError:
        raise ConfigError(f"max_depth должен быть целым числом: '{text}'")
    if depth < MIN_DEPTH:
        raise ConfigError(f"max_depth должен быть не меньше {MIN_DEPTH}")
    return depth


def check_repo(repo, test_mode):
    """Проверить URL репозитория или путь к файлу тестового репозитория."""
    if not repo:
        raise ConfigError("repo_url не может быть пустым")
    if test_mode:
        if not os.path.isfile(repo):
            raise ConfigError(f"файл тестового репозитория не найден: {repo}")
    elif not repo.startswith(("http://", "https://")):
        raise ConfigError(f"repo_url должен начинаться с http(s)://: {repo}")


def load_config(path):
    """Прочитать конфигурацию из CSV-файла и проверить все параметры."""
    data = read_csv(path)
    for key in REQUIRED_KEYS:
        if key not in data:
            raise ConfigError(f"не задан параметр {key}")
    if not data["package_name"]:
        raise ConfigError("package_name не может быть пустым")
    test_mode = parse_bool("test_mode", data["test_mode"])
    check_repo(data["repo_url"], test_mode)
    return {
        "package_name": data["package_name"],
        "repo_url": data["repo_url"],
        "test_mode": test_mode,
        "ascii_tree": parse_bool("ascii_tree", data["ascii_tree"]),
        "max_depth": parse_depth(data["max_depth"]),
    }


def fetch_package(repo_url, package_name):
    """Скачать описание последней версии пакета из npm-репозитория."""
    url = f"{repo_url.rstrip('/')}/{package_name}/latest"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RepositoryError(
            f"пакет {package_name} не найден (код ответа {error.code})"
        )
    except urllib.error.URLError as error:
        raise RepositoryError(f"нет связи с репозиторием: {error.reason}")
    except ValueError:
        raise RepositoryError("репозиторий вернул данные не в формате JSON")


def get_direct_dependencies(repo_url, package_name):
    """Вернуть словарь прямых зависимостей пакета «имя -> версия»."""
    package = fetch_package(repo_url, package_name)
    return package.get("dependencies", {})


def print_dependencies(package_name, dependencies):
    """Вывести на экран прямые зависимости пакета."""
    if not dependencies:
        print(f"У пакета {package_name} нет прямых зависимостей")
        return
    print(f"Прямые зависимости пакета {package_name}:")
    for name, version in dependencies.items():
        print(f"  {name} {version}")


def main():
    """Точка входа: загрузить конфигурацию и вывести прямые зависимости."""
    args = sys.argv[1:]
    path = args[0] if args else DEFAULT_CONFIG
    try:
        config = load_config(path)
        if config["test_mode"]:
            raise ConfigError("тестовый режим будет реализован на этапе 3")
        dependencies = get_direct_dependencies(
            config["repo_url"], config["package_name"]
        )
    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}")
        return 1
    except RepositoryError as error:
        print(f"Ошибка репозитория: {error}")
        return 1
    print_dependencies(config["package_name"], dependencies)
    return 0


if __name__ == "__main__":
    sys.exit(main())
