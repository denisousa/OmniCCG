import subprocess
import xmltodict
import json
import copy
from pathlib import Path
from git import Repo
from git import Repo, NULL_TREE
from typing import List, Dict
import subprocess, os
import subprocess

def check_snippet_existence(repo_path: str, file_path: str, start_line: str, end_line: str, commit_hash: str):
    file_path = file_path.replace('../../', './').replace('workspace/dataset/production', repo_path)

    def was_range_added_in_commit(commit_hash: str, file_path: str, start_line: int, end_line: int, repo_path: str = ".") -> bool:
        from git import Repo
        try:
            repo = Repo(repo_path)
            commit = repo.commit(commit_hash)
            blame = repo.blame(commit.hexsha, file_path.replace('workspace/repo',''))
        except Exception:
            return False
        total = sum(len(lines) for _, lines in blame)
        if start_line < 1 or end_line < start_line or end_line > total:
            return False
        i = 1
        for c, lines in blame:
            length = len(lines)
            bstart = i
            bend = i + length - 1
            s = max(start_line, bstart)
            e = min(end_line, bend)
            if s <= e and c.hexsha != commit.hexsha:
                return False
            i += length
        return True

    def get_file_content_at_commit(repo_path: str, commit_hash: str, file_path: str) -> str:
        repo = Repo(repo_path)
        commit = repo.commit(commit_hash)

        # Ensure file path is relative to the repo root
        rel_path = Path(file_path).as_posix().replace('workspace/repo/', '')

        try:
            blob = commit.tree / rel_path
            return blob.data_stream.read().decode("utf-8", errors="ignore")
        except KeyError:
            raise FileNotFoundError(f"File {rel_path} not found in commit {commit_hash}")

    # Extract snippet at the given commit
    file_content = get_file_content_at_commit(repo_path, commit_hash, file_path)
    if file_content is None:
        raise ValueError("File does not exist in the given commit.")

    snippet = '\n'.join(file_content.splitlines()[start_line - 1:end_line])
    the_was_added_in_coomit = was_range_added_in_commit(commit_hash, file_path, start_line, end_line, repo_path)

    if the_was_added_in_coomit:
        return True
    return False 



