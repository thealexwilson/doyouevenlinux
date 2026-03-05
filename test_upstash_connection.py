#!/usr/bin/env python3
"""Test script to verify Upstash Redis connection and environment variables."""

from dotenv import load_dotenv
from upstash_redis import Redis

print("Loading .env file...")
load_dotenv()

print("Connecting to Upstash Redis...")
try:
    redis_client = Redis.from_env()
    
    print("✅ Connection successful!")
    print("\nTesting write operation...")
    redis_client.set("test:connection", "success")
    
    print("Testing read operation...")
    result = redis_client.get("test:connection")
    
    if result == "success":
        print("✅ Read/Write test passed!")
        print(f"   Value retrieved: {result}")
    else:
        print(f"⚠️  Unexpected value: {result}")
    
    print("\nCleaning up test key...")
    redis_client.delete("test:connection")
    print("✅ All tests passed! Your populate_upstash.py should work.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check that UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN are in .env")
    print("2. Verify your credentials are correct in the Upstash dashboard")
    print("3. Make sure the .env file is in the same directory as this script")
