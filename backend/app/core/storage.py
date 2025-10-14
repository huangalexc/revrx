"""
S3-Compatible Storage Service
Encrypted file storage for clinical notes and billing codes
"""

import boto3
from botocore.exceptions import ClientError
from typing import BinaryIO
import structlog
from datetime import datetime, timedelta

from app.core.config import settings

logger = structlog.get_logger(__name__)


class StorageService:
    """
    S3-compatible storage service with encryption at rest
    """

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.encryption = settings.AWS_S3_ENCRYPTION

    async def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str,
        metadata: dict = None
    ) -> str:
        """
        Upload file to S3 with encryption

        Args:
            file_obj: File-like object to upload
            key: S3 object key (path)
            content_type: MIME type of the file
            metadata: Optional metadata to attach to the object

        Returns:
            S3 key of uploaded file

        Raises:
            StorageError: If upload fails
        """
        try:
            extra_args = {
                'ContentType': content_type,
                'ServerSideEncryption': self.encryption,
            }

            if metadata:
                extra_args['Metadata'] = metadata

            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )

            logger.info(
                "File uploaded to S3",
                key=key,
                bucket=self.bucket_name,
                encryption=self.encryption
            )

            return key

        except ClientError as e:
            logger.error(
                "Failed to upload file to S3",
                key=key,
                error=str(e)
            )
            raise StorageError(f"Upload failed: {str(e)}")

    async def download_file(self, key: str) -> bytes:
        """
        Download file from S3

        Args:
            key: S3 object key

        Returns:
            File contents as bytes

        Raises:
            StorageError: If download fails
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            logger.info("File downloaded from S3", key=key)
            return response['Body'].read()

        except ClientError as e:
            logger.error(
                "Failed to download file from S3",
                key=key,
                error=str(e)
            )
            raise StorageError(f"Download failed: {str(e)}")

    async def delete_file(self, key: str) -> None:
        """
        Delete file from S3

        Args:
            key: S3 object key

        Raises:
            StorageError: If deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )

            logger.info("File deleted from S3", key=key)

        except ClientError as e:
            logger.error(
                "Failed to delete file from S3",
                key=key,
                error=str(e)
            )
            raise StorageError(f"Deletion failed: {str(e)}")

    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "get_object"
    ) -> str:
        """
        Generate presigned URL for secure file access

        Args:
            key: S3 object key
            expiration: URL expiration in seconds (default: 1 hour)
            method: S3 method (get_object or put_object)

        Returns:
            Presigned URL

        Raises:
            StorageError: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )

            logger.info(
                "Presigned URL generated",
                key=key,
                expiration=expiration
            )

            return url

        except ClientError as e:
            logger.error(
                "Failed to generate presigned URL",
                key=key,
                error=str(e)
            )
            raise StorageError(f"URL generation failed: {str(e)}")

    async def list_files(self, prefix: str = "") -> list[dict]:
        """
        List files in bucket with optional prefix

        Args:
            prefix: Object key prefix for filtering

        Returns:
            List of file metadata dictionaries
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })

            logger.info(
                "Files listed from S3",
                prefix=prefix,
                count=len(files)
            )

            return files

        except ClientError as e:
            logger.error(
                "Failed to list files from S3",
                prefix=prefix,
                error=str(e)
            )
            raise StorageError(f"List operation failed: {str(e)}")

    def get_file_key(self, user_id: str, encounter_id: str, filename: str) -> str:
        """
        Generate standardized S3 key for uploaded files

        Args:
            user_id: User ID
            encounter_id: Encounter ID
            filename: Original filename

        Returns:
            S3 object key
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        return f"uploads/{user_id}/{encounter_id}/{timestamp}/{filename}"


class StorageError(Exception):
    """Custom exception for storage operations"""
    pass


# Global storage service instance
storage_service = StorageService()
