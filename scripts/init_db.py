from __future__ import annotations

import os
import pathlib

import psycopg


def main() -> None:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        raise RuntimeError("DATABASE_URL não definida")

    # ajuste pq psycopg usa "postgresql://", não "postgresql+psycopg://"
    url = raw_url.replace("postgresql+psycopg://", "postgresql://")

    schema_path = pathlib.Path(__file__).parent.parent / "db" / "schema.sql"
    schema_sql = schema_path.read_text()

    with psycopg.connect(url) as conn:
        exists = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'unidade'"
        ).fetchone()

        if exists:
            print("[init_db] Schema já aplicado, ignorando.")
            return

        conn.execute(schema_sql)
        conn.commit()
        print("[init_db] Schema criado com sucesso.")


if __name__ == "__main__":
    main()
