import asyncio
import websockets
import PyPDF2
from time import sleep
import requests as re
from os import remove
from beepy import beep


class PDFServer:
    def __init__(self):
        self.pause_main_loop = asyncio.Event()
        self.data = bytearray()
        self.is_receiving = False
        self.file_name = ""

    def extract_text_from_pdf(self):
        reader = PyPDF2.PdfReader("pdf.pdf")
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def send_text_to_backend(self, file_name, text):
        print(" ===== " + file_name + " ===== ")
        print(text)
        print("Sending text to backend...")

    async def handler(self, websocket):
        while True:
            if not self.is_receiving:
                await self.pause_main_loop.wait()
                
            print("Trying to get soem data")
            if not self.is_receiving:
                await websocket.send("give data pls")
                self.is_receiving = True
                beep(5)

            while self.is_receiving:
                message = await websocket.recv()

                if message == "":
                    self.is_receiving = False
                    self.pause_main_loop.clear()
                    self.data.clear()
                    continue

                # Start of a new PDF file
                if message.startswith("text:start"):
                    message = message.replace("text:start:", "")
                    self.file_name = message
                    self.data.clear()
                    continue

                if message.startswith("pdf:"):
                    self.is_receiving = False
                    self.pause_main_loop.clear()
                    url = message.replace("pdf:", "")
                    r = re.get(url)

                    with open("pdf.pdf", "wb") as file:
                        file.write(r.content)

                    text = self.extract_text_from_pdf()
                    self.send_text_to_backend(self.file_name, text)
                    self.data.clear()
                    remove("pdf.pdf")
                    continue

                if message.startswith("text:end"):
                    self.is_receiving = False
                    self.pause_main_loop.clear()
                    self.send_text_to_backend(self.file_name, self.data.decode("utf-8"))
                    self.data.clear()
                    continue

                if self.is_receiving:
                    self.data.extend(message.encode("utf-8"))
                    continue
            await asyncio.sleep(0)

    async def main(self):
        print("Starting server...")
        self.server_started = asyncio.Event()
        async with websockets.serve(self.handler, "", 8001):
            await self.server_started.wait()
            print("IN LOOP")
        print("Server finished properly") 

if __name__ == "__main__":
    server = PDFServer()
    asyncio.run(server.main())