import json
import xml.etree.ElementTree as ET
from typing import Any, Dict

import toml
from fastapi import HTTPException

from app.core.config import get_settings

settings = get_settings()


def parse_config_content(content: str, file_format: str) -> Dict[str, Any]:
    """Parse config content based on file format."""
    try:
        if file_format == "json":
            return json.loads(content)
        elif file_format == "toml":
            return toml.loads(content)
        elif file_format == "xml":
            root = ET.fromstring(content)
            return {elem.tag: elem.text for elem in root}
        else:
            raise ValueError(f"Unsupported format: {file_format}")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid {file_format} format: {str(e)}"
        )


def format_config_content(data: Dict[str, Any], file_format: str) -> str:
    """Format config data based on file format."""
    if file_format not in settings.supported_formats:
        raise ValueError(f"Unsupported format: {file_format}")

    try:
        if file_format == "json":
            return json.dumps(data, indent=2)
        elif file_format == "toml":
            return toml.dumps(data)
        elif file_format == "xml":
            root = ET.Element("config")
            for key, value in data.items():
                elem = ET.SubElement(root, str(key))
                elem.text = str(value)
            return ET.tostring(root, encoding="unicode")
    except Exception as e:
        raise ValueError(f"Error formatting {file_format}: {str(e)}")


def extract_version_number(commit_message: str) -> int:
    """Extract version number from commit message if it exists."""
    try:
        if "[Version " in commit_message:
            version_str = commit_message.split("[Version ")[1].split("]")[0]
            return int(version_str)
    except Exception:
        pass
    return None


def create_version_message(message: str, version: int) -> str:
    """Create a commit message with version number."""
    return f"{message} [Version {version}]"


def get_default_message(operation: str, config_name: str) -> str:
    """Get default commit message for various operations."""
    operation_messages = {
        "create": f"Create configuration '{config_name}'",
        "update": f"Update configuration '{config_name}'",
        "delete": f"Delete configuration '{config_name}'",
        "restore": lambda v: f"Restore configuration '{config_name}' to version {v}",
    }

    message = operation_messages.get(operation)
    if callable(message):
        return message
    return message
