# GitHub Commit Checker

A Python CLI tool to check if students have committed to their GitHub repositories on specific dates.

## Prerequisites
- Python 3.x
- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).
- `rich` library (`pip install rich`).
- the GitHub user authenticated must have access to the repos

## Project Structure
- `check_commits.py`: Main script.
- `repos.txt`: List of GitHub repository URLs (one per line).
- `dates.txt`: List of target dates in `YYYY-MM-DD` format (one per line).
- `assignments/`: Contains subdirectories (e.g. `4di-analizzatore-dati/`) each with their own `repos.txt` and `dates.txt` for different classes/assignments.

## Usage
Run the script to check all repositories against all dates:
```bash
python3 check_commits.py
```

### Advanced Options
- **Filter missing only:** Show only repositories with at least one missing commit.
  ```bash
  python3 check_commits.py --missing-only
  ```
- **Export to CSV:** Save the results to a CSV file.
  ```bash
  python3 check_commits.py --csv report.csv
  ```
- **Parallelization:** Use multiple threads to speed up the process (default is 5).
  ```bash
  python3 check_commits.py --threads 10
  ```
- **Interactive mode:** Pick an assignment folder from a numbered list instead of typing the path.
  ```bash
  python3 check_commits.py -i
  ```
- **Custom files:**
  ```bash
  python3 check_commits.py --repos my_repos.txt --dates my_dates.txt
  ```
- **Error log path:**
  ```bash
  python3 check_commits.py --log-file errors.log
  ```

## Output
The tool displays a table in the terminal with columns for each target date, an **Outside** column (commits outside the date range), and a **Total** column. Symbols shown per date:
- `✔ N`: Commit(s) found (N = number of commits on that date).
- `✘`: No commit found on that date.
- `?`: Error accessing the repository (e.g., private or deleted).

Errors are also logged to `check_commits.log` (or the path specified via `--log-file`).
