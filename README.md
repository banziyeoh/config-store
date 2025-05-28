# Config Store

A FastAPI-based service that provides version-controlled configuration management using GitHub as a backend storage.

## Features

- Store and manage configuration files in JSON, YAML, TOML, and XML formats
- Version control with automatic versioning
- Project-based organization
- Full history tracking
- Version recovery
- RESTful API interface

## Prerequisites

- Python 3.8+
- GitHub account and personal access token
- Git repository for storing configurations

## Installation

1. Clone the repository:

```bash
git clone https://github.com/banziyeoh/config-store.git
cd config-store
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:

```env
GITHUB_REPO=https://github.com/username/repo
GITHUB_TOKEN=your_github_token
```

## Usage

1. Start the server:

```bash
uvicorn app.main:app --reload
```

2. Access the API documentation at `http://localhost:8000/docs`

## API Endpoints

- `GET /` - Health check
- `POST /configs/{project}/{config_name}` - Create new config
- `GET /configs/{project}/{config_name}` - Read config
- `PUT /configs/{project}/{config_name}` - Update config
- `DELETE /configs/{project}/{config_name}` - Delete config
- `GET /configs/{project}` - List all configs in project
- `GET /configs/{project}/{config_name}/versions` - List config versions
- `POST /configs/{project}/{config_name}/recover/{version}` - Recover specific version

## Development

### Running Tests

```bash
pytest
```

## License

MIT
