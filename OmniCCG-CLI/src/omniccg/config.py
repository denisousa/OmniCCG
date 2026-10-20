import os
from typing import Dict, Any

from omniccg.models import Settings


def validate_user_input_or_raise(general_settings: Dict[str, Any]) -> None:
    if not isinstance(general_settings, dict):
        raise ValueError("Invalid configuration: root object must be a dictionary.")

    user = general_settings.get("user_settings", {}) or {}

    git_repo = general_settings.get("git_repository")
    if not git_repo or not isinstance(git_repo, str) or not git_repo.strip():
        raise ValueError("Missing required field: 'git_repository'.")

    ffc = bool(user.get("from_first_commit"))
    fac = user.get("from_a_specific_commit")
    fac_ok = isinstance(fac, str) and fac.strip() != ""
    dp = user.get("days_prior")
    dp_ok = isinstance(dp, int) and dp > 0

    chosen = (1 if ffc else 0) + (1 if fac_ok else 0) + (1 if dp_ok else 0)
    if chosen > 1:
        raise ValueError(
            "Invalid configuration: provide only ONE of "
            "'from_first_commit', 'from_a_specific_commit', or 'days_prior' (mutually exclusive)."
        )
    if dp is not None and not dp_ok:
        raise ValueError("'days_prior' must be an integer > 0 when provided.")


def init_settings_from_user(general_settings: Dict[str, Any]) -> Settings:
    user = general_settings.get("user_settings", {}) or {}

    git_repository = general_settings.get("git_repository", "")
    local_path = general_settings.get("local_path", "")
    detection_api = general_settings.get("detection-api") or None

    from_first_commit = bool(user.get("from_first_commit"))
    specific_commit = (user.get("from_a_specific_commit") or "").strip()
    days_prior = user.get("days_prior")

    fac_ok = bool(specific_commit)
    dp_ok = isinstance(days_prior, int) and days_prior > 0
    chosen = (1 if from_first_commit else 0) + (1 if fac_ok else 0) + (1 if dp_ok else 0)
    if chosen == 0:
        from_first_commit = True
        specific_commit = ""
        days_prior = None

    merge_commit = user.get("merge_commit")
    fixed_leaps = user.get("fixed_leaps")
    clone_detector = user.get("clone_detector")

    return Settings(
        git_url=git_repository,
        local_path=local_path,
        clone_detector_tool=clone_detector,
        detection_api=detection_api,
        from_begin=from_first_commit,
        specific_commit=specific_commit or "",
        use_days=dp_ok,
        days=days_prior if dp_ok else None,
        use_merge_commits=bool(merge_commit),
        use_leaps=bool(fixed_leaps),
        commit_leaps=fixed_leaps,
        language=user.get("language"),
    )


def derive_repo_name(settings: Settings) -> str:
    if settings.local_path:
        return os.path.basename(os.path.normpath(settings.local_path)) or "repo"
    url = (settings.git_url or "").rstrip("/")
    base = os.path.basename(url) or "repo"
    if base.endswith(".git"):
        base = base[:-4]
    base = os.path.splitext(base)[0] or base
    return base or "repo"
