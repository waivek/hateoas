from rich.console import Console
from rich.table import Table
from rich.text import Text
import sys
from textwrap import wrap
from dataclasses import dataclass

@dataclass
class GitRepo:
    name: str
    branch: str
    status: str
    message: str
    # Store original colored strings
    raw_name: str
    raw_branch: str
    raw_status: str
    raw_message: str

def parse_line(line: str) -> GitRepo:
    # Split by multiple spaces, preserving original colored text
    parts = [p for p in line.split('  ') if p.strip()]

    # Extract name and remaining content
    raw_name = parts[0].strip()
    remaining = '  '.join(parts[1:]).strip()

    # Parse branch and status
    status_start = remaining.find('[')
    raw_branch = remaining[:status_start].strip()

    # Find status between brackets
    status_end = remaining.find(']') + 1
    raw_status = remaining[status_start:status_end].strip()

    # Get commit message
    raw_message = remaining[status_end:].strip()

    # Store both raw (colored) and plain versions
    return GitRepo(
        name=Text.from_ansi(raw_name).plain,
        branch=Text.from_ansi(raw_branch).plain,
        status=Text.from_ansi(raw_status).plain,
        message=Text.from_ansi(raw_message).plain,
        raw_name=raw_name,
        raw_branch=raw_branch,
        raw_status=raw_status,
        raw_message=raw_message
    )

def format_table(repos: list[GitRepo], width: int = 100) -> None:
    console = Console()

    # Calculate column widths
    name_width = max(len(repo.name) for repo in repos)
    branch_width = max(len(repo.branch) for repo in repos)
    status_width = max(len(repo.status) for repo in repos)

    # Calculate message width with some padding
    message_width = width - (name_width + branch_width + status_width + 12)

    # Create and configure table
    table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
        padding=(0, 1),
        collapse_padding=True
    )

    # Add columns with specific widths
    table.add_column("Name", width=name_width, no_wrap=True)
    table.add_column("Branch", width=branch_width, no_wrap=True)
    table.add_column("Status", width=status_width, no_wrap=True)
    table.add_column("Message", width=message_width, overflow="fold")

    # Add rows
    for repo in repos:
        # Create Text objects from raw (colored) strings
        name = Text.from_ansi(repo.raw_name)
        branch = Text.from_ansi(repo.raw_branch)
        status = Text.from_ansi(repo.raw_status)
        message = Text.from_ansi(repo.raw_message)

        table.add_row(name, branch, status, message)

    # Print the table
    console.print(table)

def main():
    # Read input from stdin
    lines = sys.stdin.readlines()
    repos = [parse_line(line.strip()) for line in lines]

    # Format and print output
    format_table(repos)

if __name__ == "__main__":
    main()
