import os
import sys
from dotenv import load_dotenv
import oss2

# Load env from root
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(root_path, '.env')
load_dotenv(env_path)

def test_oss():
    ak = os.getenv("ALIYUN_ACCESS_KEY_ID")
    sk = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
    bucket_name = os.getenv("ALIYUN_OSS_BUCKET_NAME")
    endpoint = os.getenv("ALIYUN_OSS_ENDPOINT")

    print(f"AK: {ak[:4]}***")
    print(f"SK: {sk[:4]}***")
    print(f"Bucket: {bucket_name}")
    print(f"Endpoint: {endpoint}")

    if not all([ak, sk, bucket_name, endpoint]):
        print("Missing config!")
        return

    if not endpoint.startswith('http'):
        endpoint = 'https://' + endpoint
    
    auth = oss2.Auth(ak, sk)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    print("Attempting to upload test file...")
    try:
        result = bucket.put_object('test_config_check.txt', b'Hello OSS')
        print(f"Upload Result Status: {result.status}")
        if result.status == 200:
            print("OSS Upload Success!")
    except Exception as e:
        print(f"OSS Error: {e}")

if __name__ == "__main__":
    test_oss()
