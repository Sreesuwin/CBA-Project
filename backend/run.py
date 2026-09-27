"""Development entrypoint.

    python run.py    ->  http://127.0.0.1:5000/api/health

For production-style serving use a WSGI server, e.g.:
    waitress-serve --port=5000 run:app
"""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_ENV", "development") == "development",
    )
