from block import *
from utils import *


class Blockchain:
    def __init__(self, chain=None):
        if chain is None:
            chain = [Block()]
        self.chain = chain

    def create_block(self, data=None):
        index = self.chain[-1].index + 1
        prev_hash = self.chain[-1].generate_hash().hexdigest()
        block = Block(index, prev_hash, data)
        self.chain.append(block)
        return block

    def __str__(self):
        ret_str = ""
        for block in self.chain:
            ret_str += f"{block}\n"
        return ret_str[:-1]

    def get_validators_dict(self):
        validators = {}
        for block in self.chain:
            transaction = block.data
            if transaction.receiver == STAKE_ADDRESS:
                if not (transaction.sender in validators):
                    validators[transaction.sender] = transaction.amount
                else:
                    validators[transaction.sender] += transaction.amount

        return validators

    def get_balance(self, public_key):
        """gets a public_key and returns the balance associated with it"""
        sum_value = 0
        for block in self.chain:
            transaction = block.data
            if block.validator == public_key:
                sum_value += transaction.fee

            if transaction.receiver == public_key:
                sum_value += transaction.amount

            if transaction.sender == public_key:
                sum_value -= (transaction.amount + transaction.fee)

        return sum_value

    def to_json(self):
        blockchain_dict = dict(self.__dict__)
        block_list = []
        for block in blockchain_dict["chain"]:
            block_dict = dict(block.__dict__)
            transaction = block_dict["data"]
            block_dict["data"] = transaction.__dict__
            block_list.append(block_dict)
        blockchain_dict["chain"] = block_list
        return str(json.dumps(blockchain_dict, indent=4))

    @staticmethod
    def from_json(data):
        data_dict = json.loads(data)
        block_list = []
        for block in data_dict["chain"]:
            block_list.append(Block.from_json(block))
        return Blockchain(block_list)
