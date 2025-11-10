import re
from collections import defaultdict

CONTROL_KEYWORDS = {"if", "for", "while", "catch", "switch", "synchronized"}
BLOCK_START_RE = re.compile(r"\{")
BLOCK_END_RE = re.compile(r"\}")
# captura o token imediatamente antes de "(" garantindo que não seja uma chamada com "."
CANDIDATE_NAME_RE = re.compile(r"(?<![\w\.])([A-Za-z_][A-Za-z0-9_]*)\s*\(")

def _strip_comments(java_src: str) -> str:
    """Remove // e /* */ preservando quebras de linha para manter a numeração."""
    out = []
    i = 0
    n = len(java_src)
    in_block = False
    while i < n:
        if not in_block and i+1 < n and java_src[i] == '/' and java_src[i+1] == '/':
            # até o fim da linha
            while i < n and java_src[i] != '\n':
                i += 1
            out.append('\n')
            i += 1
            continue
        if not in_block and i+1 < n and java_src[i] == '/' and java_src[i+1] == '*':
            in_block = True
            i += 2
            continue
        if in_block and i+1 < n and java_src[i] == '*' and java_src[i+1] == '/':
            in_block = False
            i += 2
            continue
        if in_block:
            # preserve newline to keep line numbers aligned
            if java_src[i] == '\n':
                out.append('\n')
            i += 1
            continue
        out.append(java_src[i])
        i += 1
    return ''.join(out)

def _is_method_signature(signature_text: str) -> str | None:
    """
    Dado um texto (possivelmente multi-linha) até o '{', retorna o nome do método se parecer assinatura válida.
    Ignora construtos de controle e chamadas.
    """
    st = signature_text.strip()
    # descartar lambdas rapidamente
    if "->" in st:
        return None
    # deve conter "(" e ")", e NÃO terminar com ';' (método abstrato/interf/interface)
    if "(" not in st or ")" not in st or st.rstrip().endswith(";"):
        return None

    # Evitar cabeçalhos de classe/enum/record
    if re.search(r'\b(class|interface|enum|record)\b', st):
        return None

    # pegar último identificador antes de "("
    # Para reduzir falsos positivos em chamadas, exigimos que não haja '.' imediatamente antes do nome
    candidates = list(CANDIDATE_NAME_RE.finditer(st))
    if not candidates:
        return None
    name = candidates[-1].group(1)

    if name in CONTROL_KEYWORDS:
        return None

    # Também filtra construções como "new Foo(bar) {"
    if re.search(r'\bnew\s+' + re.escape(name) + r'\s*\(', st):
        return None

    return name

def get_enclosing_java_method(file_path: str, startline: int, endline: int) -> str | None:
    """
    Retorna o nome do método Java que contém a maior parte do trecho [startline, endline].
    Se nenhum método contiver o trecho, tenta heurística olhando acima de startline.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    src = _strip_comments(raw)
    lines = src.splitlines()

    brace_depth = 0
    current_method = None
    method_stack = []
    # mapeia linha -> nome do método ativo
    line_to_method = {}
    # buffer para assinatura até abrir '{'
    sig_buf = []
    awaiting_body_for = None  # nome detectado enquanto aguardamos '{'

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Ignora apenas annotations na coleta de assinatura
        if awaiting_body_for is None:
            if stripped.startswith("@"):
                # annotations ficam no buffer se já estamos acumulando assinatura
                pass

        # Acumular assinatura se ainda não estamos em método e linha parece parte de cabeçalho
        if awaiting_body_for is None and current_method is None:
            if "(" in stripped or stripped.startswith("@") or re.search(r'\b(public|protected|private|static|final|abstract|synchronized|native|strictfp)\b', stripped):
                # iniciar/continuar buffer se parecer início de assinatura
                sig_buf.append(stripped)
                joined = " ".join(sig_buf)
                # Se já tem ')' podemos tentar identificar nome
                if ")" in joined:
                    name = _is_method_signature(joined)
                    if name:
                        awaiting_body_for = name
                    # Se terminar com ';', descartar (interface/abstract)
                    if joined.rstrip().endswith(";"):
                        sig_buf = []
                        awaiting_body_for = None
            else:
                sig_buf = []  # reset quando linha não parece assinatura

        # Detectar abertura de bloco
        opens = BLOCK_START_RE.findall(line)
        closes = BLOCK_END_RE.findall(line)

        # Se está aguardando corpo e encontramos '{', abrimos método
        if awaiting_body_for and opens:
            method_stack.append((awaiting_body_for, brace_depth))
            current_method = awaiting_body_for
            awaiting_body_for = None
            sig_buf = []
        # Atualiza depth após processar possível entrada no método (para atribuir depth correto)
        brace_depth += len(opens)

        # Mapear linha ao método atual
        if current_method:
            line_to_method[idx] = current_method

        # Fechamentos
        if closes:
            # primeiro reduz profundidade
            brace_depth -= len(closes)
            # se saímos do nível do método do topo, fazer pop
            while method_stack and brace_depth <= method_stack[-1][1]:
                method_stack.pop()
                current_method = method_stack[-1][0] if method_stack else None

        # Se a linha finaliza uma assinatura com ';' e ainda aguardávamos corpo, cancelar
        if awaiting_body_for:
            joined = " ".join(sig_buf)
            if joined.rstrip().endswith(";"):
                awaiting_body_for = None
                sig_buf = []

    # Selecionar o método que cobre a maior parte do intervalo
    startline = max(1, startline)
    endline = max(startline, endline)

    coverage = defaultdict(int)
    for ln in range(startline, min(endline, len(lines)) + 1):
        if ln in line_to_method:
            coverage[line_to_method[ln]] += 1

    if coverage:
        # retorna o de maior cobertura
        return max(coverage.items(), key=lambda kv: kv[1])[0]

    # Heurística: subir até 50 linhas a partir de startline procurando assinatura acima
    lookback = max(1, startline - 50)
    text_above = "\n".join(lines[lookback - 1:startline])
    # pegar último bloco que pareça assinatura antes de um '{'
    candidate = None
    acc = []
    for raw_line in text_above.splitlines():
        s = raw_line.strip()
        if s.startswith("@") or "(" in s or re.search(r'\b(public|protected|private|static|final|abstract|synchronized|native|strictfp)\b', s):
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
