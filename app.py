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
import datetime
import concurrent.futures
import sqlite3

app = Flask(__name__)

X_DEVICE_TOKEN = os.environ['X_DEVICE_TOKEN']
X_DEVICE_POSSESSION_TOKEN = os.environ['X_DEVICE_POSSESSION_TOKEN']

conn = None
c = None
def init():
  global conn
  global c
  conn = sqlite3.connect('logs.sqlite')
  c = conn.cursor()
executor = concurrent.futures.ProcessPoolExecutor(initializer=init)

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
      return (response.json()['result']['id'], response.json()['result']['text'])
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
  text = f'''🎮 [{game.name}](https://rawg.io/games/{game.slug})\n
Дата релиза: {datetime.datetime.strptime(game.released, '%Y-%m-%d').strftime("%d.%m.%Y")}'''
  if game.metacritic != '':
    text = text + f'\nРейтинг Metacritic: [{game.metacritic}]({game.metacritic_url})'
  if len(game.developers) > 0:
    devs = []
    for dev in game.developers:
      devs.append(f'{dev.name}')
    developers_text = ', '.join(devs)
    text = text + f'\n\nРазработчик{ "и" if len(devs)>1 else ""}: {developers_text}'
  if len(game.publishers) > 0:
    pubs = []
    for pub in game.publishers:
      pubs.append(f'{pub.name}')
    publishers_text = ', '.join(pubs)
    text = text + f'\nИздател{ "и" if len(pubs)>1 else "ь"}: {publishers_text}'
  if len(game.stores) > 0:
    stores = []
    for store in game.stores:
      stores.append(f'[{store.name}]({store.url})')
    stores_text = '\n🛒 ' + ' • '.join(stores)
    text = '\n'.join([text, stores_text])
  return text

def deal_with_comment(payload):
  try:
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
    slugs = set()
    for game_name in games_names:
      game = game_info(game_name)
      if game is not None:
        if game.slug not in slugs:
          games_texts.append(game_text(game))
          slugs.add(game.slug)
    (reply_id, reply_text) = (None, None)
    if len(games_texts) > 0 and post_id == 47384:
      reply_text = 'Кажется, вы искали эти игры.\n\n' + '\n⁣\n'.join(games_texts)
      (reply_id, reply_text) = send_a_comment(post_id = post_id, comment_id = comment_id, reply_text = reply_text)
    c.execute('insert into received (created_at, post_id, comment_id, comment_text, comment_author, games_names, payload, reply_id, reply_text) values (?, ?, ?, ?, ?, ?, ?, ?, ?)', (datetime.datetime.now(), post_id, comment_id, comment_text, comment_author, '❧'.join(games_names), json.dumps(payload), reply_id, reply_text))
    conn.commit()
  except Exception as e:
    print(e)
  return('OK')

@app.route("/comment_webhook", methods=['POST'])
def comment_webhook():
  payload = request.get_json()
  executor.submit(deal_with_comment, payload)
  return('OK')