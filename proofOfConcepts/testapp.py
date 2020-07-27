import logging
import asyncio
import threading
import random
from flask import Flask, request

logging.basicConfig(filename='loggy.log', level=logging.DEBUG)
app = Flask(__name__)

@app.route('/')
def index():
    logging.info('Starting Index')
    logging.info('Number of current threads: {}'.format(threading.active_count()))
    thread_names = [thread.name for thread in threading.enumerate()]
    if "Internal Thread" not in thread_names:
        internal_thread = threading.Thread(target=asyncio.run,
                                           args=(wrapper(),),
                                           name="Internal Thread",
                                           daemon=True)
        internal_thread.start()
    logging.info('Number of current threads: {}'.format(threading.active_count()))
    thread_names = [thread.name for thread in threading.enumerate()]
    logging.info(str(thread_names))
    logging.info('Done with Index')
    return 'The response'



async def sleepit(num):
    logging.info('Starting sleeping')
    logging.info('Sleepint Loop: ' + str(asyncio.get_running_loop()))
    await asyncio.sleep(10)
    logging.info('Done with sleepit')

async def wrapper():
    logging.info('Starting Wrapper')
    logging.info('Wrapper loop: ' + str(asyncio.get_running_loop()))
    task = asyncio.create_task(sleepit(random.randint(0, 100)))
    logging.info(asyncio.all_tasks())
    await task
    logging.info('Done with Wrapper')

if __name__ == "__main__":
    app.run(port=5000)
    
