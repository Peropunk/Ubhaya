"""PDF browser discovery on machines where Edge is outside PATH."""
from app import report


def test_finds_windows_browser_outside_path(tmp_path, monkeypatch):
    monkeypatch.delenv("UBHAYA_BROWSER", raising=False)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "browsers"))
    monkeypatch.setattr(report.shutil, "which", lambda _: None)
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path))
    edge = tmp_path / "Microsoft" / "Edge" / "Application" / "msedge.exe"
    edge.parent.mkdir(parents=True)
    edge.touch()
    assert report.browser_executable() == str(edge)


def test_prefers_installed_headless_shell_over_desktop_browser(tmp_path, monkeypatch):
    monkeypatch.delenv("UBHAYA_BROWSER", raising=False)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    monkeypatch.setattr(report.shutil, "which", lambda name: "chrome" if name == "chrome" else None)
    name = "chrome-headless-shell.exe" if report.os.name == "nt" else "chrome-headless-shell"
    shell = tmp_path / "chromium_headless_shell-1243" / "browser" / name
    shell.parent.mkdir(parents=True)
    shell.touch()
    shell.chmod(0o755)
    assert report.browser_executable() == str(shell)
