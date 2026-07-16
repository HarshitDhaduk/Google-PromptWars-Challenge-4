"""Cross-platform dev launcher: python run.py"""

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    # No auto-reload: a single, predictable process. (During development run
    # `uvicorn app.main:app --reload` from this directory instead.)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
