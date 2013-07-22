#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
PYTHON_MAJOR = sys.version_info[0]
from datetime import datetime
from random import randint, shuffle, choice
from collections import deque
from hashlib import sha256, sha1
from itertools import izip, cycle, chain
from functools import partial
from math import log
from bisect import bisect_right
import Crypto.Util.number as number
inverse = number.inverse
from Crypto import Random
from operator import mul as mul_operator
from os import (fork, kill, getpid, waitpid, ftruncate, lseek, fstat,
                read, write, unlink, open as os_open, close,
                O_CREAT, O_RDWR, O_APPEND, SEEK_CUR, SEEK_SET)
from fcntl import flock, LOCK_EX, LOCK_UN
from multiprocessing import Semaphore, Queue as mpQueue
from Queue import Empty, Full
from select import select
from signal import SIGKILL
from errno import ESRCH
from cStringIO import StringIO
from marshal import loads as marshal_loads, dumps as marshal_dumps
from json import load as json_load
from binascii import hexlify
import inspect
import re
import csv
from time import time, sleep

try:
    from gmpy import mpz
    _pow = pow

    def pow(b, e, m):
        return int(_pow(mpz(b), e, m))
except ImportError:
    print "Warning: Could not import gmpy. Falling back to SLOW crypto."

bit_length = lambda num: num.bit_length()
if sys.version_info < (2, 7):
    def bit_length(num):
        s = bin(num)
        s = s.lstrip('-0b')
        return len(s)


class ZeusError(Exception):
    pass

ALPHA = 0
BETA  = 1
PROOF = 2

VOTER_KEY_CEIL = 2**256
VOTER_SLOT_CEIL = 2**48
MIN_MIX_ROUNDS = 3

V_CAST_VOTE     =   'CAST VOTE'
V_PUBLIC_AUDIT  =   'PUBLIC AUDIT'
V_PUBLIC_AUDIT_FAILED = 'PUBLIC AUDIT FAILED'
V_AUDIT_REQUEST =   'AUDIT REQUEST'

V_FINGERPRINT   =   'FINGERPRINT: '
V_INDEX         =   'INDEX: '
V_PREVIOUS      =   'PREVIOUS VOTE: '
V_VOTER         =   'VOTER: '
V_ELECTION      =   'ELECTION PUBLIC: '
V_ZEUS_PUBLIC   =   'ZEUS PUBLIC: '
V_TRUSTEES      =   'TRUSTEE PUBLICS: '
V_CANDIDATES    =   'CANDIDATES: '
V_MODULUS       =   'MODULUS: '
V_GENERATOR     =   'GENERATOR: '
V_ORDER         =   'ORDER: '
V_ALPHA         =   'ALPHA: '
V_BETA          =   'BETA: '
V_COMMITMENT    =   'COMMITMENT: '
V_CHALLENGE     =   'CHALLENGE: '
V_RESPONSE      =   'RESPONSE: '
V_COMMENTS      =   'COMMENTS: '

_random_generator_file = Random.new()


def c2048():
    p = 19936216778566278769000253703181821530777724513886984297472278095277636456087690955868900309738872419217596317525891498128424073395840060513894962337598264322558055230566786268714502738012916669517912719860309819086261817093999047426105645828097562635912023767088410684153615689914052935698627462693772783508681806906452733153116119222181911280990397752728529137894709311659730447623090500459340155653968608895572426146788021409657502780399150625362771073012861137005134355305397837208305921803153308069591184864176876279550962831273252563865904505239163777934648725590326075580394712644972925907314817076990800469107L
    q = (p - 1) / 2
    g0 = 9413060360466448686039353223715000895476653994878292629580005715413149309413036670654764332965742884842644976907757623558004566639402772235441684360505344528020498265000752015019397070007216279360736764344882321624397028370364113905272387950790871846302871493514381824738727519597460997038917208851728646071589006043553117796202327835258471557309074326286364547643265711871602511049432774864712871101230345650552324151494772279651818096255453921354231946373043379760842748887723994561573824188324702878924365252191380946510359485948529040410642676919518011031107993744638249385966735471272747905107277767654692463409L
    g = pow(g0, 2, p)
    x = 1469094658184849175779600697490107440856998313689389490776822841770551060089241836869172678278809937016665355003873748036083276189561224629758766413235740137792419398556764972234641620802215276336480535455350626659186073159498839187349683464453803368381196713476682865017622180273953889824537824501190403304240471132731832092945870620932265054884989114885295452717633367777747206369772317509159592997530169042333075097870804756411795033721522447406584029422454978336174636570508703615698164528722276189939139007204305798392366034278815933412668128491320768153146364358419045059174243838675639479996053159200364750820L
    y = pow(g, x, p)
    return p, q, g, x, y


def c4096():
    p = 989739086584899206262870941495275160824429055560857686533827330176266094758539805894052465425543742758378056898916975688830042897464663659316565658681455337631927169716594388227886841821639348093631558865282436882702647379556880510663048896169189712894445414625772725732980365633359489925655152255197807877415565545449245335018149917344244391646710898790373814092708148348289809496148127266128833710713633812316745730790666494269135285419129739194203790948402949190257625314846368819402852639076747258804218169971481348145318863502143264235860548952952629360195804480954275950242210138303839522271423213661499105830190864499755639732898861749724262040063985288535046880936634385786991760416836059387492478292392296693123148006004504907256931727674349140604415435481566616601234362361163612719971993921275099527816595952109693903651179235539510208063074745067478443861419069632592470768800311029260991453478110191856848938562584343057011570850668669874203441257913658507505815731791465642613383737548884273783647521116197224510681540408057273432623662515464447911234487758557242493633676467408119838655147603852339915225523319492414694881196888820764825261617098818167419935357949154327914941970389468946121733826997098869038220817867L
    q = (p - 1) / 2
    g0 = 905379109279378054831667933021934383049203365537289539394872239929964585601843446288620085443488215849235670964548330175314482714496692320746423694498241639600420478719942396782710397961384242806030551242192462751290192948710587865133212966245479354320246142602442604733345159076201107781809110926242797620743135121644363670775798795477440466184912353407400277976761890802684500243308628180860899087380817190547647023064960578905266420963880594962888959726707822636419644103299943828117478223829675719242465626206333420547052590211049681468686068299735376912002300947541151842072332585948807353379717577259205480481848616672575793598861753734098315126325768793219682113886710293716896643847366229743727909553144369466788439959883261553813689358512428875932488880462227384092880763795982392286068303024867839002503956419627171380097115921561294617590444883631704182199378743252195067113032765888842970561649353739790451845746283977126938388768194155261756458620157130236063008120298689861009201257816492322336749660466823368953374665392072697027974796990473518319104748485861774121624711704031122201281866933558898944724654566536575747335471017845835905901881155585701928903481835039679354164368715779020008195518681150433222291955165L
    g = pow(g0, 2, p)
    x = 647933544049795511827798129172072110981142881302659046504851880714758189954678388061140591638507897688860150172786162388977702691017897290499481587217235024527398988456841084908316048392761588172586494519258100136278585068551347732010458598151493508354286285844575102407190886593809138094472405420010538813082865337021620149988134381297015579494516853390895025461601426731339937104058096140467926750506030942064743367210283897615531268109510758446261715511997406060121720139820616153611665890031155426795567735688778815148659805920368916905139235816256626015209460683662523842754345740675086282580899535810538696220285715754930732549385883748798637705838427072703804103334932744710977146180956976178075890301249522417212403111332457542823335873806433530059450282385350277072533852089242268226463602337771206993440307129522655918026737300583697821541073342234103193338354556016483037272142964453985093357683693494958668743388232300130381063922852993385893280464288436851062428165061787405879100666008436508712657212533042512552400211216182296391299371649632892185300062585730422510058896752881990053421349276475246102235172848735409746894932366562445227945573810219957699804623611666670328066491935505098459909869015330820515152531557L
    y = pow(g, x, p)
    return p, q, g, x, y


p, q, g, x, y = c2048()

_default_crypto = {}
_default_crypto['modulus'] = p
_default_crypto['order'] = q
_default_crypto['generator'] = g

_default_public_key = {}
_default_public_key.update(_default_crypto)
_default_public_key['public'] = y

_default_secret_key = {}
_default_secret_key.update(_default_crypto)
_default_secret_key['secret'] = x


def crypto_args(cryptosys):
    return [cryptosys['modulus'], cryptosys['generator'], cryptosys['order']]

def crypto_from_args(p, g, q):
    return {'modulus': p, 'generator': g, 'order': q}

def key_proof(k):
    return [k['commitment'], k['challenge'], k['response']]

def key_public(pk):
    return pk['public']

def key_secret(sk):
    return sk['secret']

def pk_args(pk):
    return [pk['modulus'], pk['generator'], pk['order'], pk['public']]

def pk_all_args(pk):
    return [pk['modulus'], pk['generator'], pk['order'], pk['public'],
            ['commitment'], pk['challenge'], pk['response']]

def pk_noproof_from_args(p, g, q, y):
    return {'modulus': p, 'generator': g, 'order': q, 'public': y}

def pk_from_args(p, g, q, y, t, c, f):
    return {'modulus': p, 'generator': g, 'order': q, 'public': y,
            'commitment': t, 'challenge': c, 'response': f}

def sk_args(pk):
    return [pk['modulus'], pk['generator'], pk['order'], pk['secret']]

def sk_all_args(sk):
    return [sk['modulus'], sk['generator'], sk['order'],
            sk['secret'], sk['public'],
            ['commitment'], sk['challenge'], sk['response']]

def sk_from_args(p, g, q, x, y, t, c, f):
    return {'modulus': p, 'generator': g, 'order': q,
            'secret': x, 'public': y,
            'commitment': t, 'challenge': c, 'response': f}


def get_timestamp():
    return datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%S.%fZ")

def to_canonical(obj, out=None):
    toplevel = 0
    if out is None:
        toplevel = 1
        out = StringIO()
    if isinstance(obj, basestring):
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        z = len(obj)
        x = "%x" % z
        w = ("%02x" % len(x))[:2]
        out.write("%s%s_" % (w, x))
        out.write(obj)
    elif isinstance(obj, int) or isinstance(obj, long):
        s = "%x" % obj
        z = len(s)
        x = "%x" % z
        w = ("%02x" % len(x))[:2]
        out.write("%s%s0%s" % (w, x, s))
    elif isinstance(obj, dict):
        out.write('{\x0a')
        cobj = {}
        for k, v in obj.iteritems():
            if not isinstance(k, str):
                if isinstance(k, unicode):
                    k = k.encode('utf-8')
                elif isinstance(k, int) or isinstance(k, long):
                    k = str(k)
                else:
                    m = "Unsupported dict key type '%s'" % (type(k),)
            cobj[k] = v
        del obj
        keys = cobj.keys()
        keys.sort()
        prev = None
        for k in keys:
            if prev is not None:
                out.write(',\x0a')
            if k == prev:
                tail = '...' if len(k) > 64 else ''
                m = "duplicate key '%s' in dict" % (k[:64] + tail,)
                raise AssertionError(m)
            to_canonical(k, out=out)
            out.write(': ')
            to_canonical(cobj[k], out=out)
            prev = k
        out.write('}\x0a')
    elif isinstance(obj, list) or isinstance(obj, tuple):
        out.write('[\x0a')
        iterobj = iter(obj)
        for o in iterobj:
            to_canonical(o, out=out)
            break
        for o in iterobj:
            out.write(',\x0a')
            to_canonical(o, out=out)
        out.write(']\x0a')
    elif obj is None:
        out.write('null')
    else:
        m = "to_canonical: invalid object type '%s'" % (type(obj),)
        raise AssertionError(m)

    if toplevel:
        out.seek(0)
        return out.read()

def from_canonical(inp, unicode_strings=0, s=''):
    if isinstance(inp, str):
        inp = StringIO(inp)

    read = inp.read
    if not s:
        s = read(2)

    if s == 'nu':
        s += read(2)
        if s == 'null':
            return None
        else:
            m = ("byte %d: invalid token '%s' instead of 'null'"
                % (inp.tell(), s))
            raise ValueError(m)

    if s == '[\x0a':
        obj = []
        append = obj.append
        while 1:
            s = read(2)
            if not s:
                m = "byte %d: eof within a list" % inp.tell()
                raise ValueError(m)

            if s == ']\x0a':
                return obj

            item = from_canonical(inp, unicode_strings=unicode_strings, s=s)
            append(item)

            s = read(2)
            if s == ']\x0a':
                return obj

            if s != ',\x0a':
                m = ("byte %d: in list: illegal token '%s' instead of ',\\n'"
                    % (inp.tell(), s))
                raise ValueError(m)

    if s == '{\x0a':
        obj = {}
        while 1:
            s = read(2)
            if not s:
                m = "byte %d: eof within dict" % inp.tell()
                raise ValueError(m)

            if s == '}\x0a':
                return obj

            key = from_canonical(inp, unicode_strings=unicode_strings, s=s)
            s = read(2)
            if s != ': ':
                m = ("byte %d: invalid token '%s' instead of ': '"
                    % (inp.tell(), s))
                raise ValueError(m)

            value = from_canonical(inp, unicode_strings=unicode_strings)
            obj[key] = value  # allow key TypeError rise through

            s = read(2)
            if not s:
                m = "byte %d: eof inside dict" % inp.tell()
                raise ValueError(m)

            if s == '}\x0a':
                return obj

            if s != ',\x0a':
                m = ("byte %d: illegal token '%s' in dict instead of ',\\n'"
                    % (inp.tell(), s))
                raise ValueError(m)

    w = int(s, 16)
    s = read(w)
    if len(s) != w:
        m = "byte %d: eof while reading header size %d" % (inp.tell(), w)
        raise ValueError(m)

    z = int(s, 16)
    c = read(1)
    if not c:
        m = "byte %d: eof while reading object tag" % inp.tell()
        raise ValueError(m)

    s = read(z)
    if len(s) != z:
        m = "byte %d: eof while reading object size %d" % (inp.tell(), z)
        raise ValueError(m)

    if c == '_':
        if unicode_strings:
            try:
                s = s.decode('utf-8')
            except UnicodeDecodeError:
                pass
        return s
    elif c == '0':
        num = int(s, 16)
        return num
    else:
        m = "byte %d: invalid object tag '%d'" % (inp.tell()-z, c)
        raise ValueError(m)


#class Empty(Exception):
#    pass
#class Full(Exception):
#    pass
class EOF(Exception):
    pass

MV_ASYNCARGS = '=ASYNCARGS='
MV_EXCEPTION = '=EXCEPTION='

def wait_read(fd, block=True, timeout=0):
    if block:
        timeout = None
    while 1:
        r, w, x = select([fd], [], [], timeout)
        if not r:
            if not block:
                raise Empty()
            else:
                raise EOF("Select Error")
        if block:
            st = fstat(fd)
            if not st.st_size:
                sleep(0.01)
                continue

def read_all(fd, size):
    got = 0
    s = ''
    while got < size:
        r = read(fd, size-got)
        if not r:
            break
        got += len(r)
        s += r
    return s

def wait_write(fd, block=True, timeout=0):
    if block:
        timeout = None
    r, w, x = select([], [fd], [], timeout)
    if not w:
        if not block:
            raise Full()
        else:
            raise EOF("Write Error")

def write_all(fd, data):
    size = len(data)
    written = 0
    while written < size:
        w = write(fd, buffer(data, written, size-written))
        if not w:
            m = "Write EOF"
            raise EOF(m)
        written += w
    return written


class CheapQueue(object):
    _initpid = None
    _pid = _initpid
    _serial = 0

    @classmethod
    def atfork(cls):
        cls._pid = getpid()

    def __init__(self):
        pid = getpid()
        self._initpid = pid
        self._pid = None
        serial = CheapQueue._serial + 1
        CheapQueue._serial = serial
        self.serial = serial
        self.frontfile = '/dev/shm/cheapQ.%s.%s.front' % (pid, serial)
        self.backfile = '/dev/shm/cheapQ.%s.%s.back' % (pid, serial)
        self.front_fd = None
        self.back_fd = None
        self.front_sem = Semaphore(0)
        self.back_sem = Semaphore(0)
        self.getcount = 0
        self.putcount = 0
        self.get_input = self.init_input
        self.get_output = self.init_output

    def init(self):
        frontfile = self.frontfile
        self.front_fd = os_open(frontfile, O_RDWR|O_CREAT|O_APPEND, 0600)
        backfile = self.backfile
        self.back_fd = os_open(backfile, O_RDWR|O_CREAT|O_APPEND, 0600)
        self._pid = getpid()
        del self.get_output
        del self.get_input

    def __del__(self):
        try:
            unlink(self.frontfile)
            unlink(self.backfile)
        except:
            pass

    def init_input(self):
        self.init()
        return self.get_input()

    def init_output(self):
        self.init()
        return self.get_output()

    def get_input(self):
        if self._pid == self._initpid:
            return self.front_sem, self.front_fd
        else:
            return self.back_sem, self.back_fd

    def get_output(self):
        if self._pid == self._initpid:
            return self.back_sem, self.back_fd
        else:
            return self.front_sem, self.front_fd

    def down(self, sema, timeout=None):
        #if timeout is None:
        #    print ("REQ DOWN %d %d %d [%d %d]"
        #            % (self.serial, getpid(), sema._semlock.handle,
        #               self.front_sem._semlock.handle,
        #               self.back_sem._semlock.handle))
        ret = sema.acquire(True, timeout=timeout)
        #if ret:
        #    print "DOWN %d %d" % (self.serial, getpid())
        return ret

    def up(self, sema, timeout=None):
        sema.release()
        #print ("UP %d %d %d [%d %d]"
        #        % (self.serial, getpid(), sema._semlock.handle,
        #           self.front_sem._semlock.handle,
        #           self.back_sem._semlock.handle))

    def put(self, obj, block=True, timeout=0):
        data = marshal_dumps(obj)
        sema, fd = self.get_output()
        #if self._pid == self._initpid:
        #    print "> PUT  ", getpid(), self.serial, self.putcount, '-'
        #else:
        #    print "  PUT <", getpid(), self.serial, self.putcount, '-'
        chk = sha256(data).digest()
        flock(fd, LOCK_EX)
        try:
            write_all(fd, "%016x%s" % (len(data), chk))
            write_all(fd, data)
        finally:
            flock(fd, LOCK_UN)
            self.up(sema)
        self.putcount += 1

    def get(self, block=True, timeout=0):
        if block:
            timeout=None
        sema, fd = self.get_input()
        #if self._pid == self._initpid:
        #    print "< GET  ", getpid(), self.serial, self.getcount, '-'
        #else:
        #    print "  GET >", getpid(), self.serial, self.getcount, '-'
        if not self.down(sema, timeout=timeout):
            raise Empty()
        flock(fd, LOCK_EX)
        try:
            header = read_all(fd, 48)
            chk = header[16:]
            header = header[:16]
            size = int(header, 16)
            data = read_all(fd, size)
            pos = lseek(fd, 0, SEEK_CUR)
            if pos > 1048576:
                st = fstat(fd)
                if pos >= st.st_size:
                    ftruncate(fd, 0)
                    lseek(fd, 0, SEEK_SET)
        finally:
            flock(fd, LOCK_UN)
        _chk = sha256(data).digest()
        if chk != _chk:
            raise AssertionError("Corrupt Data!")
        obj = marshal_loads(data)
        self.getcount += 1
        return obj

#Queue = mpQueue
Queue = CheapQueue

def async_call(func, args, kw, channel):
    argspec = inspect.getargspec(func)
    if argspec.keywords or 'async_channel' in argspec.args:
        kw['async_channel'] = channel
    return func(*args, **kw)

def async_worker(link):
    while 1:
        inp = link.receive()
        if inp is None:
            break
        try:
            if not isinstance(inp, tuple) and inp and inp[0] != MV_ASYNCARGS:
                m = "%x: first input not in MV_ASYNCARGS format: '%s'" % (inp,)
                raise ValueError(m)
            mv, func, args, kw = inp
            func = globals()[func]
            ret = async_call(func, args, kw, link)
            link.send(ret)
        except Exception, e:
            #import traceback
            #traceback.print_exc()
            e = (MV_EXCEPTION, str(e))
            link.send_shared(e)
            raise
        finally:
            link.disconnect()

class AsyncWorkerLink(object):
    def __init__(self, pool, index):
        self.pool = pool
        self.index = index

    def send(self, data, wait=1):
        self.pool.master_queue.put((self.index, data), block=wait)

    def receive(self, wait=1):
        ret = self.pool.worker_queues[self.index].get(block=wait)
        if isinstance(ret, tuple) and ret and ret[0] == MV_EXCEPTION:
            raise Exception(ret[1])
        return ret

    def send_shared(self, data, wait=1):
        self.pool.master_queue.put((0, data), block=wait)

    def disconnect(self, wait=1):
        self.pool.master_queue.put((self.index, None), block=wait)

class AsyncWorkerPool(object):
    def __init__(self, nr_parallel, worker_func):
        master_queue = Queue()
        self.master_queue = master_queue
        self.worker_queues = [master_queue] + [
                              Queue() for _ in xrange(nr_parallel)]
        worker_pids = []
        self.worker_pids = worker_pids
        append = worker_pids.append

        for i in xrange(nr_parallel):
            pid = fork()
            Random.atfork()
            CheapQueue.atfork()
            if not pid:
                try:
                    worker_link = AsyncWorkerLink(self, i+1)
                    worker_func(worker_link)
                finally:
                    try:
                        kill(getpid(), SIGKILL)
                    except:
                        pass
                    while 1:
                        print "PLEASE KILL ME"
                        sleep(1)
            append(pid)

    def kill(self):
        for pid in self.worker_pids:
            try:
                kill(pid, SIGKILL)
                waitpid(pid, 0)
            except OSError, e:
                if e.errno != ESRCH:
                    raise

    def send(self, worker, data):
        if not worker:
            m = "Controller attempt to write to master link"
            raise AssertionError(m)
        self.worker_queues[worker].put(data)

    def receive(self, wait=1):
        try:
            val = self.master_queue.get(block=wait)
        except Empty:
            val = None
        return val

class AsyncChannel(object):
    def __init__(self, controller):
        self.controller = controller
        self.channel_no = controller.get_channel()

    def send(self, data):
        return self.controller.send(self.channel_no, data)

    def receive(self, wait=1):
        data = self.controller.receive(self.channel_no, wait=wait)
        if isinstance(data, tuple) and data and data[0] == MV_EXCEPTION:
            raise Exception(data[1])
        return data

class AsyncFunc(object):
    def __init__(self, controller, func, args, kw):
        self.controller = controller
        self.func = func
        self.args = args
        self.kw = kw

    def __call__(self, *args, **kw):
        call_kw = dict(self.kw)
        call_kw.update(kw)
        call_args = self.args + args
        call_func = self.func
        controller = self.controller
        async_args = (MV_ASYNCARGS, call_func.__name__, call_args, call_kw)
        channel = AsyncChannel(controller)
        controller.submit(channel.channel_no, async_args)
        return channel

class AsyncController(object):
    serial = 0
    parallel = 0
    channel_queue = None
    shared_queue = None

    def __new__(cls, *args, **kw):
        parallel = int(kw.get('parallel', 2))
        self = object.__new__(cls)
        master_link = AsyncWorkerPool(parallel, async_worker)
        self.master_link = master_link
        self.idle_workers = set(xrange(1, parallel + 1))
        self.worker_to_channel = [0] + [None] * (parallel)
        self.channel_to_worker = {0: 0}
        self.pending = deque()
        self.channels = {0: deque()}
        self.parallel = parallel
        return self

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        master_link = self.master_link
        for i in xrange(1, self.parallel + 1):
            master_link.send(i, None)
        sleep(0.3)
        self.master_link.kill()

    def get_channel(self):
        channel = self.serial + 1
        self.serial = channel
        return channel

    def process(self, wait=0):
        master_link = self.master_link
        idle_workers = self.idle_workers
        pending = self.pending
        channel_to_worker = self.channel_to_worker
        worker_to_channel = self.worker_to_channel
        channels = self.channels

        _wait = wait
        while 1:
            blocked = []
            while pending:
                channel, data = pending.pop()
                if channel in channel_to_worker:
                    worker = channel_to_worker[channel]
                    master_link.send(worker, data)
                elif not idle_workers:
                    blocked.append((channel, data))
                else:
                    worker = idle_workers.pop()
                    channel_to_worker[channel] = worker
                    worker_to_channel[worker] = channel
                    master_link.send(worker, data)
            for b in blocked:
                pending.appendleft(b)

            data = master_link.receive(wait=_wait)
            if data is None:
                break
            _wait = 0

            worker, data = data
            channel = worker_to_channel[worker]
            if channel is None:
                continue

            if data is None:
                if worker > 0:
                    worker_to_channel[worker] = None
                else:
                    m = "Attempt to disconnect master link"
                    raise AssertionError(m)
                if channel > 0:
                    del channel_to_worker[channel]
                else:
                    m = "Attempt to close master channel"
                    raise AssertionError(m)

                idle_workers.add(worker)
            else:
                channels[channel].appendleft(data)

    def send(self, channel_no, data):
        channels = self.channels
        channel_to_worker = self.channel_to_worker
        if channel not in channel_to_worker:
            return
        worker = channel_to_worker[channel]
        self.master_link.send(worker, data)

    def receive(self, channel_no, wait=1):
        channels = self.channels
        if channel_no not in channels:
            return None

        self.process(wait=0)
        while 1:
            if not channels[channel_no]:
                if (channel_no is not None and
                    channel_no not in self.channel_to_worker):
                    del channels[channel_no]
                    return None

                if not wait:
                    return None

                self.process(wait=1)
            else:
                val = channels[channel_no].pop()
                return val

    def receive_shared(self, wait=1):
        val = self.receive(0, wait=wait)
        if isinstance(val, tuple) and val and val[0] == MV_EXCEPTION:
            raise Exception(val[1])
        return val

    def submit(self, channel_no, async_args):
        channels = self.channels
        if channel_no in channels:
            m = "Channel already in use"
            raise ValueError(m)
        channels[channel_no] = deque()
        self.pending.appendleft((channel_no, async_args))
        if self.parallel <= 0:
            async_worker
        self.process(wait=0)

    def make_async(self, func, *args, **kw):
        return AsyncFunc(self, func, args, kw)


class TellerStream(object):

    def __init__(self, outstream=None, output_interval_ms=2000,
                       buffering=1, buffer_feeds=0):
        self.oms = output_interval_ms
        self.outstream = outstream
        self.last_output = 0
        self.last_eject = 0
        self.buffer_feeds = buffer_feeds
        self.buffering = buffering
        self.buffered_lines = []

    def write(self, data):
        buffer_feeds = self.buffer_feeds
        eject = not buffer_feeds and (1 if '\n' in data else 0)
        if not self.buffering:
            self.buffered_lines = []
        self.buffered_lines.append(data)

        t = time()
        tdiff = (t - self.last_output) * 1000.0

        if eject or self.last_eject or tdiff > self.oms:
            self.last_output = t
            self.flush()

        self.last_eject = eject

    def flush(self):
        outstream = self.outstream
        if outstream:
            outstream.write(''.join(self.buffered_lines))
        self.buffered_lines = []


class Teller(object):
    name = None
    total = None
    current = None
    finished = None
    status_fmt = None
    status_args = None
    start_time = None
    disabled = False
    children = None
    parent = None
    resuming = None
    outstream = None
    last_active = None
    last_teller = [None]
    last_ejected = [None]
    last_line = ['']

    redirect = True
    fail_parent = True
    raise_errors = True
    default_tell = True
    suppress_exceptions = False
    default_status_fmt = '%d/%d'

    eol             =   '\r'
    feed            =   '\n'
    prefix_filler   =   '|  '
    status_sep      =   ' ... '

    start_mark      =   '-- '
    pending_mark    =   '|  '
    notice_mark     =   '|  :: '
    fail_mark       =   '!! '
    finish_mark     =   '++ '

    start_status    =   '      '
    pending_status  =   '      '
    fail_status     =   '*FAIL*'
    finish_status   =   ' -OK- '

    def __init__(self, name='', total=1, current=0, depth=0,
                       parent=None, resume=False, subtask=False,
                       outstream=sys.stderr, **kw):
        if subtask and parent:
            name = str(parent) + '/' + name
            self.feed = ''
        self.name = name
        self.depth = depth
        self.total = total
        self.current = current
        self.clear_size = 0
        self.parent = parent
        self.children = {}
        self.set_format()
        self.resuming = resume
        self.outstream = outstream
        self.start_time = time()

        for k, v in kw.iteritems():
            a = getattr(self, k, None)
            if (a is None and not (isinstance(a, basestring)
                                    or isinstance(a, bool))):
                continue
            setattr(self, k, v)

    def set_format(self):
        current = self.current
        total = self.total
        if total == 1:
            self.status_fmt = ''
            self.status_args = ()
            return

        self.status_fmt = self.default_status_fmt
        self.status_args = (current, total)

    def kill_child(self, child_id):
        children = self.children
        if child_id in children:
            del children[child_id]

    def __str__(self):
        total = self.total
        current = self.current
        status_fmt = self.status_fmt
        if status_fmt is None:
            self.set_format()
            status_fmt = self.status_fmt
        status_args = self.status_args

        start_time = self.start_time
        running_time = time() - start_time

        finished = self.finished
        if finished is None:
            mark = self.start_mark
            status = self.start_status
        elif finished > 0:
            mark = self.finish_mark
            status = self.finish_status
        elif finished < 0:
            mark = self.fail_mark
            status = self.fail_status
        elif finished == 0:
            mark = self.pending_mark
            status = self.pending_status
        else:
            m = "Finished not None or int: %r" % (finished,)
            raise ValueError(m)

        line = (self.prefix_filler * (self.depth - 1)) + mark
        line += self.name + self.status_sep
        line += self.status_fmt % self.status_args
        line += status
        if running_time > 2 and current > 0 and current < total:
            ss = running_time * (total - current) / current
            mm = ss / 60
            ss = ss % 60
            hh = mm / 60
            mm = mm % 60
            line += 'approx. %02d:%02d:%02d left' % (hh, mm, ss)
        return line

    def disable(self):
        self.disabled = True
        for child in self.children.values():
            child.disable()

    def tell(self, feed=False, eject=False):
        if self.disabled:
            return

        line = self.__str__()
        self.output(line, feed=feed, eject=eject)

    def output(self, text, feed=False, eject=0):
        outstream = self.outstream
        if outstream is None or self.disabled:
            return

        feeder = self.feed
        eol = self.eol
        text += eol
        last_line = self.last_line
        if eol.endswith('\r'):
            clear_line = ' ' * len(last_line[0]) + '\r'
        else:
            clear_line = ''
        text = clear_line + text

        last_teller = self.last_teller
        teller = last_teller[0]
        last_ejected = self.last_ejected
        ejected = last_ejected[0]
        if not ejected and (feed or teller != self):
            text = feeder + text
        if eject:
            text += feeder * eject

        outstream.write(text)
        last_teller[0] = self
        last_ejected[0] = eject
        junk, sep, last = text.rpartition('\n')
        last_line[0] = last[len(clear_line):]

    def check_tell(self, tell, feed=False, eject=False):
        if tell or (tell is None and self.default_tell):
            self.tell(feed=feed, eject=eject)

    def active(self):
        if not self.redirect:
            return self

        last_active = self.last_active
        if (last_active is not None
            and last_active == self.last_teller[0]
            and not last_active.disabled):
            return last_active

        while 1:
            children = self.children
            if not children:
                return self

            if len(children) != 1:
                m = ("Cannot redirect: more than one children are active! "
                     "Either start one children at a time, "
                     "or set redirect=False")
                raise ValueError(m)

            self, = children.values()

        return self

    def task(self, name='', total=1, current=0,
             resume=False, subtask=False, **kw):
        self = self.active()
        children = self.children
        kw['parent'] = self
        kw['depth'] = self.depth + 1
        kw['outstream'] = self.outstream
        kw['fail_parent'] = self.fail_parent
        kw['active'] = self.active
        task = self.__class__(name=name, total=total, current=current,
                              resume=resume, subtask=subtask, **kw)
        children[id(task)] = task
        task.check_tell(None)
        return task

    def notice(self, fmt, *args):
        self = self.active()

        text = fmt % args
        lines = []
        append = lines.append

        for text_line in text.split('\n'):
            line = self.prefix_filler * (self.depth-1) + self.notice_mark
            line += text_line
            append(line)

        final_text = '\n'.join(lines)
        self.output(final_text, feed=1, eject=1)

    def __enter__(self):
        if self.disabled:
            m = "Task '%s' has been disabled" % (self.name,)
            raise ValueError(m)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if not self.resuming:
                self.end(1)
            self.resuming = 0
            return None

        self.end(-1)
        if self.raise_errors:
            return None
        if not self.suppress_exceptions:
            print_exc()
        return True

    def end(self, finished, name='', tell=None):
        if self.disabled:
            return

        self.finished = finished
        eject = 2
        parent = self.parent
        if parent and parent.parent:
            eject = 1
        self.check_tell(tell, eject=eject)

        task = self
        while 1:
            if task is None or task.name.startswith(name):
                break
            task = task.parent

        if task is not None:
            parent = task.parent
            if parent is not None:
                parent.kill_child(id(task))
                if finished < 0 and task.fail_parent:
                    parent.fail(tell=tell)

        task.disable()

    def resume(self):
        self = self.active()
        self.resuming = 1
        return self

    def status(self, status_fmt, *status_args, **kw):
        self = self.active()
        tell = kw.get('tell', None)
        self.status_fmt = status_fmt
        self.status_args = status_args
        self.check_tell(tell)

    def progress(self, current, tell=None):
        self = self.active()
        self.current = current
        total = self.total
        self.status_fmt = self.default_status_fmt
        self.status_args = (current, total)
        if total and current >= total:
            self.finished = 1

        self.check_tell(tell)

    def advance(self, delta_current=1, tell=None):
        self = self.active()
        current = self.current + delta_current
        self.current = current
        total = self.total
        self.status_fmt = self.default_status_fmt
        self.status_args = (current, total)
        if total and current >= total:
            self.finished = 1

        self.check_tell(tell)

    def get_current(self):
        self = self.active()
        return self.current

    def get_total(self):
        self = self.active()
        return self.total

    def get_finished(self):
        self = self.active()
        return self.finished

    def finish(self, name='', tell=None):
        self = self.active()
        return self.end(1, name=name, tell=tell)

    def fail(self, name='', tell=None):
        self = self.active()
        return self.end(-1, name=name, tell=tell)


_teller = Teller()


def validate_cryptosystem(modulus, generator, order, teller=_teller):
    m = None
    p = modulus
    g = generator
    q = order

    with teller.task("Validating Cryptosystem", resume=1):
        teller.notice("modulus     : %s...", ("%x" % p)[:32])
        teller.notice("generator   : %s...", ("%x" % g)[:32])
        teller.notice("group order : %s...", ("%x" % q)[:32])

    task = teller.task

    with task("is the modulus size >= 2048 bits?"):
        if log(p, 2) <= 2047:
            m = "MODULUS BIT SIZE < 2048"
            raise AssertionError(m)

    with task("is the modulus 3mod4?"):
        if p % 4 != 3:
            m = "MODULUS NOT 3(MOD 4)"
            raise AssertionError(m)

    with task("is the modulus prime?"):
        if not number.isPrime(p):
            m = "MODULUS NOT PRIME"
            raise AssertionError(m)

    with task("is the ElGamal group order prime?"):
        if not number.isPrime(q):
            m = "ELGAMAL GROUP ORDER NOT PRIME"
            raise AssertionError(m)

    with task("is the ElGamal group, the modulus quadratic residues?"):
        if 2*q + 1 != p:
            m = "ELGAMAL GROUP IS NOT THE MODULUS' QUADRATIC RESIDUES"
            raise AssertionError(m)

    with task("is the generator size >= 2000 bits?"):
        if log(g, 2) <= 2000:
            m = "GENERATOR SMALLER THAN 2000 BITS"
            raise AssertionError(m)

    with task("is the generator valid?"):

        if g >= p and pow(g, q, p) != 1:
            m = "INVALID ELGAMAL GROUP GENERATOR"
            raise AssertionError(m)

    if m is not None:
        teller.fail()
    else:
        teller.finish()

    return not m


def get_choice_params(nr_choices, nr_candidates=None, max_choices=None):
    if nr_candidates is None:
        nr_candidates = nr_choices
    if max_choices is None:
        max_choices = nr_candidates

    if nr_choices < 0 or nr_candidates <= 0 or max_choices <= 0:
        m = ("invalid parameters not (%d < 0 or %d <= 0 or %d <= 0)"
             % (nr_choices, nr_candidates, max_choices))
        raise ZeusError(m)

    if nr_choices > max_choices:
        m = ("Invalid number of choices (%d expected up to %d)" %
             (nr_choices, max_choices))
        raise AssertionError(m)

    return [nr_candidates, max_choices]

def validate_choices(choices, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(len(choices), nr_candidates, max_choices)

    choice_iter = iter(enumerate(choices))

    for i, choice in choice_iter:
        m = nr_candidates - i
        if choice < 0 or choice >= m:
            m = "Choice #%d: %d not in range [%d, %d]" % (i, choice, 0, m)
            raise AssertionError(m)
        m -= 1

    return 1


def permutation_to_selection(permutation):
    nr_elements = len(permutation)
    lefts = list([None]) * nr_elements
    rights = list([None]) * nr_elements
    offsets = list([None]) * nr_elements
    shifts = list([0]) * nr_elements
    maxdepth = 0

    iter_permutation = iter(permutation)
    for offset in iter_permutation:
        offsets[0] = offset
        break
    pop = 1

    selection = [offset]
    output = selection.append

    for offset in iter_permutation:
        node = 0
        shift = 0
        depth = 0

        while 1:
            node_offset = offsets[node]
            if offset < node_offset:
                shifts[node] += 1
                left = lefts[node]
                if left is None:
                    left = pop
                    pop += 1
                    offsets[left] = offset
                    lefts[node] = left
                    break
                node = left
            elif offset > node_offset:
                right = rights[node]
                shift += shifts[node] + 1
                if right is None:
                    right = pop
                    pop += 1
                    offsets[right] = offset
                    rights[node] = right
                    break
                node = right
            else:
                m = "Duplicate offset insert: %d!" % offset
                raise ValueError(m)

            depth += 1

        output(offset - shift)
        if depth > maxdepth:
            maxdepth = depth

    return selection

def get_random_selection(nr_elements, full=1):
    selection = []
    variable = not bool(full)
    append = selection.append
    for m in xrange(nr_elements, 1, -1):
        r = get_random_int(0, m+variable)
        if r == m:
            break
        append(r)
    else:
        append(0)
    return selection

def get_random_party_selection(nr_elements, nr_parties=2):
    selection = []
    party = get_random_int(0, nr_parties)
    per_party = nr_elements // nr_parties
    low = party * per_party
    high = (party + 1) * per_party
    if nr_elements - high < per_party:
        high = nr_elements

    choices = []
    append = choices.append
    r = get_random_int(0, 2**(high - low))
    for i in xrange(low, high):
        skip = r & 1
        r >>= 1
        if skip:
            continue
        append(i)

    return to_relative_answers(choices, nr_elements)

def selection_to_permutation(selection):
    nr_elements = len(selection)
    lefts = list([None]) * nr_elements
    rights = list([None]) * nr_elements
    leftpops = list([0]) * nr_elements
    pop = 1

    iter_selection = iter(reversed(selection))
    for pos in iter_selection:
        break

    for pos in iter_selection:
        node = 0
        cur = 0
        depth = 0
        while 1:
            leftpop = leftpops[node]
            newcur = cur + leftpops[node] + 1
            if pos >= newcur:
                right = rights[node]
                if right is None:
                    rights[node] = pop
                    pop += 1
                    break
                node = right
                cur = newcur
            else:
                leftpops[node] += 1
                left = lefts[node]
                if left is None:
                    lefts[node] = pop
                    pop += 1
                    break
                node = left

    maxdepth = 0
    depth = 0
    stack = [0]
    append = stack.append
    pop = stack.pop

    permutation = list([None]) * nr_elements
    offset = 0
    max_offset = nr_elements - 1

    while stack:
        node = pop()
        if node < 0:
            permutation[nr_elements + node] = offset
            offset += 1
            continue

        depth += 1
        if depth > maxdepth:
            maxdepth = depth

        right = rights[node]
        if right is not None:
            append(right)
        append(-node-1)
        left = lefts[node]
        if left is not None:
            append(left)

    return permutation

def get_random_permutation(nr_elements):
    return selection_to_permutation(get_random_selection(nr_elements, full=1))

_terms = {}

def get_term(n, k):
    if k >= n:
        return 1

    if n in _terms:
        t = _terms[n]
        if k in t:
            return t[k]
    else:
        t = {n: 1}
        _terms[n] = t

    m = k
    while 1:
        m += 1
        if m in t:
            break

    term = t[m]
    while 1:
        term *= m
        m -= 1
        t[m] = term
        if m <= k:
            break

    return term

_offsets = {}

def get_offsets(n):
    if n in _offsets:
        return _offsets[n]

    factor = 1
    offsets = []
    append = offsets.append
    sumus = 0
    i = 0
    while 1:
        sumus += get_term(n, n-i)
        append(sumus)
        if i == n:
            break
        i += 1

    _offsets[n] = offsets
    return offsets

_factors = {}

def get_factor(b, n):
    if n <= 1:
        return 1

    if b in _factors:
        t = _factors[b]
        if n in t:
            return t[n]
    else:
        t = {1: 1}
        _factors[b] = t

    i = n
    while 1:
        i -= 1
        if i in t:
            break

    f = t[i]
    while 1:
        f *= b + i
        i += 1
        t[i] = f
        if i >= n:
            break

    return f

def gamma_encode(choices, nr_candidates=None, max_choices=None):
    nr_choices = len(choices)
    nr_candidates, max_choices = \
        get_choice_params(nr_choices, nr_candidates, max_choices)
    if not nr_choices:
        return 0

    offsets = get_offsets(nr_candidates)
    sumus = offsets[nr_choices - 1]

    b = nr_candidates - nr_choices
    i = 1
    while 1:
        sumus += choices[-i] * get_factor(b, i)
        if i >= nr_choices:
            break
        i += 1

    return sumus

def gamma_encoding_max(nr_candidates, max_choices=None):
    if max_choices is None:
        max_choices = nr_candidates
    if nr_candidates <= 0:
        return 0
    choices = range(nr_candidates - 1, nr_candidates - max_choices -1, -1)
    return gamma_encode(choices, nr_candidates, max_choices)

def gamma_decode(sumus, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(nr_candidates, nr_candidates, max_choices)

    if sumus <= 0:
        return []

    offsets = get_offsets(nr_candidates)
    nr_choices = bisect_right(offsets, sumus)
    sumus -= offsets[nr_choices - 1]

    choices = []
    append = choices.append
    b = nr_candidates - nr_choices
    i = nr_choices
    while 1:
        choice, sumus = divmod(sumus, get_factor(b, i))
        append(choice)
        if i <= 1:
            break
        i -= 1

    return choices

def verify_gamma_encoding(n, completeness=1):
    choice_sets = {}
    encode_limit = get_offsets(n)[-1]
    encoded_limit = gamma_encode(range(n-1, -1, -1), n) + 1
    if encode_limit != encoded_limit:
        m = "Incorrect encode limit %d vs %d!" % (encode_limit, encoded_limit)
        raise AssertionError(m)

    for encoded in xrange(encode_limit):
        choices = tuple(gamma_decode(encoded, n))
        new_encoded = gamma_encode(choices, n)
        if new_encoded != encoded:
            m = ("Incorrect encoding %s to %d instead of %d"
                    % (choices, new_encoded, encoded))
            raise AssertionError(m)

        if not completeness:
            continue

        nr_choices = len(choices)
        if nr_choices not in choice_sets:
            choice_sets[nr_choices] = set()
        choice_set = choice_sets[nr_choices]
        if choices in choice_set:
            m = ("Duplicate decoding for %d: %s!" % (encoded, choices))
        choice_set.add(choices)

    if not completeness:
        return

    for i in xrange(n + 1):
        if i not in choice_sets:
            m = "Encoding is not bijective! missing choice set %d" % (i,)
            AssertionError(m)

        c = len(choice_sets[i])
        t = get_term(n, n-i)
        if c != t:
            m = ("Encoding is not bijective! "
                 "length-%d choices are %d instead of %d"
                 % (i, c, t))
            raise AssertionError(m)
        print "%d length-%d choices OK" % (c, i)

def factorial_encode(choices, nr_candidates=None, max_choices=None):
    nr_choices = len(choices)
    nr_candidates, max_choices = \
        get_choice_params(nr_choices, nr_candidates, max_choices)

    sumus = 0
    base = nr_candidates + 1
    factor = 1
    for choice in choices:
        choice += 1
        if choice >= base:
            m = ("Cannot vote for %dth candidate when there are only %d remaining"
                    % (choice, base - 1))
            raise ZeusError(m)
        sumus += choice * factor
        factor *= base
        base -= 1

    return sumus

def factorial_decode(encoded, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(nr_candidates, nr_candidates, max_choices)

    if encoded <= 0:
        return []

    sumus = encoded
    factors = []
    append = factors.append
    base = nr_candidates + 1
    factor = 1

    while factor <= sumus:
        append(factor)
        factor *= base
        base -= 1

    factors.reverse()
    choices = []
    append = choices.append
    for factor in factors:
        choice, sumus = divmod(sumus, factor)
        if choice == 0:
            break
        append(choice - 1)

    if sumus != 0:
        m = ("Invalid encoding %d" % (encoded,))
        raise AssertionError(m)

    nr_choices = len(choices)

    if nr_choices > max_choices:
        m = ("Decoding came up with more choices than allowed: %d > %d"
            % (nr_choices, max_choices))
        raise AssertionError(m)

    choices.reverse()
    return choices

def maxbase_encode(choices, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(len(choices), nr_candidates, max_choices)

    base = nr_candidates + 2
    sumus = 0
    e = 1
    for i, choice in enumerate(choices):
        sumus += (choice + 1) * e
        e *= base

    return sumus

def maxbase_decode(sumus, nr_candidates, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(nr_candidates, nr_candidates, max_choices)
    choices = []
    append = choices.append

    base = nr_candidates + 2
    while sumus > 0:
        sumus, choice = divmod(sumus, base)
        append(choice - 1)

    return choices

def cross_check_encodings(n):
    # verify_gamma_encoding(n)
    encode_limit = gamma_encode(range(n-1, -1, -1), n) + 1
    for e in xrange(encode_limit):
        choices = gamma_decode(e, n)
        maxbase_encoded = maxbase_encode(choices, n)
        maxbase_choices = maxbase_decode(maxbase_encoded, n)
        factorial_encoded = factorial_encode(choices, n)
        factorial_choices = factorial_decode(factorial_encoded, n)

        if (factorial_choices != maxbase_choices
            or factorial_choices != choices
            or maxbase_choices != choices):

            m = ("gamma_encoded: %d, choices mismatch: "
                 "gamma %s, maxbase %s, factorial %s"
                 % (e, choices, maxbase_choices, factorial_choices))
            raise AssertionError(m)

def gamma_decode_to_candidates(encoded, candidates):
    nr_candidates = len(candidates)
    selection = gamma_decode(encoded, nr_candidates)
    choices = to_absolute_answers(selection, nr_candidates)
    return [candidates[i] for i in choices]

def gamma_count_candidates(encoded_list, candidates):
    encoded_list = sorted(encoded_list)
    iter_encoded_list = iter(encoded_list)
    lastone = None
    counts = []
    append = counts.append

    for lastone in iter_encoded_list:
        count = 1
        break

    for encoded in chain(iter_encoded_list, [None]):
        if encoded == lastone:
            count += 1
        else:
            append([count] + gamma_decode_to_candidates(lastone, candidates))
            count = 1
            lastone = encoded

    return counts

PARTY_SEPARATOR = ': '
PARTY_OPTION_SEPARATOR = ', '

def strforce(thing, encoding='utf8'):
    if isinstance(thing, unicode):
        return thing.encode(encoding)
    return str(thing)

class FormatError(ValueError):
    pass

def parse_party_options(optstring):
    substrings = optstring.split(PARTY_OPTION_SEPARATOR, 1)

    range_str = substrings[0]

    r = range_str.split('-')
    if len(r) != 2:
        m = ("Malformed min-max choices option '%s'"
             % (range_str,))
        raise FormatError(m)

    min_choices, max_choices = r
    try:
        min_choices = int(min_choices)
        max_choices = int(max_choices)
    except ValueError:
        m = ("Malformed numbers in "
             "min-max choices option '%s'" % (name,))
        raise FormatError(m)

    group = None
    if len(substrings) == 2:
        group_str = substrings[1]
        try:
            group = int(group_str)
        except ValueError:
            m = "Malformed decimal group number in option '%s'" % (group_str,)
            raise FormatError(m)

    options = {'opt_min_choices': min_choices,
               'opt_max_choices': max_choices,
               'group': group}

    return options

def parties_from_candidates(candidates, separator=PARTY_SEPARATOR):
    parties = {}
    options = {}
    theparty = None
    group_no = 0
    nr_groups = 1

    for i, candidate in enumerate(candidates):
        candidate = strforce(candidate)
        party, sep, name = candidate.partition(separator)
        if party and not name:
            name = party
            party = ''

        if theparty is None or party != theparty:
            if party not in parties:
                opts = parse_party_options(name)
                group = opts['group']
                if group is None:
                    group = group_no
                    opts['group'] = group
                if group not in (group_no, nr_groups):
                    m = ("Party group numbers must begin at zero and "
                         "increase monotonically. Expected %d but got %d") % (
                         group_no, opts['group'])
                    raise FormatError(m)
                group_no = group
                nr_groups = group + 1
                opts['choice_index'] = i
                parties[party] = opts
                theparty = party
                continue

        parties[theparty][i] = name

    return parties, nr_groups

def gamma_decode_to_party_ballot(encoded, candidates, parties, nr_groups,
                                 separator=PARTY_SEPARATOR):

    nr_candidates = len(candidates)
    selection = gamma_decode(encoded, nr_candidates)
    choices = to_absolute_answers(selection, nr_candidates)
    voted_candidates = []
    voted_parties = []
    voted_parties_counts = {}
    last_index = -1
    thegroup = None
    party_list = None
    valid = True
    invalid_reason = None
    no_candidates_flag = 0

    for i in choices:
        if i <= last_index or no_candidates_flag:
            valid = False
            voted_candidates = None
            thegroup = None
            #print ("invalid index: %d <= %d -- choices: %s"
            #        % (i, last_index, choices))
            break

        last_index = i
        candidate = candidates[i]

        candidate = strforce(candidate)
        party, sep, name = candidate.partition(separator)
        if party and not name:
            name = party
            party = ''

        if party not in parties:
            m = "Voted party list not found"
            raise AssertionError(m)

        party_list = parties[party]
        group = party_list['group']
        if group >= nr_groups:
            m = "Group number out of limits! (%d > %d)" % (group, nr_groups)
            raise AssertionError(m)

        if thegroup is None:
            thegroup = group
            if i == party_list['choice_index']:
                no_candidates_flag = 1
            #continue

        if thegroup != group:
            valid = False
            invalid_reason = ('Choices from different groups '
                              '(%d, %d)') % (thegroup, group)
            voted_candidates = None
            thegroup = None
            break

        if not no_candidates_flag:
            if i not in party_list:
                m = "Candidate not found in party list"
                raise AssertionError(m)

            list_name = party_list[i]
            if name != list_name:
                m = "Candidate name mismatch (%s vs %s)" % (name, list_name)
                raise AssertionError(m)
                # name = party_list[i]

        if not voted_parties or voted_parties[-1] != party:
            voted_parties.append(party)
        if party not in voted_parties_counts:
            voted_parties_counts[party] = 0
        voted_parties_counts[party] += 1
        voted_candidates.append((party, name))

    if choices and valid:
        # validate number of choices for each party separately
        for party, nr_choices in voted_parties_counts.iteritems():
            party_list = parties[party]
            max_choices = party_list['opt_max_choices']
            min_choices = party_list['opt_min_choices']

            if (nr_choices < min_choices or
                nr_choices > max_choices):
                valid = False
                invalid_reason = ("Invalid min/max choices "
                                  "(min: %d, max: %d, 'choices: %d") % (
                                  min_choices, max_choices, nr_choices)
                break

    if not valid:
        voted_candidates = None
        thegroup = None

    ballot = {'parties': voted_parties,
              'group': thegroup,
              'candidates': voted_candidates,
              'invalid_reason': invalid_reason,
              'valid': valid}

    return ballot

def gamma_count_parties(encoded_list, candidates, separator=PARTY_SEPARATOR):
    invalid_count = 0
    blank_count = 0
    candidate_counters = {}
    party_counters = {}
    ballots = []
    append = ballots.append
    parties, nr_groups = parties_from_candidates(candidates,
                                                 separator=separator)
    for party, party_candidates in parties.iteritems():
        party_counters[party] = 0
        for index, candidate in party_candidates.iteritems():
            if not isinstance(index, (int, long)):
                continue
            candidate_counters[(party, candidate)] = 0

    for encoded in encoded_list:
        ballot = gamma_decode_to_party_ballot(encoded, candidates, parties,
                                              nr_groups, separator=separator)
        if not ballot['valid']:
            invalid_count += 1
            continue

        append(ballot)

        ballot_parties = ballot['parties']
        for party in ballot_parties:
            if party not in party_counters:
                m = "Cannot find initialized counter at '%s'!" % (party)
                raise AssertionError(m)
            party_counters[party] += 1

        ballot_candidates = ballot['candidates']
        filtered_candidates = []
        filtered_append = filtered_candidates.append
        for party, candidate in ballot_candidates:
            key = (party, candidate)
            if key not in candidate_counters:
                if len(ballot_candidates) != 1:
                    m = "Cannot find initialized counter at %s!" % (key,)
                    raise FormatError()
                opts = parse_party_options(candidate)
                filtered_append((party, ''))
                continue
            else:
                filtered_append((party, candidate))
            candidate_counters[key] += 1

        ballot['candidates'] = filtered_candidates

        if not ballot_parties and not ballot_candidates:
            blank_count += 1

    party_counts = [(-v, k) for k, v in party_counters.iteritems()]
    party_counts.sort()
    fmt = "%s" + separator + "%s"
    party_counts = [(-v, k) for v, k in party_counts]
    candidate_counts = [(-v, fmt % k)
                        for k, v in candidate_counters.iteritems()]
    candidate_counts.sort()
    candidate_counts = [(-v, k) for v, k in candidate_counts]

    results = {'ballots': ballots,
               'parties': parties,
               'party_counts': party_counts,
               'candidate_counts': candidate_counts,
               'ballot_count': len(ballots) + invalid_count,
               'blank_count': blank_count,
               'invalid_count': invalid_count}
    return results

def candidates_to_parties(candidates, separator=PARTY_SEPARATOR):
    parties = {}
    options = {}
    separator = strforce(separator)
    for candidate in candidates:
        party, sep, name = candidate.partition(separator)
        if not name:
            party = ''
            name = party
        party = strforce(party)
        name = strforce(name)

def chooser(answers, candidates):
    candidates = list(candidates)
    nr_candidates = len(candidates)
    validate_choices(answers, nr_candidates, nr_candidates)

    rank = []
    append = rank.append
    for answer in answers:
        append(candidates.pop(answer))

    return [rank, candidates]

def strbin_to_int_mul(string):
    # lsb
    s = 0
    base = 1
    for c in string:
        s += ord(c) * base
        base *= 256

    return s

def strbin_to_int_native(string):
    return int.from_bytes(string)

if PYTHON_MAJOR == 3:
    strbin_to_int = strbin_to_int_native
else:
    strbin_to_int = strbin_to_int_mul

def bit_iterator(nr, infinite=True):
    while nr:
        yield nr & 1
        nr >>= 1

    if not infinite:
        return

    while 1:
        yield 0

def get_random_int(minimum, ceiling):
    top = ceiling - minimum
    nr_bits = bit_length(top)
    nr_bytes = (nr_bits - 1) / 8 + 1
    strbin = _random_generator_file.read(nr_bytes)
    num = strbin_to_int(strbin)
    shift = bit_length(num) - nr_bits
    if shift > 0:
        num >>= shift
    if num >= top:
        num -= top
    return num + minimum

def get_random_element(modulus, generator, order):
    exponent = get_random_int(2, order)
    element = pow(generator, exponent, modulus)
    return element

def validate_element(modulus, generator, order, element):
    legendre = pow(element, order, modulus)
    return legendre == 1

def encrypt(message, modulus, generator, order, public, randomness=None):
    if randomness is None:
        randomness = get_random_int(1, order)
    message = message + 1
    if message >= order:
        m = "message is too large"
        raise ValueError(m)

    legendre = pow(message, order, modulus)
    if legendre != 1:
        message = -message % modulus
    alpha = pow(generator, randomness, modulus)
    beta = (message * pow(public, randomness, modulus)) % modulus
    return [alpha, beta, randomness]

def decrypt_with_randomness(modulus, generator, order, public,
                            beta, secret):
    encoded = pow(public, secret, modulus)
    encoded = inverse(encoded, modulus)
    encoded = (encoded * beta) % modulus
    if encoded >= order:
        encoded = -encoded % modulus
    return encoded - 1

def decrypt_with_decryptor(modulus, generator, order, beta, decryptor):
    decryptor = inverse(decryptor, modulus)
    message = (decryptor * beta) % modulus
    legendre = pow(message, order, modulus)
    if legendre not in (0, 1, -1 % modulus):
        m = "This should be impossible. Invalid encryption."
        raise AssertionError(m)
    if message >= order:
        message = -message % modulus
    return message - 1

def decrypt(modulus, generator, order, secret, alpha, beta):
    decryptor = pow(alpha, secret, modulus)
    return decrypt_with_decryptor(modulus, generator, order, beta, decryptor)


def numbers_hash(numbers):
    h = sha256()
    update = h.update
    for num in numbers:
        update("%x:" % num)
    return h.hexdigest()

def texts_hash(texts):
    h = sha256()
    texts_gen = ((t.encode('utf8') if not isinstance(t, str) else t)
                 for t in texts)
    h.update('\x00'.join(texts_gen))
    return h.digest()

def number_from_texts_hash(modulus, *texts):
    digest = texts_hash(texts)
    number = strbin_to_int(digest) % modulus
    return number

def number_from_numbers_hash(modulus, *numbers):
    digest = numbers_hash(numbers)
    number = strbin_to_int(digest) % modulus
    return number

def element_from_texts_hash(modulus, generator, order, *texts):
    num_hash = numbers_hash((modulus, generator, order))
    digest = texts_hash((num_hash,) + texts)
    number = strbin_to_int(digest) % order
    element = pow(generator, number, modulus)
    return element

def element_from_elements_hash(modulus, generator, order, *elements):
    digest = numbers_hash((modulus, generator, order) + elements)
    number = strbin_to_int(digest) % order
    element = pow(generator, number, modulus)
    return element

def prove_dlog_zeus(modulus, generator, order, power, dlog,
                    *extra_challenge_input):
    randomness = get_random_int(2, order)
    commitment = pow(generator, randomness, modulus)
    challenge = element_from_elements_hash(modulus, generator, order,
                                           power, commitment,
                                           *extra_challenge_input)
    response = (randomness + challenge * dlog) % order
    return [commitment, challenge, response]

def verify_dlog_power_zeus(modulus, generator, order, power,
                           commitment, challenge, response,
                           *extra_challenge_input):
    _challenge = element_from_elements_hash(modulus, generator, order,
                                            power, commitment,
                                            *extra_challenge_input)
    if _challenge != challenge:
        return 0
    return (pow(generator, response, modulus)
            == ((commitment * pow(power, challenge, modulus)) % modulus))

def prove_dlog_helios(modulus, generator, order, power, dlog):
    randomness = get_random_int(2, order)
    commitment = pow(generator, randomness, modulus)
    challenge = int(sha1(str(commitment)).hexdigest(), 16) % order
    response = (randomness + challenge * dlog) % order
    return [commitment, challenge, response]

def verify_dlog_power_helios(modulus, generator, order, power,
                             commitment, challenge, response):
    _challenge = int(sha1(str(commitment)).hexdigest(), 16) % order
    if _challenge != challenge:
        return 0
    return (pow(generator, response, modulus)
            == ((commitment * pow(power, challenge, modulus)) % modulus))

prove_dlog = prove_dlog_zeus
verify_dlog_power = verify_dlog_power_zeus

def generate_keypair(modulus, generator, order, secret_key=None):
    if secret_key is None:
        secret_key = get_random_element(modulus, generator, order)
    elif not validate_element(modulus, generator, order, secret_key):
        m = "Invalid secret key is not a quadratic residue"
        raise AssertionError(m)

    public = pow(generator, secret_key, modulus)
    commitment, challenge, response = \
        prove_dlog(modulus, generator, order, public, secret_key)
    return [secret_key, public, commitment, challenge, response]

def validate_public_key(modulus, generator, order, public_key,
                        commitment, challenge, response):
    if not validate_element(modulus, generator, order, public_key):
        return 0

    return verify_dlog_power(modulus, generator, order, public_key,
                             commitment, challenge, response)

def prove_ddh_tuple_zeus(modulus, generator, order,
                    message, base_power, message_power, exponent):
    randomness = get_random_int(2, order)

    base_commitment = pow(generator, randomness, modulus)
    message_commitment = pow(message, randomness, modulus)

    args = (modulus, generator, order, base_power, base_commitment,
                     message, message_power, message_commitment)
    challenge = element_from_elements_hash(*args)
    response = (randomness + challenge * exponent) % order
    return [base_commitment, message_commitment, challenge, response]

def verify_ddh_tuple_zeus(modulus, generator, order,
                     message, base_power, message_power,
                     base_commitment, message_commitment,
                     challenge, response):
    args = (modulus, generator, order, base_power, base_commitment,
            message, message_power, message_commitment)
    _challenge = element_from_elements_hash(*args)
    if _challenge != challenge:
        return 0

    b = (base_commitment * pow(base_power, challenge, modulus)) % modulus
    if b != pow(generator, response, modulus):
        return 0

    m = (message_commitment * pow(message_power, challenge, modulus)) % modulus
    if m != pow(message, response, modulus):
        return 0

    return 1

def prove_ddh_tuple_helios(modulus, generator, order,
                    message, base_power, message_power, exponent):
    randomness = get_random_int(2, order)

    base_commitment = pow(generator, randomness, modulus)
    message_commitment = pow(message, randomness, modulus)

    args = (str(base_commitment), str(message_commitment))
    challenge = int(sha1(','.join(args)).hexdigest(), 16) % order
    response = (randomness + challenge * exponent) % order
    return [base_commitment, message_commitment, challenge, response]

def verify_ddh_tuple_helios(modulus, generator, order,
                     message, base_power, message_power,
                     base_commitment, message_commitment,
                     challenge, response):
    args = (str(base_commitment), str(message_commitment))
    _challenge = int(sha1(','.join(args)).hexdigest(), 16) % order
    if _challenge != challenge:
        return 0

    b = (base_commitment * pow(base_power, challenge, modulus)) % modulus
    if b != pow(generator, response, modulus):
        return 0

    m = (message_commitment * pow(message_power, challenge, modulus)) % modulus
    if m != pow(message, response, modulus):
        return 0

    return 1

prove_ddh_tuple = prove_ddh_tuple_helios
verify_ddh_tuple = verify_ddh_tuple_helios

def prove_encryption(modulus, generator, order, alpha, beta, secret):
    """Prove ElGamal encryption"""
    ret = prove_dlog(modulus, generator, order, alpha, secret, beta)
    commitment, challenge, response = ret
    return [commitment, challenge, response]

def verify_encryption(modulus, generator, order, alpha, beta,
                      commitment, challenge, response):
    """Verify ElGamal encryption"""
    ret = verify_dlog_power(modulus, generator, order, alpha,
                            commitment, challenge, response, beta)
    return ret

def reencrypt(modulus, generator, order, public, alpha, beta, secret=None):
    key = get_random_int(3, order) if secret is None else secret
    new_alpha = (alpha * pow(generator, key, modulus)) % modulus
    new_beta = (beta * pow(public, key, modulus)) % modulus
    if secret is None:
        return [alpha, beta, key]
    return [alpha, beta]

def prove_reencryption(modulus, generator, order, public,
                       a0, b0, a1, b1, secret):
    base = generator
    base_power = a0
    message = public
    message_power = (b1 * inverse(b0, modulus)) % modulus
    args = (modulus, generator, order, public,
            base, base_power, message, message_power, secret)
    return prove_ddh_tuple(*args)

def verify_reencryption(modulus, generator, order, public,
                        a0, b0, a1, b1,
                        a_commitment, b_commitment, challenge, response):
    base = generator
    base_power = a0
    message = public
    message_power = (b1 * inverse(b0, modulus)) % modulus
    args = (modulus, generator, order, public,
            base, base_power, message, message_power,
            a_commitment, b_commitment, challenge, response)
    return verify_ddh_tuple(*args)

def sign_element(element, modulus, generator, order, key):
    """Compute ElGamal signature"""
    while 1:
        w = 2 * get_random_int(3, order) - 1
        r = pow(generator, w, modulus)
        modulus1 = modulus - 1
        w = inverse(w, modulus1)
        s = (w * ((element - (r*key) % modulus1))) % modulus1
        if s != 0:
            break
    return {'r': r, 's': s, 'e': element,
            'crypto':  {'modulus': modulus,
                        'generator': generator,
                        'order': order}}

def verify_element_signature(signature, modulus, generator, order, public):
    """Verify ElGamal signature"""
    r = signature['r']
    s = signature['s']
    e = signature['e']
    if 'crypto' in signature:
        crypto = signature['crypto']
        if (crypto['modulus'] != modulus or
            crypto['generator'] != generator or
            crypto['order'] != order):
            return 0

    if r <= 0 or r >= modulus:
        return 0

    x0 = (pow(public, r, modulus) * pow(r, s, modulus)) % modulus
    x1 = pow(generator, e, modulus)
    if x0 != x1:
        return 0

    return 1

def sign_text_message(text_message, modulus, generator, order, key):
    element = element_from_texts_hash(modulus, generator, order, text_message)
    signature = sign_element(element, modulus, generator, order, key)
    signature['m'] = text_message
    return signature

def verify_text_signature(signature, modulus, generator, order, public):
    text_message = signature['m']
    element = element_from_texts_hash(modulus, generator, order, text_message)
    if element != signature['e']:
        return 0
    return verify_element_signature(signature,
                                    modulus, generator, order, public)


def encode_selection(selection, nr_candidates=None):
    if nr_candidates is None:
        nr_candidates = len(selection)
    return gamma_encode(selection, nr_candidates, nr_candidates)

def vote_from_encoded(modulus, generator, order, public,
                      voter, encoded, nr_candidates,
                      audit_code=None, publish=None):

    alpha, beta, rnd = encrypt(encoded, modulus, generator, order, public)
    proof = prove_encryption(modulus, generator, order, alpha, beta, rnd)
    commitment, challenge, response = proof
    eb = {'modulus': modulus,
          'generator': generator,
          'order': order,
          'public': public,
          'alpha': alpha,
          'beta': beta,
          'commitment': commitment,
          'challenge': challenge,
          'response': response}

    fingerprint = numbers_hash((modulus, generator, alpha, beta,
                                commitment, challenge, response))
    vote = {'voter': voter,
            'fingerprint': fingerprint,
            'encrypted_ballot': eb}

    if audit_code:
        vote['audit_code'] = audit_code

    if publish:
        vote['voter_secret'] = rnd

    return vote

def sign_vote(vote, trustees, candidates, comments,
              modulus, generator, order, public, secret):
    eb = vote['encrypted_ballot']
    election = eb['public']
    fingerprint = vote['fingerprint']
    previous_vote = vote['previous']
    index = vote['index']
    status = vote['status']

    m00 = status
    m01 = (V_FINGERPRINT + "%s") % fingerprint
    m02 = (V_INDEX + "%s") % (("%d" % index) if index is not None else 'NONE')
    m03 = (V_PREVIOUS + "%s") % (previous_vote,)
    m04 = (V_ELECTION + "%x") % election
    m05 = (V_ZEUS_PUBLIC + "%x") % public
    m06 = (V_TRUSTEES + "%s") % (' '.join(("%x" % t) for t in trustees),)
    m07 = (V_CANDIDATES + "%s") % (' % '.join(("%s" % c) for c in candidates),)
    m08 = (V_MODULUS + "%x") % modulus
    m09 = (V_GENERATOR + "%x") % generator
    m10 = (V_ORDER + "%x") % order
    m11 = (V_ALPHA + "%x") % eb['alpha']
    m12 = (V_BETA + "%x") % eb['beta']
    m13 = (V_COMMITMENT + "%x") % eb['commitment']
    m14 = (V_CHALLENGE + "%x") % eb['challenge']
    m15 = (V_RESPONSE + "%x") % eb['response']
    m16 = (V_COMMENTS + "%s") % (comments,)
    message = '\n'.join((m00, m01, m02, m03, m04, m05, m06, m07,
                         m08, m09, m10, m11, m12, m13, m14, m15, m16))
    signature = sign_text_message(message, modulus, generator, order, secret)
    text = signature['m']
    text += '\n-----------------\n'
    text += '%x\n%x\n%x\n' % (signature['e'], signature['r'], signature['s'])
    return text

def verify_vote_signature(vote_signature):
    message, sep, e, r, s, null = vote_signature.rsplit('\n', 5)
    e = int(e, 16)
    r = int(r, 16)
    s = int(s, 16)
    (m00, m01, m02, m03, m04, m05, m06, m07,
     m08, m09, m10, m11, m12, m13, m14, m15, m16) = message.split('\n', 16)
    if (not (m00.startswith(V_CAST_VOTE)
             or m00.startswith(V_AUDIT_REQUEST)
             or m00.startswith(V_PUBLIC_AUDIT)
             or m00.startswith(V_PUBLIC_AUDIT_FAILED))
        or not m01.startswith(V_FINGERPRINT)
        or not m02.startswith(V_INDEX)
        or not m03.startswith(V_PREVIOUS)
        or not m04.startswith(V_ELECTION)
        or not m05.startswith(V_ZEUS_PUBLIC)
        or not m06.startswith(V_TRUSTEES)
        or not m07.startswith(V_CANDIDATES)
        or not m08.startswith(V_MODULUS)
        or not m09.startswith(V_GENERATOR)
        or not m10.startswith(V_ORDER)
        or not m11.startswith(V_ALPHA)
        or not m12.startswith(V_BETA)
        or not m13.startswith(V_COMMITMENT)
        or not m14.startswith(V_CHALLENGE)
        or not m15.startswith(V_RESPONSE)
        or not m16.startswith(V_COMMENTS)):

        m = "Invalid vote signature structure!"
        raise ZeusError(m)

    status = m00
    fingerprint = m01[len(V_FINGERPRINT):]
    index_str   = m02[len(V_INDEX):]
    if index_str == 'NONE':
        index = None
    elif index_str.isdigit():
        index = int(index_str)
    else:
        m = "Invalid vote index '%s'" % (index_str,)
        raise ZeusError(m)
    previous    = m03[len(V_PREVIOUS):]
    public      = int(m04[len(V_ELECTION):], 16)
    zeus_public = int(m05[len(V_ZEUS_PUBLIC):], 16)
    _m06 = m06[len(V_TRUSTEES):]
    trustees    = [int(x, 16) for x in _m06.split(' ')] if _m06 else []
    _m07 = m07[len(V_CANDIDATES):]
    candidates  = _m07.split(' % ')
    modulus     = int(m08[len(V_MODULUS):], 16)
    generator   = int(m09[len(V_GENERATOR):], 16)
    order       = int(m10[len(V_ORDER):], 16)
    alpha       = int(m11[len(V_ALPHA):], 16)
    beta        = int(m12[len(V_BETA):], 16)
    commitment  = int(m13[len(V_COMMITMENT):], 16)
    challenge   = int(m14[len(V_CHALLENGE):], 16)
    response    = int(m15[len(V_RESPONSE):], 16)
    comments    = m16[len(V_COMMENTS):]

    signature = {'m': message, 'r': r, 's': s, 'e': e}
    if not verify_text_signature(signature, modulus, generator, order,
                                 zeus_public):
        m = "Invalid vote signature!"
        raise ZeusError(m)

    if (index is not None and
        not verify_encryption(modulus, generator, order, alpha, beta,
                              commitment, challenge, response)):
        m = "Invalid vote encryption proof in valid signature!"
        raise AssertionError(m)

    crypto = [modulus, generator, order]

    eb = {'alpha': alpha, 'beta': beta,
          'public': public,
          'commitment': commitment,
          'challenge': challenge,
          'response': response}

    vote = {'status': status,
            'fingerprint': fingerprint,
            'previous': previous,
            'index': index,
            'public': public,
            'encrypted_ballot': eb}

    return vote, crypto, trustees, candidates, comments

def to_relative_answers(choices, nr_candidates):
    """
    Answer choices helper, convert absolute indexed answers to relative.

    e.g. for candidates [A, B, C] absolute choices [1, 2, 0] will be converted
    to [1, 1, 0].
    """
    relative = []
    candidates = list(range(nr_candidates))
    choices = [candidates.index(c) for c in choices]
    for choice in choices:
        index = candidates.index(choice)
        relative.append(index)
        candidates.remove(choice)

    return relative

def to_absolute_answers(choices, nr_candidates):
    """
    Inverts `to_relative_answers` result.
    """
    absolute_choices = []
    candidates = list(range(nr_candidates))
    tmp_cands = candidates[:]
    for choice in choices:
        choice = tmp_cands[choice]
        absolute_choices.append(candidates.index(choice))
        tmp_cands.remove(choice)
    return absolute_choices


def compute_mix_challenge(cipher_mix):
    hasher = sha256()
    update = hasher.update

    update("%x" % cipher_mix['modulus'])
    update("%x" % cipher_mix['generator'])
    update("%x" % cipher_mix['order'])
    update("%x" % cipher_mix['public'])

    original_ciphers = cipher_mix['original_ciphers']
    for cipher in original_ciphers:
        update("%x" % cipher[ALPHA])
        update("%x" % cipher[BETA])

    mixed_ciphers = cipher_mix['mixed_ciphers']
    for cipher in mixed_ciphers:
        update("%x" % cipher[ALPHA])
        update("%x" % cipher[BETA])

    for ciphers in cipher_mix['cipher_collections']:
        for cipher in ciphers:
            update("%x" % cipher[ALPHA])
            update("%x" % cipher[BETA])

    challenge = hasher.hexdigest()
    return challenge

def get_random_permutation_gamma(nr_elements):
    if nr_elements <= 0:
        return []
    low = list([0]) * nr_elements
    high = range(nr_elements - 1, -1, -1)
    max_low = gamma_encode(low, nr_elements)
    max_high = gamma_encode(high, nr_elements)
    rand = get_random_int(max_low, max_high + 1)
    selection = gamma_decode(rand, nr_elements)
    return selection

def shuffle_ciphers(modulus, generator, order, public, ciphers,
                    teller=None, report_thresh=128, async_channel=None):
    nr_ciphers = len(ciphers)
    mixed_offsets = get_random_permutation(nr_ciphers)
    mixed_ciphers = list([None]) * nr_ciphers
    mixed_randoms = list([None]) * nr_ciphers
    count = 0

    for i in xrange(nr_ciphers):
        alpha, beta = ciphers[i]
        alpha, beta, secret = reencrypt(modulus, generator, order,
                                        public, alpha, beta)
        mixed_randoms[i] = secret
        o = mixed_offsets[i]
        mixed_ciphers[o] = [alpha, beta]
        count += 1
        if count >= report_thresh:
            if teller:
                teller.advance(count)
            if async_channel:
                async_channel.send_shared(count, wait=1)
            count = 0

    if count:
        if teller:
            teller.advance(count)
        if async_channel:
            async_channel.send_shared(count, wait=1)
    return [mixed_ciphers, mixed_offsets, mixed_randoms]

def mix_ciphers(ciphers_for_mixing, nr_rounds=MIN_MIX_ROUNDS,
                teller=_teller, nr_parallel=0):
    p = ciphers_for_mixing['modulus']
    g = ciphers_for_mixing['generator']
    q = ciphers_for_mixing['order']
    y = ciphers_for_mixing['public']

    original_ciphers = ciphers_for_mixing['mixed_ciphers']
    nr_ciphers = len(original_ciphers)

    if nr_parallel > 0:
        Random.atfork()
        async = AsyncController(parallel=nr_parallel)
        async_shuffle_ciphers = async.make_async(shuffle_ciphers)

    teller.task('Mixing %d ciphers for %d rounds' % (nr_ciphers, nr_rounds))

    cipher_mix = {'modulus': p, 'generator': g, 'order': q, 'public': y}
    cipher_mix['original_ciphers'] = original_ciphers

    with teller.task('Producing final mixed ciphers', total=nr_ciphers):
        shuffled = shuffle_ciphers(p, g, q, y, original_ciphers, teller=teller)
        mixed_ciphers, mixed_offsets, mixed_randoms = shuffled
        cipher_mix['mixed_ciphers'] = mixed_ciphers

    total = nr_ciphers * nr_rounds
    with teller.task('Producing ciphers for proof', total=total):
        if nr_parallel > 0:
            channels = [async_shuffle_ciphers(p, g, q, y, original_ciphers,
                                              teller=None)
                        for _ in xrange(nr_rounds)]

            count = 0
            while count < total:
                nr = async.receive_shared()
                teller.advance(nr)
                count += nr

            collections = [channel.receive(wait=1) for channel in channels]
            async.shutdown()
        else:
            collections = [shuffle_ciphers(p, g, q, y,
                                           original_ciphers, teller=teller)
                           for _ in xrange(nr_rounds)]

        unzipped = [list(x) for x in zip(*collections)]
        cipher_collections, offset_collections, random_collections = unzipped
        cipher_mix['cipher_collections'] = cipher_collections
        cipher_mix['random_collections'] = random_collections
        cipher_mix['offset_collections'] = offset_collections

    with teller.task('Producing cryptographic hash challenge'):
        challenge = compute_mix_challenge(cipher_mix)
        cipher_mix['challenge'] = challenge

    bits = bit_iterator(int(challenge, 16))

    with teller.task('Answering according to challenge', total=nr_rounds):
        for i, bit in zip(xrange(nr_rounds), bits):
            ciphers = cipher_collections[i]
            offsets = offset_collections[i]
            randoms = random_collections[i]

            if bit == 0:
                # Nothing to do, we just publish our offsets and randoms
                pass
            elif bit == 1:
                # The image is given. We now have to prove we know
                # the both this image's and mixed_ciphers' offsets/randoms
                # by providing # new offsets/randoms so one can reencode
                # this image # to end up with mixed_ciphers.
                # original_ciphers -> image
                # original_ciphers -> mixed_ciphers
                # Provide image -> mixed_ciphers
                new_offsets = list([None]) * nr_ciphers
                new_randoms = list([None]) * nr_ciphers

                for j in xrange(nr_ciphers):
                    cipher_random = randoms[j]
                    cipher_offset = offsets[j]
                    mixed_random = mixed_randoms[j]
                    mixed_offset = mixed_offsets[j]

                    new_offsets[cipher_offset] = mixed_offset
                    new_random = (mixed_random - cipher_random) % q
                    new_randoms[cipher_offset] = new_random

                offset_collections[i] = new_offsets
                random_collections[i] = new_randoms
                del ciphers, offsets, randoms
            else:
                m = "This should be impossible. Something is broken."
                raise AssertionError(m)

            teller.advance()
    teller.finish('Mixing')

    return cipher_mix


def verify_mix_round(i, bit, original_ciphers, mixed_ciphers,
                     ciphers, randoms, offsets,
                     teller=None, report_thresh=128, async_channel=None):
    nr_ciphers = len(original_ciphers)
    count = 0
    if bit == 0:
        for j in xrange(nr_ciphers):
            original_cipher = original_ciphers[j]
            a = original_cipher[ALPHA]
            b = original_cipher[BETA]
            r = randoms[j]
            new_a, new_b = reencrypt(p, g, q, y, a, b, r)
            o = offsets[j]
            cipher = ciphers[o]
            if new_a != cipher[ALPHA] or new_b != cipher[BETA]:
                m = ('MIXING VERIFICATION FAILED AT '
                     'ROUND %d CIPHER %d' % (i, j))
                raise AssertionError(m)
            count += 1
            if count >= report_thresh:
                if async_channel:
                    async_channel.send_shared(count)
                if teller:
                    teller.advance(count)
                count = 0
    elif bit == 1:
        for j in xrange(nr_ciphers):
            cipher = ciphers[j]
            a = cipher[ALPHA]
            b = cipher[BETA]
            r = randoms[j]
            new_a, new_b = reencrypt(p, g, q, y, a, b, r)
            o = offsets[j]
            mixed_cipher = mixed_ciphers[o]
            if new_a != mixed_cipher[ALPHA] or new_b != cipher[BETA]:
                m = ('MIXING VERIFICATION FAILED AT '
                     'ROUND %d CIPHER %d' % (i, j))
                raise AssertionError(m)
            count += 1
            if count >= report_thresh:
                if async_channel:
                    async_channel.send_shared(count)
                if teller:
                    teller.advance(count)
                count = 0
    else:
        m = "This should be impossible. Something is broken."
        raise AssertionError(m)

    if count:
        if async_channel:
            async_channel.send_shared(count)
        if teller:
            teller.advance(count)


def verify_cipher_mix(cipher_mix, teller=_teller, nr_parallel=0):
    try:
        p = cipher_mix['modulus']
        g = cipher_mix['generator']
        q = cipher_mix['order']
        y = cipher_mix['public']

        original_ciphers = cipher_mix['original_ciphers']
        mixed_ciphers = cipher_mix['mixed_ciphers']
        challenge = cipher_mix['challenge']
        cipher_collections = cipher_mix['cipher_collections']
        offset_collections = cipher_mix['offset_collections']
        random_collections = cipher_mix['random_collections']
    except KeyError, e:
        m = "Invalid cipher mix format"
        raise ZeusError(m, e)

    nr_ciphers = len(original_ciphers)
    nr_rounds = len(cipher_collections)
    teller.task('Verifying mixing of %d ciphers for %d rounds'
                 % (nr_ciphers, nr_rounds))

    if (len(offset_collections) != nr_rounds or
        len(random_collections) != nr_rounds):
        m = "Invalid cipher mix format: collections not of the same size!"
        raise ZeusError(m)

    #if not validate_cryptosystem(p, g, q, teller):
    #    m = "Invalid cryptosystem"
    #    raise AssertionError(m)

    if nr_parallel > 0:
        async = AsyncController(parallel=nr_parallel)
        async_verify_mix_round = async.make_async(verify_mix_round)

    total = nr_rounds * nr_ciphers
    with teller.task('Verifying ciphers', total=total):
        channels = []
        append = channels.append
        for i, bit in zip(xrange(nr_rounds), bit_iterator(int(challenge, 16))):
            ciphers = cipher_collections[i]
            randoms = random_collections[i]
            offsets = offset_collections[i]
            if nr_parallel <= 0:
                verify_mix_round(i, bit, original_ciphers,
                                 mixed_ciphers, ciphers,
                                 randoms, offsets,
                                 teller=teller)
            else:
                append(async_verify_mix_round(i, bit,
                                              original_ciphers,
                                              mixed_ciphers,
                                              ciphers, randoms, offsets,
                                              teller=None))
        if nr_parallel > 0:
            count = 0
            while count < total:
                nr = async.receive_shared(wait=1)
                teller.advance(nr)
                count += nr

            for channel in channels:
                channel.receive(wait=1)

            async.shutdown()

    teller.finish('Verifying mixing')
    return 1


def compute_decryption_factors1(modulus, generator, order, secret, ciphers,
                                teller=_teller):
    factors = []
    public = pow(generator, secret, modulus)
    append = factors.append
    nr_ciphers = len(ciphers)
    with teller.task("Computing decryption factors", total=nr_ciphers):
        for alpha, beta in ciphers:
            factor = pow(alpha, secret, modulus)
            proof = prove_ddh_tuple(modulus, generator, order,
                                    alpha, public, factor, secret)
            append([factor, proof])
            teller.advance()
    return factors

def compute_some_decryption_factors(modulus, generator, order,
                                    secret, public, ciphers,
                                    teller=None, async_channel=None,
                                    report_thresh=16):
    count = 0
    factors = []
    append = factors.append

    for alpha, beta in ciphers:
        factor = pow(alpha, secret, modulus)
        proof = prove_ddh_tuple(modulus, generator, order,
                                alpha, public, factor, secret)
        append([factor, proof])
        count += 1
        if count >= report_thresh:
            if teller is not None:
                teller.advance(count)
            if async_channel is not None:
                async_channel.send_shared(count)
            count = 0

    if count:
        if teller is not None:
            teller.advance(count)
        if async_channel is not None:
            async_channel.send_shared(count)

    return factors

def compute_decryption_factors(modulus, generator, order, secret, ciphers,
                               teller=_teller, nr_parallel=1):
    if nr_parallel <= 0:
        return compute_decryption_factors1(modulus, generator, order,
                                           secret, ciphers, teller=teller)

    public = pow(generator, secret, modulus)
    nr_ciphers = len(ciphers)
    async = AsyncController(parallel=nr_parallel)
    compute_some = async.make_async(compute_some_decryption_factors)

    d, q = divmod(nr_ciphers, nr_parallel)
    if not d:
        d = nr_ciphers
    index = range(0, nr_ciphers, d)
    with teller.task("Computing decryption factors", total=nr_ciphers):
        channels = [compute_some(modulus, generator, order,
                                 secret, public, ciphers[i:i+d])
                    for i in index]
        count = 0
        while count < nr_ciphers:
            nr = async.receive_shared(wait=1)
            teller.advance(nr)
            count += nr

        factors = []
        for c in channels:
            r = c.receive(wait=1)
            factors.extend(r)

    async.shutdown()
    return factors

def verify_decryption_factors1(modulus, generator, order, public,
                               ciphers, factors, teller=_teller):
    nr_ciphers = len(ciphers)
    if nr_ciphers != len(factors):
        return 0

    with teller.task("Verifying decryption factors", total=nr_ciphers):
        for cipher, factor in izip(ciphers, factors):
            alpha, beta = cipher
            factor, proof = factor
            if not verify_ddh_tuple(modulus, generator, order, alpha, public,
                                    factor, *proof):
                teller.fail()
                return 0
            teller.advance()
    return 1

def verify_some_decryption_factors(modulus, generator, order,
                                   public, ciphers, factors,
                                   teller=None, async_channel=None,
                                   report_thresh=16):
    count = 0
    for cipher, factor in izip(ciphers, factors):
        alpha, beta = cipher
        factor, proof = factor
        if not verify_ddh_tuple(modulus, generator, order, alpha, public,
                                factor, *proof):
            if async_channel is not None:
                async_channel.send_shared(-1)
            if teller is not None:
                teller.fail()
            return 0

        count += 1
        if count >= report_thresh:
            if teller is not None:
                teller.advance(count)
            if async_channel is not None:
                async_channel.send_shared(count)
            count = 0

    if count:
        if teller is not None:
            teller.advance(count)
        if async_channel is not None:
            async_channel.send_shared(count)

    return 1

def verify_decryption_factors(modulus, generator, order, public,
                              ciphers, factors, teller=_teller,
                              nr_parallel=1):
    if nr_parallel <= 0:
        return verify_decryption_factors1(modulus, generator, order, public,
                                          ciphers, factors, teller=teller)

    nr_ciphers = len(ciphers)
    if nr_ciphers != len(factors):
        return 0

    async = AsyncController(parallel=nr_parallel)
    verify_some = async.make_async(verify_some_decryption_factors)

    d, q = divmod(nr_ciphers, nr_parallel)
    if not d:
        d = nr_ciphers
    index = range(0, nr_ciphers, d)
    with teller.task("Verifying decryption factors", total=nr_ciphers):
        channels = [verify_some(modulus, generator, order,
                                public, ciphers[i:i+d], factors[i:i+d])
                    for i in index]

        count = 0
        while count < nr_ciphers:
            nr = async.receive_shared(wait=1)
            if nr < 0:
                async.shutdown()
                teller.fail()
                return 0
            teller.advance(nr)
            count += nr

    async.shutdown()
    return 1

def combine_decryption_factors(modulus, factor_collection):
    if not factor_collection:
        return
    master_factors = []
    append = master_factors.append
    for decryption_factors in izip(*factor_collection):
        master_factor = 1
        for factor, proof in decryption_factors:
            master_factor = (master_factor * factor) % modulus
        append(master_factor)
    return master_factors


class ZeusCoreElection(object):
    stage = 'UNINITIALIZED'

    def __init__(self, cryptosystem=crypto_args(_default_crypto),
                       teller=_teller, **kw):
        self.teller = teller
        self.do_init_creating()
        self.do_init_voting()
        self.do_init_mixing()
        self.do_init_decrypting()
        self.do_init_finished()
        self.init_creating(cryptosystem)
        if 'nr_parallel' not in kw:
            kw['nr_parallel'] = 0
        self.set_option(**kw)

    def do_set_stage(self, stage):
        self.stage = stage

    def do_get_stage(self):
        return self.stage

    def do_assert_stage(self, stage):
        if self.stage != stage:
            m = "Election must be in stage '%s' not '%s'" % (stage, self.stage)
            raise ZeusError(m)

    ### CREATING BACKEND API ###

    def do_init_creating(self):
        self.cryptosys = None
        self.candidates = []
        self.voters = {}
        self.audit_codes = {}
        self.options = {}
        self.zeus_secret = None
        self.zeus_public = None
        self.zeus_key_proof = None
        self.trustees = {}
        self.election_public = None

    def do_store_cryptosystem(self, modulus, generator, order):
        self.cryptosys = [modulus, generator, order]

    def do_get_cryptosystem(self):
        return self.cryptosys

    def do_store_zeus_key(self, secret, public,
                                commitment, challenge, response):
        self.zeus_secret = secret
        self.zeus_public = public
        self.zeus_key_proof = [commitment, challenge, response]

    def do_get_zeus_secret(self):
        return self.zeus_secret

    def do_get_zeus_public(self):
        return self.zeus_public

    def do_get_zeus_key_proof(self):
        return self.zeus_key_proof

    def do_store_election_public(self, public):
        self.election_public = public

    def do_get_election_public(self):
        return self.election_public

    def do_get_public_election_key(self):
        args = self.cryptosys + [self.election_public]
        return pk_from_args(*args)

    def do_get_zeus_key(self):
        args = self.cryptosys
        args += [self.zeus_secret, self.zeus_public]
        args += self.zeus_key_proof
        return sk_from_args(*args)

    def do_set_option(self, kw):
        self.options.update(kw)

    def do_get_option(self, name):
        options = self.options
        return options[name] if name in options else None

    def do_get_options(self):
        return dict(self.options)

    def do_store_trustee(self, public, commitment, challenge, response):
        trustees = self.trustees
        trustees[public] = [commitment, challenge, response]

    def do_get_trustee(self, public):
        trustees = self.trustees
        if public not in trustees:
            return None
        return trustees[public]

    def do_get_trustees(self):
        return self.trustees

    def do_store_candidates(self, names):
        self.candidates += names

    def do_get_candidates(self):
        return self.candidates

    def do_store_voters(self, voters):
        self.voters.update(voters)

    def do_get_voter(self, voter_key):
        voters = self.voters
        if voter_key not in voters:
            return None
        return voters[voter_key]

    def do_get_voters(self):
        return dict(self.voters)

    def do_store_voter_audit_codes(self, audit_codes):
        self.audit_codes.update(audit_codes)

    def do_get_voter_audit_codes(self, voter_key):
        audit_codes = self.audit_codes
        if voter_key not in audit_codes:
            return None
        return audit_codes[voter_key]

    def do_get_all_voter_audit_codes(self):
        return dict(self.audit_codes)

    ### VOTING BACKEND API ###

    def do_init_voting(self):
        self.cast_vote_index = []
        self.votes = {}
        self.cast_votes = {}
        self.audit_requests = {}
        self.audit_publications = []
        self.excluded_voters = {}

    def do_store_audit_publication(self, fingerprint):
        self.audit_publications.append(fingerprint)

    def do_get_audit_publications(self):
        return list(self.audit_publications)

    def do_store_audit_request(self, fingerprint, voter_key):
        audit_requests = self.audit_requests
        audit_requests[fingerprint] = voter_key

    def do_get_audit_request(self, fingerprint):
        audit_requests = self.audit_requests
        if fingerprint not in audit_requests:
            return None
        return audit_requests[fingerprint]

    def do_get_audit_requests(self):
        return dict(self.audit_requests)

    def do_store_votes(self, votes):
        for vote in votes:
            fingerprint = vote['fingerprint']
            self.votes[fingerprint] = vote

    def do_get_vote(self, fingerprint):
        return self.votes.get(fingerprint, None)

    def do_get_votes(self):
        return dict(self.votes)

    def do_index_vote(self, fingerprint):
        cast_vote_index = self.cast_vote_index
        index = len(cast_vote_index)
        cast_vote_index.append(fingerprint)
        return index

    def do_get_index_vote(self, index):
        cast_vote_index = self.cast_vote_index
        if index >= len(cast_vote_index):
            return None
        return cast_vote_index[index]

    def do_get_vote_index(self):
        return list(self.cast_vote_index)

    def do_append_vote(self, voter_key, fingerprint):
        cast_votes = self.cast_votes
        if voter_key not in cast_votes:
            cast_votes[voter_key] = []
        cast_votes[voter_key].append(fingerprint)

    def do_get_cast_votes(self, voter_key):
        cast_votes = self.cast_votes
        if voter_key not in cast_votes:
            return None
        return cast_votes[voter_key]

    def do_get_all_cast_votes(self):
        return dict(self.cast_votes)

    def do_store_excluded_voter(self, voter_key, reason):
        self.excluded_voters[voter_key] = reason

    def do_get_excluded_voters(self):
        return dict(self.excluded_voters)

    def custom_audit_publication_message(self, vote):
        return ''

    def custom_audit_request_message(self, vote):
        return ''

    def custom_cast_vote_message(self, vote):
        return ''

    ### MIXING BACKEND API ###

    def do_init_mixing(self):
        self.mixes = []

    def do_store_mix(self, mix):
        self.mixes.append(mix)

    def do_get_last_mix(self):
        mixes = self.mixes
        if not mixes:
            return None
        return mixes[-1]

    def do_get_all_mixes(self):
        return list(self.mixes)

    ### DECRYPTING BACKEND API ###

    def do_init_decrypting(self):
        self.trustee_factors = {}
        self.zeus_decryption_factors = []

    def do_store_trustee_factors(self, trustee_factors):
        trustee_public = trustee_factors['trustee_public']
        factors = trustee_factors['decryption_factors']
        self.trustee_factors[trustee_public] = factors

    def do_get_all_trustee_factors(self):
        return dict(self.trustee_factors)

    def do_store_zeus_factors(self, zeus_decryption_factors):
        self.zeus_decryption_factors = zeus_decryption_factors

    def do_get_zeus_factors(self):
        return self.zeus_decryption_factors

    ### FINISHED BACKEND API ###

    def do_init_finished(self):
        self.results = None

    def do_store_results(self, plaintexts):
        self.results = list(plaintexts)

    def do_get_results(self):
        return self.results

    ### GENERIC IMPLEMENTATION ###

    def set_option(self, **kw):
        #self.do_assert_stage('CREATING')
        return self.do_set_option(kw)

    def get_option(self, name):
        return self.do_get_option(name)

    def init_creating(self, cryptosystem):
        modulus, generator, order = cryptosystem
        self.do_store_cryptosystem(modulus, generator, order)
        self.do_set_stage('CREATING')

    @classmethod
    def new_at_creating(cls, cryptosystem=_default_crypto,
                             teller=_teller, **kw):
        self = cls(cryptosystem, teller=teller, **kw)
        return self

    def create_zeus_key(self, secret_key=None):
        # No need to assert creating, all other stages must have a key
        if self.do_get_zeus_secret() is not None:
            m = "Zeus key already initialized"
            raise ZeusError(m)

        modulus, generator, order = self.do_get_cryptosystem()
        key_info = generate_keypair(modulus, generator, order,
                                    secret_key=secret_key)
        secret, public, commitment, challenge, response = key_info

        self.do_store_zeus_key(secret, public, commitment, challenge, response)
        return key_info

    def invalidate_election_public(self):
        self.do_store_election_public(None)

    def compute_election_public(self):
        trustees = self.do_get_trustees()
        public = self.do_get_zeus_public()
        modulus, generator, order = self.do_get_cryptosystem()
        for trustee in trustees:
            public = (public * trustee) % modulus
        self.do_store_election_public(public)

    def add_trustee(self, trustee_public_key, trustee_key_proof):
        self.do_assert_stage('CREATING')
        p, g, q = self.do_get_cryptosystem()
        args = [p, g, q, trustee_public_key] + trustee_key_proof
        if not validate_public_key(*args):
            m = "Cannot validate key"
            raise ZeusError(m)

        election_public = self.do_get_election_public()
        if election_public is None:
            election_public = 1
        modulus, generator, order = self.do_get_cryptosystem()
        self.invalidate_election_public()
        self.do_store_trustee(trustee_public_key, *trustee_key_proof)
        self.compute_election_public()

    def reprove_trustee(self, trustee_public_key, trustee_key_proof):
        self.do_assert_stage('CREATING')
        if not self.do_get_trustee(trustee_public_key):
            m = "Trustee does not exist!"
            raise ZeusError(m)

        return self.add_trustee(trustee_public_key, trustee_key_proof)

    def add_candidates(self, *names):
        candidates = set(self.do_get_candidates())
        for name in names:
            if name in candidates:
                m = "Candidate '%s' already exists!"
                raise ZeusError(m)
            if '%' in name:
                m = "Candidate name cannot contain character '%%'"
                raise ZeusError(m)
            if '\n' in name:
                m = "Candidate name cannot contain character '\\n'"
                raise ZeusError(m)

        self.do_store_candidates(names)

    def add_voters(self, *names):
        name_set = set(self.do_get_voters().values())
        intersection = name_set.intersection(names)
        if intersection:
            m = "Voter '%s' already exists!" % (intersection.pop(),)
            raise ZeusError(m)

        new_voters = {}
        voter_audit_codes = {}
        for name in names:
            voter_key = "%x" % get_random_int(2, VOTER_KEY_CEIL)
            new_voters[voter_key] = name
            audit_codes = list(get_random_int(2, VOTER_SLOT_CEIL)
                               for _ in xrange(3))
            voter_audit_codes[voter_key] = audit_codes
        self.do_store_voters(new_voters)
        self.do_store_voter_audit_codes(voter_audit_codes)

    def validate_creating(self):
        teller = self.teller
        teller.task("Validating stage: 'CREATING'")

        with teller.task("Validating Candidates"):
            candidates = self.do_get_candidates()
            nr_candidates = len(candidates)
            if nr_candidates <= 1:
                m = "Not enough candidates for election!"
                raise ZeusError(m)
            if len(set(candidates)) != nr_candidates:
                m = "Duplicate candidates!"
                raise ZeusError(m)
            teller.notice("%d candidates" % nr_candidates)

        with teller.task("Validating Voters"):
            voters = self.do_get_voters()
            if not voters:
                m = "No voters for election!"
                raise ZeusError(m)
            with teller.task("Validating Voter Names"):
                names = voters.values()
                nr_names = len(names)
                if len(set(names)) != nr_names:
                    m = "Duplicate voter names!"
                    raise ZeusError(m)
                del names
            with teller.task("Validating Voter Keys"):
                keys = voters.keys()
                nr_keys = len(keys)
                if len(set(keys)) != nr_keys:
                    m = "Duplicate voter keys!"
                    raise ZeusError(m)

            with teller.task("Validating voter audit_codes"):
                audit_codes = self.do_get_all_voter_audit_codes()
                if audit_codes.keys() != keys:
                    m = "Slots do not correspond to voters!"
                    raise ZeusError(m)
                audit_code_set = set(tuple(v) for v in audit_codes.values())
                if len(audit_code_set) < nr_keys / 2:
                    m = "Slots don't have enough variation!"
                    raise ZeusError(m)
            teller.notice("%d voters" % nr_keys)

        modulus, generator, order = self.do_get_cryptosystem()
        if not validate_cryptosystem(modulus, generator, order, teller=teller):
            m = "Invalid Cryptosystem!"
            raise AssertionError(m)

        with teller.task("Validating Zeus Election Key"):
            secret = self.do_get_zeus_secret()
            public = self.do_get_zeus_public()
            key_proof = self.do_get_zeus_key_proof()
            if secret is not None:
                if not validate_element(modulus, generator, order, secret):
                    m = "Invalid Secret Key"
                    raise AssertionError(m)
                _public = pow(generator, secret, modulus)
                if _public != public:
                    m = "Invalid Public Key"
                    raise AssertionError(m)
            if not validate_public_key(modulus, generator, order,
                                       public, *key_proof):
                m = "Invalid Key Proof"
                raise AssertionError(m)

        trustees = self.do_get_trustees()
        nr_trustees = len(trustees)
        with teller.task("Validating Trustees", total=nr_trustees):
            for public, proof in trustees.iteritems():
                commitment, challenge, response = proof
                if not validate_public_key(modulus, generator, order, public,
                                           commitment, challenge, response):
                    m = "Invalid Trustee: %x" % public
                    raise AssertionError(m)
                teller.advance()

        election_public = self.do_get_election_public()
        with teller.task("Validating Election Public Key"):
            _election_public = self.do_get_zeus_public()
            for public in trustees:
                _election_public = (_election_public * public) % modulus
            if _election_public != election_public:
                m = "Invalid Election Public Key!"
                raise AssertionError(m)

        teller.finish('Validating stage')

    def export_creating(self):
        stage = self.do_get_stage()
        if stage in ('UNINITIALIZED', 'CREATING'):
            m = "Stage 'CREATING' must have passed before it can be exported"
            raise ZeusError(m)

        creating = {}
        creating['candidates'] = self.do_get_candidates()
        creating['voters'] = self.do_get_voters()
        creating['cryptosystem'] = self.do_get_cryptosystem()
        creating['zeus_public'] = self.do_get_zeus_public()
        creating['zeus_key_proof'] = self.do_get_zeus_key_proof()
        creating['election_public'] = self.do_get_election_public()
        creating['trustees'] = self.do_get_trustees()
        creating['voters'] = self.do_get_voters()
        creating['voter_audit_codes'] = self.do_get_all_voter_audit_codes()
        return creating

    def set_voting(self):
        stage = self.do_get_stage()
        if stage == 'VOTING':
            m = "Already in stage 'VOTING'"
            raise ZeusError(m)
        if stage != 'CREATING':
            m = "Cannot transition from stage '%s' to 'VOTING'" % (stage,)
            raise ZeusError(m)

        if not self.get_option('no_verify'):
            self.validate_creating()
        self.do_set_stage('VOTING')

    @classmethod
    def new_at_voting(cls, voting, teller=_teller, **kw):
        self = cls.new_at_creating(teller=teller, **kw)
        #self.do_set_option(voting.get('options', {}))
        self.do_store_candidates(voting['candidates'])
        self.do_store_cryptosystem(*voting['cryptosystem'])
        self.do_store_zeus_key(None,
                               voting['zeus_public'],
                               *voting['zeus_key_proof'])
        self.do_store_election_public(voting['election_public'])
        for t in voting['trustees'].iteritems():
            trustee_public_key, trustee_key_proof = t
            trustee_public_key = int(trustee_public_key)
            self.do_store_trustee(trustee_public_key, *trustee_key_proof)
        for voter_key, reason in voting['excluded_voters'].iteritems():
            self.do_store_excluded_voter(voter_key, reason)
        self.do_store_voters(voting['voters'])
        self.do_store_voter_audit_codes(voting['voter_audit_codes'])
        self.do_set_stage('VOTING')
        return self

    def validate_submitted_vote(self, vote):
        keys = set(('voter', 'encrypted_ballot', 'fingerprint',
                    'audit_code', 'voter_secret'))
        nr_keys = len(keys)
        vote_keys = vote.keys()
        if len(vote_keys) > len(keys):
            m = "Extra vote contents"
            raise ZeusError(m)

        if len(set(keys).union(vote_keys)) != nr_keys:
            m = "Invalid Vote: Extra vote contents"
            raise ZeusError(m)

        if 'voter' not in vote:
            m = "'voter' field missing from vote"
            raise ZeusError(m)

        if 'encrypted_ballot' not in vote:
            m = "'encrypted_ballot' field missing from vote"
            raise ZeusError(m)

        if 'fingerprint' not in vote:
            m = "'fingerprint' field missing from vote"
            raise ZeusError(m)

        eb = vote['encrypted_ballot']

        keys = set(('modulus', 'generator', 'order', 'public',
                    'alpha', 'beta',
                    'commitment', 'challenge', 'response'))
        if set(eb.keys()) != keys:
            m = "Invalid encrypted ballot format!"
            raise ZeusError(m)

        eb = dict(eb)
        vote = dict(vote)
        vote['encrypted_ballot'] = eb

        crypto = self.do_get_cryptosystem()
        eb_crypto = [eb.pop('modulus'), eb.pop('generator'), eb.pop('order')]
        if crypto != eb_crypto:
            m = "Invalid encrypted ballot cryptosystem"
            raise ZeusError(m)

        alpha = eb['alpha']
        beta = eb['beta']
        commitment = eb['commitment']
        challenge = eb['challenge']
        response = eb['response']

        modulus, generator, order = crypto
        if not verify_encryption(modulus, generator, order, alpha, beta,
                                 commitment, challenge, response):
            m = "Invalid vote encryption proof!"
            raise ZeusError(m)

        fingerprint = numbers_hash((modulus, generator, alpha, beta,
                                    commitment, challenge, response))
        if fingerprint != vote['fingerprint']:
            m = "Invalid vote fingerprint!"
            raise ZeusError(m)

        stored = self.do_get_vote(fingerprint)
        if stored is not None:
            m = "Vote has already been cast!"
            raise ZeusError(m)

        return vote

    def sign_vote(self, vote, comments):
        modulus, generator, order = self.do_get_cryptosystem()
        candidates = self.do_get_candidates()
        public = self.do_get_zeus_public()
        secret = self.do_get_zeus_secret()
        trustees = list(self.do_get_trustees())
        trustees.sort()
        signature = sign_vote(vote, trustees, candidates, comments,
                              modulus, generator, order, public, secret)
        self.verify_vote_signature(signature)
        return signature

    def verify_vote_signature(self, vote_signature):
        vote_info = verify_vote_signature(vote_signature)
        vote, vote_crypto, vote_trustees, vote_candidates, comments = vote_info
        trustees = list(self.do_get_trustees())
        trustees.sort()
        crypto = self.do_get_cryptosystem()
        public = self.do_get_election_public()
        eb = vote['encrypted_ballot']
        if crypto != vote_crypto:
            m = "Cannot verify vote signature: Cryptosystem mismatch!"
            raise ZeusError(m)
        if public != eb['public']:
            m = "Cannot verify vote signature: Election public mismatch!"
            raise ZeusError(m)
        if set(trustees) != set(vote_trustees):
            m = "Vote signature: trustees mismatch!"
            raise AssertionError(m)
        candidates = self.do_get_candidates()
        if candidates != vote_candidates:
            m = "Vote signature: candidates mismatch!"
            raise AssertionError(m)
        return vote

    def validate_vote(self, signed_vote):
        election = signed_vote['encrypted_ballot']['public']
        fingerprint = signed_vote['fingerprint']
        index = signed_vote['index']
        previous = signed_vote['previous']

        if election != self.do_get_election_public():
            m = "Election mismatch in vote!"
            raise ZeusError(m)

        stored = self.do_get_vote(fingerprint)
        if not stored:
            m = "Cannot find verified vote [%s] in store!" % (fingerprint,)
            raise AssertionError(m)

        if index:
            indexed_fingerprint = self.do_get_index_vote(index)
            if indexed_fingerprint != fingerprint:
                m = ("Corrupt vote index: "
                     "signed vote [%s] with index %d not found: "
                     "index %d holds vote [%s]"
                     % (fingerprint, index, index, indexed_fingerprint))
                raise AssertionError(m)

        if previous and self.do_get_vote(previous) is None:
            m = "Cannot find valid previous vote [%s] in store!" % (previous,)
            raise AssertionError(m)

    def verify_vote(self, vote):
        if 'signature' not in vote:
            m = "No signature found in vote!"
            raise ZeusError(m)
        signature = vote['signature']
        signed_vote = self.verify_vote_signature(signature)
        return self.validate_vote(signed_vote)

    def cast_vote(self, vote):
        self.do_assert_stage('VOTING')
        fingerprint = vote['fingerprint']
        voter_key = vote['voter']
        voter = self.do_get_voter(voter_key)
        audit_codes = self.do_get_voter_audit_codes(voter_key)
        if not voter and not audit_codes:
            m = "Invalid voter key!"
            raise ZeusError(m)

        if not voter or not audit_codes:
            m = "Voter audit_code inconsistency! Invalid Election."
            raise AssertionError(m)

        audit_request = self.do_get_audit_request(fingerprint)
        voter_secret = vote['voter_secret'] if 'voter_secret' in vote else None
        voter_audit_code = vote['audit_code'] if 'audit_code' in vote else None

        if voter_secret:
            # This is an audit publication
            if not voter_audit_code:
                m = "Invalid audit vote publication! No audit_code given."
                raise ZeusError(m)
            if voter_audit_code in audit_codes:
                m = "Invalid audit vote publication! Invalid audit_code given."
                raise ZeusError(m)
            if voter_key != audit_request:
                m = "Cannot find prior audit request for publish request!"
                raise ZeusError(m)
            vote['previous'] = ''
            vote['index'] = None
            vote['status'] = V_PUBLIC_AUDIT
            missing, failed = self.verify_audit_votes(votes=[vote])
            if missing:
                m = "This should have been impossible"
                raise AssertionError(m)
            if failed:
                vote['status'] = V_PUBLIC_AUDIT_FAILED
            comments = self.custom_audit_publication_message(vote)
            signature = self.sign_vote(vote, comments)
            vote['signature'] = signature
            self.do_store_audit_publication(fingerprint)
            self.do_store_votes((vote,))
            return signature

        if not voter_audit_code:
            skip_audit = self.do_get_option('skip_audit')
            if skip_audit or skip_audit is None:
                # skip auditing for submission simplicity
                voter_audit_code = audit_codes[0]
            else:
                m = ("Invalid vote submission! "
                     "No audit_code given but skip_audit is disabled")
                raise ZeusError(m)

        if voter_audit_code not in audit_codes:
            # This is an audit request submission
            if audit_request:
                m = ("Audit request for vote [%s] already exists!"
                    % (fingerprint,))
                raise ZeusError(m)

            vote['previous'] = ''
            vote['index'] = None
            vote['status'] = V_AUDIT_REQUEST
            comments = self.custom_audit_request_message(vote)
            signature = self.sign_vote(vote, comments)
            vote['signature'] = signature
            self.do_store_audit_request(fingerprint, voter_key)
            self.do_store_votes((vote,))
            return signature

        # This is a genuine vote submission
        if self.do_get_vote(fingerprint):
            m = "Vote [%s] already cast!" % (fingerprint,)
            raise ZeusError(m)

        cast_votes = self.do_get_cast_votes(voter_key)
        vote_limit = self.get_option('vote_limit')
        if vote_limit and len(cast_votes) >= vote_limit:
            m = "Maximum allowed number of votes reached: %d" % vote_limit
            raise ZeusError(m)

        if not cast_votes:
            previous_fingerprint = ''
        else:
            previous_fingerprint = cast_votes[-1]

        vote = self.validate_submitted_vote(vote)

        vote['previous'] = previous_fingerprint
        vote['status'] = V_CAST_VOTE
        index = self.do_index_vote(fingerprint)
        vote['index'] = index
        comments = self.custom_cast_vote_message(vote)
        signature = self.sign_vote(vote, comments)
        vote['signature'] = signature
        self.do_append_vote(voter_key, fingerprint)
        self.do_store_votes((vote,))
        # DANGER: commit all data to disk before giving a signature out!
        return signature

    def verify_audit_votes(self, votes=None):
        teller = self.teller
        if not votes:
            audit_reqs = self.do_get_audit_requests()
            get_vote = self.do_get_vote
            votes = [dict(get_vote(f)) for f in audit_reqs]
            add_plaintext = 0
        else:
            add_plaintext = 1
        failed = []
        missing = []
        modulus, generator, order = self.do_get_cryptosystem()
        public = self.do_get_election_public()
        nr_candidates = len(self.do_get_candidates())
        max_encoded = gamma_encoding_max(nr_candidates)

        with teller.task("Verifying audit votes", total=len(votes)):
            for vote in votes:
                if not 'voter_secret' in vote:
                    missing.append(vote)
                    m = "[%s] public audit secret not found"
                    teller.notice(m, vote['fingerprint'])
                    teller.advance()
                    continue

                voter_secret = vote['voter_secret']

                eb = vote['encrypted_ballot']
                if not verify_encryption(modulus, generator, order,
                                         eb['alpha'], eb['beta'],
                                         eb['commitment'],
                                         eb['challenge'],
                                         eb['response']):
                    failed.append(vote)
                    m = "failed audit [%s]"
                    teller.notice(m, vote['fingerprint'])
                    teller.advance()
                    continue

                alpha = pow(generator, voter_secret, modulus)
                if alpha != eb['alpha']:
                    failed.append(vote)
                    m = "[%s] ciphertext mismatch: wrong key"
                    teller.notice(m, vote['fingerprint'])
                    teller.advance()
                    continue

                beta = eb['beta']
                encoded = decrypt_with_randomness(modulus, generator, order,
                                                  public, beta, voter_secret)
                if encoded > max_encoded:
                    m = "[%s] invalid plaintext!"
                    teller.notice(m, vote['fingerprint'])
                    failed.append(vote)
                if add_plaintext:
                    vote['plaintext'] = encoded
                teller.advance()

        return missing, failed

    def exclude_voter(self, voter_key, reason=''):
        stage = self.do_get_stage()
        if stage in ('FINISHED', 'DECRYPTING', 'MIXING'):
            m = "Cannot exclude voter in stage '%s'!" % (stage,)
            raise ZeusError(m)
        self.do_store_excluded_voter(voter_key, reason)

    def validate_voting(self):
        teller = self.teller
        teller.task("Validating state: 'VOTING'")

        all_cast_votes = self.do_get_all_cast_votes()
        all_votes = self.do_get_votes()
        nr_votes = len(all_votes)
        with teller.task("Validating cast votes", total=nr_votes):
            for voter_key, cast_votes in all_cast_votes.iteritems():
                previous = ''
                for cast_vote in cast_votes:
                    if cast_vote not in all_votes:
                        m = ("Vote %s/[%s] not found in vote archive!"
                            % (voter_key, cast_vote))
                        raise AssertionError(m)
                    vote = all_votes[cast_vote]
                    vote_previous = vote['previous']
                    if vote_previous != previous:
                        m = ("Vote %s/[%s] previous '%s' != '%s'"
                            % (voter_key, cast_vote, vote_previous, previous))
                        raise AssertionError(m)
                    self.verify_vote(vote)
                    del all_votes[cast_vote]
                    teller.advance()
                    previous = cast_vote

        audit_pubs = self.do_get_audit_publications()
        nr_audit_pubs = len(audit_pubs)
        with teller.task("Validating audit publications", total=nr_audit_pubs):
            all_audit_requests = self.do_get_audit_requests()
            for audit_vote in audit_pubs:
                if audit_vote not in all_votes:
                    m = "Audit vote [%s] not found in vote archive!" % (audit_vote,)
                    raise AssertionError(m)
                vote = all_votes[audit_vote]
                self.verify_vote(vote)
                msg = vote['signature']
                if msg.startswith(V_PUBLIC_AUDIT):
                    if vote['fingerprint'] not in all_audit_requests:
                        m = "Public audit vote not found in requests!"
                        raise AssertionError(m)
                else:
                    m = "Invalid audit vote!"
                    raise AssertionError(m)
                teller.advance()

        all_audit_requests = self.do_get_audit_requests()
        nr_all_audit_requests = len(all_audit_requests)
        with teller.task("Validating audit requests",
                         total=nr_all_audit_requests):
            for audit_request, voter_key in all_audit_requests.iteritems():
                if audit_request not in all_votes:
                    m = ("Audit request %s/[%s] not found in vote archive!"
                        % (voter_key, audit_request))
                    raise AssertionError(m)
                vote = all_votes[audit_request]
                self.verify_vote(vote)
                del all_votes[audit_request]
                teller.advance()

            current = teller.get_current()

        if all_votes:
            m = "%d unaccounted votes in archive!" % len(all_votes)
            raise AssertionError(m)

        excluded = self.do_get_excluded_voters()
        nr_excluded = len(excluded)
        with teller.task("Validating excluded voters", total=nr_excluded):
            for voter_key, reason in excluded.iteritems():
                voter = self.do_get_voter(voter_key)
                if voter is None:
                    m = "Nonexistent excluded voter '%s'!"
                    raise AssertionError(m)
                teller.advance()

        teller.finish('Validating state')

    def export_voting(self):
        stage = self.do_get_stage()
        if stage in ('UNINITIALIZED', 'CREATING'):
            m = ("Stage 'VOTING' must have been reached "
                 "before it can be exported")
            raise ZeusError(m)

        voting = self.export_creating()
        voting['votes'] = self.do_get_votes().values()
        voting['cast_vote_index'] = self.do_get_vote_index()
        voting['cast_votes'] = self.do_get_all_cast_votes()
        voting['audit_requests'] = self.do_get_audit_requests()
        voting['audit_publications'] = self.do_get_audit_publications()
        voting['excluded_voters'] = self.do_get_excluded_voters()
        return voting

    def extract_votes_for_mixing(self):
        vote_index = self.do_get_vote_index()
        nr_votes = len(vote_index)
        scratch = list([None]) * nr_votes
        counted = list([None]) * nr_votes
        do_get_vote = self.do_get_vote
        vote_count = 0
        excluded_voters = self.do_get_excluded_voters()
        excluded_votes = set()
        update = excluded_votes.update
        for voter_key, reason in excluded_voters.iteritems():
            update(self.do_get_cast_votes(voter_key))

        for i, fingerprint in enumerate(vote_index):
            vote = dict(do_get_vote(fingerprint))
            index = vote['index']
            if i != index:
                m = "Index mismatch %d != %d. Corrupt index!" % (i, index)
                raise AssertionError(m)

            if fingerprint in excluded_votes:
                continue

            eb = vote['encrypted_ballot']
            _vote = [eb['alpha'], eb['beta']]
            scratch[i] = _vote
            counted[i] = fingerprint
            previous = vote['previous']
            if not previous:
                vote_count += 1
                continue

            previous_vote = dict(do_get_vote(previous))
            previous_index = previous_vote['index']
            if previous_index >= index or scratch[previous_index] is None:
                m = "Inconsistent index!"
                raise AssertionError(m)
            if previous_vote['voter'] != vote['voter']:
                m = ("Voter mismatch '%s' vs '%s'!"
                    % (previous_vote['voter'], vote['voter']))
                raise AssertionError(m)

            scratch[previous_index] = None
            counted[previous_index] = None

        votes_for_mixing = [v for v in scratch if v is not None]
        counted_list = [c for c in counted if c is not None]
        nr_votes = len(votes_for_mixing)
        if nr_votes != vote_count:
            m = ("Vote count mismatch %d != %d. Corrupt index!"
                % (nr_votes, vote_count))
            raise AssertionError(m)

        crypto = self.do_get_cryptosystem()
        modulus, generator, order = crypto
        public = self.do_get_election_public()
        mix = {'modulus': modulus,
               'generator': generator,
               'order': order,
               'public': public,
               'original_ciphers': votes_for_mixing,
               'mixed_ciphers': votes_for_mixing}
        return mix, counted_list

    def set_mixing(self):
        stage = self.do_get_stage()
        if stage == 'MIXING':
            m = "Already in stage 'MIXING'"
            raise ZeusError(m)
        if stage != 'VOTING':
            m = "Cannot transition from stage '%s' to 'MIXING'" % (stage,)
            raise ZeusError(m)

        if not self.get_option('no_verify'):
            self.validate_voting()
        votes_for_mixing, counted_list = self.extract_votes_for_mixing()
        self.do_store_mix(votes_for_mixing)
        self.do_set_stage('MIXING')

    @classmethod
    def new_at_mixing(cls, mixing, teller=_teller, **kw):
        self = cls.new_at_voting(mixing, teller=teller, **kw)
        self.do_store_votes(mixing['votes'])
        for fingerprint in mixing['cast_vote_index']:
            self.do_index_vote(fingerprint)
        for voter_key, fingerprints in mixing['cast_votes'].iteritems():
            for fingerprint in fingerprints:
                self.do_append_vote(voter_key, fingerprint)
        for fingerprint, voter_key in mixing['audit_requests'].iteritems():
            self.do_store_audit_request(fingerprint, voter_key)
        for fingerprint in mixing['audit_publications']:
            self.do_store_audit_publication(fingerprint)
        votes_for_mixing, counted_list = self.extract_votes_for_mixing()
        self.do_store_mix(votes_for_mixing)
        self.do_set_stage('MIXING')
        return self

    def get_last_mix(self):
        self.do_assert_stage('MIXING')
        last_mix = dict(self.do_get_last_mix())
        last_mix.pop('offset_collections', None)
        last_mix.pop('random_collections', None)
        last_mix.pop('cipher_collections', None)
        return last_mix

    def validate_mix(self, mix):
        teller = self.teller
        nr_parallel = self.get_option('nr_parallel')
        if nr_parallel is None:
            nr_parallel = 2
        modulus = mix['modulus']
        generator = mix['generator']
        order = mix['order']

        if 'cipher_collections' not in mix:
            m = "Invalid mix: no proof!"
            raise ZeusError(m)

        min_rounds = self.get_option('min_mix_rounds') or MIN_MIX_ROUNDS
        nr_rounds = len(mix['cipher_collections'])
        if nr_rounds < min_rounds:
            m = ("Invalid mix: fewer than required mix rounds: %d < %d"
                % (nr_rounds, min_rounds))
            raise ZeusError(m)

        crypto = self.do_get_cryptosystem()
        if [modulus, generator, order] != crypto:
            m = "Invalid mix: cryptosystem mismatch!"
            raise ZeusError(m)

        original_ciphers = mix['original_ciphers']
        last_mix = self.do_get_last_mix()
        if original_ciphers != last_mix['mixed_ciphers']:
            m = "Invalid mix: not a mix of latest ciphers!"
            raise ZeusError(m)

        if not verify_cipher_mix(mix, teller=teller, nr_parallel=nr_parallel):
            m = "Invalid mix: proof verification failed!"
            raise ZeusError(m)

    def add_mix(self, mix):
        self.do_assert_stage('MIXING')
        self.validate_mix(mix)
        self.do_store_mix(mix)

    def validate_mixing(self):
        teller = self.teller
        nr_parallel = self.get_option('nr_parallel')
        if nr_parallel is None:
            nr_parallel = 2
        teller.task("Validating state: 'MIXING'")

        crypto = self.do_get_cryptosystem()
        previous = None
        mixes = self.do_get_all_mixes()
        min_mixes = self.get_option('min_mixes') or 1
        nr_mixes = len(mixes) - 1
        if nr_mixes < min_mixes:
            m = "Not enough mixes: %d. Minimum %d." % (nr_mixes, min_mixes)
            raise AssertionError(m)

        with teller.task("Validate mixes", total=nr_mixes):
            for i, mix in enumerate(mixes):
                if [mix['modulus'], mix['generator'], mix['order']] != crypto:
                    m = "Mix data corruption: Cryptosystem mismatch!"
                    raise AssertionError(m)

                if previous:
                    previous_mixed = previous['mixed_ciphers']
                    original_ciphers = mix['original_ciphers']
                    if original_ciphers != previous_mixed:
                        m = ("Invalid mix %d/%d: Does not mix previous one"
                            % (i+1, nr_mixes))
                        raise AssertionError(m)

                    if not verify_cipher_mix(mix, teller=teller,
                                             nr_parallel=nr_parallel):
                        m = "Invalid mix proof"
                        raise AssertionError(m)

                    teller.advance()
                else:
                    t = self.extract_votes_for_mixing()
                    votes_for_mixing, counted_list = t
                    original_ciphers = mix['original_ciphers']
                    if len(original_ciphers) != len(counted_list):
                        m = "Invalid extraction for mixing!"
                        raise AssertionError(m)
                    if original_ciphers != votes_for_mixing['original_ciphers']:
                        m = "Invalid first mix: Does not mix votes in archive!"
                        raise AssertionError(m)

                    counted_set = set(counted_list)
                    del counted_list

                    excluded = self.do_get_excluded_voters()
                    for voter_key, reason in excluded.iteritems():
                        cast_votes = self.do_get_cast_votes(voter_key)
                        for fingerprint in cast_votes:
                            if fingerprint in counted_set:
                                m = ("Invalid extraction for mixing: "
                                     "vote [%s] from voter '%s' not excluded!"
                                     % (fingerprint, voter_key))
                                raise AssertionError(m)
                    del votes_for_mixing
                    del excluded

                previous = mix

        teller.finish('Validating state')

    def export_mixing(self):
        stage = self.do_get_stage()
        if stage in ('UNINITIALIZED', 'CREATING', 'VOTING', 'MIXING'):
            m = "Stage 'MIXING' must have passed before it can be exported"
            raise ZeusError(m)

        mixing = self.export_voting()
        mixes = self.do_get_all_mixes()[1:]
        mixing['mixes'] = mixes
        return mixing

    def set_decrypting(self):
        stage = self.do_get_stage()
        if stage == 'DECRYPTING':
            m = "Already in stage 'DECRYPTING'"
            raise ZeusError(m)
        if stage != 'MIXING':
            m = "Cannot transition from stage '%s' to 'DECRYPTING'" % (stage,)
            raise ZeusError(m)

        if not self.get_option('no_verify'):
            self.validate_mixing()

        self.compute_zeus_factors()
        self.do_set_stage('DECRYPTING')

    def export_decrypting(self):
        stage = self.do_get_stage()
        if stage not in ('FINISHED'):
            m = "Stage 'DECRYPTING' must have passed before it can be exported"
            raise ZeusError(m)

        decrypting = self.export_mixing()
        all_factors = self.do_get_all_trustee_factors()
        trustee_factors = [{'trustee_public': k, 'decryption_factors': v}
                           for k, v in all_factors.iteritems()]
        decrypting['trustee_factors'] = trustee_factors
        zeus_factors = self.do_get_zeus_factors()
        decrypting['zeus_decryption_factors'] = zeus_factors
        return decrypting

    @classmethod
    def new_at_decrypting(cls, decrypting, teller=_teller, **kw):
        self = cls.new_at_mixing(decrypting, teller=teller, **kw)
        for mix in decrypting['mixes']:
            self.do_store_mix(mix)
        if 'trustee_factors' in decrypting:
            all_trustee_factors = decrypting['trustee_factors']
            for trustee_factors in all_trustee_factors:
                self.do_store_trustee_factors(trustee_factors)
        if 'zeus_decryption_factors' in decrypting:
            zeus_factors = decrypting['zeus_decryption_factors']
            self.do_store_zeus_factors(decrypting['zeus_decryption_factors'])
        self.do_set_stage('DECRYPTING')
        return self

    def get_mixed_ballots(self):
        #self.do_assert_stage('DECRYPTING')
        last_mix = self.do_get_last_mix()
        if last_mix is None:
            return []
        return list(last_mix['mixed_ciphers'])

    def validate_trustee_factors(self, trustee_factors):
        teller = self.teller
        if ('trustee_public' not in trustee_factors or
            'decryption_factors' not in trustee_factors):
            m = "Invalid trustee factors format"
            raise ZeusError(m)

        trustee_public = trustee_factors['trustee_public']
        trustees = self.do_get_trustees()
        if trustee_public not in trustees:
            m = "Invalid trustee factors: No such trustee!"
            raise ZeusError(m)

        crypto = self.do_get_cryptosystem()
        modulus = trustee_factors['modulus']
        generator = trustee_factors['generator']
        order = trustee_factors['order']
        if [modulus, generator, order] != crypto:
            m = "Invalid trustee factors: Cryptosystem mismatch"
            raise ZeusError(m)

        factors = trustee_factors['decryption_factors']
        ciphers = self.get_mixed_ballots()
        nr_parallel = self.get_option('nr_parallel')
        if not verify_decryption_factors(modulus, generator, order,
                                         trustee_public,
                                         ciphers, factors,
                                         teller=teller,
                                         nr_parallel=nr_parallel):
            print "MODULUS", modulus
            print "GENERATOR", generator
            print "ORDER", order
            print "CIPHERS", ciphers
            print "FACTORS", factors
            print "PK", trustee_public
            m = "Invalid trustee factor proof!"
            raise ZeusError(m)

        return 1

    def add_trustee_factors(self, trustee_factors):
        self.do_assert_stage('DECRYPTING')
        if not self.validate_trustee_factors(trustee_factors):
            m = "Invalid trustee factors"
            raise ZeusError(m)

        self.do_store_trustee_factors(trustee_factors)

    def validate_decrypting(self):
        teller = self.teller
        teller.task("Validating stage: 'DECRYPTING'")

        crypto = self.do_get_cryptosystem()
        modulus, generator, order = crypto
        trustees = self.do_get_trustees()
        all_factors = self.do_get_all_trustee_factors()
        nr_trustees = len(trustees)
        nr_factors = len(all_factors)
        if nr_trustees != nr_factors:
            m = ("There are %d trustees, but only %d factors!"
                % (nr_trustees, nr_factors))
            raise ZeusError(m)

        mixed_ballots = self.get_mixed_ballots()

        for trustee in trustees:
            if trustee not in all_factors:
                m = "Invalid decryption factors: trustee mismatch!"
                raise AssertionError(m)

            nr_parallel = self.get_option('nr_parallel')
            factors = all_factors[trustee]
            if not verify_decryption_factors(modulus, generator, order,
                                             trustee, mixed_ballots, factors,
                                             teller=teller,
                                             nr_parallel=nr_parallel):
                m = "Invalid trustee factors proof!"
                raise ZeusError(m)

        zeus_factors = self.do_get_zeus_factors()
        zeus_public = self.do_get_zeus_public()
        if not verify_decryption_factors(modulus, generator, order,
                                         zeus_public, mixed_ballots,
                                         zeus_factors, teller=teller):
                m = "Invalid zeus factors proof!"
                raise ZeusError(m)

        teller.finish()

    def compute_zeus_factors(self):
        Random.atfork()
        teller = self.teller
        mixed_ballots = self.get_mixed_ballots()
        modulus, generator, order = self.do_get_cryptosystem()
        secret = self.do_get_zeus_secret()
        nr_parallel = self.get_option('nr_parallel')
        with teller.task("Computing Zeus factors"):
            zeus_factors = compute_decryption_factors(modulus, generator,
                                                      order,
                                                      secret, mixed_ballots,
                                                      teller=teller,
                                                      nr_parallel=nr_parallel)
        self.do_store_zeus_factors(zeus_factors)

    def decrypt_ballots(self):
        teller = self.teller
        mixed_ballots = self.get_mixed_ballots()
        modulus, generator, order = self.do_get_cryptosystem()
        zeus_factors = self.do_get_zeus_factors()
        all_factors = self.do_get_all_trustee_factors().values()
        all_factors.append(zeus_factors)
        decryption_factors = combine_decryption_factors(modulus, all_factors)
        plaintexts = []
        append = plaintexts.append

        with teller.task("Decrypting ballots", total=len(mixed_ballots)):
            for ballot, factor in izip(mixed_ballots, decryption_factors):
                plaintext = decrypt_with_decryptor(modulus, generator, order,
                                                   ballot[BETA], factor)
                append(plaintext)
                teller.advance()

        self.do_store_results(plaintexts)
        return plaintexts

    def validate_finished(self):
        teller = self.teller
        with teller.task("Validating STAGE: 'FINISHED'"):
            old_results = self.do_get_results()
            results = self.decrypt_ballots()
            if old_results and old_results != results:
                m = "Old results did not match new results!"
                raise AssertionError(m)

    def set_finished(self):
        stage = self.do_get_stage()
        if stage == 'FINISHED':
            m = "Already in stage 'FINISHED'"
            raise ZeusError(m)
        if stage != 'DECRYPTING':
            m = "Cannot transition from stage '%s' to 'FINISHED'" % (stage,)
            raise ZeusError(m)

        if not self.get_option('no_verify'):
            self.validate_decrypting()

        self.decrypt_ballots()
        self.do_set_stage('FINISHED')

    def export_finished(self):
        stage = self.do_get_stage()
        if stage != 'FINISHED':
            m = ("Stage 'FINISHED' must have been reached "
                 "before it can be exported")
            raise ZeusError(m)

        finished = self.export_decrypting()
        finished['results'] = self.do_get_results()
        fingerprint = sha256(to_canonical(finished)).hexdigest()
        finished['election_fingerprint'] = fingerprint

        report = ''

        trustees = list(self.do_get_trustees())
        trustees.sort()
        for i, trustee in enumerate(trustees):
            report += 'TRUSTEE %d: %x\n' % (i, trustee)
        candidates = self.do_get_candidates()
        report += '\n'

        for i, candidate in enumerate(candidates):
            report += 'CANDIDATE %d: %s\n' % (i, candidate)
        report += '\n'

        excluded = self.do_get_excluded_voters()
        if excluded:
            for i, (voter, reason) in enumerate(excluded.iteritems()):
                report += 'EXCLUDED VOTER %d: %s (%s)\n' % (i, voter, reason)
            report += '\n'

        report += 'ZEUS ELECTION FINGERPRINT: %s\n' % (fingerprint,)

        finished['election_report'] = report
        return finished

    @classmethod
    def new_at_finished(cls, finished, teller=_teller, **kw):
        self = cls.new_at_decrypting(finished, teller=teller, **kw)
        self.do_store_results(finished['results'])
        finished.pop('election_report', None)
        fingerprint = finished.pop('election_fingerprint', None)
        _fingerprint = sha256(to_canonical(finished)).hexdigest()
        if fingerprint is not None:
            if fingerprint != _fingerprint:
                m = "Election fingerprint mismatch!"
                #print "WARNING: " + m
                raise AssertionError(m)
        fingerprint = _fingerprint
        self.election_fingerprint = fingerprint
        self.do_set_stage('FINISHED')
        return self

    def get_results(self):
        self.do_assert_stage('FINISHED')
        results = self.do_get_results()
        return results

    _export_methods = {
        'CREATING': None,
        'VOTING': 'export_creating',
        'MIXING': 'export_voting',
        'DECRYPTING': 'export_mixing',
        'FINISHED': 'export_finished',
    }

    def export(self):
        stage = self.do_get_stage()
        method_name = self._export_methods[stage]
        if method_name is None:
            m = "Cannot export stage '%s'" % (stage,)
            raise ValueError(m)
        return getattr(self, method_name)(), stage

    def validate(self):
        self.validate_creating()
        self.validate_voting()
        self.validate_mixing()
        self.validate_decrypting()
        self.validate_finished()
        return 1

    ### CLIENT REFERENCE ###

    def mk_random_trustee(self):
        crypto = self.do_get_cryptosystem()
        modulus, generator, order = crypto
        secret = get_random_int(3, order)
        public = pow(generator, secret, modulus)
        proof = prove_dlog(modulus, generator, order, public, secret)
        return sk_from_args(modulus, generator, order, secret, public, *proof)

    def mk_reprove_trustee(self, public, secret):
        modulus, generator, order = self.do_get_cryptosystem()
        proof = prove_dlog(modulus, generator, order, public, secret)
        return sk_from_args(modulus, generator, order, secret, public, *proof)

    def mk_psudorandom_selection(self):
        selections = []
        append = selections.append
        nr_candidates = len(self.do_get_candidates())
        if not nr_candidates:
            m = "No candidates!"
            raise ValueError(m)

        z = 0
        for m in xrange(nr_candidates-1, -1, -1):
            r = randint(0, m)
            if r == 0:
                z = 1
            if z:
                append(0)
            else:
                append(r)

        return selections

    def mk_random_vote(self, selection=None, voter=None,
                             audit_code=None, publish=None):
        modulus, generator, order = self.do_get_cryptosystem()
        public = self.do_get_election_public()
        candidates = self.do_get_candidates()
        nr_candidates = len(candidates)
        if selection is None:
            r = get_random_int(0, 4)
            if r & 1:
                selection = get_random_selection(nr_candidates, full=0)
            else:
                selection = get_random_party_selection(nr_candidates, 2)

        voters = None
        if voter is None:
            voters = self.do_get_voters()
            voter = choice(voters.keys())
        encoded = encode_selection(selection, nr_candidates)
        valid = True
        if audit_code:
            if voters is None:
                voters = self.do_get_voters()
            voter_audit_codes = self.do_get_voter_audit_codes(voter)
            if audit_code < 0:
                if voter not in voters:
                    m = ("Valid audit_code requested but voter not found!")
                    raise ValueError(m)
                audit_code = voter_audit_codes[0]
            elif voter not in voters:
                valid = False
            elif audit_code not in voter_audit_codes:
                valid = False
        vote = vote_from_encoded(modulus, generator, order, public,
                                 voter, encoded, nr_candidates,
                                 audit_code=audit_code, publish=1)
        rnd = vote['voter_secret']
        if not publish:
            del vote['voter_secret']

        return vote, selection, encoded if valid else None, rnd

    def mk_stage_creating(self, teller=_teller):
        nr_candidates = self._nr_candidates
        candidates = []
        append = candidates.append
        mid = nr_candidates // 2
        first = 1
        for i in xrange(0, mid):
            if first:
                append("Party-A" + PARTY_SEPARATOR + "0-2, 0")
                first = 0
            append("Party-A" + PARTY_SEPARATOR + "Candidate-%04d" % i)

        first = 1
        for i in xrange(mid, nr_candidates):
            if first:
                append("Party-B" + PARTY_SEPARATOR + "0-2, 1")
                first = 0
            append("Party-B" + PARTY_SEPARATOR + "Candidate-%04d" % i)

        voter_range = xrange(self._nr_voters)
        voters = [("Voter-%08d" % x) for x in voter_range]

        self.create_zeus_key()
        self.add_candidates(*candidates)
        self.add_voters(*voters)

        trustees = [self.mk_random_trustee()
                    for _ in xrange(self._nr_trustees)]
        for trustee in trustees:
            self.add_trustee(key_public(trustee), key_proof(trustee))

        trustees = [self.mk_reprove_trustee(key_public(t), key_secret(t))
                    for t in trustees]
        for trustee in trustees:
            self.reprove_trustee(key_public(trustee), key_proof(trustee))

        self._trustees = trustees

    def mk_stage_voting(self, teller=_teller):
        selections = []
        plaintexts = {}
        votes = []
        voters = list(self.do_get_voters())
        for i, voter in zip(xrange(self._nr_votes), cycle(voters)):
            kw = {'audit_code': -1} if (i & 1) else {}
            kw['voter'] = voter
            vote, selection, encoded, rnd = self.mk_random_vote(**kw)
            if vote['voter'] != voter:
                m = "Vote has wrong voter!"
                raise AssertionError(m)
            selections.append(selection)
            if encoded is not None:
                plaintexts[voter] = encoded
            votes.append(vote)
            signature = self.cast_vote(vote)
            if not signature.startswith(V_CAST_VOTE):
                m = "Invalid cast vote signature!"
                raise AssertionError(m)
            teller.advance()

        with teller.task("Excluding last voter"):
            cast_votes = self.do_get_cast_votes(voter)
            if not cast_votes:
                m = "Voter has no votes!"
                raise AssertionError(m)
            self.exclude_voter(voter)
            del selections[-1]
            del plaintexts[voter]

        self._selections = selections
        self._plaintexts = plaintexts
        self._votes = votes

        with teller.task("Casting a valid audit vote"):
            vote, selection, encoded, rnd = self.mk_random_vote(audit_code=1)
            signature = self.cast_vote(vote)
            if not signature.startswith(V_AUDIT_REQUEST):
                m = "Invalid audit request reply!"
                raise AssertionError(m)

            vote['voter_secret'] = rnd
            self.cast_vote(vote)

        self.verify_audit_votes()

        with teller.task("Casting an invalid audit vote"):
            vote, selection, encoded, rnd = self.mk_random_vote(audit_code=1)
            signature = self.cast_vote(vote)
            if not signature.startswith(V_AUDIT_REQUEST):
                m = "Invalid audit request reply!"
                raise AssertionError(m)

            vote['voter_secret'] = rnd
            eb = vote['encrypted_ballot']
            phony = eb['alpha'] + 1
            eb['alpha'] = phony
            self._phony = phony
            modulus, generator, order = self.do_get_cryptosystem()
            alpha = eb['alpha']
            beta = eb['beta']
            commitment = eb['commitment']
            challenge = eb['challenge']
            response = eb['response']
            if verify_encryption(modulus, generator, order, alpha, beta,
                                 commitment, challenge, response):
                m = "This should have failed"
                raise AssertionError(m)
            signature = self.cast_vote(vote)
            if not signature.startswith(V_PUBLIC_AUDIT):
                m = "Invalid public audit reply!"
                raise AssertionError(m)

    def mk_stage_mixing(self, teller=_teller):
        for _ in xrange(self._nr_mixes):
            cipher_collection = self.get_last_mix()
            nr_parallel = self.get_option('nr_parallel')
            mixed_collection = mix_ciphers(cipher_collection,
                                           nr_rounds=self._nr_rounds,
                                           teller=teller,
                                           nr_parallel=nr_parallel)
            self.add_mix(mixed_collection)
            teller.advance()

    def mk_stage_decrypting(self, teller=_teller):
        modulus, generator, order = self.do_get_cryptosystem()
        nr_parallel = self.get_option('nr_parallel')
        ciphers = self.get_mixed_ballots()
        with teller.task("Calculating and adding decryption factors",
                         total=self._nr_trustees):
            for trustee in self._trustees:
                factors = compute_decryption_factors(
                                    modulus, generator, order,
                                    key_secret(trustee), ciphers,
                                    teller=teller, nr_parallel=nr_parallel)
                trustee_factors = {'trustee_public': key_public(trustee),
                                   'decryption_factors': factors,
                                   'modulus': modulus,
                                   'generator': generator,
                                   'order': order}
                self.add_trustee_factors(trustee_factors)
                teller.advance()

    def mk_stage_finished(self, teller=_teller):
        with teller.task("Validating results"):
            results = self.get_results()
            if len(results) != self._nr_votes -1:
                m = "Vote exclusion was not performed!"
                raise AssertionError(m)

            if sorted(results) != sorted(self._plaintexts.values()):
                m = ("Invalid Election! "
                     "Casted plaintexts do not match plaintext results!")
                raise AssertionError(m)

            missing, failed = self.verify_audit_votes()
            if (missing or not failed or
                not failed[0]['encrypted_ballot']['alpha'] == self._phony):
                m = "Invalid audit request not detected!"
                raise AssertionError(m)

    @classmethod
    def mk_random(cls, nr_candidates   =   3,
                       nr_trustees     =   2,
                       nr_voters       =   10,
                       nr_votes        =   10,
                       nr_mixes        =   2,
                       nr_rounds       =   8,
                       stage           =   'FINISHED',
                       teller=_teller, **kw):

        self = cls(teller=teller, **kw)
        self._nr_candidates = nr_candidates
        self._nr_trustees = nr_trustees
        self._nr_voters = nr_voters
        self._nr_votes = nr_votes
        self._nr_mixes = nr_mixes
        self._nr_rounds = nr_rounds
        stage = stage.upper()

        with teller.task("Creating election"):
            self.mk_stage_creating(teller=teller)
        if stage == 'CREATING':
            return self

        self.set_voting()
        with teller.task("Voting", total=nr_votes):
            self.mk_stage_voting(teller=teller)
        if stage == 'VOTING':
            return self

        self.set_mixing()
        with teller.task("Mixing", total=nr_mixes):
            self.mk_stage_mixing(teller=teller)
        if stage == 'MIXING':
            return self

        self.set_decrypting()
        with teller.task("Decrypting"):
            self.mk_stage_decrypting(teller=teller)
        if stage == 'DECRYPTING':
            return self

        self.set_finished()
        self.mk_stage_finished(teller=teller)
        return self


def main():
    import argparse
    description='Zeus Election Reference Implementation and Verifier.'
    epilog="Try 'zeus --generate'"
    parser = argparse.ArgumentParser(description=description, epilog=epilog)

    parser.add_argument('--election', metavar='infile',
        help="Read a FINISHED election from a proofs file and verify it")

    parser.add_argument('--verify-signatures', nargs='*',
        metavar=('election_file', 'signature_file'),
        help="Read an election and a signature from a JSON file "
             "and verify the signature")

    parser.add_argument('--parallel', dest='nr_procs', default=2,
        help="Use multiple processes for parallel mixing")

    parser.add_argument('--no-verify', action='store_true', default=False,
                        help="Do not verify elections")

    parser.add_argument('--report', action='store_true', default=False,
                        help="Display election report")

    parser.add_argument('--counted', action='store_true', default=False,
                        help="Display election counted votes fingerprints")

    parser.add_argument('--results', action='store_true', default=False,
                        help="Display election plaintext results")

    parser.add_argument('--count-parties', action='store_true', default=False,
                        help="Count results based on candidate parties")

    parser.add_argument('--extract-signatures', metavar='prefix',
        help="Write election signatures for counted votes to files")

    parser.add_argument('--extract-audits', metavar='prefix',
                        help="Write election public audits to files")

    parser.add_argument('--extract-mixed', metavar='prefix',
                        help="Write election public audits to files")

    parser.add_argument('--generate', nargs='*', metavar='outfile',
        help="Generate a random election and write it out in JSON")

    parser.add_argument('--stage', type=str, default='FINISHED',
                        help="Generate: Stop when this stage is complete")

    parser.add_argument('--candidates', type=int, default=3,
                        dest='nr_candidates',
                        help="Generate: Number of candidates")

    parser.add_argument('--trustees', type=int, default=2,
                        dest='nr_trustees',
                        help="Generate: Number of trustees")

    parser.add_argument('--voters', type=int, default=10,
                        dest='nr_voters',
                        help="Generate: Number of voters")

    parser.add_argument('--votes', type=int, default=10,
                        dest='nr_votes',
                        help="Generate: Number of valid votes to cast")

    parser.add_argument('--mixes', type=int, default=2,
                        dest='nr_mixes',
                        help="Generate: Number of times to mix")

    parser.add_argument('--rounds', type=int, default=MIN_MIX_ROUNDS,
                        dest='nr_rounds',
                        help="Generate or Mix: Number of mix rounds")

    parser.add_argument('--verbose', action='store_true', default=True,
        help=("Write validation, verification, and notice messages "
              "to standard error"))

    parser.add_argument('--quiet', action='store_false', dest='verbose',
        help=("Be quiet. Cancel --verbose"))

    parser.add_argument('--oms', '--output-interval-ms', type=int,
        metavar='millisec', default=200, dest='oms',
        help=("Set the output update interval"))

    parser.add_argument('--no-buffer', action='store_true', default=False,
        help=("Do not keep output in buffer. "
              "Keep only the last one to display as per --oms."))

    parser.add_argument('--buffer-feeds', action='store_true', default=False,
        help=("Buffer output newlines according to --oms "
              "instead of sending them out immediately"))

    args = parser.parse_args()

    def do_extract_signatures(election, prefix='counted', teller=_teller):
        vfm, counted_list = election.extract_votes_for_mixing()
        count = 0
        total = len(counted_list)

        with teller.task("Extracting signatures"):
            for fingerprint in counted_list:
                vote = election.do_get_vote(fingerprint)
                signature = vote['signature']
                filename = prefix + fingerprint
                with open(filename, "w") as f:
                    f.write(strforce(signature))
                count += 1
                teller.status("%d/%d '%s'", count, total, filename, tell=1)

        return vfm, counted_list

    def do_extract_audits(election, prefix='audit', teller=_teller):
        audits = election.do_get_audit_publications()
        count = 0
        total = len(audits)

        with teller.task("Extracting audit publications"):
            for fingerprint in audits:
                vote = election.do_get_vote(fingerprint)
                signature = vote['signature']
                filename = prefix + '_' + fingerprint
                with open(filename, "w") as f:
                    f.write(strforce(signature))
                count += 1
                teller.status("%d/%d '%s'", count, total, filename, tell=1)

    def do_counted_votes(election):
        vfm, counted_list = election.extract_votes_for_mixing()
        for i, fingerprint in enumerate(counted_list):
            print 'COUNTED VOTE %d: %s' % (i, fingerprint)
        print ""
        return vfm, counted_list

    def do_report(election):
        exported, stage = election.export()
        if 'election_report' in exported:
            print exported['election_report']
        return exported, stage

    def do_results(election):
        results = election.do_get_results()
        print 'RESULTS: %s\n' % (' '.join(str(n) for n in results),)

    def do_count_parties(election):
        results = election.do_get_results()
        candidates = election.do_get_candidates()
        results = gamma_count_parties(results, candidates)
        import json
        print json.dumps(results, ensure_ascii=False, indent=2)

    def main_generate(args, teller=_teller, nr_parallel=0):
        filename = args.generate
        filename = filename[0] if filename else None
        no_verify = args.no_verify

        election = ZeusCoreElection.mk_random(
                            nr_candidates   =   args.nr_candidates,
                            nr_trustees     =   args.nr_trustees,
                            nr_voters       =   args.nr_voters,
                            nr_votes        =   args.nr_votes,
                            nr_rounds       =   args.nr_rounds,
                            stage           =   args.stage,
                            teller=teller, nr_parallel=nr_parallel,
                            no_verify=no_verify)
        exported, stage = election.export()
        if not filename:
            name = ("%x" % election.do_get_election_public())[:16]
            filename = 'election-%s-%s.zeus' % (name, stage)
            sys.stderr.write("writing out to '%s'\n\n" % (filename,))
        with open(filename, "w") as f:
            f.write(to_canonical(exported))
        report = exported.get('election_report', '')
        del exported

        if args.extract_signatures:
            do_extract_signatures(election, args.extract_signatures,
                                  teller=teller)
        if args.extract_audits:
            do_extract_audits(election, args, args.extract_audits,
                              teller=teller)
        if args.counted:
            do_counted_votes(election)

        if args.results:
            do_results(election)

        if args.count_parties:
            do_count_parties(election)

        if args.report:
            print report

    def main_verify_election(args, teller=_teller, nr_parallel=0):
        no_verify = args.no_verify
        filename = args.election
        sys.stderr.write("loading election from '%s'\n" % (filename,))
        with open(filename, "r") as f:
            try:
                finished = from_canonical(f, unicode_strings=0)
            except ValueError:
                finished = json_load(f)

        election = ZeusCoreElection.new_at_finished(finished, teller=teller,
                                                    nr_parallel=nr_parallel)
        if not no_verify:
            election.validate()

        if args.extract_signatures:
            do_extract_signatures(election, args.extract_signatures,
                                  teller=teller)

        if args.extract_audits:
            do_extract_audits(election, args.extract_audits,
                              teller=teller)

        if args.counted:
            do_counted_votes(election)

        if args.results:
            do_results(election)

        if args.count_parties:
            do_count_parties(election)

        if args.report:
            do_report(election)

        return election

    def main_verify_signature(args, teller=_teller, nr_parallel=0):
        no_verify = args.no_verify
        report = args.report
        sigfiles = args.verify_signatures
        if len(sigfiles) < 1:
            m = "No signature files given!"
            raise ValueError(m)
        if not args.election:
            m = ("cannot verify signature without an election file "
                 "and at least one signature file")
            raise ValueError(m)

        election_file = args.election
        sys.stderr.write("loading election from '%s'\n" % (election_file,))
        with open(election_file, "r") as f:
            try:
                finished = from_canonical(f, unicode_strings=0)
            except ValueError:
                finished = json_load(f)

        election = ZeusCoreElection.new_at_finished(finished, teller=teller,
                                                    nr_parallel=nr_parallel,
                                                    no_verify=no_verify)
        if report:
            do_report()

        with teller.task("Verifying signatures", total=len(sigfiles)):
            for sigfile in sigfiles:
                with open(sigfile, "r") as f:
                    signature = f.read()
                signed_vote = election.verify_vote_signature(signature)
                election.validate_vote(signed_vote)
                teller.advance()

    class Nullstream(object):
        def write(*args):
            return

        def flush(*args):
            return

    outstream = sys.stderr if args.verbose else Nullstream()
    teller_stream = TellerStream(outstream=outstream,
                                 output_interval_ms=args.oms,
                                 buffering=not args.no_buffer,
                                 buffer_feeds=args.buffer_feeds)
    teller = Teller(outstream=teller_stream)
    if args.no_buffer:
        Teller.eol = '\n'
        Teller.feed = '\n'

    nr_parallel = 0
    if args.nr_procs > 0:
        nr_parallel = int(args.nr_procs)

    if args.generate is not None:
        return main_generate(args, teller=teller, nr_parallel=nr_parallel)
    elif args.verify_signatures:
        return main_verify_signature(args, teller=teller,
                                     nr_parallel=nr_parallel)
    elif args.election:
        return main_verify_election(args, teller=teller,
                                    nr_parallel=nr_parallel)
    else:
        parser.print_help()

    teller_stream.flush()

g = _default_crypto['generator']
p = _default_crypto['modulus']
q = _default_crypto['order']

def test_decryption():
    texts = [0, 1, 2, 3, 4]
    keys = [13, 14, 15, 16]
    publics = [pow(g, x, p) for x in keys]
    pk = 1
    for y in publics:
        pk = (pk * y) % p
    cts = []
    rands = []
    for t in texts:
        ct = encrypt(t, p, g, q, pk)
        cts.append((ct[0], ct[1]))
        rands.append(ct[2])

    all_factors = []
    for x in keys:
        factors = compute_decryption_factors(p, g, q, x, cts)
        all_factors.append(factors)

    master_factors = combine_decryption_factors(p, all_factors)
    pts = []
    for (alpha, beta), factor in izip(cts, master_factors):
        pts.append(decrypt_with_decryptor(p, g, q, beta, factor))
    if pts != texts:
        raise AssertionError("Z")

    cfm = {'modulus': p,
           'generator': g,
           'order': q,
           'public': pk,
           'original_ciphers': cts,
           'mixed_ciphers': cts}

    mix1 = mix_ciphers(cfm)
    mix = mix_ciphers(mix1)
    cts = mix['mixed_ciphers']
    all_factors = []
    for x in keys:
        factors = compute_decryption_factors(p, g, q, x, cts)
        all_factors.append(factors)

    master_factors = combine_decryption_factors(p, all_factors)
    pts = []
    for (alpha, beta), factor in izip(cts, master_factors):
        pts.append(decrypt_with_decryptor(p, g, q, beta, factor))
    if sorted(pts) != sorted(texts):
        raise AssertionError("ZZ")

retval = []

if __name__ == '__main__':
    #verify_gamma_encoding(7)
    #cross_check_encodings(7)
    #test_decryption()
    retval.append(main())
