import logging
from typing import Any

from fastapi import HTTPException
from github import Auth, Github, GithubException

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub."""

    def __init__(self):
        if not settings.github_token:
            raise Exception("GITHUB_TOKEN not set in .env")
        self.auth = Auth.Token(settings.github_token)
        self.github = Github(auth=self.auth)
        self.repo = self._get_repo()

    def _get_repo(self):
        """Get the GitHub repository instance."""
        try:
            repo_name = settings.github_repo.split("github.com/")[-1].replace(
                ".git", ""
            )
            return self.github.get_repo(repo_name)
        except GithubException as e:
            logger.error(f"Failed to get GitHub repository: {e}")
            raise HTTPException(status_code=500, detail="Failed to connect to GitHub")

    def create_file(
        self, path: str, message: str, content: str, branch: str
    ) -> dict[str, Any]:
        """Create a new file in the repository."""
        try:
            result = self.repo.create_file(
                path=path, message=message, content=content, branch=branch
            )
            return {"sha": result["commit"].sha}
        except GithubException as e:
            if e.status == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Project not found: {str(e.data.get('message', ''))}",
                )
            elif "already exists" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail=f"Config already exists: {str(e.data.get('message', ''))}",
                )
            raise HTTPException(status_code=500, detail=str(e))

    def get_file(self, path: str, ref: str) -> tuple[str, str]:
        """Get file content and SHA from the repository."""
        try:
            content = self.repo.get_contents(path, ref=ref)
            return content.decoded_content.decode(), content.sha
        except GithubException as e:
            if e.status == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Config not found: {str(e.data.get('message', ''))}",
                )
            raise HTTPException(status_code=500, detail=str(e))

    def update_file(
        self, path: str, message: str, content: str, sha: str, branch: str
    ) -> dict[str, Any]:
        """Update an existing file in the repository."""
        try:
            result = self.repo.update_file(
                path=path, message=message, content=content, sha=sha, branch=branch
            )
            return {"sha": result["commit"].sha}
        except GithubException as e:
            raise HTTPException(status_code=500, detail=str(e))

    def delete_file(self, path: str, message: str, sha: str, branch: str) -> None:
        """Delete a file from the repository."""
        try:
            self.repo.delete_file(path=path, message=message, sha=sha, branch=branch)
        except GithubException as e:
            if e.status == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Config not found: {str(e.data.get('message', ''))}",
                )
            raise HTTPException(status_code=500, detail=str(e))

    def get_commits(self, path: str, branch: str):
        """Get commits for a file."""
        try:
            return self.repo.get_commits(path=path, sha=branch)
        except GithubException as e:
            raise HTTPException(status_code=500, detail=str(e))

    def list_contents(self, path: str, ref: str):
        """List contents of a directory."""
        try:
            return self.repo.get_contents(path, ref=ref)
        except GithubException as e:
            if e.status == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Project not found: {str(e.data.get('message', ''))}",
                )
            raise HTTPException(status_code=500, detail=str(e))
