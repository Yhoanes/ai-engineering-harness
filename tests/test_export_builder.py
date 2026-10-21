import subprocess
import zipfile

from engine.export.builder import build_development_archive, build_history_bundle


def test_export_builder_dry(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    # Init dummy git repo to test git bundle
    subprocess.run(["git", "init"], cwd=str(repo), check=True)
    (repo / "test.txt").write_text("hello")
    subprocess.run(["git", "add", "test.txt"], cwd=str(repo), check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=AI Engineering Harness Tests",
            "-c",
            "user.email=harness-tests@example.invalid",
            "commit",
            "-m",
            "init",
        ],
        cwd=str(repo),
        check=True,
    )

    bundle = tmp_path / "test.bundle"
    build_history_bundle(repo, bundle)
    assert bundle.exists()

    dev_zip = tmp_path / "dev.zip"
    build_development_archive(repo, dev_zip, 123456789)
    assert dev_zip.exists()

    with zipfile.ZipFile(dev_zip, "r") as z:
        names = z.namelist()
        assert "test.txt" in names
