import threading
from time import sleep
from flask import Flask, request
import requests
import re

# Instantiate a Flask object
app = Flask(__name__)

fishermen = ["Dan", "Dylan", "You", "Cole"]

def goFishing():
    output = ''
    while fishermen:
        output += fishermen[-1] + " caught a fish!\n"
        fishermen.pop()
        sleep(1)
    with open('test.txt', mode='w') as f:
        f.write(output)


# Define the only route for the server
@app.route('/', methods=['GET'])
def test():
    fishing = threading.Thread(target = goFishing)

    fishing.start()
    
    return 'This is your main response.'


if __name__ == '__main__':
    app.run(port=5000)
