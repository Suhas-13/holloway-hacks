import redis
import os
from dotenv import load_dotenv

load_dotenv()

def delete_all_indices(client):
    try:
        # List all indices
        indices = client.execute_command("FT._LIST")
        for index in indices:
            # Delete each index
            client.ft(index).dropindex(delete_documents=True)
            print(f"Index '{index}' deleted.")
    except Exception as e:
        print(f"Error deleting indices: {e}")

def main():
    client = redis.Redis(
        host='redis-11987.c322.us-east-1-2.ec2.cloud.redislabs.com',
        port=11987,
        password=os.getenv('REDIS_PASSWORD'),
        decode_responses=True
        )

    delete_all_indices(client)

if __name__ == "__main__":
    main()
