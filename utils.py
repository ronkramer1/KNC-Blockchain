import configparser
import re

from Crypto.Hash import SHA256
from Crypto.Signature import DSS

config = configparser.ConfigParser()
try:
    config.read('configure.ini')

    FEE_CONSTANT = float(config['transaction']['FEE_CONSTANT'])
    NUM_OF_TRANSACTIONS_IN_BLOCK = int(config['cryptography']['NUM_OF_TRANSACTIONS_IN_BLOCK'])

    CURVE = config['cryptography']['CURVE']
    CURVE_FORMAT = config['cryptography']['CURVE_FORMAT']
    PUBLIC_KEY_FORMAT = config['cryptography']['PUBLIC_KEY_FORMAT']
    PRIVATE_KEY_FORMAT = config['cryptography']['PRIVATE_KEY_FORMAT']
    PRIVATE_KEY_PROTECTION = config['cryptography']['PRIVATE_KEY_PROTECTION']
    STANDARD_FOR_SIGNATURES = config['cryptography']['STANDARD_FOR_SIGNATURES']

    a = int(config['fips-186-3 constants']['a'])
    b = int(config['fips-186-3 constants']['b'])
    p = int(config['fips-186-3 constants']['p'])

    STAKE_ADDRESS = config['cryptography']['STAKE_ADDRESS']

    NUMBER_OF_COINS = float(config['ICH']['NUMBER_OF_COINS'])
    INITIAL_COIN_HOLDER = str(config['ICH']['INITIAL_COIN_HOLDER'])

    RECV_SIZE = eval(config['networking']['RECV_SIZE'])
    UDP_PORT = int(config['networking']['UDP_PORT'])
    TCP_PORT = int(config['networking']['TCP_PORT'])
    NUMBER_OF_CONNECTED_CLIENTS = int(config['networking']['NUMBER_OF_CONNECTED_CLIENTS'])

except configparser.ParsingError:
    print("could not read from ini")
    FEE_CONSTANT = 0.02

    CURVE = 'P-256'
    CURVE_FORMAT = 'PEM'
    STANDARD_FOR_SIGNATURES = 'fips-186-3'

    a = -3
    b = 41058363725152142129326129780047268409114441015993725554835256314039467401291
    p = 115792089210356248762697446949407573530086143415290314195533631308867097853951

    RECV_SIZE = 1024 * 10
    UDP_PORT = 50000
    TCP_PORT = 50001
    NUMBER_OF_CONNECTED_CLIENTS = 1

    NUMBER_OF_COINS = 10000.0
    INITIAL_COIN_HOLDER = '''-----BEGIN PUBLIC KEY-----
    MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEofGBl+ldHaybl1JKCfJarla9uEWk
    fwRHMMp1H5yHbcj1GivtKBSRcNVoOMZg18guZquf50pNH2WAtnWz4vVWJQ==
    -----END PUBLIC KEY-----'''


def sha256_hash(*args):
    """return a sha256 hash of a concatenation of the input input"""
    str_rep = ""
    for arg in args:
        str_rep += str(arg)

    return SHA256.new(str_rep.encode())


def most_frequent(lst):
    """takes a list and returns the most frequent element in it"""
    counter = 0
    if lst:
        most_freq = lst[0]
    else:
        return
    for i in lst:
        curr_frequency = lst.count(i)
        if curr_frequency > counter:
            counter = curr_frequency
            most_freq = i

    return most_freq


def verify(self, hash_value, signature):
    verifier = DSS.new(self.public_key, STANDARD_FOR_SIGNATURES)
    try:
        return verifier.verify(hash_value, bytes(signature))
    except ValueError:
        return False


def password_check(password):
    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        8 characters length or more
        1 digit or more
        1 symbol or more
        1 uppercase letter or more
        1 lowercase letter or more
    """

    # calculating the length
    length_error = len(password) < 8

    # searching for digits
    digit_error = re.search(r"\d", password) is None

    # searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None

    # searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None

    # searching for symbols
    symbol_error = re.search(r"\W", password) is None

    # overall result
    password_ok = not (length_error or digit_error or uppercase_error or lowercase_error or symbol_error)

    return {
        'password_ok': password_ok,
        'length_error': length_error,
        'digit_error': digit_error,
        'uppercase_error': uppercase_error,
        'lowercase_error': lowercase_error,
        'symbol_error': symbol_error,
    }