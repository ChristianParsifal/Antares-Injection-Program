"""Exercise real Tk widgets with all host configuration/detection mocked."""
import AntaresIntelligentTool as tool
from unittest.mock import patch

with patch.object(tool, "user_env", return_value=""), patch.object(tool, "refresh_path"), patch.object(tool, "which", return_value=None):
    app = tool.App()
    try:
        app.update()
        for language in ("简体中文", "English", "简体中文"):
            app.language.set(language)
            for tab in app.profile_tabs:
                notebook = next(widget for widget in app.winfo_children() if widget.winfo_class() == "TNotebook")
                notebook.select(app.profile_tabs.index(tab))
                tab.base.set("https://relay.example/custom/v1")
                app.change_language()
                app.update()
                assert tab.base.get() == "https://relay.example/custom/v1"
                assert str(tab.base_box.cget("state")) == "normal"
                assert len(tab.base_box.cget("values")) == 4
                assert tab.endpoint() == ("https://relay.example/custom/v1" if tab.name == "Codex" else "https://relay.example/custom")
                for child in tab.base_box.master.winfo_children():
                    if child.winfo_class() == "TButton":
                        assert child.winfo_ismapped(), "button hidden"
                        assert child.winfo_rooty() + child.winfo_height() <= app.winfo_rooty() + app.winfo_height(), f"{language} {tab.name}: button {child.cget('text')} ends at {child.winfo_rooty() + child.winfo_height() - app.winfo_rooty()}, window height {app.winfo_height()}"
        print("PASS: editable URL, retained presets, language switching, all action buttons visible in both tabs")
    finally:
        app.destroy()
