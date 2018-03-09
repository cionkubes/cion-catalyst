import os
import sys

import rethinkdb as r
from flask import Flask, abort
from flask.globals import request
from logzero import logger

app = Flask(__name__)

db_host = None
db_port = None
url_token = ''


def get_from_file(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except IOError:
        return None


def get_url_token():
    if 'URL_TOKEN' not in os.environ:
        logger.error('Please configure URL_TOKEN as an environment variable '
                     'on this service')
        sys.exit(1)

    token_env = os.environ['URL_TOKEN']

    if 'file::' in token_env:
        return get_from_file(token_env[len('file::'):])
    elif 'secret::' in token_env:
        return get_from_file(f'/run/secrets/{token_env[len("secret::"):]}')
    else:
        return token_env


def setup():
    global db_host, db_port, url_token
    db_host = os.environ.get('DATABASE_HOST', default='cion_rdb-proxy')
    db_port = os.environ.get('DATABASE_PORT', default=28015)
    url_token = get_url_token()
    logger.info(f'Initializing catalyst with database host={db_host} '
                f'and port={db_port}')


def get_document(conn, doc_name):
    db_res = r.db('cion').table('documents').get(doc_name).pluck('document') \
        .run(conn)
    return db_res['document']


@app.route('/dockerhub/<token>', methods=['POST'])
def web_hook(token):
    if not token == url_token:
        abort(404)

    req_json = request.get_json()  # type: dict

    try:
        image = f'{req_json["repository"]["repo_name"]}:' \
                f'{req_json["push_data"]["tag"]}'
    except KeyError:
        return '{"Status": "invalid request body"}', 422

    logger.info(f'Received push from docker-hub with image {image}')
    conn = r.connect(db_host, db_port)

    # insert data
    data = {
        'image-name': image,
        'event': 'new-image',
        'status': 'ready',
        'time': r.now().to_epoch_time()
    }

    r.db('cion').table('tasks').insert(data).run(conn)

    conn.close()
    return '{"status": "deploy added to queue"}', 202


@app.route('/registry/<token>', methods=['POST'])
def web_hook_notification(token):
    if not token == url_token:
        abort(404)

    req_json = request.get_json()  # type: dict

    for event in req_json['events']:
        if 'push' == event['action']:
            try:
                image = f"{event['target']['repository']}:" \
                        f"{event['target']['tag']}"
            except KeyError:
                return '{"Status": "invalid request body"}', 422

            logger.info(f'Received push from registry with image {image}')
            conn = r.connect(db_host, db_port)

            # insert data
            data = {
                'image-name': image,
                'event': 'new-image',
                'status': 'ready',
                'time': r.now().to_epoch_time()
            }

            r.db('cion').table('tasks').insert(data).run(conn)
            conn.close()
            return '{"status": "deploy added to queue"}', 202
        else:
            return '{"status": "Something went wrong"}', 422


if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=80, debug=True)
