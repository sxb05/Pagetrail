from app.db.session import init_db


def main() -> None:
    """Deprecated explicit development wrapper; never runs at application startup."""
    init_db()


if __name__ == "__main__":
    main()
