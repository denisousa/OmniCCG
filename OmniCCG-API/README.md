
# OmniCCG-API

## Requirements to Execute
- [Python](https://www.python.org/) >= 3.12
- [Poetry](https://python-poetry.org/)
- [Git](https://git-scm.com/install/windows)
- [Java](https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html) >= 17
- [Txl](https://txl.ca/)

### Note
If you are using Windows, you need to perform all the installation and execution steps in [Cygwing](https://www.cygwin.com/) or [MinGW](https://sourceforge.net/projects/mingw/). This is due to Nicad restrictions. If you prefer to use only Simian, follow the instructions normally.

## Steps to Install
Download the [repository](https://anonymous.4open.science/r/OmniCCG-660A/):

Go to **`OmniCCG-API`**:
```
cd OmniCCG/OmniCCG-API
```

Install dependencies with Poetry:
```
poetry install
```

## Steps to Execute
Run the application:
```
python main.py
```

The platform will be available at `http://localhost:5000`


## Output: Code Clone Genealogies and Metrics
All results can be found in the `cloned_repositories/<repo_name>/` folder.
The genealogy and metrics are described in the files `genealogy.xml` and `metrics.xml`.


## Examples to extract Code Clone Genealogies using Curl
```
curl -X POST "http://127.0.0.1:5000/detect_clones"   -H "Content-Type: application/json"   --data '{
    "git_repository": "https://github.com/gauravrmazra/gauravbytes",
    "user_settings": {
      "from_first_commit": true,
      "from_a_specific_commit": null,
      "days_prior": null,
      "merge_commit": null,
      "fixed_leaps": 100,
      "clone_detector": "nicad"
    }
  }'
```

```
curl -X POST "http://127.0.0.1:5000/detect_clones"   -H "Content-Type: application/json"   --data '{
    "git_repository": "https://github.com/PBH-BTN/PeerBanHelper.git",
    "user_settings": {
      "from_first_commit": true,
      "from_a_specific_commit": null,
      "days_prior": null,
      "merge_commit": null,
      "fixed_leaps": 1000,
      "clone_detector": "nicad"
    }
  }'
```

