# bea-cohort-template

A [Copier](https://copier.readthedocs.io/) template for a **cohort adapter** for
[building-energy-analysis](https://github.com/c-energie/building-energy-analysis) (BEA): a package
of your own that turns one data source into a cohort BEA can analyse.

```bash
uvx copier copy gh:c-energie/bea-cohort-template my-source-dataset
cd my-source-dataset
pip install -e .
TEST_TIER=fast python -m unittest discover
```

The rendered package runs as it stands, on a toy of two households: its tests check the cohort
against BEA's cohort contract and fit MLR on one toy household. Its README then walks through
replacing the toy with your own source. The `bea-cohort-adapter` agent skill in BEA drives the
same steps.

## Contents

- [Questions](#questions)
- [Versions](#versions)
- [Working on the template](#working-on-the-template)

## Questions

| Question | Default | |
|---|---|---|
| `package_name` | `my-source-dataset` | distribution name; `<source>-dataset` suggested |
| `import_name` | from `package_name` | |
| `class_name` | from `package_name` | the cohort class, and its `bea.cohorts` entry-point name |
| `description` | | one line |
| `author_name`, `author_email` | | |
| `licence` | `MIT` | `MIT`, `BSD-3-Clause`, `Apache-2.0` or `proprietary` |

`proprietary` writes no `LICENSE` and classifies the package `Private :: Do Not Upload`, so PyPI
refuses it. Optional features (more in-home sensors, location, household attributes, filters) are
commented examples in the rendered code, not questions.

To render unattended, pass each answer as `--data <question>=<answer>`.

## Versions

The cohort contract version is rendered, never asked: template tags follow the contract major, so
template `v1.x` renders cohort contract 1.x code, pinned to `building-energy-analysis>=1.0,<2`.
A rendered package takes a new contract with `uvx copier update` from a clean working tree.

## Working on the template

- `template/` is what is rendered; everything else here is the template's own.
- `scripts/make_toy_data.py` writes the toy CSVs under `template/`. Rerun it only to change the
  toy, and commit what it writes.
- `tests/test_template.py` checks the rendered files without installing anything:

  ```bash
  uv run --no-project --with copier --with pyyaml python -m unittest discover -s tests
  ```

- CI (`.github/workflows/template.yml`) also renders the default and proprietary answers, installs
  each against BEA from git, and runs its suite.

Until BEA 1.0 is on PyPI, a render's pin cannot resolve, so CI installs BEA and
project-configuration from git and relaxes the pin with `uv pip install --override`. The rendered
`tests.yml` installs from PyPI only, and passes once BEA 1.0 is released.
