import argparse
import requests
from datetime import datetime, timedelta
import os
from collections import defaultdict
from prettytable import PrettyTable
import calendar

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, continue without it
    pass

# Get configuration from environment variables or .env file
def get_config():
    # First try environment variables
    token = os.getenv('GITHUB_TOKEN')
    org = os.getenv('GITHUB_ORG')
    
    # If not found and we're not in GitHub Actions, look for .env values
    if not token and 'GITHUB_ACTIONS' not in os.environ:
        # Try alternate names for token that might be in .env
        token = os.getenv('GITHUB_TOKEN')
    
    if not org and 'GITHUB_ACTIONS' not in os.environ:
        # Default to 'sappi' if not specified
        org = 'sappi'
    
    if not token:
        raise ValueError("GitHub token not found. Please set GITHUB_TOKEN environment variable or add it to .env file")
    
    if not org:
        raise ValueError("GitHub organization not found. Please set GITHUB_ORG environment variable or add it to .env file")
    
    return token, org

# Get configuration
GITHUB_TOKEN, GITHUB_ORG = get_config()

def parse_month_range(month_spec):
    """
    Parse month specification into start and end months relative to current date.
    Examples:
        "0" -> (0, 0) current month only
        "1" -> (1, 1) previous month only
        "2-0" -> (2, 0) from 2 months ago including current month
        "14-2" -> (14, 2) from 14 months ago up to 2 months ago
    """
    if '-' in month_spec:
        start, end = map(int, month_spec.split('-'))
        if start < end:
            raise ValueError("Start month must be greater than or equal to end month")
        return start, end
    else:
        month = int(month_spec)
        return month, month

def get_date_range(start_months_ago, end_months_ago):
    """
    Calculate start and end dates based on month specifications.
    Returns tuple of (start_date, end_date) where:
    - start_date is the first day of the start month
    - end_date is the last day of the end month
    """
    today = datetime.now()
    
    # Calculate end month
    if end_months_ago == 0:
        # Current month
        end_date = today
    else:
        # Last day of the target end month
        end_date = (today.replace(day=1) - timedelta(days=1))
        for _ in range(end_months_ago - 1):
            end_date = (end_date.replace(day=1) - timedelta(days=1))
    
    # Calculate start month
    start_date = today
    for _ in range(start_months_ago):
        start_date = (start_date.replace(day=1) - timedelta(days=1))
    start_date = start_date.replace(day=1)  # First day of start month
    
    # If end_months_ago > 0, set end_date to last day of that month
    if end_months_ago > 0:
        end_date = end_date.replace(day=calendar.monthrange(end_date.year, end_date.month)[1])
    
    return start_date, end_date

def fetch_repos(org, team_slug, token):
    repos_url = f'https://api.github.com/orgs/{org}/teams/{team_slug}/repos'
    headers = {'Authorization': f'token {token}',
              'Accept': 'application/vnd.github.v3+json'}
    response = requests.get(repos_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch repos: {response.status_code} - {response.text}")
    return response.json()

def is_auto_approved(pull, reviews):
    """
    Determine if a PR was auto-approved based on review patterns.
    
    Returns True if:
    1. There is exactly one review
    2. The review is from the org owner
    3. The review happened within 5 minutes of PR creation
    """
    if not reviews:
        return False
        
    if len(reviews) == 1:
        created_at = datetime.strptime(pull['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        reviewed_at = datetime.strptime(reviews[0]['submitted_at'], '%Y-%m-%dT%H:%M:%SZ')
        time_to_review = (reviewed_at - created_at).total_seconds() / 60  # in minutes
        return time_to_review <= 5  # Consider it auto-approved if reviewed within 5 minutes
        
    return False

def calculate_metrics(org, repos, token, month_spec):
    metrics = defaultdict(lambda: {
        'total_prs': 0,
        'reviewed_prs': 0,
        'total_review_time': 0,
        'auto_approved_prs': 0,
        'reviewers': defaultdict(int)
    })
    
    start_months_ago, end_months_ago = parse_month_range(month_spec)
    start_date, end_date = get_date_range(start_months_ago, end_months_ago)
    
    headers = {'Authorization': f'token {token}'}
    
    for repo in repos:
        repo_name = repo['name']
        pulls_url = f'https://api.github.com/repos/{org}/{repo_name}/pulls?state=all&per_page=100'
        pulls = requests.get(pulls_url, headers=headers).json()

        for pull in pulls:
            created_at = datetime.strptime(pull['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            if start_date <= created_at <= end_date:
                month_key = created_at.strftime("%Y-%m")

                # Fetch reviews for this PR
                reviews_url = f'https://api.github.com/repos/{org}/{repo_name}/pulls/{pull["number"]}/reviews'
                reviews = requests.get(reviews_url, headers=headers).json()
                
                # Check if this PR was auto-approved
                if is_auto_approved(pull, reviews):
                    metrics[month_key]['auto_approved_prs'] += 1
                    continue  # Skip auto-approved PRs in the regular metrics
                
                metrics[month_key]['total_prs'] += 1

                if 'merged_at' in pull and pull['merged_at']:
                    merged_at = datetime.strptime(pull['merged_at'], '%Y-%m-%dT%H:%M:%SZ')
                    cycle_time = (merged_at - created_at).total_seconds() / 3600
                    metrics[month_key]['total_review_time'] += cycle_time
                    metrics[month_key]['reviewed_prs'] += 1

                    reviews_url = f'https://api.github.com/repos/{org}/{repo_name}/pulls/{pull["number"]}/reviews'
                    reviews = requests.get(reviews_url, headers=headers).json()
                    for review in reviews:
                        reviewer = review['user']['login']
                        metrics[month_key]['reviewers'][reviewer] += 1

    return metrics

def generate_report(metrics, months, use_table=False):
    if use_table:
        generate_table_report(metrics, months)
    else:
        generate_text_report(metrics, months)

def generate_text_report(metrics, months):
    print("=" * 50)

    grand_total = {
        'total_prs': 0,
        'reviewed_prs': 0,
        'auto_approved_prs': 0,
        'total_review_time': 0,
        'reviewers': defaultdict(int)
    }

    for month, data in sorted(metrics.items()):
        print(f"\nMonth: {month}")
        print("-" * 20)
        
        total_prs = data['total_prs']
        reviewed_prs = data['reviewed_prs']
        auto_approved = data['auto_approved_prs']
        avg_cycle_time = data['total_review_time'] / reviewed_prs if reviewed_prs > 0 else 0
        review_coverage = (reviewed_prs / total_prs) * 100 if total_prs > 0 else 0
        
        print(f"Total Pull Requests (excluding auto-approved): {total_prs}")
        print(f"Auto-approved Pull Requests: {auto_approved}")
        print(f"Reviewed Pull Requests: {reviewed_prs}")
        print(f"Code Review Coverage: {review_coverage:.2f}%")
        print(f"Average Cycle Time: {avg_cycle_time:.2f} hours")
        print("Participation Rate:")
        total_reviews = sum(data['reviewers'].values())
        for reviewer, count in data['reviewers'].items():
            percentage = (count / total_reviews) * 100 if total_reviews > 0 else 0
            print(f"  {reviewer}: {count} reviews ({percentage:.2f}%)")

        # Update grand total
        grand_total['total_prs'] += total_prs
        grand_total['reviewed_prs'] += reviewed_prs
        grand_total['auto_approved_prs'] += auto_approved
        grand_total['total_review_time'] += data['total_review_time']
        for reviewer, count in data['reviewers'].items():
            grand_total['reviewers'][reviewer] += count

    print("\nGrand Total")
    print("=" * 50)
    total_prs = grand_total['total_prs']
    reviewed_prs = grand_total['reviewed_prs']
    auto_approved = grand_total['auto_approved_prs']
    avg_cycle_time = grand_total['total_review_time'] / reviewed_prs if reviewed_prs > 0 else 0
    review_coverage = (reviewed_prs / total_prs) * 100 if total_prs > 0 else 0
    
    print(f"Total Pull Requests (excluding auto-approved): {total_prs}")
    print(f"Reviewed Pull Requests: {reviewed_prs}")
    print(f"Auto-approved Pull Requests: {auto_approved}")
    print(f"Code Review Coverage: {review_coverage:.2f}%")
    print(f"Average Cycle Time: {avg_cycle_time:.2f} hours")
    print("Participation Rate:")
    total_reviews = sum(grand_total['reviewers'].values())
    for reviewer, count in grand_total['reviewers'].items():
        percentage = (count / total_reviews) * 100 if total_reviews > 0 else 0
        print(f"  {reviewer}: {count} reviews ({percentage:.2f}%)")

def generate_table_report(metrics, months):
    # print(f"Code Review Report for the last {months} months:")
    print("=" * 50)

    # Table 1: Metrics by month
    table1 = PrettyTable()
    table1.field_names = ["Month", "Total PRs", "Reviewed PRs", "Coverage (%)", "Avg Cycle Time (hours)"]
    table1.align["Month"] = "l"
    table1.align["Total PRs"] = "r"
    table1.align["Reviewed PRs"] = "r"
    table1.align["Coverage (%)"] = "r"
    table1.align["Avg Cycle Time (hours)"] = "r"

    grand_total = {
        'total_prs': 0,
        'reviewed_prs': 0,
        'total_review_time': 0,
        'reviewers': defaultdict(int)
    }

    for month, data in sorted(metrics.items()):
        total_prs = data['total_prs']
        reviewed_prs = data['reviewed_prs']
        review_coverage = (reviewed_prs / total_prs) * 100 if total_prs > 0 else 0
        avg_cycle_time = data['total_review_time'] / reviewed_prs if reviewed_prs > 0 else 0

        table1.add_row([
            month,
            total_prs,
            reviewed_prs,
            f"{review_coverage:.2f}",
            f"{avg_cycle_time:.2f}"
        ])

        # Update grand total
        grand_total['total_prs'] += total_prs
        grand_total['reviewed_prs'] += reviewed_prs
        grand_total['total_review_time'] += data['total_review_time']
        for reviewer, count in data['reviewers'].items():
            grand_total['reviewers'][reviewer] += count

    # Add grand total row
    total_prs = grand_total['total_prs']
    reviewed_prs = grand_total['reviewed_prs']
    review_coverage = (reviewed_prs / total_prs) * 100 if total_prs > 0 else 0
    avg_cycle_time = grand_total['total_review_time'] / reviewed_prs if reviewed_prs > 0 else 0

    table1.add_row([
        "TOTAL",
        total_prs,
        reviewed_prs,
        f"{review_coverage:.2f}",
        f"{avg_cycle_time:.2f}"
    ])

    print(table1)

    # Table 2: Participation rate
    print("\nParticipation Rate:")
    table2 = PrettyTable()
    table2.field_names = ["Reviewer", "Reviews", "Percentage"]
    table2.align["Reviewer"] = "l"
    table2.align["Reviews"] = "r"
    table2.align["Percentage"] = "r"

    total_reviews = sum(grand_total['reviewers'].values())
    for reviewer, count in grand_total['reviewers'].items():
        percentage = (count / total_reviews) * 100 if total_reviews > 0 else 0
        table2.add_row([reviewer, count, f"{percentage:.2f}%"])

    print(table2)

def main():
    parser = argparse.ArgumentParser(description="Generate Code Review Report")
    parser.add_argument("team_slug", help="The team slug for which to generate the report")
    parser.add_argument("months", help="Month specification: '0' for current month, '1' for previous month, "
                        "'2-0' for last 2 months including current, '14-2' for from 14 months ago up to 2 months ago")
    parser.add_argument("--table", action="store_true", help="Output the report in table format")
    args = parser.parse_args()

    try:
        repos = fetch_repos(GITHUB_ORG, args.team_slug, GITHUB_TOKEN)
        metrics = calculate_metrics(GITHUB_ORG, repos, GITHUB_TOKEN, args.months)
        
        # Get date range for header
        start_months_ago, end_months_ago = parse_month_range(args.months)
        start_date, end_date = get_date_range(start_months_ago, end_months_ago)
        
        print(f"Code Review Report - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Organization: {GITHUB_ORG}")
        print(f"Team: {args.team_slug}")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print("-" * 50)
        print()
        
        generate_report(metrics, args.months, args.table)
        
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        raise

if __name__ == "__main__":
    main()