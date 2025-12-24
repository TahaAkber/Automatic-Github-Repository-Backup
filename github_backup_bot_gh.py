import json
import shutil
import subprocess
import datetime as dt
from pathlib import Path

REPOS_FILE = "repos.json"
BACKUP_DIR = Path("backups")
KEEP_DAYS = 14  # delete folders older than this many days

def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=False)
    return r.returncode, r.stdout, r.stderr

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def delete_old_backups(base_dir: Path, keep_days: int):
    if not base_dir.exists():
        return
    cutoff = dt.datetime.now() - dt.timedelta(days=keep_days)
    for child in base_dir.iterdir():
        if child.is_dir():
            try:
                folder_date = dt.datetime.strptime(child.name, "%Y-%m-%d")
                if folder_date < cutoff:
                    shutil.rmtree(child, ignore_errors=True)
                    print(f"Deleted old backup folder: {child}")
            except ValueError:
                pass

def require_git():
    code, out, err = run(["git", "--version"])
    if code != 0:
        raise RuntimeError("Git not found. Install Git and ensure it's in PATH.")
    print(out.strip())

def backup_repo(url: str, branch: str, out_dir: Path):
    repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    today = dt.datetime.now().strftime("%Y-%m-%d")
    ts = dt.datetime.now().strftime("%H%M%S")

    zip_path = out_dir / f"{repo_name}-{branch}-{today}.zip"

    temp_dir = out_dir / f"__tmp_{repo_name}_{ts}"
    ensure_dir(temp_dir)

    code, out, err = run([
        "git", "clone",
        "--depth", "1",
        "--branch", branch,
        "--single-branch",
        url,
        str(temp_dir)
    ])
    if code != 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Clone failed for {url}@{branch}:\n{err}")

    zip_base = str(zip_path).replace(".zip", "")
    shutil.make_archive(zip_base, "zip", root_dir=temp_dir)

    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"✅ Archived: {url}@{branch} -> {zip_path}")

def main():
    require_git()

    repos = json.loads(Path(REPOS_FILE).read_text(encoding="utf-8"))

    today = dt.datetime.now().strftime("%Y-%m-%d")
    out_dir = BACKUP_DIR / today
    ensure_dir(out_dir)

    for item in repos:
        url = item["url"]
        branch = item.get("branch", "main")
        backup_repo(url, branch, out_dir)

    delete_old_backups(BACKUP_DIR, KEEP_DAYS)
    print("Backup completed ✅")

if __name__ == "__main__":
    main()
