from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .models import ExportRecord, FunctionInfo, ImportRecord, ModuleInfo, Position, Range, SymbolRecord
from .paths import is_generated_like, is_migration_path, is_test_path, relpath
from .suppressions import parse_suppressions

ROUTE_DECORATORS = {"get", "post", "put", "patch", "delete", "websocket", "route"}
TASK_DECORATORS = {"task", "shared_task"}
CLI_DECORATORS = {"command", "group"}
MODEL_DECORATORS = {"dataclass", "define", "frozen"}


def index_file(path: Path, root: Path, module: str, source_root: str, is_init: bool) -> ModuleInfo:
    relative = relpath(path, root)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    info = ModuleInfo(
        path=relative,
        module=module,
        source_root=source_root,
        is_package_init=is_init,
        is_test=is_test_path(relative),
        is_migration=is_migration_path(relative),
        is_generated=is_generated_like(relative, text),
        line_count=len(lines),
        suppressions=parse_suppressions(relative, lines),
    )
    try:
        tree = ast.parse(text, filename=relative)
    except SyntaxError as exc:
        info.parse_error = exc.msg
        info.parse_error_line = exc.lineno or 1
        info.parse_error_column = (exc.offset or 1)
        info.parse_error_end_line = exc.end_lineno or exc.lineno or 1
        info.parse_error_end_column = exc.end_offset or exc.offset or 1
        return info
    visitor = IndexVisitor(info)
    visitor.visit(tree)
    for symbol in info.symbols:
        if symbol.name in info.exports:
            symbol.exported = True
            symbol.public_api = True
            symbol.public_api_confidence = "high"
    return info


class IndexVisitor(ast.NodeVisitor):
    def __init__(self, info: ModuleInfo) -> None:
        self.info = info
        self.scope_depth = 0
        self.type_checking_depth = 0
        self.import_error_guard_depth = 0

    def visit_If(self, node: ast.If) -> Any:
        is_type_checking = _is_type_checking_test(node.test)
        if is_type_checking:
            self.type_checking_depth += 1
        self.visit(node.test)
        for child in node.body:
            self.visit(child)
        if is_type_checking:
            self.type_checking_depth -= 1
        for child in node.orelse:
            self.visit(child)

    def visit_Try(self, node: ast.Try) -> Any:
        guards_import_error = any(_is_import_error_handler(handler) for handler in node.handlers)
        if guards_import_error:
            self.import_error_guard_depth += 1
        for child in node.body:
            self.visit(child)
        if guards_import_error:
            self.import_error_guard_depth -= 1
        for handler in node.handlers:
            for child in handler.body:
                self.visit(child)
        for child in node.orelse + node.finalbody:
            self.visit(child)

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            name = alias.asname or alias.name.split(".", 1)[0]
            self.info.alias_to_module[name] = alias.name
            self.info.imports.append(
                ImportRecord(
                    importer=self.info.module,
                    path=self.info.path,
                    raw_module=alias.name,
                    imported_symbol=None,
                    alias=alias.asname,
                    level=0,
                    line=node.lineno,
                    column=node.col_offset,
                    kind="import",
                    in_function=self.scope_depth > 0,
                    type_checking=self.type_checking_depth > 0,
                    guarded=self.import_error_guard_depth > 0,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        raw_module = node.module
        for alias in node.names:
            if alias.name == "*":
                imported_symbol = "*"
            else:
                imported_symbol = alias.name
                local_alias = alias.asname or alias.name
                if raw_module:
                    self.info.alias_to_symbol[local_alias] = (raw_module, alias.name)
            self.info.imports.append(
                ImportRecord(
                    importer=self.info.module,
                    path=self.info.path,
                    raw_module=raw_module,
                    imported_symbol=imported_symbol,
                    alias=alias.asname,
                    level=node.level,
                    line=node.lineno,
                    column=node.col_offset,
                    kind="from",
                    in_function=self.scope_depth > 0,
                    type_checking=self.type_checking_depth > 0,
                    guarded=self.import_error_guard_depth > 0,
                )
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._record_function(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._record_function(node, "async-function")

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        if self.scope_depth == 0:
            decorators = [_decorator_name(item) for item in node.decorator_list]
            bases = [_expr_name(item) for item in node.bases]
            framework_managed = any(
                name in {"BaseModel", "TypedDict"} or name.endswith(".Model")
                for name in bases
                if name
            ) or any(name in MODEL_DECORATORS for name in decorators if name)
            self.info.symbols.append(_symbol(node, node.name, "class", bool(decorators), framework_managed, bases))
        self.scope_depth += 1
        self.generic_visit(node)
        self.scope_depth -= 1

    def visit_Assign(self, node: ast.Assign) -> Any:
        if self.scope_depth == 0:
            for target in node.targets:
                self._record_assignment_target(target, node)
            self._record_all_exports(node)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if self.scope_depth == 0:
            self._record_assignment_target(node.target, node)
        if node.annotation:
            self.visit(node.annotation)
        if node.value:
            self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        if self.scope_depth == 0 and isinstance(node.target, ast.Name) and node.target.id == "__all__":
            self._record_all_export_names(_literal_string_sequence(node.value), node.lineno, "__all__-augassign")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> Any:
        if isinstance(node.ctx, ast.Load):
            self.info.name_refs.add(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        base = _expr_name(node.value)
        if base:
            self.info.attribute_refs.append((base, node.attr, node.lineno))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        call_name = _expr_name(node.func)
        if self.scope_depth == 0 and call_name in {"__all__.append", "__all__.extend"} and node.args:
            names = (
                _literal_string_sequence(node.args[0])
                if call_name.endswith(".extend")
                else _literal_string_value(node.args[0])
            )
            self._record_all_export_names(names, node.lineno, "__all__-mutation")
        if call_name in {"importlib.import_module", "__import__"} or call_name.endswith(".import_module"):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                module_name = node.args[0].value
                self.info.imports.append(
                    ImportRecord(
                        importer=self.info.module,
                        path=self.info.path,
                        raw_module=module_name,
                        imported_symbol=None,
                        alias=None,
                        level=0,
                        line=node.lineno,
                        column=node.col_offset,
                        kind="dynamic",
                        in_function=self.scope_depth > 0,
                        type_checking=self.type_checking_depth > 0,
                        guarded=self.import_error_guard_depth > 0,
                        dynamic=True,
                        dynamic_literal=True,
                    )
                )
            else:
                self.info.dynamic_import_hints += 1
                self.info.imports.append(
                    ImportRecord(
                        importer=self.info.module,
                        path=self.info.path,
                        raw_module=None,
                        imported_symbol=None,
                        alias=None,
                        level=0,
                        line=node.lineno,
                        column=node.col_offset,
                        kind="dynamic",
                        in_function=self.scope_depth > 0,
                        type_checking=self.type_checking_depth > 0,
                        guarded=self.import_error_guard_depth > 0,
                        dynamic=True,
                        dynamic_literal=False,
                    )
                )
        if call_name in {"FastAPI", "fastapi.FastAPI"}:
            self.info.framework_hints.add("fastapi")
        if call_name in {"Flask", "flask.Flask"}:
            self.info.framework_hints.add("flask")
        if call_name in {"Celery", "celery.Celery"}:
            self.info.framework_hints.add("celery")
        if call_name in {"Typer", "typer.Typer"}:
            self.info.framework_hints.add("typer")
        self.generic_visit(node)

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
        decorators = [_decorator_name(item) for item in node.decorator_list]
        framework_managed = _is_framework_decorated(decorators)
        if self.scope_depth == 0:
            if self.info.is_package_init and node.name == "__getattr__":
                self.info.dynamic_import_hints += 1
            self.info.symbols.append(_symbol(node, node.name, kind, bool(decorators), framework_managed))
        self.info.functions.append(
            FunctionInfo(
                name=node.name,
                kind=kind,
                line=node.lineno,
                column=node.col_offset + 1,
                end_line=getattr(node, "end_lineno", node.lineno),
                end_column=getattr(node, "end_col_offset", node.col_offset) + 1,
                decorators=[item for item in decorators if item],
                framework_managed=framework_managed,
                ast_node=node,
            )
        )
        self.scope_depth += 1
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in node.args.defaults + node.args.kw_defaults:
            if default is not None:
                self.visit(default)
        for child in node.body:
            self.visit(child)
        self.scope_depth -= 1

    def _record_assignment_target(self, target: ast.AST, node: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self.info.symbols.append(_symbol(node, target.id, "assignment", False, False))
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._record_assignment_target(item, node)

    def _record_all_exports(self, node: ast.Assign) -> None:
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
            return
        self._record_all_export_names(_literal_string_sequence(node.value), node.lineno, "__all__")

    def _record_all_export_names(self, names: set[str], line: int, source: str) -> None:
        for name in sorted(names):
            self.info.exports.add(name)
            self.info.export_records.append(
                ExportRecord(
                    name=name,
                    line=line,
                    source=source,
                    confidence="high",
                    complete=source == "__all__",
                    explicit=True,
                )
            )


def _symbol(
    node: ast.AST,
    name: str,
    kind: str,
    decorated: bool,
    framework_managed: bool,
    bases: list[str] | None = None,
) -> SymbolRecord:
    return SymbolRecord(
        name=name,
        kind=kind,
        line=getattr(node, "lineno", 1),
        column=getattr(node, "col_offset", 0),
        end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
        end_column=getattr(node, "end_col_offset", getattr(node, "col_offset", 0)),
        bases=bases or [],
        decorated=decorated,
        framework_managed=framework_managed,
    )


def _literal_string_sequence(node: ast.AST) -> set[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return {item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)}
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _literal_string_sequence(node.left) | _literal_string_sequence(node.right)
    return set()


def _literal_string_value(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    return set()


def _is_type_checking_test(node: ast.AST) -> bool:
    name = _expr_name(node)
    if name in {"TYPE_CHECKING", "typing.TYPE_CHECKING"}:
        return True
    if isinstance(node, ast.BoolOp):
        return any(_is_type_checking_test(item) for item in node.values)
    return False


def _is_import_error_handler(handler: ast.ExceptHandler) -> bool:
    name = _expr_name(handler.type) if handler.type else ""
    return name in {"ImportError", "ModuleNotFoundError"} or name.endswith(".ImportError")


def _decorator_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _expr_name(node.func)
    return _expr_name(node)


def _expr_name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expr_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _expr_name(node.func)
    if isinstance(node, ast.Subscript):
        return _expr_name(node.value)
    return ""


def _is_framework_decorated(decorators: list[str | None]) -> bool:
    for decorator in decorators:
        if not decorator:
            continue
        tail = decorator.rsplit(".", 1)[-1]
        if tail in ROUTE_DECORATORS | TASK_DECORATORS | CLI_DECORATORS:
            return True
        if decorator in {"pytest.fixture", "click.command", "click.group", "shared_task"}:
            return True
    return False
