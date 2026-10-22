"""S3-compatible private object storage for durable binary assets.

Configure all four KAE_OBJECT_* environment variables to enable it. If absent,
local filesystem storage remains available for development, but is not durable
on Render free web services.
"""
import io
import os
from functools import lru_cache


def configured():
    return all(os.environ.get(key, "").strip() for key in (
        "KAE_OBJECT_ENDPOINT_URL",
        "KAE_OBJECT_BUCKET",
        "KAE_OBJECT_ACCESS_KEY_ID",
        "KAE_OBJECT_SECRET_ACCESS_KEY",
    ))


def _required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not configured")
    return value


@lru_cache(maxsize=1)
def _client():
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError("Object storage is configured but boto3 is not installed") from exc
    return boto3.client(
        "s3",
        endpoint_url=_required("KAE_OBJECT_ENDPOINT_URL"),
        aws_access_key_id=_required("KAE_OBJECT_ACCESS_KEY_ID"),
        aws_secret_access_key=_required("KAE_OBJECT_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("KAE_OBJECT_REGION", "auto").strip() or "auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def _bucket():
    return _required("KAE_OBJECT_BUCKET")


def put(key, data, content_type):
    _client().put_object(
        Bucket=_bucket(), Key=key, Body=data, ContentType=content_type,
        ServerSideEncryption="AES256",
    )


def get(key):
    response = _client().get_object(Bucket=_bucket(), Key=key)
    stream = io.BytesIO(response["Body"].read())
    stream.seek(0)
    return stream


def delete(key):
    _client().delete_object(Bucket=_bucket(), Key=key)


def check_connection():
    """Check access to the configured bucket without listing user assets."""
    _client().head_bucket(Bucket=_bucket())
    return True
