import os
import time
import shutil
from git import Repo
from pathlib import Path
import xml.etree.ElementTree as etree
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from code_operations import get_enclosing_method_name
from run_simian import parse_simian_to_clones
from check_results import generate_clones_xml
import subprocess
import hashlib
import re
from typing import Union, Dict, Any, List

# Project settings
# GIT_URL = "https://github.com/tjake/Jlama" # The URL of the git repository to clone.
# GIT_URL = "https://github.com/Grasscutters/Grasscutter"
GIT_URL = "https://github.com/denisousa/clones-test"
# GIT_URL = "https://github.com/spring-projects/spring-petclinic"
USE_MERGE_COMMITS = False
USE_INTERVAL = False
COMMIT_INTERVAL = 20
FROM_BEGIN = True       # How often a commit should be analysed (put 1 for every commit)
ALL_COMMITS = True
USE_MAX_COMMITS = False        # Get all Commits to defined time
MAX_COMMITS = 30         # Maximum number of commits to analyse
DAYS = 365 * 2
LANGUAGE = "java"             # Language extension of project ("java" of "c")
CLONE_DETECTOR_TOOL = ["Nicad", "Simian"]

# Directories
SCRIPT_DIR = "scripts"
TOOLS_DIR = "tools"
RES_DIR = "results"
CUR_RES_DIR = RES_DIR + "/0000000"
WS_DIR = "workspace"
REPO_DIR = WS_DIR + "/repo"
DATA_DIR = WS_DIR + "/dataset"
PROD_DATA_DIR = DATA_DIR + "/production"
CLONE_DETECTOR_DIR = "clone_detector_result"
CLONE_DETECTOR_XML = "clone_detector_result/result.xml"

# Files
HIST_FILE = WS_DIR + "/githistory.txt"
P_RES_FILE = RES_DIR + "/production_results.xml"
P_DENS_FILE = RES_DIR + "/production_density.csv"

# Data
P_LIN_DATA = [] # All Lineages
P_DENS_DATA = [] # All Density

# get_commit_neighbors(REPO_DIR, "af32499")

# Output functions
def printWarning(message):
    print('\033[93m WARNING: ' + message + '\033[0m')

def printError(message):
    print('\033[91m ERROR: ' + message + '\033[0m')

def printInfo(message):
    print('\033[96m INFO: ' + message + '\033[0m')

# Classes
class CloneFragment():
    def __init__(self, file, ls, le, fn = "", fh = 0):
        self.file = file.replace('/dataset/production','/repo')
        self.ls = ls
        self.le = le
        self.function_name = fn
        self.function_hash = fh
        self.code_content = self.get_code_content()
        self.origin_note = None
        self.death_note = None
        self.move_note = None
        self.hash = hashlib.sha256(f'{self.file}{self.ls}{self.le}'.encode('utf-8')).hexdigest()

    def contains(self, other):
        return self.file == other.file and self.ls <= other.ls and self.le >= other.le

    def __eq__(self, other):
        return self.file == other.file and self.ls == other.ls and self.le == other.le

    def get_current_commit7(self, repo_path):
        try:
            res = subprocess.run(
                ["git", "-C", repo_path, "rev-parse", "--short=7", "HEAD"],
                check=True, capture_output=True, text=True
            )
            commit7 = res.stdout.strip()
            return commit7 or None
        except subprocess.CalledProcessError:
            return None

    def get_code_content(self):
        try:
            path = self.file.replace('../../','./')
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            # converte para base-0 e inclui end_line
            start_idx = max(0, self.ls - 1)
            end_idx = min(len(lines), self.le)
            snippet = "".join(lines[start_idx:end_idx])
            # normaliza quebras de linha
            return snippet.replace("\r\n", "\n").replace("\r", "\n")
        except Exception:
            # Em caso de erro de leitura, retornamos None para indicar desconhecido
            return None

    def matches(self, other):
        return self.hash == other.hash

    def matchesStrictly(self, other):
        return self.file == other.file and self.function_name == other.function_name and (self.ls == other.ls or self.function_hash == other.function_hash)

    def __hash__(self):
        return hash(self.file+str(self.ls))
    
    def toXML(self):
        if self.origin_note:
            return "\t\t\t<source file=\"%s\" startline=\"%d\" endline=\"%d\" function=\"%s\" hash=\"%d\"></source>\n" % (self.file, self.ls, self.le,self.function_name, self.function_hash)
        if self.death_note:
            return "\t\t\t<source file=\"%s\" startline=\"%d\" endline=\"%d\" function=\"%s\" hash=\"%d\" death_note=\"%s\"></source>\n" % (self.file, self.ls, self.le,self.function_name, self.function_hash, self.death_note)
        if self.move_note:
            return "\t\t\t<source file=\"%s\" startline=\"%d\" endline=\"%d\" function=\"%s\" hash=\"%d\" move_note=\"%s\"></source>\n" % (self.file, self.ls, self.le,self.function_name, self.function_hash, self.move_note)
        # if self.evolution_note:
            # return "\t\t\t<source file=\"%s\" startline=\"%d\" endline=\"%d\" function=\"%s\" hash=\"%d\" evolution_note=\"%s\"></source>\n" % (self.file, self.ls, self.le,self.function_name, self.function_hash, self.evolution_note)

        return "\t\t\t<source file=\"%s\" startline=\"%d\" endline=\"%d\" function=\"%s\" hash=\"%d\"></source>\n" % (self.file, self.ls, self.le,self.function_name, self.function_hash)

    def countLOC(self):
        return (self.le - self.ls)

class CloneClass():
    def __init__(self):
        self.fragments = []

    def contains(self, fragment):
        for f in self.fragments:
            if f.matches(fragment):
                return True
        return False

    def matches(self, cc):
        n = 0
        for fragment in cc.fragments:
            if self.contains(fragment):
                n+=1
        return (n == len(cc.fragments)) or (n == len(self.fragments))

    def toXML(self):
        s = "\t\t<class nclones=\"%d\">\n" % (len(self.fragments))
        for fragment in self.fragments:
            try:
                s += fragment.toXML()
            except:
                pass
        s += "\t\t</class>\n"
        return s

    def countLOC(self):
        count = 0
        for fragment in self.fragments:
            count += fragment.countLOC()
        return count

class CloneVersion():
    def __init__(self, cc = None, h = None, n = None, evo = "None", chan = "None", origin=False, move = False):
        self.cloneclass = cc
        self.hash = h
        self.parent_hash = ""
        self.nr = n
        self.evolution_pattern = evo
        self.change_pattern = chan
        self.origin = origin
        self.move = move
        self.clone_death = None
        self.removed_fragments = []

    def toXMLRemoved(self):
        for f in self.removed_fragments:
            s += f.toXML()
        return s

    def toXML(self):
        if self.origin:
            # code_types = [analyze_method_change(REPO_DIR, fragment.file, fragment.ls, fragment.le, self.hash) for fragment in self.cloneclass.fragments]
            # origin_type = analyze_snippets(code_types)
            s = "\t<version nr=\"%d\" hash=\"%s\" evolution=\"%s\" change=\"%s\" origin=\"True\">\n" % (self.nr, self.hash, self.evolution_pattern, self.change_pattern)
        elif self.clone_death:
            s = "\t<version nr=\"%d\" death=\"True\">\n" % (self.nr)
        elif "Add" in self.evolution_pattern:
            s = "\t<version nr=\"%d\" hash=\"%s\" evolution=\"%s\" change=\"%s\" parent_hash=\"%s\">\n" % (self.nr, self.hash, self.evolution_pattern, self.change_pattern, self.parent_hash)
        else:
            s = "\t<version nr=\"%d\" hash=\"%s\" evolution=\"%s\" change=\"%s\" move=\"%s\" parent_hash=\"%s\">\n" % (self.nr, self.hash, self.evolution_pattern, self.change_pattern, self.move, self.parent_hash)

        try:
            s += self.cloneclass.toXML()
        except:
            pass
        s += "\t</version>\n"

        if self.removed_fragments != []:
            s += self.toXMLRemoved()
        return s

class Lineage():
    def __init__(self):
        self.versions = []

    def matches(self, cc):
        for fragment in cc.fragments:
            if self.versions[-1].cloneclass.contains(fragment):
                return True
        return False

    def toXML(self):
        s = "<lineage>\n"
        for version in self.versions:
            s += version.toXML()
        s += "</lineage>\n"
        return s

def getLastCommitFromDensityCSV(filename):
    try:
        with open(filename, 'r+') as file:
            return int(file.readlines()[-1].split(",")[0])
    except Exception as e:
        printError("Something went wrong while parsing the density dataset:")
        printError(str(e))
        return 0

def getDataFromCSV(filename):
    try:
        with open(filename, 'r+') as file:
            data = []
            for line in file.readlines():
                data.append((int(line.split(",")[0]), float(line.split(",")[1]), float(line.split(",")[2])))
            return data
    except Exception as e:
        printError("Something went wrong while parsing the CSV file:")
        printError(str(e))
        return 0

def parseLineageFile(filename):
    lineages = []
    with open(filename, 'r+') as file:
        # try to parse the xml file
        try:
            file_xml = etree.parse(file)
            # transform each pair in python objects for easy comparison
            for lineage in file_xml.getroot():
                lin = Lineage()
                versions = lineage.getchildren()
                for version in versions:
                    cc = CloneClass()
                    cloneclasses = version.getchildren()
                    if len(cloneclasses) != 1:
                        printWarning("Unexpected amount of clone classes in version.")
                        printWarning("Please check if inputfile is consistent.")
                    for fragment in cloneclasses[0].getchildren():
                        cc.fragments.append(CloneFragment(fragment.get("file"), int(fragment.get("startline")), int(fragment.get("endline")), fragment.get("function"), int(fragment.get("hash"))))
                    cv = CloneVersion(cc, version.get("hash"), int(version.get("nr")), version.get("evolution"), version.get("change"))
                    lin.versions.append(cv)
                lineages.append(lin)
        except Exception as e:
            printError("Something went wrong while parsing the lineage dataset:")
            printError(str(e))
            return []
    return lineages

def _read_text_with_fallback(path):
    with open(path, 'rb') as f:
        data = f.read()
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    # Último recurso: ignora bytes inválidos em UTF-8
    return data.decode('utf-8', errors='ignore')

def GetCloneFragment(filename, startline, endline):
    text = _read_text_with_fallback(filename)

    lines_out = [""]
    remove_ws = False

    for i, raw in enumerate(text.splitlines(True)):  # i é 0-based
        if i >= (startline - 1):
            base = raw.split("//", 1)[0]  # remove comentários de fim de linha
            if base.strip() == "":        # pula linhas apenas com comentário/espacos
                continue

            l = base.rstrip()             # tira espaços à direita

            if remove_ws:
                l = l.lstrip()            # desindenta a linha "continuada"
                remove_ws = False

            # Se a linha parece "quebrada", marcar para desindentar a próxima
            if len(l) > 2 and l[-1] not in ";{":
                remove_ws = True
            else:
                l = l + "\n"              # caso contrário, garante newline

            lines_out.append(l)

        if i >= (endline - 1):
            break

    return "".join(lines_out)

def GetPattern(v1, v2):
    evolution = "None"
    if len(v1.fragments) == len(v2.fragments):
        evolution = "Same"
    elif len(v1.fragments) > len(v2.fragments):
        evolution = "Subtract"
    else:
        evolution = "Add"

    change = "None"
    if evolution == "Same" or evolution == "Subtract":
        nr_of_matches = 0
        for f2 in v2.fragments:
            for f1 in v1.fragments:
                if f1.function_hash == f2.function_hash:
                    nr_of_matches += 1
                    break
        if nr_of_matches == len(v2.fragments):
            change = "Same"
        elif nr_of_matches == 0:
            change = "Consistent"
        else:
            change = "Inconsistent"
    elif evolution == "Add":
        nr_of_matches = 0
        for f1 in v1.fragments:
            for f2 in v2.fragments:
                if f1.function_hash == f2.function_hash:
                    nr_of_matches += 1
                    break
        if nr_of_matches == len(v1.fragments):
            change = "Same"
        elif nr_of_matches == 0:
            change = "Consistent"
        else:
            change = "Inconsistent"

    return (evolution, change)
    
def SetupRepo():
    print("Setting up workspace for git repository " + GIT_URL)
    # Check if the workspace, repo, and .git directories exist
    if os.path.exists(WS_DIR) and os.path.exists(REPO_DIR) and os.path.exists(REPO_DIR + "/.git"):
        # Check if the current repo is the correct repo
        current_url = os.popen('git --git-dir workspace/repo/.git config --get remote.origin.url').read()
        if GIT_URL in current_url:
            print("The requested repo is already present.\n Repository setup complete.\n")
            return
        else:
            printWarning("Incorrect repo found:\n\t" + current_url)
            print(" > Clearing workspace...")
            os.system('rm -rf ' + WS_DIR) # Clean workspace
    os.system('mkdir ' + WS_DIR) # Make directory for workspace
    os.system('mkdir ' + REPO_DIR) # Make directory for REPO
    os.system('git clone ' + GIT_URL + ' ' + REPO_DIR) # Clone REPO
    print(" Repository setup complete.\n")

def PrepareGitHistory(days: int):
    print("Getting git history")
    repo = Repo(REPO_DIR)
    now = datetime.now()

    # Parâmetros comuns para o iter_commits
    iter_kwargs = {}

    # Se quiser apenas merges, pedimos merges ao git.
    # Além disso, filtramos por segurança (caso a versão do GitPython ignore o flag).
    if USE_MERGE_COMMITS:
        iter_kwargs["merges"] = True

    # Seleção da janela de commits
    if ALL_COMMITS:
        # Todo o histórico
        commits = repo.iter_commits(**iter_kwargs)

    elif FROM_BEGIN:
        # Do início até "now - days"
        until = now - timedelta(days=days)
        commits = repo.iter_commits(until=until.isoformat(), **iter_kwargs)

    else:
        # Dos últimos "days"
        since = now - timedelta(days=days)
        commits = repo.iter_commits(since=since.isoformat(), **iter_kwargs)

    # Filtro extra de segurança para merges (caso o parâmetro 'merges' não seja suportado)
    if USE_MERGE_COMMITS:
        commits = (c for c in commits if len(c.parents) > 1)

    lines = [
        f"{c.hexsha[:7]} {datetime.fromtimestamp(c.committed_date).date()} {c.author.name} {c.summary}"
        for c in commits
    ]

    Path(HIST_FILE).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(lines)} commit(s) to {HIST_FILE}")

def GetHashes():
    hashes = []
    with open(HIST_FILE, "rb") as fp:  # binary mode avoids text-decoding the whole line
        for raw in fp:
            raw = raw.strip()
            if not raw:
                continue
            first = raw.split(None, 1)[0]  # bytes up to first whitespace
            try:
                h = first.decode("ascii")   # commit hashes are ASCII hex
            except UnicodeDecodeError:
                continue                     # skip malformed lines just in case
            hashes.append(h)
    hashes.reverse()
    return hashes

def PrepareSourceCode():
    print("Preparing source code")
    exists_java_file = False

    # Remove o diretório DATA_DIR se já existir
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)

    os.makedirs(DATA_DIR, exist_ok=True)       # Cria o dataset directory
    os.makedirs(PROD_DATA_DIR, exist_ok=True)  # Cria o production code directory

    # Copia todos os arquivos de produção preservando a estrutura de diretórios
    for root, dirs, files in os.walk(REPO_DIR):
        for file in files:
            if file.endswith('.' + LANGUAGE) and 'test' not in os.path.join(root, file).lower():
                src_path = os.path.join(root, file)
                
                # recria a estrutura relativa ao REPO_DIR
                rel_path = os.path.relpath(root, REPO_DIR)
                dst_dir = os.path.join(PROD_DATA_DIR, rel_path)
                os.makedirs(dst_dir, exist_ok=True)

                dst_path = os.path.join(dst_dir, file)
                shutil.copy2(src_path, dst_path)
                exists_java_file = True

    print("Source code ready for clone analysis.\n")

    return exists_java_file

def StartFromPreviousVersion():
    # Check if the results directory exists
    if not os.path.exists(RES_DIR):
        os.system('mkdir ' + RES_DIR)
        return 0
    elif os.path.exists(P_RES_FILE) and os.path.exists(P_DENS_FILE) and os.path.exists(T_RES_FILE) and os.path.exists(T_DENS_FILE):
        printInfo("Previous version found.\n")

        print(" Importing data from " + P_RES_FILE)
        global P_LIN_DATA
        P_LIN_DATA = parseLineageFile(P_RES_FILE)
        if not len(P_LIN_DATA):
            printError("Empty production data: no linages found in " + P_RES_FILE)
            return -1

        print(" Importing data from " + T_RES_FILE)
        global T_LIN_DATA
        T_LIN_DATA = parseLineageFile(T_RES_FILE)
        if not len(T_LIN_DATA):
            printError("Empty production data: no linages found in " + T_RES_FILE)
            return -1

        print(" Importing data from " + P_DENS_FILE)
        global P_DENS_DATA
        P_DENS_DATA = getDataFromCSV(P_DENS_FILE)
        if not len(P_DENS_DATA):
            printError("Empty production data: no density evolution found in " + P_DENS_FILE)
            return -1

        printInfo("  >> Resuming data collection from last version.\n")
        return P_DENS_DATA[-1][0]

    return 0

def parse_clones_xml(xml_input: Union[str, bytes]) -> Dict[str, Any]:
    # Decide whether xml_input is a path or an XML string
    if isinstance(xml_input, (bytes,)):
        root = ET.fromstring(xml_input)
    elif isinstance(xml_input, str) and (xml_input.strip().startswith("<") or "\n" in xml_input):
        root = ET.fromstring(xml_input)
    else:
        # treat as a file path
        if not os.path.exists(xml_input):
            raise FileNotFoundError(f"XML file not found: {xml_input}")
        tree = ET.parse(xml_input)
        root = tree.getroot()

    if root.tag != "clones":
        raise ValueError(f"Unexpected root tag '{root.tag}', expected 'clones'.")

    result: Dict[str, List[Dict[str, Any]]] = {"clones": []}

    for class_el in root.findall("class"):
        class_dict = {"sources": []}
        for src in class_el.findall("source"):
            # Read attributes and cast line numbers to int
            file_path = src.get("file")
            startline = int(src.get("startline")) if src.get("startline") is not None else None
            endline = int(src.get("endline")) if src.get("endline") is not None else None

            class_dict["sources"].append(
                {
                    "file": file_path,
                    "startline": startline,
                    "endline": endline,
                }
            )
        result["clones"].append(class_dict)

    return result

# padrão simples: "<nome>(<params>) {"
SIG_RE = re.compile(r'\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{')

def find_decl_line(lines, startline):
    CONTROL = {"if", "for", "while", "switch", "catch", "try", "do", "else", "synchronized"}
    n = len(lines)

    def strip_inline_comments(s: str) -> str:
        # remove // e pares /* ... */ que estejam na mesma linha
        s = s.split("//", 1)[0]
        while "/*" in s and "*/" in s and s.find("/*") < s.find("*/"):
            a, b = s.find("/*"), s.find("*/") + 2
            s = s[:a] + s[b:]
        return s

    i = min(max(1, startline), n)  # 1..n
    i -= 1  # 0-based cursor

    # Sobe procurando uma linha com '{' que faça parte da assinatura
    while i >= 0:
        # Considera até 3 linhas acima para capturar assinaturas quebradas
        top = max(0, i - 2)
        window_lines = [strip_inline_comments(lines[k]) for k in range(top, i + 1)]
        joined = " ".join(window_lines)

        # precisa ter '{' e '(' na janela, e '(' antes de '{'
        brace_pos_joined = joined.rfind("{")
        lpar_pos_joined = joined.rfind("(")
        if brace_pos_joined != -1 and lpar_pos_joined != -1 and lpar_pos_joined < brace_pos_joined:
            # extrai o nome imediatamente antes do '('
            k = lpar_pos_joined - 1
            while k >= 0 and joined[k].isspace():
                k -= 1
            end = k
            while k >= 0 and (joined[k].isalnum() or joined[k] in "_$"):
                k -= 1
            name = joined[k + 1:end + 1]

            # valida nome (não ser controle e começar por letra/_/$)
            if name and name not in CONTROL and (name[0].isalpha() or name[0] in "_$"):
                # Coluna real do '{' na última linha da janela (linha i)
                last_line = strip_inline_comments(lines[i])
                brace_col = last_line.rfind("{")
                if brace_col == -1:
                    # '{' está numa das linhas acima; ajusta iterando de trás pra frente
                    brace_col = 0
                    for j in range(i, top - 1, -1):
                        tmp = strip_inline_comments(lines[j])
                        pos = tmp.rfind("{")
                        if pos != -1:
                            i = j  # declaração está nesta linha
                            brace_col = pos
                            break
                return name, i + 1, brace_col  # (1-based, 0-based)

        i -= 1

    return None, None, None

def find_method_end(lines, decl_line, brace_col):
    depth = 0
    for li in range(decl_line - 1, len(lines)):
        line = lines[li].split("//", 1)[0]
        start_c = brace_col if li == decl_line - 1 else 0
        for cj in range(start_c, len(line)):
            ch = line[cj]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return li + 1  # 1-based
    return None

def expand_sources(join_all_clones):
    cache = {}
    final_out = []
    for clone_group_by_clone_detector in join_all_clones:
        final_sources = []
        for clone_group in clone_group_by_clone_detector['clones']:
            out = []
            for s in clone_group['sources']: 
                if '/' == s['file'][0]:
                    s['file'] = s['file'][1:] 
                fp = s['file']
                if fp not in cache:
                    cache[fp] = Path(fp).read_text(encoding='utf-8').splitlines(True)
                lines = cache[fp]

                name, decl_line, brace_col = find_decl_line(lines, int(s['startline']))
                
                if name == 'if':
                    print()
                    
                if not name:
                    continue

                end_line = find_method_end(lines, decl_line, brace_col) or s['endline']
                out.append({
                    'file': fp,
                    'method': name,            # <<<< nome do método
                    'startline': decl_line,    # início real do método
                    'endline': end_line,        # fim real do método
                    'hash': hash(f'{fp}{name}{decl_line}{end_line}')
                })

            if len(out) == 1:
                print("")
            final_sources.append({'sources': out})
        final_out.append({'clones': final_sources})
    return final_out

def join_clone_detectors_result():
    results_path = 'clone_detector_result'
    results_path = [f'{results_path}/{xml_result}' for xml_result in os.listdir(results_path)]
    results_dict = []
    for xml_path in results_path:
      xml_txt = open(xml_path, 'r').read()
      xml_txt = xml_txt.replace(os.getcwd(), '')
      results_dict.append(parse_clones_xml(xml_txt))

    results_dict = expand_sources(results_dict)
    generate_clones_xml(results_dict)

def RunCloneDetection():
    print("Starting clone detection:")

    clone_detector_result = Path("clone_detector_result")
    for item in clone_detector_result.iterdir():
        if item.is_file():
            item.unlink()

    if len(CLONE_DETECTOR_TOOL) > 1:
        print(" >>> Running nicad6...")
        os.system('cd ' + TOOLS_DIR + '/NiCad && ./nicad6 functions ' + LANGUAGE + ' ../../' + PROD_DATA_DIR)

        NICAD_XML = PROD_DATA_DIR + '_functions-clones/production_functions-clones-0.30-classes.xml'
        shutil.move(NICAD_XML, 'clone_detector_result/nicad-result.xml')

        # Clean up
        os.system('rm -rf ' + PROD_DATA_DIR + '_functions-clones')
        os.system('rm ' + DATA_DIR + '/*.log')
        new_xml_data = open('clone_detector_result/nicad-result.xml', 'r').read().replace('../../', '')
        open('clone_detector_result/nicad-result.xml', 'w').write(new_xml_data)

        print(" >>> Running Simian...")
        java_jar_command = 'java -jar ./tools/simian/simian-4.0.0.jar'
        options_command = '-formatter=xml -threshold=4'
        simian_command = f'{java_jar_command} {options_command} {PROD_DATA_DIR}/*.{LANGUAGE} > clone_detector_result/simian-result.xml'

        os.system(simian_command)
        parse_simian_to_clones('clone_detector_result/simian-result.xml')
        join_clone_detectors_result()
        return

    if "Nicad" in CLONE_DETECTOR_TOOL:
        print(" >>> Running nicad6...")
        os.system('mkdir ' + CUR_RES_DIR)
        os.system('cd ' + TOOLS_DIR + '/NiCad && ./nicad6 functions ' + LANGUAGE + ' ../../' + PROD_DATA_DIR)

        NICAD_XML = PROD_DATA_DIR + '_functions-clones/production_functions-clones-0.30-classes.xml'
        shutil.move(NICAD_XML, CLONE_DETECTOR_XML)

        # Clean up
        os.system('rm -rf ' + PROD_DATA_DIR + '_functions-clones')
        os.system('rm ' + DATA_DIR + '/*.log')
        new_xml_data = open(CLONE_DETECTOR_XML, 'r').read().replace('../../', '')
        open(CLONE_DETECTOR_XML, 'w').write(new_xml_data)
        join_clone_detectors_result()
        return

    if "Simian" in CLONE_DETECTOR_TOOL:
        print(" >>> Running Simian...")
        java_jar_command = 'java -jar ./tools/simian/simian-4.0.0.jar'
        options_command = '-formatter=xml -threshold=4'
        simian_command = f'{java_jar_command} {options_command} {PROD_DATA_DIR}/*.{LANGUAGE} > {CLONE_DETECTOR_XML}'

        os.system(simian_command)
        parse_simian_to_clones('clone_detector_result/result.xml')
        join_clone_detectors_result()
        return

    folder_result = Path("clone_detector_result")
    for f in folder_result.iterdir():
        if f.is_file():
            f.unlink()  # apaga o arquivo

    print(" Finished clone detection.\n")

def parseCloneClassFile(cloneclass_filename):
    print(cloneclass_filename)
    cloneclasses = []
    try:
        file_xml = ET.parse(cloneclass_filename)
        root = file_xml.getroot()

        for child in root:  # cada "cloneclass"
            cc = CloneClass()
            fragments = list(child)  # <- substitui getchildren()
            if not fragments:
                continue

            for fragment in fragments:
                file_path = fragment.get("file")
                startline = int(fragment.get("startline"))
                endline = int(fragment.get("endline"))
                cf = CloneFragment(file_path, startline, endline)
                # evita KeyError se não existir a chave exata
                cf.function_name = get_enclosing_method_name(file_path, startline, endline)
                # se o caminho sempre tem um prefixo a remover, mantenha o [3:] — caso contrário, remova
                cf.function_hash = hash(GetCloneFragment(cf.file, cf.ls, cf.le))

                cc.fragments.append(cf)

            cloneclasses.append(cc)

    except Exception as e:
        printError("Something went wrong while parsing the nicad clonepair dataset:")
        raise e

    return cloneclasses

def CheckDoubleMatch(cc_original, cc1, cc2):
    cc1_strict_match = False
    cc2_strict_match = False
    for fragment in cc_original.fragments:
        for f1 in cc1.fragments:
            if fragment.matchesStrictly(f1):
                cc1_strict_match = True
        for f2 in cc2.fragments:
            if fragment.matchesStrictly(f2):
                cc2_strict_match = True

    if cc1_strict_match == cc2_strict_match:
        return 0
    if cc1_strict_match:
        return 1
    elif cc2_strict_match:
        return 2
    return 0

def RunDensityAnalysis(commitNr,  pcloneclasses):
    print("Starting density analysis:")
    print(" > Production code...")
    total_amount_of_p_functions = int(os.popen('grep "/source" ' + CUR_RES_DIR + '/production_functions.xml | wc -l').read())
    amount_of_cloned_p_functions = int(os.popen('grep "/source" ' + CUR_RES_DIR + '/production_functions-clones-0.30-classes.xml | wc -l').read())
    density_f_p = 100 * (float(amount_of_cloned_p_functions) / total_amount_of_p_functions)

    cloc_p_out = os.popen('perl tools/cloc/cloc-1.72.pl workspace/dataset/production/ | grep "SUM"').read().split()
    total_amount_of_p_loc = int(cloc_p_out[-1]) + int(cloc_p_out[-2]) + int(cloc_p_out[-3])
    amount_of_cloned_p_loc = 0
    for cloneclass in pcloneclasses:
        amount_of_cloned_p_loc += cloneclass.countLOC()
    density_loc_p = 100 * (float(amount_of_cloned_p_loc) / total_amount_of_p_loc)

    P_DENS_DATA.append((commitNr, density_f_p, density_loc_p))
    print(" Finished density analysis.\n")

def RunGenealogyAnalysis(commitNr, hash):
    print("Starting genealogy analysis:")
    print(" > Production code...")
    pcloneclasses = parseCloneClassFile(CLONE_DETECTOR_XML)
    if not P_LIN_DATA: # If there is no lineage data for production yet
        for pcc in pcloneclasses:
            v = CloneVersion(pcc, hash, commitNr)
            l = Lineage()
            l.versions.append(v)
            P_LIN_DATA.append(l)
    else:
        for pcc in pcloneclasses:
            found = False
            for lineage in P_LIN_DATA: # Search for the lineage this cloneclass is part of
                if lineage.matches(pcc):

                    if lineage.versions[-1].nr == commitNr: # special case: another clone class has already been matched in this commit
                        if (len(lineage.versions) < 2):
                            continue
                        checkDoubleMatch = CheckDoubleMatch(lineage.versions[-2].cloneclass, lineage.versions[-1].cloneclass, pcc)
                        if checkDoubleMatch == 1:
                            continue
                        elif checkDoubleMatch == 2:
                            pcloneclasses.append(lineage.versions[-1].cloneclass)
                            lineage.versions.pop()

                    evolution, change = GetPattern(lineage.versions[-1].cloneclass, pcc)
                    if evolution == "Same" and change == "Same" and lineage.versions[-1].evolution_pattern == "Same" and lineage.versions[-1].change_pattern == "Same":
                        lineage.versions[-1].nr = commitNr
                        lineage.versions[-1].hash = hash
                    else:
                        lineage.versions.append(CloneVersion(pcc, hash, commitNr, evolution, change))
                    found = True
                    break
            if not found: # There is no lineage yet for this cloneclass, start a new lineage
                v = CloneVersion(pcc, hash, commitNr)
                l = Lineage()
                l.versions.append(v)
                P_LIN_DATA.append(l)

    print(" Finished genealogy analysis.\n")

    # Run clone density analysis
    # RunDensityAnalysis(commitNr, pcloneclasses)
    
def WriteLineageFile(lineages, filename):
    output_file = open(filename, "w+")
    output_file.write("<lineages>\n")
    for lineage in lineages:
        output_file.write(lineage.toXML())
    output_file.write("</lineages>\n")
    output_file.close()

def WriteDensityFile(densitys, filename):
    output_file = open(filename, "w+")
    for density in densitys:
        output_file.write(str(density[0]) + ', ' + str(density[1]) + ', ' + str(density[2]) + '\n')
    output_file.close()

def timeToString(seconds):
    result = ""
    hours=seconds//3600
    minutes=(seconds%3600)//60
    seconds=(seconds%3600)%60
    if (hours):
        result += str(hours) + " hours, "
    if (minutes):
        result += str(minutes) + " minutes, "
    result += str(seconds) + " seconds"
    return result

def insert_parent_hash(hash_index, parent_hash):
    for lineage in P_LIN_DATA:
        lineage.versions[-1].parent_hash = parent_hash

def main():
    print("STARTING DATA COLLECTION SCRIPT\n")
    SetupRepo()
    PrepareGitHistory(DAYS)
    hashes = GetHashes()
    time.sleep(1)

    start = StartFromPreviousVersion()
    if start < 0:
        return
    elif start > 0:
        start += COMMIT_INTERVAL
    analysis_index = 0
    total_time = 0

    if USE_INTERVAL:
        range_hash = range(start, len(hashes), COMMIT_INTERVAL)
    else:
        range_hash = range(start, len(hashes))
    
    if USE_MAX_COMMITS:
        range_hash = range_hash[:MAX_COMMITS]

    for hash_index in range_hash:
        iteration_start_time = time.time()
        analysis_index += 1

        current_hash = hashes[hash_index]
        hash_index += 1

        printInfo('Analyzing commit nr.' + str(hash_index) + ' with hash '+ current_hash)
        global CUR_RES_DIR
        CUR_RES_DIR = RES_DIR + "/" + str(hash_index) + '_' + current_hash

        # Check if maximum number of commits has been analyzed
        if analysis_index > MAX_COMMITS and USE_MAX_COMMITS:
            printInfo('Maximum amount of commits has been analyzed. Ending data collection...')
            break

        # Checkout current hash
        if not current_hash in os.popen('git --git-dir workspace/repo/.git show --oneline -s').read():
            os.system('(cd ' + REPO_DIR +'; git checkout ' + current_hash + ' -f > /dev/null 2>&1)')
            time.sleep(1)

        # Run clone detection on current hash
        find_files = PrepareSourceCode()
        if not find_files:
            continue

        if hash_index == 5:
            print("")

        RunCloneDetection()
        RunGenealogyAnalysis(hash_index, current_hash)
        WriteLineageFile(P_LIN_DATA, P_RES_FILE)

        if hash_index != 1:
            insert_parent_hash(hash_index, hashes[hash_index - 2])
        
        # Clean-up
        os.system('rm -rf ' + CUR_RES_DIR)
        # time
        iteration_end_time = time.time()
        iteration_time = iteration_end_time - iteration_start_time
        total_time += iteration_time
        print("Iteration finished in " + timeToString(int(iteration_time)))
        print(" >>> Average iteration time: " + timeToString(int(total_time/analysis_index)))
        if USE_MAX_COMMITS:
            print(" >>> Estimated remaining time: " + timeToString(int((total_time/analysis_index)*(len(range_hash)-analysis_index))))
        else:
            print(" >>> Estimated remaining time: " + timeToString(int((total_time/analysis_index)*(MAX_COMMITS-analysis_index))))

        WriteLineageFile(P_LIN_DATA, P_RES_FILE)
        time.sleep(1)

    # Write Lineage Data to Files
    WriteLineageFile(P_LIN_DATA, P_RES_FILE)
    WriteDensityFile(P_DENS_DATA, P_DENS_FILE)
    print("\nDONE")

if __name__ == "__main__":
    os.system(f'rm -rf {RES_DIR} && rm -rf {DATA_DIR} && rm -rf {HIST_FILE} && rm -rf {REPO_DIR}')
    main()
