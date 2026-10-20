import os
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

from git import Repo
from git.exc import BadName

from omniccg.models import Context
from omniccg.utils import safe_rmtree, clean_git_locks, printWarning, printInfo, printError


def SetupRepo(ctx: Context) -> None:
    s, p = ctx.settings, ctx.paths

    if s.local_path:
        src = Path(s.local_path)
        dest = Path(p.repo_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            safe_rmtree(dest)
        shutil.copytree(src, dest)
        return

    print("Setting up local directory for git repository " + s.git_url)

    repo_git_dir = os.path.join(p.repo_dir, ".git")

    if os.path.isdir(repo_git_dir):
        repo = Repo(p.repo_dir)
        try:
            clean_git_locks(p.repo_dir)
            for remote in repo.remotes:
                remote.fetch(prune=True)
            if not repo.head.is_detached:
                try:
                    repo.git.pull("--ff-only")
                except Exception:
                    printInfo("Pull --ff-only skipped (non-FF or no upstream). Fetched refs only.")
            else:
                printInfo("Detached HEAD or no branch; fetched refs only.")
        except Exception as e:
            printWarning(f"Git fetch/pull encountered an issue: {e}")
        return

    if os.path.isdir(p.repo_dir):
        clean_git_locks(p.repo_dir)
        safe_rmtree(p.repo_dir)

    os.makedirs(p.ws_dir, exist_ok=True)
    Repo.clone_from(s.git_url, p.repo_dir)
    print(" Repository setup complete.\n")


def PrepareGitHistory(ctx: Context) -> None:
    print("Getting git history")
    s, p = ctx.settings, ctx.paths
    repo = Repo(p.repo_dir)

    rev = "HEAD"
    iter_kwargs: Dict[str, Any] = {}

    if s.specific_commit:
        try:
            target_commit = repo.commit(s.specific_commit)
        except BadName:
            raise RuntimeError(
                f"Specific commit '{s.specific_commit}' not found in repository {p.repo_dir}"
            )
        rev = f"{target_commit.hexsha}..HEAD"
    elif s.use_days and s.days is not None:
        rev = "--all"
        cutoff_datetime = datetime.now() - timedelta(days=int(s.days or 0))
        iter_kwargs = {"since": cutoff_datetime}
    elif s.from_begin:
        rev = "--all"

    if s.use_merge_commits:
        iter_kwargs["merges"] = True

    commits = repo.iter_commits(rev, **iter_kwargs)

    if s.use_merge_commits:
        commits = (c for c in commits if len(c.parents) > 1)

    if s.use_leaps and int(s.commit_leaps or 0) > 1:
        step = int(s.commit_leaps)
        commits = (c for i, c in enumerate(commits) if i % step == 0)

    commits = list(commits)
    lines = [
        f"{c.hexsha[:7]} {datetime.fromtimestamp(c.committed_date).date()} {c.author.name} {c.summary}"
        for c in commits
    ]
    Path(p.hist_file).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(lines)} commit(s) to {p.hist_file}")


def GetHashes(ctx: Context) -> List[str]:
    p = ctx.paths
    hashes: List[str] = []
    if not os.path.exists(p.hist_file):
        return hashes
    with open(p.hist_file, "rb") as fp:
        for raw in fp:
            raw = raw.strip()
            if not raw:
                continue
            first = raw.split(None, 1)[0]
            try:
                h = first.decode("ascii")
            except UnicodeDecodeError:
                continue
            hashes.append(h)
    hashes.reverse()
    return hashes


def PrepareSourceCode(ctx: Context) -> bool:
    s, p = ctx.settings, ctx.paths
    print("Preparing source code")
    found = False

    repo_root = os.path.abspath(p.repo_dir)
    if not os.path.isdir(repo_root):
        printError(f"Repository directory not found: {repo_root}")
        return False

    if os.path.exists(p.data_dir):
        safe_rmtree(p.data_dir)
    os.makedirs(p.res_dir, exist_ok=True)
    os.makedirs(p.clone_detector_dir, exist_ok=True)
    os.makedirs(p.data_dir, exist_ok=True)
    os.makedirs(p.prod_data_dir, exist_ok=True)

    repo_path = Path(repo_root)

    for src in repo_path.rglob("*"):
        if not src.is_file():
            continue
        if any(part == ".git" for part in src.parts):
            continue
        name_lower = src.name.lower()
        if not name_lower.endswith(f".{s.language}"):
            continue
        if "test" in name_lower:
            continue

        rel_dir = os.path.relpath(str(src.parent), repo_root)
        dst_dir = p.prod_data_dir if rel_dir == "." else os.path.join(p.prod_data_dir, rel_dir)
        os.makedirs(dst_dir, exist_ok=True)
        try:
            shutil.copy2(str(src), os.path.join(dst_dir, src.name))
        except Exception:
            pass
        else:
            found = True

    print("Source code ready for clone analysis.\n")
    return found


def checkout_commit(repo: Repo, commit_hash: str, repo_dir: str) -> None:
    try:
        head_short = repo.git.rev_parse("--short", "HEAD")
    except Exception:
        head_short = ""
    if commit_hash in head_short:
        return
    for attempt in range(2):
        try:
            clean_git_locks(repo_dir)
            if attempt > 0:
                time.sleep(1)
            repo.git.checkout(commit_hash, f=True)
            time.sleep(0.5)
            return
        except Exception as e:
            if attempt == 1:
                raise RuntimeError(f"git checkout {commit_hash} failed: {e}")
