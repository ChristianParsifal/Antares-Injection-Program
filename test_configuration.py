"""Offline configuration tests; never import the GUI or write user configuration."""
import ast
import json
import pathlib
import shutil
import tempfile
import tomllib
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit

ROOT = pathlib.Path(__file__).parent
source = (ROOT / "AntaresIntelligentTool.py").read_text(encoding="utf-8")
tree = ast.parse(source)


def extract_functions(*names):
    return [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]


def extract_profile_methods(*names):
    profile = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ProfileTab")
    return [node for node in profile.body if isinstance(node, ast.FunctionDef) and node.name in names]


# Keep the existing Codex TOML preservation, backup, and malformed-file tests.
selected = extract_functions("toml_quote", "write_codex_config")
with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
    config = pathlib.Path(tmp) / "config.toml"
    original = 'model="old"\nmodel_provider="old"\n[projects."C:/sample"]\ntrust_level="trusted"\n[model_providers.openclawplan]\nname="old"\nbase_url="https://example.invalid"\n[other]\nmodel="keep-nested"\n'
    config.write_text(original, encoding="utf-8")
    scope = {"json": json, "shutil": shutil, "re": __import__("re"), "datetime": datetime, "tomllib": tomllib, "codex_config_path": lambda: config}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "selected-safe-functions", "exec"), scope)
    scope["write_codex_config"]("https://example.invalid/v1", "test-model")
    data = tomllib.loads(config.read_text(encoding="utf-8"))
    assert data["model"] == "test-model"
    assert data["model_provider"] == "api_client"
    assert data["other"]["model"] == "keep-nested"
    assert data["projects"]["C:/sample"]["trust_level"] == "trusted"
    assert "openclawplan" not in data["model_providers"]
    assert data["model_providers"]["api_client"]["wire_api"] == "responses"
    assert data["model_providers"]["api_client"]["name"] == "Antares Client"
    scope["write_codex_config"]("https://example.invalid/v1", "test-model-2")
    assert tomllib.loads(config.read_text(encoding="utf-8"))["model"] == "test-model-2"
    assert len(list(config.parent.glob("*.backup-*"))) == 2
    print("PASS: valid TOML, top-level placement, nested settings preserved, repeat write, backups")
    config.write_text("invalid =[", encoding="utf-8")
    try:
        scope["write_codex_config"]("https://example.invalid/v1", "test")
    except tomllib.TOMLDecodeError:
        assert config.read_text(encoding="utf-8") == "invalid =["
    else:
        raise AssertionError("Invalid TOML was overwritten")
    print("PASS: malformed existing configuration is not overwritten")

# The four built-in routes remain available. Their values are intentionally not
# asserted or rendered: arbitrary user-entered endpoints are now supported.
values = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "_ENDPOINTS" for target in node.targets))
assert len(values) == 4
assert len(set(values)) == 4
print("PASS: four unique built-in routes retained")

# Extract the pure endpoint/model functions without importing Pillow or starting Tk.
network_scope = {
    "json": json,
    "Request": __import__("urllib.request", fromlist=["Request"]).Request,
    "open_api_request": None,
    "urlsplit": urlsplit, "urlunsplit": urlunsplit,
}
network_functions = extract_functions("normalize_endpoint", "fetch_models")
assert len(network_functions) == 2, "main file must expose normalize_endpoint and fetch_models"
exec(compile(ast.Module(body=network_functions, type_ignores=[]), "selected-network-functions", "exec"), network_scope)
normalize_endpoint = network_scope["normalize_endpoint"]
fetch_models = network_scope["fetch_models"]

assert normalize_endpoint("https://relay.example.com", "Codex") == "https://relay.example.com/v1"
assert normalize_endpoint("https://relay.example.com/v1", "Codex") == "https://relay.example.com/v1"
assert normalize_endpoint("https://relay.example.com/v1", "Claude Code") == "https://relay.example.com"
assert normalize_endpoint("https://relay.example.com/v1/", "Claude Code") == "https://relay.example.com"
assert normalize_endpoint("https://relay.example.com/custom/path", "Codex") == "https://relay.example.com/custom/path"
assert normalize_endpoint("https://relay.example.com/custom/v1/chat", "Claude Code") == "https://relay.example.com/custom/v1/chat"
for invalid in ("", "relay.example.com", "ftp://relay.example.com", "https:///missing-host", "https://",
                "https://user:pass@relay.example", "https://relay.example?a=1", "https://relay.example#fragment",
                "https://relay.example:abc", "https://relay.example:99999", "https://relay .example", "https://relay.example/\npath"):
    try:
        normalize_endpoint(invalid, "Codex")
    except (ValueError, TypeError):
        pass
    else:
        raise AssertionError(f"invalid endpoint accepted: {invalid!r}")
print("PASS: endpoint normalization and invalid URL rejection")

class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.payload

captured = {}
def fake_urlopen(request, timeout=0):
    captured["url"] = request.full_url
    captured["auth"] = request.get_header("Authorization")
    captured["timeout"] = timeout
    captured["api_key"] = request.get_header("X-api-key")
    captured["version"] = request.get_header("Anthropic-version")
    return FakeResponse({"data": [{"id": "model-a"}, {"id": "model-b"}, {"name": "ignored"}]})
network_scope["open_api_request"] = fake_urlopen
assert fetch_models("https://relay.example.com/v1/", "secret") == ["model-a", "model-b"]
assert captured == {"url": "https://relay.example.com/v1/models", "auth": "Bearer secret", "timeout": 20, "api_key": None, "version": None}
assert fetch_models("https://relay.example.com/anthropic/v1", "secret", "Claude Code") == ["model-a", "model-b"]
assert captured["url"] == "https://relay.example.com/anthropic/v1/models"
assert captured["api_key"] == "secret" and captured["version"] == "2023-06-01"
assert captured["auth"] is None
fetch_models("https://relay.example/anthropic", "secret", "Claude Code", "bearer")
assert captured["auth"] == "Bearer secret" and captured["api_key"] is None
print("PASS: fetch_models uses mocked requests, selected auth scheme, and correct model routes")

# ProfileTab behavior is tested from extracted methods with a tiny mocked GUI.
profile_methods = extract_profile_methods("set_status", "localize", "endpoint", "validated_endpoint", "save", "load_models", "_load_models")
assert {node.name for node in profile_methods} >= {"localize", "save", "load_models", "_load_models"}
profile_scope = {
    "tk": SimpleNamespace(),
    "threading": SimpleNamespace(Thread=lambda **kwargs: None),
    "set_user_env": lambda name, value: profile_scope["env"].append((name, value)),
    "write_codex_config": lambda base, model: profile_scope["writes"].append((base, model)),
    "user_env": lambda name: "",
    "fetch_models": fetch_models,
    "BASE_URLS": tuple("https://builtin-%d.example/v1" % i for i in range(1, 5)),
    "normalize_endpoint": normalize_endpoint,
    "ConfigurationError": type("ConfigurationError", (Exception,), {}),
    "write_claude_desktop_config": lambda base, key, model: profile_scope["desktop"].append((base, key, model)),
    "desktop": [],
    "write_profile_configuration": lambda *args: profile_scope["writes"].append(args),
}
exec(compile(ast.Module(body=profile_methods, type_ignores=[]), "selected-profile-methods", "exec"), profile_scope)
profile_scope["env"], profile_scope["writes"] = [], []
methods = {node.name: profile_scope[node.name] for node in profile_methods}

class Var:
    def __init__(self, value=""): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value

class Widget:
    def __init__(self): self.values = None
    def configure(self, **kwargs): self.values = kwargs.get("values", self.values)

class App:
    def tr(self, text, **values): return text.format(**values)
    def after(self, delay, callback): callback()

obj = SimpleNamespace(
    app=App(), name="Codex", profile={"key_env": "KEY", "base_env": "BASE", "aliases": ("ALIAS",), "model_env": "MODEL", "default_model": "default"},
    base=Var("https://custom.example/prefix/v1/"), key=Var("secret"), model=Var("custom"), status=Var(), status_spec=("等待检测", {}),
    base_box=Widget(), model_box=Widget(), auth=Var("x-api-key"), saved_configuration=False, configured_at_start=False,
    refresh=lambda: setattr(obj, "refreshed", True), dialog=lambda *args: None,
)
for name, function in methods.items():
    setattr(obj, name, function.__get__(obj, type(obj)))
assert obj.endpoint() == "https://custom.example/prefix/v1"
obj.localize()
assert obj.base.get() == "https://custom.example/prefix/v1/"
assert obj.save(quiet=True) is True
assert profile_scope["writes"] == [("Codex", "https://custom.example/prefix/v1", "secret", "custom", "x-api-key")]
assert obj.saved_configuration
obj.name = "Claude Code"
obj.saved_configuration = False
assert obj.save(quiet=True)
assert profile_scope["writes"][-1] == ("Claude Code", "https://custom.example/prefix", "secret", "custom", "x-api-key")
assert obj.saved_configuration
before = list(profile_scope["writes"])
obj.base.set("not-a-url")
assert not obj.save(quiet=True)
assert profile_scope["writes"] == before
obj.load_models()  # Invalid URL must not start a thread or call the network.
obj.base.set("https://custom.example")
obj._load_models("https://relay.example.com/v1", "secret")
assert obj.model_box.values == ["model-a", "model-b"]
print("PASS: ProfileTab save and model loading use endpoint/key without GUI or user writes")

# Exercise the actual opener construction without opening a socket.
from urllib.request import HTTPRedirectHandler, Request
redirect_scope = {"HTTPRedirectHandler": HTTPRedirectHandler}
redirect_nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in ("NoApiRedirect", "open_api_request")]
exec(compile(ast.Module(body=redirect_nodes, type_ignores=[]), "safe-redirect-handler", "exec"), redirect_scope)
request = Request("https://relay.example/v1/models", headers={"Authorization": "Bearer secret"})
for target in ("https://different.example/models", "http://relay.example/models", "https://relay.example/new"):
    for code in (301, 302, 303, 307, 308):
        assert redirect_scope["NoApiRedirect"]().redirect_request(request, None, code, "redirect", {}, target) is None
handlers_used = []
def fake_builder(handler):
    handlers_used.append(handler)
    return SimpleNamespace(open=lambda req, timeout: (req, timeout))
redirect_scope["build_opener"] = fake_builder
assert redirect_scope["open_api_request"](request, 20) == (request, 20)
assert isinstance(handlers_used[0], redirect_scope["NoApiRedirect"])
print("PASS: authenticated API requests disable redirects so credentials cannot be forwarded")
print("All offline tests passed; no original application imported or executed.")
