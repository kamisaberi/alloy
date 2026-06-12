# alloy/cli.py
import typer

app = typer.Typer(help="Alloy: Universal Package Manager")

@app.command()
def update():
    """Update the local registry index."""
    typer.echo("Updating registry...")

@app.command()
def install(package: str):
    """Install a package."""
    typer.echo(f"Installing {package}...")

if __name__ == "__main__":
    app()