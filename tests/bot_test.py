from flask import Flask, request
import requests
import re
from loaves import breadfacts
import json
from insults import insult, insult_part

post = json.loads('''{
  "attachments": [],
  "avatar_url": "https://i.groupme.com/123456789",
  "created_at": 1302623328,
  "group_id": "1234567890",
  "id": "1234567890",
  "name": "John",
  "sender_id": "12345",
  "sender_type": "user",
  "source_guid": "GUID",
  "system": false,
  "text": "Hello world ☃☃",
  "user_id": "1234567890"
}''')

def test_post():
    assert type(post) == dict

def test_breadfacts():
    assert type(breadfacts()) == str

def test_insult():
    temp_insult = insult(insult_part())
    assert type(insult_part()) == str
    assert type(temp_insult) == str
    assert temp_insult[-1] == '.'
