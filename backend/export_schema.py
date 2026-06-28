"""Run sqlDBinfo.sql and export schema snapshot for AskAI reference."""

from db import export_schema_snapshot, test_db_connection


def main() -> None:
    ok, message = test_db_connection()
    print(f"DB connection: {'OK' if ok else 'FAILED'}")
    print(message)
    if not ok:
        raise SystemExit(1)

    exported, export_message = export_schema_snapshot()
    print(export_message)
    if not exported:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
