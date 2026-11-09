from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

scripts = Path(SPECPATH)
root = scripts.parent.parent
defaults = [
    (str(root / "huntly.yaml"), "share/huntly"),
    (str(root / ".env.example"), "share/huntly"),
]
for folder, private_names in {
    "prompts": set(),
    "skills": {"product_knowledge.md", "email_rules.md", "competitive_intel.md"},
}.items():
    defaults.extend(
        (str(path), f"share/huntly/{folder}")
        for path in sorted((root / folder).glob("*.md"))
        if path.name not in private_names
    )

a = Analysis(
    [str(scripts / "desktop_entry.py")],
    pathex=[str(root)],
    datas=defaults + collect_data_files("huntly", subdir="web"),
    hiddenimports=["huntly.cli", "keyring.backends.Windows", "webview.platforms.edgechromium"],
)
def browser_files(files):
    # Huntly launches Playwright for browsing and does not record sessions.
    return [item for item in files if "/.local-browsers/ffmpeg-" not in item[0].replace("\\", "/")]


pyz = PYZ(a.pure)
desktop = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Huntly",
    console=False, icon=str(scripts / "huntly.ico"), upx=False,
)
cli = EXE(
    pyz, a.scripts[:-1] + [("cli_entry", str(scripts / "cli_entry.py"), "PYSOURCE")], [],
    exclude_binaries=True, name="HuntlyCLI", console=True,
    icon=str(scripts / "huntly.ico"), upx=False,
)
coll = COLLECT(desktop, cli, browser_files(a.binaries), browser_files(a.datas), name="Huntly", upx=False)
