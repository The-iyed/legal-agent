#!/usr/bin/env python3
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

app = typer.Typer(help="Maarefa Agent V2 CLI Tool")
console = Console()

def run_command(command: str) -> None:
    """Run a shell command and show output in real-time."""
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    for line in process.stdout:
        console.print(line.strip())
    
    process.wait()
    if process.returncode != 0:
        console.print("[red]Command failed![/red]")
        sys.exit(1)

@app.command()
def create_agent():
    """Create a new agent interactively."""
    console.print(Panel.fit(
        "[bold blue]Create New Agent[/bold blue]\n"
        "This will help you create a new agent with all necessary files and configurations.",
        title="Agent Creation Wizard"
    ))
    
    # Get agent name
    agent_name = Prompt.ask(
        "\n[bold]Enter agent name[/bold]",
        default="new_agent"
    )
    
    # Convert to snake_case if needed
    agent_name = agent_name.lower().replace(" ", "_")
    
    # Get prompt types
    console.print("\n[bold]Available prompt types:[/bold]")
    prompt_types = ["general", "technical", "creative", "study", "qa"]
    for i, ptype in enumerate(prompt_types, 1):
        console.print(f"{i}. {ptype}")
    
    selected_types = []
    while True:
        choice = Prompt.ask(
            "\nSelect prompt type (number) or 'done' to finish",
            default="done"
        )
        if choice.lower() == "done":
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(prompt_types):
                selected_types.append(prompt_types[idx])
            else:
                console.print("[yellow]Invalid selection![/yellow]")
        except ValueError:
            console.print("[yellow]Please enter a number![/yellow]")
    
    if not selected_types:
        selected_types = ["general"]
    
    # Confirm creation
    if Confirm.ask(f"\nCreate agent '{agent_name}' with prompt types: {', '.join(selected_types)}?"):
        cmd = f"python scripts/create_agent.py {agent_name} --prompt-types {' '.join(selected_types)}"
        run_command(cmd)
        console.print("[green]Agent created successfully![/green]")

@app.command()
def run():
    """Run the application locally."""
    console.print(Panel.fit(
        "[bold blue]Starting Application[/bold blue]\n"
        "Running the application in development mode...",
        title="Application Runner"
    ))
    run_command("uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")

@app.command()
def test():
    """Run tests."""
    console.print(Panel.fit(
        "[bold blue]Running Tests[/bold blue]\n"
        "Executing test suite...",
        title="Test Runner"
    ))
    run_command("pytest tests/ -v")

@app.command()
def build():
    """Build Docker container."""
    console.print(Panel.fit(
        "[bold blue]Building Docker Container[/bold blue]\n"
        "Building the application container...",
        title="Docker Builder"
    ))
    run_command("docker-compose build")

@app.command()
def clean():
    """Clean up generated files."""
    console.print(Panel.fit(
        "[bold blue]Cleaning Project[/bold blue]\n"
        "Removing generated files and caches...",
        title="Project Cleaner"
    ))
    
    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        "**/.coverage",
        "**/*.egg-info",
        "**/*.egg",
        "**/.pytest_cache",
        "**/htmlcov",
        "**/dist",
        "**/build"
    ]
    
    for pattern in patterns:
        for path in Path(".").glob(pattern):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
    
    console.print("[green]Cleanup completed![/green]")

@app.command()
def status():
    """Show project status."""
    console.print(Panel.fit(
        "[bold blue]Project Status[/bold blue]",
        title="Status Checker"
    ))
    
    # Check Docker status
    console.print("\n[bold]Docker Status:[/bold]")
    run_command("docker-compose ps")
    
    # Check Python environment
    console.print("\n[bold]Python Environment:[/bold]")
    run_command("python --version")
    run_command("pip list")

def show_menu():
    """Show the main menu."""
    table = Table(title="Maarefa Agent V2 CLI")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    
    commands = [
        ("create-agent", "Create a new agent"),
        ("run", "Run the application locally"),
        ("test", "Run tests"),
        ("build", "Build Docker container"),
        ("clean", "Clean up generated files"),
        ("status", "Show project status"),
        ("exit", "Exit the CLI")
    ]
    
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    
    console.print(table)

@app.command()
def main():
    """Interactive CLI for Maarefa Agent V2."""
    console.print(Panel.fit(
        "[bold blue]Maarefa Agent V2[/bold blue]\n"
        "Welcome to the interactive CLI!",
        title="CLI Tool"
    ))
    
    while True:
        show_menu()
        choice = Prompt.ask("\nSelect a command", choices=["create-agent", "run", "test", "build", "clean", "status", "exit"])
        
        if choice == "exit":
            console.print("[yellow]Goodbye![/yellow]")
            break
        
        # Call the appropriate command
        if choice == "create-agent":
            create_agent()
        elif choice == "run":
            run()
        elif choice == "test":
            test()
        elif choice == "build":
            build()
        elif choice == "clean":
            clean()
        elif choice == "status":
            status()

if __name__ == "__main__":
    app() 