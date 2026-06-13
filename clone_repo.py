import os
import shutil
import tempfile
import requests
from git import Repo
from dotenv import load_dotenv
load_dotenv()

# =====================================================
# GITHUB TOKEN - replace with your new token
# =====================================================

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


def get_headers():
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def fetch_repository_info(repo_url):
    """
    Calls the GitHub REST API and returns a plain dict
    with repo metadata. Has NO dependency on gitpython.
    """
    try:
        parts = repo_url.strip().rstrip("/").split("/")
        if len(parts) < 2:
            print("Invalid GitHub URL format.")
            return None

        owner = parts[-2]
        repo  = parts[-1]

        api_url  = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(api_url, headers=get_headers(), timeout=15)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"Repository not found: {owner}/{repo}")
        elif response.status_code == 403:
            print("GitHub API rate limit hit. Set GITHUB_TOKEN env variable.")
        else:
            print(f"GitHub API error {response.status_code}: {response.text}")

        return None

    except Exception as e:
        print(f"Error fetching repository info: {e}")
        return None


def clone_repo(repo_url):
    """
    Clones the GitHub repo into a temp folder using gitpython.
    Returns the folder path (str) on success, None on failure.
    """
    tmp_dir = tempfile.mkdtemp(prefix="repo_")

    try:
        Repo.clone_from(repo_url, tmp_dir)
        return tmp_dir

    except Exception as e:
        print(f"Git clone failed: {e}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None