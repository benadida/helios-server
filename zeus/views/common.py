from django.conf import settings

from helios.crypto import elgamal
from helios import datatypes

# Parameters for everything
ELGAMAL_PARAMS = elgamal.Cryptosystem()

DEFAULT_CRYPTOSYSTEM_PARAMS = getattr(settings,
                                      'HELIOS_CRYPTOSYSTEM_PARAMS', False)

# trying new ones from OlivierP
ELGAMAL_PARAMS.p = DEFAULT_CRYPTOSYSTEM_PARAMS['p']
ELGAMAL_PARAMS.q = DEFAULT_CRYPTOSYSTEM_PARAMS['q']
ELGAMAL_PARAMS.g = DEFAULT_CRYPTOSYSTEM_PARAMS['g']

# object ready for serialization
ELGAMAL_PARAMS_LD_OBJECT = datatypes.LDObject.\
        instantiate(ELGAMAL_PARAMS, datatype='legacy/EGParams')

