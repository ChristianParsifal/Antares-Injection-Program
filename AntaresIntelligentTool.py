from __future__ import annotations

import base64
import json
import os
import platform
import shlex
import shutil
import subprocess
import threading
import tkinter as tk
import sys
import zipfile
import re
import webbrowser
import tomllib
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter import font as tkfont
from PIL import Image, ImageDraw, ImageTk
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit, urlunsplit

APP_TITLE = "Antares Intelligent配置工具"
VERSION = "2.1-universal"
LOGO_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets" / "logo.png"
COPYRIGHT_ZH = "上海星溯科技有限公司，保留一切权利"
COPYRIGHT_EN = "Antares,Shanghai · All rights reserved"
TRANSLATIONS = {
    "Antares Intelligent配置工具": "Antares Intelligent Configuration Tool",
    "上海星溯科技有限公司，保留一切权利": "Antares,Shanghai · All rights reserved",
    "语言": "Language",
    "API 接入配置": "API connection settings",
    "检测": "Check",
    "获取模型": "Fetch models",
    "上海星溯科技有限公司，保留一切权利": "Antares,Shanghai · All rights reserved",
    "Designed by Christian Parsifal in China.": "Designed by Christian Parsifal in China.",
    "线路": "Route",
    "认证方式": "Authentication",
    "Claude CLI 已启用其它推理提供商，请先关闭对应环境变量后重试。": "Claude CLI has another inference provider enabled. Disable its environment flag before trying again.",
    "配置写入失败，部分旧设置无法自动恢复。请使用配置备份恢复后重试。": "Configuration failed and some old settings could not be restored. Restore the configuration backup before trying again.",
    "线路 URL 无效": "Invalid route URL",
    "Claude CLI 和桌面第三方网关配置已保存。请完全退出并重新打开 Claude，在登录页选择第三方推理模式。": "Claude CLI and desktop gateway settings saved. Fully quit and reopen Claude, then choose third-party inference on the sign-in screen.",
    "配置已保存。请完全退出并重新打开 Codex 或终端以读取最新配置。": "Configuration saved. Fully quit and reopen Codex or your terminal to apply it.",
    "Claude 桌面端自动配置目前仅支持 Windows。": "Automatic Claude desktop configuration currently requires Windows.",
    "Claude 桌面端存在计算机级策略，用户配置不会生效。请联系管理员调整后重试。": "Machine-level Claude policies override user settings. Ask your administrator to adjust them first.",
    "Claude 桌面端已有引导服务器或动态凭据配置，请先在原配置中取消后重试。": "Claude already has bootstrap or dynamic credentials configured. Remove that configuration before trying again.",
    "Claude 桌面端已有非字符串推理策略，请先在原配置中调整后重试。": "Claude has inference policies with incompatible value types. Adjust the existing configuration first.",
    "Claude 桌面端将使用第三方网关模式，相关设置由用户策略管理。": "Claude desktop will use third-party gateway mode, managed by user policy.",
    "请输入有效的 HTTP(S) API 地址，不要包含账号、密码、查询参数或片段。": "Enter a valid HTTP(S) API URL without credentials, query parameters or fragments.",
    "可直接输入中转站 API 地址；也可从下拉列表选择原有线路。": "Enter a relay API URL, or select an original route from the list.",
    "Codex 需要 Responses API；Claude Code 需要 Anthropic Messages API。": "Codex requires the Responses API; Claude Code requires the Anthropic Messages API.",
    "线路 {number}": "Route {number}",
    "检测": "Check",
    "显示": "Show",
    "模型（可选）": "Model (optional)",
    "获取模型": "Fetch models",
    "保存配置": "Save configuration",
    "保存并安装 {name}": "Save and install {name}",
    "打开 {name} 官方桌面端下载": "Download the official {name} desktop app",
    "Designed by Christian Parsifal in China.": "Designed by Christian Parsifal in China.",
    "等待检测": "Waiting for checks",
    "已安装": "Installed",
    "未检测到": "Not detected",
    "未安装": "Not installed",
    "已配置": "Configured",
    "未配置": "Not configured",
    "配置状态": "Configuration status",
    "已填写": "Complete",
    "未完整填写": "Incomplete",
    "Node.js: {node}  |  npm: {npm}  | {name}: {cli}\n配置状态：{configured}": "Node.js: {node}  |  npm: {npm}  | {name}: {cli}\nConfiguration: {configured}",
    "缺少 API Key": "Missing API Key",
    "请先输入 API Key。": "Please enter your API Key first.",
    "配置完成": "Configuration saved",
    "配置已保存。新打开的终端或客户端会读取最新配置。": "Configuration saved. Restart your terminal or client to apply the changes.",
    "配置失败": "Configuration failed",
    "无法写入本地配置，请检查文件格式与当前用户权限。": "Unable to write the local configuration. Check the file format and your user permissions.",
    "正在获取模型列表……": "Fetching models…",
    "已获取 {count} 个模型": "Fetched {count} models",
    "模型列表获取失败，请检查 API Key 或线路": "Unable to fetch models. Check your API Key or select another route.",
    "确认安装": "Confirm installation",
    "将保存当前配置，并在缺少依赖时解压内置 Node.js/Git，随后通过 npm 联网安装 CLI。是否继续？": "This will save the configuration, extract bundled Node.js/Git if needed, and install the CLI online through npm. Continue?",
    "正在准备依赖并安装 {name} CLI……": "Preparing dependencies and installing {name} CLI…",
    "{name} CLI 安装完成": "{name} CLI installed",
    "安装完成": "Installation complete",
    "安装完成。请重新打开终端后使用客户端。": "Installation complete. Open a new terminal to use the client.",
    "{name} CLI 安装失败": "{name} CLI installation failed",
    "安装失败": "Installation failed",
    "CLI 安装失败，请确认 Node.js/npm 可用后重试。": "CLI installation failed. Make sure Node.js/npm is available, then try again.",
}
# Keep the original routes as optional presets; users can enter any compatible URL.
_ENDPOINTS = (
    "aHR0cHM6Ly9hcGkub3BlbmNsYXdw bGFuLmNvbS92MQ==",
    "aHR0cHM6Ly9hcGktbm9kZTEub3BlbmNsYXdw bGFuLmNvbS92MQ==",
    "aHR0cHM6Ly9hcGktbm9kZTIub3BlbmNsYXdw bGFuLmNvbS92MQ==",
    "aHR0cHM6Ly9hcGktbm9kZTMub3BlbmNsYXdw bGFuLmNvbS92MQ==",
)
# Spaces are removed before decoding so the literal values are not shown in UI.
BASE_URLS = tuple(base64.b64decode(x.replace(" ", "")).decode() for x in _ENDPOINTS)

PROFILES = {
    "Codex": {
        "command": "codex",
        "package": "@openai/codex",
        "key_env": "OPENAI_API_KEY",
        "base_env": "OPENAI_BASE_URL",
        "aliases": ("OPENAI_API_BASE",),
        "model_env": "OPENAI_MODEL",
        "default_model": "gpt-5",
    },
    "Claude Code": {
        "command": "claude",
        "package": "@anthropic-ai/claude-code",
        "key_env": "ANTHROPIC_API_KEY",
        "base_env": "ANTHROPIC_BASE_URL",
        "aliases": (),
        "model_env": "ANTHROPIC_MODEL",
        "default_model": "claude-sonnet-4-5",
    },
}


def run(args: list[str], timeout: int = 60, env: dict[str, str] | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return p.returncode, (p.stdout or p.stderr or "").strip()
    except FileNotFoundError:
        return 127, "未找到命令"
    except subprocess.TimeoutExpired:
        return 124, "命令执行超时"
    except Exception as exc:
        return 1, str(exc)


def which(name: str) -> str | None:
    return shutil.which(name)


def user_env(name: str) -> str:
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                return str(winreg.QueryValueEx(key, name)[0])
        except OSError:
            pass
    return os.environ.get(name, "")


RUNTIME = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "APIClientTool" / "runtime"


def refresh_path() -> None:
    paths = [str(RUNTIME / "node"), str(RUNTIME / "git" / "cmd"), str(RUNTIME / "git" / "bin"), str(RUNTIME / "npm"), str(Path(os.environ.get("APPDATA", str(Path.home()))) / "npm"), r"C:\Program Files\nodejs", r"C:\Program Files\Git\cmd"]
    os.environ["PATH"] = os.pathsep.join(paths + [os.environ.get("PATH", "")])


def append_path(path: Path) -> None:
    current = user_env("Path") if os.name == "nt" else os.environ.get("PATH", "")
    parts = current.split(os.pathsep)
    if str(path).lower() not in [p.lower() for p in parts]:
        set_user_env("Path" if os.name == "nt" else "PATH", os.pathsep.join(parts + [str(path)]))
    refresh_path()


def install_dependencies() -> None:
    refresh_path()
    root = Path(getattr(sys, "_MEIPASS", str(Path(__file__).parent))) / "assets" / "installers"
    if not which("node") or not which("npm.cmd" if os.name == "nt" else "npm"):
        archive = next(root.glob("node-*.zip"), None)
        if archive is None:
            raise RuntimeError("缺少内置 Node.js 安装包")
        target = RUNTIME / "node"
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                parts = Path(info.filename).parts[1:]
                if not parts:
                    continue
                dest = target.joinpath(*parts).resolve()
                if not dest.is_relative_to(target.resolve()):
                    raise RuntimeError("安装包路径无效")
                if info.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as source, dest.open("wb") as out:
                        shutil.copyfileobj(source, out)
        append_path(target)
    if not which("git"):
        installer = next(root.glob("PortableGit*.exe"), None)
        if installer is None:
            raise RuntimeError("缺少内置 Git 安装包")
        target = RUNTIME / "git"
        target.mkdir(parents=True, exist_ok=True)
        code, _ = run([str(installer), "-y", "-o" + str(target)], timeout=300)
        if code != 0:
            raise RuntimeError("Git 依赖解压失败")
        append_path(target / "cmd")
        append_path(target / "bin")
    refresh_path()


def set_user_env(name: str, value: str) -> None:
    if os.name == "nt":
        import winreg
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    else:
        profile = Path.home() / (".zshrc" if os.environ.get("SHELL", "").endswith("zsh") else ".bash_profile")
        marker = "# API client configuration tool"
        lines = profile.read_text(encoding="utf-8", errors="replace").splitlines() if profile.exists() else []
        lines = [line for line in lines if not line.startswith(f"export {name}=")]
        lines += [marker, f"export {name}={shlex.quote(value)}"]
        profile.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[name] = value
    if os.name == "nt":
        import ctypes
        result = ctypes.c_size_t()
        ctypes.windll.user32.SendMessageTimeoutW(65535, 26, 0, "Environment", 2, 2000, ctypes.byref(result))


def codex_config_path() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser() / "config.toml"


class ConfigurationError(Exception):
    """An actionable configuration conflict safe to show without credentials."""


def claude_desktop_values(base_url: str, key: str, model: str, auth_scheme: str = "x-api-key") -> dict[str, str]:
    return {
        "inferenceProvider": "gateway",
        "inferenceGatewayBaseUrl": normalize_endpoint(base_url, "Claude Code"),
        "inferenceGatewayApiKey": key,
        "inferenceGatewayAuthScheme": auth_scheme,
        "inferenceCredentialKind": "static",
        "inferenceModels": json.dumps([model], ensure_ascii=False),
    }


def read_claude_policy(hive) -> dict:
    import winreg
    try:
        with winreg.OpenKey(hive, r"SOFTWARE\Policies\Claude", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as handle:
            return {name: (value, kind) for name, value, kind in
                    (winreg.EnumValue(handle, i) for i in range(winreg.QueryInfoKey(handle)[1]))}
    except FileNotFoundError:
        return {}


def write_claude_desktop_config(base_url: str, key: str, model: str, auth_scheme: str = "x-api-key") -> None:
    """Use the documented Windows user policy; back up touched values for recovery."""
    if os.name != "nt":
        raise ConfigurationError("Claude 桌面端自动配置目前仅支持 Windows。")
    import winreg
    machine = read_claude_policy(winreg.HKEY_LOCAL_MACHINE)
    if any(kind in (winreg.REG_SZ, winreg.REG_EXPAND_SZ, winreg.REG_DWORD) for _, kind in machine.values()):
        raise ConfigurationError("Claude 桌面端存在计算机级策略，用户配置不会生效。请联系管理员调整后重试。")
    existing = read_claude_policy(winreg.HKEY_CURRENT_USER)
    if any(existing.get(name, ("",))[0] for name in
           ("bootstrapUrl", "inferenceGatewayOidc", "inferenceIdpOidc", "inferenceCredentialHelper")):
        raise ConfigurationError("Claude 桌面端已有引导服务器或动态凭据配置，请先在原配置中取消后重试。")
    values = claude_desktop_values(base_url, key, model, auth_scheme)
    # Only values this tool changes are included. Unrelated policies remain intact.
    backup_lines = ["Windows Registry Editor Version 5.00", "", r"[HKEY_CURRENT_USER\SOFTWARE\Policies\Claude]"]
    for name in values:
        previous = existing.get(name)
        if previous is None:
            backup_lines.append(f'"{name}"=-')
        elif previous[1] == winreg.REG_SZ:
            escaped = str(previous[0]).replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
            backup_lines.append(f'"{name}"="{escaped}"')
        else:
            raise ConfigurationError("Claude 桌面端已有非字符串推理策略，请先在原配置中调整后重试。")
    backup_dir = RUNTIME.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / ("claude-desktop-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".reg")
    backup.write_text("\n".join(backup_lines) + "\n", encoding="utf-16")
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Policies\Claude", 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as handle:
        try:
            for name, value in values.items():
                winreg.SetValueEx(handle, name, 0, winreg.REG_SZ, value)
        except OSError:
            try:
                errors = restore_registry_values(r"SOFTWARE\Policies\Claude", {name: existing.get(name) for name in values})
            except OSError:
                errors = list(values)
            if errors:
                raise ConfigurationError("配置写入失败，部分旧设置无法自动恢复。请使用配置备份恢复后重试。") from None
            raise


def restore_registry_values(path: str, snapshot: dict) -> list[str]:
    import winreg
    errors = []
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as handle:
        for name, previous in snapshot.items():
            try:
                if previous is None:
                    try:
                        winreg.DeleteValue(handle, name)
                    except FileNotFoundError:
                        pass
                else:
                    value, kind = previous
                    winreg.SetValueEx(handle, name, 0, kind, value)
            except OSError:
                errors.append(name)
    return errors


def write_profile_configuration(name: str, base: str, key: str, model: str, auth_scheme: str = "x-api-key") -> None:
    """Save desktop and CLI settings together, restoring all targets on failure."""
    profile = PROFILES[name]
    values = {profile["key_env"]: key, profile["base_env"]: base, profile["model_env"]: model}
    values.update({alias: base for alias in profile["aliases"]})
    if name == "Claude Code":
        for flag in ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"):
            if user_env(flag).lower() in ("1", "true"):
                raise ConfigurationError("Claude CLI 已启用其它推理提供商，请先关闭对应环境变量后重试。")
        values["ANTHROPIC_API_KEY"] = key if auth_scheme == "x-api-key" else ""
        values["ANTHROPIC_AUTH_TOKEN"] = key if auth_scheme == "bearer" else ""
    process_before = {env: os.environ.get(env) for env in values}
    env_before = {}
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ) as handle:
                for env in values:
                    try:
                        env_before[env] = winreg.QueryValueEx(handle, env)
                    except FileNotFoundError:
                        env_before[env] = None
        except FileNotFoundError:
            env_before = {env: None for env in values}
    shell_path = Path.home() / (".zshrc" if os.environ.get("SHELL", "").endswith("zsh") else ".bash_profile")
    file_path = codex_config_path() if name == "Codex" else None
    snapshots = {path: path.read_bytes() if path.exists() else None for path in
                 ([file_path] if file_path else []) + ([shell_path] if os.name != "nt" else [])}
    policy_before = {}
    if name == "Claude Code" and os.name == "nt":
        existing = read_claude_policy(winreg.HKEY_CURRENT_USER)
        policy_before = {item: existing.get(item) for item in claude_desktop_values(base, key, model, auth_scheme)}
    desktop_written = False
    env_started = False
    try:
        if name == "Codex":
            write_codex_config(base, model)
        else:
            write_claude_desktop_config(base, key, model, auth_scheme)
        desktop_written = True
        env_started = True
        for env, value in values.items():
            set_user_env(env, value)
    except Exception:
        errors = []
        if desktop_written:
            for path, content in snapshots.items():
                try:
                    if content is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(content)
                except OSError:
                    errors.append("file")
            if policy_before:
                try:
                    errors.extend(restore_registry_values(r"SOFTWARE\Policies\Claude", policy_before))
                except OSError:
                    errors.append("policy")
        if env_started and os.name == "nt":
            try:
                errors.extend(restore_registry_values(r"Environment", env_before))
            except OSError:
                errors.append("environment")
        for env, previous in process_before.items():
            if previous is None:
                os.environ.pop(env, None)
            else:
                os.environ[env] = previous
        if errors:
            raise ConfigurationError("配置写入失败，部分旧设置无法自动恢复。请使用配置备份恢复后重试。") from None
        raise


def configuration_matches(name: str, base: str, key: str, model: str, auth_scheme: str = "x-api-key") -> bool:
    try:
        base = normalize_endpoint(base, name)
        profile = PROFILES[name]
        key_env = "ANTHROPIC_AUTH_TOKEN" if name == "Claude Code" and auth_scheme == "bearer" else profile["key_env"]
        if not key or user_env(key_env) != key or user_env(profile["base_env"]) != base or user_env(profile["model_env"]) != model:
            return False
        if name == "Codex":
            data = tomllib.loads(codex_config_path().read_text(encoding="utf-8-sig"))
            provider = data.get("model_providers", {}).get("api_client", {})
            return (data.get("model_provider") == "api_client" and data.get("model") == model
                    and provider.get("base_url") == base and provider.get("wire_api") == "responses"
                    and provider.get("env_key") == "OPENAI_API_KEY")
        if os.name != "nt":
            return False
        import winreg
        if any(kind in (winreg.REG_SZ, winreg.REG_EXPAND_SZ, winreg.REG_DWORD)
               for _, kind in read_claude_policy(winreg.HKEY_LOCAL_MACHINE).values()):
            return False
        actual = read_claude_policy(winreg.HKEY_CURRENT_USER)
        expected = claude_desktop_values(base, key, model, auth_scheme)
        other_env = "ANTHROPIC_API_KEY" if auth_scheme == "bearer" else "ANTHROPIC_AUTH_TOKEN"
        return not user_env(other_env) and all(actual.get(item) == (value, winreg.REG_SZ) for item, value in expected.items())
    except (OSError, ValueError, KeyError):
        return False


def toml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_codex_config(base_url: str, model: str) -> None:
    path = codex_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8-sig", errors="replace").splitlines() if path.exists() else []
    kept = []
    skip = False
    in_section = False
    for line in existing:
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            in_section = True
            skip = s in ("[model_providers.openclawplan]", "[model_providers.api_client]")
        if not skip and not (not in_section and re.match(r"^(model|model_provider|openai_base_url)\s*=", s)):
            kept.append(line)
    if path.exists():
        shutil.copy2(path, path.with_name("config.toml.backup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")))
    kept = [f"model = {toml_quote(model)}", 'model_provider = "api_client"', ""] + kept + [
        "",
        "[model_providers.api_client]",

        'name = "Antares Client"',
        f"base_url = {toml_quote(base_url)}",
        'env_key = "OPENAI_API_KEY"',
        'wire_api = "responses"',
        "requires_openai_auth = false",
    ]
    content = "\n".join(kept).rstrip() + "\n"
    tomllib.loads(content)
    temporary = path.with_suffix(".toml.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def normalize_endpoint(value: str, profile_name: str) -> str:
    """Accept API base URLs, preserving custom prefixes and API versions."""
    value = value.strip()
    if not value or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value) or "\\" in value:
        raise ValueError("Invalid API URL")
    try:
        parts = urlsplit(value)
        if (parts.scheme.lower() not in ("http", "https") or not parts.hostname
                or parts.username is not None or parts.password is not None
                or "?" in value or "#" in value):
            raise ValueError("Invalid API URL")
        # Accessing port also validates malformed/non-numeric and out-of-range ports.
        parts.port
    except ValueError:
        raise ValueError("Invalid API URL") from None
    path = parts.path.rstrip("/")
    if profile_name == "Codex" and not path:
        path = "/v1"
    elif profile_name == "Claude Code" and path.endswith("/v1"):
        # Anthropic clients append /v1/messages themselves.
        path = path[:-3]
    return urlunsplit((parts.scheme.lower(), parts.netloc, path, "", ""))


class NoApiRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward credentials to a redirect target, including HTTPS downgrades.
        return None


def open_api_request(request, timeout):
    return build_opener(NoApiRedirect()).open(request, timeout=timeout)


def fetch_models(base_url: str, key: str, profile_name: str = "Codex", auth_scheme: str = "x-api-key") -> list[str]:
    base_url = normalize_endpoint(base_url, profile_name)
    headers = {"Authorization": f"Bearer {key}"}
    if profile_name == "Claude Code":
        headers = {"anthropic-version": "2023-06-01"}
        headers["Authorization" if auth_scheme == "bearer" else "x-api-key"] = f"Bearer {key}" if auth_scheme == "bearer" else key
    suffix = "/v1/models" if profile_name == "Claude Code" else "/models"
    req = Request(base_url + suffix, headers=headers)
    with open_api_request(req, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    return [item.get("id", "") for item in data.get("data", []) if isinstance(item, dict) and item.get("id")]


class RoundedCard(tk.Canvas):
    """A borderless, resize-aware rounded surface around native ttk widgets."""

    def __init__(self, parent, background="#f5f5f7", surface="#ffffff", radius=20, padding=24):
        super().__init__(parent, background=background, highlightthickness=0, bd=0)
        self.surface, self.radius, self.padding = surface, radius, padding
        self.content = ttk.Frame(self, style="Card.TFrame")
        self.window = self.create_window(padding, padding, window=self.content, anchor="nw")
        self.bind("<Configure>", self._resize)
        self.content.bind("<Configure>", self._request_height)

    def _request_height(self, event=None):
        height = self.content.winfo_reqheight() + self.padding * 2
        if int(float(self.cget("height"))) != height:
            self.configure(height=height)

    def _resize(self, event):
        self.delete("surface")
        w, h, r = event.width, event.height, self.radius
        points = [r, 0, w-r, 0, w, 0, w, r, w, h-r, w, h,
                  w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0]
        self.create_polygon(points, smooth=True, splinesteps=24, fill=self.surface,
                            outline="", tags="surface")
        self.tag_lower("surface")
        self.itemconfigure(self.window, width=max(1, w - self.padding * 2))


class ProfileTab:
    def __init__(self, app: "App", parent: ttk.Frame, name: str):
        self.app, self.name, self.profile = app, name, PROFILES[name]
        configured = user_env(self.profile["base_env"])
        self.base = tk.StringVar(value=configured or BASE_URLS[0])
        self.busy = False
        self.key = tk.StringVar(value="")
        self.auth = tk.StringVar(value="bearer" if self.name == "Claude Code" and user_env("ANTHROPIC_AUTH_TOKEN") else "x-api-key")
        self.model = tk.StringVar(value=user_env(self.profile["model_env"]) or self.profile["default_model"])
        key_env = "ANTHROPIC_AUTH_TOKEN" if self.name == "Claude Code" and self.auth.get() == "bearer" else self.profile["key_env"]
        self.configured_at_start = configuration_matches(self.name, configured, user_env(key_env), self.model.get(), self.auth.get())
        self.show_key = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="")
        self.status_node = tk.StringVar(value="")
        self.status_config = tk.StringVar(value="")
        self.status_node_ok = False
        self.status_config_ok = False
        self.saved_configuration = False
        self.status_spec = ("等待检测", {})
        self._build(parent)
        self.localize()
        self.refresh()

    def set_status(self, text, **values):
        self.status_spec = (text, values)
        self.status.set(self.app.tr(text, **values))

    def localize(self):
        self.base_box.configure(values=BASE_URLS)
        text, values = self.status_spec
        self.refresh()
        self.set_status(text, **values)

    def dialog(self, method, title, text):
        return getattr(messagebox, method)(self.app.tr(title), self.app.tr(text), parent=self.app)

    def _build(self, parent: ttk.Frame) -> None:
        card = RoundedCard(parent)
        card.pack(fill="both", expand=True, pady=(12, 0))
        box = card.content
        box.columnconfigure(1, weight=1)
        self.app.localized(ttk.Label, box, "API 接入配置", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))
        self.app.localized(ttk.Label, box, "线路", style="Field.TLabel").grid(row=1, column=0, sticky="w", pady=7)
        self.base_box = ttk.Combobox(box, textvariable=self.base, values=BASE_URLS, state="normal")
        self.base_box.grid(row=1, column=1, sticky="ew", pady=7)
        self.check_button = self.app.localized(ttk.Button, box, "检测", command=self.refresh, width=8)
        self.check_button.configure(style="Compact.TButton")
        self.check_button.grid(row=1, column=2, padx=(8, 0), pady=7, sticky="ew")
        ttk.Label(box, text="API Key", style="Field.TLabel").grid(row=2, column=0, sticky="w", pady=7)
        self.key_entry = ttk.Entry(box, textvariable=self.key, show="*")
        self.key_entry.grid(row=2, column=1, sticky="ew", pady=7)
        self.app.localized(ttk.Checkbutton, box, "显示", variable=self.show_key, command=self.toggle_key).grid(row=2, column=2, padx=(8, 0))
        self.app.localized(ttk.Label, box, "模型（可选）", style="Field.TLabel").grid(row=3, column=0, sticky="w", pady=7)
        self.model_box = ttk.Combobox(box, textvariable=self.model, state="normal")
        self.model_box.grid(row=3, column=1, sticky="ew", pady=7)
        self.models_button = self.app.localized(ttk.Button, box, "获取模型", command=self.load_models, width=8)
        self.models_button.configure(style="Compact.TButton")
        self.models_button.grid(row=3, column=2, padx=(8, 0), pady=7, sticky="ew")
        if self.name == "Claude Code":
            self.app.localized(ttk.Label, box, "认证方式", style="Field.TLabel").grid(row=4, column=0, sticky="w", pady=7)
            ttk.Combobox(box, textvariable=self.auth, values=("x-api-key", "bearer"), state="readonly").grid(row=4, column=1, sticky="ew", pady=7)
        hints = ttk.Frame(box, style="Card.TFrame")
        hints.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self.app.localized(ttk.Label, hints, "可直接输入中转站 API 地址；也可从下拉列表选择原有线路。",
                           style="Hint.TLabel", wraplength=700).pack(anchor="w")
        if self.name == "Claude Code":
            self.app.localized(ttk.Label, hints, "Claude 桌面端将使用第三方网关模式，相关设置由用户策略管理。",
                               style="Hint.TLabel", wraplength=700).pack(anchor="w")
        status_surface = RoundedCard(box, background="#ffffff", surface="#f5f5f7", radius=14, padding=16)
        status_surface.content.configure(style="StatusCard.TFrame")
        status_surface.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(20, 2))
        status_card = status_surface.content
        status_card.columnconfigure(0, weight=1)
        ttk.Label(status_card, textvariable=self.status_node, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(status_card, textvariable=self.status_config, style="Status.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.status_node_label = status_card.grid_slaves(row=0, column=0)[0]
        self.status_config_label = status_card.grid_slaves(row=1, column=0)[0]
        ttk.Label(status_card, textvariable=self.status, style="Status.TLabel", wraplength=700).grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.app.localized(ttk.Button, box, "保存配置", style="Primary.TButton", command=self.save).grid(row=7, column=0, columnspan=3, sticky="ew", pady=(18, 6))
        self.app.localized(ttk.Button, box, "保存并安装 {name}", values={"name": self.name}, command=self.install).grid(row=8, column=0, columnspan=3, sticky="ew")
        self.app.localized(ttk.Button, box, "打开 {name} 官方桌面端下载", values={"name": self.name}, command=self.desktop_download).grid(row=9, column=0, columnspan=3, sticky="ew", pady=(6, 0))

    def desktop_download(self):
        url = "https://get.microsoft.com/installer/download/9PLM9XGG6VKS?cid=website_cta_psi" if self.name == "Codex" else "https://claude.ai/download"
        webbrowser.open(url)

    def toggle_key(self):
        self.key_entry.configure(show="" if self.show_key.get() else "*")

    def endpoint(self) -> str:
        return normalize_endpoint(self.base.get(), self.name)

    def validated_endpoint(self) -> str | None:
        try:
            return self.endpoint()
        except ValueError:
            self.dialog("showwarning", "线路 URL 无效", "请输入有效的 HTTP(S) API 地址，不要包含账号、密码、查询参数或片段。")
            return None

    def refresh(self):
        refresh_path()
        node = which("node") is not None
        npm = which("npm.cmd" if os.name == "nt" else "npm") is not None
        cli = which(self.profile["command"]) is not None
        configured = self.saved_configuration or self.configured_at_start
        self.status_node_ok = node and npm and cli
        self.status_config_ok = configured
        install_state = self.app.tr("已安装" if self.status_node_ok else "未安装")
        config_state = self.app.tr("已配置" if self.status_config_ok else "未配置")
        self.status_node.set(f'{self.name} / Node.js / npm: {install_state}')
        self.status_config.set(f'{self.app.tr("配置状态")}: {config_state}')
        self.status.set("")
        self.status_node_label.configure(style="Good.TLabel" if self.status_node_ok else "Warn.TLabel")
        self.status_config_label.configure(style="Good.TLabel" if self.status_config_ok else "Warn.TLabel")

    def save(self, quiet: bool = False) -> bool:
        if not self.key.get().strip():
            self.dialog("showwarning", "缺少 API Key", "请先输入 API Key。")
            return False
        base = self.validated_endpoint()
        if base is None:
            return False
        try:
            model = self.model.get().strip() or self.profile["default_model"]
            write_profile_configuration(self.name, base, self.key.get().strip(), model, self.auth.get())
            self.base.set(base)
            self.saved_configuration = True
            self.configured_at_start = False
            self.refresh()
            if not quiet:
                text = ("Claude CLI 和桌面第三方网关配置已保存。请完全退出并重新打开 Claude，在登录页选择第三方推理模式。"
                        if self.name == "Claude Code" else "配置已保存。请完全退出并重新打开 Codex 或终端以读取最新配置。")
                self.dialog("showinfo", "配置完成", text)
            return True
        except ConfigurationError as exc:
            self.dialog("showerror", "配置失败", str(exc))
            return False
        except Exception:
            self.dialog("showerror", "配置失败", "无法写入本地配置，请检查文件格式与当前用户权限。")
            return False

    def load_models(self):
        if not self.key.get().strip():
            self.dialog("showwarning", "缺少 API Key", "请先输入 API Key。")
            return
        base = self.validated_endpoint()
        if base is None:
            return
        self.set_status("正在获取模型列表……")
        threading.Thread(target=self._load_models, args=(base, self.key.get().strip(), self.auth.get()), daemon=True).start()

    def _load_models(self, endpoint, key, auth_scheme="x-api-key"):
        try:
            models = fetch_models(endpoint, key, self.name, auth_scheme)
            self.app.after(0, lambda: (self.model_box.configure(values=models), self.set_status("已获取 {count} 个模型", count=len(models))))
        except Exception:
            self.app.after(0, lambda: self.set_status("模型列表获取失败，请检查 API Key 或线路"))

    def install(self):
        if self.busy:
            return
        if not self.dialog("askyesno", "确认安装", "将保存当前配置，并在缺少依赖时解压内置 Node.js/Git，随后通过 npm 联网安装 CLI。是否继续？"):
            return
        if not self.save(quiet=True):
            return
        self.busy = True
        self.set_status("正在准备依赖并安装 {name} CLI……", name=self.name)
        threading.Thread(target=self._install, daemon=True).start()

    def _install(self):
        code = 1
        detail = ""
        try:
            self.app.after(0, lambda: self.set_status("正在准备运行环境……"))
            install_dependencies()
            refresh_path()
            npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or shutil.which("npm")
            if not npm:
                raise RuntimeError("npm 不可用")
            prefix = RUNTIME / "npm"
            cache = RUNTIME / "cache"
            prefix.mkdir(parents=True, exist_ok=True)
            cache.mkdir(parents=True, exist_ok=True)
            append_path(prefix)
            env = os.environ.copy()
            env.update(NPM_CONFIG_PREFIX=str(prefix), NPM_CONFIG_CACHE=str(cache), NPM_CONFIG_USERCONFIG=str(RUNTIME / "npmrc"))
            self.app.after(0, lambda: self.set_status("正在安装 {name} CLI……", name=self.name))
            code, detail = run([npm, "install", "-g", self.profile["package"], "--registry=https://registry.npmmirror.com"], timeout=600, env=env)
            if code != 0:
                raise RuntimeError(detail or "npm 安装失败")
            refresh_path()
            cli_path = shutil.which(self.profile["command"])
            if not cli_path:
                # 回退：直接探测 npm 全局安装目录
                candidate = prefix / (self.profile["command"] + (".cmd" if os.name == "nt" else ""))
                if candidate.exists():
                    append_path(prefix)
                    cli_path = str(candidate)
            if not cli_path:
                raise RuntimeError("CLI 安装完成但未检测到命令")

            # 保存并校验配置
            if not self.save(quiet=True):
                raise RuntimeError("CLI 已安装，但配置写入失败")
            if not self.verify_configuration():
                raise RuntimeError("配置写入后校验失败")
            code = 0
        except Exception as exc:
            detail = str(exc)
            code = 1
        self.app.after(0, lambda: self._finish_install(code, detail))

    def verify_configuration(self) -> bool:
        return configuration_matches(self.name, self.base.get(), self.key.get().strip(),
                                     self.model.get().strip() or self.profile["default_model"], self.auth.get())

    def _finish_install(self, code: int, detail: str = ""):
        self.busy = False
        self.saved_configuration = self.verify_configuration()
        self.refresh()
        if code == 0:
            self.set_status("{name} CLI 安装完成，配置已校验", name=self.name)
            self.dialog("showinfo", "安装完成", "CLI 安装完成，配置也已写入并校验。请重新打开终端后使用客户端。")
        else:
            self.set_status("{name} CLI 安装失败：{detail}", name=self.name, detail=detail[:180])
            self.dialog("showerror", "安装失败", "CLI 安装或配置失败。请检查网络、权限和 Node.js/npm 环境后重试。")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.language = tk.StringVar(value="简体中文")
        self.localized_widgets = []
        self.profile_tabs = []
        self.logo_image = None
        self.title(APP_TITLE)
        self.geometry("900x820")
        self.minsize(900, 820)
        self._style()
        self.configure(background="#f5f5f7")
        self._load_logo()
        toolbar = ttk.Frame(self, style="Header.TFrame")
        toolbar.pack(fill="x", padx=32, pady=(20, 0))
        self.language_box = ttk.Combobox(toolbar, textvariable=self.language, values=("简体中文", "English"), state="readonly", width=12)
        self.language_box.pack(side="right")
        self.localized(ttk.Label, toolbar, "语言", style="Subtitle.TLabel").pack(side="right", padx=(0, 10))
        self.language_box.bind("<<ComboboxSelected>>", self.change_language)
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", padx=32, pady=(12, 24))
        self.logo_label = ttk.Label(header, image=self.logo_image, style="HeaderLogo.TLabel")
        self.logo_label.pack(side="left", padx=(0, 16))
        heading = ttk.Frame(header, style="Header.TFrame")
        heading.pack(side="left", fill="x", expand=True)
        self.localized(ttk.Label, heading, APP_TITLE, style="Header.TLabel").pack(anchor="w")
        self.localized(ttk.Label, heading, COPYRIGHT_ZH, style="Subtitle.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(self, text="Designed by Christian Parsifal in China.", style="Hint.TLabel").pack(side="bottom", pady=(12, 18))
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=32)
        for name in PROFILES:
            frame = ttk.Frame(tabs)
            tabs.add(frame, text=name)
            self.profile_tabs.append(ProfileTab(self, frame, name))

    def tr(self, text, **values):
        template = TRANSLATIONS.get(text, text) if self.language.get() == "English" else text
        return template.format(**values)

    def localized(self, factory, parent, text, values=None, **options):
        values = values or {}
        widget = factory(parent, text=self.tr(text, **values), **options)
        self.localized_widgets.append((widget, text, values))
        return widget

    def change_language(self, event=None):
        self.title(self.tr(APP_TITLE))
        for widget, text, values in self.localized_widgets:
            widget.configure(text=self.tr(text, **values))
        for tab in self.profile_tabs:
            tab.localize()

    def _load_logo(self):
        try:
            path = LOGO_PATH
            if not path.exists():
                path = Path(__file__).resolve().parent / "assets" / "logo.png"
            with Image.open(path) as original:
                image = original.convert("RGBA")
                self.logo_image = ImageTk.PhotoImage(image.resize((64, 64), Image.Resampling.LANCZOS))
                self.app_icon = ImageTk.PhotoImage(image.resize((256, 256), Image.Resampling.LANCZOS))
                self.iconphoto(True, self.app_icon)
        except Exception:
            self.logo_image = None

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        families = set(tkfont.families(self))
        family = next((f for f in ("SF Pro Text", "Segoe UI Variable Text", "Microsoft YaHei UI", "Segoe UI") if f in families), "TkDefaultFont")
        self.ui_family = family
        font = (family, 10)
        self.option_add("*TCombobox*Listbox.font", font)
        self.option_add("*TCombobox*Listbox.background", "#ffffff")
        self.option_add("*TCombobox*Listbox.selectBackground", "#007aff")
        style.configure(".", font=font, background="#ffffff", foreground="#1d1d1f")
        style.configure("TFrame", background="#f5f5f7")
        style.configure("App.TFrame", background="#f5f5f7")
        style.configure("Cards.TFrame", background="#ffffff", borderwidth=1, relief="solid")
        style.configure("TLabel", background="#f5f5f7", foreground="#151a17")
        style.configure("Header.TFrame", background="#f5f5f7")
        style.configure("Header.TLabel", font=("Microsoft YaHei UI", 18, "bold"), foreground="#007aff", background="#f5f5f7")
        style.configure("HeaderLogo.TLabel", background="#f5f5f7")
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 13, "bold"), background="#f5f5f7", foreground="#151a17")
        style.configure("Field.TLabel", font=("Microsoft YaHei UI", 10), foreground="#66736b", background="#f5f5f7")
        style.configure("Hint.TLabel", foreground="#66736b", background="#f5f5f7", font=("Microsoft YaHei UI", 9))
        style.configure("Subtitle.TLabel", foreground="#66736b", background="#f5f5f7", font=("Microsoft YaHei UI", 9))
        style.configure("StatusCard.TFrame", background="#ffffff")
        style.configure("Status.TLabel", foreground="#66736b", background="#ffffff", font=("Microsoft YaHei UI", 9))
        style.configure("Good.TLabel", foreground="#007aff", background="#ffffff", font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Warn.TLabel", foreground="#c2413b", background="#ffffff", font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("TCheckbutton", background="#ffffff", foreground="#6b7280", padding=6)
        style.map("TCheckbutton", background=[("active", "#ffffff")])
        style.configure("TEntry", padding=(8, 5), fieldbackground="#ffffff", bordercolor="#dfe7e2", lightcolor="#dfe7e2", darkcolor="#dfe7e2", insertcolor="#007aff")
        style.map("TEntry", bordercolor=[("focus", "#007aff")], lightcolor=[("focus", "#007aff")], darkcolor=[("focus", "#007aff")])
        style.configure("TCombobox", padding=(8, 4), fieldbackground="#ffffff", background="#ffffff", bordercolor="#dfe7e2", lightcolor="#dfe7e2", darkcolor="#dfe7e2", arrowsize=11, arrowcolor="#66736b")
        style.map("TCombobox", fieldbackground=[("readonly", "#f7f8fb")], foreground=[("readonly", "#1d1d1f")], selectbackground=[("readonly", "#f7f8fb")], selectforeground=[("readonly", "#1d1d1f")], bordercolor=[("focus", "#007aff")])
        style.configure("TButton", foreground="#007aff", background="#ffffff", padding=(10, 4), anchor="center", font=("Microsoft YaHei UI", 9))
        style.map("TButton", foreground=[("active", "#007aff"), ("disabled", "#a0a7b3")], background=[("active", "#edf3ff")])
        style.configure("Primary.TButton", foreground="#ffffff", background="#007aff", padding=(10, 6), anchor="center", font=("Microsoft YaHei UI", 9, "bold"))
        style.map("Primary.TButton", foreground=[("active", "#ffffff")], background=[("active", "#006fe6")])
        style.configure("Compact.TButton", padding=(10, 0), foreground="#34445e", font=("Microsoft YaHei UI", 9))
        style.configure("Compact.TButton", padding=(10, 0), foreground="#34445e", font=("Microsoft YaHei UI", 9))
        style.configure("TNotebook", background="#f5f5f7", borderwidth=0, tabmargins=(8, 0, 8, 6))
        style.configure("TNotebook.Tab", padding=(18, 7), background="#eef3ef", foreground="#66736b", borderwidth=0, font=("Microsoft YaHei UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", "#007aff")])
        style.configure("TSeparator", background="#dfe7e2")
        style.configure("Card.TFrame", background="#ffffff", borderwidth=0, relief="flat")
        style.configure("Cards.TFrame", borderwidth=0, relief="flat")
        style.configure("StatusCard.TFrame", background="#f5f5f7", borderwidth=0)
        style.configure("Header.TLabel", foreground="#1d1d1f", font=(family, 22, "bold"))
        style.configure("Title.TLabel", background="#ffffff", foreground="#1d1d1f", font=(family, 14, "bold"))
        style.configure("Field.TLabel", background="#ffffff", foreground="#6e6e73", font=font, padding=(0, 0, 18, 0))
        for name in ("Hint.TLabel", "Subtitle.TLabel", "Status.TLabel"):
            style.configure(name, background="#f5f5f7", foreground="#6e6e73", font=(family, 9))
        style.configure("Good.TLabel", background="#f5f5f7", foreground="#248a3d", font=(family, 9))
        style.configure("Warn.TLabel", background="#f5f5f7", foreground="#b45309", font=(family, 9))
        for name in ("TEntry", "TCombobox"):
            style.configure(name, padding=(12, 9), borderwidth=0, relief="flat", fieldbackground="#f5f5f7")
        style.configure("TNotebook.Tab", font=(family, 10, "bold"), padding=(24, 10))
        style.configure("TNotebook", tabmargins=(0, 0, 0, 0), borderwidth=0, relief="flat")

        style.layout("TNotebook", [("Notebook.padding", {"sticky": "nswe"})])
        style.layout("TNotebook.Tab", [("Notebook.padding", {
            "sticky": "nswe", "children": [("Notebook.label", {"sticky": "nswe"})]})])
        style.configure("TNotebook.Tab", expand=(0, 0, 0, 0), borderwidth=0)
        style.map("TNotebook.Tab", expand=[("selected", (0, 0, 0, 0)), ("!selected", (0, 0, 0, 0))])
        for name in ("TFrame", "App.TFrame", "Header.TFrame"):
            style.configure(name, borderwidth=0, relief="flat")

        style.layout("TEntry", [("Entry.padding", {"sticky": "nswe", "children": [
            ("Entry.textarea", {"sticky": "nswe"})]})])
        style.layout("TCombobox", [("Combobox.downarrow", {"side": "right", "sticky": "ns"}),
            ("Combobox.padding", {"sticky": "nswe", "children": [
                ("Combobox.textarea", {"sticky": "nswe"})]})])
        self._rounded_buttons(style, family)

    def _rounded_buttons(self, style, family):
        self.button_images = []
        for name, colors, foreground in (
            ("Soft", ("#eef4ff", "#e2edff", "#d5e5ff", "#f2f2f7"), "#007aff"),
            ("Blue", ("#007aff", "#0071e3", "#0062c4", "#b8d7fa"), "#ffffff"),
        ):
            images = []
            for color in colors:


                image = Image.new("RGB", (240, 144), "#ffffff")
                ImageDraw.Draw(image).rounded_rectangle((0, 0, 239, 143), radius=44, fill=color)
                images.append(ImageTk.PhotoImage(image.resize((60, 36), Image.Resampling.LANCZOS)))
            self.button_images.extend(images)
            element = name + ".Rounded.button"
            style.element_create(element, "image", images[0], ("disabled", images[3]),
                ("pressed", images[2]), ("active", images[1]), border=12, sticky="nsew")
            layout = [(element, {"sticky": "nsew", "children": [("Button.padding", {
                "sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})]
            targets = ("Primary.TButton",) if name == "Blue" else ("TButton", "Compact.TButton")
            for target in targets:
                style.layout(target, layout)
                style.configure(target, foreground=foreground, font=(family, 10), padding=(16, 0), anchor="center", borderwidth=0)
                style.map(target, foreground=[("disabled", "#8e8e93"), ("active", foreground)])


if __name__ == "__main__":
    App().mainloop()
