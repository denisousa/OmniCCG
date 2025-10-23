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
    # junta todas as sources de todos os exemplos
    all_classes = []
    for ex in examples or []:
        for cls in ex.get("clones", []):
            norm_sources = _dedupe_sources_by_hash(cls.get("sources", []))
            if norm_sources:
                all_classes.append(norm_sources)

    # Grafo: nós = hashes, arestas = aparecerem juntos numa mesma classe
    from collections import defaultdict, deque
    adj = defaultdict(set)
    hash_to_source = {}

    for cls in all_classes:
        hashes = [s["hash"] for s in cls]
        for s in cls:
            hash_to_source[s["hash"]] = s
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                adj[hashes[i]].add(hashes[j])
                adj[hashes[j]].add(hashes[i])

    visited = set()
    groups = []
    for h in hash_to_source:
        if h in visited:
            continue
        # BFS/DFS para coletar componente
        comp = []
        q = deque([h])
        visited.add(h)
        while q:
            cur = q.popleft()
            comp.append(hash_to_source[cur])
            for nei in adj[cur]:
                if nei not in visited:
                    visited.add(nei)
                    q.append(nei)
        groups.append({"sources": comp})

    # ordena fontes dentro de cada grupo
    for g in groups:
        g["sources"].sort(
            key=lambda s: (
                str(s.get("file", "")),
                int(s.get("startline", 0)),
                str(s.get("method", "")),
                str(s.get("hash", "")),
            )
        )

    return {"clones": groups}
