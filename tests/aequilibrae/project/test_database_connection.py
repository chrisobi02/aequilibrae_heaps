from aequilibrae.context import activate_project
from aequilibrae.project.database_connection import database_connection
import pytest


class TestDatabaseConnection:
    def test_cannot_connect_when_no_active_project(self):
        activate_project(None)
        with pytest.raises(FileNotFoundError):
            database_connection()

    def test_connection_with_new_project(self, project):
        conn = database_connection(project.project_base_path)
        cursor = conn.cursor()
        cursor.execute("select count(*) from links")
        assert cursor.fetchone()[0] == 0, "Returned more links thant it should have"
