
def get_commit_neighbors(repo_path: str, commit_ref: str, n: int = 5, scope: str = "--all", order: str = "topo") -> dict:
    import os
    import subprocess

    if not os.path.isdir(repo_path):
        raise RuntimeError("Invalid repository path.")

    def run_git(args):
        p = subprocess.run(["git"] + args, cwd=repo_path, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stderr.strip() or f"git {' '.join(args)} failed")
        return p.stdout

    # Resolve full hash
    target_full = run_git(["rev-parse", commit_ref]).strip()

    # Build ordered list of commits within the chosen scope
    revs = ["--all"] if scope == "--all" else [scope]
    order_flag = "--topo-order" if order == "topo" else "--date-order"
    rev_list_out = run_git(["rev-list", order_flag] + revs)
    commits = [c for c in (rev_list_out.splitlines()) if c]
    if not commits:
        raise RuntimeError("No commits found in the selected scope.")

    try:
        idx = commits.index(target_full)
    except ValueError:
        raise RuntimeError("The target commit is not present in the selected scope. Try scope='--all' or a different branch.")

    before_hashes = commits[max(0, idx - n): idx]
    after_hashes = commits[idx + 1: idx + 1 + n]

    # Helper to format commit metadata in one git call
    def format_commits(hashes):
        if not hashes:
            return []
        fmt = "%H%x01%h%x01%an%x01%ad%x01%s"
        out = run_git(["show", "-s", f"--format={fmt}", "--date=iso"] + hashes)
        rows = []
        for line in out.splitlines():
            parts = line.split("\x01")
            if len(parts) == 5:
                rows.append({
                    "hash": parts[0],
                    "short": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                    "subject": parts[4],
                })
        return rows

    before = format_commits(before_hashes)
    target = format_commits([target_full])[0]
    after = format_commits(after_hashes)

    return {"before": before, "target": target, "after": after}

