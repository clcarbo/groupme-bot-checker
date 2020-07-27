import asyncio
import threading
import logging

logging.basicConfig(filename='temp.log',level=logging.DEBUG)

loop = asyncio.new_event_loop()

async def my_task():
    logging.info("starting my_task")
    await asyncio.sleep(10)
    logging.info("my_task finished")

async def your_task():
    logging.info("starting your_task")
    await asyncio.sleep(10)
    logging.info("your_task finished")

logging.info("Starting thread")
outer = threading.Thread(target=loop.run_forever, daemon=False)
outer.start()

loop.call_soon_threadsafe(asyncio.create_task, my_task())
loop.call_soon_threadsafe(asyncio.create_task, your_task())


logging.info("Main thread done")
