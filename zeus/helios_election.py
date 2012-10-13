import datetime
import uuid

from zeus.core import ZeusCoreElection, Teller, sk_from_args
from zeus.models import ElectionInfo
from helios import models as helios_models
from helios.views import ELGAMAL_PARAMS
from helios import datatypes
from django.conf import settings

class NullStream(object):
    def read(*args):
        return ''
    def write(*args):
        return


def get_datatype(datatype, obj):
    if len(datatype.split("/")) == 1:
        datatype = 'legacy/%s' % datatype
    return datatypes.LDObject.fromDict(obj, type_hint=datatype)

class HeliosElection(ZeusCoreElection):

    def __init__(self, uuid, *args, **kwargs):
        self.model, created = ElectionInfo.objects.get_or_create(uuid=uuid)
        kwargs['cryptosystem'] = (ELGAMAL_PARAMS.p, ELGAMAL_PARAMS.g,
                                  ELGAMAL_PARAMS.q)
        kwargs['teller'] = Teller(outstream=NullStream())
        super(HeliosElection, self).__init__(*args, **kwargs)

    def do_get_cryptosystem(self):
        return [ELGAMAL_PARAMS.p, ELGAMAL_PARAMS.g,
                                  ELGAMAL_PARAMS.q]

    def do_store_zeus_key(self, secret, public,
                                commitment, challenge, response):

        p, g, q = self.do_get_cryptosystem()
        pk = get_datatype('EGPublicKey', {'p':p, 'g':g, 'q':q, 'y':public})
        trustee, created = helios_models.Trustee.objects.get_or_create(election=self.model.election,
                                        public_key_hash=pk.hash)

        trustee.uuid = str(uuid.uuid4())
        trustee.name = settings.DEFAULT_FROM_NAME
        trustee.email = settings.DEFAULT_FROM_EMAIL

        p, g, q = self.do_get_cryptosystem()
        pk = get_datatype('EGPublicKey', {'p':p, 'g':g, 'q':q, 'y':public})
        trustee.public_key = pk

        sk = get_datatype('EGSecretKey', {'public_key': pk.toDict(), 'x': secret})
        trustee.secret_key = sk
        trustee.last_verified_key_at = datetime.datetime.now()
        trustee.public_key_hash = pk.hash

        pok = get_datatype('DLogProof', {'commitment': commitment, 'challenge':
                                         challenge, 'response': response})
        trustee.pok = pok
        trustee.save()

    def do_get_zeus_key(self):
        t = self.model.election.get_helios_trustee()
        args = self.do_get_cryptosystem()
        args += [t.secret_key.x, t.public_key.y]
        args += (t.pok.commitment, t.pok.challenge, t.pok.response)
        return sk_from_args(*args)


