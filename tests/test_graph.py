"""Тесты построения графа зависимостей (Этап 3)."""

import os
import tempfile
import unittest

from src.main import RepositoryError, build_graph, load_test_repo

REPOS = os.path.join(os.path.dirname(__file__), "repos")


def graph_from_file(name, package, max_depth):
    """Построить граф по файлу тестового репозитория из папки repos."""
    repo = load_test_repo(os.path.join(REPOS, name))
    return build_graph(package, lambda p: repo.get(p, []), max_depth)


class TestGraph(unittest.TestCase):
    """Проверки BFS, глубины, циклов и тестового режима."""

    def test_load_test_repo(self):
        """Файл тестового репозитория читается в словарь."""
        repo = load_test_repo(os.path.join(REPOS, "simple.txt"))
        self.assertEqual(repo["A"], ["B", "C"])
        self.assertEqual(repo["D"], [])

    def test_bad_line(self):
        """Строка без двоеточия — ошибка формата."""
        file = tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        )
        file.write("A B C\n")
        file.close()
        with self.assertRaises(RepositoryError):
            load_test_repo(file.name)
        os.remove(file.name)

    def test_transitive(self):
        """В граф попадают зависимости зависимостей, D — один раз."""
        graph = graph_from_file("simple.txt", "A", 10)
        self.assertEqual(list(graph), ["A", "B", "C", "D"])

    def test_cycle(self):
        """Цикл A -> B -> C -> A не приводит к зацикливанию."""
        graph = graph_from_file("cycle.txt", "A", 10)
        self.assertEqual(graph, {"A": ["B"], "B": ["C"], "C": ["A"]})

    def test_max_depth(self):
        """При max_depth = 2 обрабатываются только A и B."""
        graph = graph_from_file("deep.txt", "A", 2)
        self.assertEqual(graph, {"A": ["B"], "B": ["C"]})

    def test_start_from_middle(self):
        """Анализ можно начать с любого пакета."""
        graph = graph_from_file("deep.txt", "C", 10)
        self.assertEqual(list(graph), ["C", "D", "E"])


if __name__ == "__main__":
    unittest.main()
