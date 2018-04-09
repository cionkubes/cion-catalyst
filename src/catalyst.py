import asyncio

import rethinkdb as r
from aiohttp import web
from async_rethink import connection
from logzero import logger

r.set_loop_type('asyncio')

conn = None

db_host = None
db_port = None
url_token = ''

app = web.Application()

def init():
    global conn
    db_host = os.environ['DATABASE_HOST']
    db_port = os.environ['DATABASE_PORT']

    conn = asyncio.get_event_loop().run_until_complete(connection(db_host, db_port))


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
    print(url_token)
    logger.info(f'Initializing catalyst with database host={db_host} '
                f'and port={db_port}')


def get_document(conn, doc_name):
    db_res = r.db('cion').table('documents').get(doc_name).pluck('document') \
        .run(conn)
    return db_res['document']


async def web_hook(request):
    if not request.match_info['token'] == url_token:
        return web.Response(status=404,
                            text='{"error": "Not found."}',
                            content_type='application/json')

    req_json = await request.json()  # type: dict

    try:
        image = f'{req_json["repository"]["repo_name"]}:' \
                f'{req_json["push_data"]["tag"]}'
    except KeyError:
        return web.Response(status=422,
                            text='{"error: invalid request body',
                            content_type='application/json')

    logger.info(f'Received push from docker-hub with image {image}')

    # insert data
    data = {
        'image-name': image,
        'event': 'new-image',
        'status': 'ready',
        'time': r.now().to_epoch_time()
    }

    await conn.run(
        conn.db().table('tasks').insert(data)
    )

    return web.Response(status=202,
                        text='{"status": "deploy added to queue"}',
                        content_type='application/json')


async def web_hook_notification(request):
    if not request.match_info['token'] == url_token:
        return web.Response(status=404,
                            text='{"error": "Not found"}',
                            content_type='application/json')

    req_json = await request.json()  # type: dict

    for event in req_json['events']:
        print(event['action'])
        if 'push' == event['action']:
            try:
                image = f"{event['target']['repository']}:" \
                        f"{event['target']['tag']}"
            except KeyError:
                return web.Response(status=422,
                                    text='{"error: invalid request body',
                                    content_type='application/json')

            logger.info(f'Received push from registry with image {image}')

            # insert data
            data = {
                'image-name': image,
                'event': 'new-image',
                'status': 'ready',
                'time': r.now().to_epoch_time()
            }

            await conn.run(
                conn.db().table('tasks').insert(data)
            )

            return web.Response(status=202,
                                text='{"status": "deploy added to queue"}',
                                content_type='application/json')
        else:
            return web.Response(status=422,
                                text='{"status": "Something went wrong"}',
                                content_type='application/json')



if __name__ == '__main__':
    import sys
    import os
    setup()
    init()
    app.router.add_post('/dockerhub/{token}', web_hook)
    app.router.add_post('/registry/{token}', web_hook_notification)

    web.run_app(app, host='0.0.0.0', port=8080)