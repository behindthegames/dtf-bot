import concurrent.futures
import datetime
import os
import re
from time import sleep

import rawgpy
import requests
import sentry_sdk
from flask import Flask, request
from fuzzywuzzy import fuzz
from sentry_sdk.integrations.flask import FlaskIntegration

X_DEVICE_TOKEN = os.environ['X_DEVICE_TOKEN']
X_DEVICE_POSSESSION_TOKEN = os.environ['X_DEVICE_POSSESSION_TOKEN']
URL_SECRET = os.environ['URL_SECRET']
BOT_ID = os.environ['BOT_ID']
SENTRY_URL = os.environ.get('SENTRY_URL')
MAX_RESULTS = 5
RETRIES = 10
RETRY_TIMEOUT = 5

if SENTRY_URL:
    sentry_sdk.init(dsn=SENTRY_URL, integrations=[FlaskIntegration()])

app = Flask(__name__)

stores = [
    'steam',
    'playstation-store',
    'xbox-store',
    'apple-appstore',
    'gog',
    'nintendo',
    'xbox360',
    'google-play',
    'itch',
    'epic-games',
    'discord'
]
stores_order = {store: i for i, store in enumerate(stores)}

executor = concurrent.futures.ThreadPoolExecutor()


def send_a_comment(post_id, comment_id, reply_text):
    requests.post(
        url='https://api.dtf.ru/v1.8/comment/add',
        headers={
            'X-Device-Token': X_DEVICE_TOKEN,
            'X-Device-Possession-Token': X_DEVICE_POSSESSION_TOKEN,
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        },
        data={
            'id': post_id,
            'reply_to': comment_id,
            'text': reply_text,
        },
    )


def get_game_names_from_text(text):
    md_links = re.compile(r'\[[^\[\]]+\]\([^()]+\)')
    text = md_links.sub('', text)
    matches = re.findall(r'(\[[^\[\]]+\]|{[^{\}]+\})', text)
    for i, m in enumerate(matches):
        matches[i] = m.strip('[]{}')
    return matches


def game_info(name, retry=RETRIES):
    rawg = rawgpy.RAWG('dtf-bot')
    try:
        res = rawg.search(name, num_results=1)
    except:
        if not retry:
            raise
        retry -= 1
        sleep(RETRY_TIMEOUT * (RETRIES - retry))
        return game_info(name, retry=retry)
    if not res:
        return
    game = res[0]
    game.populate()
    if fuzz.partial_ratio(game.name.lower(), name.lower()) > 70:
        return game
    if hasattr(game, 'alternative_names'):
        for alt_name in game.alternative_names:
            if fuzz.partial_ratio(alt_name.lower(), name.lower()) > 70:
                return game


def game_text(game):
    text = f'🎮 [{game.name}](https://rawg.io/games/{game.slug})'
    if hasattr(game, 'released') and game.released:
        text = text + f'\nДата релиза: {datetime.datetime.strptime(game.released, "%Y-%m-%d").strftime("%d.%m.%Y")}'
    if hasattr(game, 'metacritic') and game.metacritic:
        text = text + f'\nРейтинг Metacritic: [{game.metacritic}]({game.metacritic_url})'
    if hasattr(game, 'developers') and game.developers:
        devs = []
        for dev in game.developers:
            devs.append(f'{dev.name}')
        developers_text = ', '.join(devs)
        text = text + f'\n\nРазработчик{"и" if len(devs) > 1 else ""}: {developers_text}'
    if hasattr(game, 'publishers') and game.publishers:
        pubs = []
        for pub in game.publishers:
            pubs.append(f'{pub.name}')
        publishers_text = ', '.join(pubs)
        text = text + f'\nИздател{"и" if len(pubs) > 1 else "ь"}: {publishers_text}'
    if hasattr(game, 'stores') and game.stores:
        stores = []
        for store in sorted(game.stores, key=lambda s: stores_order.get(s.slug) or len(stores_order)):
            stores.append(f'[{store.name}]({store.url})')
        stores_text = '\n🛒 ' + ' • '.join(stores)
        text = '\n'.join([text, stores_text])
    return text


def deal_with_comment(payload):
    assert payload['type'] == 'new_comment'
    post_id = payload['data']['content']['id']
    comment_id = payload['data']['id']
    comment_text = payload['data']['text']
    comment_author = payload['data']['creator']['id']
    if int(comment_author) == int(BOT_ID):
        return
    games_texts = []
    slugs = set()
    for game_name in get_game_names_from_text(comment_text):
        # skip [1], [23], etc.
        if len(game_name) < 3 and game_name.isdigit():
            continue
        # skip [@1234|name]
        if game_name[0] == '@':
            continue
        game = game_info(game_name)
        if not game:
            continue
        if game.slug in slugs:
            continue
        games_texts.append(game_text(game))
        slugs.add(game.slug)
        if len(slugs) == MAX_RESULTS:
            break
    if games_texts:
        reply_text = '\n\n———\n\n'.join(games_texts)
        send_a_comment(post_id=post_id, comment_id=comment_id, reply_text=reply_text)


def execute(*args, **kwargs):
    try:
        deal_with_comment(*args, **kwargs)
    except Exception as e:
        if not SENTRY_URL:
            raise e
        sentry_sdk.capture_exception(e)


@app.route('/comment_webhook', methods=['POST'])
def comment_webhook():
    if request.args.get('secret') != URL_SECRET:
        return 'NOTOK'
    payload = request.get_json()
    if payload:
        executor.submit(execute, payload)
    return 'OK'


@app.route('/', methods=['GET'])
def main():
    return 'OK'
