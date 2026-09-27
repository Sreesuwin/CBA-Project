"""Custom Flask CLI commands.

    flask create-db            create all tables
    flask seed-db              insert demo data (idempotent)
    flask seed-db --reset      drop, recreate, then seed
    flask drop-db --yes        drop all tables
"""

import click
from flask.cli import with_appcontext

from .extensions import db
from .utils.seed import DEMO_PASSWORD, seed_database


def register_cli(app):
    @app.cli.command("create-db")
    @with_appcontext
    def create_db_command():
        """Create all tables on the configured database."""
        db.create_all()
        click.echo(f"Tables created on {db.engine.dialect.name}.")

    @app.cli.command("drop-db")
    @click.option("--yes", is_flag=True, help="Skip the confirmation prompt.")
    @with_appcontext
    def drop_db_command(yes):
        """Drop all tables. Destructive."""
        if not yes:
            click.confirm("This deletes all data. Continue?", abort=True)
        db.drop_all()
        click.echo("All tables dropped.")

    @app.cli.command("seed-db")
    @click.option("--reset", is_flag=True, help="Drop and recreate tables first.")
    @with_appcontext
    def seed_db_command(reset):
        """Insert demo users, loan products and applications."""
        stats = seed_database(reset=reset)

        if any(stats.values()):
            click.echo(
                "Created: "
                + ", ".join(f"{count} {name}" for name, count in stats.items())
            )
        else:
            click.echo("Nothing to do - demo data is already present.")

        click.echo(f"Shared demo password: {DEMO_PASSWORD}")
