from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ConfigBase(BaseModel):
    """Base config schema."""

    content: Dict[str, Any] = Field(..., description="Configuration content")
    message: Optional[str] = Field(None, description="Optional commit message")


class ConfigCreate(ConfigBase):
    """Schema for creating a config."""

    pass


class ConfigUpdate(ConfigBase):
    """Schema for updating a config."""

    pass


class ConfigVersion(BaseModel):
    """Schema for config version information."""

    version: int
    commit_sha: str
    commit_message: str
    author: str
    date: datetime
    content: Dict[str, Any]


class ConfigVersions(BaseModel):
    """Schema for paginated config versions."""

    total: int
    skip: int
    limit: int
    versions: list[ConfigVersion]


class ConfigInfo(BaseModel):
    """Schema for config file information."""

    name: str
    format: str
    path: str
