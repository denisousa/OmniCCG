
# OmniCCG

## Description
OmniCCG is a tool for detecting and analyzing Code Clone Genealogies (CCG) in Git repositories.
It allows understanding how a piece of code is replicated, evolves, and propagates throughout the history of a software project.
This tool uses other two tools that detect clones, the Simian and Nicad.

## Project Structure
```
OmniCCG/
 ├─ analysis.py            
 ├─ check_results.py   
 ├─ code_operations.py
 ├─ commit_tests.py     # A script for tests
 ├─ count_methods.py            
 ├─ tools/              # Secondary tools used by this script
 ├─ main.py             # Main execution entry point
 ├─ pyproject.toml      # Poetry configuration
 ├─ omniccg.py          # Script for settings
 └─ README.md
```

## Configuration
Clone the repository:
```
git clone https://github.com/denisousa/OmniCCG.git
cd OmniCCG
```

If Git prompts for credentials, provide your GitHub username and Personal Access Token.

## Output: Clone Genealogies
The tool generates genealogical lineage information of detected code clones.
The default API output format for clone lineage retrieval is XML.

## Workflow Summary
1. The target Git repository is defined in `git_url` inside `omniccg.py`.
2. The repository is fetched and analyzed.
3. Code clone genealogies are produced and exposed through an API endpoint.

## Requirements to Execute
- Python >= 3.12
- Poetry
- Git

## Steps to Install
Install necessary system dependencies (In Linux):
```
sudo apt install python3-poetry
```
Install Python dependencies:
```
pip install Flask GitPython
```

## Steps to Execute
Before running, configure the target repository:
- Ensure the repository you want to analyze is **public**. The tool will clone this repository and return the genealogy of clones within this project.
- Set `git_url` inside `omniccg.py`.
- If authentication issues occur, configure your GitHub SSH key.

Run the application:
```
python3 main.py
```

## Endpoints to Access
### Example to detect Code Clone Genealogies (CCG)
```
curl -X GET "http://127.0.0.1:5000/detect_clones"   -H "Content-Type: application/json"   --data '{
    "git_repository": "https://github.com/jfree/jfreechart",
    "user_settings": {
      "from_first_commit": true,
      "from_a_specific_commit": null,
      "days_prior": null,
      "merge_commit": null,
      "fixed_leaps": 40,
      "clone_detector": "simian"
    }
  }'
```

## Output Example
The endpoint returns an **XML** describing genealogical clone lineages of the analyzed project and this result is save in:
```
results/
```
