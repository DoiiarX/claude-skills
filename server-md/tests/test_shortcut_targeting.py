import argparse
import contextlib
import io
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "server-md"), run_name="server_md_test")
shortcut_execution_plan = MODULE["shortcut_execution_plan"]
cmd_shortcut_run = MODULE["cmd_shortcut_run"]
mark_remote_local_server = MODULE["mark_remote_local_server"]


def sidecar(local_server=None):
    execution = {"default_mode": "render"}
    if local_server:
        execution["local_server"] = local_server
    return {
        "execution": execution,
        "servers": {
            "prod": {
                "aliases": ["production"],
                "tailnet_ip": "100.64.0.10",
                "public_host": "prod.example.com",
                "users": ["deploy"],
                "identity": "/keys/prod.pem",
            }
        },
    }


class ShortcutTargetingTests(unittest.TestCase):
    def test_hosted_shortcut_uses_ssh_for_remote_target(self):
        with patch.dict(shortcut_execution_plan.__globals__, {"server_matches_local_machine": lambda *_: False}):
            plan = shortcut_execution_plan(
                sidecar(),
                {"host": "prod", "transport": "auto"},
                "systemctl status example-app --no-pager",
                "tailnet",
            )

        self.assertEqual(plan["transport"], "ssh")
        self.assertEqual(plan["target"], "prod")
        self.assertEqual(plan["argv"][:5], ["ssh", "-i", "/keys/prod.pem", "deploy@100.64.0.10", "bash -lc 'systemctl status example-app --no-pager'"])

    def test_hosted_shortcut_runs_locally_on_target_sidecar(self):
        plan = shortcut_execution_plan(
            sidecar(local_server="prod"),
            {"host": "production", "transport": "auto"},
            "curl -fsSI http://127.0.0.1:8080/",
        )

        self.assertEqual(plan["transport"], "local")
        self.assertEqual(plan["target"], "prod")
        self.assertIsNone(plan["argv"])

    def test_legacy_explicit_ssh_is_not_wrapped_twice(self):
        plan = shortcut_execution_plan(
            sidecar(),
            {"host": "prod", "transport": "auto"},
            "ssh deploy@prod.example.com systemctl status example-app",
        )

        self.assertEqual(plan["transport"], "local")
        self.assertTrue(plan["legacy_explicit_transport"])
        self.assertIsNone(plan["argv"])

    def test_transport_local_overrides_host_targeting(self):
        plan = shortcut_execution_plan(
            sidecar(),
            {"host": "prod", "transport": "local"},
            "curl -fsSI https://prod.example.com/healthz",
        )

        self.assertEqual(plan["transport"], "local")
        self.assertFalse(plan["legacy_explicit_transport"])

    def test_unknown_host_is_rejected(self):
        with self.assertRaisesRegex(SystemExit, "not registered"):
            shortcut_execution_plan(
                sidecar(),
                {"host": "missing", "transport": "auto"},
                "hostname",
            )

    def test_shortcut_run_executes_remote_plan_without_shell(self):
        data = sidecar()
        data["shortcuts"] = {
            "status": {
                "app": {
                    "host": "prod",
                    "command": "systemctl status example-app --no-pager",
                    "transport": "auto",
                    "risk": "read-only",
                    "execute_mode": "auto",
                }
            }
        }
        with tempfile.TemporaryDirectory() as temp:
            sidecar_path = Path(temp) / "server-md.json"
            log_path = Path(temp) / "ops.jsonl"
            sidecar_path.write_text(json.dumps(data), encoding="utf-8")
            args = argparse.Namespace(
                sidecar=str(sidecar_path),
                category="status",
                name="app",
                prefer="tailnet",
                execute_mode=None,
                confirm_code=None,
                log=str(log_path),
                timeout=10,
                output_limit=4000,
                arg=None,
                raw=True,
                detail=False,
                json=True,
            )
            completed = SimpleNamespace(returncode=0, stdout="active\n", stderr="")
            globals_dict = cmd_shortcut_run.__globals__
            with (
                patch.dict(globals_dict, {"server_matches_local_machine": lambda *_: False}),
                patch.object(globals_dict["subprocess"], "run", return_value=completed) as run_mock,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                cmd_shortcut_run(args)

        executed = run_mock.call_args.args[0]
        self.assertIsInstance(executed, list)
        self.assertEqual(executed[0], "ssh")
        self.assertFalse(run_mock.call_args.kwargs["shell"])

    def test_sync_marks_target_sidecar_as_local_server(self):
        data = {"execution": {}, "servers": {}, "resources": {}, "shortcuts": {}}
        report = {"updated": []}

        mark_remote_local_server(data, "prod", report)

        self.assertEqual(data["execution"]["local_server"], "prod")
        self.assertIn("execution:local_server", report["updated"])


if __name__ == "__main__":
    unittest.main()
