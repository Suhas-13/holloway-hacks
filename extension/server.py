import asyncio

import websockets

from time import sleep


async def handler(websocket):
    while True:
        await websocket.send("give data pls")
        message = await websocket.recv()
        print(message)
        sleep(10)


async def main():
    print("Starting server...")
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
