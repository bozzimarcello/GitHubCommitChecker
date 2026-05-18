import json
import subprocess
import sys
import argparse
import csv
import os
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.panel import Panel

LOG_ENTRIES = []

console = Console()

def read_lines(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def get_repo_slug(url):
    """Converts https://github.com/owner/repo to owner/repo"""
    return url.replace('https://github.com/', '').strip('/')

def check_gh_auth():
    """Checks if gh is authenticated."""
    try:
        subprocess.run(['gh', 'auth', 'status'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_commits_dates(repo_slug, since=None, until=None):
    """Fetches commit dates for a repo using gh api. Returns (counts, error_msg)."""
    path = f"repos/{repo_slug}/commits"
    params = []
    if since:
        params.append(f"since={since}T00:00:00Z")
    if until:
        params.append(f"until={until}T23:59:59Z")
    
    if params:
        path += "?" + "&".join(params)

    cmd = ['gh', 'api', path, '--paginate']
        
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = json.loads(result.stdout)
        if not isinstance(commits, list):
            return None, f"Unexpected response format (not a list): got {type(commits).__name__}"
        counts = {}
        for c in commits:
            date = c['commit']['committer']['date'][:10]
            counts[date] = counts.get(date, 0) + 1
        return counts, None
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "No error output"
        return None, f"gh api call failed (exit {e.returncode}): {stderr}"
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON response: {e}"

def process_repo(repo_url, target_dates, since, until):
    repo_slug = get_repo_slug(repo_url)
    actual_counts, error_msg = get_commits_dates(repo_slug, since=since, until=until)
    
    missing = []
    has_error = False
    status_row = []
    counts_row = []
    
    if actual_counts is None:
        has_error = True
        status_row = ["ERR"] * len(target_dates)
        counts_row = [0] * len(target_dates)
        total_commits = 0
        outside_commits = 0
        LOG_ENTRIES.append({
            "slug": repo_slug,
            "error": error_msg or "Unknown error",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    else:
        total_commits = sum(actual_counts.values())
        commits_on_target = 0
        for d in target_dates:
            count = actual_counts.get(d, 0)
            counts_row.append(count)
            commits_on_target += count
            if count > 0:
                status_row.append("OK")
            else:
                status_row.append("MISSING")
                missing.append(d)
        outside_commits = total_commits - commits_on_target
                
    return {
        "slug": repo_slug,
        "status": status_row,
        "counts": counts_row,
        "has_error": has_error,
        "missing_count": len(missing),
        "total_commits": total_commits,
        "outside_commits": outside_commits,
        "error_msg": error_msg
    }

def pick_assignment_interactively(assignments_dir="assignments"):
    assignments_path = Path(assignments_dir)
    if not assignments_path.is_dir():
        console.print(f"[bold red]Error:[/bold red] Assignments directory '{assignments_dir}' not found.")
        sys.exit(1)

    folders = sorted([d.name for d in assignments_path.iterdir() if d.is_dir()])
    if not folders:
        console.print(f"[bold red]Error:[/bold red] No assignment folders found in '{assignments_dir}'.")
        sys.exit(1)

    choices_str = "\n".join(f"  [{i+1}] {name}" for i, name in enumerate(folders))
    console.print(Panel.fit(f"[bold]Select an assignment[/bold]\n\n{choices_str}", border_style="cyan"))

    while True:
        try:
            selection = input("Enter number: ").strip()
            idx = int(selection) - 1
            if 0 <= idx < len(folders):
                selected = folders[idx]
                break
            console.print("[yellow]Invalid choice. Try again.[/yellow]")
        except ValueError:
            console.print("[yellow]Please enter a number.[/yellow]")

    assignment_path = assignments_path / selected
    repos_file = str(assignment_path / "repos.txt")
    dates_file = str(assignment_path / "dates.txt")

    for f in (repos_file, dates_file):
        if not os.path.isfile(f):
            console.print(f"[bold red]Error:[/bold red] Required file '{f}' not found in assignment '{choice}'.")
            sys.exit(1)

    return repos_file, dates_file

def main():
    parser = argparse.ArgumentParser(description="Check GitHub commits for specific dates.")
    parser.add_argument("--repos", default="repos.txt", help="Path to repos.txt")
    parser.add_argument("--dates", default="dates.txt", help="Path to dates.txt")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactively select an assignment folder")
    parser.add_argument("--missing-only", action="store_true", help="Only show repositories with missing commits")
    parser.add_argument("--csv", help="Export results to a CSV file")
    parser.add_argument("--threads", type=int, default=5, help="Number of parallel threads")
    parser.add_argument("--log-file", default="check_commits.log", help="Path to the error log file")
    args = parser.parse_args()

    if args.interactive:
        repos_file, dates_file = pick_assignment_interactively()
    else:
        repos_file = args.repos
        dates_file = args.dates

    if not check_gh_auth():
        console.print("[bold red]Error:[/bold red] gh CLI is not authenticated. Please run 'gh auth login'.")
        sys.exit(1)

    try:
        repos = read_lines(repos_file)
        target_dates = sorted(read_lines(dates_file))
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return

    if not target_dates:
        console.print("[bold yellow]Warning:[/bold yellow] No dates specified in dates.txt")
        return

    since = target_dates[0]
    until = target_dates[-1]

    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Checking repositories...", total=len(repos))
        
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {executor.submit(process_repo, url, target_dates, since, until): url for url in repos}
            for future in as_completed(futures):
                results.append(future.result())
                progress.update(task, advance=1)

    # Sort results by slug
    results.sort(key=lambda x: x['slug'])

    # Display Table
    table = Table(title="Commit Compliance Report")
    table.add_column("Student/Repo", style="cyan", no_wrap=True)
    for d in target_dates:
        formatted_date = "\n".join(d.split("-"))
        table.add_column(formatted_date, justify="center")
    table.add_column("Outside", justify="center")
    table.add_column("Total", justify="center")

    for res in results:
        if args.missing_only and res['missing_count'] == 0 and not res['has_error']:
            continue
            
        row_data = [res['slug']]
        for s, count in zip(res['status'], res['counts']):
            if s == "OK":
                row_data.append(f"[bold green]✔ {count}[/bold green]")
            elif s == "ERR":
                row_data.append("[bold magenta]?[/bold magenta]")
            else:
                row_data.append("[bold red]✘[/bold red]")
        row_data.append(str(res['outside_commits']))
        row_data.append(str(res['total_commits']))
        table.add_row(*row_data)

    console.print(table)

    # CSV Export
    if args.csv:
        with open(args.csv, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Repository"] + target_dates + ["Outside", "Total"])
            for res in results:
                writer.writerow([res['slug']] + res['counts'] + [res['outside_commits'], res['total_commits']])
        console.print(f"\n[bold green]Success:[/bold green] Results exported to {args.csv}")

    # Error Log
    separator = "=" * 70
    if LOG_ENTRIES:
        with open(args.log_file, 'w') as f:
            f.write(f"GitHub Commit Checker - Error Log\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{separator}\n\n")
            for entry in LOG_ENTRIES:
                f.write(f"[{entry['timestamp']}] {entry['slug']}\n")
                f.write(f"  Error: {entry['error']}\n\n")
        console.print(f"\n[bold yellow]Warning:[/bold yellow] {len(LOG_ENTRIES)} error(s) logged to {args.log_file}")
    else:
        with open(args.log_file, 'w') as f:
            f.write(f"GitHub Commit Checker - Error Log\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{separator}\n\n")
            f.write("No errors encountered.\n")
        console.print(f"\n[bold green]No errors.[/bold green] Log written to {args.log_file}")

if __name__ == "__main__":
    main()
