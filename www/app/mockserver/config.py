from typing import List
from enum import StrEnum
from pydantic import BaseModel, Field


class Method(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class MockEndpointConfig(BaseModel):
    methods: List[Method] = Field(default=[Method.GET])
    mount_paths: List[str] = Field(default=["/mock"])
    source_files_directory: str = Field(
        description="Directory where response files are mounted", default=None
    )
    error_probability: float = Field(
        description="Probability of 5xx error", default=0.0
    )
    latency_median: float = Field(description="Median latency in seconds", default=0.0)
    latency_std_deviation: float = Field(
        description="Standard deviation in seconds", default=0.0
    )


class NettestConfig(BaseModel):
    redact_headers: List[str] = Field(
        default_factory=list,
        description="Headers listed here will be redacted from logs and responses",
    )

    mock_server_configs: List[MockEndpointConfig] = Field(default_factory=list)
