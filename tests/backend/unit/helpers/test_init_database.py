"""Tests for helpers/init_database.py."""

import subprocess
from unittest.mock import patch, MagicMock

from helpers.init_database import (
    database_exists,
    alembic_table_exists,
    run_alembic_command,
    init_alembic,
    init_database,
)


class TestDatabaseExists:

    @patch("helpers.init_database.engine")
    def test_returns_true_when_tables_exist(self, mock_engine):
        with patch("helpers.init_database.inspect") as mock_inspect:
            mock_inspect.return_value.get_table_names.return_value = ["users", "roles"]
            assert database_exists() is True

    @patch("helpers.init_database.engine")
    def test_returns_false_when_no_tables(self, mock_engine):
        with patch("helpers.init_database.inspect") as mock_inspect:
            mock_inspect.return_value.get_table_names.return_value = []
            assert database_exists() is False

    @patch("helpers.init_database.engine")
    def test_returns_false_on_operational_error(self, mock_engine):
        from sqlalchemy.exc import OperationalError

        with patch("helpers.init_database.inspect") as mock_inspect:
            mock_inspect.return_value.get_table_names.side_effect = OperationalError(
                "stmt", {}, Exception("conn refused")
            )
            assert database_exists() is False


class TestAlembicTableExists:

    @patch("helpers.init_database.Session")
    def test_returns_true_when_queryable(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = lambda s: mock_session
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        assert alembic_table_exists() is True

    @patch("helpers.init_database.Session")
    def test_returns_false_on_exception(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("table not found")
        mock_session_cls.return_value.__enter__ = lambda s: mock_session
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        assert alembic_table_exists() is False


class TestRunAlembicCommand:

    @patch("helpers.init_database.subprocess.run")
    def test_success_returns_true(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="")
        assert run_alembic_command("upgrade head") is True

    @patch("helpers.init_database.subprocess.run")
    def test_failure_returns_false(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "alembic")
        assert run_alembic_command("upgrade head") is False

    @patch("helpers.init_database.subprocess.run")
    def test_passes_correct_arguments(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="")
        run_alembic_command("upgrade head")

        args = mock_run.call_args
        assert args[0][0] == ["alembic", "upgrade", "head"]
        assert "cwd" in args[1]

    @patch("helpers.init_database.subprocess.run")
    def test_logs_stdout_on_success(self, mock_run):
        mock_run.return_value = MagicMock(stdout="Running migration 001")
        with patch("helpers.init_database.log") as mock_log:
            run_alembic_command("upgrade head")
            mock_log.info.assert_called()


class TestInitAlembic:

    @patch("helpers.init_database.run_alembic_command", return_value=True)
    @patch("helpers.init_database.Session")
    def test_success_returns_true(self, mock_session_cls, mock_run_cmd):
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = lambda s: mock_session
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        assert init_alembic() is True
        mock_run_cmd.assert_called_once_with("stamp head")

    @patch("helpers.init_database.run_alembic_command", return_value=False)
    @patch("helpers.init_database.Session")
    def test_returns_false_when_stamp_fails(self, mock_session_cls, mock_run_cmd):
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = lambda s: mock_session
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        assert init_alembic() is False


class TestInitDatabase:

    @patch("helpers.init_database.run_alembic_command", return_value=True)
    @patch("helpers.init_database.alembic_table_exists", return_value=True)
    @patch("helpers.init_database.database_exists", return_value=True)
    def test_existing_db_with_alembic_runs_upgrade(self, mock_db, mock_alembic, mock_run):
        assert init_database() is True
        mock_run.assert_called_once_with("upgrade head")

    @patch("helpers.init_database.run_alembic_command", return_value=True)
    @patch("helpers.init_database.init_alembic", return_value=True)
    @patch("helpers.init_database.alembic_table_exists", return_value=False)
    @patch("helpers.init_database.database_exists", return_value=True)
    def test_existing_db_without_alembic_inits_then_upgrades(
        self, mock_db, mock_alembic, mock_init, mock_run
    ):
        assert init_database() is True
        mock_init.assert_called_once()
        mock_run.assert_called_once_with("upgrade head")

    @patch("helpers.init_database.init_alembic", return_value=True)
    @patch("helpers.init_database.Base")
    @patch("helpers.init_database.engine")
    @patch("helpers.init_database.database_exists", return_value=False)
    def test_new_db_creates_tables_and_stamps(
        self, mock_db, mock_engine, mock_base, mock_init
    ):
        assert init_database() is True
        mock_base.metadata.create_all.assert_called_once_with(mock_engine)
        mock_init.assert_called_once()

    @patch("helpers.init_database.run_alembic_command", return_value=False)
    @patch("helpers.init_database.alembic_table_exists", return_value=True)
    @patch("helpers.init_database.database_exists", return_value=True)
    def test_returns_false_on_migration_failure(self, mock_db, mock_alembic, mock_run):
        assert init_database() is False

    @patch("helpers.init_database.init_alembic", return_value=False)
    @patch("helpers.init_database.alembic_table_exists", return_value=False)
    @patch("helpers.init_database.database_exists", return_value=True)
    def test_returns_false_when_init_alembic_fails(self, mock_db, mock_alembic, mock_init):
        assert init_database() is False

    @patch("helpers.init_database.init_alembic", return_value=False)
    @patch("helpers.init_database.Base")
    @patch("helpers.init_database.engine")
    @patch("helpers.init_database.database_exists", return_value=False)
    def test_new_db_returns_false_when_init_alembic_fails(
        self, mock_db, mock_engine, mock_base, mock_init
    ):
        assert init_database() is False
