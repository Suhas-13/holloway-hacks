import asyncio
import websockets
from io import BytesIO
import PyPDF2

def extract_text_from_pdf(pdf_bytes):
    reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def send_text_to_backend(text):
    print("Sending text to backend...")

async def handler(websocket):
    data = bytearray()
    is_receiving = False
    file_name = ""

    while True:
        await websocket.send("give data pls")
        message = await websocket.recv()

        # Start of a new PDF file
        if message.startswith("pdf:start") or message.startswith("text:start"):
            is_receiving = True
            message = message.replace("pdf:start", "")
            file_name = message.split(":")[0]
            message = ":".join(message.split(":")[1:])
            data.clear()
            continue

        if message.startswith("pdf:end"):
            is_receiving = False
            text = extract_text_from_pdf(data)
            send_text_to_backend(file_name, text)
            continue
        elif message.startswith("text:end"):
            is_receiving = False
            send_text_to_backend(file_name, data.decode("utf-8"))
            continue

        if is_receiving:
            data.extend(message)
            continue

        print(message)

async def main():
    print("Starting server...")
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
