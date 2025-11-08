import re
import os
import re
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
import os
import re
from typing import List, Tuple, Optional

CONTROL_KW = {
    "if", "for", "while", "switch", "try", "catch",
    "finally", "do", "synchronized", "else"
}

MODIFIERS = {
    "public", "private", "protected", "static", "final", "abstract",
    "synchronized", "native", "strictfp", "transient", "volatile",
    "default", "sealed", "non-sealed"
}

CLASS_KINDS = {"class", "record", "enum"}

CLASS_DECL_RE = re.compile(
    r"""^\s*
        (?:(?:public|private|protected|abstract|final|static|sealed|non-sealed)\s+)*   # mods
        (?P<kind>class|record|enum)\s+
        (?P<name>[A-Za-z_]\w*)
        \b
    """,
    re.VERBOSE,
)

# retorna (lines_sem_comentário, mapeamento índice_original->índice_filtrado)
def _strip_comments(lines: List[str]) -> List[str]:
    out = []
    in_block = False
    for line in lines:
        s = line
        if not in_block:
            # remove // comentários de linha (ignorando dentro de bloco)
            # e trata abertura de /* */
            i = 0
            res = []
            while i < len(s):
                if not in_block and i + 1 < len(s) and s[i] == '/' and s[i+1] == '/':
                    # resto da linha é comentário
                    break
                if not in_block and i + 1 < len(s) and s[i] == '/' and s[i+1] == '*':
                    in_block = True
                    i += 2
                    continue
                res.append(s[i])
                i += 1
            out.append(''.join(res))
        else:
            # estamos dentro de /* ... */
            end = s.find("*/")
            if end >= 0:
                in_block = False
                out.append(s[end+2:])  # tudo após */ na mesma linha
            else:
                out.append("")          # linha inteira é comentário
    return out

def _first_nonempty_from(lines: List[str], j: int) -> int:
    n = len(lines)
    while j < n and not lines[j].strip():
        j += 1
    return j

def _gather_signature(lines_nc: List[str], i: int) -> Tuple[str, int, int]:
    """
    Coleta uma assinatura de método/ctor Java a partir da linha i (0-based),
    incluindo anotações acima e continua até encontrar '{'.
    Retorna (assinatura_compacta, idx_inicio, idx_linha_com_abre_chave).
    Se não obtiver '{', retorna ("", i, i).
    """
    n = len(lines_nc)

    # pular anotações acima
    start = i
    while start > 0 and lines_nc[start-1].lstrip().startswith("@"):
        start -= 1

    # pular linhas em branco entre anotações e assinatura
    while start < n and not lines_nc[start].strip():
        start += 1

    # concatenar até achar '{'
    buf = []
    j = start
    found_brace = -1
    while j < n:
        part = lines_nc[j]
        buf.append(part.strip())
        if "{" in part:
            found_brace = j
            break
        # se a linha termina com ';' antes de encontrar '{', é declaração/abstract/interface
        if ";" in part and "{" not in part:
            return ("", i, i)
        j += 1

    if found_brace == -1:
        return ("", i, i)

    # compactar espaços
    sig = " ".join(x for x in buf if x)
    # remover conteúdo após o primeiro '{'
    sig = sig.split("{", 1)[0].strip()
    return (sig, start, found_brace)

def _is_control_signature(sig: str) -> bool:
    # token inicial sendo palavra de controle => não é método
    tokens = sig.split()
    if not tokens:
        return True
    head = tokens[0]
    return head in CONTROL_KW

def _extract_method_name(sig: str, current_class: Optional[str]) -> Tuple[Optional[str], bool]:
    """
    Extrai o nome imediatamente antes de '('.
    Retorna (name, is_constructor).
    Valida construtor (igual à classe). Para métodos, exige que haja "tipo" antes do nome
    que não seja apenas modificador.
    """
    if "(" not in sig:
        return (None, False)

    # pegue a substring até '(' e ache o último identificador
    pre = sig.split("(", 1)[0]
    # troque <...> por vazio (generics) para simplificar a tokenização do tipo
    pre_clean = re.sub(r"<[^>]*>", " ", pre)
    # também remova annotations embutidas (pouco comum, mas seguro)
    pre_clean = re.sub(r"@\w+(?:\([^)]*\))?", " ", pre_clean)

    # último identificador antes de '('
    m = re.search(r"([A-Za-z_]\w*)\s*$", pre_clean)
    if not m:
        return (None, False)
    name = m.group(1)

    # verificação de construtor
    if current_class and name == current_class:
        return (name, True)

    # Para método, precisa haver algo antes do nome que não seja só modificador
    before = pre_clean[:m.start()].strip()
    if not before:
        return (None, False)

    # pegue o último token significativo antes do nome (ignorando espaços múltiplos)
    toks = [t for t in re.split(r"\s+", before) if t]
    if not toks:
        return (None, False)
    last = toks[-1]

    # se o último token é apenas modificador, não temos tipo -> provavelmente NÃO é método
    if last in MODIFIERS:
        return (None, False)

    # evitar casos bizarros como label: foo(...) (raro em Java), ou lambda
    if "=>" in sig or ":" in toks[-1]:
        return (None, False)

    return (name, False)

def _block_end(lines_nc: List[str], start_line_with_open_brace: int) -> int:
    """
    Dada a linha (0-based) onde existe '{' que abre o bloco do método,
    encontra a linha (1-based) onde o bloco termina.
    """
    n = len(lines_nc)
    depth = 0
    opened = False
    for j in range(start_line_with_open_brace, n):
        s = lines_nc[j]
        depth += s.count("{")
        if s.count("{"):
            opened = True
        depth -= s.count("}")
        if opened and depth == 0:
            return j + 1  # devolver 1-based
    return n

def get_enclosing_method_name(file_path: str, startline: int, endline: int) -> Optional[str]:
    file_path = file_path.replace("../../", "./")
    if not os.path.isfile(file_path):
        return None

    if not file_path.lower().endswith(".java"):
        # funciona somente para Java, conforme solicitado
        return None

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = f.read().splitlines()

    n = len(raw_lines)
    if n == 0:
        return None
    startline = max(1, min(startline, n))
    endline = max(startline, min(endline, n))

    lines_nc = _strip_comments(raw_lines)

    # rastrear classe/record/enum atuais para validar construtores
    class_stack: List[Tuple[int, str]] = []  # (brace_depth, class_name)
    defs: List[Tuple[int, int, str]] = []    # (start, end, name) 1-based

    # brace depth com comentários removidos
    depth = 0
    i = 0
    while i < n:
        line = lines_nc[i]

        # detectar declaração de classe/record/enum
        mcls = CLASS_DECL_RE.match(line)
        if mcls:
            kind = mcls.group("kind")
            cname = mcls.group("name")
            # empilha com a profundidade ATUAL; o '{' pode estar nesta linha ou na próxima
            class_stack.append((depth, cname))

        # tentar montar assinatura começando aqui (considerando anotações acima)
        sig, sig_start, open_brace_line = _gather_signature(lines_nc, i)
        if sig:
            # rejeitar controles
            if not _is_control_signature(sig):
                # nome + verificação construtor ou método com tipo
                current_class = None
                for d, cname in reversed(class_stack):
                    if d <= depth:
                        current_class = cname
                        break

                name, is_ctor = _extract_method_name(sig, current_class)

                # se extraiu nome, é um candidato válido (método ou construtor)
                if name:
                    # se a assinatura tinha ';' antes do '{', _gather_signature já descartou
                    # agora calcula fim do bloco
                    end_1based = _block_end(lines_nc, open_brace_line)
                    start_1based = sig_start + 1  # converter 0-based -> 1-based
                    defs.append((start_1based, end_1based, name))
                    # avançar o cursor para depois da linha do '{' para evitar matches redundantes
                    i = open_brace_line
        # atualizar profundidade e stack de classes
        depth += line.count("{")
        depth -= line.count("}")
        # desempilha classes que saíram de escopo
        while class_stack and class_stack[-1][0] > depth:
            class_stack.pop()

        i += 1

    if not defs:
        return None

    # Escolhe o menor bloco que contém completamente [startline, endline]
    best = None
    for s, e, name in defs:
        if s <= startline and e >= endline:
            if best is None or (e - s) < (best[1] - best[0]):
                best = (s, e, name)

    if best:
        return best[2]

    # Fallback: pega a definição imediatamente anterior que ainda cobre o início
    prev = [d for d in defs if d[0] <= startline]
    if prev:
        s, e, name = max(prev, key=lambda x: x[0])
        if e >= startline:
            return name

    return None
