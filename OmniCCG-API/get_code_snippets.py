import os
import shutil
import subprocess
from pathlib import Path


def _clean_git_locks(repo_path: str) -> None:
    """Remove Git lock files that may prevent operations."""
    git_dir = Path(repo_path) / '.git'
    
    if not git_dir.exists():
        return
    
    # Common Git lock files
    lock_files = [
        git_dir / 'index.lock',
        git_dir / 'HEAD.lock',
        git_dir / 'config.lock',
        git_dir / 'shallow.lock',
    ]
    
    for lock_file in lock_files:
        if lock_file.exists():
            try:
                lock_file.unlink()
                print(f"Removed lock file: {lock_file}")
            except Exception as e:
                print(f"Warning: Could not remove lock file {lock_file}: {e}")
    
    # Check refs directory for lock files
    refs_dir = git_dir / 'refs'
    if refs_dir.exists():
        for lock_file in refs_dir.rglob('*.lock'):
            try:
                lock_file.unlink()
                print(f"Removed lock file: {lock_file}")
            except Exception as e:
                print(f"Warning: Could not remove lock file {lock_file}: {e}")


def _derive_repo_name(git_url: str) -> str:
    tail = (git_url or "").rstrip("/").split("/")[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    return tail or "repo"

def _ensure_repo(git_url: str, base_root: str = "cloned_repositories") -> str:
    repo_name = _derive_repo_name(git_url)
    base_dir = os.path.join(base_root, repo_name)
    repo_dir = os.path.join(base_dir, "repo")

    os.makedirs(base_dir, exist_ok=True)

    git_dir = os.path.join(repo_dir, ".git")
    if os.path.isdir(git_dir):
        # Clean locks before git operations
        _clean_git_locks(repo_dir)
        subprocess.run(["git", "-C", repo_dir, "fetch", "--all", "--prune"], 
                      check=False, stdin=subprocess.DEVNULL)
        return os.path.abspath(repo_dir)

    # Fresh clone
    if os.path.isdir(repo_dir):
        shutil.rmtree(repo_dir, ignore_errors=True)
    subprocess.run(["git", "clone", git_url, repo_dir], 
                  check=True, stdin=subprocess.DEVNULL)
    return os.path.abspath(repo_dir)

def _checkout(repo_dir: str, commit: str) -> None:
    # Clean locks before checkout
    _clean_git_locks(repo_dir)
    try:
        subprocess.run(["git", "-C", repo_dir, "checkout", "-f", commit], 
                      check=True, stdin=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        # Retry once after cleaning locks again
        print(f"Checkout failed, retrying after cleaning locks...")
        _clean_git_locks(repo_dir)
        subprocess.run(["git", "-C", repo_dir, "checkout", "-f", commit], 
                      check=True, stdin=subprocess.DEVNULL)

def _read_text_with_fallback(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")

def _safe_repo_path(repo_dir: str, incoming_path: str) -> Path:
    """
    Safely resolve a file path from XML to an actual file in the cloned repo.
    Handles paths in various formats:
    - Absolute paths with /dataset/production (from NiCad/analysis)
    - Paths already containing /repo
    - Relative paths
    """
    repo_dir_abs = Path(repo_dir).resolve()
    
    # Normalize the incoming path: replace /dataset/production with /repo
    normalized_path = incoming_path.replace("/dataset/production", "/repo")
    normalized_path = normalized_path.replace("\\dataset\\production", "\\repo")
    
    p = Path(normalized_path)
    
    if not p.is_absolute():
        # Simple relative path - just join with repo_dir
        candidate = (repo_dir_abs / p).resolve()
    else:
        # Absolute path - try to extract relative part after /repo
        candidate = Path(normalized_path).resolve()
        
        # Try to keep as-is if it's already inside repo_dir
        try:
            candidate.relative_to(repo_dir_abs)
        except ValueError:
            # Not inside repo_dir, try to extract the part after /repo or last /repo segment
            parts = list(Path(normalized_path).parts)
            
            if "repo" in parts:
                # Find the last occurrence of "repo" and take everything after it
                repo_indices = [i for i, part in enumerate(parts) if part == "repo"]
                idx = repo_indices[-1]  # Use last occurrence
                relative_parts = parts[idx+1:]
                if relative_parts:
                    candidate = (repo_dir_abs / Path(*relative_parts)).resolve()
                else:
                    # If nothing after /repo, just use the filename
                    candidate = repo_dir_abs / Path(normalized_path).name
            else:
                # No "repo" in path, try to use just the filename
                candidate = repo_dir_abs / Path(normalized_path).name

    # Final safety check: must be inside repo_dir
    try:
        candidate.relative_to(repo_dir_abs)
    except ValueError:
        raise ValueError(
            f"Path '{incoming_path}' resolves to '{candidate}' which is outside repo directory '{repo_dir_abs}'"
        )
    
    return candidate

def _slice_lines(text: str, startline: int, endline: int) -> str:
    if startline is None or endline is None or startline < 1 or endline < startline:
        return ""
    lines = text.splitlines(True)  # keep line endings
    start_idx = startline - 1
    end_idx = min(endline, len(lines))
    return "".join(lines[start_idx:end_idx])