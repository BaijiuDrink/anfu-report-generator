from pathlib import Path

import yaml

import build_support

ROOT = Path(__file__).resolve().parents[1]


def test_pywin32_dependency_is_windows_only():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    pywin32_lines = [
        line.strip()
        for line in requirements.splitlines()
        if line.strip().startswith("pywin32")
    ]

    assert pywin32_lines == ['pywin32>=300; sys_platform == "win32"']


def test_executable_name_is_platform_specific():
    assert build_support.executable_name("win32") == "安服报告生成工具"
    assert build_support.executable_name("linux") == "anfu-report-generator"


def test_release_workflow_builds_windows_and_linux_downloads():
    workflow_path = ROOT / ".github" / "workflows" / "release.yml"
    workflow = yaml.load(
        workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )

    assert workflow["on"]["push"]["tags"] == ["v*"]
    jobs = workflow["jobs"]
    assert jobs["windows"]["runs-on"] == "windows-latest"
    assert jobs["linux"]["runs-on"] == "ubuntu-22.04"
    assert jobs["publish"]["needs"] == ["windows", "linux"]
    publish_steps = str(jobs["publish"]["steps"])
    assert "GH_REPO" in publish_steps
    assert "github.repository" in publish_steps

    windows_steps = str(jobs["windows"]["steps"])
    linux_steps = str(jobs["linux"]["steps"])
    assert "安服报告生成工具.exe" in windows_steps
    assert "python -m PyInstaller" in windows_steps
    assert "Smoke test Windows executable" in windows_steps
    assert "anfu-report-generator-x86_64.AppImage" in linux_steps
    assert "anfu-report-generator-linux-x86_64.tar.gz" in linux_steps
    assert "packaging/build_appimage.sh" in linux_steps
    assert "Smoke test Linux packages" in linux_steps


def test_appimage_layout_files_are_present():
    expected = [
        ROOT / "packaging" / "build_appimage.sh",
        ROOT / "packaging" / "linux" / "AppRun",
        ROOT / "packaging" / "linux" / "anfu-report-generator.desktop",
        ROOT / "packaging" / "linux" / "anfu-report-generator.svg",
    ]

    assert all(path.is_file() for path in expected)
