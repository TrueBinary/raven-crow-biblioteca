"""Installer integration tests: temporary Git/runtime, never a real scheduler."""
import json
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import stat
import sys
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'ops/indexnow/install.ps1'
POWERSHELL = shutil.which('powershell.exe')


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(POWERSHELL and os.name == 'nt', 'Windows PowerShell required')
class InstallTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(INSTALLER.exists(), 'Task5 installer is absent')
        # Python 3.15's private temp-dir ACL is unusable in this Windows sandbox.
        self.root = ROOT / ('_indexnow-install-test-' + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(self.cleanup)
        self.source = self.root / 'source with spaces'
        self.package = self.source / 'ops/indexnow'
        self.package.mkdir(parents=True)
        # An isolated committed runtime; editing the shared checkout is never needed.
        state = ROOT / 'ops/indexnow/state.py'
        self.assertTrue(state.exists(), 'Task2 StateStore is needed for lease integration')
        for name in ('state.py', 'snapshot.py', '__init__.py'):
            shutil.copyfile(ROOT / 'ops/indexnow' / name, self.package / name)
        (self.package / '__main__.py').write_text('# reviewed runtime\n', encoding='utf-8')
        (self.package / 'client.py').write_text('# reviewed client\n', encoding='utf-8')
        self.git('init', '-q')
        self.git('config', 'core.autocrlf', 'false')
        self.git('config', 'user.name', 'Installer Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('add', '.')
        self.git('commit', '-qm', 'isolated test fixture')
        self.sha = self.git('rev-parse', 'HEAD')
        self.target = self.root / 'installed with spaces'

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.source), *args], text=True).strip()

    def cleanup(self):
        def writable(func, path, exc):
            Path(path).chmod(stat.S_IWRITE)
            func(path)
        self.assertEqual(self.root.resolve().parent, ROOT.resolve())
        shutil.rmtree(self.root, onexc=writable)

    def ps(self, code, *, check=True):
        result = subprocess.run([POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command',
                                 "$ErrorActionPreference='Stop'; " + code],
                                capture_output=True, text=True, timeout=40)
        if check:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def plan_code(self):
        return (f"Get-IndexNowInstallPlan -SourceRoot {ps_quote(self.source)} "
                f"-InstallRoot {ps_quote(self.target)} -PythonExe {ps_quote(sys.executable)}")

    def install_code(self, register=None):
        register = register or '{ param($request) $script:captured = $request }'
        return (f". {ps_quote(INSTALLER)}; $p = {self.plan_code()}; "
                f"$result = Install-IndexNowRuntime -Plan $p -RegisterTask {register}; "
                '@{ result=$result; task=$script:captured } | ConvertTo-Json -Depth 8')

    def tree(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_plan_only_has_no_side_effects(self):
        before = self.tree()
        result = subprocess.run([POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File',
                                 str(INSTALLER), '-SourceRoot', str(self.source),
                                 '-InstallRoot', str(self.target), '-PythonExe', sys.executable,
                                 '-PlanOnly'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['installed_sha'], self.sha)
        self.assertEqual(self.tree(), before)

    def test_task_contract_is_independent(self):
        plan = json.loads(self.ps(f'. {ps_quote(INSTALLER)}; {self.plan_code()} | ConvertTo-Json -Depth 8').stdout)
        self.assertEqual(plan['task_name'], 'Raven Crow - IndexNow')
        self.assertEqual(plan['interval_minutes'], 5)
        self.assertEqual(plan['execution_limit_seconds'], 120)
        self.assertEqual(plan['multiple_instances'], 'IgnoreNew')
        self.assertEqual(Path(plan['working_directory']), self.target / 'app')
        self.assertEqual(Path(plan['executable']), Path(sys.executable).with_name('pythonw.exe'))
        self.assertEqual(plan['arguments'], f'-m ops.indexnow run --config "{self.target / "config.json"}"')
        self.assertNotIn('release', plan['arguments'])
        self.assertTrue(plan['start_when_available'])
        self.assertTrue(plan['files'])

    def test_task_contract_records_interactive_availability(self):
        plan = json.loads(self.ps(f'. {ps_quote(INSTALLER)}; {self.plan_code()} | ConvertTo-Json -Depth 8').stdout)
        self.assertIs(plan['interactive_only'], True)
        self.assertEqual(plan['logon_type'], 'Interactive')
        self.assertTrue(plan['hidden'])

    def seed_state(self):
        from ops.indexnow.state import StateStore
        self.target.mkdir()
        db = self.target / 'state.sqlite3'
        store = StateStore(db)
        store.close()
        (self.target / 'config.json').write_text(json.dumps({'state_db': str(db), 'enabled': False}), encoding='utf-8')
        (self.target / 'events.jsonl').write_bytes(b'keep log\n')
        (self.target / 'ownership.txt').write_bytes(b'keep key')
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute('CREATE TABLE installer_sentinel(value TEXT)')
            conn.execute("INSERT INTO installer_sentinel VALUES ('preserved')")
        return db

    def test_install_preserves_local_state_and_config(self):
        db = self.seed_state()
        saved = {name: (self.target / name).read_bytes()
                 for name in ('config.json', 'events.jsonl', 'ownership.txt')}
        result = json.loads(self.ps(self.install_code()).stdout)
        self.assertEqual(result['task']['task_name'], 'Raven Crow - IndexNow')
        for name, content in saved.items():
            self.assertEqual((self.target / name).read_bytes(), content)
        with closing(sqlite3.connect(db)) as conn:
            self.assertEqual(conn.execute('SELECT value FROM installer_sentinel').fetchone()[0], 'preserved')
        self.assertEqual((self.target / 'installed-version.txt').read_text().strip(), self.sha)
        self.assertEqual((self.target / 'app/ops/indexnow/__main__.py').read_text(), '# reviewed runtime\n')

    def test_install_uses_planned_sha_despite_dirty_tree_and_head_change(self):
        code = f'. {ps_quote(INSTALLER)}; $p = {self.plan_code()}; '
        code += f"Set-Content -LiteralPath {ps_quote(self.package / '__main__.py')} -Value 'unreviewed'; "
        code += f"git -C {ps_quote(self.source)} add .; git -C {ps_quote(self.source)} commit -qm later; "
        code += 'Install-IndexNowRuntime $p { param($request) } | ConvertTo-Json -Depth 8'
        self.ps(code)
        self.assertEqual((self.target / 'app/ops/indexnow/__main__.py').read_text(), '# reviewed runtime\n')
        self.assertEqual((self.target / 'installed-version.txt').read_text().strip(), self.sha)

    def test_active_runner_lease_prevents_replacement_and_registration(self):
        import time
        from ops.indexnow.state import StateStore
        db = self.seed_state()
        # Honor the actual configured database, even outside InstallRoot.
        external_db = self.root / 'external-state.sqlite3'
        db.rename(external_db)
        db = external_db
        (self.target / 'config.json').write_text(json.dumps({'state_db': str(db), 'enabled': False}), encoding='utf-8')
        store = StateStore(db)
        self.addCleanup(store.close)
        self.assertTrue(store.claim('running-test', int(time.time())))
        result = self.ps(self.install_code('{ throw "REGISTER MUST NOT RUN" }'), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('REGISTER MUST NOT RUN', result.stderr)
        self.assertIn('lease is busy', result.stderr)
        self.assertFalse((self.target / 'app').exists())
        self.assertFalse((self.target / 'installed-version.txt').exists())
        self.assertTrue(store.owns('running-test', int(time.time())))

    def test_install_holds_runner_lease_and_singleton_until_registration_finishes(self):
        self.seed_state()
        check_lease = '''import sqlite3,sys
c=sqlite3.connect(sys.argv[1], timeout=0)
assert c.execute('SELECT owner FROM lease WHERE id=1').fetchone()[0].startswith('install-')
try:
    c.execute('BEGIN IMMEDIATE')
except sqlite3.OperationalError:
    pass
else:
    raise AssertionError('installation has no SQLite fence')
c.close()
'''
        register = ('{ param($request) '
                    f'& $p.console_executable -B -c {ps_quote(check_lease)} {ps_quote(self.target / "state.sqlite3")}; '
                    'if ($LASTEXITCODE -ne 0) { throw "lease/fence not held during registration" }; '
                    'try { Install-IndexNowRuntime $p { throw "inner registration" }; throw "nested install accepted" } '
                    'catch { if ($_.Exception.Message -ne "Another IndexNow installation is in progress.") { throw } }; '
                    '$script:captured=$request }')
        self.ps(self.install_code(register))
        from ops.indexnow.state import StateStore
        import time
        store = StateStore(self.target / 'state.sqlite3')
        self.addCleanup(store.close)
        self.assertTrue(store.claim('after-install', int(time.time())))

    def test_registration_failure_restores_previous_app_and_releases_lease(self):
        self.seed_state()
        app = self.target / 'app'
        app.mkdir()
        (app / 'old.txt').write_bytes(b'previous runtime')
        (self.target / 'installed-version.txt').write_bytes(b'previous-sha\n')
        result = self.ps(self.install_code('{ throw "simulated scheduler failure" }'), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('simulated scheduler failure', result.stderr)
        self.assertEqual((app / 'old.txt').read_bytes(), b'previous runtime')
        self.assertEqual((self.target / 'installed-version.txt').read_bytes(), b'previous-sha\n')
        from ops.indexnow.state import StateStore
        import time
        store = StateStore(self.target / 'state.sqlite3')
        self.addCleanup(store.close)
        self.assertTrue(store.claim('after-failure', int(time.time())))

    def test_corrupt_state_is_not_replaced_or_registered(self):
        self.target.mkdir()
        db = self.target / 'state.sqlite3'
        db.write_bytes(b'not a SQLite database')
        result = self.ps(self.install_code('{ throw "REGISTER MUST NOT RUN" }'), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not a database', result.stderr)
        self.assertEqual(db.read_bytes(), b'not a SQLite database')
        self.assertFalse((self.target / 'app').exists())

    def test_first_install_does_not_create_or_enable_configuration(self):
        self.ps(self.install_code())
        self.assertFalse((self.target / 'config.json').exists())
        self.assertTrue((self.target / 'state.sqlite3').exists())

    def test_dot_source_only_defines_functions(self):
        result = self.ps(f'. {ps_quote(INSTALLER)} -SourceRoot "missing" -PlanOnly; '
                         '(Get-Command Get-IndexNowInstallPlan).Name')
        self.assertEqual(result.stdout.strip(), 'Get-IndexNowInstallPlan')
        self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
