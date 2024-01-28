import asyncio
import multiprocessing
import websockets
import PyPDF2
import requests as re
import base64
import os
from urllib.parse import quote
from vectors.redis_handler import RedisManager
import string
from beepy import beep
import random
class PDFServer:
    def __init__(self, queue):
        self.data = []
        self.queue = queue
        self.is_receiving_text = False
        self.file_name = ""
        self.title = ""
        self.redis_manager = RedisManager()
        self.event = asyncio.Event()
        self.websocket = None

    def extract_text_from_pdf(self, filename):
        with open(filename, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        return text
    
    def generate_alphanumeric_string(self, length):
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))
    def send_text_to_backend(self, file_name, title, text):
        print(f"===== {file_name} =====", flush=True)
        print("Sending text to backend...")
        file_name = quote(file_name)
        title = quote(title)
        self.redis_manager.upload_string(file_name, title, text)

    def process_pdf_message(self, url, title):
        try:
            r = re.get(url, verify=False)
            filename = "pdf.pdf"
            with open(filename, "wb") as file:
                file.write(r.content)

            text = self.extract_text_from_pdf(filename)
            new_file_name = quote(title)
            if os.path.exists(f"pdfs/{new_file_name}.pdf"):
                os.remove(f"pdfs/{new_file_name}.pdf")
            os.rename(filename, f"pdfs/{new_file_name}.pdf")
            self.send_text_to_backend(url, title, text)
        except Exception as e:
            print(f"Error processing PDF: {e}")

    async def handle_connection(self, websocket):
        self.websocket = websocket
        while True:
            #print("Waiting for event...", flush=True)
            if not self.queue.empty():
                message = self.queue.get()
                if message == "restart":
                    print("RECONNCETING WEBSOCKET")
                    await self.websocket.reconnect()

                print("Trying to send websockets", flush=True)
                await self.websocket.send("Requesting data...")

                # Continuously read messages until 'text:end' is received
                while True:
                    try:
                        message = await asyncio.wait_for(self.websocket.recv(), timeout=10.0) 
                    except asyncio.TimeoutError:
                        print("Timeout while waiting for message!")
                        break  # Exit the loop if a timeout occurs

                    if message.startswith("text:start:"):
                        self.is_receiving_text = True
                        message = message.replace("text:start:", "")
                        self.title = message.split(":")[0]
                        self.file_name = message[len(self.title) + 1:]
                        self.data.clear()

                    elif message.startswith("pdf:"):
                        message = message[4:]
                        title = message.split(":")[0]
                        url = message[len(title) + 1:]
                        self.process_pdf_message(url, title)
                        beep(0)
                        break

                    elif message == "text:end":
                        if self.is_receiving_text:
                            complete_text = "".join(self.data)
                            self.send_text_to_backend(self.file_name, self.title, complete_text)
                            self.data.clear()
                            self.is_receiving_text = False
                            beep(0)
                        break

                    elif self.is_receiving_text:
                        self.data.append(message)
                    
                    await asyncio.sleep(0)
            await asyncio.sleep(0)

            
    async def handler(self, websocket, path):
        while True:
            try:
                await self.handle_connection(websocket)
            except Exception as e:
                print(e)
                print("Connection closed, attempting to reconnect...")
                # Logic to initiate a reconnection
                # This could involve waiting for a few seconds and then retrying the connection
                await asyncio.sleep(2)  # Wait for 5 seconds before retrying
                # You might also need to handle the reconnection process here
            
            

    async def server(self):
        while True:
            try:
                async with websockets.serve(self.handler, "localhost", 8001):
                    await asyncio.Future()  # Run indefinitely
            except Exception as e:
                print(f"Server error: {e}. Restarting...")
                continue

    def start_websocket_server(self):
        asyncio.run(self.server())

    def trigger_event(self):
        asyncio.run(self.event.set())


if __name__ == "__main__":
    server = PDFServer(None)  # Assuming None for redis_manager for now
    server.start_server()
