import math
import hashlib
import logging

from helios.crypto import randpool, number

from helios.crypto import numtheory
from helios.crypto import elgamal
import sys
from helios.crypto.algs import Utils
from helios.crypto import algs
from helios.crypto import utils

from fractions import *


class Thresholdscheme():

    def __init__(self, n=None, k=None, ground_1=None, ground_2=None):
        self.ground_1 = ground_1
        self.ground_2 = ground_2
        self.n = n
        self.k = k

    def share_verifiably(self, s, t, EG, trustees):
        q = EG.q
        p = EG.p
        g = EG.g
        F = Polynomial(s, self, EG)
        G = Polynomial(t, self, EG)

        # Create points on polynomials from trustee x values.
        # F(0) is secret!
        points_F = F.create_points(trustees)
        points_G = G.create_points(trustees)

        # create commitments
        Ei = []
        for i in range(self.k):
            commitment_loop = Commitment_E()
            commitment_loop.generate(F.coeff[i], G.coeff[i], self.ground_1, self.ground_2, p, q, g)
            if commitment_loop.value > p - 1:
                raise Exception('Ei value to big!')

            Ei.append(commitment_loop)

        shares = []
        for i in range(self.n):
            share = Share(points_F[i], points_G[i], Ei)
            if share.verify_share(self, p, q, g):
                shares.append(share)
            else:
                return None

        return shares


class Polynomial():
    # c0 is the free term and is equal to coeff[0]
    # grade is k-1

    def __init__(self, c0=None, scheme=None, EG=None):
        p = EG.p
        q = EG.q

        self.coeff = []
        self.coeff.append(c0 % q)
        self.EG = EG
        self.scheme = scheme
        self.grade = self.scheme.k - 1

        for i in range(self.grade):
            # coefficients should be mod q
            self.coeff.append(Utils.random_mpz_lt(q))

    def set(self, coeff):
        self.coeff = coeff

    def evaluate(self, x):
        q = self.EG.q
        p = self.EG.p
        value = 0
        for i in range(self.grade + 1):
            value = (value + (self.coeff[i] * pow(x, i, q))) % q
        return value

    def create_points(self, trustees):
        points = []
        for trustee in trustees:
            point = Point(trustee.id, self.evaluate(trustee.id))
            points.append(point)

        return points


class Point():

    def __init__(self, x, y):
        self.x_value = x
        self.y_value = y

    def encrypt(self, public_key):
        plain_x = algs.EGPlaintext(self.x_value, public_key)
        plain_y = algs.EGPlaintext(self.y_value, public_key)

        return Encrypted_point(public_key.encrypt(plain_x), public_key.encrypt(plain_y))

    def on_polynomial(self, polynom):
        if polynom.evaluate(self.x_value) == self.y_value:
            return True
        else:
            return False

    @classmethod
    def from_dict(cls, d):
        """
        Deserialize from dictionary.
        """
        x_value = int(d['x_value'])
        y_value = int(d['y_value'])
        point = cls(x_value, y_value)

        return point

    def to_dict(self):
        """
        Serialize to dictionary.
        """
        return {'x_value': str(self.x_value), 'y_value': str(self.y_value)}


class Encrypted_point():

    def __init__(self, ciph_x=None, ciph_y=None):
        self.ciph_x = ciph_x
        self.ciph_y = ciph_y

    def decrypt(self, secret_key):
        x_val = secret_key.decrypt(self.ciph_x).m
        y_val = secret_key.decrypt(self.ciph_y).m

        return Point(x_val, y_val)

    @classmethod
    def from_dict(cls, d):
        """
        Deserialize from dictionary.
        """
        ciph_x = algs.EGCiphertext.from_dict(d['ciph_x'])
        ciph_y = algs.EGCiphertext.from_dict(d['ciph_y'])
        encr_point = Encrypted_point(ciph_x, ciph_y)
        return encr_point

    def to_dict(self):
        """
        Serialize to dictionary.
        """
        return {'ciph_x': self.ciph_x.to_dict(), 'ciph_y': self.ciph_y.to_dict()}


class Share():

    def __init__(self, point_s=None, point_t=None, Ei=None):
        self.point_s = point_s
        self.point_t = point_t
        self.Ei = Ei

    def add(self, addedshare, p, q, g):
        if self.point_s.x_value == addedshare.point_s.x_value == self.point_t.x_value == addedshare.point_t.x_value:
            x = self.point_s.x_value
            new_point_s = Point(x, (self.point_s.y_value + addedshare.point_s.y_value) % q)
            new_point_t = Point(x, (self.point_t.y_value + addedshare.point_t.y_value) % q)
            new_Ei = []
            for i in range(len(self.Ei)):
                Ei_now = self.Ei[i]
                Ei_now.add(addedshare.Ei[i], p, q, g)
                new_Ei.append(Ei_now)
            self.point_s = new_point_s
            self.point_t = new_point_t
            self.Ei = new_Ei

    def encrypt(self, public_key):
        encry_point_s = self.point_s.encrypt(public_key)
        encry_point_t = self.point_t.encrypt(public_key)
        encry_share = Encrypted_Share(encry_point_s, encry_point_t, self.Ei)

        return encry_share

    def sign(self, secret_key, p, q, g):
        string = utils.to_json_js(self.to_dict())
        sig = Signature()
        sig.generate(string, secret_key, p, q, g)
        return sig

    def verify_share(self, scheme, p, q, g):
        k = scheme.k
        n = scheme.n
        E = Commitment_E()
        E.generate(self.point_s.y_value, self.point_t.y_value, scheme.ground_1, scheme.ground_2, p, q, g)
        if E.value > p - 1:
            raise Exception('E value too big')

        point_number = self.point_s.x_value
        result = 1
        if len(self.Ei) != k:
            raise Exception('Ei has a wrong number of elements')

        for j in range(len(self.Ei)):
            i = point_number
            interm = pow(i, j, p)
            result = (result * pow(self.Ei[j].value, interm, p)) % p

        if result != E.value:
            return False
        else:
            return True

    @classmethod
    def from_dict(cls, d):
        """
        Deserialize from dictionary.
        """
        point_s = Point.from_dict(d['point_s'])
        point_t = Point.from_dict(d['point_t'])
        Ei_dict = d['Ei']
        Ei = []
        i = 0
        while Ei_dict.has_key(str(i)):
            dict = Ei_dict[str(i)]
            com = Commitment_E().from_dict(dict)
            Ei.append(com)
            i = i + 1

        share = Share(point_s, point_t, Ei)
        return share

    def to_dict(self):
        """
        Serialize to dictionary.
        """
        com_dict = {}
        for i in range(len(self.Ei)):
            com_dict[str(i)] = self.Ei[i].to_dict()

        return {'point_s': self.point_s.to_dict(), 'point_t': self.point_t.to_dict(), 'Ei': com_dict}


class Encrypted_Share():

    def __init__(self, encry_point_s=None, encry_point_t=None, Ei=None):
        self.encry_point_s = encry_point_s
        self.encry_point_t = encry_point_t

        self.Ei = Ei

    def decrypt(self, secret_key):
        point_s = self.encry_point_s.decrypt(
            secret_key)  # select only the value
        point_t = self.encry_point_t.decrypt(secret_key)

        return Share(point_s, point_t, self.Ei)

    @classmethod
    def from_dict(cls, d):
        """
        Deserialize from dictionary.
        """
        encry_point_s = Encrypted_point.from_dict(d['encry_point_s'])
        encry_point_t = Encrypted_point.from_dict(d['encry_point_t'])
        Ei_dict = d['Ei']
        Ei = []
        i = 0
        while Ei_dict.has_key(str(i)):
            dict = Ei_dict[str(i)]
            com = Commitment_E().from_dict(dict)
            Ei.append(com)
            i = i + 1

        encry_share = Encrypted_Share(encry_point_s, encry_point_t, Ei)

        return encry_share

    def to_dict(self):
        """
        Serialize to dictionary.
        """
        com_dict = {}
        for i in range(len(self.Ei)):
            com_dict[str(i)] = self.Ei[i].to_dict()

        return {'encry_point_s': self.encry_point_s.to_dict(), 'encry_point_t': self.encry_point_t.to_dict(), 'Ei': com_dict}


class Signed_Encrypted_Share():

    def __init__(self, sig=None, encr_share=None):
        self.sig = sig
        self.encr_share = encr_share

    @classmethod
    def from_dict(cls, d):
        """
        Deserialize from dictionary.
        """
        encr_share = Encrypted_Share.from_dict(d['encr_share'])
        sig = Signature.from_dict(d['sig'])
        sig_encr_share = Signed_Encrypted_Share(sig, encr_share)

        return sig_encr_share

    def to_dict(self):
        """
        Serialize to dictionary.
        """
        return {'sig': self.sig.to_dict(), 'encr_share': self.encr_share.to_dict()}


class Committed_Point():

    def __init__(self, point, E, Ei):
        self.point = point
        self.E = E
        self.Ei = Ei  # list of commitments

    def verify_commitments(self):
        p = self.E.p
        point_number = self.point.x_value
        result = 1
        for j in range(len(self.Ei)):
            i = point_number
            interm = pow(i, j, p)
            result = (result * pow(self.Ei[j].value, interm, p)) % (p - 1)
            if result != self.E.value:
                return False
            else:
                return True


class Feedback():

    def __init__(self, trustee_id, feedback):
        self.trustee_id = trustee_id
        self.feedback = feedback

    def set_feedback(self, feedback):
        self.feedback = feedback


class Commitment_E():

    def __init__(self, ground_1=None, ground_2=None, value=None):
        self.ground_1 = ground_1
        self.ground_2 = ground_2
        self.value = value

    def generate(self, s, t, ground_1, ground_2, p, q, g):
        s = s % q
        t = t % q
        self.ground_1 = ground_1
        self.ground_2 = ground_2
        self.value = (pow(self.ground_1, s, p) * pow(self.ground_2, t, p)) % p

    def add(self, addedcommitment, p, q, g):
        if self.ground_1 == addedcommitment.ground_1 and self.ground_2 == addedcommitment.ground_2:
            self.value = (self.value * addedcommitment.value) % p

    @classmethod
    def from_dict(cls, d):
        """
        Deserialize from dictionary.
        """
        ground_1 = int(d['ground_1'])
        ground_2 = int(d['ground_2'])
        value = int(d['value'])
        com = Commitment_E(ground_1, ground_2, value)

        return com

    @classmethod
    def array_from_dict(cls, d):
        i = 0
        while d.has_key(str(i)):
            dict = d[str(i)]
            com = Commitment_E().from_dict(dict)
            com = Commitment_E()
            i = i + 1

    def to_dict(self):
        """
        Serialize to dictionary.
        """
        return {'ground_1': str(self.ground_1), 'ground_2': str(self.ground_2), 'value': str(self.value)}


class Trustee():

    def __init__(self, trustee_id, public_key=None):
        self.trustee_id = trustee_id
        self.public_key = public_key

    def generate_keypair(self, ELGAMAL_PARAMS):
        keypair = ELGAMAL_PARAMS.generate_keypair()
        self.public_key = keypair.pk
        self.secret_key = keypair.sk
        self.pok = self.secret_key.prove_sk(algs.DLog_challenge_generator)

    def write_public_key(self, path):
        y = self.public_key.y
        string = utils.to_json(self.public_key.to_dict())
        f = open(path, 'w')
        f.write(string + '\n')
        f.close

    def write_secret_key(self, path):
        x = self.secret_key.x
        #string = str(x)+'\n'
        string = utils.to_json(self.secret_key.to_dict())
        f = open(path, 'w')
        f.write(string + '\n')
        f.close()

    def write_pok(self, path):
        pok = self.pok
        string = utils.to_json(self.pok.to_dict())
        f = open(path, 'w')
        f.write(string + '\n')
        f.close()


class Signature():

    def __init__(self, r=None, s=None):
        self.r = r
        self.s = s

    def generate(self, m, secret_key, p, q, g):
        while True:
            hash = utils.hash_b64(m)
            hash_dec = utils.encode_string_to_decimal(hash)
            k = algs.Utils.random_k_relative_prime_p_1(p)
            k_inv = algs.Utils.inverse(k, p - 1)
            x = secret_key.x
            r = pow(g, k, p)
            s = ((hash_dec - x * r) * k_inv) % (p - 1)
            if s != 1:
                self.s = s
                self.r = r
                return None

    def verify(self, m, public_key, p, q, g):
        correct = True
        y = public_key.y
        hash = utils.hash_b64(m)
        hash_dec = utils.encode_string_to_decimal(hash)
        if self.r >= p:
            correct = False
        if self.s >= p - 1:
            correct = False
        val = (pow(y, self.r, p) * pow(self.r, self.s, p)) % p
        if (pow(g, hash_dec, p) != val):
            correct = False

        return correct

    @classmethod
    def from_dict(cls, d):
        """
        Deserialize from dictionary.
        """
        r = int(d['r'])
        s = int(d['s'])

        return cls(r, s)

    def to_dict(self):
        """
        Serialize to dictionary.
        """
        return {'r': str(self.r), 's': str(self.s)}

