import sys
from select import select

from Crypto.PublicKey import ECC

from block import Block
from peer import Peer
from transcation import Transaction

from ui import Ui_MainWindow
from utils import *
from wallet import Wallet

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc


class Main(qtw.QMainWindow):

    def __init__(self):
        super(Main, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # self.setWindowFlag(qtc.Qt.FramelessWindowHint)

        self.wallet = None
        self.peer = Peer()
        self.finished_collecting_missing_blocks_by_button = False  # for checking if finished collecting missing blocks
        self.is_validator = False

        # navigation buttons
        self.ui.login_create_wallet_button.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.create_wallet_page))
        self.ui.login_with_key_button.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.retrieve_wallet_page))
        self.ui.back_to_login_button.clicked.connect(lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.login_page))
        self.ui.retrieve_back_to_login_button.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.login_page))

        # functional buttons
        self.ui.login_button.clicked.connect(self.login)
        self.ui.create_wallet_button.clicked.connect(self.create_wallet)
        self.ui.retrieve_wallet_button.clicked.connect(self.create_wallet_with_private_key)
        self.ui.stop_waiting_button.clicked.connect(self.stop_waiting_for_blocks)
        self.ui.send_kcn_button.clicked.connect(self.send_transaction)

    def login(self):
        password = self.ui.login_password_line.text()
        try:
            with open("storage/encrypted private key.txt", 'r') as protected_private_key_file:
                protected_private_key = protected_private_key_file.read()
                self.wallet = Wallet(ECC.import_key(protected_private_key, passphrase=password))
                self.wallet.create_blockchain_file()

            self.request_missing_blocks()

        except ValueError:
            qtw.QMessageBox.critical(None, 'Fail',
                                     "password doesn't match the protected private key that was provided.")
        except (IndexError, FileNotFoundError):
            qtw.QMessageBox.critical(None, 'Fail', "there is no wallet on this device.")

    def create_wallet(self):
        self.wallet = Wallet()
        password = self.ui.create_password_line.text()
        with open(f"storage/encrypted private key.txt", 'w') as private_key_file:
            if password:
                private_key_file.write(self.wallet.private_key.export_key(format=PRIVATE_KEY_FORMAT,
                                                                          passphrase=password,
                                                                          protection=PRIVATE_KEY_PROTECTION))
            else:
                private_key_file.write(self.wallet.private_key.export_key(format=PRIVATE_KEY_FORMAT,
                                                                          protection=PRIVATE_KEY_PROTECTION))
        self.enter_main_menu()

    def create_wallet_with_private_key(self):
        """gets protected private key from user, a  password, and if they match, calls request_missing_blocks"""
        warning_window = qtw.QMessageBox
        answer = warning_window.warning(None, 'Warning',
                                        "creating a new wallet will delete the wallet that is already on this device"
                                        " from it, are you sure you want to create a new wallet?",
                                        warning_window.Yes | warning_window.No)
        if answer == warning_window.Yes:
            password = self.ui.retrieve_password_line.text()
            protected_secret_key = self.ui.retrieve_protected_key_line.text()
            try:
                self.wallet = Wallet(ECC.import_key(protected_secret_key, passphrase=password))
                with open(f"storage/encrypted private key.txt", 'w') as secret_key_file:
                    secret_key_file.write(protected_secret_key)
                self.request_missing_blocks()
                self.enter_main_menu()
            except ValueError:
                qtw.QMessageBox.critical(None, 'Fail',
                                         "password doesn't match the protected private key that was provided.")
        else:
            warning_window.information(None, '', "a wallet was not recreated.")

    def enter_main_menu(self):
        if self.wallet.public_key.export_key(format=PUBLIC_KEY_FORMAT) in self.wallet.blockchain.get_validators_dict():
            self.is_validator = True
        else:
            self.is_validator = False

        self.ui.public_key_label.setText(str(self.wallet.public_key.export_key(format=PUBLIC_KEY_FORMAT)))
        self.ui.balance_label.setText(str(self.wallet.blockchain.get_balance(self.wallet.public_key.export_key
                                                                             (format=PUBLIC_KEY_FORMAT))))
        blockchain_text = self.wallet.blockchain.to_json()
        self.ui.blockchain_label.setText(blockchain_text)

        try:
            self.ui.staked_label.setText(str(self.wallet.blockchain.get_validators_dict()
                                             [self.wallet.public_key.export_key(format=PUBLIC_KEY_FORMAT)]))
        except KeyError:
            self.ui.staked_label.setText('0')

        self.ui.stackedWidget.setCurrentWidget(self.ui.main_page)

        self.handle_blocks()
        self.constant_receive()

    # block handling:
    def handle_blocks(self):
        """calls add_blocks_to_chain and make_blocks"""
        self.add_blocks_to_chain()
        self.make_blocks()

    def add_blocks_to_chain(self):
        """tries to add a block to chain, and keeps calling itself every five seconds"""
        if self.wallet.add_a_block_to_chain():
            # checking if validator now:
            if self.wallet.public_key.export_key(
                    format=PUBLIC_KEY_FORMAT) in self.wallet.blockchain.get_validators_dict():
                self.is_validator = True
            else:
                self.is_validator = False

            # clearing trees:
            # self.ui.transaction_pool_tree.clear()
            # self.ui.proposed_blocks_tree.clear()

        # update blockchain file and blockchain tree:
        self.update_blockchain_file()
        with open(f"storage\\blockchain.json", "r") as blockchain_file:
            pass
            # self.put_json_chain_on_tree(blockchain_file)

        qtc.QTimer.singleShot(10000, self.add_blocks_to_chain)

    def make_blocks(self):
        """tries to make a block and send it, calls itself every five seconds"""
        new_block = self.wallet.create_block()
        if self.is_validator and new_block:
            self.peer.udp_send(new_block)
            # self.ui.transaction_pool_tree.clear()

        qtc.QTimer.singleShot(5000, self.make_blocks)

    # networking:
    def send_transaction(self):
        """sends a transaction, the data for the transaction is provided by the user"""
        public_key = self.ui.send_to_line.text()
        if public_key != STAKE_ADDRESS:
            try:
                ECC.import_key(public_key)
            except (ValueError, IndexError):
                qtw.QMessageBox.critical(None, 'Fail', "public key is incorrect")
                return
        password = self.ui.send_kcn_password_line.text()
        with open(f"storage/encrypted private key.txt", 'r') as secret_key_file:
            protected_secret_key = secret_key_file.read()
            try:
                Wallet(ECC.import_key(protected_secret_key, passphrase=password))
            except ValueError:
                qtw.QMessageBox.critical(None, 'Fail',
                                         "password doesn't match the protected private key that was provided.")
                return

            receiver = self.ui.send_to_line.text()
            # selected_contacts = self.ui.contacts_list.selectedItems()
            # if not selected_contacts:
            #     qtw.QMessageBox.critical(None, 'Fail', "no contact was selected.")
            #     return

            # for receiver in selected_contacts:
            #     try:
            #         receiver = receiver.text().split(": ")[-1]
            #     except AttributeError:
            #         qtw.QMessageBox.critical(None, 'Fail', "no contact selected.")
            #         return

            try:
                amount = float(self.ui.amount_line.text())
            except ValueError:
                qtw.QMessageBox.critical(None, 'Fail', "amount must be a number.")
                return

            if (amount > 0) or (receiver == STAKE_ADDRESS and amount != 0):
                transaction = self.wallet.make_transaction(receiver, amount)
                if transaction:
                    self.peer.udp_send(transaction)
                    qtw.QMessageBox.information(None, 'Success', "successfully sent the transaction.")
                else:
                    qtw.QMessageBox.critical(None, 'Fail',
                                             "you don't have enough coins to complete this transaction.")
            else:
                qtw.QMessageBox.critical(None, 'Fail',
                                         "amount must be more than zero when not retrieving coins from stake, "
                                         "or different to zero when retrieving or staking coins.")

    def constant_receive(self):
        """tries to receive messages from other peers (both tcp and udp), calls itself every 0.01 seconds"""
        if self.peer.tcp_client:
            rlist, wlist, xlist = select([self.peer.udp_receiver, self.peer.tcp_client], [], [], 0.01)
        else:
            rlist, wlist, xlist = select([self.peer.udp_receiver], [], [], 0.01)
        for socket in rlist:
            if socket == self.peer.udp_receiver:
                received_message = self.peer.udp_receive()
                self.received_from_udp_socket(received_message)

            if socket == self.peer.tcp_client:
                try:
                    received_message = socket.recv(RECV_SIZE).decode()
                except ConnectionResetError:
                    received_message = ''
                if received_message[:len("position ")] == "position ":
                    block_position_from_end_of_chain_to_send = int(received_message[len("position "):])
                    self.send_a_missing_block(block_position_from_end_of_chain_to_send)
                elif received_message[len("finished"):] == "finished" or received_message == '':
                    self.peer.close_client()

        qtc.QTimer.singleShot(100, self.constant_receive)

    def received_from_udp_socket(self, message):
        """handles a message that was received by the udp receiver socket"""
        if type(message) == Transaction:
            if self.wallet.add_transaction_to_pool(message):
                print("added")
            else:
                print("not added")
                # self.add_transaction_to_pool_tree(message)
        elif type(message) == Block:
            self.wallet.add_proposed_block(message)
            # self.add_block_to_proposed_tree(message)
        elif type(message) == str and message[:len("connected")] == "connected":
            self.send_a_missing_block(self.wallet.blockchain.chain[-1].index)
        else:
            print("received: " + str(message))

    def send_a_missing_block(self, position):
        """sends a block that might be missing for a newly connected peer on tcp"""
        block_to_send = [block for block in self.wallet.blockchain.chain if block.index == position][0]

        self.peer.tcp_client_send(block_to_send)

    def request_missing_blocks(self):
        """switches to waiting page and starts requesting blocks that might be missing"""
        self.ui.stackedWidget.setCurrentWidget(self.ui.waiting_page)
        self.collect_blocks()

    def update_blockchain_file(self):
        """updates the blockchain file with data from wallet"""
        with open(f"storage\\blockchain.json", "w") as blockchain_file:
            blockchain_file.write(self.wallet.blockchain.to_json())

        blockchain_text = self.wallet.blockchain.to_json()
        self.ui.blockchain_label.setText(blockchain_text)
        self.ui.balance_label.setText(str(self.wallet.get_balance()))
        try:
            self.ui.staked_label.setText(str(self.wallet.blockchain.get_validators_dict()
                                             [self.wallet.public_key.export_key(format=PUBLIC_KEY_FORMAT)]))
        except KeyError:
            self.ui.staked_label.setText('0')

    def collect_blocks(self):
        """collects blocks that might be missing from other peers"""
        self.peer.request_update_connection()
        peers_and_missing_blocks_dict = {}
        finished_collecting_peers = 0
        tcp_connected_peers = []
        finished_collecting_missing_blocks = False

        def collect_blocks_networking():
            nonlocal finished_collecting_peers
            nonlocal tcp_connected_peers
            nonlocal finished_collecting_missing_blocks

            # rlist, wlist, xlist = [], [], []
            rlist = []
            if len(tcp_connected_peers) <= NUMBER_OF_CONNECTED_CLIENTS:
                rlist, _, _ = select([self.peer.tcp_server] + tcp_connected_peers, [], [], 0.01)
            for socket in rlist:
                if socket == self.peer.tcp_server:
                    (new_socket, address) = self.peer.tcp_server.accept()
                    tcp_connected_peers.append(new_socket)

                elif socket in tcp_connected_peers:
                    received_message = socket.recv(RECV_SIZE).decode()
                    if received_message[:len("Block: ")] == "Block: ":
                        received_message = received_message[len("Block: "):]
                        received_block = Block.from_json(received_message)
                        # if block number isn't already in chain
                        if received_block.index not in [block.index for block
                                                        in self.wallet.blockchain.chain]:
                            if socket not in peers_and_missing_blocks_dict:
                                peers_and_missing_blocks_dict[socket] = []
                            peers_and_missing_blocks_dict[socket].append(received_block)
                            socket.send(f"position {received_block.index - 1}".encode())
                        else:
                            socket.send("finished".encode())
                            finished_collecting_peers += 1
                            if finished_collecting_peers >= NUMBER_OF_CONNECTED_CLIENTS:
                                finished_collecting_missing_blocks = True

                    elif received_message == '':
                        tcp_connected_peers.remove(socket)

                    else:
                        print(received_message)

            if not (self.finished_collecting_missing_blocks_by_button or finished_collecting_missing_blocks):
                qtc.QTimer.singleShot(1000, collect_blocks_networking)
            else:
                tcp_connected_peers = []
                self.peer.close_server()
                if finished_collecting_missing_blocks:
                    self.handle_collected_blocks(list(peers_and_missing_blocks_dict.values()))
                self.enter_main_menu()

        collect_blocks_networking()

    def stop_waiting_for_blocks(self):
        """stops waiting for blocks"""
        self.finished_collecting_missing_blocks_by_button = True

    def handle_collected_blocks(self, collected_blocks_lists_list):
        """gets a list of lists of blocks that were collected.
        decides which of the collected blocks should be believed to, and adds them to the blockchain"""

        # put all valid blocks in list
        if collected_blocks_lists_list:
            valid_collected_blocks_lists_list = []
            for collected_blocks_list in collected_blocks_lists_list:
                for collected_block in collected_blocks_list:
                    if collected_block.is_valid(self.wallet.blockchain):
                        valid_collected_blocks_lists_list.append(collected_blocks_list)

            valid_collected_blocks_lists_tuples = []
            for valid_collected_blocks_list in valid_collected_blocks_lists_list:
                valid_collected_blocks_list_tuples = []
                for valid_collected_block in valid_collected_blocks_list:
                    valid_collected_blocks_list_tuples.append(
                        (valid_collected_block.index, valid_collected_block.generate_hash))
                valid_collected_blocks_lists_tuples.append(valid_collected_blocks_list_tuples)

            correct_valid_collected_blocks_list_tuples = most_frequent(valid_collected_blocks_lists_tuples)
            index_of_correct_valid_collected_blocks_list = valid_collected_blocks_lists_tuples.index(
                correct_valid_collected_blocks_list_tuples)
            correct_valid_collected_blocks_list = valid_collected_blocks_lists_list[
                index_of_correct_valid_collected_blocks_list]

            for correct_valid_collected_block in correct_valid_collected_blocks_list:
                self.wallet.add_proposed_block(correct_valid_collected_block)
                if not self.wallet.add_a_block_to_chain():
                    self.request_missing_blocks()


if __name__ == "__main__":
    # wallet = Wallet()
    # second_wallet = Wallet()
    # wallet.create_blockchain_file()
    # wallet.make_transaction_and_add_to_blockchain(second_wallet.public_key.export_key(format=PUBLIC_KEY_FORMAT), 100)
    # is_valid = wallet.blockchain.chain[2].is_valid(wallet.blockchain)
    # print(is_valid)

    # for handling exceptions:
    sys._excepthook = sys.excepthook


    def exception_hook(exctype, value, traceback):
        print(traceback)
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)


    sys.excepthook = exception_hook

    app = qtw.QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())
