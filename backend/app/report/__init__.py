"""Render a printable report with the laptop's Chromium installation."""
import json
import os
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory

CHECKLIST = [
    "Identify each electronic record, its source device and how the output was produced.",
    "Document ordinary use, regular input, operation and reproduction under section 63(2).",
    "Collect the applicable scheduled certificate, party and expert particulars and signatures.",
    "Record the hash algorithm and digest, attach the hash report and check submission requirements.",
]
LEGAL_SOURCE = "https://www.indiacode.nic.in/bitstream/123456789/20063/1/a2023-47.pdf"


def browser_executable():
    override = os.getenv("UBHAYA_BROWSER")
    if override:
        return override

    if executable := shutil.which("chrome-headless-shell"):
        return executable

    # Playwright's standalone Chromium renderer is usually outside PATH.
    if location := os.getenv("PLAYWRIGHT_BROWSERS_PATH"):
        cache = Path(location)
    elif sys.platform == "win32":
        cache = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData/Local") / "ms-playwright"
    elif sys.platform == "darwin":
        cache = Path.home() / "Library/Caches/ms-playwright"
    else:
        cache = Path(os.getenv("XDG_CACHE_HOME") or Path.home() / ".cache") / "ms-playwright"
    shell_name = "chrome-headless-shell.exe" if os.name == "nt" else "chrome-headless-shell"
    shells = cache.glob(f"chromium_headless_shell-*/*/{shell_name}")
    for shell in sorted(shells, key=lambda p: p.stat().st_mtime, reverse=True):
        if shell.is_file() and os.access(shell, os.X_OK):
            return str(shell.resolve())

    for command in ("chromium", "google-chrome", "chrome", "msedge", "brave-browser"):
        if executable := shutil.which(command):
            return executable

    windows_browser_paths = (
        "Microsoft/Edge/Application/msedge.exe",
        "Google/Chrome/Application/chrome.exe",
        "BraveSoftware/Brave-Browser/Application/brave.exe",
    )
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "ProgramW6432", "LOCALAPPDATA"):
        if root := os.getenv(variable):
            for relative_path in windows_browser_paths:
                candidate = Path(root) / relative_path
                if candidate.is_file():
                    return str(candidate)

    for bundle, executable in (("Google Chrome", "Google Chrome"), ("Microsoft Edge", "Microsoft Edge"),
                               ("Chromium", "Chromium"), ("Brave Browser", "Brave Browser")):
        candidate = Path("/Applications") / f"{bundle}.app" / "Contents" / "MacOS" / executable
        if candidate.is_file():
            return str(candidate)
    return None


def render_pdf(report):
    browser = browser_executable()
    if not browser:
        raise RuntimeError("Set UBHAYA_BROWSER to the full path of Chrome, Edge, Brave or Chromium for PDF export")
    parts = ["<!doctype html><meta charset=utf-8><style>body{font:11pt sans-serif}pre{white-space:pre-wrap;overflow-wrap:anywhere}h2{break-after:avoid}</style>",
             "<h1>" + escape(report["case"]["title"]) + "</h1>"]
    for title, rows in (("Findings",report["claims"]),("Reviews",report["reviews"]),("Artifacts and SHA-256",report["artifacts"]),
                        ("Observations",report["observations"]),("Evidence requests",report["requests"]),
                        ("Limitations",report["limitations"]),("Section 63 checklist",report["section_63_checklist"])):
        parts.append("<h2>" + title + "</h2>")
        for row in rows:
            parts.append("<pre>" + escape(json.dumps(row,ensure_ascii=False,indent=2)) + "</pre>")
    with TemporaryDirectory() as directory:
        root = Path(directory)
        html = root/"report.html"
        html.write_text("".join(parts),encoding="utf-8")
        pdf = root/"report.pdf"
        try:
            subprocess.run([browser,"--headless","--disable-gpu","--no-pdf-header-footer","--disable-background-networking",
                            "--no-first-run","--no-default-browser-check",
                        f"--user-data-dir={root/'profile'}",f"--print-to-pdf={pdf}",html.as_uri()],
                           check=True,timeout=45,capture_output=True)
            return pdf.read_bytes()
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError("PDF renderer failed. Set UBHAYA_BROWSER to a working Chromium headless executable.") from exc
