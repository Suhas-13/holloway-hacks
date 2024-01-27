import json
import numpy as np
import redis
from sentence_transformers import SentenceTransformer
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from dotenv import load_dotenv
import os
from openai import OpenAI


load_dotenv()
INDEX_NAME = "dev"
openai_client = OpenAI(
    api_key=os.getenv('OPENAI_KEY'),
)


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


# def get_answer_from_gpt(question, context):
#     response = openai.Completion.create(
#       engine="davinci",
#       prompt=f"Context: {context}\n\nQuestion: {question}\nAnswer:",
#       max_tokens=50
#     )

#     return response.choices[0].text.strip()


# might have a tiny deadlock risk but it's calm
def vector_search_and_gpt(query, openai_client, redis_client, embedder, index_name):
    search_results = vector_search(redis_client, embedder, index_name, query)
    context = search_results[0]["Text"] if search_results else ""

    print("context:", context)

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Answer the question based on the context below, and if the question can't be answered based on the context, say \"I don't know\"\n\n"},
            {"role": "user", "content": f"Context: {context}\n\n---\n\nQuestion: {query}\nAnswer:"}
        ],
        temperature=0,
        max_tokens=80,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        # stop=stop_sequence,
    )

    return response.choices[0].message.content.strip()


def split_text_by_paragraphs(text, min_length=200, max_length=1000):
    paragraphs = text.split('\n\n')
    segments = []

    current_segment = ""
    for paragraph in paragraphs:
        if len(current_segment) + len(paragraph) <= max_length:
            current_segment += paragraph + "\n\n"
        else:
            if len(current_segment) >= min_length:
                segments.append(current_segment.strip())
                current_segment = paragraph + "\n\n"
            else:
                current_segment += paragraph + "\n\n"
    
    # Adding the last segment if it's not empty
    if current_segment.strip():
        segments.append(current_segment.strip())

    return segments


def main(upload=False, search=False, ask=False):
    # Sample text data
    # data = [
    #     {"id": "doc1", "text": "Test123"},
    #     # {"id": "doc2", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit"},
    # ]

    data = get_data_json("doc3", "Alice is friends with Bob.")

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

    if ask:
        query = "Who is Alice friends with?"

        gpt_answer = vector_search_and_gpt(query, openai_client, client, embedder, INDEX_NAME)
        print(gpt_answer)


if __name__ == "__main__":
    main(upload=False, search=False, ask=False)
