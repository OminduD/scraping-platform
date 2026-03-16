"""Create database tables (alternative to Alembic for quick setup)."""

from data_models import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


if __name__ == "__main__":
    init_db()
