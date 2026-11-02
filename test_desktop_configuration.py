"""Offline Windows policy tests. All registry access is replaced with an in-memory fake."""
import ast
import json
import os
import pathlib
import sys
import tempfile
import types
from datetime import datetime
from unittest.mock import patch
from urllib.parse import urlsplit, urlunsplit

ROOT = pathlib.Path(__file__).parent
source = ast.parse((ROOT / "AntaresIntelligentTool.py").read_text(encoding="utf-8"))
names = {"ConfigurationError", "normalize_endpoint", "claude_desktop_values", "read_claude_policy", "write_claude_desktop_config", "codex_config_path", "restore_registry_values", "write_profile_configuration", "configuration_matches", "toml_quote", "write_codex_config"}
nodes = [node for node in source.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]


class Handle:
    def __init__(self, values): self.values = values
    def __enter__(self): return self
    def __exit__(self, *args): pass


class Registry(types.ModuleType):
    HKEY_LOCAL_MACHINE = "machine"
    HKEY_CURRENT_USER = "user"
    KEY_READ, KEY_SET_VALUE, KEY_WOW64_64KEY = 1, 2, 256
    REG_SZ, REG_EXPAND_SZ, REG_DWORD = 1, 2, 4

    def __init__(self):
        super().__init__("winreg")
        self.hives = {"machine": {}, "user": {}}
        self.fail_once = None
        self.writes = 0
        self.env = {}

    def OpenKey(self, hive, path, reserved, access):
        assert path in (r"SOFTWARE\Policies\Claude", "Environment")
        return Handle(self.env if path == "Environment" else self.hives[hive])

    CreateKeyEx = OpenKey

    def QueryValueEx(self, handle, name):
        if name not in handle.values: raise FileNotFoundError(name)
        return handle.values[name]

    def QueryInfoKey(self, handle): return (0, len(handle.values), 0)
    def EnumValue(self, handle, i):
        name, (value, kind) = list(handle.values.items())[i]
        return name, value, kind

    def SetValueEx(self, handle, name, reserved, kind, value):
        if name == self.fail_once:
            self.fail_once = None
            raise OSError("simulated registry write failure")
        self.writes += 1
        handle.values[name] = (value, kind)

    def DeleteValue(self, handle, name):
        if name not in handle.values: raise FileNotFoundError(name)
        del handle.values[name]


registry = Registry()
with tempfile.TemporaryDirectory(dir=ROOT) as tmp, patch.dict(sys.modules, winreg=registry):
    scope = {"json": json, "Path": pathlib.Path, "os": types.SimpleNamespace(name="nt", environ={}),
             "datetime": datetime, "urlsplit": urlsplit, "urlunsplit": urlunsplit,
             "RUNTIME": pathlib.Path(tmp) / "runtime"}
    import re, shutil, tomllib
    scope.update(re=re, shutil=shutil, tomllib=tomllib)
    scope["PROFILES"] = next(ast.literal_eval(node.value) for node in source.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "PROFILES" for target in node.targets))
    scope["user_env"] = lambda name: registry.env.get(name, ("", 1))[0]
    def set_fake_env(name, value):
        registry.SetValueEx(Handle(registry.env), name, 0, registry.REG_SZ, value)
        scope["os"].environ[name] = value
    scope["set_user_env"] = set_fake_env
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "desktop-safe-functions", "exec"), scope)
    write = scope["write_claude_desktop_config"]
    conflict = scope["ConfigurationError"]
    registry.hives["user"] = {"unrelated": ("keep", registry.REG_SZ), "inferenceGatewayApiKey": ("old-key", registry.REG_SZ)}
    write("https://relay.example/anthropic/v1", "test-key", "custom-model")
    values = registry.hives["user"]
    assert values["unrelated"] == ("keep", registry.REG_SZ)
    assert values["inferenceProvider"] == ("gateway", registry.REG_SZ)
    assert values["inferenceGatewayBaseUrl"] == ("https://relay.example/anthropic", registry.REG_SZ)
    assert values["inferenceGatewayApiKey"] == ("test-key", registry.REG_SZ)
    assert values["inferenceCredentialKind"] == ("static", registry.REG_SZ)
    assert json.loads(values["inferenceModels"][0]) == ["custom-model"]
    backup = next((pathlib.Path(tmp) / "backups").glob("*.reg")).read_text(encoding="utf-16")
    assert '"inferenceGatewayApiKey"="old-key"' in backup
    assert '"inferenceProvider"=-' in backup
    assert "test-key" not in backup and "unrelated" not in backup
    print("PASS: desktop gateway policy, model encoding, unrelated values preserved, recovery backup")

    for kind in (registry.REG_SZ, registry.REG_EXPAND_SZ, registry.REG_DWORD):
        registry.hives["machine"] = {"machine-policy": ("managed", kind)}
        before = dict(values)
        try: write("https://relay.example", "other-key", "model")
        except conflict: pass
        else: raise AssertionError("machine policy conflict ignored")
        assert registry.hives["user"] == before
    registry.hives["machine"] = {}
    print("PASS: machine policy precedence blocks ineffective user writes")

    for name in ("bootstrapUrl", "inferenceGatewayOidc", "inferenceIdpOidc", "inferenceCredentialHelper"):
        registry.hives["user"][name] = ("configured", registry.REG_SZ)
        before = dict(registry.hives["user"])
        try: write("https://relay.example", "other-key", "model")
        except conflict: pass
        else: raise AssertionError("credential conflict ignored")
        assert registry.hives["user"] == before
        del registry.hives["user"][name]
    print("PASS: bootstrap and dynamic credential conflicts do not modify policy")

    before = dict(registry.hives["user"])
    registry.fail_once = "inferenceGatewayApiKey"
    try: write("https://new-relay.example", "new-key", "new-model")
    except OSError: pass
    else: raise AssertionError("write failure ignored")
    assert registry.hives["user"] == before
    print("PASS: interrupted policy writes restore original values")

    scope["os"].environ["CODEX_HOME"] = tmp
    assert scope["codex_config_path"]() == pathlib.Path(tmp) / "config.toml"
    print("PASS: Codex honors CODEX_HOME")

    save = scope["write_profile_configuration"]
    matches = scope["configuration_matches"]
    registry.env["ANTHROPIC_AUTH_TOKEN"] = ("old-token", registry.REG_SZ)
    save("Claude Code", "https://relay.example", "new-key", "custom-model", "x-api-key")
    assert registry.env["ANTHROPIC_AUTH_TOKEN"][0] == ""
    assert registry.env["ANTHROPIC_API_KEY"][0] == "new-key"
    assert registry.hives["user"]["inferenceGatewayAuthScheme"][0] == "x-api-key"
    assert matches("Claude Code", "https://relay.example", "new-key", "custom-model", "x-api-key")
    save("Claude Code", "https://relay.example", "bearer-key", "custom-model", "bearer")
    assert registry.env["ANTHROPIC_API_KEY"][0] == ""
    assert registry.env["ANTHROPIC_AUTH_TOKEN"][0] == "bearer-key"
    assert registry.hives["user"]["inferenceGatewayAuthScheme"][0] == "bearer"
    assert matches("Claude Code", "https://relay.example", "bearer-key", "custom-model", "bearer")
    print("PASS: desktop and CLI auth agree; stale credentials cleared in both directions")

    policy_before = dict(registry.hives["user"])
    env_before = dict(registry.env)
    process_before = dict(scope["os"].environ)
    registry.fail_once = "ANTHROPIC_BASE_URL"
    try: save("Claude Code", "https://new.example", "failed-key", "failed-model", "x-api-key")
    except OSError: pass
    else: raise AssertionError("partial environment failure ignored")
    assert registry.hives["user"] == policy_before
    assert registry.env == env_before
    assert scope["os"].environ == process_before
    print("PASS: CLI environment failure rolls back desktop policies and all environment changes")

    save("Codex", "https://codex.example/v1", "codex-key", "codex-model")
    config = pathlib.Path(tmp) / "config.toml"
    assert matches("Codex", "https://codex.example/v1", "codex-key", "codex-model")
    config_before = config.read_bytes()
    env_before = dict(registry.env)
    process_before = dict(scope["os"].environ)
    registry.fail_once = "OPENAI_BASE_URL"
    try: save("Codex", "https://failed.example/v1", "failed-key", "failed-model")
    except OSError: pass
    else: raise AssertionError("Codex environment failure ignored")
    assert config.read_bytes() == config_before
    assert registry.env == env_before
    assert scope["os"].environ == process_before
    print("PASS: Codex environment failure restores TOML and previous credentials")

    del registry.hives["user"]["inferenceProvider"]
    assert not matches("Claude Code", "https://relay.example", "bearer-key", "custom-model", "bearer")
    registry.env["CLAUDE_CODE_USE_BEDROCK"] = ("1", registry.REG_SZ)
    env_before = dict(registry.env)
    try: save("Claude Code", "https://relay.example", "new-key", "custom-model")
    except conflict: pass
    else: raise AssertionError("Conflicting provider flag ignored")
    assert registry.env == env_before
    print("PASS: missing desktop config is not configured; other provider conflicts rejected")

print("All desktop tests passed; no real registry or user configuration changed.")
