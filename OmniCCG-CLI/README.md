
# OmniCCG-CLI

## Requirements to Execute
- [Python](https://www.python.org/) >= 3.12
- [Poetry](https://python-poetry.org/)
- [Pip](https://pypi.org/project/pip/)
- [Git](https://git-scm.com/install/windows)
- [Java](https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html) >= 17
- [Txl](https://txl.ca/)

### Note
If you are using Windows, you need to perform all the installation and execution steps in [Cygwing](https://www.cygwin.com/) or [MinGW](https://sourceforge.net/projects/mingw/). This is due to Nicad restrictions. If you prefer to use only Simian, follow the instructions normally.

## Steps to Install
Download the [repository](https://anonymous.4open.science/r/OmniCCG-660A/):

Go to **`OmniCCG-CLI`**:
```
cd OmniCCG/OmniCCG-CLI
```

Install dependencies with Poetry and Pip:
```
poetry install
pip instal -e .
```

e
### Basic usage (no config file)
You can run the application from any path:
```sh
omniccg \
  --git-repo https://github.com/<user>/<project.git> \
  --from-first-commit
```

## Output: Code Clone Genealogies and Metrics
The **OmniCCG-CLI** extracts code clone genealogy and metrics from a Git repository and writes the results as XML files (e.g., `genealogy.xml` and `metrics.xml`) in your current path.


### Examples to extract Code Clone Genealogies using OmniCCG-CLI
```sh
omniccg \
  --git-repo https://github.com/spring-projects/spring-framework \
  --from-first-commit \
  --fixed-leaps 5000
```

```sh
omniccg \
  --git-repo https://github.com/google/guava \
  --fixed-leaps 22 
  --merge-commit true\
```

```sh
omniccg \
  --git-repo https://github.com/apple/pkl \
  --days-prior 100 \
  --clone-detector simian
```
