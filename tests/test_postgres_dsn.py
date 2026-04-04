import unittest

from backend.infrastructure.postgres_dsn import normalize_psycopg_postgres_dsn, normalize_sqlalchemy_postgres_dsn


class PostgresDsnTestCase(unittest.TestCase):
    def test_rewrites_sqlalchemy_scheme_back_for_psycopg(self):
        self.assertEqual(
            normalize_psycopg_postgres_dsn("postgresql+psycopg://rag:rag@postgres:5432/rag"),
            "postgresql://rag:rag@postgres:5432/rag",
        )

    def test_keeps_plain_scheme_for_psycopg(self):
        self.assertEqual(
            normalize_psycopg_postgres_dsn("postgresql://rag:rag@postgres:5432/rag"),
            "postgresql://rag:rag@postgres:5432/rag",
        )

    def test_rewrites_plain_postgresql_scheme_for_sqlalchemy(self):
        self.assertEqual(
            normalize_sqlalchemy_postgres_dsn("postgresql://rag:rag@postgres:5432/rag"),
            "postgresql+psycopg://rag:rag@postgres:5432/rag",
        )

    def test_rewrites_short_postgres_scheme_for_sqlalchemy(self):
        self.assertEqual(
            normalize_sqlalchemy_postgres_dsn("postgres://rag:rag@postgres:5432/rag"),
            "postgresql+psycopg://rag:rag@postgres:5432/rag",
        )

    def test_keeps_explicit_driver_scheme(self):
        self.assertEqual(
            normalize_sqlalchemy_postgres_dsn("postgresql+psycopg://rag:rag@postgres:5432/rag"),
            "postgresql+psycopg://rag:rag@postgres:5432/rag",
        )


if __name__ == "__main__":
    unittest.main()
