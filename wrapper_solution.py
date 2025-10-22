from typing import List
import git

def analyze_snippets(snippets: List[str]) -> str:
    if len(snippets) < 2:
        raise ValueError("The list must have at least 2 elements.")
    
    if snippets.count("No Change") == 1 and snippets.count("Complete Method") == len(snippets) - 1:
        return "type-1"
    if snippets.count("No Change") == 1 and snippets.count("Modify Method") == len(snippets) - 1:
        return "type-2"
    if snippets.count("No Change") == 0 and snippets.count("Complete Method") >= 1 and snippets.count("Modify Method") >= 1:
        return "type-3"
    if snippets.count("Complete Method") >= len(snippets):
        return "type-4"
    if snippets.count("Modify Method") >= len(snippets):
        return "type-5"
    if snippets.count("No Change") >= 1 and snippets.count("Complete Method") >= 1 and snippets.count("Modify Method") >= 1:
        return "type-6"
    return "Unclassified"

def analyze_method_change(repo_path: str, file_path: str, start_line: int, end_line: int, commit_hash: str) -> str:
    file_path = file_path.replace('../../', './').replace('workspace/dataset/production', repo_path)
    
    try:
        repo = git.Repo(repo_path)
        commit = repo.commit(commit_hash)

        # Se não há commit pai, significa que é o commit inicial (arquivo novo)
        if not commit.parents:
            return "Complete Method"

        parent = commit.parents[0]

        def get_file_content(commit, path: str):
            """Retorna o conteúdo de um arquivo em um commit específico, ou None se não existir."""
            try:
                blob = commit.tree / path.replace('./workspace/repo/', '')
                return blob.data_stream.read().decode('utf-8', errors='ignore')
            except KeyError:
                return None

        # Lê o conteúdo do arquivo no commit atual e no commit pai
        current_content = get_file_content(commit, file_path)
        parent_content = get_file_content(parent, file_path)

        # Se o arquivo não existe no commit atual → foi removido
        if current_content is None:
            return "Modified Method"

        # Extrai as linhas do método (atual)
        current_method_lines = current_content.splitlines()[start_line - 1:end_line]

        # Extrai as linhas do método (pai), se o arquivo existia
        parent_method_lines = []
        if parent_content is not None:
            parent_method_lines = parent_content.splitlines()[start_line - 1:end_line]

        # Caso 1: método não existia antes e agora existe
        if not parent_method_lines and current_method_lines:
            return "Complete Method"

        # Caso 2: método existia e mudou
        if parent_method_lines != current_method_lines:
            return "Modified Method"

        # Caso 3: método não mudou
        return "No Change"

    except (git.exc.GitCommandError, KeyError, IndexError) as e:
        print(f"An error occurred: {e}")
        return "Modified Method"
