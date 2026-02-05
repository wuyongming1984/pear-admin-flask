# pear_admin/oss_utils.py
import oss2
import uuid
from flask import current_app
import os

class OSSUtils:
    def __init__(self, app=None):
        self.bucket = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        access_key_id = app.config.get('ALIYUN_ACCESS_KEY_ID')
        access_key_secret = app.config.get('ALIYUN_ACCESS_KEY_SECRET')
        bucket_name = app.config.get('ALIYUN_OSS_BUCKET_NAME')
        endpoint = app.config.get('ALIYUN_OSS_ENDPOINT')
        
        # Ensure endpoint has http/https
        if endpoint and not endpoint.startswith('http'):
            endpoint = 'https://' + endpoint

        if not all([access_key_id, access_key_secret, bucket_name, endpoint]):
            app.logger.warning("Aliyun OSS configuration missing.")
            self.bucket = None
            return

        auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)
    
    def upload_file(self, file_storage, filename=None):
        """
        Upload a Flask FileStorage object to OSS.
        :param file_storage: Flask file object (from request.files) or stream
        :param filename: Target filename in OSS
        :return: Public URL or None if failed
        """
        if not self.bucket:
            raise Exception("OSS not configured")

        if not filename:
            ext = file_storage.filename.rsplit('.', 1)[1].lower() if '.' in file_storage.filename else 'bin'
            filename = f"{uuid.uuid4().hex}.{ext}"

        # Determine content type if possible
        headers = {}
        if hasattr(file_storage, 'mimetype'):
             headers['Content-Type'] = file_storage.mimetype

        # Reset stream position just in case
        file_storage.seek(0)
        
        result = self.bucket.put_object(filename, file_storage, headers=headers)
        
        if result.status == 200:
            # Construct URL
            # Standard OSS URL: https://bucket-name.endpoint/filename
            # If endpoint contains bucket name (rare), customized
            # Default: Endpoint is like https://oss-cn-hangzhou.aliyuncs.com
            
            # Extract domain from endpoint
            domain = self.bucket.endpoint.replace('http://', '').replace('https://', '')
            url = f"https://{self.bucket.bucket_name}.{domain}/{filename}"
            return url
        else:
            raise Exception(f"OSS Upload Failed: {result.status}")
    
    
    def generate_signed_url(self, object_key, expires=3600, params=None):
        """
        Generate a signed URL for accessing a private OSS object.
        :param object_key: The OSS object key (path) or full URL
        :param expires: URL expiration time in seconds (default: 1 hour)
        :return: Signed URL string
        """
        if not self.bucket:
            return None
        
        try:
            # Extract object key from full URL if provided
            if object_key and object_key.startswith('http'):
                # Parse URL: https://bucket.endpoint/path/to/file.pdf -> path/to/file.pdf
                from urllib.parse import urlparse
                parsed = urlparse(object_key)
                # Remove leading slash from path
                object_key = parsed.path.lstrip('/')
            
            # Generate signed URL
            signed_url = self.bucket.sign_url('GET', object_key, expires, params=params)
            return signed_url
        except Exception as e:
            current_app.logger.error(f"Failed to generate signed URL for '{object_key}': {e}")
            return None
