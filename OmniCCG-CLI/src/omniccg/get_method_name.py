import re
from collections import defaultdict

CONTROL_KEYWORDS = {"if", "for", "while", "catch", "switch", "synchronized"}
BLOCK_START_RE = re.compile(r"\{")
BLOCK_END_RE = re.compile(r"\}")
# capture token immediately before "(" ensuring it's not a call with "."
CANDIDATE_NAME_RE = re.compile(r"(?<![\w\.])([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def _strip_comments(java_src: str) -> str:
    """Remove // and /* */ while preserving newlines to keep line numbers."""
    out = []
    i = 0
    n = len(java_src)
    in_block = False
    while i < n:
        if not in_block and i + 1 < n and java_src[i] == "/" and java_src[i + 1] == "/":
            # until the end of the line
            while i < n and java_src[i] != "\n":
                i += 1
            out.append("\n")
            i += 1
            continue
        if not in_block and i + 1 < n and java_src[i] == "/" and java_src[i + 1] == "*":
            in_block = True
            i += 2
            continue
        if in_block and i + 1 < n and java_src[i] == "*" and java_src[i + 1] == "/":
            in_block = False
            i += 2
            continue
        if in_block:
            # preserve newline to keep line numbers aligned
            if java_src[i] == "\n":
                out.append("\n")
            i += 1
            continue
        out.append(java_src[i])
        i += 1
    return "".join(out)


def _is_method_signature(signature_text: str) -> str | None:
    """
    Given a text (possibly multi-line) up to '{', return the method name if it looks like a valid signature.
    Ignores control constructs and calls.
    """
    st = signature_text.strip()
    # discard lambdas quickly
    if "->" in st:
        return None
    # must contain "(" and ")", and must NOT end with ';' (abstract/interface method)
    if "(" not in st or ")" not in st or st.rstrip().endswith(";"):
        return None

    # avoid class/enum/record headers
    if re.search(r"\b(class|interface|enum|record)\b", st):
        return None

    # get last identifier before "("
    # To reduce false positives in calls, require that there is no '.' immediately before the name
    candidates = list(CANDIDATE_NAME_RE.finditer(st))
    if not candidates:
        return None
    name = candidates[-1].group(1)

    if name in CONTROL_KEYWORDS:
        return None

    # Also filters constructs like "new Foo(bar) {"
    if re.search(r"\bnew\s+" + re.escape(name) + r"\s*\(", st):
        return None

    return name


def get_enclosing_java_method(file_path: str, startline: int, endline: int) -> str | None:
    """
    Return the Java method name that contains most of the [startline, endline] range.
    If no method contains the range, try a heuristic looking above startline.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    src = _strip_comments(raw)
    lines = src.splitlines()

    brace_depth = 0
    current_method = None
    method_stack = []
    # map line -> current method name
    line_to_method = {}
    # buffer for signature until '{' opens
    sig_buf = []
    awaiting_body_for = None  # detected name while waiting for '{'

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # ignore only annotations when collecting signature
        if awaiting_body_for is None:
            if stripped.startswith("@"):
                # annotations stay in buffer if we are already accumulating signature
                pass

        # accumulate signature if we are not yet inside a method and line looks like part of a header
        if awaiting_body_for is None and current_method is None:
            if (
                "(" in stripped
                or stripped.startswith("@")
                or re.search(
                    r"\b(public|protected|private|static|final|abstract|synchronized|native|strictfp)\b",
                    stripped,
                )
            ):
                # start/continue buffer if it looks like start of a signature
                sig_buf.append(stripped)
                joined = " ".join(sig_buf)
                # if we already have ')', we can try to identify name
                if ")" in joined:
                    name = _is_method_signature(joined)
                    if name:
                        awaiting_body_for = name
                    # if it ends with ';', discard (interface/abstract)
                    if joined.rstrip().endswith(";"):
                        sig_buf = []
                        awaiting_body_for = None
            else:
                sig_buf = []  # reset when line does not look like signature

        # detect block opening
        opens = BLOCK_START_RE.findall(line)
        closes = BLOCK_END_RE.findall(line)

        # if we are waiting for body and found '{', we open method
        if awaiting_body_for and opens:
            method_stack.append((awaiting_body_for, brace_depth))
            current_method = awaiting_body_for
            awaiting_body_for = None
            sig_buf = []
        # update depth after processing possible method entry (to assign correct depth)
        brace_depth += len(opens)

        # map line to current method
        if current_method:
            line_to_method[idx] = current_method

        # closing braces
        if closes:
            # first reduce depth
            brace_depth -= len(closes)
            # if we left the level of the top method, pop
            while method_stack and brace_depth <= method_stack[-1][1]:
                method_stack.pop()
                current_method = method_stack[-1][0] if method_stack else None

        # if line ends a signature with ';' and we were still waiting for body, cancel
        if awaiting_body_for:
            joined = " ".join(sig_buf)
            if joined.rstrip().endswith(";"):
                awaiting_body_for = None
                sig_buf = []

    # select the method that covers the largest part of the interval
    startline = max(1, startline)
    endline = max(startline, endline)

    coverage = defaultdict(int)
    for ln in range(startline, min(endline, len(lines)) + 1):
        if ln in line_to_method:
            coverage[line_to_method[ln]] += 1

    if coverage:
        # return the one with maximum coverage
        return max(coverage.items(), key=lambda kv: kv[1])[0]

    # heuristic: look up to 50 lines above startline for a signature above
    lookback = max(1, startline - 50)
    text_above = "\n".join(lines[lookback - 1 : startline])
    # get last block that looks like a signature before a '{'
    candidate = None
    acc = []
    for raw_line in text_above.splitlines():
        s = raw_line.strip()
        if s.startswith("@") or "(" in s or re.search(
            r"\b(public|protected|private|static|final|abstract|synchronized|native|strictfp)\b",
            s,
        ):
            acc.append(s)
        else:
            acc = []
        joined = " ".join(acc)
        if "{" in s and joined:
            name = _is_method_signature(joined)
            if name:
                candidate = name
            acc = []
    return candidate
