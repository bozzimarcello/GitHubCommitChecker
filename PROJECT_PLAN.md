# GitHub Commit Checker - Project Plan

This tool allows checking if a list of GitHub repositories has commits on specific target dates. It uses the `gh` CLI for authentication and API access.

## Phase 1: MVP (Minimal Viable Product) - COMPLETED
**Goal:** Basic functionality to read files and report missing commits for target dates.

- [x] Initialize Python environment and project structure.
- [x] Implement file parsing for `repos.txt` and `dates.txt`.
- [x] Implement a function to call `gh api` and fetch commit dates for a given repository.
- [x] Logic to compare actual commit dates with target dates.
- [x] Simple CLI output showing which students missed which dates.

## Phase 2: Refinement & Robustness - COMPLETED
**Goal:** Improve error handling and usability.

- [x] Add robust error handling for network issues or invalid repository URLs.
- [x] Check if `gh` is installed and authenticated before starting.
- [x] Support for different date formats if needed.
- [x] Prettier CLI output (using `rich` tables and progress bars).

## Phase 3: Advanced Features - COMPLETED
**Goal:** Add power-user features.

- [x] Command-line arguments using `argparse` (input file paths, filtering).
- [x] Export results to CSV.
- [x] Parallelize API calls to speed up checking multiple repositories using `ThreadPoolExecutor`.

## Technical Stack
- **Language:** Python 3.x
- **Dependencies:** 
  - `subprocess` (to call `gh` CLI)
  - `datetime` (for date manipulation)
  - `json` (to parse `gh api` output)
  - `rich` (for advanced CLI UI)
  - `concurrent.futures` (for parallelization)
  - `csv` (for report generation)
