import os
import threading
import time
import webbrowser
import traceback
import sys
import types
import functools

# =====================================================================
# Kivy imports first — these MUST succeed for anything to render
# =====================================================================
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.uix.textinput import TextInput

# =====================================================================
# Android logcat helper (works even if android libs are missing)
# =====================================================================
LOG_TAG = "SOS69069CSOS"
APP_VERSION = "0.4"

# Early theme constants (must exist before make_button/make_input run)
try:
    from kivy.utils import get_color_from_hex as _gch
except Exception:
    def _gch(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)

BG          = _gch("#0a0e0b")
CARD_BG     = _gch("#141b16")
INPUT_BG    = _gch("#232f27")
BORDER      = _gch("#2c3830")
TEXT        = _gch("#ffffff")
TEXT_SEC    = _gch("#bbbbbb")
TEXT_MUTED  = _gch("#9ca3af")
GREEN       = _gch("#04aa34")
GREEN_BR    = _gch("#22c55e")
BLUE        = _gch("#0038fe")
BLUE_SOFT   = _gch("#5b8bff")
YELLOW      = _gch("#facc15")
ORANGE      = _gch("#f97316")
DANGER      = _gch("#ef4444")
GRAY        = INPUT_BG
WHITE       = TEXT
try:
    Window.clearcolor = BG
except Exception:
    pass


def _alog(msg):
    try:
        from jnius import autoclass
        autoclass('android.util.Log').i(LOG_TAG, str(msg))
    except Exception:
        print("[{}] {}".format(LOG_TAG, msg))

def _alog_err(msg):
    try:
        from jnius import autoclass
        autoclass('android.util.Log').e(LOG_TAG, str(msg))
    except Exception:
        print("[{}][ERR] {}".format(LOG_TAG, msg))


# =====================================================================
# Pure-Python cytoolz stub (complete enough for eth-account 0.10.0)
# Injected into sys.modules BEFORE eth_account is imported
# =====================================================================
def _make_cytoolz_stub():
    mod = types.ModuleType("cytoolz")

    def dissoc(d, *keys):
        return {k: v for k, v in d.items() if k not in keys}

    def assoc(d, key, value):
        result = dict(d)
        result[key] = value
        return result

    def merge(*dicts):
        result = {}
        for d in dicts:
            if d:
                result.update(d)
        return result

    def get_in(keys, coll, default=None):
        for key in keys:
            try:
                coll = coll[key]
            except (KeyError, TypeError, IndexError):
                return default
        return coll

    def curry(func):
        """Minimal curry implementation sufficient for eth-account."""
        @functools.wraps(func)
        def curried(*args, **kwargs):
            try:
                needed = func.__code__.co_argcount
            except Exception:
                needed = 1
            if len(args) + len(kwargs) >= needed:
                return func(*args, **kwargs)
            return functools.partial(curried, *args, **kwargs)
        return curried

    def compose(*funcs):
        def composed(*args, **kwargs):
            for f in reversed(funcs):
                args = (f(*args, **kwargs),)
                kwargs = {}
            return args[0] if args else None
        return composed

    def identity(x):
        return x

    def first(seq):
        return next(iter(seq))

    def second(seq):
        it = iter(seq)
        next(it)
        return next(it)

    def last(seq):
        item = None
        for item in seq:
            pass
        return item

    def take(n, seq):
        return list(seq)[:n]

    def drop(n, seq):
        it = iter(seq)
        for _ in range(n):
            next(it, None)
        return list(it)

    def concat(seqs):
        for seq in seqs:
            for item in seq:
                yield item

    def mapcat(func, seqs):
        return concat(map(func, seqs))

    def pipe(data, *funcs):
        for f in funcs:
            data = f(data)
        return data

    partial = functools.partial

    def keymap(func, d):
        return {func(k): v for k, v in d.items()}

    def valmap(func, d):
        return {k: func(v) for k, v in d.items()}

    def itemmap(func, d):
        return dict(func(k, v) for k, v in d.items())

    def keyfilter(pred, d):
        return {k: v for k, v in d.items() if pred(k)}

    def valfilter(pred, d):
        return {k: v for k, v in d.items() if pred(v)}

    def itemfilter(pred, d):
        return {k: v for k, v in d.items() if pred((k, v))}

    # Expose everything eth-account is likely to need
    for name, obj in list(locals().items()):
        if not name.startswith("_") and name != "mod":
            setattr(mod, name, obj)

    mod.functoolz = mod
    mod.dicttoolz = mod
    mod.itertoolz = mod
    return mod

# Install the stub so "import cytoolz" and "from cytoolz import curry" succeed
_cytoolz = _make_cytoolz_stub()
sys.modules["cytoolz"] = _cytoolz
sys.modules["cytoolz.dicttoolz"] = _cytoolz
sys.modules["cytoolz.functoolz"] = _cytoolz
sys.modules["cytoolz.itertoolz"] = _cytoolz


# =====================================================================
# Fix CFFI / pycryptodome crash on Android (PYTHONOPTIMIZE=2)
# Must run BEFORE any Crypto / eth_account / eth_keyfile import
# =====================================================================
import ctypes
try:
    ctypes.pythonapi = ctypes.PyDLL("libpython%d.%d.so" % sys.version_info[:2])
except Exception:
    pass


# =====================================================================
# Heavy imports — wrapped so a failure shows on screen instead of
# killing the process before Kivy starts.
# =====================================================================
_IMPORT_ERROR = None
_IMPORT_OK = False

try:
    import requests
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    from eth_abi import encode as abi_encode
    from eth_utils import keccak
    _IMPORT_OK = True
    _alog("Heavy imports OK (requests, eth_account, eth_abi, eth_utils)")
except Exception:
    _IMPORT_ERROR = traceback.format_exc()
    _alog_err("HEAVY IMPORT FAILED:\n" + _IMPORT_ERROR)


# =====================================================================
# Constants (only computed if imports succeeded; otherwise placeholders)
# =====================================================================
CONTRACT_BYTECODE = "0x6080604052600436106101fb575f3560e01c8063739e2e091161010c578063a457c2d71161009f578063d113b95c1161006e578063d113b95c146107f5578063d7bf81a31461080b578063dd62ed3e14610835578063fed3fdcb14610871578063fed976f71461089b57610232565b8063a457c2d71461073d578063a6cd4c6914610779578063a9059cbb146107a3578063cfc98a24146107df57610232565b806395d89b41116100db57806395d89b41146106a35780639ab475b5146106cd5780639d2cc436146106e95780639fbaf3de1461071357610232565b8063739e2e09146105d757806377b5255614610601578063862e2fc81461063d57806392a49e211461066757610232565b8063313ce5671161018f5780634b6604191161015e5780634b660419146104c857806359441eae146104f257806364e4d3a41461052e5780636fab912a1461055e57806370a082311461059b57610232565b8063313ce567146103fc57806339509351146104265780633c3a44da1461046257806342fcfe391461048c57610232565b80631e7269c5116101cb5780631e7269c51461033057806323b872dd1461036c57806324031a05146103a85780632d2c5565146103d257610232565b80625dfcbf1461026457806306fdde03146102a0578063095ea7b3146102ca57806318160ddd1461030657610232565b36610232576040517f60f8f32100000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b6040517f60f8f32100000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b34801561026f575f5ffd5b5061028a60048036038101906102859190612302565b6108c5565b6040516102979190612345565b60405180910390f35b3480156102ab575f5ffd5b506102b46108da565b6040516102c191906123ce565b60405180910390f35b3480156102d5575f5ffd5b506102f060048036038101906102eb9190612418565b610913565b6040516102fd9190612470565b60405180910390f35b348015610311575f5ffd5b5061031a610a00565b6040516103279190612345565b60405180910390f35b34801561033b575f5ffd5b5061035660048036038101906103519190612302565b610a06565b6040516103639190612345565b60405180910390f35b348015610377575f5ffd5b50610392600480360381019061038d9190612489565b610a1b565b60405161039f9190612470565b60405180910390f35b3480156103b3575f5ffd5b506103bc610d75565b6040516103c991906124e8565b60405180910390f35b3480156103dd575f5ffd5b506103e6610d8d565b6040516103f391906124e8565b60405180910390f35b348015610407575f5ffd5b50610410610db1565b60405161041d919061251c565b60405180910390f35b348015610431575f5ffd5b5061044c60048036038101906104479190612418565b610db5565b6040516104599190612470565b60405180910390f35b34801561046d575f5ffd5b50610476610f2a565b6040516104839190612345565b60405180910390f35b348015610497575f5ffd5b506104b260048036038101906104ad9190612535565b610f30565b6040516104bf91906123ce565b60405180910390f35b3480156104d3575f5ffd5b506104dc610f98565b6040516104e991906125bb565b60405180910390f35b3480156104fd575f5ffd5b5061051860048036038101906105139190612302565b610fb0565b6040516105259190612345565b60405180910390f35b61054860048036038101906105439190612668565b6110cb565b6040516105559190612345565b60405180910390f35b348015610569575f5ffd5b50610584600480360381019061057f91906126c5565b61116f565b604051610592929190612724565b60405180910390f35b3480156105a6575f5ffd5b506105c160048036038101906105bc9190612302565b611219565b6040516105ce9190612345565b60405180910390f35b3480156105e2575f5ffd5b506105eb61122e565b6040516105f89190612345565b60405180910390f35b34801561060c575f5ffd5b5061062760048036038101906106229190612752565b611233565b6040516106349190612470565b60405180910390f35b348015610648575f5ffd5b50610651611250565b60405161065e9190612345565b60405180910390f35b348015610672575f5ffd5b5061068d600480360381019061068891906126c5565b611256565b60405161069a919061277d565b60405180910390f35b3480156106ae575f5ffd5b506106b76112fa565b6040516106c491906123ce565b60405180910390f35b6106e760048036038101906106e29190612796565b611333565b005b3480156106f4575f5ffd5b506106fd6113ca565b60405161070a9190612345565b60405180910390f35b34801561071e575f5ffd5b506107276113cf565b6040516107349190612345565b60405180910390f35b348015610748575f5ffd5b50610763600480360381019061075e9190612418565b6113d5565b6040516107709190612470565b60405180910390f35b348015610784575f5ffd5b5061078d611589565b60405161079a91906123ce565b60405180910390f35b3480156107ae575f5ffd5b506107c960048036038101906107c49190612418565b6115c2565b6040516107d69190612470565b60405180910390f35b3480156107ea575f5ffd5b506107f36117b4565b005b348015610800575f5ffd5b50610809611920565b005b348015610816575f5ffd5b5061081f611a96565b60405161082c9190612345565b60405180910390f35b348015610840575f5ffd5b5061085b60048036038101906108569190612807565b611aba565b6040516108689190612345565b60405180910390f35b34801561087c575f5ffd5b50610885611ada565b6040516108929190612345565b60405180910390f35b3480156108a6575f5ffd5b506108af611ae1565b6040516108bc9190612345565b60405180910390f35b6007602052805f5260405f205f915090505481565b6040518060400160405280600d81526020017f534f5336393036392063534f530000000000000000000000000000000000000081525081565b5f8160085f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f8573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f20819055508273ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925846040516109ee9190612345565b60405180910390a36001905092915050565b60045481565b6006602052805f5260405f205f915090505481565b5f5f73ffffffffffffffffffffffffffffffffffffffff168373ffffffffffffffffffffffffffffffffffffffff1603610a81576040517fd92e233d00000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b8160055f8673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f20541015610af8576040517ff4d678b800000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b5f60085f8673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f2054905082811015610bae576040517f13be252b00000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8114610c5e578281610be19190612872565b60085f8773ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f20819055505b8260055f8773ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f828254610caa9190612872565b925050819055508260055f8673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f828254610cfd91906128a5565b925050819055508373ffffffffffffffffffffffffffffffffffffffff168573ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef85604051610d619190612345565b60405180910390a360019150509392505050565b731c10e6574ee696f54b21a611a21313e4714628ad81565b7f0000000000000000000000001c10e6574ee696f54b21a611a21313e4714628ad81565b5f81565b5f5f8260085f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f8673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f2054610e3b91906128a5565b90508060085f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f8673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f20819055508373ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b92583604051610f179190612345565b60405180910390a3600191505092915050565b60015481565b60606040518060400160405280600a81526020017f63534f533a4d494e543a00000000000000000000000000000000000000000000815250610f7183611af6565b604051602001610f82929190612912565b6040516020818303038152906040529050919050565b737373dbc24dcd785896e8ac3d5372c6ced9b75a8a81565b5f5f737373dbc24dcd785896e8ac3d5372c6ced9b75a8a73ffffffffffffffffffffffffffffffffffffffff166378be73fc846040518263ffffffff1660e01b8152600401610fff91906124e8565b602060405180830381865afa15801561101a573d5f5f3e3d5ffd5b505050506040513d601f19601f8201168201806040525081019061103e9190612968565b9050600a8113611051575f9150506110c6565b5f600a8261105f9190612872565b90505f60065f8673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205490508181106110b4575f93505050506110c6565b80826110c09190612872565b93505050505b919050565b5f6002600a5403611108576040517fab143c0600000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b6002600a8190555061111933610fb0565b90505f8103611154576040517f017f629a00000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b61116081858585611c4f565b6001600a819055509392505050565b60605f61117b84610f30565b9150737373dbc24dcd785896e8ac3d5372c6ced9b75a8a73ffffffffffffffffffffffffffffffffffffffff1663cd6f7d9b868786866040518563ffffffff1660e01b81526004016111d09493929190612993565b602060405180830381865afa1580156111eb573d5f5f3e3d5ffd5b505050506040513d601f19601f8201168201806040525081019061120f91906129f1565b9050935093915050565b6005602052805f5260405f205f915090505481565b5f5481565b6009602052805f5260405f205f915054906101000a900460ff1681565b60025481565b5f737373dbc24dcd785896e8ac3d5372c6ced9b75a8a73ffffffffffffffffffffffffffffffffffffffff1663cd6f7d9b85868561129388610f30565b6040518563ffffffff1660e01b81526004016112b29493929190612993565b602060405180830381865afa1580156112cd573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906112f191906129f1565b90509392505050565b6040518060400160405280600481526020017f63534f530000000000000000000000000000000000000000000000000000000081525081565b6002600a540361136f576040517fab143c0600000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b6002600a819055505f84036113b0576040517f017f629a00000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b6113bc84848484611c4f565b6001600a8190555050505050565b600a81565b60035481565b5f5f60085f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f8573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205490508281101561148c576040517f13be252b00000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b5f83826114999190612872565b90508060085f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f8773ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f20819055508473ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925836040516115759190612345565b60405180910390a360019250505092915050565b6040518060400160405280600a81526020017f63534f533a4d494e543a0000000000000000000000000000000000000000000081525081565b5f5f73ffffffffffffffffffffffffffffffffffffffff168373ffffffffffffffffffffffffffffffffffffffff1603611628576040517fd92e233d00000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b8160055f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f2054101561169f576040517ff4d678b800000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b8160055f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f8282546116eb9190612872565b925050819055508160055f8573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f82825461173e91906128a5565b925050819055508273ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef846040516117a29190612345565b60405180910390a36001905092915050565b6002600a54036117f0576040517fab143c0600000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b6002600a819055505f60015490505f810361180b5750611916565b5f6001819055505f731c10e6574ee696f54b21a611a21313e4714628ad73ffffffffffffffffffffffffffffffffffffffff168260405161184b90612a49565b5f6040518083038185875af1925050503d805f8114611885576040519150601f19603f3d011682016040523d82523d5f602084013e61188a565b606091505b50509050806118c5576040517fd41997a500000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b3373ffffffffffffffffffffffffffffffffffffffff167fcb2e84b08a7a96bf62a4416748a26a53aeb0f87dd26e2ef25bc46df567411b348360405161190b9190612345565b60405180910390a250505b6001600a81905550565b6002600a540361195c576040517fab143c0600000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b6002600a819055505f5f5490505f81036119765750611a8c565b5f5f819055505f7f0000000000000000000000001c10e6574ee696f54b21a611a21313e4714628ad73ffffffffffffffffffffffffffffffffffffffff16826040516119c190612a49565b5f6040518083038185875af1925050503d805f81146119fb576040519150601f19603f3d011682016040523d82523d5f602084013e611a00565b606091505b5050905080611a3b576040517f0e373cf800000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b3373ffffffffffffffffffffffffffffffffffffffff167fb6c81b526e1bd55a3845d8caa6fe0c1ce87b3c9e534eec43f43b3c1849d4e2e883604051611a819190612345565b60405180910390a250505b6001600a81905550565b7f000000000000000000000000000000000000000000000000000000000000000081565b6008602052815f5260405f20602052805f5260405f205f91509150505481565b6201388081565b5f3a62013880611af19190612a5d565b905090565b60605f8203611b3c576040518060400160405280600181526020017f30000000000000000000000000000000000000000000000000000000000000008152509050611c4a565b5f8290505f5b5f8214611b6b578080611b5490612a9e565b915050600a82611b649190612b12565b9150611b42565b5f8167ffffffffffffffff811115611b8657611b85612b42565b5b6040519080825280601f01601f191660200182016040528015611bb85781602001600182028036833780820191505090505b5090505b5f8514611c4357600182611bd09190612872565b9150600a85611bdf9190612b6f565b6030611beb91906128a5565b60f81b818381518110611c0157611c00612b9f565b5b60200101907effffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff191690815f1a905350600a85611c3c9190612b12565b9450611bbc565b8093505050505b919050565b5f611c5933610fb0565b905080851115611c95576040517f017f629a00000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b5f7f000000000000000000000000000000000000000000000000000000000000000086611cc29190612a5d565b905080341015611cfe576040517f9a0833b600000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b5f8134611d0b9190612872565b90505f611d1788610f30565b90505f737373dbc24dcd785896e8ac3d5372c6ced9b75a8a73ffffffffffffffffffffffffffffffffffffffff1663cd6f7d9b33338b866040518563ffffffff1660e01b8152600401611d6d9493929190612993565b602060405180830381865afa158015611d88573d5f5f3e3d5ffd5b505050506040513d601f19601f82011682018060405250810190611dac91906129f1565b905060095f8281526020019081526020015f205f9054906101000a900460ff1615611e03576040517f8ec9ddad00000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b600160095f8381526020019081526020015f205f6101000a81548160ff0219169083151502179055508860065f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f828254611e7891906128a5565b925050819055508360075f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f828254611ecb91906128a5565b925050819055508360035f828254611ee391906128a5565b92505081905550835f5f828254611efa91906128a5565b925050819055505f831115611f3a578260015f828254611f1a91906128a5565b925050819055508260025f828254611f3291906128a5565b925050819055505b737373dbc24dcd785896e8ac3d5372c6ced9b75a8a73ffffffffffffffffffffffffffffffffffffffff16631c7c27c833338b8b8b886040518763ffffffff1660e01b8152600401611f9196959493929190612c16565b5f604051808303815f87803b158015611fa8575f5ffd5b505af1158015611fba573d5f5f3e3d5ffd5b50505050737373dbc24dcd785896e8ac3d5372c6ced9b75a8a73ffffffffffffffffffffffffffffffffffffffff1663f8e5bb59826040518263ffffffff1660e01b815260040161200b919061277d565b602060405180830381865afa158015612026573d5f5f3e3d5ffd5b505050506040513d601f19601f8201168201806040525081019061204a9190612ca1565b612080576040517f63be7c4900000000000000000000000000000000000000000000000000000000815260040160405180910390fd5b61208a338a6121cc565b3373ffffffffffffffffffffffffffffffffffffffff167f5a3358a3d27a5373c0df2604662088d37894d56b7cfd27f315770440f4e0d9198a8660065f3373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205460405161211193929190612ccc565b60405180910390a2803373ffffffffffffffffffffffffffffffffffffffff167fd01f93a87f0f41307d528a0bce47898b357d3fcc990e88d8a5e4967366044a248b85604051612162929190612d01565b60405180910390a35f8311156121c1573373ffffffffffffffffffffffffffffffffffffffff167f264f630d9efa0d07053a31163641d9fcc0adafc9d9e76f1c37c2ce3a558d2c52846040516121b89190612345565b60405180910390a25b505050505050505050565b8060045f8282546121dd91906128a5565b925050819055508060055f8473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020015f205f82825461223091906128a5565b925050819055508173ffffffffffffffffffffffffffffffffffffffff165f73ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef836040516122949190612345565b60405180910390a35050565b5f5ffd5b5f5ffd5b5f73ffffffffffffffffffffffffffffffffffffffff82169050919050565b5f6122d1826122a8565b9050919050565b6122e1816122c7565b81146122eb575f5ffd5b50565b5f813590506122fc816122d8565b92915050565b5f60208284031215612317576123166122a0565b5b5f612324848285016122ee565b91505092915050565b5f819050919050565b61233f8161232d565b82525050565b5f6020820190506123585f830184612336565b92915050565b5f81519050919050565b5f82825260208201905092915050565b8281835e5f83830152505050565b5f601f19601f8301169050919050565b5f6123a08261235e565b6123aa8185612368565b93506123ba818560208601612378565b6123c381612386565b840191505092915050565b5f6020820190508181035f8301526123e68184612396565b905092915050565b6123f78161232d565b8114612401575f5ffd5b50565b5f81359050612412816123ee565b92915050565b5f5f6040838503121561242e5761242d6122a0565b5b5f61243b858286016122ee565b925050602061244c85828601612404565b9150509250929050565b5f8115159050919050565b61246a81612456565b82525050565b5f6020820190506124835f830184612461565b92915050565b5f5f5f606084860312156124a05761249f6122a0565b5b5f6124ad868287016122ee565b93505060206124be868287016122ee565b92505060406124cf86828701612404565b9150509250925092565b6124e2816122c7565b82525050565b5f6020820190506124fb5f8301846124d9565b92915050565b5f60ff82169050919050565b61251681612501565b82525050565b5f60208201905061252f5f83018461250d565b92915050565b5f6020828403121561254a576125496122a0565b5b5f61255784828501612404565b91505092915050565b5f819050919050565b5f61258361257e612579846122a8565b612560565b6122a8565b9050919050565b5f61259482612569565b9050919050565b5f6125a58261258a565b9050919050565b6125b58161259b565b82525050565b5f6020820190506125ce5f8301846125ac565b92915050565b5f819050919050565b6125e6816125d4565b81146125f0575f5ffd5b50565b5f81359050612601816125dd565b92915050565b5f5ffd5b5f5ffd5b5f5ffd5b5f5f83601f84011261262857612627612607565b5b8235905067ffffffffffffffff8111156126455761264461260b565b5b6020830191508360018202830111156126615761266061260f565b5b9250929050565b5f5f5f6040848603121561267f5761267e6122a0565b5b5f61268c868287016125f3565b935050602084013567ffffffffffffffff8111156126ad576126ac6122a4565b5b6126b986828701612613565b92509250509250925092565b5f5f5f606084860312156126dc576126db6122a0565b5b5f6126e9868287016122ee565b93505060206126fa86828701612404565b925050604061270b868287016125f3565b9150509250925092565b61271e816125d4565b82525050565b5f6040820190508181035f83015261273c8185612396565b905061274b6020830184612715565b9392505050565b5f60208284031215612767576127666122a0565b5b5f612774848285016125f3565b91505092915050565b5f6020820190506127905f830184612715565b92915050565b5f5f5f5f606085870312156127ae576127ad6122a0565b5b5f6127bb87828801612404565b94505060206127cc878288016125f3565b935050604085013567ffffffffffffffff8111156127ed576127ec6122a4565b5b6127f987828801612613565b925092505092959194509250565b5f5f6040838503121561281d5761281c6122a0565b5b5f61282a858286016122ee565b925050602061283b858286016122ee565b9150509250929050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52601160045260245ffd5b5f61287c8261232d565b91506128878361232d565b925082820390508181111561289f5761289e612845565b5b92915050565b5f6128af8261232d565b91506128ba8361232d565b92508282019050808211156128d2576128d1612845565b5b92915050565b5f81905092915050565b5f6128ec8261235e565b6128f681856128d8565b9350612906818560208601612378565b80840191505092915050565b5f61291d82856128e2565b915061292982846128e2565b91508190509392505050565b5f819050919050565b61294781612935565b8114612951575f5ffd5b50565b5f815190506129628161293e565b92915050565b5f6020828403121561297d5761297c6122a0565b5b5f61298a84828501612954565b91505092915050565b5f6080820190506129a65f8301876124d9565b6129b360208301866124d9565b6129c06040830185612715565b81810360608301526129d28184612396565b905095945050505050565b5f815190506129eb816125dd565b92915050565b5f60208284031215612a0657612a056122a0565b5b5f612a13848285016129dd565b91505092915050565b5f81905092915050565b50565b5f612a345f83612a1c565b9150612a3f82612a26565b5f82019050919050565b5f612a5382612a29565b9150819050919050565b5f612a678261232d565b9150612a728361232d565b9250828202612a808161232d565b91508282048414831517612a9757612a96612845565b5b5092915050565b5f612aa88261232d565b91507fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8203612ada57612ad9612845565b5b600182019050919050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52601260045260245ffd5b5f612b1c8261232d565b9150612b278361232d565b925082612b3757612b36612ae5565b5b828204905092915050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52604160045260245ffd5b5f612b798261232d565b9150612b848361232d565b925082612b9457612b93612ae5565b5b828206905092915050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52603260045260245ffd5b5f82825260208201905092915050565b828183375f83830152505050565b5f612bf58385612bcc565b9350612c02838584612bdc565b612c0b83612386565b840190509392505050565b5f60a082019050612c295f8301896124d9565b612c3660208301886124d9565b612c436040830187612715565b8181036060830152612c56818587612bea565b90508181036080830152612c6a8184612396565b9050979650505050505050565b612c8081612456565b8114612c8a575f5ffd5b50565b5f81519050612c9b81612c77565b92915050565b5f60208284031215612cb657612cb56122a0565b5b5f612cc384828501612c8d565b91505092915050565b5f606082019050612cdf5f830186612336565b612cec6020830185612336565b612cf96040830184612336565b949350505050565b5f604082019050612d145f830185612336565b8181036020830152612d268184612396565b9050939250505056fea2646970667358221220ffb5a3ed0c96dacaf2545c241af67b369012ebd7333f6dc917042bcaf5f2257464736f6c63430008240033"

LEDGER_ADDR = "0x7373DBC24Dcd785896E8Ac3d5372c6ced9B75a8A"
DOMAIN_NAME = "69069"
DOMAIN_VERSION = "1"
C_SOS_RESERVE = 10
CONSTRUCTOR_TYPES = ["uint256", "address"]

if _IMPORT_OK:
    EIP712_DOMAIN_TYPEHASH = keccak(text=(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    ))
    RECORD_TYPEHASH = keccak(text=(
        "Record(address signer,address intendedTo,bytes32 payloadHash,bytes32 metadataHash)"
    ))
else:
    EIP712_DOMAIN_TYPEHASH = b""
    RECORD_TYPEHASH = b""

EXPLORER_HOSTS = {
    1: "etherscan.io", 5: "goerli.etherscan.io",
    11155111: "sepolia.etherscan.io", 17000: "holesky.etherscan.io",
    137: "polygonscan.com", 80001: "mumbai.polygonscan.com",
    10: "optimistic.etherscan.io", 42161: "arbiscan.io", 8453: "basescan.org",
}


# =====================================================================
# Platform / explorer
# =====================================================================
def open_url(url: str):
    try:
        from jnius import autoclass  # type: ignore
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        PythonActivity.mActivity.startActivity(
            Intent(Intent.ACTION_VIEW, Uri.parse(url))
        )
    except Exception:
        try:
            webbrowser.open(url)
        except Exception:
            pass


def explorer_url(chain_id, address, code_tab=False):
    host = EXPLORER_HOSTS.get(int(chain_id), "etherscan.io")
    return f"https://{host}/address/{address}{'#code' if code_tab else ''}"


def explorer_tx_url(chain_id, tx_hash) -> str:
    host = EXPLORER_HOSTS.get(int(chain_id), "etherscan.io")
    h = tx_hash if str(tx_hash).startswith("0x") else "0x" + str(tx_hash)
    return f"https://{host}/tx/{h}"


def signed_raw_hex(signed) -> str:
    """eth-account 0.10 uses rawTransaction; newer uses raw_transaction."""
    raw = getattr(signed, "raw_transaction", None)
    if raw is None:
        raw = getattr(signed, "rawTransaction", None)
    if raw is None:
        raise AttributeError("SignedTransaction has neither raw_transaction nor rawTransaction")
    if isinstance(raw, (bytes, bytearray)):
        return "0x" + bytes(raw).hex()
    s = raw.hex() if hasattr(raw, "hex") else str(raw)
    return s if s.startswith("0x") else "0x" + s


# =====================================================================
# JSON-RPC
# =====================================================================
def rpc(url, method, params):
    r = requests.post(
        url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["result"]


def selector(sig: str) -> str:
    return "0x" + keccak(text=sig)[:4].hex()


def eth_call(rpc_url, to, data):
    return rpc(rpc_url, "eth_call", [{"to": to, "data": data}, "latest"])


def decode_uint(h):
    return 0 if not h or h == "0x" else int(h, 16)


def decode_int(h):
    if not h or h == "0x":
        return 0
    n = int(h, 16)
    if n >= 2**255:
        n -= 2**256
    return n


def decode_bool(h):
    return int(h, 16) != 0 if h and h != "0x" else False


def decode_bytes32(h):
    return h if h.startswith("0x") else "0x" + h


def decode_string(h):
    b = bytes.fromhex(h[2:] if h.startswith("0x") else h)
    off = int.from_bytes(b[0:32], "big")
    ln = int.from_bytes(b[off:off + 32], "big")
    return b[off + 32:off + 32 + ln].decode("utf-8", errors="replace")


def _encode_address(addr: str) -> str:
    """Manual ABI word for address — avoids eth_abi isinstance issues on Android."""
    a = addr.lower().replace("0x", "")
    if len(a) != 40:
        raise ValueError(f"bad address: {addr}")
    return a.rjust(64, "0")


def _encode_bytes32(b32: str) -> str:
    h = b32.lower().replace("0x", "")
    if len(h) != 64:
        raise ValueError(f"bad bytes32: {b32}")
    return h


def _pad32(b: bytes) -> bytes:
    if len(b) > 32:
        raise ValueError("word > 32 bytes")
    return b.rjust(32, b"\x00")


def _enc_uint256(n: int) -> bytes:
    if n < 0:
        n = n % (2 ** 256)
    return int(n).to_bytes(32, "big")


def _enc_address(addr: str) -> bytes:
    a = addr.lower().replace("0x", "")
    if len(a) != 40:
        raise ValueError(f"bad address: {addr}")
    return bytes.fromhex(a.rjust(64, "0"))


def _enc_bytes32(val) -> bytes:
    if isinstance(val, (bytes, bytearray)):
        h = bytes(val)
        if len(h) != 32:
            raise ValueError("bytes32 must be 32 bytes")
        return h
    s = str(val).lower().replace("0x", "")
    if len(s) != 64:
        raise ValueError(f"bad bytes32: {val}")
    return bytes.fromhex(s)


def _enc_bytes_dynamic(data: bytes) -> bytes:
    """ABI dynamic bytes: length + data + padding."""
    ln = _enc_uint256(len(data))
    pad = (32 - (len(data) % 32)) % 32
    return ln + data + (b"\x00" * pad)


def _enc_string(s: str) -> bytes:
    return _enc_bytes_dynamic(s.encode("utf-8"))


def _keccak(data: bytes) -> bytes:
    return keccak(data)



def read_uint(rpc_url, contract, sig, address_arg=None):
    data = selector(sig)
    if address_arg:
        data += _encode_address(address_arg)
    return decode_uint(eth_call(rpc_url, contract, data))


def read_int(rpc_url, contract, sig, address_arg=None):
    data = selector(sig)
    if address_arg:
        data += _encode_address(address_arg)
    return decode_int(eth_call(rpc_url, contract, data))


def read_bool(rpc_url, contract, sig, bytes32_arg):
    data = selector(sig) + _encode_bytes32(bytes32_arg)
    return decode_bool(eth_call(rpc_url, contract, data))


def read_string(rpc_url, contract, sig):
    return decode_string(eth_call(rpc_url, contract, selector(sig)))


def wait_for_receipt(rpc_url, tx_hash, timeout_s=360):
    for _ in range(timeout_s // 2):
        r = rpc(rpc_url, "eth_getTransactionReceipt", [tx_hash])
        if r:
            if r.get("status") != "0x1":
                raise RuntimeError(f"Tx reverted: {tx_hash}")
            return r
        time.sleep(2)
    raise TimeoutError(f"No receipt after {timeout_s}s. Tx: {tx_hash}")


# =====================================================================
# EIP-712 hashing
# =====================================================================
def compute_metadata(amount: int) -> str:
    return f"cSOS:MINT:{amount}"


def compute_struct_hash(signer, intended_to, payload_hash, metadata):
    """EIP-712 Record struct hash — pure, no eth_abi."""
    ph = _enc_bytes32(payload_hash)
    metadata_hash = keccak(text=metadata)
    encoded = (
        _enc_bytes32(RECORD_TYPEHASH)
        + _enc_address(signer)
        + _enc_address(intended_to)
        + ph
        + _enc_bytes32(metadata_hash)
    )
    return "0x" + keccak(encoded).hex()


def compute_domain_separator(chain_id: int, verifying_contract: str) -> str:
    encoded = (
        _enc_bytes32(EIP712_DOMAIN_TYPEHASH)
        + _enc_bytes32(keccak(text=DOMAIN_NAME))
        + _enc_bytes32(keccak(text=DOMAIN_VERSION))
        + _enc_uint256(int(chain_id))
        + _enc_address(verifying_contract)
    )
    return "0x" + keccak(encoded).hex()


def sign_record(private_key, chain_id, ledger_addr,
                signer, intended_to, payload_hash, metadata) -> str:
    """Sign EIP-712 Record without eth_abi / encode_typed_data (Android-safe)."""
    if not payload_hash.startswith("0x"):
        payload_hash = "0x" + payload_hash
    struct_hash = bytes.fromhex(
        compute_struct_hash(signer, intended_to, payload_hash, metadata)[2:]
    )
    domain_sep = bytes.fromhex(
        compute_domain_separator(int(chain_id), ledger_addr)[2:]
    )
    # digest = keccak256("\x19\x01" || domainSeparator || structHash)
    digest = keccak(b"\x19\x01" + domain_sep + struct_hash)
    acct = Account.from_key(private_key)
    # eth-account 0.10: signHash on LocalAccount (msg hash, no extra prefix)
    if hasattr(acct, "unsafe_sign_hash"):
        signed = acct.unsafe_sign_hash(digest)
    else:
        signed = acct.signHash(digest)
    sig = signed.signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig


# =====================================================================
# Chain helpers
# =====================================================================
def check_ledger_present(rpc_url):
    code = rpc(rpc_url, "eth_getCode", [LEDGER_ADDR, "latest"])
    if not code or code == "0x":
        raise RuntimeError(
            f"LEDGER {LEDGER_ADDR} has NO code on this chain.\n"
            f"Minting would revert on every call. Aborting."
        )
    return len(code) // 2 - 1


def verify_struct_hash(rpc_url, user, payload, metadata) -> str:
    # ABI: address, address, bytes32, string(dynamic)
    # head: addr, addr, bytes32, offset(to string = 128)
    head = (
        _enc_address(user)
        + _enc_address(user)
        + _enc_bytes32(payload)
        + _enc_uint256(128)
    )
    tail = _enc_string(metadata)
    call_data = selector("recordStructHash(address,address,bytes32,string)") + (head + tail).hex()
    return decode_bytes32(eth_call(rpc_url, LEDGER_ADDR, call_data))


def fetch_mint_status(rpc_url, csos_addr, user):
    """Returns (effective, minted, mintable). Raises on RPC/decode errors."""
    eff = read_int(rpc_url, LEDGER_ADDR, "effectiveOf(address)", user)
    minted = read_uint(rpc_url, csos_addr, "minted(address)", user)
    mintable = read_uint(rpc_url, csos_addr, "mintable(address)", user)
    return int(eff), int(minted), int(mintable)


# =====================================================================
# Deploy + mint tx
# =====================================================================
def deploy_contract(rpc_url, chain_id, private_key, mint_fee, treasury):
    acct = Account.from_key(private_key)
    bytecode = CONTRACT_BYTECODE
    if not bytecode.startswith("0x"):
        bytecode = "0x" + bytecode
    if len(bytecode) < 100:
        raise ValueError("CONTRACT_BYTECODE is empty — paste it at the top of main.py")

    data = bytecode + abi_encode(CONSTRUCTOR_TYPES, [int(mint_fee), treasury]).hex()
    nonce = int(rpc(rpc_url, "eth_getTransactionCount", [acct.address, "pending"]), 16)
    gas_price = int(rpc(rpc_url, "eth_gasPrice", []), 16)
    est = rpc(rpc_url, "eth_estimateGas",
              [{"from": acct.address, "data": data, "value": "0x0"}])
    tx = {
        "nonce": nonce, "gasPrice": gas_price,
        "gas": int(int(est, 16) * 1.25),
        "to": None, "value": 0, "data": data, "chainId": int(chain_id),
    }
    signed = acct.sign_transaction(tx)
    raw = signed_raw_hex(signed)
    tx_hash = rpc(rpc_url, "eth_sendRawTransaction", [raw])
    receipt = wait_for_receipt(rpc_url, tx_hash)
    return receipt["contractAddress"], tx_hash


def submit_mint(rpc_url, chain_id, private_key, csos_addr, amount,
                payload_hash, signature, mint_fee, use_max=False):
    acct = Account.from_key(private_key)
    nonce = int(rpc(rpc_url, "eth_getTransactionCount", [acct.address, "pending"]), 16)
    gas_price = int(rpc(rpc_url, "eth_gasPrice", []), 16)

    sig_bytes = bytes.fromhex(signature[2:] if signature.startswith("0x") else signature)
    ph_bytes = _enc_bytes32(payload_hash)

    if use_max:
        # mintMax(bytes32,bytes) — head: bytes32, offset(64); tail: dynamic bytes
        sig_name = "mintMax(bytes32,bytes)"
        head = ph_bytes + _enc_uint256(64)
        tail = _enc_bytes_dynamic(sig_bytes)
        encoded = head + tail
    else:
        # mint(uint256,bytes32,bytes) — head: uint, bytes32, offset(96); tail: bytes
        sig_name = "mint(uint256,bytes32,bytes)"
        head = _enc_uint256(int(amount)) + ph_bytes + _enc_uint256(96)
        tail = _enc_bytes_dynamic(sig_bytes)
        encoded = head + tail

    data = selector(sig_name) + encoded.hex()
    value = int(amount) * int(mint_fee)
    est = rpc(rpc_url, "eth_estimateGas", [{
        "from": acct.address, "to": csos_addr,
        "value": hex(value), "data": data}])
    gas_limit = int(int(est, 16) * 1.25)
    tx = {
        "nonce": nonce, "gasPrice": gas_price, "gas": gas_limit,
        "to": csos_addr, "value": value, "data": data, "chainId": int(chain_id),
    }
    signed = acct.sign_transaction(tx)
    raw = signed_raw_hex(signed)
    tx_hash = rpc(rpc_url, "eth_sendRawTransaction", [raw])
    wait_for_receipt(rpc_url, tx_hash)
    return tx_hash


# =====================================================================
# UI helpers
# =====================================================================
BTN_H   = dp(56)     # touch-friendly button height
INPUT_H = dp(56)     # input field height
PAD_X   = dp(14)     # horizontal text padding inside inputs


def make_button(label, bg=None, height=None):
    """Large touch target — easy to hit with a finger."""
    return Button(
        text=label,
        size_hint_y=None,
        height=height or BTN_H,
        background_normal="",
        background_down="",
        background_color=bg if bg is not None else GREEN,
        color=TEXT,
        bold=True,
        font_size="17sp",
    )


def make_input(hint, password=False, numeric=False, text=""):
    """Single-line input with the text vertically CENTERED.

    Kivy's TextInput draws text from the top padding down, so a fixed
    padding leaves the text hugging the bottom (or clipped) on high-DPI
    phones. We compute the vertical padding from the real line height and
    re-apply it whenever the size or font changes.
    NOTE: do NOT pass bold= (TextInput has no bold property crash).
    """
    ti = TextInput(
        hint_text=hint,
        password=password,
        multiline=False,
        input_filter="int" if numeric else None,
        size_hint_y=None,
        height=INPUT_H,
        text=text,
        background_normal="",
        background_active="",
        background_color=INPUT_BG,
        foreground_color=TEXT,
        cursor_color=BLUE_SOFT,
        cursor_width=dp(2),
        font_size="17sp",
        write_tab=False,
        hint_text_color=TEXT_MUTED,
        halign="left",
        padding=[PAD_X, dp(12), PAD_X, dp(12)],
    )
    if numeric:
        ti.input_type = "number"

    def _center(*_):
        pad_y = max(0.0, (ti.height - ti.line_height) / 2.0)
        ti.padding = [PAD_X, pad_y, PAD_X, pad_y]

    ti.bind(height=_center, line_height=_center, font_size=_center)
    Clock.schedule_once(_center, 0)
    return ti


def make_caption(text):
    """Small label shown above an input (hints vanish once you type)."""
    lbl = Label(
        text=text, size_hint_y=None, height=dp(22),
        color=TEXT_SEC, font_size="13sp", halign="left", valign="bottom",
    )
    lbl.bind(size=lambda *_: setattr(lbl, "text_size", lbl.size))
    return lbl


def make_log_area(initial=""):
    """Log label that lives INSIDE the tab's scrolling form (no nested scroll)."""
    lbl = Label(text=initial, size_hint_y=None, halign="left", valign="top",
                color=TEXT_SEC, font_size="14sp", padding=(dp(10), dp(10)))
    def _resize(*_):
        lbl.text_size = (lbl.width - dp(20), None)
        lbl.height = max(dp(180), lbl.texture_size[1] + dp(20))
    lbl.bind(width=_resize, texture_size=_resize)
    with lbl.canvas.before:
        from kivy.graphics import Color, Rectangle
        Color(*CARD_BG)
        rect = Rectangle(pos=lbl.pos, size=lbl.size)
    lbl.bind(pos=lambda *_: setattr(rect, "pos", lbl.pos),
             size=lambda *_: setattr(rect, "size", lbl.size))
    return lbl, lbl


def _scroll_to_bottom(label):
    p = label.parent
    while p is not None and not isinstance(p, ScrollView):
        p = p.parent
    if p is not None:
        p.scroll_y = 0


def log_to(label):
    def _log(msg):
        def _do(*_):
            label.text += msg + "\n"
            Clock.schedule_once(lambda *_: _scroll_to_bottom(label), 0.05)
        Clock.schedule_once(_do)
    return _log


# =====================================================================
# Theme (aligned with SOS69069APP theme.py)
# =====================================================================
BG          = get_color_from_hex("#0a0e0b")
CARD_BG     = get_color_from_hex("#141b16")
INPUT_BG    = get_color_from_hex("#232f27")
BORDER      = get_color_from_hex("#2c3830")
TEXT        = get_color_from_hex("#ffffff")
TEXT_SEC    = get_color_from_hex("#bbbbbb")
TEXT_MUTED  = get_color_from_hex("#9ca3af")
GREEN       = get_color_from_hex("#04aa34")
GREEN_BR    = get_color_from_hex("#22c55e")
BLUE        = get_color_from_hex("#0038fe")
BLUE_SOFT   = get_color_from_hex("#5b8bff")
YELLOW      = get_color_from_hex("#facc15")
ORANGE      = get_color_from_hex("#f97316")
DANGER      = get_color_from_hex("#ef4444")
GRAY        = INPUT_BG
WHITE       = TEXT

try:
    Window.clearcolor = BG
    Window.softinput_mode = "below_target"   # keyboard pushes the focused field into view
except Exception:
    pass


def make_header(title_text="SOS 69069 cSOS"):
    """Logo top-left + title only (NO version here — version is splash-only)."""
    from kivy.uix.image import Image
    row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(64),
                    spacing=dp(12), padding=[dp(14), dp(10), dp(10), dp(6)])
    try:
        logo = Image(source="assets/logo.png", size_hint=(None, None),
                     size=(dp(48), dp(48)), allow_stretch=True, keep_ratio=True)
        row.add_widget(logo)
    except Exception:
        row.add_widget(Label(text="SOS", color=GREEN_BR, bold=True, size_hint=(None, None),
                             size=(dp(40), dp(40))))
    lbl = Label(text=title_text, color=TEXT, bold=True, font_size=dp(20),
                halign="left", valign="middle", size_hint_x=1)
    lbl.bind(size=lambda *a: setattr(lbl, "text_size", lbl.size))
    row.add_widget(lbl)
    return row


def make_unique_payload(user: str, amount: int) -> str:
    """Generate a unique payloadHash — pure Python, no eth_abi."""
    import os, time
    rand = os.urandom(32)
    raw = (
        _enc_address(user)
        + _enc_uint256(int(amount))
        + _enc_bytes32(rand)
        + _enc_uint256(int(time.time()))
    )
    return "0x" + keccak(raw).hex()


def status_label(text=""):
    lbl = Label(
        text=text, size_hint_y=None, height=dp(40),
        color=GREEN_BR, bold=True, halign="left", valign="middle",
        font_size="15sp",
    )
    lbl.bind(size=lambda *_: setattr(lbl, "text_size", lbl.size))
    return lbl


class FormTab(ScrollView):
    """Scrollable form: every tab scrolls, so nothing is squeezed off-screen
    on small phones or when the keyboard is open."""
    def __init__(self, **kw):
        super().__init__(do_scroll_x=False, bar_width=dp(3), **kw)
        self.form = BoxLayout(orientation="vertical", size_hint_y=None,
                              padding=[dp(14), dp(8), dp(14), dp(24)],
                              spacing=dp(6))
        self.form.bind(minimum_height=self.form.setter("height"))
        super().add_widget(self.form)

    def field(self, caption, widget):
        self.form.add_widget(make_caption(caption))
        self.form.add_widget(widget)
        return widget

    def gap(self, h=8):
        from kivy.uix.widget import Widget
        self.form.add_widget(Widget(size_hint_y=None, height=dp(h)))


# =====================================================================
# Deploy tab  (kept almost identical, only green accents + logo)
# =====================================================================
class DeployTab(FormTab):
    def __init__(self, **kw):
        super().__init__(**kw)

        
        self.pk       = make_input("Private key (0x...)", password=True)
        self.rpc_url  = make_input("RPC URL (mainnet)",
                                  text="https://ethereum-rpc.publicnode.com")
        self.chain_id = make_input("Chain ID (1=mainnet)", numeric=True,
                                   text="1")
        self.mint_fee = make_input("MINT_FEE in wei (recommend 0)", numeric=True, text="0")
        self.treasury = make_input("TREASURY address (0x...)",
                                   text="0x1C10e6574ee696f54b21A611a21313E4714628ad")
        self.form.clear_widgets()
        self.field("Private key", self.pk)
        self.field("RPC URL", self.rpc_url)
        self.field("Chain ID", self.chain_id)
        self.field("Mint fee (wei)", self.mint_fee)
        self.field("Treasury address", self.treasury)
        self.gap()

        row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=dp(10))
        self.deploy_btn = make_button("Deploy Contract", GREEN)
        self.check_ledger_btn = make_button("Check LEDGER", INPUT_BG)
        self.deploy_btn.bind(on_press=self.on_deploy)
        self.check_ledger_btn.bind(on_press=self.on_check_ledger)
        row.add_widget(self.deploy_btn)
        row.add_widget(self.check_ledger_btn)
        self.form.add_widget(row)

        self.etherscan_btn = make_button("Open on Etherscan (verify source)", BLUE)
        self.etherscan_btn.disabled = True
        self.etherscan_btn.bind(on_press=self._on_etherscan)
        self.form.add_widget(self.etherscan_btn)

        self.mint_tab_btn = make_button("Go to Mint tab (prefilled)", GREEN)
        self.mint_tab_btn.disabled = True
        self.mint_tab_btn.bind(on_press=self._on_goto_mint)
        self.form.add_widget(self.mint_tab_btn)

        sv, self.log = make_log_area("Ready. Test on Sepolia first!\n")
        self.form.add_widget(sv)
        self._log = log_to(self.log)
        self._last_addr = None
        self._last_chain = None

    def _on_etherscan(self, *_):
        if self._last_addr:
            open_url(explorer_url(self._last_chain, self._last_addr, code_tab=True))

    def _on_goto_mint(self, *_):
        app = App.get_running_app()
        if hasattr(app, "mint_tab"):
            app.mint_tab.prefill_from_deploy(
                rpc_url=self.rpc_url.text.strip(),
                chain_id=self.chain_id.text.strip(),
                private_key=self.pk.text.strip(),
                contract=self._last_addr or "",
                mint_fee=self.mint_fee.text.strip() or "0",
            )
            app.switch_to_tab(app.mint_tab)

    def on_check_ledger(self, *_):
        rpc_url = self.rpc_url.text.strip()
        if not rpc_url:
            self._log("[X] Enter RPC URL first.")
            return
        self._log(f"Checking LEDGER at {LEDGER_ADDR} …")
        threading.Thread(target=self._check_worker, args=(rpc_url,), daemon=True).start()

    def _check_worker(self, rpc_url):
        try:
            size = check_ledger_present(rpc_url)
            self._log(f"[OK] LEDGER present ({size} bytes of code)")
            onchain_ds = decode_bytes32(eth_call(
                rpc_url, LEDGER_ADDR, selector("domainSeparator()")))
            chain_id = int(self.chain_id.text.strip() or "1")
            local_ds = compute_domain_separator(chain_id, LEDGER_ADDR)
            self._log(f"   on-chain domainSeparator = {onchain_ds}")
            self._log(f"   local domainSeparator    = {local_ds}")
            if onchain_ds.lower() == local_ds.lower():
                self._log("   [OK] domain separators match")
            else:
                self._log("   [!]  domain separators differ — check chain ID")
        except Exception as e:
            self._log(f"[X] {e}")

    def on_deploy(self, *_):
        pk = self.pk.text.strip()
        rpc_url = self.rpc_url.text.strip()
        chain_id = self.chain_id.text.strip()
        mint_fee = self.mint_fee.text.strip() or "0"
        treasury = self.treasury.text.strip()
        if not all([pk, rpc_url, chain_id, treasury]):
            self._log("[X] Fill in all fields.")
            return
        if chain_id == "1":
            self._log("[!]  MAINNET — make sure you tested on Sepolia first.")

        self.deploy_btn.disabled = True
        self.etherscan_btn.disabled = True
        self.mint_tab_btn.disabled = True
        self._log(f"Deploying to chain {chain_id} …")
        threading.Thread(
            target=self._worker,
            args=(rpc_url, chain_id, pk, mint_fee, treasury),
            daemon=True).start()

    def _worker(self, rpc_url, chain_id, pk, mint_fee, treasury):
        try:
            try:
                check_ledger_present(rpc_url)
                self._log("[OK] LEDGER present on chain")
            except Exception as e:
                self._log(f"[X] Pre-flight failed: {e}")
                return

            addr, h = deploy_contract(rpc_url, chain_id, pk, mint_fee, treasury)
            self._log(f"[OK] Contract deployed: {addr}")
            self._log(f"   Tx: {h}")
            self._log(f"   Tx link: {explorer_tx_url(chain_id, h)}")
            self._log(f"   Contract: {explorer_url(chain_id, addr)}")
            try:
                open_url(explorer_tx_url(chain_id, h))
            except Exception:
                pass
            self._last_addr = addr
            self._last_chain = chain_id

            app = App.get_running_app()
            app.last_deployed = addr
            app.last_chain = chain_id
            app.last_rpc = rpc_url

            try:
                got_t = "0x" + eth_call(rpc_url, addr, selector("TREASURY()"))[-40:]
                got_f = decode_uint(eth_call(rpc_url, addr, selector("MINT_FEE()")))
                self._log(f"   TREASURY = {got_t}")
                self._log(f"   MINT_FEE = {got_f}")
                if got_t.lower() != treasury.lower():
                    self._log("   [!]  TREASURY mismatch!")
                if got_f != int(mint_fee):
                    self._log("   [!]  MINT_FEE mismatch!")
            except Exception as e:
                self._log(f"   (read-back failed: {e})")

            Clock.schedule_once(lambda *_: setattr(self.etherscan_btn, "disabled", False))
            Clock.schedule_once(lambda *_: setattr(self.mint_tab_btn, "disabled", False))
            self._log("Verify on Etherscan, or tap the green button to mint.")
        except Exception as e:
            self._log(f"[X] Deployment failed:\n{e}")
        finally:
            Clock.schedule_once(lambda *_: setattr(self.deploy_btn, "disabled", False))


# =====================================================================
# Mint tab  — simplified, minimal user input
# =====================================================================
class MintTab(FormTab):
    def __init__(self, **kw):
        super().__init__(**kw)

        
        # Connection fields (can be prefilled from Deploy)
        self.rpc_url  = make_input("RPC URL",
                                  text="https://ethereum-rpc.publicnode.com")
        self.chain_id = make_input("Chain ID", numeric=True, text="1")
        self.pk       = make_input("Private key (signer = minter)", password=True)
        self.contract = make_input("cSOS contract address (0x...)",
                                   text="0xce9B507C242Adf722DD1DE2d7aa5Db1BF2259D8F")
        self.form.clear_widgets()
        self.field("RPC URL", self.rpc_url)
        self.field("Chain ID", self.chain_id)
        self.field("Private key (signer = minter)", self.pk)
        self.field("cSOS contract address", self.contract)

        # Live status
        self.gap(4)
        self.status = status_label("Connect & tap Refresh Status")
        self.form.add_widget(self.status)

        # Amount — the only number the user normally cares about
        self.amount = make_input("Leave blank = Mint Max", numeric=True)
        self.field("Amount to mint", self.amount)

        # Optional donation
        self.donation = make_input("Optional donation in wei (0 = none)", numeric=True)
        self.donation.text = "0"
        self.field("Optional donation (wei)", self.donation)

        # Advanced (collapsed by default – payload only shown for power users)
        self.payload = make_input("Leave blank = auto-generate")
        self.field("payloadHash (advanced)", self.payload)
        self.gap()

        # Buttons
        row1 = BoxLayout(size_hint_y=None, height=BTN_H, spacing=dp(10))
        b_refresh = make_button("Refresh Status", INPUT_BG)
        b_refresh.bind(on_press=lambda *_: self._start("status"))
        row1.add_widget(b_refresh)
        self.form.add_widget(row1)

        row2 = BoxLayout(size_hint_y=None, height=BTN_H, spacing=dp(10))
        self.mint_btn = make_button("Sign & Mint", GREEN, height=dp(62))
        self.mint_btn.bind(on_press=lambda *_: self._start("mint"))
        row2.add_widget(self.mint_btn)
        self.form.add_widget(row2)

        # Log
        sv, self.log = make_log_area(
            "1. Fill RPC / key / contract (or come from Deploy tab)\n"
            "2. Tap Refresh Status\n"
            "3. Enter amount (or leave blank for max)\n"
            "4. Tap Sign & Mint — payloadHash is generated automatically\n")
        self.form.add_widget(sv)
        self._log = log_to(self.log)

        self._mint_fee = 0
        self._last_payload = None
        self._mintable = 0

    def prefill_from_deploy(self, rpc_url, chain_id, private_key, contract, mint_fee):
        self.rpc_url.text  = rpc_url or ""
        self.chain_id.text = chain_id or ""
        self.pk.text       = private_key or ""
        self.contract.text = contract or ""
        self._mint_fee     = int(mint_fee or 0)
        self._log(f"Prefill: contract={contract}  fee={self._mint_fee}")
        # auto-refresh status after a short delay
        Clock.schedule_once(lambda *_: self._start("status"), 0.4)

    def _start(self, mode):
        rpc_url = self.rpc_url.text.strip()
        chain_id = self.chain_id.text.strip()
        pk = self.pk.text.strip()
        csos = self.contract.text.strip()
        if not all([rpc_url, chain_id, pk, csos]):
            self._log("[X] Fill RPC, Chain ID, Private key and cSOS address.")
            return
        self.mint_btn.disabled = True
        threading.Thread(
            target=self._worker,
            args=(mode, rpc_url, int(chain_id), pk, csos),
            daemon=True).start()

    def _worker(self, mode, rpc_url, chain_id, pk, csos):
        try:
            acct = Account.from_key(pk)
            user = acct.address
            self._log(f"User = {user}")

            # Always fetch live status
            try:
                eff, minted, mintable = fetch_mint_status(rpc_url, csos, user)
                self._mintable = mintable
                status_txt = f"Effective {eff}  |  Minted {minted}  |  Mintable {mintable}"
                Clock.schedule_once(lambda *_: setattr(self.status, "text", status_txt))
                self._log(f"   {status_txt}")
            except Exception as e:
                self._log(f"[!]  status read failed: {e}")
                if mode == "status":
                    return
                eff = minted = mintable = 0

            if mode == "status":
                self._log("[OK] Status updated.")
                return

            # ---- prepare amount ----
            amount_txt = self.amount.text.strip()
            if amount_txt == "":
                amount = mintable
                if amount == 0:
                    self._log("[X] Nothing mintable (need effective > 10 and remaining capacity).")
                    return
                self._log(f"MintMax selected amount = {amount}")
            else:
                amount = int(amount_txt)
                if amount <= 0:
                    self._log("[X] Amount must be > 0")
                    return
                if amount > mintable:
                    self._log(f"[X] Requested {amount} but only {mintable} mintable.")
                    return

            # ---- payloadHash (auto if blank) ----
            payload = self.payload.text.strip()
            if not payload:
                payload = make_unique_payload(user, amount)
                self._log(f"Auto payloadHash = {payload[:18]}…")
                Clock.schedule_once(lambda *_: setattr(self.payload, "text", payload))
            else:
                if not payload.startswith("0x"):
                    payload = "0x" + payload
                self._log(f"Using provided payloadHash = {payload[:18]}…")

            metadata = compute_metadata(amount)
            self._log(f"   metadata = {metadata}")

            # local struct hash
            local_sh = compute_struct_hash(user, user, payload, metadata)
            self._log(f"   local structHash = {local_sh}")

            # verify against LEDGER
            try:
                onchain_sh = verify_struct_hash(rpc_url, user, payload, metadata)
                if onchain_sh.lower() != local_sh.lower():
                    self._log("[X] structHash mismatch with LEDGER — aborting.")
                    return
                self._log("   [OK] hashes match")
            except Exception as e:
                self._log(f"   [!]  on-chain structHash call failed: {e}")

            try:
                used_ledger = read_bool(rpc_url, LEDGER_ADDR,
                                        "isRecordHashUsed(bytes32)", local_sh)
                if used_ledger:
                    self._log("[X] This exact record already exists on LEDGER.")
                    return
            except Exception as e:
                self._log(f"   [!]  isRecordHashUsed check failed: {e}")

            try:
                used_csos = read_bool(rpc_url, csos, "usedMintHash(bytes32)", local_sh)
                if used_csos:
                    self._log("[X] This mint hash is already used on cSOS.")
                    return
            except Exception as e:
                self._log(f"   [!]  usedMintHash check failed: {e}")

            # ---- sign ----
            self._log("Signing EIP-712 Record …")
            signature = sign_record(pk, chain_id, LEDGER_ADDR,
                                    user, user, payload, metadata)
            self._log(f"   signature = {signature[:20]}…")

            # ---- submit ----
            use_max = (self.amount.text.strip() == "")
            self._log(f"Submitting {'mintMax' if use_max else 'mint'} …")
            # note: donation is currently not attached to value; fee path still uses MINT_FEE
            tx_hash = submit_mint(rpc_url, chain_id, pk, csos, amount,
                                  payload, signature, self._mint_fee, use_max=use_max)
            tx_link = explorer_tx_url(chain_id, tx_hash)
            self._log(f"[OK] Minted {amount} cSOS")
            self._log(f"   Tx: {tx_hash}")
            self._log(f"   Tx link: {tx_link}")
            self._log(f"   Contract: {explorer_url(chain_id, csos)}")
            try:
                open_url(tx_link)
            except Exception:
                pass

            self._last_payload = None
            Clock.schedule_once(lambda *_: setattr(self.payload, "text", ""))
            Clock.schedule_once(lambda *_: setattr(self.amount, "text", ""))

            try:
                new_bal = read_uint(rpc_url, csos, "balanceOf(address)", user)
                self._log(f"   balanceOf(user) = {new_bal}")
            except Exception:
                pass

            # refresh status numbers
            try:
                eff2, minted2, mintable2 = fetch_mint_status(rpc_url, csos, user)
                status_txt = f"Effective {eff2}  |  Minted {minted2}  |  Mintable {mintable2}"
                Clock.schedule_once(lambda *_: setattr(self.status, "text", status_txt))
            except Exception:
                pass

        except Exception as e:
            self._log(f"[X] {e}\n{traceback.format_exc()}")
        finally:
            Clock.schedule_once(lambda *_: setattr(self.mint_btn, "disabled", False))


# =====================================================================
# Query tab (simple read-only helper)
# =====================================================================
class QueryTab(FormTab):
    def __init__(self, **kw):
        super().__init__(**kw)

        
        self.rpc_url  = make_input("RPC URL",
                                  text="https://ethereum-rpc.publicnode.com")
        self.address  = make_input("Address to query (0x...)")
        self.csos     = make_input("cSOS contract (optional)",
                                   text="0xce9B507C242Adf722DD1DE2d7aa5Db1BF2259D8F")
        self.form.clear_widgets()
        self.field("RPC URL", self.rpc_url)
        self.field("Address to query", self.address)
        self.field("cSOS contract (optional)", self.csos)
        self.gap()

        row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=dp(10))
        b = make_button("Query", GREEN)
        b.bind(on_press=self.on_query)
        row.add_widget(b)
        self.form.add_widget(row)

        sv, self.log = make_log_area("Enter an address and tap Query.\n")
        self.form.add_widget(sv)
        self._log = log_to(self.log)

    def on_query(self, *_):
        rpc_url = self.rpc_url.text.strip()
        addr = self.address.text.strip()
        csos = self.csos.text.strip()
        if not rpc_url or not addr:
            self._log("[X] RPC + address required.")
            return
        threading.Thread(target=self._worker, args=(rpc_url, addr, csos), daemon=True).start()

    def _worker(self, rpc_url, addr, csos):
        try:
            self._log(f"Query {addr}")
            push = read_uint(rpc_url, LEDGER_ADDR, "pushCountOf(address)", addr)
            trust = read_uint(rpc_url, LEDGER_ADDR, "trustCountOf(address)", addr)
            eff = read_int(rpc_url, LEDGER_ADDR, "effectiveOf(address)", addr)
            bal = read_uint(rpc_url, LEDGER_ADDR, "balanceOf(address)", addr)
            self._log(f"   Push   = {push}")
            self._log(f"   Trust  = {trust}")
            self._log(f"   Effective = {eff}")
            self._log(f"   balanceOf (SOS display) = {bal}")
            if csos:
                try:
                    m = read_uint(rpc_url, csos, "minted(address)", addr)
                    cbal = read_uint(rpc_url, csos, "balanceOf(address)", addr)
                    mintable = read_uint(rpc_url, csos, "mintable(address)", addr)
                    self._log(f"   cSOS minted   = {m}")
                    self._log(f"   cSOS balance  = {cbal}")
                    self._log(f"   cSOS mintable = {mintable}")
                except Exception as e:
                    self._log(f"   cSOS read error: {e}")
            self._log("[OK] done")
        except Exception as e:
            self._log(f"[X] {e}")


# =====================================================================
# Root
# =====================================================================
class Root(BoxLayout):
    """Logo header ABOVE tab strip (theme.py style). Version only on splash."""
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.padding = 0
        self.spacing = 0

        # Global header: logo top-left + title (no version)
        self.add_widget(make_header("SOS 69069 cSOS"))

        tabs = TabbedPanel(
            do_default_tab=False,
            tab_width=dp(110),
            tab_height=dp(48),
            size_hint=(1, 1),
        )
        try:
            tabs.background_color = BG
            tabs.border = [0, 0, 0, 0]
            tabs.background_image = ""
        except Exception:
            pass

        q = TabbedPanelItem(text="Query")
        q.add_widget(QueryTab())
        tabs.add_widget(q)

        m = TabbedPanelItem(text="Mint")
        m.add_widget(MintTab())
        tabs.add_widget(m)

        d = TabbedPanelItem(text="Deploy")
        d.add_widget(DeployTab())
        tabs.add_widget(d)

        tabs.default_tab = q
        self.tabs = tabs
        self.add_widget(tabs)
        self.tab_list = tabs.tab_list


# =====================================================================
# Error screen
# =====================================================================
class ImportErrorScreen(BoxLayout):
    def __init__(self, err_text, **kw):
        super().__init__(orientation="vertical", padding=12, spacing=8, **kw)
        self.add_widget(Label(
            text="Startup failed — missing or broken import",
            size_hint_y=None, height=48, bold=True,
            color=(1, 0.3, 0.3, 1),
        ))
        sv = ScrollView()
        lbl = Label(text=err_text, size_hint_y=None, halign="left", valign="top",
                    color=(1, 1, 1, 1))
        lbl.bind(width=lambda *_: setattr(lbl, "text_size", (lbl.width, None)))
        lbl.bind(texture_size=lambda *_: setattr(lbl, "height", lbl.texture_size[1]))
        sv.add_widget(lbl)
        self.add_widget(sv)


# =====================================================================
# App
# =====================================================================
class DeployerApp(App):
    title = f"SOS 69069 cSOS v{APP_VERSION}"
    last_deployed = None
    last_chain = None
    last_rpc = None

    def build(self):
        _alog("DeployerApp.build() called")
        if not _IMPORT_OK:
            _alog_err("Returning error screen due to import failure")
            return ImportErrorScreen(_IMPORT_ERROR or "Unknown import error")

        try:
            root = Root()
            for tab in root.tab_list:
                if tab.text == "Mint":
                    self.mint_tab = tab.content
                    break
            self.root_widget = root
            _alog("UI built OK")
            return root
        except Exception:
            err = traceback.format_exc()
            _alog_err("UI build crashed:\n" + err)
            return ImportErrorScreen(err)

    def switch_to_tab(self, content_widget):
        tabs = getattr(self.root_widget, "tabs", self.root_widget)
        for tab in tabs.tab_list:
            if tab.content is content_widget:
                tabs.switch_to(tab)
                return


if __name__ == "__main__":
    try:
        _alog("Entering DeployerApp().run()")
        DeployerApp().run()
        _alog("App.run() returned cleanly")
    except Exception:
        _alog_err("TOP-LEVEL CRASH:\n" + traceback.format_exc())
        raise
