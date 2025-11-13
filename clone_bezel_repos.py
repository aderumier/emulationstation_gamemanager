#!/usr/bin/env python3
"""
Clone all repositories from thebezelproject GitHub organization.

This script uses the GitHub API to fetch all repositories from the organization
and clones them to a specified directory.
"""

import os
import subprocess
import sys
import requests
import time
from pathlib import Path


def get_all_repos(username, per_page=100, token=None):
    """
    Fetch all repositories from a GitHub user or organization.
    Tries organization endpoint first, then falls back to user endpoint.
    
    Args:
        username: GitHub username or organization name
        per_page: Number of repos per page (max 100)
        token: Optional GitHub personal access token
    
    Returns:
        List of repository dictionaries with 'name' and 'clone_url' keys
    """
    repos = []
    page = 1
    
    print(f"Fetching repositories from {username}...")
    
    # Try organization endpoint first, then user endpoint
    endpoints = [
        f"https://api.github.com/orgs/{username}/repos",
        f"https://api.github.com/users/{username}/repos"
    ]
    
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    
    url = None
    for endpoint in endpoints:
        try:
            # Test the endpoint
            test_response = requests.get(endpoint, headers=headers, params={'per_page': 1})
            if test_response.status_code == 200:
                url = endpoint
                print(f"  Using endpoint: {endpoint}")
                break
            elif test_response.status_code == 404:
                continue  # Try next endpoint
            else:
                test_response.raise_for_status()
        except requests.exceptions.RequestException:
            continue
    
    if not url:
        print(f"Error: Could not find user/organization '{username}'")
        print("  Tried both /orgs/ and /users/ endpoints")
        sys.exit(1)
    
    while True:
        params = {
            'per_page': per_page,
            'page': page,
            'type': 'all'  # Get all repos (public, private if authenticated)
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            page_repos = response.json()
            
            if not page_repos:
                break
            
            for repo in page_repos:
                repos.append({
                    'name': repo['name'],
                    'clone_url': repo['clone_url'],
                    'ssh_url': repo['ssh_url'],
                    'default_branch': repo.get('default_branch', 'main')
                })
            
            print(f"  Fetched page {page}: {len(page_repos)} repositories (total: {len(repos)})")
            
            # Check if there are more pages
            if len(page_repos) < per_page:
                break
            
            page += 1
            
            # Rate limiting: GitHub API allows 60 requests/hour for unauthenticated requests
            # Add a small delay to be respectful
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repositories: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 403:
                    print("Rate limit exceeded. Consider using a GitHub token with --token option.")
                elif e.response.status_code == 404:
                    print(f"User/organization '{username}' not found.")
            sys.exit(1)
    
    return repos


def clone_repo(repo_info, target_dir, use_ssh=False):
    """
    Clone a single repository.
    
    Args:
        repo_info: Dictionary with repository information
        target_dir: Directory to clone into
        use_ssh: If True, use SSH URL; otherwise use HTTPS
    
    Returns:
        True if successful, False otherwise
    """
    repo_name = repo_info['name']
    clone_url = repo_info['ssh_url'] if use_ssh else repo_info['clone_url']
    repo_path = Path(target_dir) / repo_name
    
    # Skip if already exists
    if repo_path.exists():
        print(f"  ⏭️  Skipping {repo_name} (already exists)")
        return True
    
    print(f"  📥 Cloning {repo_name}...")
    
    try:
        result = subprocess.run(
            ['git', 'clone', clone_url, str(repo_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per repo
        )
        
        if result.returncode == 0:
            print(f"  ✅ Successfully cloned {repo_name}")
            return True
        else:
            print(f"  ❌ Failed to clone {repo_name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⏱️  Timeout cloning {repo_name}")
        return False
    except Exception as e:
        print(f"  ❌ Error cloning {repo_name}: {e}")
        return False


def main():
    """Main function to clone all repositories."""
    username = 'thebezelproject'
    default_target_dir = 'bezel_repositories'
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description='Clone all repositories from thebezelproject GitHub user/organization'
    )
    parser.add_argument(
        '-d', '--directory',
        default=default_target_dir,
        help=f'Target directory for clones (default: {default_target_dir})'
    )
    parser.add_argument(
        '--ssh',
        action='store_true',
        help='Use SSH URLs instead of HTTPS (requires SSH keys configured)'
    )
    parser.add_argument(
        '--token',
        help='GitHub personal access token (for higher rate limits)'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='Skip repositories that already exist (default: True)'
    )
    parser.add_argument(
        '--user',
        default=username,
        help=f'GitHub username or organization name (default: {username})'
    )
    
    args = parser.parse_args()
    
    target_dir = Path(args.directory).resolve()
    
    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Target directory: {target_dir}\n")
    
    # Get all repositories
    repos = get_all_repos(args.user, token=args.token)
    
    if not repos:
        print("No repositories found.")
        return
    
    print(f"\nFound {len(repos)} repositories.\n")
    print("Starting clone process...\n")
    
    # Clone each repository
    successful = 0
    failed = 0
    skipped = 0
    
    for i, repo in enumerate(repos, 1):
        print(f"[{i}/{len(repos)}] {repo['name']}")
        
        if args.skip_existing and (target_dir / repo['name']).exists():
            skipped += 1
            print(f"  ⏭️  Skipping {repo['name']} (already exists)")
            continue
        
        if clone_repo(repo, target_dir, use_ssh=args.ssh):
            successful += 1
        else:
            failed += 1
        
        # Small delay between clones to be respectful
        time.sleep(0.2)
    
    # Summary
    print("\n" + "="*60)
    print("Summary:")
    print(f"  ✅ Successfully cloned: {successful}")
    print(f"  ⏭️  Skipped (already exists): {skipped}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📦 Total: {len(repos)}")
    print("="*60)


if __name__ == '__main__':
    main()

