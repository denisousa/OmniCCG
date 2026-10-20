import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Settings:
    git_url: str = ""
    local_path: str = ""
    clone_detector_tool: Optional[str] = None
    detection_api: Optional[str] = None

    from_begin: bool = False
    specific_commit: str = ""
    use_days: bool = False
    days: Optional[int] = None

    use_merge_commits: bool = False
    use_leaps: bool = False
    commit_leaps: Optional[int] = None

    language: Optional[str] = None


@dataclass
class Paths:
    script_dir: str = "scripts"
    tools_dir: str = "tools"
    res_dir: str = "final_results"
    cur_res_dir: str = field(default_factory=lambda: os.path.join("final_results", "0000000"))
    ws_dir: str = "workspace"
    repo_dir: str = field(default_factory=lambda: os.path.join("workspace", "repo"))
    data_dir: str = field(default_factory=lambda: os.path.join("workspace", "dataset"))
    prod_data_dir: str = field(default_factory=lambda: os.path.join("workspace", "dataset", "production"))
    clone_detector_dir: str = "clone_detector_result"
    clone_detector_xml: str = field(default_factory=lambda: os.path.join("clone_detector_result", "result.xml"))
    hist_file: str = field(default_factory=lambda: os.path.join("workspace", "githistory.txt"))
    metrics_xml: str = field(default_factory=lambda: os.path.join("workspace", "metrics.xml"))
    p_res_file: str = field(default_factory=lambda: os.path.join("final_results", "production_results.xml"))
    p_dens_file: str = field(default_factory=lambda: os.path.join("final_results", "production_density.csv"))


@dataclass
class State:
    p_lin_data: List = field(default_factory=list)
    p_dens_data: List[Tuple[int, float, float]] = field(default_factory=list)


@dataclass
class Context:
    settings: Settings
    paths: Paths
    state: State
