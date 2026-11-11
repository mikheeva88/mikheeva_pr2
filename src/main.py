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


def load_test_repo(path):
    """Прочитать файл тестового репозитория (строки вида «A: B C»)."""
    repo = {}
    with open(path, encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            if ":" not in line:
                raise RepositoryError(f"неверная строка в {path}: {line}")
            name, _, dependencies = line.partition(":")
            repo[name.strip()] = dependencies.split()
    return repo


def make_dependency_getter(config):
    """Вернуть функцию, которая по имени пакета выдаёт его зависимости."""
    package_name = config["package_name"]
    repo_url = config["repo_url"]
    if not config["test_mode"]:
        return lambda name: list(get_direct_dependencies(repo_url, name))
    repo = load_test_repo(repo_url)
    if package_name not in repo:
        raise RepositoryError(
            f"пакет {package_name} не найден в тестовом репозитории"
        )
    return lambda name: repo.get(name, [])


def bfs_level(level, depth, graph, get_dependencies, max_depth):
    """Обработать один уровень BFS и рекурсивно перейти к следующему."""
    if not level or depth >= max_depth:
        return
    for package in level:
        graph[package] = get_dependencies(package)
    next_level = []
    for package in level:
        for dependency in graph[package]:
            if dependency not in graph and dependency not in next_level:
                next_level.append(dependency)
    bfs_level(next_level, depth + 1, graph, get_dependencies, max_depth)


def build_graph(package_name, get_dependencies, max_depth):
    """Построить граф зависимостей «пакет -> список зависимостей»."""
    graph = {}
    bfs_level([package_name], 0, graph, get_dependencies, max_depth)
    return graph


def print_graph(graph):
    """Вывести граф: для каждого пакета — список его зависимостей."""
    print("Граф зависимостей:")
    for package, dependencies in graph.items():
        print(f"  {package} -> {', '.join(dependencies) or '-'}")


def main():
    """Точка входа: загрузить конфигурацию и вывести граф зависимостей."""
    args = sys.argv[1:]
    path = args[0] if args else DEFAULT_CONFIG
    try:
        config = load_config(path)
        get_dependencies = make_dependency_getter(config)
        graph = build_graph(
            config["package_name"], get_dependencies, config["max_depth"]
        )
    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}")
        return 1
    except RepositoryError as error:
        print(f"Ошибка репозитория: {error}")
        return 1
    print_graph(graph)
    return 0


if __name__ == "__main__":
    sys.exit(main())
