from flask import Flask, render_template, jsonify, request, redirect
from bigchaindb_driver.crypto import generate_keypair
from bigchaindb_driver import BigchainDB
from werkzeug.utils import secure_filename
import ipfsapi
import shutil
import os

app = Flask(__name__)

UPLOAD_FOLDER = '/uploads/'
API_ENDPOINT = 'http://localhost:9984/api/v1'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app.config['DEBUG'] = True  # Comment this line before deploying
ipfs = ipfsapi.connect('127.0.0.1', 5001)
bigchain = BigchainDB(API_ENDPOINT)


@app.route('/', methods=['POST', 'GET'])
def index():
    return render_template('index.html')


@app.route('/generateKeys')
def generate_keys():
    person = generate_keypair()
    print (person)
    key_pair = {
        "public": person.public_key,
        "private": person.private_key
    }
    return jsonify(key_pair)


@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':

        file = request.files['file']
        public_key = request.form['pubKey']
        private_key = request.form['privKey']

        # Verify if file exists and is valid
        if 'file' not in request.files or file.filename == '':
            return redirect('/')

        if file and allowed_file(file.filename):

            filename = secure_filename(file.filename)
            base_destination = APP_ROOT + UPLOAD_FOLDER + public_key
            destination = os.path.join(APP_ROOT + UPLOAD_FOLDER + public_key + '/', filename)

            if not os.path.isdir(base_destination):
                os.mkdir(base_destination)

            file.save(destination)
            ipfs_file = ipfs.add(destination)
            shutil.rmtree(base_destination)

            payload = {
                'data': {
                    'Hash': ipfs_file['Hash'],
                    'Name': ipfs_file['Name']
                },
            }

            prepared_creation_tx = bigchain.transactions.prepare(
                operation='CREATE',
                signers=public_key,
                asset=payload,
            )

            fulfilled_creation_tx = bigchain.transactions.fulfill(
                prepared_creation_tx, private_keys=private_key)

            bigchain.transactions.send(fulfilled_creation_tx)

            txid = fulfilled_creation_tx['id']

            trials = 0
            while trials < 100:

                try:
                    if bigchain.transactions.status(txid).get('status') == 'valid':
                        break

                except bigchain.exceptions.NotFoundError:
                        trials += 1

            return "ok " + txid + " " + str(bigchain.transactions.status(txid))


@app.route('/download', methods=['POST'])
def download():
    transaction_id = request.form['tx_id']
    transaction = bigchain.transactions.retrieve(transaction_id)
    file_name = transaction['transaction']['asset']['data']['Name']
    file_hash = transaction['transaction']['asset']['data']['Hash']
    download_link = 'https://gateway.ipfs.io/ipfs/' + file_hash

    return render_template('download.html', file_name=file_name, download_link=download_link)
 # c1308d0819f3c740c846e96c3645edc87a8659cff26d32d76a74ca695e13200d


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == '__main__':
    app.run()
