import os
import sys
import requests
import json
import logging
import base64
from dotenv import load_dotenv
from typing import Dict, List, Any

class GitHubAPI:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        if not token:
            raise ValueError("GitHub token is required")
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        }
    
    def _get(self, endpoint: str) -> Any:
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data from GitHub: {e}")
            raise

    def get_repository_details(self, repo_name: str) -> Dict[str, Any]:
        return self._get(f"repos/{repo_name}")

    def get_repositories(self) -> List[Dict[str, Any]]:
        all_repos = self._get("user/repos")
        return [repo for repo in all_repos if repo.get("permissions", {}).get("push")] if all_repos else []

    def get_file_content(self, repo_name: str, file_path: str) -> Dict[str, Any]:
        repository_details = self.get_repository_details(repo_name)
        if not repository_details:
            return {"error": "Repository not found"}

        branch = repository_details.get("default_branch", "main")
        try:
            file_data = self._get(f"repos/{repo_name}/contents/{file_path}?ref={branch}")
            if not file_data or "content" not in file_data:
                return {"error": f"File '{file_path}' not found on branch '{branch}'"}
            
            decoded_content = base64.b64decode(file_data["content"]).decode("utf-8")
            return {"path": file_data["path"], "content": decoded_content, "url": file_data["url"]}
        except (UnicodeDecodeError, TypeError):
            return {"error": "Failed to decode file content"}
        except Exception as e:
            return {"error": f"Error fetching file: {str(e)}"}
    
    def list_files_in_repository(self, repo_name: str) -> List[Dict[str, Any]]:
        repo_details = self.get_repository_details(repo_name)
        if not repo_details:
            return {"error": "Repository not found"}
        
        branch = repo_details.get("default_branch", "main")
        try:
            contents = self._get(f"repos/{repo_name}/git/trees/{branch}?recursive=1")
            if not contents or "tree" not in contents:
                return []
            return [{"name": item["path"].split("/")[-1], "type": item["type"], "path": item["path"]} 
                   for item in contents["tree"]]
        except Exception as e:
            return {"error": f"Error listing files: {str(e)}"}

def print_usage():
    usage = """
GitHub API Tool for Windsurf
Usage: python github_tools.py <command> <args>

Commands:
    list-repos                    List all repositories for the authenticated user
    list-files <repo_name>        List all files in a repository
    get-file-content <repo_name> <file_path>  Get the content of a file
    """
    print(usage, file=sys.stderr)

def main():
    args = sys.argv[1:]
    if not args:
        print_usage()
        return
    
    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logging.error("GITHUB_TOKEN not found in environment variables")
        return
        
    api = GitHubAPI(github_token)
    command = args[0]
    result = {}

    try:
        if command == "list-repos":
            result = api.get_repositories()
        elif command == "list-files":
            if len(args) < 2:
                print("Error: repo_name is required for list-files command", file=sys.stderr)
                print_usage()
                return
            repo_name = args[1]
            result = api.list_files_in_repository(repo_name)
        elif command == "get-file-content":
            if len(args) < 3:
                print("Error: repo_name and file_path are required for get-file-content command", file=sys.stderr)
                print_usage()
                return
            repo_name = args[1]
            file_path = args[2]
            result = api.get_file_content(repo_name, file_path)
        else:
            print_usage()
            return
        
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": f"An unexpected error occurred: {str(e)}"}, indent=2), file=sys.stderr)

if __name__ == "__main__":
    main()