
# OmniCCG-API

## Requirements to Execute
For OmniCCG execute:
- [Python](https://www.python.org/) >= 3.12
- [Poetry](https://python-poetry.org/)
- [Pip](https://pypi.org/project/pip/)
- [Git](https://git-scm.com/install/windows)
- [Cygwing](https://www.cygwin.com/) or [MinGW](https://sourceforge.net/projects/mingw/) - If you are using Windows, you need to perform all the installation and execution steps using one of these tools.

For Clone detectors execute:
- [Java](https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html) >= 17 - It is necessary for the Simian execution.
- [Txl](https://txl.ca/) - It is necessary for the Nicad execution.

### Installation tip:
You can run these commands to install Txl:
```sh
curl -L -o /tmp/freetxl.tar.gz https://txl.ca/download/25536-txl10.8b.linux64.tar.gz && \
    mkdir -p /opt/txl && \
    tar -xzf /tmp/freetxl.tar.gz -C /opt/txl --strip-components=1 && \
    chmod +x /opt/txl/bin/txl && \
    ln -sf /opt/txl/bin/txl /usr/local/bin/txl && \
    rm /tmp/freetxl.tar.gz
```

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

