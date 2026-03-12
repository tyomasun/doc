#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------
# Config via env + local file
# ---------------------------
SKILL_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG_PATH = SKILL_ROOT / "local_config.json"


def _load_local_config() -> dict:
    if not LOCAL_CONFIG_PATH.is_file():
        return {}
    try:
        payload = json.loads(LOCAL_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


LOCAL_CONFIG = _load_local_config()

# Required for GitLab API calls.
GITLAB_TOKEN = (
    os.environ.get("GITLAB_TOKEN")
    or os.environ.get("GH_TOKEN")
    or str(LOCAL_CONFIG.get("GITLAB_TOKEN", ""))
).strip()

# Optional: if your GitLab uses a self-signed cert and Python fails SSL verification.
# Set GITLAB_INSECURE_SSL=1 only if absolutely required.
GITLAB_INSECURE_SSL = os.environ.get("GITLAB_INSECURE_SSL", "0").strip() == "1"

# Roots to search for local repos.
# Multiple roots are separated with os.pathsep (';' on Windows, ':' on Linux/macOS).
GIT_REPO_ROOTS = (
    os.environ.get("GIT_REPO_ROOTS")
    or str(LOCAL_CONFIG.get("GIT_REPO_ROOTS", ""))
).strip()

# Optional: path to SBIS/Saby Python stubs used during review.
STUBS_PATH = (
    os.environ.get("SBIS_STUBS_PATH")
    or os.environ.get("SABY_STUBS_PATH")
).strip()

# Where to write artifacts.
OUT_DIR = Path(
    os.environ.get("CODEX_SKILL_OUT_DIR", ".codex/tmp/gitlab-mr-review")
).resolve()


# ---------------------------
# Helpers
# ---------------------------
@dataclass
class MrInfo:
    host: str
    project_path: str
    iid: int
    project_id: int
    web_url: str
    target_branch: str
    source_branch: str
    ssh_url_to_repo: Optional[str]
    http_url_to_repo: Optional[str]


def run(cmd: list[str], cwd: Optional[Path] = None) -> str:
    if cmd and cmd[0] == "git":
        # Keep stdout clean for JSON; git command trace goes to stderr.
        print(f"[git] {' '.join(cmd)}", file=sys.stderr, flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "Command failed: "
            + " ".join(cmd)
            + "\nSTDOUT:\n"
            + proc.stdout
            + "\nSTDERR:\n"
            + proc.stderr
        )
    return proc.stdout.strip()


def choose_remote(repo_dir: Path) -> Optional[str]:
    try:
        remotes = run(["git", "remote"], cwd=repo_dir).splitlines()
    except Exception:
        return None
    if "origin" in remotes:
        return "origin"
    return remotes[0] if remotes else None


def remote_ref_exists(repo_dir: Path, remote: str, branch: str) -> bool:
    try:
        run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/{remote}/{branch}"],
            cwd=repo_dir,
        )
    except Exception:
        return False
    return True


def resolve_ref(repo_dir: Path, remote: Optional[str], branch: str) -> str:
    if remote and remote_ref_exists(repo_dir, remote, branch):
        return f"{remote}/{branch}"
    return branch


def parse_mr_url(mr_url: str) -> tuple[str, str, int]:
    """
    Expected pattern:
    https://gitlab.example.com/group/subgroup/repo/-/merge_requests/123
    """
    parsed = urllib.parse.urlparse(mr_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("MR_URL must be an absolute URL.")

    match = re.search(r"/(.+?)/-/merge_requests/(\d+)", parsed.path)
    if not match:
        raise ValueError(
            "Could not parse MR URL. Expected: .../<project>/-/merge_requests/<iid>."
        )

    host = f"{parsed.scheme}://{parsed.netloc}"
    project_path = urllib.parse.unquote(match.group(1))
    iid = int(match.group(2))
    return host, project_path, iid


def api_get(host: str, path: str):
    if not GITLAB_TOKEN:
        raise RuntimeError(
            "GITLAB_TOKEN is required (env GITLAB_TOKEN/GH_TOKEN "
            f"or {LOCAL_CONFIG_PATH})."
        )

    url = host.rstrip("/") + "/api/v4" + path
    req = urllib.request.Request(url)
    req.add_header("PRIVATE-TOKEN", GITLAB_TOKEN)
    ssl_context = None
    if GITLAB_INSECURE_SSL:
        import ssl

        ssl_context = ssl._create_unverified_context()  # noqa: S323

    with urllib.request.urlopen(req, context=ssl_context) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_remote(remote_url: str) -> str:
    normalized = remote_url.strip().replace(".git", "")
    normalized = re.sub(r"^git@([^:]+):", r"\1/", normalized)
    normalized = normalized.replace("ssh://git@", "")
    normalized = re.sub(r"^https?://", "", normalized)
    return normalized.strip("/")


def discover_repo_dir(
    project_path: str, host: str, ssh_url: Optional[str], http_url: Optional[str]
) -> Optional[Path]:
    if not GIT_REPO_ROOTS:
        return None

    roots = [value.strip() for value in GIT_REPO_ROOTS.split(os.pathsep) if value.strip()]
    if not roots:
        return None

    host_no_scheme = re.sub(r"^https?://", "", host).strip("/")
    expected_remotes = {normalize_remote(f"{host_no_scheme}/{project_path}")}
    if ssh_url:
        expected_remotes.add(normalize_remote(ssh_url))
    if http_url:
        expected_remotes.add(normalize_remote(http_url))

    candidates: list[Path] = []
    for root in roots:
        root_path = Path(os.path.expanduser(root)).resolve()
        if not root_path.exists():
            continue
        for git_dir in root_path.rglob(".git"):
            repo_dir = git_dir.parent
            try:
                remotes = run(["git", "remote", "-v"], cwd=repo_dir)
            except Exception:
                continue
            repo_remotes = set()
            for line in remotes.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    repo_remotes.add(normalize_remote(parts[1]))
            if expected_remotes.intersection(repo_remotes):
                candidates.append(repo_dir)

    if not candidates:
        return None
    candidates.sort(key=lambda path: len(str(path)))
    return candidates[0]


def resolve_stubs_path(notes: list[str]) -> str:
    if not STUBS_PATH:
        notes.append(
            "SBIS_STUBS_PATH is not set; stubs-based contract checks may be unavailable."
        )
        return ""

    stubs_dir = Path(os.path.expanduser(STUBS_PATH)).resolve()
    if not stubs_dir.exists():
        notes.append(f"Configured stubs path does not exist: {stubs_dir}")
    elif not (stubs_dir / "sbis").exists():
        notes.append(f"Configured stubs path does not contain sbis package: {stubs_dir}")

    return str(stubs_dir)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: mr_prep.py <MR_URL>", file=sys.stderr)
        raise SystemExit(2)

    mr_url = sys.argv[1].strip()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    stubs_path = resolve_stubs_path(notes)

    host, project_path, iid = parse_mr_url(mr_url)
    project_path_encoded = urllib.parse.quote(project_path, safe="")

    mr = api_get(host, f"/projects/{project_path_encoded}/merge_requests/{iid}")
    project = api_get(host, f"/projects/{project_path_encoded}")
    changes = api_get(host, f"/projects/{project_path_encoded}/merge_requests/{iid}/changes")

    info = MrInfo(
        host=host,
        project_path=project_path,
        iid=iid,
        project_id=mr["project_id"],
        web_url=mr.get("web_url", mr_url),
        target_branch=mr["target_branch"],
        source_branch=mr["source_branch"],
        ssh_url_to_repo=project.get("ssh_url_to_repo"),
        http_url_to_repo=project.get("http_url_to_repo"),
    )

    repo_dir = discover_repo_dir(
        info.project_path,
        info.host,
        info.ssh_url_to_repo,
        info.http_url_to_repo,
    )

    repo_dir_str = ""
    if repo_dir is None:
        notes.append(
            "Local repo was not found via GIT_REPO_ROOTS scanning. "
            f"Set GIT_REPO_ROOTS env var or update {LOCAL_CONFIG_PATH}."
        )
    else:
        repo_dir_str = str(repo_dir)

        run(["git", "fetch", "--all", "--prune"], cwd=repo_dir)
        remote = choose_remote(repo_dir)

        run(["git", "checkout", info.target_branch], cwd=repo_dir)
        run(["git", "pull", "--ff-only"], cwd=repo_dir)

        if remote:
            try:
                run(["git", "fetch", remote, info.source_branch], cwd=repo_dir)
            except Exception:
                notes.append(
                    f"Could not fetch source branch from {remote}; relying on --all fetch."
                )
        else:
            notes.append("No git remotes detected; relying on existing refs only.")

    changes_path = OUT_DIR / f"mr_{info.project_id}_{info.iid}_changes.json"
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")

    diff_path = OUT_DIR / f"mr_{info.project_id}_{info.iid}.diff"
    if repo_dir is not None:
        remote = choose_remote(repo_dir)
        target_ref = resolve_ref(repo_dir, remote, info.target_branch)
        source_ref = resolve_ref(repo_dir, remote, info.source_branch)
        diff_text = run(["git", "diff", f"{target_ref}...{source_ref}"], cwd=repo_dir)
        if diff_text and not diff_text.endswith("\n"):
            diff_text += "\n"
        diff_path.write_text(diff_text, encoding="utf-8")
    else:
        fallback_chunks = []
        for change in changes.get("changes", []):
            fallback_chunks.append(
                f"diff --git a/{change.get('old_path')} b/{change.get('new_path')}"
            )
            fallback_chunks.append(change.get("diff", ""))
            fallback_chunks.append("")
        diff_path.write_text("\n".join(fallback_chunks), encoding="utf-8")
        notes.append("Used GitLab API diff fragments because local git repo was not found.")

    output = {
        "repo_dir": repo_dir_str,
        "project_path": info.project_path,
        "mr_url": info.web_url,
        "target_branch": info.target_branch,
        "source_branch": info.source_branch,
        "stubs_path": stubs_path,
        "diff_unified_path": str(diff_path),
        "changes_json_path": str(changes_path),
        "notes": notes,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
