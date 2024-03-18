from hashlib import sha256
import json
import time

from flask import Flask, request
import requests

# Block hace referencia a un bloque de la cadena de bloques, que contiene transacciones y un hash anterior, así como un nonce. 
class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        # index: posición del bloque en la cadena
        self.index = index
        # transactions: lista de transacciones
        self.transactions = transactions
        # timestamp: marca de tiempo
        self.timestamp = timestamp
        # previous_hash: hash del bloque anterior
        self.previous_hash = previous_hash
        # nonce: número aleatorio
        self.nonce = nonce

    def compute_hash(self):
        """
        # Función que devuelve el hash del contenido del bloque.
        """
        # json.dumps: convierte un objeto de Python en una cadena JSON
        block_string = json.dumps(self.__dict__, sort_keys=True)
        # sha256: devuelve un objeto hash que contiene el hash SHA-256 del contenido de la cadena
        return sha256(block_string.encode()).hexdigest()

# Blockchain es una lista de bloques, con un método para crear el bloque de génesis y otro para agregar un bloque a la cadena.
class Blockchain:
    # difficulty: dificultad de nuestro algoritmo de PoW
    difficulty = 4

    # Método constructor
    def __init__(self):
        # unconfirmed_transactions: lista de transacciones pendientes
        self.unconfirmed_transactions = []
        # chain: lista de bloques
        self.chain = []

    # Método para crear el bloque de génesis, El bloque genesis es el primer bloque de la cadena de bloques.
    def create_genesis_block(self):
        """
        # Función para generar el bloque de génesis y lo agrega a la cadena. El bloque tiene índice 0, previous_hash como 0 y un hash válido.
        """
        # Block: clase que representa un bloque
        genesis_block = Block(0, [], 0, "0")
        # compute_hash: función que devuelve el hash del contenido del bloque
        genesis_block.hash = genesis_block.compute_hash()
        # chain: lista de bloques
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of latest block
          in the chain match.
        """
        previous_hash = self.last_block.hash

        if previous_hash != block.previous_hash:
            return False

        if not Blockchain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    @staticmethod
    def proof_of_work(block):
        """
        # Función que intenta diferentes valores de nonce para obtener un hash que cumpla con nuestros criterios de dificultad.
        """
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash
    
    # Método para agregar una nueva transacción a la lista de transacciones pendientes
    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        # Método para verificar si block_hash es un hash válido del bloque y satisface los criterios de dificultad.
        """
        # verifica si el hash del bloque comienza con un número de ceros igual a la dificultad
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    # Método para verificar si la cadena es válida
    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            # quita el campo hash para volver a calcular el hash
            # usando el método `compute_hash`.
            # delattr: elimina un atributo de un objeto
            delattr(block, "hash")

            # verifica si el hash del bloque es válido y el bloque anterior y el hash del bloque actual coinciden
            if not cls.is_valid_proof(block, block_hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            # restaura el hash eliminado
            block.hash, previous_hash = block_hash, block_hash

        return result
    
    # Método para minar bloques
    def mine(self):
        """
        # Esta función sirve como una interfaz para agregar las transacciones pendientes a la cadena de bloques agregándolas al bloque y descubriendo la Prueba de Trabajo.
        """
        if not self.unconfirmed_transactions:
            return False

        # el último bloque de la cadena
        last_block = self.last_block

        # crea un nuevo bloque con las transacciones pendientes y lo agrega a la cadena
        # y descubre la prueba de trabajo.
        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        # proof_of_work: función que intenta diferentes valores de nonce para obtener un hash que cumpla con nuestros criterios de dificultad.
        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_transactions = []

        return True


app = Flask(__name__)

# el nodo tiene una copia de la cadena de bloques
blockchain = Blockchain()
blockchain.create_genesis_block()

# la lista de nodos en la red
peers = set()


# endpoint to submit a new transaction. This will be used by
# our application to add new data (posts) to the blockchain
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["author", "content"]

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404

    tx_data["timestamp"] = time.time()

    blockchain.add_new_transaction(tx_data)

    return "Success", 201


# endpoint to return the node's copy of the chain.
# Our application will be using this endpoint to query
# all the posts to display.
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data,
                       "peers": list(peers)})


# endpoint to request the node to mine the unconfirmed
# transactions (if any). We'll be using it to initiate
# a command to mine from our application itself.
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    else:
        # Making sure we have the longest chain before announcing to the network
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            # announce the recently mined block to the network
            announce_new_block(blockchain.last_block)
        return "Block #{} is mined.".format(blockchain.last_block.index)


selected_nodes = ["http://10.253.55.151:8000", "http://10.253.19.173:8000"]

# Endpoint para registrar un nuevo nodo en la red
@app.route('/register_node', methods=['POST'])
def register_node():
    node_address = request.json.get('node_address')
    if node_address:
        peers.add(node_address)
        return 'Node registered successfully', 200
    else:
        return 'Invalid node address', 400

# Endpoint para propagar un nuevo bloque a todos los nodos en la red
@app.route('/propagate_block', methods=['POST'])
def propagate_block():
    block_data = request.json
    for peer in peers:
        requests.post(peer + '/receive_block', json=block_data)
    return 'Block propagated successfully', 200

# Endpoint para recibir un nuevo bloque de otro nodo en la red
@app.route('/receive_block', methods=['POST'])
def receive_block():
    block_data = request.json
    # Procesar y agregar el bloque a la cadena de bloques local
    return 'Block received successfully', 200

'''# endpoint to add new peers to the network.
@app.route('/register_node', methods=['POST'])
def register_new_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    # Add the node to the peer list
    peers.add(node_address)

    # Return the consensus blockchain to the newly registered node
    # so that he can sync
    return get_chain()
'''

@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to
    register current node with the node specified in the
    request, and sync the blockchain as well as peer data.
    """
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        global peers
        # update chain and the peers
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain


# endpoint to add a block mined by someone else to
# the node's chain. The block is first verified by the node
# and then added to the chain.
@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201


# endpoint to query unconfirmed transactions
@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)

def consensus():
    """
    Our naive consnsus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('{}chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True

    return False


def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for peer in peers:
        url = "{}add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)

# Uncomment this line if you want to specify the port number in the code
app.run(debug=True, port=8000)
