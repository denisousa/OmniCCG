import os
import json
from pathlib import Path
from typing import List, Tuple

from omniccg.models import Context
from omniccg.domain.CloneClass import CloneClass
from omniccg.utils import run_cmd, which, printWarning
from omniccg.analysis import count_functions_in_file
from omniccg.clone_detection import parseCloneClassFile


def _cloc_total_loc(path: str) -> int:
    candidates = [
        os.path.join(Path(path).parents[2], "tools", "cloc", "cloc-1.72.pl"),
        which("cloc"),
    ]
    cloc_path = next((c for c in candidates if c and os.path.exists(str(c))), None)

    if cloc_path:
        try:
            if cloc_path.endswith(".pl"):
                perl = which("perl")
                if not perl:
                    raise FileNotFoundError("Perl not found for cloc-1.72.pl; will use Python fallback.")
                proc = run_cmd([perl, cloc_path, "--json", path])
            else:
                proc = run_cmd([cloc_path, "--json", path])
            data = json.loads(proc.stdout or '{}')
            if "SUM" in data and isinstance(data["SUM"], dict):
                return (
                    int(data["SUM"].get("code", 0))
                    + int(data["SUM"].get("comment", 0))
                    + int(data["SUM"].get("blank", 0))
                )
        except Exception as e:
            printWarning(f"cloc JSON parsing failed, using fallback: {e}")

    total = 0
    for file in Path(path).rglob("*"):
        if file.is_file():
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    total += sum(1 for _ in f)
            except Exception:
                pass
    return total


def RunDensityAnalysis(ctx: Context, commitNr: int, pcloneclasses: List[CloneClass]) -> None:
    s, p, st = ctx.settings, ctx.paths, ctx.state
    if not os.path.exists(p.clone_detector_xml):
        st.p_dens_data.append((commitNr, 0, 0))
        return

    current_clones = parseCloneClassFile(p.clone_detector_xml)
    if len(current_clones) == 0:
        st.p_dens_data.append((commitNr, 0, 0))
        return

    all_paths = {fr.file for clone in current_clones for fr in clone.fragments}
    total_amount_of_p_functions = sum(count_functions_in_file(path, s.language) for path in all_paths)

    all_sources = [fr for clone in current_clones for fr in clone.fragments]
    amount_of_cloned_p_functions = len(all_sources)
    try:
        density_f_p = 100 * (float(amount_of_cloned_p_functions) / total_amount_of_p_functions)
    except Exception:
        density_f_p = 0.0

    total_amount_of_p_loc = _cloc_total_loc(ctx.paths.prod_data_dir)
    amount_of_cloned_p_loc = sum(cc.countLOC() for cc in pcloneclasses)
    density_loc_p = (
        100 * (float(amount_of_cloned_p_loc) / total_amount_of_p_loc)
        if total_amount_of_p_loc
        else 0.0
    )

    st.p_dens_data.append((commitNr, density_f_p, density_loc_p))


def WriteDensityFile(ctx: Context, densitys: List[Tuple[int, float, float]], filename: str) -> None:
    with open(filename, "w+", encoding="utf-8") as output_file:
        for density in densitys:
            output_file.write(f"{density[0]}, {density[1]}, {density[2]}\n")
