import json
import numpy as np
import redis
from sentence_transformers import SentenceTransformer
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from dotenv import load_dotenv
import os

load_dotenv()
INDEX_NAME = "dev"


def get_embeddings(model, data):
    embeddings = model.encode([item['text'] for item in data]).astype(np.float32)   # FIXME: only json
    return embeddings


def upload_data(client, data, embeddings):
    pipeline = client.pipeline()
    for item, embedding in zip(data, embeddings):
        redis_key = f"text_data:{item['id']}"
        pipeline.json().set(redis_key, "$", item)
        pipeline.json().set(redis_key, "$.embedding", embedding.tolist())
    pipeline.execute()


def create_index(client, index_name, embeddings_dimension):
    schema = (
        TextField("$.text", as_name="text"),
        VectorField(
            "$.embedding",
            "FLAT",
            {"TYPE": "FLOAT32", "DIM": embeddings_dimension, "DISTANCE_METRIC": "COSINE"},
            as_name="embedding"
        ),
    )
    definition = IndexDefinition(prefix=["text_data:"], index_type=IndexType.JSON)
    client.ft(index_name).create_index(fields=schema, definition=definition)


def vector_search(client, model, index_name, input_string):

    query_vector = model.encode([input_string]).astype(np.float32)[0]

    query = (
        Query("(*)=>[KNN 5 @embedding $vec AS score]")
        .sort_by("score")
        .return_fields("score", "text")
        .dialect(2)
    )

    params = {"vec": query_vector.tobytes()}
    results = client.ft(index_name).search(query, query_params=params).docs

    search_results = []
    for doc in results:
        search_results.append({"Score": doc.score, "Text": doc.text})

    return search_results


def delete_index(client, index_name, delete_documents=False):
    try:
        client.ft(index_name).dropindex(delete_documents=delete_documents)
        print(f"Index '{index_name}' deleted successfully.")
    except Exception as e:
        print(f"Error deleting index: {e}")

def get_data_json(filename, input):
    return [
        {"id": filename, "text": input},
    ]


def main(upload=False, search=False):
    # Sample text data
    # data = [
    #     {"id": "doc1", "text": "Test123"},
    #     # {"id": "doc2", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit"},
    # ]

    data = get_data_json("doc1", "Test123")

    client = redis.Redis(
        host='redis-11987.c322.us-east-1-2.ec2.cloud.redislabs.com',
        port=11987,
        password=os.getenv('REDIS_PASSWORD'),
        decode_responses=True
        )
    
    if client:
        print("connected")
    
    embedder = SentenceTransformer("msmarco-distilbert-base-v4")

    embeddings = get_embeddings(embedder, data)

    # kinda dirty, assumes INDEX_NAME exists
    if upload:
        upload_data(client, data, embeddings)
        delete_index(client, INDEX_NAME)
        create_index(client, INDEX_NAME, len(embeddings[0]))

    if search:
        print(vector_search(client, embedder, INDEX_NAME, "test"))


if __name__ == "__main__":
    main(upload=False, search=False)
