import os
import shutil
import platform
import subprocess
import stat
import time
from pathlib import Path
from typing import Union, Optional, List


def run_cmd(cmd: List[str], cwd: Optional[Union[str, Path]] = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=check)


def which(exe: str) -> Optional[str]:
    return shutil.which(exe)


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def remove_readonly(func, path, excinfo):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        try:
            if is_windows():
                subprocess.run(['attrib', '-R', path], check=False, capture_output=True)
                subprocess.run(['del', '/F', '/Q', path], shell=True, check=False, capture_output=True)
            else:
                subprocess.run(['chmod', '+w', path], check=False, capture_output=True)
                subprocess.run(['rm', '-f', path], check=False, capture_output=True)
        except Exception:
            pass


def force_remove_directory(path: Path) -> bool:
    try:
        if is_windows():
            result = subprocess.run(['rmdir', '/s', '/q', str(path)], shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return True
            ps_cmd = f'Remove-Item -Path "{path}" -Recurse -Force -ErrorAction SilentlyContinue'
            result = subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True, text=True)
            return result.returncode == 0
        else:
            result = subprocess.run(['rm', '-rf', str(path)], capture_output=True, text=True)
            return result.returncode == 0
    except Exception:
        return False


def safe_rmtree(path: Union[str, Path], max_retries: int = 5) -> None:
    path = Path(path)
    if not path.exists():
        return

    try:
        for root, dirs, files in os.walk(path):
            for fname in files:
                fpath = Path(root) / fname
                try:
                    os.chmod(fpath, stat.S_IWRITE | stat.S_IREAD)
                except Exception:
                    pass
    except Exception:
        pass

    for attempt in range(max_retries):
        try:
            shutil.rmtree(path, onerror=remove_readonly)
            if not path.exists():
                return
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))
            else:
                if force_remove_directory(path):
                    return
                print(f"Warning: Could not completely remove directory {path}: {e}")


def clean_git_locks(repo_path: Union[str, Path]) -> None:
    repo_path = Path(repo_path)
    git_dir = repo_path / '.git'
    if not git_dir.exists():
        return

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

    refs_dir = git_dir / 'refs'
    if refs_dir.exists():
        for lock_file in refs_dir.rglob('*.lock'):
            try:
                lock_file.unlink()
                print(f"Removed lock file: {lock_file}")
            except Exception as e:
                print(f"Warning: Could not remove lock file {lock_file}: {e}")


def printWarning(message: str) -> None:
    print("\033[93m WARNING: " + message + "\033[0m")


def printError(message: str) -> None:
    print("\033[91m ERROR: " + message + "\033[0m")


def printInfo(message: str) -> None:
    print("\033[96m INFO: " + message + "\033[0m")


def timeToString(seconds: int) -> str:
    result = ""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 3600) % 60
    if hours:
        result += str(hours) + " hours, "
    if minutes:
        result += str(minutes) + " minutes, "
    result += str(seconds) + " seconds"
    return result