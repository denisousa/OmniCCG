from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import Counter
from dataclasses import dataclass
from typing import List, Tuple

# --- Configure your label mapping here (case-insensitive) ---
CONSISTENT_CHANGE_LABELS = {"same", "consistent"}
INCONSISTENT_CHANGE_LABELS = {"inconsistent", "different", "conflict", "conflicting", "diverged"}

@dataclass
class LineageInfo:
    first_nr: int
    last_nr: int
    age_versions: int
    is_dead: bool
    change_labels: List[str]  # raw change labels for the lineage (per version)

def _norm(s: str) -> str:
    return (s or "").strip()

def _lower(s: str) -> str:
    return _norm(s).lower() if s is not None else ""

def _pretty_xml(elem) -> str:
    raw = ET.tostring(elem, encoding="utf-8")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

def fmt2(x) -> str:
    """Format any numeric value to a string with two decimal places."""
    try:
        return f"{float(x):.2f}"
    except Exception:
        return str(x)

def parse_lineages(xml_text: str, last_version: int) -> Tuple[List[LineageInfo], List[str], List[str]]:
    """
    Parse o XML de linhagens e computa, para cada linhagem:
      - first_nr, last_nr
      - age em versões (intervalo inclusivo)
      - is_dead (True se last_nr != last_version)
      - lista de rótulos 'change' por versão (incluindo 'Same' para lacunas)
    Também retorna listas achatadas de todos os rótulos 'evolution' e 'change' por versão
    (incluindo 'Same' para lacunas e 'None' no ponto de origem).
    """
    root = ET.fromstring(xml_text)
    infos: List[LineageInfo] = []
    evolution_values: List[str] = []
    change_values: List[str] = []

    for lin in root.findall("lineage"):
        versions = lin.findall("version")
        if not versions:
            continue

        # Ordena por número de versão
        versions_sorted = sorted(versions, key=lambda v: int(v.attrib.get("nr")))
        nrs = [int(v.attrib.get("nr")) for v in versions_sorted]

        first_nr = min(nrs)
        last_nr = max(nrs)
        age = (last_nr - first_nr) + 1
        is_dead = (last_nr != last_version)

        lineage_change: List[str] = []

        prev_nr = None
        for v in versions_sorted:
            nr = int(v.attrib.get("nr"))

            # Preenche lacunas entre versões consecutivas com "Same"
            if prev_nr is not None and nr > prev_nr + 1:
                gap = nr - prev_nr - 1
                for _ in range(gap):
                    evolution_values.append("Same")
                    change_values.append("Same")
                    lineage_change.append("Same")

            evo = _norm(v.attrib.get("evolution"))
            chg = _norm(v.attrib.get("change"))

            evolution_values.append(evo if evo else "None")
            change_values.append(chg if chg else "None")
            lineage_change.append(chg if chg else "None")

            prev_nr = nr

        infos.append(LineageInfo(first_nr, last_nr, age, is_dead, lineage_change))

    return infos, evolution_values, change_values

def classify_lineage_change_category(change_values: List[str]) -> str:
    """
    Classify a lineage into one of:
      - 'same'         : all change in {"None", "Same"}
      - 'consistent'   : has change(s) and all non-None/non-empty in CONSISTENT_CHANGE_LABELS
      - 'inconsistent' : has at least one in INCONSISTENT_CHANGE_LABELS (or fallback)
    """
    normed = [_lower(c) if c else "none" for c in change_values]
    if all(c in {"none", "same"} for c in normed):
        return "same"
    if any(c in INCONSISTENT_CHANGE_LABELS for c in normed):
        return "inconsistent"
    non_none = [c for c in normed if c != "none"]
    if non_none and all(c in CONSISTENT_CHANGE_LABELS for c in non_none):
        return "consistent"
    return "inconsistent"

def safe_avg(nums: List[float]) -> float:
    return sum(nums)/len(nums) if nums else 0.0

def compute_kvolatile_points(ages: List[int], is_dead: List[bool]) -> List[Tuple[int, int, float, float]]:
    """
    Returns list of tuples (k, count_dead_age_le_k, cdf_dead, rvolatile).
    """
    total_all = len(ages)
    dead_ages = [a for a, d in zip(ages, is_dead) if d]
    total_dead = len(dead_ages)
    max_age = max(ages) if ages else 0
    f_dead = Counter(dead_ages)

    points: List[Tuple[int, int, float, float]] = []
    cum_dead = 0
    for k in range(max_age + 1):
        cum_dead += f_dead.get(k, 0)
        cdf_dead = (cum_dead / total_dead) if total_dead else 0.0
        rvolatile = (cum_dead / total_all) if total_all else 0.0
        points.append((k, cum_dead, cdf_dead, rvolatile))
    return points

def build_results_xml(
    lineages: List[LineageInfo],
    evolution_values: List[str],
    change_values: List[str],
    last_version: int,
    clones_density: List[Tuple[int, float, float]]  # list of (version, density, extra) -> extra unused
) -> str:
    """
    Build a rich XML report.
    - Adds a <clone_density> block with multiple <point> entries:
        <point><version>ver</version><clones_density>dens</clones_density></point>
      using only the first two elements of each tuple.
    - Adds clone-density averages:
        avg_density_present      : average over provided points
        avg_density_full_range   : average across 1..last_version (missing versions = 0)
    - EXCLUDES 'None' labels from the *version-level* distributions as they mark lineage origin.
    - Formats ALL float metrics with two decimals.
    """
    clones_density = _dedup_consecutive_by_density(clones_density, tol=1e-9)

    total_lineages = len(lineages)
    ages = [i.age_versions for i in lineages]
    is_dead_flags = [i.is_dead for i in lineages]

    # Status
    dead_count = sum(1 for i in lineages if i.is_dead)
    alive_count = total_lineages - dead_count

    # Average lineage age (in versions)
    avg_age_all = safe_avg([float(a) for a in ages])

    # Lineage-level change categories (same/consistent/inconsistent)
    lineage_cats = [classify_lineage_change_category(i.change_labels) for i in lineages]
    lineage_cat_counts = Counter(lineage_cats)
    lineage_cat_ratios = {
        k: (lineage_cat_counts.get(k, 0) / total_lineages if total_lineages else 0.0)
        for k in ("consistent", "same", "inconsistent")
    }

    # Dead-lineage length stats
    dead_ages = [a for a, d in zip(ages, is_dead_flags) if d]
    dead_min = min(dead_ages) if dead_ages else 0
    dead_avg = safe_avg(dead_ages) if dead_ages else 0.0
    dead_max = max(dead_ages) if dead_ages else 0

    # --- Version-level distributions (EXCLUDE 'none' because it marks lineage origin) ---
    evo_labels = [_lower(x) if x else "none" for x in evolution_values]
    chg_raw    = [_lower(x) if x else "none" for x in change_values]

    evo_labels_no_none = [lbl for lbl in evo_labels if lbl != "none"]

    def map_change_bucket(lbl: str) -> str:
        lbl = _lower(lbl) if lbl else "none"
        if lbl == "same":
            return "same"
        if lbl in INCONSISTENT_CHANGE_LABELS:
            return "inconsistent"
        if lbl in CONSISTENT_CHANGE_LABELS:
            return "consistent"
        # 'none' (origin) and unknowns are excluded from version-level stats
        return "exclude"

    chg_buckets_no_none = [map_change_bucket(x) for x in chg_raw if (_lower(x) if x else "none") != "none"]
    chg_buckets_no_none = [b for b in chg_buckets_no_none if b != "exclude"]

    evo_counts = Counter(evo_labels_no_none)
    chg_counts = Counter(chg_buckets_no_none)

    total_versions_evo = sum(evo_counts.values())
    total_versions_chg = sum(chg_counts.values())

    def pct(v: int, total: int) -> float:
        return (100.0 * v / total) if total else 0.0

    # k-volatile points
    k_points = compute_kvolatile_points(ages, is_dead_flags)

    # ---- Build XML ----
    root = ET.Element("results")

    # ---------- clone density block (list of tuples + averages) ----------
    cd_block = ET.SubElement(root, "clone_density")

    versions_seen: List[int] = []
    densities: List[float] = []

    for tup in clones_density or []:
        ver = tup[0] if len(tup) > 0 else None
        dens = tup[1] if len(tup) > 1 else None

        pt = ET.SubElement(cd_block, "point")
        ET.SubElement(pt, "version").text = "" if ver is None else str(ver)
        ET.SubElement(pt, "clones_density").text = "" if dens is None else fmt2(dens)

        if ver is not None and dens is not None:
            versions_seen.append(int(ver))
            try:
                densities.append(float(dens))
            except Exception:
                pass

    avg_density_present = safe_avg(densities)

    if isinstance(last_version, int) and last_version > 0:
        dens_by_ver = {int(v): float(d) for v, d in zip(versions_seen, densities)}
        full_series = [dens_by_ver.get(v, 0.0) for v in range(1, last_version + 1)]
        avg_density_full_range = safe_avg(full_series)
    else:
        avg_density_full_range = avg_density_present

    cd_summary = ET.SubElement(cd_block, "summary")
    ET.SubElement(cd_summary, "versions_count_present").text = str(len(densities))
    ET.SubElement(cd_summary, "avg_density_present").text = fmt2(avg_density_present)
    ET.SubElement(cd_summary, "avg_density_full_range").text = fmt2(avg_density_full_range)

    # ---------- global lineage metrics ----------
    ET.SubElement(root, "total_clone_lineages").text = str(total_lineages)
    ET.SubElement(root, "total_amount_of_versions").text = fmt2(avg_age_all)

    # lineage-level change patterns (percentages over lineages)
    cp_lin = ET.SubElement(root, "change_patterns_of_lineages")
    ET.SubElement(cp_lin, "consistent").text = fmt2(100.0 * lineage_cat_ratios["consistent"])
    ET.SubElement(cp_lin, "same").text = fmt2(100.0 * lineage_cat_ratios["same"])
    ET.SubElement(cp_lin, "inconsistent").text = fmt2(100.0 * lineage_cat_ratios["inconsistent"])

    # status (alive/dead)
    status = ET.SubElement(root, "status_of_clone_lineages")
    alive_el = ET.SubElement(status, "alive")
    ET.SubElement(alive_el, "count").text = str(alive_count)
    ET.SubElement(alive_el, "percentage").text = fmt2(pct(alive_count, total_lineages))
    dead_el = ET.SubElement(status, "dead")
    ET.SubElement(dead_el, "count").text = str(dead_count)
    ET.SubElement(dead_el, "percentage").text = fmt2(pct(dead_count, total_lineages))

    # dead-length stats
    dead_len = ET.SubElement(root, "length_of_dead_clone_lineages")
    ET.SubElement(dead_len, "min").text = str(dead_min)
    ET.SubElement(dead_len, "avg").text = fmt2(dead_avg)
    ET.SubElement(dead_len, "max").text = str(dead_max)

    # evolution pattern of versions (WITHOUT 'none', renormalized)
    evo_el = ET.SubElement(root, "evolution_pattern_of_versions")
    for label, count in sorted(evo_counts.items()):
        ET.SubElement(evo_el, label).text = f"{pct(count, total_versions_evo):.2f}"

    # change pattern of versions (WITHOUT 'none', renormalized)
    chg_el = ET.SubElement(root, "change_pattern_of_versions")
    for label in ("consistent", "same", "inconsistent"):
        ET.SubElement(chg_el, label).text = f"{pct(chg_counts.get(label, 0), total_versions_chg):.2f}"

    # k-volatile (with two-decimal formatting)
    kv = ET.SubElement(root, "kvolatile", attrib={"last_version": str(last_version)})
    for k, count, cdf_dead, rvol in k_points:
        ET.SubElement(
            kv, "point",
            attrib={
                "k": str(k),
                "count": str(count),
                "cdf_dead": fmt2(cdf_dead),
                "rvolatile": fmt2(rvol),
            }
        )

    return _pretty_xml(root)

def _dedup_consecutive_by_density(points: List[Tuple[int, float, float]], tol: float = 1e-9):
    """
    Remove pontos consecutivos cuja densidade (2º elemento) repete.
    Mantém o primeiro da sequência e descarta os seguintes repetidos.
    Ex.: [(1, 5.4, ...), (2, 5.4, ...)] -> remove o segundo.
    """
    out = []
    prev_dens = None
    has_prev = False
    for tup in points or []:
        dens = tup[1] if len(tup) > 1 else None
        # Se não há densidade, mantemos o ponto
        if dens is None or not has_prev:
            out.append(tup)
            prev_dens = dens
            has_prev = True
            continue
        # Compara com tolerância para floats
        if prev_dens is not None and abs(float(dens) - float(prev_dens)) <= tol:
            # densidade repetida em sequência -> descarta
            continue
        out.append(tup)
        prev_dens = dens
    return out


# --------- Public entry-point ---------
def generate_detailed_report(
    xml_text: str,
    last_version: int,
    clones_density: List[Tuple[int, float, float]]
) -> str:
    """
    High-level function: parse -> compute -> build XML report.
    - Produces a <clone_density> block with multiple <point> items,
      each using (version, density) from the tuple list.
    - Adds density averages: avg_density_present and avg_density_full_range.
    - EXCLUDES 'None' from version-level distributions ('evolution'/'change').
    - Formats ALL float metrics with two decimals.
    """
    lineages, evo_vals, chg_vals = parse_lineages(xml_text, last_version)
    return build_results_xml(lineages, evo_vals, chg_vals, last_version, clones_density)
