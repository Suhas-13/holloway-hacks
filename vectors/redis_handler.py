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


def create_redisearch_index(client, index_name, embeddings_dimension):
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



def main():
    # Sample text data
    data = [
        {"id": 1, "text": "A quick brown fox jumps over the lazy dog"},
        {"id": 2, "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit"},
    ]
    # data = [{"id": 3, "text": "Computer Architecture & Concurrency COMP0008 Lecture 1: Introduction (Part 3) Kevin Bryson k.bryson@ucl.ac.uk Darwin Building Room 632. So to end with … the start … Part I: Overview and motivation behind understanding computer architecture Again this is an informal introduction to computer architecture ... In later lectures we give a detailed knowledge of how a MIPS32 processor works, how to program it in assembly and machine code, and how parallelism is employed in the architecture to make it run faster. When was the first ‘computer’ built by humans? • Antikythera computer. • Very basic instruction set architecture (fixed multiplication and division with fixed data flow between instructions ... no data registers to store values). 3 • If we were to design this ‘computer architecture’ ... we would probably have designed it’s organization out of electronic logic gates and programmed it using C ... • Or we could have used Lego ... 4 But was this a computer? It did compute with “input data” following an algorithm and produce “output data”. But what were its limitations? What is it missing? Any ideas: • General purpose? • Programmable? • Turing Complete? (Look this up ...) Antikythera “computer” Architecture • Data values Continuous floating point values • Storage Stored in degrees rotation of cogs. • Operations Divisions and multiplications • Programmable. Only by rebuilding machine. • General purpose? Not “Turing Complete” (Requires branching instructions) Organization • Fixed layout of wheels and cogs to do calculations. 5 The Analytical Engine • Designed by Charles Babbage from 1834 -1871. • Considered to be the first “digital computer” running a “program” from punched cards. • Built of mechanical gears represented discrete value (0 -9). • All the key elements of a modern computer. 6 Babbage’s Analytical Engine Architecture • Data values Discrete 40 digit decimal values • Storage Stored in discrete rotation of wheels (with a memory of 1000 40-digit values) • Operations +, -, *, /, comparisons, optional sqrt ! • Programmable. Yes – using punched cards. (Similar in approach to modern day assembly language.) • General purpose? Yes - “Turing Complete” (Requires branching instructions) Organization • Fixed layout of wheels and cogs to do calculations. 7 8 Experimental architectures ... What number base should we be using? • Russian scientists created a machine called Setun that used ternary (Base 3). • It used negative, zero and positive voltages for the three symbols. Setun (1958, Russia) ENIAC 1 used decimal calculations like the Analytical Engine. Anyone know what this is ? 9 Why use a discrete number of levels? More information in continuous voltages? • The Antikythera computer (both real and in Lego). • In a way this was an analogue mechanical computer using the ‘angle’ of different wheels between 0 and 360 degrees. 10 • Heathkit educational analogue computer used continuous voltage values … • Essentially 1V + 1V = 2V although complex operations such as differentiation could be accomplished. Colossus – binary programmable electronic computer • Colossus was built in 1943 at Bletchley Park (just outside Cambridge) and used to help decrypt the German Lorenz Cipher. • It is regarded as one of the first digital programmable electronic computers (but again using switches and patched cables). • Its organization used thermionic valves (vacuum tubes) to carry out binary operations (Boolean algebra). 11 12 EXTERNAL BUS OR BUSES Computers settled into a “Stored program” von Neumann Architecture INPUT / OUTPUT (IO) DEVICES Displays / Keyboards / Pointer Devices PROCESSOR / CENTRAL PROCESSING UNIT (CPU) MEMORY STORAGE INSTRUCTIONS AND DATA But the computer architecture / hardware radically changed over the years ... 13 One of the first transistor electronic computers IBM 7030 Individual transistors One of the first electronic computers ENIAC 1 Thermionic valves The first “von Neumann architecture” and Turing-complete computer Analytical Engine Mechanical gears But the computer architecture / hardware radically changed over the years ... 14 Intel 4004 Busicom 141-PF First microprocessor on a chip. Intel 8088 16-bit processor Original IBM PC Discrete chips with transistors IBM 360 Discrete chips with logic gates. The IBM 360 also introduced the idea of having a single “computer architecture” and different implementations of that architecture 15 Discrete chips with transistors IBM 360 Discrete chips with logic gates. Problem with CISC (Complex Instruction Set Computer) • During the 80s Intel and other manufacturers were driving ever more complex instruction sets since people were programming in assembly and wanted fancier instructions. • This required writing complex “microprograms” within the hardware chips to execute these instructions. • Hennessey and Patterson went for a radically new architecture ... RISC (Reduced Instruction Set Computer) Released:1988 Transistor count: 115,000 This processor was used to render 3D scenes in 90s movies like Jurrasic Park or Terminator 2. RISC now used for 20 billion portable devices a year … in addition to supercomputers ! 17 Unusually not Intel architecture but custom 260 core 64-bit RISC chips made in China. Both hardware and architectures need to evolve to get faster ... New application specific architectures: Google Tensor Processing Unit (TPU) Computer architecture continues to evolve ... 20 Computers can be understood in terms of abstraction layers ... Intel 4004 Processor ... 22 Understanding a modern computer … add $s3,$s3,1 # MIPS assembly 001000 01011 01011 0000000000000001 • Level 5) Problem Oriented Language Level • Level 4) Assembly Language Level • Level 3) Operating System Level • Level 2) Instruction Set Architecture Level (ISA Level) • Level 1) Microprogramming Level (not all computers have this level) • Level 0.5) Modular view (datapath) • Level 0) Digital Logic Level i = i + 1; // C source 23 Understanding a modern computer … • Level 5) Problem Oriented Language Level • Level 4) Assembly Language Level • Level 3) Operating System Level • Level 2) Instruction Set Architecture Level (ISA Level) • Level 1) Microprogramming Level (not all computers have this level) • Level 0.5) Modular view (datapath) • Level 0) Digital Logic Level i = i + 1; // C source add $s3,$s3,1 # MIPS assembly 001000 01011 01011 0000000000000001 We will look at computer arithmetic and memory layout since the ISA level is entirely numbers. We will learn MIPS assembly language and how machine code works. We will look at how C language constructs are compiled into MIPS assembly and executed. Why would I want to learn low-level assembly language programming? It is 2020 you know ... • In the 80s, my little brother was programming complete games in x86 assembly (anyone heard of Lemmings 2 ?) • He was still using assembly in the 90s ... partly because he was doing 3D graphics engine optimization. • Working on low-level device drivers then you often want to examine/write assembly language ... • My cousin is writing a tool-chain (compiler) for an unusual graph-based processor. He says the assembly language is a nightmare! • Fully understanding concurrency and multithreaded programming requires understanding the machine ... • Also it allows you to do low-level debugging (you put in print statements and the bug disappears ... what next?) Summary • You should be aware that concurrency is fundamental within both hardware and software in computer science ... from the smallest embedded processors to the (un)coordinated vastness of the Internet. • The aim of this course is to thoroughly understood key principles of Java concurrency so that bugs can be “designed out” of code by analysis rather than detected during testing (often impossible with concurrent code). • A full understanding of concurrency requires in-depth knowledge of modern computer hardware (cache structure, processor reordering of instructions, etc.) • Computer architecture and hardware are fundamental topics anyway for computer science (and job interviews!)"}]

    client = redis.Redis(
        host='redis-11987.c322.us-east-1-2.ec2.cloud.redislabs.com',
        port=11987,
        password=os.getenv('REDIS_PASSWORD'),
        decode_responses=True
        )
    
    embedder = SentenceTransformer("msmarco-distilbert-base-v4")

    embeddings = get_embeddings(embedder, data)

    # Upload data to Redis
    # upload_data(client, data, embeddings)

    # Create a Redisearch index
    # create_redisearch_index(client, "text_index", len(embeddings[0]))

    print(vector_search(client, embedder, "text_index", "A quick brown fox jumps"))

if __name__ == "__main__":
    main()
