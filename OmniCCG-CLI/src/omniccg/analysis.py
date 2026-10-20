import os
import re

C_LIKE_METHOD_REGEX = re.compile(
    r"""
    ^\s*                                        # ⬅ anchor to line start
    (?:(?:public|protected|private|static|final|abstract|synchronized|native|strictfp|default)\s+)*
    (?:<[^>;{()]*>\s*)?
    (?!class\b|interface\b|enum\b|record\b)
    (?:
        [A-Za-z_][$\w]* (?:\s*\.\s*[A-Za-z_][$\w]*)*
        (?:\s*<[^>;{}()]*>)?
        (?:\s*\[\s*\])*
        | void
    )
    \s+
    ([A-Za-z_][$\w]*)                            # method name
    \s*
    \(
        [^()]* (?:\([^()]*\)[^()]*)*
    \)
    \s*
    (?:throws\s+[A-Za-z_][$\w]*(?:\s*\.\s*[A-Za-z_][$\w]*(?:\s*\.\s*[A-Za-z_][$\w]*)*)*(?:\s*,\s*[A-Za-z_][$\w]*(?:\s*\.\s*[A-Za-z_][$\w]*)*)*)?
    \s*
    (?:\{|\;)                                    # body or abstract/interface
    """,
    re.VERBOSE | re.MULTILINE,
)

PYTHON_FUNCTION_REGEX = re.compile(
    r"^\s*(?:async\s+)?def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(",
    re.MULTILINE,
)

RUBY_METHOD_REGEX = re.compile(
    r"^\s*def\s+(?:self\.)?[A-Za-z_][A-Za-z0-9_]*[!?=]?\s*(?:\(|$)",
    re.MULTILINE,
)

C_FUNCTION_REGEX = re.compile(
    r"""
    ^\s*
    (?!if\b|for\b|while\b|switch\b|return\b)
    (?:(?:static|inline|extern|const|volatile|unsigned|signed|long|short)\s+)*
    (?:struct\s+[A-Za-z_][A-Za-z0-9_]*\s+|enum\s+[A-Za-z_][A-Za-z0-9_]*\s+|union\s+[A-Za-z_][A-Za-z0-9_]*\s+)?
    [A-Za-z_][A-Za-z0-9_\s\*]*
    \s+
    [A-Za-z_][A-Za-z0-9_]*
    \s*
    \([^;{}]*\)
    \s*
    \{
    """,
    re.VERBOSE | re.MULTILINE,
)

SUPPORTED_LANGUAGE_REGEX = {
    "java": C_LIKE_METHOD_REGEX,
    "cs": C_LIKE_METHOD_REGEX,
    "c#": C_LIKE_METHOD_REGEX,
    "csharp": C_LIKE_METHOD_REGEX,
    "py": PYTHON_FUNCTION_REGEX,
    "python": PYTHON_FUNCTION_REGEX,
    "rb": RUBY_METHOD_REGEX,
    "ruby": RUBY_METHOD_REGEX,
    "c": C_FUNCTION_REGEX,
}

EXTENSION_TO_LANGUAGE = {
    ".java": "java",
    ".cs": "cs",
    ".py": "py",
    ".rb": "rb",
    ".c": "c",
}

LINE_COMMENT = re.compile(r"//.*?$", re.MULTILINE)
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
STRING_LIT = re.compile(r"\"(?:\\.|[^\"\\])*\"|\'(?:\\.|[^\'\\])*\'")
HASH_LINE_COMMENT = re.compile(r"#.*?$", re.MULTILINE)
TRIPLE_STRING = re.compile(r'""".*?"""|\'\'\'.*?\'\'\'', re.DOTALL)


def _strip_comments_and_strings(code: str) -> str:
    code = STRING_LIT.sub('""', code)
    code = BLOCK_COMMENT.sub("", code)
    code = LINE_COMMENT.sub("", code)
    return code


def _strip_python_comments_and_strings(code: str) -> str:
    code = TRIPLE_STRING.sub('""', code)
    code = STRING_LIT.sub('""', code)
    code = HASH_LINE_COMMENT.sub("", code)
    return code


def _strip_ruby_comments_and_strings(code: str) -> str:
    code = STRING_LIT.sub('""', code)
    code = HASH_LINE_COMMENT.sub("", code)
    return code


def _detect_language(file_path: str, language: str | None = None) -> str:
    if language:
        detected = language.strip().lower()
    else:
        detected = EXTENSION_TO_LANGUAGE.get(os.path.splitext(file_path)[1].lower(), "")

    if detected not in SUPPORTED_LANGUAGE_REGEX:
        raise ValueError("Unsupported language. Supported languages: java, cs, py, rb, c.")
    return detected


def _clean_source_for_language(code: str, language: str) -> str:
    if language in {"java", "cs", "c#", "csharp", "c"}:
        return _strip_comments_and_strings(code)
    if language in {"py", "python"}:
        return _strip_python_comments_and_strings(code)
    if language in {"rb", "ruby"}:
        return _strip_ruby_comments_and_strings(code)
    return code


def count_functions_in_file(file_path: str, language: str | None = None) -> int:
    if not os.path.isfile(file_path):
        raise ValueError("Please provide a valid path to a source file.")

    detected_language = _detect_language(file_path, language)

    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
        code = fh.read()
    cleaned = _clean_source_for_language(code, detected_language)
    return sum(1 for _ in SUPPORTED_LANGUAGE_REGEX[detected_language].finditer(cleaned))