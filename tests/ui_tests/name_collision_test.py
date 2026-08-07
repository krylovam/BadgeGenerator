"""Регрессионный тест: в классах UI не должно быть конфликтов
«метод vs атрибут» (self.<имя> = ... перекрывает метод <имя>()).

Именно такой конфликт (_preview_scale) ломал открытие мастера шаблона:
клик по кнопке «Настроить шаблон…» молча ничего не делал.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHECKED_FILES = sorted((ROOT / "design").glob("*.py")) + \
                sorted((ROOT / "badge_generator").glob("*.py")) + \
                sorted((ROOT / "detector").glob("*.py"))


def _class_conflicts(tree: ast.AST) -> list:
    problems = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
        attrs = set()
        for sub in ast.walk(node):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for st in ast.walk(sub):
                    if isinstance(st, ast.Assign):
                        for t in st.targets:
                            if (isinstance(t, ast.Attribute)
                                    and isinstance(t.value, ast.Name)
                                    and t.value.id == "self"):
                                attrs.add(t.attr)
        clash = methods & attrs
        if clash:
            problems.append((node.name, sorted(clash)))
    return problems


def test_no_method_attribute_name_collisions() -> None:
    all_problems = []
    for f in CHECKED_FILES:
        if f.name.startswith("ui_"):
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for cls, clash in _class_conflicts(tree):
            all_problems.append(f"{f.name}.{cls}: {clash}")
    assert not all_problems, \
        "Конфликты имя-метода/атрибута (self.X = ... перекрывает def X()):\n" + \
        "\n".join(all_problems)
