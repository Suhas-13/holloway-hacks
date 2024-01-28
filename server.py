import asyncio
import threading
import websockets
import PyPDF2
import requests as re
import base64
import os

class PDFServer:
    def __init__(self, redis_manager):
        self.data = []
        self.is_receiving_text = False
        self.file_name = ""
        self.redis_manager = redis_manager
        self.event = asyncio.Event()
        self.websocket = None

    def extract_text_from_pdf(self, filename):
        with open(filename, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        return text

    def send_text_to_backend(self, file_name, text):
        print(f"===== {file_name} =====", flush=True)
        print("Sending text to backend...")
        self.redis_manager.upload_string(file_name, text)

    def process_pdf_message(self, url):
        try:
            r = re.get(url, verify=False)
            filename = "pdf.pdf"
            with open(filename, "wb") as file:
                file.write(r.content)

            text = self.extract_text_from_pdf(filename)
            new_file_name = base64.b64encode(url.encode("utf-8")).decode("utf-8")
            os.rename(filename, f"pdfs/{new_file_name}.pdf")
            self.send_text_to_backend(url, text)
        except Exception as e:
            print(f"Error processing PDF: {e}")

    async def handler(self, websocket, path):
        self.websocket = websocket
        while True:
            await self.event.wait()  # Wait for the signal to proceed
            #self.event.clear()  # Reset the event after it's been triggered
            print("Triyng to send websockets", flush=True)
            if self.websocket:
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
                        self.file_name = message.replace("text:start:", "")
                        self.data.clear()

                    elif message.startswith("pdf:"):
                        url = message.replace("pdf:", "")
                        await self.process_pdf_message(url)
                        break

                    elif message == "text:end":
                        if self.is_receiving_text:
                            complete_text = "".join(self.data)
                            self.send_text_to_backend(self.file_name, complete_text)
                            self.data.clear()
                            self.is_receiving_text = False
                        break

                    elif self.is_receiving_text:
                        self.data.append(message)
            await asyncio.sleep(0.1)

    async def server(self):
        async with websockets.serve(self.handler, "localhost", 8001):
            await asyncio.Future()  # Run indefinitely

    def start_websocket_server(self):
        asyncio.run(self.server())

    def trigger_event(self):
        asyncio.run(self.event.set())


if __name__ == "__main__":
    server = PDFServer(None)  # Assuming None for redis_manager for now
    server.start_server()
