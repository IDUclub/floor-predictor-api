import os
from minio import Minio

from floor_predictor_api.core.config import FileServerConfig


def download_model_from_minio(config: FileServerConfig, tmp_path: str) -> None:
    """
    Downloads model from MinIO to temporary file.

    Args:
        config: FileServerConfig with MinIO connection params.
        tmp_path: Path where to save the model file locally.

    Returns:
        str: Path to the downloaded (or existing) model file.
    """
    if not os.path.exists(tmp_path):
        raise FileNotFoundError(f"Not found temporary file with name: {tmp_path}")

    client = Minio(
        endpoint=config.url.replace("http://", "").replace("https://", ""),
        access_key=config.access_key,
        secret_key=config.secret_key,
        secure=config.url.startswith("https"),
    )

    client.fget_object(config.bucket, config.model_path, tmp_path)
