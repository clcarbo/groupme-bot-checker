import logging
import multiprocessing
import time
from flask import Flask



logging.basicConfig(filename="temp3.log", level=logging.DEBUG)

app = Flask(__name__)

def inner_wait():
    logging.info("Starting Task")
    time.sleep(15)
    logging.info("Task complete")


@app.route("/")
def test():
    if "Process-1" in [p.name for p in multiprocessing.active_children()]:
        pro = [p for p in multiprocessing.active_children()
               if p.name == "Process-1"][0]
        pro.terminate()
        logging.info("It worked!!!!")
        time.sleep(2)
        logging.info(multiprocessing.active_children())
    else:
        logging.info(multiprocessing.active_children())
        the_process = multiprocessing.Process(target=inner_wait)
        the_process.start()
        logging.info(multiprocessing.active_children())

    return "This is the response"

if __name__ == "__main__":
    app.run(port=5000)
