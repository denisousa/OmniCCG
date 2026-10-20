# CodeRabbit Activities in Open Source Software Projects Dataset

## Overview

This dataset contains metadata about CodeRabbit activities in engineered open-source GitHub repositories. CodeRabbit is an AI-powered code review agent that can review pull requests, comment on issues, and generate code changes through features such as docstring generation, autofixes, unit test generation, and merge conflict resolution.

The dataset is intended to support empirical research on AI-assisted code review, specialized code review agents, and human-AI collaboration in software engineering. It links repositories, pull requests, issues, commits authored by CodeRabbit, and CodeRabbit configuration files.

## Dataset Contents

This Zenodo release includes the following files:

| File | Format | Rows | Description |
|---|---:|---:|---|
| `repositories.parquet` | Parquet | 481 rows | Repository-level metadata and the heuristic that identified evidence of CodeRabbit adoption. |
| `pull_requests.parquet` | Parquet | 99,454 rows | Metadata for merged pull requests involving CodeRabbit review activity or CodeRabbit-authored Finishing Touch pull requests. |
| `issues.parquet` | Parquet | 2,255 rows | Metadata for closed issues in which CodeRabbit participated through comments. |
| `commits.parquet` | Parquet | 188 rows | Commits authored by `coderabbitai[bot]`, labeled by Finishing Touch activity when identifiable. |
| `coderabbit_configuration_files-20260626T230847Z-3-001.zip` | ZIP | 345 YAML files | Original CodeRabbit configuration files collected from repository roots. |

## CodeRabbit Activity Types

The dataset distinguishes the following pull request activity categories:

| Activity Type | Meaning |
|---|---|
| `Reviewed PR` | A merged pull request reviewed by CodeRabbit. |
| `Finishing Touch PR: <activity>` | A merged pull request authored by CodeRabbit to apply generated changes. |
| `Reviewed PR with Finishing Touch: <activity>` | A pull request reviewed by CodeRabbit that also contains CodeRabbit-generated code changes. |

The Finishing Touch activities identified from CodeRabbit-authored commits are:

| Finishing Touch | Commit Count |
|---|---:|
| `generate docstrings` | 111 |
| `autofix` | 43 |
| `generate unit tests` | 9 |
| `resolve merge conflicts` | 3 |
| `Other` | 22 |

The `Other` category contains commits whose messages did not match the predefined regular-expression patterns used for known CodeRabbit Finishing Touch activities. This category may include undocumented, custom, or project-specific actions.

### Pull Requests

The `pull_requests.parquet` file contains 99,454 pull request records. All records correspond to closed pull requests collected as merged pull requests during the extraction process.

### Issues

The `issues.parquet` file contains 2,255 closed issues with comments from CodeRabbit, spanning 160 repositories.

### Commits

The `commits.parquet` file contains 188 commits authored by `coderabbitai[bot]`, spanning 63 repositories and 175 pull requests.

## Data Schema

### `repositories.parquet`

| Column | Type | Description |
|---|---|---|
| `repo_id` | integer | Internal repository identifier used to join tables. |
| `repo_name` | string | GitHub repository name in `owner/repository` format. |
| `coderabbit_method_heuristic` | string | Heuristic that identified evidence of CodeRabbit adoption: `Configuration File`, `Branch`, or `Author`. |
| `mined_at` | string | Timestamp indicating when the repository metadata was mined. |
| `github_link` | string | URL of the GitHub repository. |
| `language` | string | Primary programming language reported by GitHub. |
| `license` | string | Repository license reported by GitHub. |
| `created_at` | string | Repository creation timestamp. |
| `commits` | integer | Number of commits reported for the repository at mining time. |
| `forks` | integer | Number of forks reported by GitHub. |
| `watchers` | integer | Number of watchers reported by GitHub. |
| `stargazers` | integer | Number of stars reported by GitHub. |
| `contributors` | integer | Number of contributors reported for the repository. |
| `topics` | string | Repository topics, when available. |

### `pull_requests.parquet`

| Column | Type | Description |
|---|---|---|
| `repo_id` | integer | Internal repository identifier. |
| `repo` | string | GitHub repository name in `owner/repository` format. |
| `pr_id` | string | Internal pull request identifier, generally combining `repo_id` and `pr_number`. |
| `pr_number` | integer | GitHub pull request number. |
| `title` | string | Pull request title. |
| `url` | string | GitHub pull request URL. |
| `state` | string | Pull request state at extraction time. |
| `author` | string | GitHub username of the pull request author. |
| `created_at` | string | Pull request creation timestamp. |
| `updated_at` | string | Pull request last update timestamp. |
| `closed_at` | string | Pull request close timestamp. |
| `labels` | list[string] | Labels assigned to the pull request. |
| `number_comments` | integer | Number of comments reported for the pull request. |
| `coderabbit_activity` | string | CodeRabbit activity label assigned to the pull request. |

### `issues.parquet`

| Column | Type | Description |
|---|---|---|
| `repo_id` | integer | Internal repository identifier. |
| `repo` | string | GitHub repository name in `owner/repository` format. |
| `issue_id` | string | Internal issue identifier, generally combining `repo_id` and `issue_number`. |
| `issue_number` | integer | GitHub issue number. |
| `title` | string | Issue title. |
| `url` | string | GitHub issue URL. |
| `state` | string | Issue state at extraction time. |
| `author` | string | GitHub username of the issue author. |
| `created_at` | string | Issue creation timestamp. |
| `updated_at` | string | Issue last update timestamp. |
| `closed_at` | string | Issue close timestamp. |
| `labels` | list[string] | Labels assigned to the issue. |
| `comments` | integer | Number of comments reported for the issue. |

### `commits.parquet`

| Column | Type | Description |
|---|---|---|
| `repo_id` | integer | Internal repository identifier. |
| `repo` | string | GitHub repository name in `owner/repository` format. |
| `pr_id` | string | Internal pull request identifier associated with the commit. |
| `pr_number` | integer | GitHub pull request number associated with the commit. |
| `commit_id` | string | Internal commit identifier. |
| `sha` | string | Git commit SHA. |
| `message` | string | Commit message. |
| `finishing_touch` | string | Finishing Touch activity label inferred from the commit message. |
| `author_name` | string | Commit author name. |
| `author_date` | string | Commit author timestamp. |
| `url` | string | GitHub commit URL. |

## Configuration Files

The ZIP archive contains 345 CodeRabbit YAML configuration files. Each file is stored under a path derived from the repository name, using the following structure:

```text
coderabbit_configuration_files/<owner>__<repository>/.coderabbit.yaml
```

These files can be used to study how projects configure CodeRabbit behavior, such as review settings, path filters, language-specific options, and automated review preferences.

## How to Load the Data

Install the required Python dependencies:

```bash
pip install pandas pyarrow
```

Load the Parquet files:

```python
import pandas as pd

repositories = pd.read_parquet("repositories.parquet")
pull_requests = pd.read_parquet("pull_requests.parquet")
issues = pd.read_parquet("issues.parquet")
commits = pd.read_parquet("commits.parquet")
```

Join pull requests with repository metadata:

```python
prs_with_repo_metadata = pull_requests.merge(
    repositories[["repo_id", "repo_name", "language", "license"]],
    on="repo_id",
    how="left",
)
```

Read the configuration files from the ZIP archive:

```python
from zipfile import ZipFile

with ZipFile("coderabbit_configuration_files-20260626T230847Z-3-001.zip") as archive:
    yaml_files = [
        name for name in archive.namelist()
        if name.endswith((".yaml", ".yml"))
    ]

    first_config = archive.read(yaml_files[0]).decode("utf-8")
```
