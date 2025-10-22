from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import os
import difflib
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def generate_clones_xml(data: Dict[str, Any],
                        encoding: str = "utf-8",
                        indent: int = 2,
                        xml_declaration: bool = True) -> str:

    data = find_equal_classes(data)
    root = Element("clones")

    for cls in data.get("clones", []):
        class_el = SubElement(root, "class")
        for src in cls.get("sources", []):
            attrs = {"file": str(src.get("file", ""))}
            sl: Optional[int] = src.get("startline")
            el: Optional[int] = src.get("endline")
            if sl is not None:
                attrs["startline"] = str(sl)
            if el is not None:
                attrs["endline"] = str(el)
            attrs["method_name"] = str(src.get("method"))
            attrs["hash"] = str(src.get("hash"))
            SubElement(class_el, "source", attrs)

    raw = tostring(root, encoding=encoding)
    pretty = minidom.parseString(raw).toprettyxml(indent=" " * indent, encoding=encoding)

    if not xml_declaration:
        return pretty.decode(encoding).split("\n", 1)[1]
    

    clone_detector_result = Path("clone_detector_result")
    for item in clone_detector_result.iterdir():
        if item.is_file():
            item.unlink()

    open('clone_detector_result/result.xml', 'w').write(pretty.decode(encoding))

from typing import Any, Dict, List

def _dedupe_sources_by_hash(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = {}
    for s in sources or []:
        h = s.get("hash")
        if h not in seen:
            seen[h] = dict(s)
            seen[h]["hash"] = h  # garante presença
    return list(seen.values())

def find_equal_classes(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: List[Dict[str, Any]] = []
    merged_sets: List[set] = []  # conjunto de hashes correspondente ao merged[i]

    # Itera sobre a estrutura de entrada (lista de exemplos com "clones")
    for ex in examples or []:
        for cls in ex.get("clones", []):
            # 1) dedupe interno
            norm_sources = _dedupe_sources_by_hash(cls.get("sources", []))
            S = {s["hash"] for s in norm_sources}

            if not S:
                continue

            # 2) tenta unificar com grupos existentes
            equal_idx = None
            supersets = []  # índices de grupos existentes que são superset de S
            subsets = []    # índices de grupos existentes que são subset de S

            for i, H in enumerate(merged_sets):
                if H == S:
                    equal_idx = i
                    break
                if H.issuperset(S):
                    supersets.append(i)
                elif H.issubset(S):
                    subsets.append(i)

            if equal_idx is not None:
                # Mesmo conjunto: apenas garante que todos os sources existam (e enriquece se for o caso)
                by_hash = {s["hash"]: s for s in merged[equal_idx]["sources"]}
                for s in norm_sources:
                    by_hash.setdefault(s["hash"], s)
                merged[equal_idx]["sources"] = list(by_hash.values())
                continue

            if supersets:
                # Já existe um grupo que contém todos esses hashes -> adiciona quaisquer membros faltantes nele
                i = supersets[0]  # qualquer superset serve
                by_hash = {s["hash"]: s for s in merged[i]["sources"]}
                for s in norm_sources:
                    by_hash.setdefault(s["hash"], s)
                merged[i]["sources"] = list(by_hash.values())
                merged_sets[i] = {s["hash"] for s in merged[i]["sources"]}
                continue

            if subsets:
                # S é um superset de um ou mais grupos existentes -> faz união em um deles e remove os demais subsets
                i_base = subsets[0]
                by_hash = {s["hash"]: s for s in merged[i_base]["sources"]}
                for s in norm_sources:
                    by_hash.setdefault(s["hash"], s)
                merged[i_base]["sources"] = list(by_hash.values())
                merged_sets[i_base] = {s["hash"] for s in merged[i_base]["sources"]}

                # Remove outros subsets (já absorvidos)
                for j in sorted(subsets[1:], reverse=True):
                    del merged[j]
                    del merged_sets[j]
                continue

            # 3) caso não tenha relação de igualdade/subconjunto/superset, vira um grupo novo
            merged.append({"sources": norm_sources})
            merged_sets.append(S)

    # Normaliza saída (pode ordenar fontes por algo estável, ex.: file, startline)
    for g in merged:
        g["sources"].sort(key=lambda s: (str(s.get("file","")), int(s.get("startline", 0)), str(s.get("method","")), str(s.get("hash",""))))

    return {"clones": merged}
