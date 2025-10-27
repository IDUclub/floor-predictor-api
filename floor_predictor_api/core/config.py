"""Application configuration class is defined here."""

import os
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

import yaml

from floor_predictor_api.__version__ import VERSION

from .logging import LoggingLevel


@dataclass
class AppConfig:
    """Represents application configuration."""

    host: str
    port: int
    debug: bool
    name: str

    def __post_init__(self):
        self.name = f"urban_api ({VERSION})"


@dataclass
class FileLogger:
    """Represents file-based logging configuration."""

    filename: str
    level: LoggingLevel


@dataclass
class LoggingConfig:
    """Represents the logging configuration for the application."""

    level: LoggingLevel
    files: list[FileLogger] = field(default_factory=list)

    def __post_init__(self):
        # If `files` is loaded as a list of dicts (e.g., from YAML), convert to FileLogger instances.
        if self.files and isinstance(self.files[0], dict):
            self.files = [FileLogger(**f) for f in self.files]


@dataclass
class PrometheusConfig:
    """Represents Prometheus metrics configuration."""

    port: int = 9000
    disable: bool = False


@dataclass
class ExternalAPIConfig:
    """Configuration for external API access."""

    host: str
    ping_timeout_seconds: float = 2.0
    operation_timeout_seconds: float = 120.0


@dataclass
class FileServerConfig:
    url: str
    bucket: str
    model_path: str
    access_key: str
    secret_key: str

    def __post_init__(self):
        if not self.url.startswith("http"):
            self.url = "http://" + self.url


@dataclass
class Config:
    """
    Main application configuration class.

    Combines all sub-configs and provides methods for serialization, deserialization, and merging.
    """

    app: AppConfig
    logging: LoggingConfig
    prometheus: PrometheusConfig
    urban_api: ExternalAPIConfig
    fileserver: FileServerConfig

    def to_order_dict(self) -> OrderedDict:
        """
        Convert this configuration to an OrderedDict recursively, suitable for YAML dumping.

        Returns:
            OrderedDict: Ordered representation of the config.
        """

        def to_ordered_dict_recursive(obj) -> OrderedDict:
            if isinstance(obj, (dict, OrderedDict)):
                return OrderedDict((k, to_ordered_dict_recursive(v)) for k, v in obj.items())
            if isinstance(obj, list):
                return [to_ordered_dict_recursive(item) for item in obj]
            if hasattr(obj, "__dataclass_fields__"):
                return OrderedDict(
                    (field, to_ordered_dict_recursive(getattr(obj, field))) for field in obj.__dataclass_fields__
                )
            return obj

        return OrderedDict(
            [
                ("app", to_ordered_dict_recursive(self.app)),
                ("logging", to_ordered_dict_recursive(self.logging)),
                ("prometheus", to_ordered_dict_recursive(self.prometheus)),
                ("urban_api", to_ordered_dict_recursive(self.urban_api)),
                ("fileserver", to_ordered_dict_recursive(self.fileserver)),
            ]
        )

    def dump(self, file: str | Path | TextIO) -> None:
        """
        Export the current configuration to a YAML file or stream.

        Args:
            file (str | Path | TextIO): Target file path or open file object.
        """

        class OrderedDumper(yaml.SafeDumper):
            """OrderedDump dump serializer."""

            def represent_dict_preserve_order(self, data):
                """Represent OrderedDict data as YAML dict."""
                return self.represent_dict(data.items())

        OrderedDumper.add_representer(OrderedDict, OrderedDumper.represent_dict_preserve_order)

        if isinstance(file, (str, Path)):
            with open(str(file), "w", encoding="utf-8") as file_w:
                yaml.dump(self.to_order_dict(), file_w, Dumper=OrderedDumper, default_flow_style=False)
        else:
            yaml.dump(self.to_order_dict(), file, Dumper=OrderedDumper, default_flow_style=False)

    @classmethod
    def example(cls) -> "Config":
        """
        Generate a sample AppConfig instance for testing or default usage.

        Returns:
            Config: Example configuration.
        """
        return cls(
            app=AppConfig(host="0.0.0.0", port=8000, debug=False, name="floor_predictor_api"),
            logging=LoggingConfig(level="INFO", files=[FileLogger(filename="logs/info.log", level="INFO")]),
            prometheus=PrometheusConfig(port=9000, disable=False),
            urban_api=ExternalAPIConfig(host="http://localhost:8100"),
            fileserver=FileServerConfig(
                url="http://localhost:9000",
                bucket="projects.images",
                model_path="models/model.joblib",
                access_key="access_key",
                secret_key="secret_key",
            ),
        )

    @classmethod
    def load(cls, file: str | Path | TextIO) -> "Config":
        """
        Load configuration from a YAML file or stream.

        Args:
            file (str | Path | TextIO): Path or open file stream to read from.

        Returns:
            Config: Loaded configuration.

        Raises:
            ValueError: If the file can't be read or parsed.
        """
        try:
            if isinstance(file, (str, Path)):
                with open(file, "r", encoding="utf-8") as file_r:
                    data = yaml.safe_load(file_r)
            else:
                data = yaml.safe_load(file)

            return cls(
                app=AppConfig(**data.get("app", {})),
                logging=LoggingConfig(**data.get("logging", {})),
                prometheus=PrometheusConfig(**data.get("prometheus", {})),
                urban_api=ExternalAPIConfig(**data.get("urban_api", {})),
                fileserver=FileServerConfig(**data.get("fileserver", {})),
            )
        except Exception as exc:
            print(exc)  # Can be replaced with structured logging if desired
            raise ValueError(f"Could not read app config file: {file}") from exc

    @classmethod
    def from_file_or_default(cls, config_path: str | None = os.getenv("CONFIG_PATH")) -> "Config":
        """
        Load configuration from the provided file path or return a default example if not found.

        Args:
            config_path (str | None): File path to load config from (defaults to CONFIG_PATH env var).

        Returns:
            Config: Loaded or fallback configuration.
        """
        if not config_path:
            return cls.example()
        return cls.load(config_path)

    def update(self, other: "Config") -> None:
        """
        Update the current configuration with values from another Config instance.

        Args:
            other (Config): The configuration instance to merge from.
        """
        for section in ("app", "logging", "prometheus", "urban_api", "fileserver"):
            current_subconfig = getattr(self, section)
            other_subconfig = getattr(other, section)

            for param, value in other_subconfig.__dict__.items():
                if param in current_subconfig.__dict__:
                    setattr(current_subconfig, param, value)
