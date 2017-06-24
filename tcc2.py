import builtins

import bigchaindb_driver
from flask import Flask, render_template, request, send_file
from bigchaindb_driver.crypto import generate_keypair
from bigchaindb_driver import BigchainDB
from werkzeug.utils import secure_filename
import datetime
import ipfsapi
import shutil
import time
import os
from io import BytesIO

app = Flask(__name__)

UPLOAD_FOLDER = '/uploads/'
API_ENDPOINT = 'http://localhost:9984'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
ALLOWED_EXTENSIONS = {'pdf'}
IPFS_GATEWAY = 'https://gateway.ipfs.io/ipfs/'

app.config['DEBUG'] = True  # Comment this line before deploying
ipfs = ipfsapi.connect('127.0.0.1', 5001)
bigchain = BigchainDB(API_ENDPOINT)


@app.route('/', methods=['POST', 'GET'])
def index():
    return render_template('index.html')


@app.route('/comprovanteUpload/<tx_id>/<pub_key>')
def uploadReceipt(tx_id, pub_key):

    transaction = bigchain.transactions.retrieve(tx_id)

    if transaction['operation'] == 'TRANSFER':
        transaction = bigchain.transactions.retrieve(transaction['asset']['id'])

    file_name = transaction['asset']['data']['name']

    header = '############ Comprovante emitido em: ' + str(
        datetime.datetime.utcfromtimestamp(int(time.time()))) + ' ############'
    body = '\n\t\t\t\tImportante!' \
           '\nGuarde as informações abaixo em um local seguro.' \
           '\nSem essas informações não será possível transferir ou consultar o seu documento.' \
           '\nPor questões de segurança este comprovante não contêm a chave privada.' \
           '\n—————————————————————————————————————————————————————————————————————————————————————' \
           '\n| ID da transação: ' + tx_id + ' |' \
           '\n| Chave Pública: ' + pub_key + '                       |' \
           '\n| Nome do documento:' + file_name + \
           '\n—————————————————————————————————————————————————————————————————————————————————————'

    comprovante = BytesIO()
    comprovante.write((header + body).encode('utf-8'))
    comprovante.seek(0)

    return send_file(comprovante,
                     attachment_filename="Comprovante.txt",
                     as_attachment=True)


@app.route('/generateKeys')
def generate_keys():
    person = generate_keypair()
    header = '############################ Emitido em: ' + str(
        datetime.datetime.utcfromtimestamp(int(time.time()))) + ' ############################'
    body = '\n				Importante!' \
           '\n		Guarde as informações abaixo em um local seguro.' \
           '\n	————————————————————————————————————————————————————————————————————' \
           '\n	| Assinatura Pública: ' + person.public_key + ' |' \
           '\n	| Assinatura Privada: ' + person.private_key + ' |' \
           '\n	————————————————————————————————————————————————————————————————————'

    comprovante = BytesIO()
    comprovante.write((header + body).encode('utf-8'))
    comprovante.seek(0)
    return send_file(comprovante, attachment_filename="Par Assinaturas.txt", as_attachment=True)


@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':

        file = request.files['file']
        public_key = request.form['pubKey']
        private_key = request.form['privKey']

        # Verify if file exists and is valid
        if 'file' not in request.files or file.filename == '':
            return render_template('index.html', error=True, message="Não detectamos o seu documento. Tente novamente.")

        # Verify if file extension is permitted
        if file and not allowed_file(file.filename):
            return render_template('index.html', error=True, message="Tipo de arquivo não permitido. Somente PDF.")

        # Verify if both keys are fulfilled
        if not public_key or not private_key:
            return render_template('index.html', error=True, message="Uma, ou ambas assinaturas não foram fornecidas.")

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
                'hash': ipfs_file['Hash'],
                'name': ipfs_file['Name']
            },
        }

        timestamp = int(time.time())

        metadata = {
            'timestamp': str(timestamp)
        }

        try:
            prepared_creation_tx = bigchain.transactions.prepare(
                operation='CREATE',
                signers=public_key,
                asset=payload,
                metadata=metadata
            )
        except builtins.ValueError:
            return render_template('index.html', error=True, message="Assinatura pública não está completa.")

        try:
            fulfilled_creation_tx = bigchain.transactions.fulfill(
                prepared_creation_tx, private_keys=private_key)

        except builtins.ValueError:
            return render_template('index.html', error=True, message="Assinatura privada não está completa.")

        except bigchaindb_driver.exceptions.MissingPrivateKeyError:
            return render_template('index.html', error=True, message="O par de assinaturas não combina.")

        bigchain.transactions.send(fulfilled_creation_tx)

        txid = fulfilled_creation_tx['id']

        return render_template('upload.html', txid=txid, public_key=public_key, private_key=private_key)


@app.route('/download', methods=['POST'])
def download():

    transaction_id = request.form['tx_id']
    pub_key = request.form['pubKey']

    # Verify if transaction id is fulfilled
    if not transaction_id:
        return render_template('index.html', error=True,
                               message="Referência do documento não foi detectada. Tente novamente.")

    try:
        transaction = bigchain.transactions.retrieve(transaction_id)

    except bigchaindb_driver.exceptions.NotFoundError:
        return render_template('index.html', error=True,
                               message="Ops. Este documento não foi encontrado.")

    current_owner = transaction['outputs'][0]['public_keys'][0]
    status = bigchain.transactions.status(transaction_id)['status']
    timestamp = transaction['metadata']['timestamp']
    file_timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))

    if transaction['operation'] == 'TRANSFER':
        transaction = bigchain.transactions.retrieve(transaction['asset']['id'])

    if pub_key == current_owner:
        isOwner = True
    else:
        isOwner = False

    if not pub_key:
        isOwner = None

    file_name = transaction['asset']['data']['name']
    file_hash = transaction['asset']['data']['hash']

    download_link = IPFS_GATEWAY + file_hash

    return render_template('download.html', file_name=file_name, download_link=download_link,
                           file_hash=file_hash, file_timestamp=file_timestamp, current_owner=current_owner,
                           transaction_id=transaction_id, status=status, isOwner=isOwner)


@app.route('/transfer', methods=['POST'])
def transfer():
    transaction_id = request.form['tx_id_send']
    sender_private_key = request.form['sender-privKey']
    dest_public_key = request.form['dest-pubKey']

    # Verify if sender key is fulfilled
    if not sender_private_key:
        return render_template('index.html', error=True, message="A assinatura do remetente não foi fornecida.")

    if not dest_public_key:
        return render_template('index.html', error=True, message="A assinatura do destinatário não foi fornecida.")

    try:
        transaction = bigchain.transactions.retrieve(transaction_id)

    except bigchaindb_driver.exceptions.NotFoundError:
        return render_template('index.html', error=True,
                               message="Ops. Este documento não foi encontrado.")

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

    try:
        prepared_transfer_tx = bigchain.transactions.prepare(
            operation='TRANSFER',
            asset=transfer_asset,
            inputs=transfer_input,
            recipients=dest_public_key,
        )

    except builtins.ValueError:
        return render_template('index.html', error=True, message="Assinatura pública não está completa.")

    try:
        fulfilled_transfer_tx = bigchain.transactions.fulfill(
            prepared_transfer_tx,
            private_keys=sender_private_key,
        )

    except builtins.ValueError:
        return render_template('index.html', error=True, message="Assinatura privada não está completa.")

    except bigchaindb_driver.exceptions.MissingPrivateKeyError:
        return render_template('index.html', error=True, message="A assinatura privada não confere.")

    bigchain.transactions.send(fulfilled_transfer_tx)

    return render_template('index.html', success=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == '__main__':
    app.run()
