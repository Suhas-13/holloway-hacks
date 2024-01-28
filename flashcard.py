import redis
import json


# Connect to Redis
client = redis.Redis(
        host='redis-11987.c322.us-east-1-2.ec2.cloud.redislabs.com',
        port=11987,
        password='ADD_URS',
        decode_responses=True
        )

# Sample JSON data
data = {
    "Topic 1": {
    "What's the local cuisine?": "A mystery"
  },
  "Topic 2": {
    "What's the population?": "A mystery"
  },
  "Topic 3": {
    "When was it founded?": "Uncertain"
  },
  "Topic 4": {
    "What's the local cuisine?": "A mystery"
  },
  "Topic 5": {
    "What's the capital?": "Unknown"
  },
  "Topic 6": {
    "What's the population?": "Uncertain"
  },
  "Topic 7": {
    "When was it founded?": "To be discovered"
  },
  "Topic 8": {
    "When was it founded?": "Uncertain"
  },
  "Topic 9": {
    "When was it founded?": "Not clear"
  },
  "Topic 10": {
    "When was it founded?": "Unspecified"
  }
}

def add_flashcards(topic, details):
    json_data = json.dumps(details)

    if not client.set(topic, json_data):
        print("Adding to the database failed")
    
def display_flashcards(topic):

    json_data = client.get(topic)
    data = json.loads(json_data)

    return data


def all_flashcards():
    all_data = []

    all_keys = client.keys('*')

    for key in all_keys:
        if not key.startswith("Topic"):
            continue
        value = client.get(key)
        if value:
            json_data = json.loads(value)
            all_data.append([list(json_data.keys())[0], list(json_data.values())[0]])

    print(all_data)
    return all_data

for topic, data in data.items():
    add_flashcards(topic, data)