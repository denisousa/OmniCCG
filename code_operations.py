import re
import os
import re
import subprocess
import json, xmltodict, pathlib
from typing import Optional, List, Tuple

_HEADER_RE = re.compile(
    r"""
    (?P<header>
        ^\s*
        (?:(?:public|protected|private|static|final|abstract|synchronized|
             native|strictfp|default|sealed|non-sealed)\s+)*
        (?:<[^>;{}()]*>\s*)?              # leading generics (e.g. <T>)
        [\w$<>\[\].?]+\s+                 # return type
        (?P<name>[A-Za-z_]\w*)\s*         # method name
        \(
            (?P<params>[^()]*)            # params blob (flat, heur.)
        \)
        \s*
        (?:throws\s+[\w$<>\[\].?,\s]+)?   # optional throws
    )
    \s*\{                                  # body starts
    """,
    re.VERBOSE | re.MULTILINE,
)

def _strip_comments(code: str) -> str:
    """Remove /* ... */ and // ... comments while preserving line breaks."""
    code = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), code, flags=re.S)
    code = re.sub(r'//.*?$', '', code, flags=re.M)
    return code


def java_function_exists_by_name(function_name: str, java_file_content: str) -> bool:
    try:
        cleaned = _strip_comments(java_file_content)
        for m in _HEADER_RE.finditer(cleaned):
            if m.group('name') == function_name:
                return True
        return False
    except:
        return False

import git
import os
from git import Repo, BadName, InvalidGitRepositoryError
import os
import subprocess
import re
import os
import subprocess

def extract_added_code(diff_content, target_file):
    # Initialize an empty list to store the added code blocks
    added_code_blocks = []

    # Flag to track when we are in the section of the diff for the target file
    in_target_file_diff = False
    
    # Remove the 'a/' and 'b/' prefixes from the file paths in the diff content
    target_file = target_file.replace('a/', '').replace('b/', '')

    # Split the diff content into lines
    diff_lines = diff_content.splitlines()

    # Loop through the diff content line by line
    current_block = []
    for line in diff_lines:
        # Detect the beginning of the diff for the target file (it starts with '--- a/<file_name>')
        if line.startswith(f'--- a/{target_file}') or line.startswith(f'+++ b/{target_file}'):
            in_target_file_diff = True  # We are now in the diff for the specified file
            continue  # Skip this line (just a header for the diff)

        # If we're inside the diff for the target file, start processing the changes
        if in_target_file_diff:
            # End of the diff for the target file (starts with '+++ <file_name>' or '--- <file_name>')
            if line.startswith('+++ ') or line.startswith('--- '):
                continue  # Skip this line (file path with a/ or b/ prefix)

            # Identify added lines (those starting with '+')
            if line.startswith('+'):
                current_block.append(line[1:].strip())  # Remove the '+' and strip the line

            # If we reach a line that isn't an added line, we complete the current block
            elif current_block:
                added_code_blocks.append("\n".join(current_block))  # Add the block as a single string
                current_block = []  # Reset the current block

    # If there was any remaining block (e.g., file ended with added lines)
    if current_block:
        added_code_blocks.append("\n".join(current_block))

    return added_code_blocks

def check_commit_for_code(repo_path, fragment, commit_sha):
    if not os.path.isdir(os.path.join(repo_path, '.git')):
        raise ValueError(f"The provided path '{repo_path}' is not a valid git repository.")


    cmd = f"git -C {repo_path} show {commit_sha}"
    diff_content = subprocess.check_output(cmd, shell=True, text=True)

    added_code = extract_added_code(diff_content, fragment.file.replace('../../workspace/repo/', ''))

    start_line = fragment.ls
    end_line = fragment.le

    # Get the fragment lines from the local file (lines to compare with the diff)
    local_path = fragment.file.replace('../../', './')
    with open(local_path, 'r') as file:
        lines_in_file = file.readlines()[start_line - 1:end_line]  # 0-indexed

    fragment_lines = [line.strip() for line in lines_in_file]

    # Initialize flags for determining the state of the code
    all_added = all(line in "\n".join(added_code) for line in fragment_lines)
    part_added = any(line in "\n".join(added_code) for line in fragment_lines)

    # Return the result based on the flags
    if all_added:
        return "Code fully added"
    elif part_added:
        return "Part of the code was added"
    else:
        return "Code already existed"

import os
import re
import subprocess
from typing import List, Tuple, Optional

def check_method_change(file_path: str, method_name: str, v1_hash: str, v2_hash, repo: str = ".") -> str:
    """
    Return one of: "removed", "modified", "unchanged", "not-found".

    Compares `commit` against its first parent and checks whether the given
    method/function in `file_path` was removed or modified.

    Heuristics supported:
      - Python:  def name(...):  ... (until next def/class at same indent)
      - C-like (C/C++/C#/Java/JS/TS/Go/Swift/Kotlin/Scala/Rust/PHP): header 'name(' then brace-matched { ... }
      - Ruby:    def name ... end
      - Lua:     function name(...) ... end
      - Fallback: textual occurrences of 'name(' (1-line pseudo-blocks)
    """

    def show_blob(repo_path: str, commit: str, file_path: str) -> Optional[str]:
        try:
            os.system(f'cd {repo_path} && git checkout {commit}')
            content = open(file_path, 'r').read()
            return content
        except:
            return None


    def pick_kind(path: str) -> str:
        ext = os.path.splitext(path.lower())[1]
        if ext == ".py": return "python"
        if ext in {".rb"}: return "ruby"
        if ext in {".lua"}: return "lua"
        if ext in {".c",".h",".cpp",".hpp",".cc",".cxx",".cs",".java",".js",".jsx",".ts",".tsx",".go",".swift",".kt",".kts",".scala",".rs",".php"}:
            return "c_like"
        return "fallback"

    def blocks_python(src: str, name: str) -> List[Tuple[int,int]]:
        lines = src.splitlines()
        pat = re.compile(rf"^\s*def\s+{re.escape(name)}\s*\(")
        out = []
        for i, line in enumerate(lines):
            if pat.search(line):
                indent = len(line) - len(line.lstrip())
                j = i + 1
                while j < len(lines):
                    l = lines[j]
                    if l.strip() and (len(l) - len(l.lstrip()) <= indent) and re.match(r"^\s*(def|class)\b", l):
                        break
                    j += 1
                out.append((i, j))
        return out

    def blocks_c_like(src: str, name: str) -> List[Tuple[int,int]]:
        out = []
        text = src
        rx = re.compile(rf"\b{re.escape(name)}\s*\(")
        pos = 0
        while True:
            m = rx.search(text, pos)
            if not m: break
            brace = text.find("{", m.end())
            if brace == -1:
                pos = m.end(); continue
            depth = 0; i = brace
            while i < len(text):
                ch = text[i]
                if ch == "{": depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        start_ln = text.count("\n", 0, m.start())
                        end_ln = text.count("\n", 0, i+1) + 1
                        out.append((start_ln, end_ln))
                        pos = i + 1
                        break
                i += 1
            else:
                pos = m.end()
        return out

    def blocks_ruby(src: str, name: str) -> List[Tuple[int,int]]:
        lines = src.splitlines()
        start_rx = re.compile(rf"^\s*def\s+{re.escape(name)}\b")
        out = []; start = None; depth = 0
        for i, line in enumerate(lines):
            if start is None and start_rx.search(line):
                start = i; depth = 1; continue
            if start is not None:
                if re.search(r"\b(def|do)\b", line): depth += 1
                if re.search(r"^\s*end\b", line):
                    depth -= 1
                    if depth <= 0:
                        out.append((start, i+1)); start = None; depth = 0
        return out

    def blocks_lua(src: str, name: str) -> List[Tuple[int,int]]:
        lines = src.splitlines()
        start_rx = re.compile(rf"^\s*function\s+{re.escape(name)}\s*\(")
        out = []; start = None; depth = 0
        for i, line in enumerate(lines):
            if start is None and start_rx.search(line):
                start = i; depth = 1; continue
            if start is not None:
                if re.search(r"\b(function|do|then)\b", line): depth += 1
                if re.search(r"^\s*end\b", line):
                    depth -= 1
                    if depth <= 0:
                        out.append((start, i+1)); start = None; depth = 0
        return out

    def blocks_fallback(src: str, name: str) -> List[Tuple[int,int]]:
        lines = src.splitlines()
        rx = re.compile(rf"\b{re.escape(name)}\s*\(")
        return [(i, i+1) for i, ln in enumerate(lines) if rx.search(ln)]

    def extract_blocks(src: Optional[str], path: str, name: str) -> List[Tuple[int,int]]:
        if src is None: return []
        kind = pick_kind(path)
        if kind == "python":   bs = blocks_python(src, name)
        elif kind == "c_like": bs = blocks_c_like(src, name)
        elif kind == "ruby":   bs = blocks_ruby(src, name)
        elif kind == "lua":    bs = blocks_lua(src, name)
        else:                  bs = []
        return bs if bs else blocks_fallback(src, name)

    def norm(txt: str) -> str:
        lines = [l.rstrip() for l in txt.splitlines()]
        while lines and lines[0] == "": lines.pop(0)
        while lines and lines[-1] == "": lines.pop()
        return "\n".join(lines)

    file_path = file_path.replace('../../', './')
    before = show_blob(repo, v1_hash, file_path)
    after  = show_blob(repo, v2_hash, file_path)
    if before is None and after is None:
        return "not-found"

    # 3) Extract method “blocks”
    b_blocks = extract_blocks(before, file_path, method_name)
    a_blocks = extract_blocks(after,  file_path, method_name)

    if not b_blocks and not a_blocks:
        return "Not-found"
    if b_blocks and not a_blocks:
        return "Removed"
    if not b_blocks and a_blocks:
        # Added in commit; not removed/modified relative to parent
        return "Unchanged"

    # 4) Compare each before-block to best after-block
    used = set()
    modified = False
    for bspan in b_blocks:
        btxt = "\n".join(before.splitlines()[bspan[0]:bspan[1]]) if before else ""
        bnorm = norm(btxt)
        match_j = None
        equal = False
        for j, aspan in enumerate(a_blocks):
            if j in used: continue
            atxt = "\n".join(after.splitlines()[aspan[0]:aspan[1]]) if after else ""
            anorm = norm(atxt)
            if anorm == bnorm:
                match_j = j; equal = True; break
            # header-line equality heuristic
            if btxt.splitlines()[:1] and atxt.splitlines()[:1] and \
               btxt.splitlines()[0].strip() == atxt.splitlines()[0].strip():
                match_j = j; equal = False; break
        if match_j is None:
            # This specific occurrence disappeared -> treat as removed,
            # but since there are also other occurrences, prioritize "removed".
            return "Removed"
        used.add(match_j)
        if not equal:
            modified = True

    return "Modified" if modified else "Unhanged"


def xml_to_json(xml_path: str, json_path: str, pretty=True):
    xml_path = pathlib.Path(xml_path)
    if json_path is None:
        json_path = xml_path.with_suffix(".json")

    with xml_path.open("r", encoding="utf-8") as f:
        data = xmltodict.parse(f.read())  # atributos -> "@attr", texto -> "#text"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2 if pretty else None)

    return str(json_path)


def get_enclosing_method_name(file_path: str, startline: int, endline: int) -> Optional[str]:
    file_path = file_path.replace('../../', './')
    if not os.path.isfile(file_path):
        return None

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    n = len(lines)
    if n == 0:
        return None
    startline = max(1, min(startline, n))
    endline = max(startline, min(endline, n))

    ext = os.path.splitext(file_path)[1].lower()

    # --- padrões de definição ---
    py_pat = re.compile(r"^\s*(?:async\s+)?def\s+(?P<name>[A-Za-z_]\w*)\s*\(")
    # Bem permissivo para C/C++/Java: linha que termina abrindo bloco de função
    c_like_pats = [
        re.compile(
            r"""^\s*
                (?:inline|static|extern|virtual|constexpr|explicit|friend|typedef|
                   public|private|protected|final|abstract|synchronized|native|volatile|
                   const|register|mutable|auto|template|class|struct|enum
                )?[\s\w:<>\*\&\.\[\],()@]*?
                (?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{
            """,
            re.VERBOSE,
        ),
        # fallback: tipo nome(args) {
        re.compile(r"^\s*[\w:<>\*\&\.\[\],\s]+\s+(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{")
    ]

    def is_python() -> bool:
        return ext == ".py"

    # --- localiza todas as defs e seus blocos ---
    defs: List[Tuple[int, int, str]] = []  # (inicio, fim, nome)

    if is_python():
        # método termina quando a indentação volta
        def indent(s: str) -> int:
            return len(s) - len(s.lstrip(" "))

        for i, line in enumerate(lines, 1):
            m = py_pat.match(line)
            if not m:
                continue
            name = m.group("name")
            base = indent(line)
            end = n
            for j in range(i + 1, n + 1):
                lj = lines[j - 1]
                if not lj.strip():
                    continue
                if lj.lstrip().startswith("#"):
                    continue
                if indent(lj) <= base:
                    end = j - 1
                    break
            defs.append((i, end, name))
    else:
        # C-like: conta chaves a partir da linha da definição
        def block_end_from(i_start: int) -> int:
            depth = 0
            opened = False
            for j in range(i_start, n + 1):
                s = lines[j - 1]
                # abordagem simples: apenas conta { e }
                depth += s.count("{")
                if s.count("{"):
                    opened = True
                depth -= s.count("}")
                if opened and depth == 0:
                    return j
            return n

        for i, line in enumerate(lines, 1):
            m = None
            for pat in c_like_pats:
                m = pat.match(line)
                if m:
                    break
            if not m:
                continue
            name = m.group("name")
            end = block_end_from(i)
            defs.append((i, end, name))

    if not defs:
        return None

    # escolhe o menor bloco que contém completamente [startline, endline]
    best = None
    for s, e, name in defs:
        if s <= startline and e >= endline:
            if best is None or (e - s) < (best[1] - best[0]):
                best = (s, e, name)

    if best:
        return best[2]

    # fallback: se não cobrir totalmente, pega a definição imediatamente anterior que ainda cobre o início
    prev = [d for d in defs if d[0] <= startline]
    if prev:
        s, e, name = max(prev, key=lambda x: x[0])
        if e >= startline:
            return name

    return None
