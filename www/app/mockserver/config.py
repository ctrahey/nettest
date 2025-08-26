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
    lognormal_latency_mean: float = Field(
        description="Mean latency in seconds for latency distribution",
        default=0.0,
        ge=0.0,
    )
    lognormal_latency_std_deviation: float = Field(
        description="Standard deviation in seconds for latency distribution",
        default=0.0,
        ge=0.0,
    )
    media_type: str = Field(
        description="MIME type for Content Type header in response.",
        default=None
    )


class NettestConfig(BaseModel):
    redact_headers: List[str] = Field(
        default_factory=list,
        description="Headers listed here will be redacted from logs and responses",
    )

    mock_server_configs: List[MockEndpointConfig] = Field(default_factory=list)

    seed: int = Field(description="Seed for random number generator", default=None)
