from os import environ
from pathlib import Path

import nox


package_path = Path(__file__).parent
is_circleci = 'CIRCLECI' in environ

nox.options.default_venv_backend = 'uv'


@nox.session(python=['3.12', '3.13', '3.14'])
def pytest(session: nox.Session):
    uv_sync(session, 'pytest')
    pytest_run(session)


@nox.session
def prek(session: nox.Session):
    uv_sync(session)
    session.run(
        'prek',
        'run',
        '--all-files',
    )


@nox.session
def audit(session: nox.Session):
    # Much faster to install the deps first and have pip-audit run against the venv
    uv_sync(session)
    session.run(
        'pip-audit',
        '--desc',
        '--skip-editable',
        *pip_audit_ignore_args(),
    )


@nox.session
def build(session: nox.Session):
    uv_sync(session)
    output_dir = package_path / 'tmp' / 'dist'
    session.run('python', '-m', 'build', '--outdir', output_dir)
    session.run('twine', 'check', *output_dir.glob('*'))


def pytest_run(session: nox.Session, *args, **env):
    """
    Using functions for pytest and uv enables more advanced uses cases.  Examples:

    py_all = ['3.10', '3.11', '3.12', '3.13']

    @session(py=py_all)
    @parametrize('db', ['pg', 'sqlite'])
    def pytest(session: Session, db: str):
        uv_sync(session)
        pytest_run(session, WEBTEST_DB=db)


    @session(py=py_single)
    def pytest_mssql(session: Session):
        uv_sync(session, 'pytest', 'mssql')
        pytest_run(session, WEBTEST_DB='mssql')


    @session(py=py_single)
    def pytest_i18n(session: Session):
        uv_sync(session, extra='i18n')
        pytest_run(session, WEBTEST_DB='sqlite')

    """
    # CircleCI will give additional info in the UI about tests if junit-xml is output.
    junit_opt = f'--junit-xml={package_path}/ci/test-reports/{session.name}.pytests.xml'
    junit_args = (junit_opt,) if is_circleci else ()

    test_args = session.posargs or (package_path / 'tests',)
    session.run(
        'pytest',
        '-rA',
        '--tb=native',
        '--strict-markers',
        '--cov',
        '--cov-report=xml',
        '--no-cov-on-fail',
        *junit_args,
        *args,
        *test_args,
        env=env,
    )


def uv_sync(session: nox.Session, *groups, project=False, extra=None):
    # If no group given, assume group shares name of session.
    if not groups:
        groups = (session.name,)

    # At least pytest needs the project installed.
    project_args = () if project or session.name.startswith('pytest') else ('--no-install-project',)

    group_args = [arg for group in groups for arg in ('--group', group)]
    extra_args = ('--extra', extra) if extra else ()

    run_args = (
        'uv',
        'sync',
        '--active',
        '--frozen',
        '--exact',
        # Use --no-default-groups instead of --only-group as the latter implies
        # --no-install-project.
        '--no-default-groups',
        *project_args,
        *group_args,
        *extra_args,
    )
    session.run(*run_args)


def pip_audit_ignore_args() -> list | tuple:
    ignore_fpath = package_path / 'pip-audit-ignore.txt'

    if not ignore_fpath.exists():
        return ()

    vuln_ids = [
        line
        for line in ignore_fpath.read_text().strip().splitlines()
        if line.strip() and not line.startswith('#')
    ]

    return [arg for vuln_id in vuln_ids for arg in ('--ignore-vuln', vuln_id)]
