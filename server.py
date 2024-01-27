import asyncio
import websockets
import PyPDF2
from time import sleep
import requests as re
from os import remove


def extract_text_from_pdf():
    reader = PyPDF2.PdfReader("pdf.pdf")
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def send_text_to_backend(file_name, text):
    print(" ===== " + file_name + " ===== ")
    print(text)
    print("Sending text to backend...")


async def handler(websocket):
    data = bytearray()
    is_receiving = False
    file_name = ""

    while True:
        sleep(5)
        await websocket.send("give data pls")
        is_receiving = True

        while is_receiving:
            message = await websocket.recv()

            if message == "":
                is_receiving = False
                data.clear()
                continue

            # Start of a new PDF file
            if message.startswith("text:start"):
                message = message.replace("text:start:", "")
                file_name = message
                data.clear()
                continue

            if message.startswith("pdf:"):
                is_receiving = False
                url = message.replace("pdf:", "")
                r = re.get(url)

                with open("pdf.pdf", "wb") as file:
                    file.write(r.content)

                text = extract_text_from_pdf()
                send_text_to_backend(file_name, text)
                data.clear()
                remove("pdf.pdf")
                continue

            if message.startswith("text:end"):
                is_receiving = False
                send_text_to_backend(file_name, data.decode("utf-8"))
                data.clear()
                continue

            if is_receiving:
                data.extend(message.encode("utf-8"))
                continue


async def main():
    print("Starting server...")
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
