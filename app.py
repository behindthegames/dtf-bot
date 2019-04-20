#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask
from flask import request
import json
import re
import rawgpy
from fuzzywuzzy import fuzz
import requests
import os

app = Flask(__name__)

X_DEVICE_TOKEN = os.environ['X_DEVICE_TOKEN']
X_DEVICE_POSSESSION_TOKEN = os.environ['X_DEVICE_POSSESSION_TOKEN']

def send_a_comment(post_id, comment_id, reply_text):
  try:
      response = requests.post(
          url="https://api.dtf.ru/v1.6/comment/add",
          headers={
              "X-Device-Token": X_DEVICE_TOKEN,
              "X-Device-Possession-Token": X_DEVICE_POSSESSION_TOKEN,
              "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
          },
          data={
              "id": post_id,
              "reply_to": comment_id,
              "text": reply_text,
          },
      )
      return response
      print('Response HTTP Status Code: {status_code}'.format(
          status_code=response.status_code))
      print('Response HTTP Response Body: {content}'.format(
          content=response.content))
  except requests.exceptions.RequestException as e:
    return f'Exception trying to post a reply {e}'

def get_game_names_from_text(text):
  md_links = re.compile('\[[^\[\]]+\]\([^\(\)]+\)')
  text = md_links.sub('', text)
  matches = re.findall('(\[[^\[\]]+\]|\{[^\{\}]+\})', text)
  for i, m in enumerate(matches):
    matches[i] = m.strip('[]{}')
  return matches

def game_info(name):
  rawg = rawgpy.RAWG('dtf-bot')
  res = rawg.search(name, num_results=1)
  if res.count == 0:
    return None
  game = res[0]
  game.populate()
  if fuzz.partial_ratio(game.name.lower(), name.lower()) > 70:
    return game
  for alt_name in game.alternative_names:
    if fuzz.partial_ratio(alt_name.lower(), name.lower()) > 70:
      return game
  else:
    return None

def game_text(game):
  pubs = []
  for pub in game.publishers:
    pubs.append(f'[{pub.name}](https://rawg.io/publishers/{pub.slug})')
  publishers_text = ', '.join(pubs)
  text = f'''[{game.name}](https://rawg.io/games/{game.slug})
Дата релиза: {game.released}
Метакритикс: [{game.metacritic}]({game.metacritic_url})
Издатель: {publishers_text}'''
  stores = []
  for store in game.stores:
    stores.append(f'[{store.name}]({store.url})')
  stores_text = ' • '.join(stores)
  text = '\n'.join([text, stores_text])
  return text


@app.route("/comment_webhook", methods=['POST'])
def comment_webhook():
  payload = request.get_json()
  # TODO: save payload to a database along with a timestamp for further analytics needs
  if payload['type'] != 'new_comment':
    raise Exception(f'unexpected webhook payload type = {data["type"]}, expected new_comment')
  post_id = payload['data']['content']['id']
  comment_id = payload['data']['id']
  comment_text = payload['data']['text']
  comment_author = payload['data']['creator']['id']
  if comment_author == 128204:
    return('OK')
  if post_id == 47384:
    print(f'payload: {payload}')
  games_texts = []
  games_names = get_game_names_from_text(comment_text)
  print(f'games_names: {games_names}')
  for game_name in games_names:
    game = game_info(game_name)
    if game is not None:
      games_texts.append(game_text(game))
  reply_text = '\n'.join(games_texts)
  if reply_text != '' and post_id == 47384:
    send_a_comment(post_id = post_id, comment_id = comment_id, reply_text = reply_text)
  return('OK')
  # TODO: save a reply to a database along with a timestamp for further analytics needs