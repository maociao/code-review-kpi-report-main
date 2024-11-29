# Code Review Report Generator

## Overview

This Python script generates comprehensive code review reports for GitHub repositories associated with a specific team. It provides insights into code review metrics such as total pull requests, review coverage, cycle time, and participation rates. The report can be run locally or as a GitHub Action.

## Features

- Fetches data from GitHub repositories for a specified team
- Calculates and reports on key code review metrics:
  - Total number of pull requests
  - Number of reviewed pull requests
  - Code review coverage percentage
  - Average code review cycle time
  - Participation rate (number and percentage of reviews per reviewer)
- Provides both monthly breakdowns and grand totals for the specified time period
- Flexible month range specification for precise reporting periods
- Offers both text and table output formats
- Can be run locally or as an automated GitHub Action
- Supports scheduled and manual execution through GitHub Actions
- Automatically creates GitHub issues with report results

## Prerequisites

- Python 3.6 or higher
- GitHub Personal Access Token with appropriate permissions
- For GitHub Actions: Repository admin access to set up workflows

## Installation

### Local Installation

1. Clone this repository or download the script.

2. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the same directory as the script and add your GitHub token:

   ```bash
   GITHUB_TOKEN=your_github_token_here
   GITHUB_ORG=your_organization_name
   ```

### GitHub Actions Installation

1. Create a Fine-grained Personal Access Token (PAT):
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
   - Click "Generate new token"
   - Set Repository access to "All repositories" (or select specific repositories)
   - Set the following permissions:
     - Repository permissions:
       - Contents: Read
       - Issues: Write
       - Pull requests: Read and write
     - Organization permissions:
       - Members: Read
       - Teams: Read
   - Save the token

2. Add the PAT to your repository:
   - Go to your repository's Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `GH_PAT`
   - Value: Your generated PAT from step 1

3. Replace `your_organization_name` in the workflow file, `.github/workflows/code-review-report.yml` with your GitHub organization name.

## Usage

### Local Usage

Run the script from the command line with the following syntax:

```bash
python code-review-kpi-report.py <team_slug> <months> [--table]
```

- `<team_slug>`: The slug of the GitHub team you want to generate the report for.
- `<months>`: The month specification for the report period. Can be specified in two formats:
  - Single month: A single number indicating which month to report on
    - `0`: Current month only
    - `1`: Previous month only
    - `2`: Two months ago only
  - Month range: Two numbers separated by a hyphen, indicating the range of months to include
    - `2-0`: From 2 months ago through current month
    - `14-2`: From 14 months ago through 2 months ago
- `--table`: (Optional) Use this flag to output the report in table format.

Examples:

```bash
# Generate a report for the current month only
python code-review-kpi-report.py mulesoft-development-team 0

# Generate a report for the previous month only
python code-review-kpi-report.py mulesoft-development-team 1

# Generate a report for the last 3 months including current month
python code-review-kpi-report.py mulesoft-development-team 2-0

# Generate a report from 6 months ago up to 2 months ago
python code-review-kpi-report.py mulesoft-development-team 6-2

# Generate any of the above in table format
python code-review-kpi-report.py mulesoft-development-team 2-0 --table
```

### GitHub Actions Usage

#### Automated Execution

The report will automatically run every Monday at 9:00 AM UTC and create a new issue with the results.

#### Manual Execution

1. Go to your repository on GitHub
2. Click the "Actions" tab
3. Select "Code Review Report" from the workflows
4. Click "Run workflow"
5. (Optional) Modify the input parameters:
   - Team slug
   - Month specification (as described above)
6. Click "Run workflow" to start the execution

The workflow will:

1. Generate the report in table format
2. Create a new issue in your repository containing the report
3. Title the issue with the current date for easy reference

## Output

The report includes:

1. Header information:
   - Generation timestamp
   - Organization name
   - Team name
   - Exact date range for the report period

2. For each month in the specified range:
   - Total number of pull requests
   - Number of reviewed pull requests
   - Code review coverage percentage
   - Average cycle time (in hours)
   - List of reviewers and their participation rates

3. Grand totals for the entire period

## Troubleshooting

### Local Execution

- Ensure your GitHub token has the necessary permissions
- Check that the team slug is correct and the team exists in the specified organization
- Verify that your `.env` file is in the correct location and contains the valid GitHub token
- For month range specifications, ensure the start month is greater than or equal to the end month

### GitHub Actions

- Verify that the `GH_PAT` secret is properly set in your repository
- Check that the PAT has all required permissions (organization, team, repository access)
- Ensure the organization name in the workflow file matches your GitHub organization
- Check the Actions tab for detailed error logs if the workflow fails
- Verify the team slug exists and is accessible to the PAT

## Contributing

Contributions to improve the script are welcome. Please feel free to submit a Pull Request or open an Issue for any bugs or feature requests.
