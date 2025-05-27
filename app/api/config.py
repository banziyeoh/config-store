import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.schemas.config import (
    ConfigCreate,
    ConfigInfo,
    ConfigUpdate,
    ConfigVersion,
    ConfigVersions,
)
from app.services.config import (
    create_version_message,
    extract_version_number,
    format_config_content,
    get_default_message,
    parse_config_content,
)
from app.services.github import GitHubService

router = APIRouter()
logger = logging.getLogger(__name__)


def get_github_service():
    """Dependency for GitHub service."""
    return GitHubService()


@router.get(
    "/",
    summary="Health Check",
    description="Check if the API is running",
    response_description="A message indicating the API status",
)
def root():
    """Health check endpoint."""
    return {"message": "Config Store API is running."}


@router.post(
    "/configs/{project}/{config_name}",
    summary="Create Config",
    description="Create a new configuration file in the specified project",
    response_description="Success message with commit SHA",
    responses={
        200: {"description": "Config created successfully"},
        400: {"description": "Invalid format or config already exists"},
        404: {"description": "Project not found"},
    },
)
async def create_config(
    project: str = Path(..., description="Project identifier"),
    config_name: str = Path(..., description="Name of the configuration"),
    file_format: str = Query(..., description="File format (json, toml, or xml)"),
    config: ConfigCreate = None,
    github: GitHubService = Depends(get_github_service),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Create a new config file in the specified project."""
    if file_format not in settings.supported_formats:
        raise HTTPException(
            status_code=400, detail=f"Unsupported format: {file_format}"
        )

    try:
        file_path = f"{project}/{config_name}.{file_format}"
        formatted_content = format_config_content(config.content, file_format)

        # Use provided message or default
        base_message = config.message or get_default_message("create", config_name)
        commit_message = create_version_message(base_message, 1)

        result = github.create_file(
            path=file_path,
            message=commit_message,
            content=formatted_content,
            branch=project,
        )

        return JSONResponse(
            status_code=200,
            content={
                "message": f"Config {config_name} created successfully as version 1",
                "commit_sha": result["sha"],
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/configs/{project}/{config_name}",
    summary="Read Config",
    description="Read a configuration file from the specified project",
    response_description="Configuration content",
    responses={
        200: {"description": "Config content successfully retrieved"},
        400: {"description": "Invalid format"},
        404: {"description": "Config not found"},
    },
)
async def read_config(
    project: str = Path(..., description="Project identifier"),
    config_name: str = Path(..., description="Name of the configuration"),
    file_format: str = Query(..., description="File format (json, toml, or xml)"),
    github: GitHubService = Depends(get_github_service),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Read a config file from the specified project."""
    if file_format not in settings.supported_formats:
        raise HTTPException(
            status_code=400, detail=f"Unsupported format: {file_format}"
        )

    file_path = f"{project}/{config_name}.{file_format}"
    content, _ = github.get_file(file_path, ref=project)
    return parse_config_content(content, file_format)


@router.put(
    "/configs/{project}/{config_name}",
    summary="Update Config",
    description="Update an existing configuration file in the specified project",
    response_description="Success message with new version and commit SHA",
    responses={
        200: {"description": "Config updated successfully"},
        400: {"description": "Invalid format or content"},
        404: {"description": "Config not found"},
    },
)
async def update_config(
    project: str = Path(..., description="Project identifier"),
    config_name: str = Path(..., description="Name of the configuration"),
    file_format: str = Query(..., description="File format (json, toml, or xml)"),
    config: ConfigUpdate = None,
    github: GitHubService = Depends(get_github_service),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Update an existing config file in the specified project."""
    if file_format not in settings.supported_formats:
        raise HTTPException(
            status_code=400, detail=f"Unsupported format: {file_format}"
        )

    try:
        file_path = f"{project}/{config_name}.{file_format}"

        # Get current version
        _, file_sha = github.get_file(file_path, ref=project)

        # Format new content
        formatted_content = format_config_content(config.content, file_format)

        # Get next version number
        commits = github.get_commits(file_path, project)
        next_version = 1
        for commit in commits:
            version = extract_version_number(commit.commit.message)
            if version:
                next_version = version + 1
                break

        # Update file with version
        base_message = config.message or get_default_message("update", config_name)
        commit_message = create_version_message(base_message, next_version)

        result = github.update_file(
            path=file_path,
            message=commit_message,
            content=formatted_content,
            sha=file_sha,
            branch=project,
        )

        return JSONResponse(
            status_code=200,
            content={
                "message": f"Config {config_name} updated successfully",
                "version": next_version,
                "commit_sha": result["sha"],
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/configs/{project}/{config_name}",
    summary="Delete Config",
    description="Delete a configuration file from the specified project",
    response_description="Success message",
    responses={
        200: {"description": "Config deleted successfully"},
        400: {"description": "Invalid format"},
        404: {"description": "Config not found"},
    },
)
async def delete_config(
    project: str = Path(..., description="Project identifier"),
    config_name: str = Path(..., description="Name of the configuration"),
    file_format: str = Query(..., description="File format (json, toml, or xml)"),
    message: Optional[str] = Query(None, description="Optional commit message"),
    github: GitHubService = Depends(get_github_service),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Delete a config file from the specified project."""
    if file_format not in settings.supported_formats:
        raise HTTPException(
            status_code=400, detail=f"Unsupported format: {file_format}"
        )

    file_path = f"{project}/{config_name}.{file_format}"
    _, file_sha = github.get_file(file_path, ref=project)

    base_message = message or get_default_message("delete", config_name)
    github.delete_file(
        path=file_path,
        message=base_message,
        sha=file_sha,
        branch=project,
    )

    return JSONResponse(
        status_code=200,
        content={"message": f"Config {config_name} deleted successfully"},
    )


@router.get(
    "/configs/{project}",
    summary="List Configs",
    description="List all configuration files in a project",
    response_description="List of configuration files",
    responses={
        200: {"description": "List of configs successfully retrieved"},
        404: {"description": "Project not found"},
    },
)
async def list_configs(
    project: str = Path(..., description="Project identifier"),
    github: GitHubService = Depends(get_github_service),
) -> List[ConfigInfo]:
    """List all config files in a project."""
    contents = github.list_contents(project, ref=project)
    configs = []

    for item in contents:
        if item.type == "file":
            name, ext = os.path.splitext(item.name)
            configs.append(
                ConfigInfo(
                    name=name,
                    format=ext[1:],  # Remove the dot from extension
                    path=item.path,
                )
            )

    return configs


@router.get(
    "/configs/{project}/{config_name}/versions",
    summary="List Config Versions",
    description="List versions of a specific configuration file with pagination",
    response_description="List of config versions with their content",
    responses={
        200: {"description": "Version list successfully retrieved"},
        400: {"description": "Invalid format"},
        404: {"description": "Config not found"},
    },
)
async def list_config_versions(
    project: str = Path(..., description="Project identifier"),
    config_name: str = Path(..., description="Name of the configuration"),
    file_format: str = Query(..., description="File format (json, toml, or xml)"),
    skip: int = Query(0, description="Number of versions to skip for pagination", ge=0),
    limit: int = Query(
        10, description="Maximum number of versions to return", ge=1, le=100
    ),
    github: GitHubService = Depends(get_github_service),
    settings: Settings = Depends(get_settings),
) -> ConfigVersions:
    """List versions of a specific config file with pagination."""
    if file_format not in settings.supported_formats:
        raise HTTPException(
            status_code=400, detail=f"Unsupported format: {file_format}"
        )

    file_path = f"{project}/{config_name}.{file_format}"

    # Verify file exists
    github.get_file(file_path, ref=project)

    # Get commit history
    commits = list(github.get_commits(file_path, project))
    total_commits = len(commits)
    versions = []

    # Process commits in page
    start_idx = skip
    end_idx = min(skip + limit, total_commits)

    for commit in commits[start_idx:end_idx]:
        try:
            content, _ = github.get_file(file_path, ref=commit.sha)
            parsed_content = parse_config_content(content, file_format)

            version_number = extract_version_number(commit.commit.message)
            if version_number is None:
                continue

            versions.append(
                ConfigVersion(
                    version=version_number,
                    commit_sha=commit.sha,
                    commit_message=commit.commit.message,
                    author=commit.commit.author.name,
                    date=commit.commit.author.date,
                    content=parsed_content,
                )
            )
        except Exception as e:
            logger.error(f"Failed to process version: {e}")
            continue

    return ConfigVersions(
        total=total_commits,
        skip=skip,
        limit=limit,
        versions=versions,
    )


@router.post(
    "/configs/{project}/{config_name}/recover/{version}",
    summary="Recover Config Version",
    description="Recover a configuration file to a specific version number",
    response_description="Success message with version information",
    responses={
        200: {"description": "Config version recovered successfully"},
        400: {"description": "Invalid format"},
        404: {"description": "Config or version not found"},
    },
)
async def recover_config_version(
    project: str = Path(..., description="Project identifier"),
    config_name: str = Path(..., description="Name of the configuration"),
    version: int = Path(..., description="Version number to recover", ge=1),
    file_format: str = Query(..., description="File format (json, toml, or xml)"),
    message: Optional[str] = Query(None, description="Optional commit message"),
    github: GitHubService = Depends(get_github_service),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Recover a config file to a specific version number."""
    if file_format not in settings.supported_formats:
        raise HTTPException(
            status_code=400, detail=f"Unsupported format: {file_format}"
        )

    file_path = f"{project}/{config_name}.{file_format}"

    # Find the commit with the specified version number
    target_commit = None
    commits = github.get_commits(file_path, project)

    for commit in commits:
        if extract_version_number(commit.commit.message) == version:
            target_commit = commit
            break

    if target_commit is None:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")

    # Get content from target version
    content, _ = github.get_file(file_path, ref=target_commit.sha)

    # Get current file SHA
    _, current_sha = github.get_file(file_path, ref=project)

    # Get next version number
    next_version = 1
    for commit in commits:
        current_version = extract_version_number(commit.commit.message)
        if current_version:
            next_version = current_version + 1
            break

    # Update file with old content
    base_message = message or get_default_message("restore", config_name)(version)
    commit_message = create_version_message(base_message, next_version)

    result = github.update_file(
        path=file_path,
        message=commit_message,
        content=content,
        sha=current_sha,
        branch=project,
    )

    return JSONResponse(
        status_code=200,
        content={
            "message": f"Config {config_name} restored to version {version}",
            "original_version": version,
            "new_version": next_version,
            "commit_sha": result["sha"],
        },
    )
