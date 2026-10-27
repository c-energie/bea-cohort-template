"""What the template renders, checked without installing anything.

Each render is made from the working tree with ``copier copy --defaults``, once with the default
answers and once with ``licence=proprietary``. Installing a render and running its own suite is
the CI's other job (``.github/workflows/template.yml``); this file holds only what can be read off
the rendered files, so it runs with nothing but ``copier`` on the ``PATH`` (``uvx copier``).

Run from the template repository's root::

    python -m unittest discover -s tests
"""
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

import yaml

TEMPLATE = Path(__file__).resolve().parents[1]

#: The longest ``AGENTS.md`` a render may have (c-energie/smeter-test-workspace#17).
AGENTS_MAX_LINES = 60

#: What a render must never contain (c-energie/smeter-test-workspace#16).
NEVER_RENDERED = ('CHANGELOG.md', 'docs', '.python-version', 'tests/Configuration_files')


def copier_command() -> list:
    """``copier``, else ``uvx copier``."""
    if shutil.which('copier'):
        return ['copier']
    if shutil.which('uvx'):
        return ['uvx', 'copier']
    raise unittest.SkipTest('neither copier nor uvx is on the PATH')


def render(destination: Path, **data) -> Path:
    """Render the working tree into ``destination`` with the defaults, overridden by ``data``."""
    command = [*copier_command(), 'copy', '--defaults', '--quiet', '--trust']
    for key, value in data.items():
        command += ['--data', f'{key}={value}']
    # HEAD, not copier's default of the latest tag: copier adds uncommitted edits to HEAD, so this
    # renders the working tree.
    command += ['--vcs-ref', 'HEAD', str(TEMPLATE), str(destination)]
    subprocess.run(command, check=True, capture_output=True, text=True,
                   env={**os.environ, 'PYTHONUTF8': '1'})
    return destination


class RendersOnce:
    """Renders the template once per class, with ``answers``, into a temporary directory."""
    answers: dict = {}

    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.addClassCleanup(directory.cleanup)
        cls.out = render(Path(directory.name, 'out'), **cls.answers)
        cls.pyproject = tomllib.loads((cls.out / 'pyproject.toml').read_text(encoding='utf-8'))


class TestsDefaultRender(RendersOnce, unittest.TestCase):

    def test_the_package_is_named_for_its_source_and_imports_under_the_derived_name(self):
        self.assertEqual('my-source-dataset', self.pyproject['project']['name'])
        self.assertTrue((self.out / 'src' / 'my_source_dataset' / '__init__.py').is_file())

    def test_it_builds_with_uv_build_under_the_import_name(self):
        self.assertEqual('uv_build', self.pyproject['build-system']['build-backend'])
        self.assertEqual('my_source_dataset', self.pyproject['tool']['uv']['build-backend']['module-name'])

    def test_its_cohort_is_a_bea_cohorts_entry_point_named_for_its_class(self):
        self.assertEqual({'MySourceCohort': 'my_source_dataset.cohort:MySourceCohort'},
                         self.pyproject['project']['entry-points']['bea.cohorts'])

    def test_it_pins_bea_to_contract_major_1_and_the_workspace_python_range(self):
        self.assertIn('building-energy-analysis>=1.0,<2', self.pyproject['project']['dependencies'])
        self.assertEqual('>=3.11.4, <3.14', self.pyproject['project']['requires-python'])

    def test_its_cohort_declares_the_contract_version_the_template_renders(self):
        answers = yaml.safe_load((self.out / '.copier-answers.yml').read_text(encoding='utf-8'))
        contract_version = yaml.safe_load((TEMPLATE / 'copier.yml').read_text(encoding='utf-8'))[
            'contract_version']['default']
        cohort = (self.out / 'src' / 'my_source_dataset' / 'cohort.py').read_text(encoding='utf-8')
        self.assertIn(f"contract_version = '{contract_version}'", cohort)
        self.assertNotIn('contract_version', answers, 'contract_version is rendered, never asked or recorded')

    def test_it_is_mit_licensed_with_the_authors_name(self):
        self.assertEqual('MIT', self.pyproject['project']['license'])
        licence = (self.out / 'LICENSE').read_text(encoding='utf-8')
        self.assertTrue(licence.startswith('MIT License'))
        self.assertIn('Your Name', licence)
        self.assertNotIn('Private :: Do Not Upload', self.pyproject['project'].get('classifiers', []))

    def test_the_toy_data_is_two_households_of_a_week_hourly_in_about_30_kb(self):
        toy = self.out / 'src' / 'my_source_dataset' / 'toy_data'
        size = sum(path.stat().st_size for path in toy.iterdir())
        self.assertLess(size, 45_000)
        households = (toy / 'households.csv').read_text(encoding='utf-8').splitlines()
        self.assertEqual(3, len(households), 'a header and two households')
        energy = (toy / 'energy.csv').read_text(encoding='utf-8').splitlines()
        self.assertEqual(1 + 2 * 7 * 24, len(energy), 'a header and a week of hours for each household')

    def test_agents_md_renders_within_its_line_budget_and_claude_md_points_at_it(self):
        agents = (self.out / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertLessEqual(len(agents.splitlines()), AGENTS_MAX_LINES)
        self.assertNotIn('{{', agents)
        self.assertEqual('@AGENTS.md', (self.out / 'CLAUDE.md').read_text(encoding='utf-8').strip())

    def test_agents_md_names_the_contract_version_and_the_commands(self):
        agents = (self.out / 'AGENTS.md').read_text(encoding='utf-8')
        for needle in ('cohort contract', 'pip install -e .', 'TEST_TIER=fast python -m unittest discover',
                       'copier update', 'inspect_source.py', 'CONTEXT.md', 'CONTRIBUTING',
                       'https://c-energie.github.io/bea-docs/',
                       'gh skill install c-energie/building-energy-analysis --scope project'):
            with self.subTest(needle=needle):
                self.assertIn(needle, agents)

    def test_its_gitignore_keeps_the_generated_configuration_out(self):
        ignored = (self.out / '.gitignore').read_text(encoding='utf-8').splitlines()
        self.assertIn('tests/Configuration_files/', ignored)
        self.assertIn('project-configuration/', ignored)
        self.assertIn('Configuration_files/', ignored)

    def test_it_ships_the_self_contained_tests_workflow(self):
        workflow = (self.out / '.github' / 'workflows' / 'tests.yml').read_text(encoding='utf-8')
        self.assertNotIn('c-energie/.github', workflow)
        self.assertIn('TEST_TIER', workflow)

    def test_it_ships_none_of_the_files_a_render_never_has(self):
        for name in NEVER_RENDERED:
            with self.subTest(name=name):
                self.assertFalse((self.out / name).exists())

    def test_none_of_the_template_repositorys_own_files_is_rendered(self):
        for name in ('copier.yml', 'scripts', '.github/workflows/template.yml', 'tests/test_template.py'):
            with self.subTest(name=name):
                self.assertFalse((self.out / name).exists())

    def test_every_rendered_python_file_compiles(self):
        for path in self.out.rglob('*.py'):
            with self.subTest(path=path.relative_to(self.out)):
                compile(path.read_text(encoding='utf-8'), str(path), 'exec')


class TestsProprietaryRender(RendersOnce, unittest.TestCase):
    answers = dict(licence='proprietary')

    def test_it_has_no_licence_file(self):
        self.assertFalse((self.out / 'LICENSE').exists())

    def test_it_cannot_be_uploaded_to_pypi_by_accident(self):
        self.assertIn('Private :: Do Not Upload', self.pyproject['project']['classifiers'])
        self.assertNotIn('license', self.pyproject['project'])


class TestsOtherLicences(unittest.TestCase):

    def test_each_open_licence_writes_its_own_text_and_spdx_identifier(self):
        for licence, spdx, first_line in (('BSD-3-Clause', 'BSD-3-Clause', 'BSD 3-Clause License'),
                                          ('Apache-2.0', 'Apache-2.0', 'Apache License')):
            with self.subTest(licence=licence), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                out = render(Path(tmp, 'out'), licence=licence)
                pyproject = tomllib.loads((out / 'pyproject.toml').read_text(encoding='utf-8'))
                self.assertEqual(spdx, pyproject['project']['license'])
                self.assertEqual(first_line, (out / 'LICENSE').read_text(encoding='utf-8').strip().splitlines()[0]
                                 .strip())


class TestsNamedAnswers(unittest.TestCase):

    def test_the_import_and_household_class_names_follow_the_package_and_cohort_names(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            out = render(Path(tmp, 'out'), package_name='acme-homes-dataset', class_name='AcmeHomesCohort')
            pyproject = tomllib.loads((out / 'pyproject.toml').read_text(encoding='utf-8'))
            self.assertEqual({'AcmeHomesCohort': 'acme_homes_dataset.cohort:AcmeHomesCohort'},
                             pyproject['project']['entry-points']['bea.cohorts'])
            household = (out / 'src' / 'acme_homes_dataset' / 'household.py').read_text(encoding='utf-8')
            self.assertIn('class AcmeHomesDataset(Dataset):', household)


if __name__ == '__main__':
    sys.exit(unittest.main())
