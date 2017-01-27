

from flask import Flask, render_template, jsonify, request
from flask.ext.uploads import UploadSet, configure_uploads, AllExcept, SCRIPTS, EXECUTABLES
from bigchaindb_driver.crypto import generate_keypair
from bigchaindb_driver import BigchainDB
import os
import ipfsapi
from werkzeug.utils import secure_filename


app = Flask(__name__)

UPLOAD_FOLDER = '/uploads/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

files = UploadSet('files', AllExcept(SCRIPTS + EXECUTABLES))

api_endpoint = 'http://localhost:9984/api/v1'

app.config['UPLOADS_DEFAULT_DEST'] = UPLOAD_FOLDER
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
app.config['DEBUG'] = True
ipfs = ipfsapi.connect('127.0.0.1', 5001)
bigchain = BigchainDB(api_endpoint)
configure_uploads(app, files)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generateKeys')
def generate_keys():
    person = generate_keypair()
    key_pair = {
        "public": person.verifying_key,
        "private": person.signing_key
    }
    return jsonify(key_pair)


@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':

        file = request.files['file']
        # Verifica se o arquivo veio
        if 'file' not in request.files or file.filename == '':
            return "deu pau"

        if file and allowed_file(file.filename):

            filename = secure_filename(file.filename)

            destination = os.path.join(APP_ROOT+UPLOAD_FOLDER, filename)
            file.save(destination)

            return "ok"


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run()
