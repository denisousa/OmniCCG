# OmniCCG
This is the replication package for the paper *OmniCCG: Agnostic Code Clone Genealogy Extractor*.

**OmniCCG** is a code clone genealogy extractor that is agnostic to clone detectors.
Given a Git repository and user settings, **OmniCCG** extracts the entire clone genealogy from the repository.

## Usage
OmniCCG offers two ways to use it.
1. Graphical user interface
OmniCCG can be used through a modern, responsive web interface that makes it easy to explore and track clone genealogies in a repository.
You may either:
= Use the hosted online platform through the following [link](https://omniccg-ipwd.vercel.app/)
- Use the platform locally by installing and executing **`OmniCCG-API`** and **`OmniCCG-Web`**.

2. Console application
OmniCCG can also be used through a console application, which makes local execution and manipulation of the extracted genealogies and associated metrics.
Run the platform locally by installing and executing **`OmniCCG-CLI`**.

## Clone Detection (Native Integration)
In its current implementation, **OmniCCG** provides built-in clone detection through [Nicad](https://github.com/CordyJ/Open-NiCad) and [Simian](https://simian.quandarypeak.com/), in case the user is not familiar with clone detectors or does not wish to integrate a different tool.

- Using the online platform, it is possible to select **NiCad** or **Simian** to detect code clones through the graphical interface.

- Using the console application, it is possible to select **NiCad** or **Simian** to detect code clones by using the `--clone-detector` flag.

## Clone Detection (Custom Integration)
**OmniCCG** is detector-agnostic because it is designed to integrate with any clone detector chosen by the user. This is achieved through a simple HTTP-based integration API.
To do this, the user must implement an API that has the target Git repository locally cloned and provides an endpoint that accepts a commit hash in the query string. **OmniCCG** issues an HTTP request using the [`requests`](https://pypi.org/project/requests/) library to the following route:

```http
GET /<user-api>/clone-detection/?sha=<hash>
```

When the API receives an HTTP call to this endpoint, a git checkout must be performed for the submitted commit.
Next, clone detection must be performed using the user's preferred detector.
After the clone detector finishes, the developer’s API must return the code clones following the predefined XML schema presented below:

```xml
<clones>
    <class>
        <source file="/folder/ExamapleOne.java" startline="4" endline="25"></source>
        <source file="/folder/ExampleTwo.java" startline="130" endline="151"></source>
    </class>
    ...
</clones>
```

## Preliminary Evaluation
We performed a preliminary evaluation of **OmniCCG** to showcase its main functionalities.
The **`results_of_evaluation/`** directory contains the results obtained in our evaluation.

## How to install and run OmniCCG as a web application and as a console application?
To learn how to install and run **`OmniCCG-API`**, **`OmniCCG-Web`**, and **`OmniCCG-CLI`**, you can read the README.md file for each project.
