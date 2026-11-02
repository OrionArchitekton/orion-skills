"""Execute the published privacy recipe in isolated, disposable Git repositories."""
import os
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/office-hours/SKILL.md"


def run(argv, cwd, env, check=True):
    return subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=check)


@pytest.fixture
def repository(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    env = {"PATH": os.environ["PATH"], "HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_COUNT": "0"}
    repo = tmp_path / "ordinary repo with spaces"
    repo.mkdir()
    run(["git", "init", "--template=", str(repo)], tmp_path, env)
    # Plumbing creates a fixture baseline without invoking any installed commit hooks.
    tree = run(["git", "mktree"], repo, env).stdout.strip()
    identity = {**env, "GIT_AUTHOR_NAME": "Fixture", "GIT_COMMITTER_NAME": "Fixture",
                "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
    commit = subprocess.run(["git", "commit-tree", tree], input="fixture\n", cwd=repo,
                            env=identity, text=True, capture_output=True, check=True).stdout.strip()
    run(["git", "update-ref", "HEAD", commit], repo, env)
    return repo, env


def recipe():
    text = SKILL.read_text()
    section = text.split("### Builder Profile Append", 1)[1]
    block = re.search(r"```bash\n(.*?)\n```", section, re.S).group(1)
    return block.replace("<SKILL_DIR>", str(SKILL.parent))


def append_profile(repo, env):
    # A consumer write immediately after the recipe must never happen on failure.
    return run(["bash", "--noprofile", "--norc", "-c", recipe() +
                "\nprintf '%s\\n' '{\"synthetic\":true}' >> \"$STATE_ROOT/builder-profile.jsonl\""],
               repo, env, check=False)


@pytest.mark.parametrize("linked", [False, True])
def test_profile_is_ignored_before_first_write(repository, tmp_path, linked):
    ordinary, env = repository
    exclude = ordinary / ".git/info/exclude"
    exclude.parent.mkdir(exist_ok=True)
    exclude.write_text("# unrelated rule\nkeep-me\n")
    repo = ordinary
    if linked:
        repo = tmp_path / "linked repo with spaces"
        run(["git", "worktree", "add", "--detach", str(repo)], ordinary, env)
    result = append_profile(repo, env)
    assert result.returncode == 0, result.stderr
    assert (repo / ".office-hours/builder-profile.jsonl").is_file()
    assert run(["git", "check-ignore", "-q", ".office-hours/builder-profile.jsonl"], repo, env, False).returncode == 0
    assert run(["git", "status", "--porcelain", "--untracked-files=all"], repo, env).stdout == ""
    assert exclude.read_text().startswith("# unrelated rule\nkeep-me\n")


@pytest.mark.parametrize("failure", ["exclusion-directory", "override", "tracked", "state-symlink", "profile-symlink"])
def test_failed_protection_leaves_no_new_profile(repository, tmp_path, failure):
    repo, env = repository
    exclude = repo / ".git/info/exclude"
    exclude.parent.mkdir(exist_ok=True)
    profile = repo / ".office-hours/builder-profile.jsonl"
    outside = tmp_path / "outside"
    outside.mkdir()
    if failure == "exclusion-directory":
        exclude.mkdir()
    elif failure == "override":
        (repo / ".gitignore").write_text("!.office-hours/\n!.office-hours/builder-profile.jsonl\n")
    elif failure == "tracked":
        profile.parent.mkdir()
        profile.write_text("existing synthetic state\n")
        run(["git", "add", ".office-hours/builder-profile.jsonl"], repo, env)
    elif failure == "state-symlink":
        profile.parent.symlink_to(outside, target_is_directory=True)
    elif failure == "profile-symlink":
        profile.parent.mkdir()
        profile.symlink_to(outside / "leaked-profile")
    before = profile.read_bytes() if profile.is_file() else None
    result = append_profile(repo, env)
    assert result.returncode != 0
    assert (profile.read_bytes() if profile.is_file() else None) == before
    assert not list(outside.iterdir())


def test_repeated_recipe_preserves_unterminated_rule_and_works_from_subdirectory(repository):
    repo, env = repository
    exclude = repo / ".git/info/exclude"
    exclude.parent.mkdir(exist_ok=True)
    exclude.write_text("keep-me")
    subdir = repo / "a nested directory"
    subdir.mkdir()
    for _ in range(2):
        result = append_profile(subdir, env)
        assert result.returncode == 0, result.stderr
    assert exclude.read_text().splitlines().count("/.office-hours/") == 1
    assert run(["git", "check-ignore", "-q", "keep-me"], repo, env, False).returncode == 0
    assert len((repo / ".office-hours/builder-profile.jsonl").read_text().splitlines()) == 2


def test_outside_git_leaves_no_profile(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    env = {"PATH": os.environ["PATH"], "HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    result = append_profile(home, env)
    assert result.returncode != 0
    assert not (home / ".office-hours").exists()
