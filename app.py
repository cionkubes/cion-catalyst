import os
from flask import Flask, abort
from flask.globals import request
import rethinkdb as r

app = Flask(__name__)

db_host = None
db_port = None
url_token = ''


def setup():
    global db_host, db_port, url_token
    db_host = os.environ.get('DATABASE_HOST', default='cion_rdb-proxy')
    db_port = os.environ.get('DATABASE_PORT', default=28015)
    url_token = os.environ.get('URL_TOKEN', default='ab57eb4ee97e022f9327c3ecc58c64026a4ce3fb')  # TODO: docker secret
    app.logger.info(f'Initializing catalyst with database host={db_host} and port={db_port}')


@app.route('/<token>', methods=['POST'])
def web_hook(token):
    if not token == url_token:
        abort(404)

    req_json = request.get_json()  # type: dict
    image = '{}:{}'.format(req_json['repository']['repo_name'], req_json['push_data']['tag'])

    app.logger.info(f'Received push from docker-hub with image {image}')

    data = {
        'image-name': image,
        'event': 'new-image',
        'status': 'ready'
    }
    r.connect(db_host, db_port).repl()  # TODO: unsure if closing of the connection is required
    r.db('cion').table('tasks').insert(data).run()
    return '{"status": "deploy added to queue"}', 201


if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=80, debug=True)