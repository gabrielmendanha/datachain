from flask import Flask, render_template, jsonify, request, redirect
from bigchaindb_driver.crypto import generate_keypair
from werkzeug.utils import secure_filename
from bigchaindb_driver import BigchainDB
import ipfsapi

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
api_endpoint = 'http://localhost:9984/api/v1'
ipfs = ipfsapi.connect('127.0.0.1', 5001)
bigchain = BigchainDB(api_endpoint)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.debug = True


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


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        print(request.form)
        if 'file' not in request.files or request.files['file'].filename == '':
            return redirect('/')

        file = request.files['file']
        if allowed_file(file.filename):
            print(ipfs.add(file))
            return redirect('/generateKeys')

if __name__ == '__main__':
    app.run()
