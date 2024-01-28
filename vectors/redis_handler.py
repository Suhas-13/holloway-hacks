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

def split_and_format_text(filename, text, max_length=650):
    words = text.split()
    formatted_data = []
    current_segment = ""
    segment_count = 1

    for word in words:
        if len(current_segment) + len(word) + 1 <= max_length:  # +1 for the space
            current_segment += word + " "
        else:
            formatted_data.append({"id": f"{filename}_part{segment_count}", "text": current_segment.strip()})
            print(f"Segment {segment_count} length: {len(current_segment)}")
            current_segment = word + " "
            segment_count += 1

    # Add the last segment if it's not empty
    if current_segment.strip():
        formatted_data.append({"id": f"{filename}_part{segment_count}", "text": current_segment.strip()})
        print(f"Segment {segment_count} length: {len(current_segment)}")

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
    

    def upload_string(self, filename, title, data):
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
    
    def gpt_response_based_on_knowledge(self, openai_client, query, context):
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You will be given a question to answer. Answer the question concisely based on your knowledge.\"\n\n"},
                {"role": "user", "content": f"Question: {query}\nAnswer:"}
            ],
            temperature=0,
            max_tokens=70,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            # stop=stop_sequence,
        )
        return response.choices[0].message.content.strip()
    
    def vector_search_and_gpt(self, query, redis_client, openai_client, index_name, context_count=9):
        search_results = self.vector_search(redis_client, index_name, query)
        if not search_results:
            contexts = [""]
        else:
            contexts = [search_results[0]["Text"]]
            for result in search_results[:context_count]:
                print("Score:", result["Score"])
                if float(result["Score"]) < 0.7:
                    contexts.append(result["Text"])
                else:
                    break

        context = "\n\n".join(contexts)

        print("context:", context)

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You will be given context and questions to answer. Answer the question concisely based on the context below, and if the question can't be answered based on the context please output 'I don't know'\"\n\n"},
                {"role": "user", "content": f"Context: {context}\n\n---\n\nQuestion: {query}\nAnswer:"}
            ],
            temperature=0,
            max_tokens=70,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            # stop=stop_sequence,
        )
        print("Answer:",response.choices[0].message.content.strip())
        if "i don't know" in response.choices[0].message.content.strip().lower():
            return "I wasn't able to find an answer from your documents but based on a search " + self.gpt_response_based_on_knowledge(openai_client, query, context)
        return response.choices[0].message.content.strip()
            

def main():
    manager = RedisManager()

    text = """During the High Middle Ages, which began after 1000, the population of Europe increased greatly as technological and agricultural innovations allowed trade to flourish and the Medieval Warm Period climate change allowed crop yields to increase. Manorialism, the organisation of peasants into villages that owed rent and labour services to the nobles, and feudalism, the political structure whereby knights and lower-status nobles owed military service to their overlords in return for the right to rent from lands and manors, were two of the ways society was organised in the High Middle Ages. This period also saw the formal division of the Catholic and Orthodox churches, with the East–West Schism of 1054. The Crusades, which began in 1095, were military attempts by Western European Christians to regain control of the Holy Land from Muslims and also contributed to the expansion of Latin Christendom in the Baltic region and the Iberian Peninsula. In the West, intellectual life was marked by scholasticism, a philosophy that emphasised joining faith to reason, and by the founding of universities. The theology of Thomas Aquinas, the paintings of Giotto, the poetry of Dante and Chaucer, the travels of Marco Polo, and the Gothic architecture of cathedrals such as Chartres mark the end of this period.

The Late Middle Ages was marked by difficulties and calamities including famine, plague, and war, which significantly diminished the population of Europe; between 1347 and 1350, the Black Death killed about a third of Europeans. Controversy, heresy, and the Western Schism within the Catholic Church paralleled the interstate conflict, civil strife, and peasant revolts that occurred in the kingdoms. Cultural and technological developments transformed European society, concluding the Late Middle Ages and beginning the early modern period."""

    manager.upload_string("two", "I am a human")

    print(manager.ask_gpt("What am i?"))


if __name__ == "__main__":
    main()
