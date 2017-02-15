from flask import Flask, render_template, jsonify, request, redirect
from bigchaindb_driver.crypto import generate_keypair
from bigchaindb_driver import BigchainDB
from werkzeug.utils import secure_filename
import datetime
import ipfsapi
import shutil
import time
import os

app = Flask(__name__)

UPLOAD_FOLDER = '/uploads/'
API_ENDPOINT = 'http://localhost:9984'
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
    print(person)
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

            timestamp = int(time.time())

            metadata = {
                'timestamp': str(timestamp)
            }

            prepared_creation_tx = bigchain.transactions.prepare(
                operation='CREATE',
                signers=public_key,
                asset=payload,
                metadata=metadata
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
    current_owner = transaction['outputs'][0]['public_keys'][0]
    status = bigchain.transactions.status(transaction_id)['status']
    timestamp = transaction['metadata']['timestamp']
    file_timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))


    if transaction['operation'] == 'TRANSFER':
        transaction = bigchain.transactions.retrieve(transaction['asset']['id'])

    file_name = transaction['asset']['data']['Name']
    file_hash = transaction['asset']['data']['Hash']

    download_link = 'https://gateway.ipfs.io/ipfs/' + file_hash #TODO COLOCAR CONSTANTE IPFS GATEWAY

    return render_template('download.html', file_name=file_name, download_link=download_link,
                           file_hash=file_hash, file_timestamp=file_timestamp, current_owner=current_owner,
                           transaction_id=transaction_id, status=status)


@app.route('/transfer', methods=['POST'])
def transfer():
    transaction_id = request.form['tx_id_send']
    sender_private_key = request.form['sender-privKey']
    dest_public_key = request.form['dest-pubKey']
    transaction = bigchain.transactions.retrieve(transaction_id)

    if transaction['operation'] == 'TRANSFER':
        asset_id = transaction['asset']['id']
    else:
        asset_id = transaction['id']

    transfer_asset = {
        'id': asset_id
    }

    output_index = 0
    output = transaction['outputs'][output_index]

    transfer_input = {
        'fulfillment': output['condition']['details'],
        'fulfills': {
            'output': output_index,
            'txid': transaction['id'],
        },
        'owners_before': output['public_keys'],
    }

    prepared_transfer_tx = bigchain.transactions.prepare(
        operation='TRANSFER',
        asset=transfer_asset,
        inputs=transfer_input,
        recipients=dest_public_key,
    )

    fulfilled_transfer_tx = bigchain.transactions.fulfill(
        prepared_transfer_tx,
        private_keys=sender_private_key,
    )

    bigchain.transactions.send(fulfilled_transfer_tx)

    return "ok"

    # pair 1
    # pub 7xaCsyEs3mmoL5cDG73HqHXGxLtrZRm6GGf4Kv4qq2kp
    # priv 8qmV2CpRr1yxvYnsg8DYpAFZUs9rBMBNUbrfjFc7Kkxz
    # tx id 80af48990a90c9761e9d2ad29762157dc60fca0ab2c93387bbbee9b708467515

    # pair 2
    # pub key 3EFKgepf6WFrZ4MjPUz1Wq2vPDAWpq2mazQedSPMnxPb
    # priv key DQVrgoBQYtvdwcZMRYnJFXjBbygzb72DbuAUz7JxbXA


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == '__main__':
    app.run()
