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

def split_and_format_text(filename, text, min_length=400, max_length=1000):
    paragraphs = text.split('\n\n')
    formatted_data = []
    current_segment = ""
    segment_count = 1

    for paragraph in paragraphs:
        if len(current_segment) + len(paragraph) <= max_length:
            current_segment += paragraph + "\n\n"
        else:
            if len(current_segment) >= min_length:
                formatted_data.append({"id": f"{filename}_part{segment_count}", "text": current_segment.strip()})
                current_segment = paragraph + "\n\n"
                segment_count += 1
            else:
                current_segment += paragraph + "\n\n"

    # Adding the last segment if it's not empty
    if current_segment.strip():
        formatted_data.append({"id": f"{filename}_part{segment_count}", "text": current_segment.strip()})

    return formatted_data


class RedisManager:
    def __init__(self) -> None:
        self.client = redis.Redis(
            host='redis-11987.c322.us-east-1-2.ec2.cloud.redislabs.com',
            port=11987,
            password=os.getenv('REDIS_PASSWORD'),
            decode_responses=True
            )
        
        self.openai_client = OpenAI(
            api_key=os.getenv('OPENAI_KEY'),
        )
        
        self.embedder = SentenceTransformer("msmarco-distilbert-base-v4")


    def get_embedding(self, text, model="text-embedding-3-small"):
        text = text.replace("\n", " ")
        return self.openai_client.embeddings.create(input = [text], model=model).data[0].embedding
    

    def upload_string(self, filename, data):
        data = split_and_format_text(filename, data)
        embeddings = [np.array(self.get_embedding(item["text"]), dtype=np.float32) for item in data]

        upload_data(self.client, data, embeddings)
        delete_index(self.client, INDEX_NAME)
        create_index(self.client, INDEX_NAME, len(embeddings[0]))


    def search_string(self, query):
        results = self.vector_search(self.client, INDEX_NAME, query)
        return results


    def ask_gpt(self, query):
        gpt_answer = self.vector_search_and_gpt(query, self.client, self.openai_client,  INDEX_NAME)
        return gpt_answer

    
    def vector_search(self, client, index_name, input_string):
        query_vector = np.array(self.get_embedding(input_string), dtype=np.float32)

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
    

    def vector_search_and_gpt(self, query, redis_client, openai_client, index_name, context_count=1):
        search_results = self.vector_search(redis_client, index_name, query)
        contexts = [result["Text"] for result in search_results[:context_count]] if search_results else [""]
        context = "\n\n".join(contexts)

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
            

def main():
    manager = RedisManager()

    manager.upload_string("1123554", "Alice ligma balls")

    print(manager.ask_gpt("Where does bbc's revenue come from?"))


if __name__ == "__main__":
    main()
