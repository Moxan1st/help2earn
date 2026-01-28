"""
Storage Skill - Google Cloud Storage for image uploads

Handles image storage operations:
- Upload images to GCS
- Generate signed URLs for access
- Delete images
"""

import os
import uuid
import logging
from datetime import timedelta
from typing import Optional

from google.cloud import storage
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

# Configuration
GCS_PROJECT_ID = os.getenv("GCS_PROJECT_ID", "")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "help2earn-images")
CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")


class GCSClient:
    """Google Cloud Storage client singleton."""
    _client: Optional[storage.Client] = None
    _bucket: Optional[storage.Bucket] = None

    @classmethod
    def get_client(cls) -> storage.Client:
        """Get or create the GCS client."""
        if cls._client is None:
            if CREDENTIALS_PATH and os.path.exists(CREDENTIALS_PATH):
                credentials = service_account.Credentials.from_service_account_file(
                    CREDENTIALS_PATH
                )
                cls._client = storage.Client(
                    project=GCS_PROJECT_ID,
                    credentials=credentials
                )
            else:
                # Use default credentials (for Cloud Run, GCE, etc.)
                cls._client = storage.Client(project=GCS_PROJECT_ID)
        return cls._client

    @classmethod
    def get_bucket(cls) -> storage.Bucket:
        """Get the storage bucket."""
        if cls._bucket is None:
            client = cls.get_client()
            cls._bucket = client.bucket(GCS_BUCKET_NAME)
        return cls._bucket


async def upload_image(
    image_data: bytes,
    facility_type: str,
    content_type: str = "image/jpeg"
) -> dict:
    """
    Upload an image to Google Cloud Storage.

    Args:
        image_data: Raw image bytes
        facility_type: Type of facility (for organizing in folders)
        content_type: MIME type of the image

    Returns:
        dict with:
        - success: Whether upload succeeded
        - url: Public URL of the uploaded image
        - blob_name: Name of the blob in GCS
    """
    try:
        bucket = GCSClient.get_bucket()

        # Generate unique filename
        file_id = str(uuid.uuid4())
        extension = "jpg" if "jpeg" in content_type else content_type.split("/")[-1]
        blob_name = f"facilities/{facility_type}/{file_id}.{extension}"

        # Create blob and upload
        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            image_data,
            content_type=content_type
        )

        # Make publicly accessible (or use signed URLs for private access)
        blob.make_public()

        logger.info(f"Image uploaded: {blob_name}")

        return {
            "success": True,
            "url": blob.public_url,
            "blob_name": blob_name
        }

    except Exception as e:
        logger.error(f"Failed to upload image: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": None,
            "blob_name": None
        }


async def get_image_url(blob_name: str, expiration_hours: int = 24) -> Optional[str]:
    """
    Get a signed URL for an image (for private buckets).

    Args:
        blob_name: Name of the blob in GCS
        expiration_hours: URL expiration time in hours

    Returns:
        Signed URL or None if failed
    """
    try:
        bucket = GCSClient.get_bucket()
        blob = bucket.blob(blob_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET"
        )

        return url

    except Exception as e:
        logger.error(f"Failed to generate signed URL: {e}")
        return None


async def delete_image(blob_name: str) -> bool:
    """
    Delete an image from GCS.

    Args:
        blob_name: Name of the blob to delete

    Returns:
        True if deleted, False otherwise
    """
    try:
        bucket = GCSClient.get_bucket()
        blob = bucket.blob(blob_name)
        blob.delete()

        logger.info(f"Image deleted: {blob_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete image: {e}")
        return False


def get_public_url(blob_name: str) -> str:
    """
    Get the public URL for an image.

    Args:
        blob_name: Name of the blob

    Returns:
        Public URL
    """
    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_name}"


# Skill registration for SpoonOS
def skill(name: str):
    """Decorator for registering skills with SpoonOS."""
    def decorator(func):
        func._skill_name = name
        return func
    return decorator


# Register skills
upload_image = skill("upload_image")(upload_image)
get_image_url = skill("get_image_url")(get_image_url)
delete_image = skill("delete_image")(delete_image)
