import pytest
from fastapi.testclient import TestClient
from github import GithubException
from jinja2 import Template

from app.main import app
from app.services.github import GitHubService

client = TestClient(app)


@pytest.fixture(scope="function")
def github_repo():
    """Fixture that provides access to the test GitHub repo and cleans up after tests."""
    github_service = GitHubService()
    repo = github_service.repo
    test_project = "test_project"

    # Delete test branch if it exists
    try:
        ref = repo.get_git_ref(f"heads/{test_project}")
        ref.delete()
    except GithubException:
        pass

    # Create new test branch from main
    main_branch = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{test_project}", sha=main_branch.commit.sha)

    yield repo

    # Clean up test branch after test
    try:
        ref = repo.get_git_ref(f"heads/{test_project}")
        ref.delete()
    except GithubException:
        pass


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Config Store API is running."}


def test_create_config(github_repo):
    request = {"content": {"key": "value"}, "message": "Test commit message"}
    response = client.post(
        "/configs/test_project/test_config",
        params={"file_format": "json"},
        json=request,
    )
    assert response.status_code == 200
    assert "created successfully" in response.json()["message"]

    # Verify the file was actually created
    file_content = github_repo.get_contents(
        "test_project/test_config.json", ref="test_project"
    )
    assert file_content is not None


def test_read_config(github_repo):
    # First create a config to read
    request = {"content": {"key": "value"}, "message": "Initial commit"}
    client.post(
        "/configs/test_project/test_config",
        params={"file_format": "json"},
        json=request,
    )

    response = client.get(
        "/configs/test_project/test_config", params={"file_format": "json"}
    )
    assert response.status_code == 200
    assert response.json() == {"key": "value"}


def test_update_config(github_repo):
    # First create a config to update
    initial_request = {"content": {"key": "value"}, "message": "Initial commit"}
    client.post(
        "/configs/test_project/test_config",
        params={"file_format": "json"},
        json=initial_request,
    )

    update_request = {"content": {"key": "new_value"}, "message": "Update commit"}
    response = client.put(
        "/configs/test_project/test_config",
        params={"file_format": "json"},
        json=update_request,
    )
    assert response.status_code == 200
    assert "updated successfully" in response.json()["message"]

    # Verify the content was updated
    response = client.get(
        "/configs/test_project/test_config", params={"file_format": "json"}
    )
    assert response.json() == update_request["content"]


def test_delete_config(github_repo):
    # First create a config to delete
    request = {"content": {"key": "value"}, "message": "Initial commit"}
    client.post(
        "/configs/test_project/test_config",
        params={"file_format": "json"},
        json=request,
    )

    response = client.delete(
        "/configs/test_project/test_config", params={"file_format": "json"}
    )
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify the file was deleted
    with pytest.raises(GithubException) as excinfo:
        github_repo.get_contents("test_project/test_config.json", ref="test_project")
    assert excinfo.value.status == 404


def test_list_configs(github_repo):
    # Create some test configs
    configs = [
        ("config1", {"key1": "value1"}),
        ("config2", {"key2": "value2"}),
    ]

    for name, content in configs:
        request = {"content": content, "message": f"Create config {name}"}
        client.post(
            f"/configs/test_project/{name}",
            params={"file_format": "json"},
            json=request,
        )

    response = client.get("/configs/test_project")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 2
    assert {
        "name": "config1",
        "format": "json",
        "path": "test_project/config1.json",
    } in result
    assert {
        "name": "config2",
        "format": "json",
        "path": "test_project/config2.json",
    } in result


def test_list_config_versions(github_repo):
    # Make sure we start with a clean slate
    config_path = "test_project/versioned_config.json"
    try:
        file = github_repo.get_contents(config_path, ref="test_project")
        github_repo.delete_file(
            path=config_path,
            message="Cleanup versioned config",
            sha=file.sha,
            branch="test_project",
        )
    except GithubException:
        pass  # File doesn't exist yet, which is fine

    # Create and update a config to generate versions
    config_name = "versioned_config"
    create_request = {"content": {"version": "1"}, "message": "Initial version"}
    update_request = {"content": {"version": "2"}, "message": "Update version"}

    client.post(
        f"/configs/test_project/{config_name}",
        params={"file_format": "json"},
        json=create_request,
    )

    client.put(
        f"/configs/test_project/{config_name}",
        params={"file_format": "json"},
        json=update_request,
    )

    response = client.get(
        f"/configs/test_project/{config_name}/versions",
        params={"file_format": "json", "skip": 0, "limit": 10},
    )

    assert response.status_code == 200
    result = response.json()
    assert "versions" in result
    assert len(result["versions"]) == 2
    assert result["versions"][0]["version"] == 2
    assert result["versions"][1]["version"] == 1


def test_recover_config_version(github_repo):
    # Create and update a config to generate versions
    config_name = "recoverable_config"
    create_request = {"content": {"version": "1"}, "message": "Initial version"}
    update_request = {"content": {"version": "2"}, "message": "Update version"}

    client.post(
        f"/configs/test_project/{config_name}",
        params={"file_format": "json"},
        json=create_request,
    )

    client.put(
        f"/configs/test_project/{config_name}",
        params={"file_format": "json"},
        json=update_request,
    )

    response = client.post(
        f"/configs/test_project/{config_name}/recover/1",
        params={"file_format": "json"},
    )

    assert response.status_code == 200
    assert "restored to version 1" in response.json()["message"]

    # Verify the content was restored
    response = client.get(
        f"/configs/test_project/{config_name}", params={"file_format": "json"}
    )
    assert response.json() == create_request["content"]


def test_config_not_found(github_repo):
    response = client.get(
        "/configs/test_project/nonexistent", params={"file_format": "json"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_invalid_json_format():
    content = "invalid json"
    response = client.post(
        "/configs/test_project/test_config",
        params={"file_format": "json"},
        json=content,
    )
    assert response.status_code == 422  # FastAPI validation error


def test_format_error():
    request = {"content": {"key": "value"}, "message": "Test unsupported format"}
    response = client.post(
        "/configs/test_project/test_config",
        params={"file_format": "yaml"},  # Unsupported format
        json=request,
    )
    assert response.status_code == 400
    assert "unsupported format" in response.json()["detail"].lower()


def test_invalid_jinja2_template(github_repo):
    """Test creating an invalid Jinja2 template."""
    template_content = """Hello {{ name!"""  # Invalid syntax: unclosed variable
    request = {
        "content": {"template": template_content},
        "message": "Create invalid Jinja2 template",
    }
    response = client.post(
        "/configs/test_project/invalid_template",
        params={"file_format": "jinja2"},
        json=request,
    )
    assert response.status_code == 400
    error_detail = response.json()["detail"].lower()
    assert "invalid jinja2 template" in error_detail


def test_create_jinja2_template(github_repo):
    """Test creating a Jinja2 template configuration."""
    template_content = """Hello {{ name }}!
Your age is {{ age }}.
{% if is_admin %}
You have admin access.
{% endif %}"""
    request = {
        "content": {"template": template_content},
        "message": "Create Jinja2 template",
    }
    response = client.post(
        "/configs/test_project/template_config",
        params={"file_format": "jinja2"},
        json=request,
    )
    assert response.status_code == 200
    assert "created successfully" in response.json()["message"]

    # Verify the template was saved
    response = client.get(
        "/configs/test_project/template_config", params={"file_format": "jinja2"}
    )
    assert response.status_code == 200
    content = response.json()
    assert "template" in content
    assert template_content == content["template"]
    assert "variables" in content
    variables = set(content["variables"])
    assert variables == {"name", "age", "is_admin"}


def test_invalid_jinja2_template(github_repo):
    """Test creating an invalid Jinja2 template."""
    template_content = """Hello {{ name!
Invalid template
{% endif %}"""  # Invalid syntax: unclosed variable and unexpected endif
    request = {
        "content": {"template": template_content},
        "message": "Create invalid Jinja2 template",
    }
    response = client.post(
        "/configs/test_project/invalid_template",
        params={"file_format": "jinja2"},
        json=request,
    )
    assert response.status_code == 400
    error_detail = response.json()["detail"].lower()
    assert any(msg in error_detail for msg in ["invalid jinja2", "invalid template"])
