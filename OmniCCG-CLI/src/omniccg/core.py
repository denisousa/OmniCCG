import os
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from omniccg.compute_time import timed
from omniccg.metrics import generate_detailed_report
from omniccg.models import Paths, State, Context
from omniccg.config import validate_user_input_or_raise, init_settings_from_user, derive_repo_name
from omniccg.git_ops import SetupRepo, PrepareGitHistory, GetHashes, PrepareSourceCode, checkout_commit
from omniccg.clone_detection import RunCloneDetection
from omniccg.genealogy import RunGenealogyAnalysis, WriteLineageFile
from omniccg.density import WriteDensityFile
from omniccg.xml_builders import build_no_clones_message, build_genealogy_xml
from omniccg.utils import safe_rmtree, printInfo, timeToString
from git import Repo


def _process_commit(
    ctx: Context, repo: Repo, hash_index: int, current_hash: str, total_commits: int
) -> float:
    p = ctx.paths
    commit_nr = hash_index + 1
    p.cur_res_dir = os.path.join(p.res_dir, f"{commit_nr}_{current_hash}")

    printInfo(f"Analyzing commit nr.{commit_nr} with hash {current_hash} | total commits: {total_commits}")
    checkout_commit(repo, current_hash, p.repo_dir)

    start = time.time()
    if not PrepareSourceCode(ctx):
        return 0.0

    RunCloneDetection(ctx, current_hash)
    RunGenealogyAnalysis(ctx, commit_nr, current_hash)
    WriteLineageFile(ctx, ctx.state.p_lin_data, p.p_res_file)
    safe_rmtree(p.cur_res_dir)

    return time.time() - start


@timed()
def execute_omniccg(general_settings: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[str]]:
    validate_user_input_or_raise(general_settings)
    settings = init_settings_from_user(general_settings)
    paths = Paths()
    state = State()
    ctx = Context(settings=settings, paths=paths, state=state)

    pkg_root = str(Path(__file__).resolve().parent)
    paths.tools_dir = os.path.join(pkg_root, "tools")
    paths.script_dir = os.path.join(pkg_root, "scripts")

    repo_name = derive_repo_name(settings)
    base_dir = os.path.join(pkg_root, "cloned_repositories", repo_name)
    paths.ws_dir = base_dir
    paths.repo_dir = os.path.join(base_dir, "repo")
    paths.data_dir = os.path.join(base_dir, "dataset")
    paths.prod_data_dir = os.path.join(paths.data_dir, "production")
    paths.hist_file = os.path.join(base_dir, "githistory.txt")
    paths.metrics_xml = os.path.join(base_dir, "metrics.xml")
    paths.p_res_file = os.path.join(base_dir, "genealogy.xml")
    paths.p_dens_file = os.path.join(base_dir, "density.csv")
    paths.res_dir = os.path.join(base_dir, "final_result")
    paths.cur_res_dir = os.path.join(paths.res_dir, "0000000")
    paths.clone_detector_dir = os.path.join(base_dir, "aggregated_results")
    paths.clone_detector_xml = os.path.join(paths.clone_detector_dir, "result.xml")

    os.makedirs(paths.res_dir, exist_ok=True)
    os.makedirs(paths.clone_detector_dir, exist_ok=True)
    os.makedirs(base_dir, exist_ok=True)

    if os.path.isdir(paths.res_dir):
        safe_rmtree(paths.res_dir)
        os.makedirs(paths.res_dir, exist_ok=True)

    print("STARTING DATA COLLECTION SCRIPT\n")
    SetupRepo(ctx)
    PrepareGitHistory(ctx)
    hashes = GetHashes(ctx)
    time.sleep(1)

    analysis_index = 0
    total_time = 0.0
    repo = Repo(paths.repo_dir)

    for hash_index, current_hash in enumerate(hashes):
        analysis_index += 1
        elapsed = _process_commit(ctx, repo, hash_index, current_hash, len(hashes))
        if not elapsed:
            continue
        total_time += elapsed
        avg = int(total_time / analysis_index)
        remaining = int(avg * (len(hashes) - analysis_index))
        print(f"Iteration finished in {timeToString(int(elapsed))}")
        print(f" >>> Average iteration time: {timeToString(avg)}")
        print(f" >>> Estimated remaining time: {timeToString(remaining)}")
        time.sleep(0.5)

    if not ctx.state.p_lin_data:
        return build_no_clones_message(settings.clone_detector_tool), None, None

    WriteDensityFile(ctx, ctx.state.p_dens_data, paths.p_dens_file)
    lineages_xml = WriteLineageFile(ctx, ctx.state.p_lin_data, paths.p_res_file)
    metrics_xml = generate_detailed_report(lineages_xml, len(hashes), ctx.state.p_dens_data)
    Path(ctx.paths.metrics_xml).write_text(metrics_xml, encoding="utf-8")
    genealogy_xml = build_genealogy_xml(lineages_xml, metrics_xml)

    print("\nDONE")
    return genealogy_xml, lineages_xml, metrics_xml
