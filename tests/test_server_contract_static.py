import ast
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _decorated_routes(path: Path, decorator_object: str) -> set[tuple[str, str]]:
    tree = _parse(path)
    routes: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute):
                continue
            if not isinstance(func.value, ast.Name):
                continue
            if func.value.id != decorator_object:
                continue
            if func.attr not in {"get", "post", "put", "delete", "websocket", "head"}:
                continue
            if not decorator.args:
                continue
            path_literal = _literal_string(decorator.args[0])
            if path_literal is None:
                continue
            routes.add((func.attr.upper(), path_literal))
    return routes


class ServerBoundaryContractTest(unittest.TestCase):
    def test_runtime_entrypoints_stay_at_server_repo_root(self) -> None:
        for name in ("main.py", "config.py", "requirements.txt", "run.bat", "run.sh"):
            with self.subTest(name=name):
                self.assertTrue((REPO_ROOT / name).is_file(), name)

        for script in ("run.bat", "run.sh"):
            text = (REPO_ROOT / script).read_text(encoding="utf-8", errors="replace")
            self.assertIn("uvicorn main:app", text)
            self.assertNotIn("server.main:app", text)

    def test_tracked_server_repo_does_not_include_nested_server_copy(self) -> None:
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={REPO_ROOT.as_posix()}",
                "ls-files",
                "server",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual("", result.stdout.strip())

    def test_nested_server_copy_is_marked_ignored(self) -> None:
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={REPO_ROOT.as_posix()}",
                "check-ignore",
                "server/main.py",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_device_and_monitor_api_contract_paths_exist(self) -> None:
        app_routes = _decorated_routes(REPO_ROOT / "main.py", "app")
        monitor_routes = _decorated_routes(REPO_ROOT / "monitor_api.py", "router")

        expected_app_routes = {
            ("GET", "/health"),
            ("POST", "/api/frame"),
            ("POST", "/api/imu"),
            ("POST", "/api/gps"),
            ("POST", "/api/asr"),
            ("GET", "/audio/latest"),
            ("GET", "/api/status"),
            ("POST", "/api/status"),
            ("GET", "/api/family/location"),
            ("GET", "/api/family/status"),
            ("POST", "/api/family/emergency"),
            ("WEBSOCKET", "/ws/viewer"),
            ("WEBSOCKET", "/ws_ui"),
        }
        expected_monitor_routes = {
            ("GET", "/api/monitor/state"),
            ("GET", "/api/monitor/events"),
            ("GET", "/api/monitor/frame"),
            ("GET", "/api/monitor/health"),
            ("GET", "/api/monitor/latency"),
        }

        self.assertTrue(expected_app_routes <= app_routes)
        self.assertTrue(expected_monitor_routes <= monitor_routes)

    def test_device_token_guard_covers_mutating_device_paths(self) -> None:
        tree = _parse(REPO_ROOT / "main.py")
        protected_paths: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "_DEVICE_TOKEN_PROTECTED_PATHS"
                for target in node.targets
            ):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            if not isinstance(call.func, ast.Name) or call.func.id != "frozenset":
                continue
            if not call.args or not isinstance(call.args[0], ast.Set):
                continue
            for elt in call.args[0].elts:
                literal = _literal_string(elt)
                if literal is not None:
                    protected_paths.add(literal)

        expected = {
            "/api/gemini",
            "/api/asr",
            "/api/imu",
            "/api/gps",
            "/api/frame",
            "/api/family/emergency",
        }
        self.assertEqual(expected, protected_paths)


if __name__ == "__main__":
    unittest.main()
