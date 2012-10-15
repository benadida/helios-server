#!/usr/bin/env python

import sys
PYTHON_MAJOR = sys.version_info[0]
from datetime import datetime
from random import randint, shuffle, choice
from collections import defaultdict
from hashlib import sha256
from itertools import izip
from math import log
from bisect import bisect_right
import Crypto.Util.number as number
inverse = number.inverse
from Crypto import Random
from operator import mul as mul_operator

class ZeusError(Exception):
    pass

ALPHA = 0
BETA  = 1
PROOF = 2

VOTER_KEY_CEIL = 2**256
VOTER_SLOT_CEIL = 2**48
MIN_MIX_ROUNDS = 8

V_CAST_VOTE     =   'CAST VOTE'
V_PUBLIC_AUDIT  =   'PUBLIC AUDIT'
V_AUDIT_REQUEST =   'AUDIT REQUEST'

V_ELECTION      =   'ELECTION: '
V_FINGERPRINT   =   'FINGERPRINT: '
V_INDEX         =   'INDEX: '
V_PREVIOUS      =   'PREVIOUS VOTE: '
V_ZEUS_PUBLIC   =   'ZEUS PUBLIC KEY: '
V_COMMENTS      =   'COMMENTS: '
V_VOTE_DATA     =   'VOTE DATA: '

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

def pk_no_proof_from_args(p, g, q, y):
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


class Teller(object):
    name = None
    total = None
    current = None
    finished = None
    status_fmt = None
    status_args = None
    clear_size = None
    disabled = False
    children = None
    parent = None
    resuming = None
    outstream = None
    last_active = None
    last_teller = [None]
    last_ejected = [None]

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
                       parent=None, resume=False,
                       outstream=sys.stderr, **kw):
        self.name = name
        self.depth = depth
        self.total = total
        self.current = current
        self.clear_size = 0
        self.parent = parent
        self.children = {}
        self.set_format()
        self.outstream = outstream
        self.resuming = resume

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
        return line

    def disable(self):
        self.disabled = True
        for child in self.children.values():
            child.disable()

    def tell(self, feed=False, eject=False):
        if self.disabled:
            return

        line = self.__str__()
        clear_size = len(line)
        if clear_size > self.clear_size:
            self.clear_size = clear_size

        line += self.eol
        self.output(line, feed=feed, eject=eject)

    def output(self, text, feed=False, eject=0):
        outstream = self.outstream
        if outstream is None or self.disabled:
            return

        last_teller = self.last_teller
        teller = last_teller[0]
        last_ejected = self.last_ejected
        ejected = last_ejected[0]
        feeder = self.feed
        if not ejected and (feed or teller != self):
            text = feeder + text
            self.clear_size = 0
        if eject:
            text += feeder * eject
            self.clear_size = 0
        outstream.write(text)
        last_teller[0] = self
        last_ejected[0] = eject

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

    def task(self, name='', total=1, current=0, resume=False, **kw):
        self = self.active()
        children = self.children
        kw['parent'] = self
        kw['depth'] = self.depth + 1
        kw['outstream'] = self.outstream
        kw['fail_parent'] = self.fail_parent
        kw['active'] = self.active
        task = self.__class__(name=name, total=total, current=current,
                              resume=resume, **kw)
        children[id(task)] = task
        task.check_tell(None)
        return task

    def notice(self, fmt, *args):
        self = self.active()

        text = fmt % args
        clear_line = ' ' * self.clear_size + self.eol
        lines = []
        append = lines.append

        for text_line in text.split('\n'):
            line = self.prefix_filler * (self.depth-1) + self.notice_mark
            line += text_line
            append(line)

        final_text = clear_line + '\n'.join(lines)
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
            m = "ELGAMAL GROUP IS NOT THE MODULUS QUADRATIC RESIDUES"
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
    lefts = [None] * nr_elements
    rights = [None] * nr_elements
    offsets = [None] * nr_elements
    shifts = [0] * nr_elements
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

def get_random_selection(nr_elements):
    selection = []
    append = selection.append
    for m in xrange(nr_elements, 1, -1):
        append(get_random_int(0, m))
        #append(randint(0, m-1))
    append(0)
    return selection

def selection_to_permutation(selection):
    nr_elements = len(selection)
    lefts = [None] * nr_elements
    rights = [None] * nr_elements
    leftpops = [0] * nr_elements
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

    permutation = [None] * nr_elements
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
    return selection_to_permutation(get_random_selection(nr_elements))

_terms = {}

def get_term(n, k):
    if k >= n:
        return 1

    if n in _terms:
        t = _terms[n]
        if k in t:
            return t[k]
    else:
        t = {n:1}
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
        choices = list(gamma_decode(encoded, n))
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
    nr_bits = top.bit_length()
    nr_bytes = (nr_bits - 1) / 8 + 1
    strbin = _random_generator_file.read(nr_bytes)
    num = strbin_to_int(strbin)
    shift = num.bit_length() - nr_bits
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

def encrypt(message, modulus, generator, order, public):
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

def prove_dlog(modulus, generator, order, power, dlog):
    randomness = get_random_int(2, order)
    commitment = pow(generator, randomness, modulus)
    challenge = element_from_elements_hash(modulus, generator, order,
                                           power, commitment)
    response = (randomness + challenge * dlog) % order
    return [commitment, challenge, response]

def verify_dlog_power(modulus, generator, order, power,
                      commitment, challenge, response):
    _challenge = element_from_elements_hash(modulus, generator, order,
                                            power, commitment)
    if _challenge != challenge:
        return 0
    return (pow(generator, response, modulus) 
            == ((commitment * pow(power, challenge, modulus)) % modulus))

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
    args = (str(base_commitment), (message_commitment))
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

def prove_encryption(modulus, generator, order, alpha, secret):
    """Prove ElGamal encryption"""
    ret = prove_dlog(modulus, generator, order, alpha, secret)
    commitment, challenge, response = ret
    return [commitment, challenge, response]

def verify_encryption(modulus, generator, order, alpha,
                      commitment, challenge, response):
    """Verify ElGamal encryption"""
    ret = verify_dlog_power(modulus, generator, order, alpha,
                            commitment, challenge, response)
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
    """Produce ElGamal signature"""
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


def encode_selection(selection):
    nr_candidates = len(selection)
    return gamma_encode(selection, nr_candidates, nr_candidates)

def vote_from_encoded(modulus, generator, order, public,
                      voter, encoded, nr_candidates,
                      slot=None, audit=None):

    alpha, beta, rnd = encrypt(encoded, modulus, generator, order, public)
    proof = prove_encryption(modulus, generator, order, alpha, rnd)
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

    if slot:
        vote['slot'] = None

    if audit:
        vote['secret'] = rnd

    return vote


def sign_vote(vote, comments, modulus, generator, order, public, secret):
    eb = vote['encrypted_ballot']
    election = eb['public']
    fingerprint = vote['fingerprint']
    previous_vote = vote['previous']
    index = vote['index']
    status = vote['status']

    m0 = status
    m1 = (V_ELECTION + "%x") % election
    m2 = (V_FINGERPRINT + "%s") % fingerprint
    m3 = (V_INDEX + "%x") % index
    m4 = (V_PREVIOUS + "%s") % previous_vote
    m5 = (V_ZEUS_PUBLIC + "%x") % public
    m6 = (V_COMMENTS + "%s") % comments
    m7 = (V_VOTE_DATA + "%r") % eb
    message = '\n'.join((m0, m1, m2, m3, m4, m5, m6, m7))
    return sign_text_message(message, modulus, generator, order, secret)

def validate_vote_info(vote_signature_message):
    m0, m1, m2, m3, m4, m5, m6 = vote_signature_message.split('\n', 6)
    if (not m0.startswith(V_CAST_VOTE)
        or not m1.startswith(V_ELECTION)
        or not m2.startswith(V_FINGERPRINT)
        or not m3.startswith(V_INDEX)
        or not m4.startswith(V_PREVIOUS)
        or not m5.startswith(V_ZEUS_PUBLIC)):

        m = "Invalid vote signature structure!"
        raise ZeusError(m)

    election = m1[len(V_ELECTION):]
    fingerprint = m2[len(V_FINGERPRINT):]
    index = m3[len(V_INDEX):]
    previous = m4[len(V_PREVIOUS):]
    zeus_public = m5[len(V_ZEUS_PUBLIC):]

    election = int(election, 16)
    index = int(index, 16)
    zeus_public = int(zeus_public, 16)
    return [election, fingerprint, index, previous, zeus_public]

def verify_vote_signature(signature, modulus, generator, order, public):
    if 'm' not in signature:
        m = "No message in signature!"
        raise ZeusError(m)
    message = signature['m']
    vote_info = validate_vote_info(message)
    election, fingerprint, index, previous, zeus_public = vote_info
    if zeus_public != public:
        m = "Public key mismatch in signature! %x != %x" % (zeus_public, public)
        raise ZeusError(m)
    if not verify_text_signature(signature, modulus, generator, order, public):
        m = "Invalid vote signature!"
        raise ZeusError(m)
    return [election, fingerprint, index, previous]

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
    low = [0] * nr_elements
    high = range(nr_elements - 1, -1, -1)
    max_low = gamma_encode(low, nr_elements)
    max_high = gamma_encode(high, nr_elements)
    rand = get_random_int(max_low, max_high + 1)
    selection = gamma_decode(rand, nr_elements)
    return selection

def shuffle_ciphers(modulus, generator, order, public, ciphers):
    nr_ciphers = len(ciphers)
    mixed_offsets = get_random_permutation(nr_ciphers)
    mixed_ciphers = [None] * nr_ciphers
    mixed_randoms = [None] * nr_ciphers

    for i in xrange(nr_ciphers):
        alpha, beta = ciphers[i]
        alpha, beta, secret = reencrypt(modulus, generator, order,
                                        public, alpha, beta)
        mixed_randoms[i] = secret
        o = mixed_offsets[i]
        mixed_ciphers[o] = (alpha, beta)

    return [mixed_ciphers, mixed_offsets, mixed_randoms]

def mix_ciphers(ciphers_for_mixing, nr_rounds=MIN_MIX_ROUNDS, teller=_teller):
    p = ciphers_for_mixing['modulus']
    g = ciphers_for_mixing['generator']
    q = ciphers_for_mixing['order']
    y = ciphers_for_mixing['public']

    original_ciphers = ciphers_for_mixing['mixed_ciphers']
    nr_ciphers = len(original_ciphers)

    teller.task('Mixing %d ciphers for %d rounds' % (nr_ciphers, nr_rounds))

    cipher_mix = {'modulus': p, 'generator': g, 'order': q, 'public': y}
    cipher_mix['original_ciphers'] = original_ciphers

    with teller.task('Producing final mixed ciphers'):
        shuffled = shuffle_ciphers(p, g, q, y, original_ciphers)
        mixed_ciphers, mixed_offsets, mixed_randoms = shuffled
        cipher_mix['mixed_ciphers'] = mixed_ciphers

    with teller.task('Producing ciphers for proof', total=nr_rounds):
        cipher_collections = []
        random_collections = []
        offset_collections = []

        for _ in xrange(nr_rounds):
            shuffled = shuffle_ciphers(p, g, q, y, original_ciphers)
            ciphers, offsets, randoms = shuffled
            cipher_collections.append(ciphers)
            offset_collections.append(offsets)
            random_collections.append(randoms)
            teller.advance()

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
                new_offsets = [None] * nr_ciphers
                new_randoms = [None] * nr_ciphers

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


def verify_cipher_mix(cipher_mix, teller=_teller):
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

    teller.task('Verifying rounds', total=nr_rounds)
    for i, bit in zip(xrange(nr_rounds), bit_iterator(int(challenge, 16))):
        ciphers = cipher_collections[i]
        randoms = random_collections[i]
        offsets = offset_collections[i]

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
        else:
            m = "This should be impossible. Something is broken."
            raise AssertionError(m)
        teller.advance()
    teller.finish('Verifying rounds')
    teller.finish('Verifying mixing')
    return 1


def compute_decryption_factors(modulus, generator, order, secret, ciphers,
                               teller=_teller):
    factors = []
    public = pow(generator, secret, modulus)
    append = factors.append
    nr_ciphers = len(ciphers)
    with teller.task("Calculating decryption factors", total=nr_ciphers):
        for alpha, beta in ciphers:
            factor = pow(alpha, secret, modulus)
            proof = prove_ddh_tuple(modulus, generator, order,
                                    alpha, public, factor, secret)
            append([factor, proof])
            teller.advance()
    return factors

def verify_decryption_factors(modulus, generator, order, public,
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
                       teller=_teller):
        self.teller = teller
        self.do_init_creating()
        self.do_init_voting()
        self.do_init_mixing()
        self.do_init_decrypting()
        self.do_init_finished()
        self.init_creating(cryptosystem)

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
        self.slots = {}
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

    def do_store_voter_slots(self, slots):
        self.slots.update(slots)

    def do_get_voter_slots(self, voter_key):
        slots = self.slots
        if voter_key not in slots:
            return None
        return slots[voter_key]

    def do_get_all_voter_slots(self):
        return dict(self.slots)

    ### VOTING BACKEND API ###

    def do_init_voting(self):
        self.cast_vote_index = []
        self.votes = {}
        self.cast_votes = {}
        self.audit_requests = {}
        self.audit_publications = []

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

    def do_store_trustee_factors(self, trustee_factors):
        trustee_public = trustee_factors['trustee_public']
        factors = trustee_factors['decryption_factors']
        self.trustee_factors[trustee_public] = factors

    def do_get_all_trustee_factors(self):
        return dict(self.trustee_factors)

    ### FINISHED BACKEND API ###

    def do_init_finished(self):
        self.results = None

    def do_store_results(self, plaintexts):
        self.results = list(plaintexts)

    def do_get_results(self):
        return self.results

    ### GENERIC IMPLEMENTATION ###

    def set_option(self, **kw):
        self.do_assert_stage('CREATING')
        return self.do_set_option(kw)

    def get_option(self, name):
        return self.do_get_option(name)

    def init_creating(self, cryptosystem):
        modulus, generator, order = cryptosystem
        self.do_store_cryptosystem(modulus, generator, order)
        self.do_set_stage('CREATING')

    @classmethod
    def new_at_creating(cls, cryptosystem=_default_crypto, teller=_teller):
        self = cls(cryptosystem, teller=teller)
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
        public = 1
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

        self.do_store_candidates(names)

    def add_voters(self, *names):
        name_set = set(self.do_get_voters().values())
        intersection = name_set.intersection(names)
        if intersection:
            m = "Voter '%s' already exists!" % (intersection.pop(),)
            raise ZeusError(m)

        new_voters = {}
        voter_slots = {}
        for name in names:
            voter_key = "%x" % get_random_int(2, VOTER_KEY_CEIL)
            new_voters[voter_key] = name
            slots = list(get_random_int(1, VOTER_SLOT_CEIL) for _ in xrange(3))
            voter_slots[voter_key] = slots
        self.do_store_voters(new_voters)
        self.do_store_voter_slots(voter_slots)

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

            with teller.task("Validating voter slots"):
                slots = self.do_get_all_voter_slots()
                if slots.keys() != keys:
                    m = "Slots do not correspond to voters!"
                    raise ZeusError(m)
                slot_set = set(tuple(v) for v in slots.values())
                if len(slot_set) < nr_keys / 2:
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
            _election_public = 1
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
        creating['options'] = self.do_get_options()
        creating['candidates'] = self.do_get_candidates()
        creating['voters'] = self.do_get_voters()
        creating['slots'] = self.do_get_all_voter_slots()
        creating['cryptosystem'] = self.do_get_cryptosystem()
        creating['zeus_public'] = self.do_get_zeus_public()
        creating['zeus_secret'] = self.do_get_zeus_secret()
        creating['zeus_key_proof'] = self.do_get_zeus_key_proof()
        creating['election_public'] = self.do_get_election_public()
        creating['trustees'] = self.do_get_trustees()
        creating['voters'] = self.do_get_voters()
        creating['voter_slots'] = self.do_get_all_voter_slots()
        return creating

    def set_voting(self):
        stage = self.do_get_stage()
        if stage == 'VOTING':
            m = "Already in stage 'VOTING'"
            raise ZeusError(m)
        if stage != 'CREATING':
            m = "Cannot transition from stage '%s' to 'VOTING'" % (stage,)
            raise ZeusError(m)

        self.validate_creating()
        self.do_set_stage('VOTING')

    @classmethod
    def new_at_voting(cls, voting, teller=_teller):
        self = cls.new_at_creating(teller=teller)
        self.do_set_option(voting['options'])
        self.do_store_candidates(voting['candidates'])
        self.do_store_cryptosystem(*voting['cryptosystem'])
        self.do_store_zeus_key(voting['zeus_secret'],
                               voting['zeus_public'],
                               *voting['zeus_key_proof'])
        self.do_store_election_public(voting['election_public'])
        for t in voting['trustees'].iteritems():
            trustee_public_key, trustee_key_proof = t
            trustee_public_key = int(trustee_public_key)
            self.do_store_trustee(trustee_public_key, *trustee_key_proof)
        self.do_store_voters(voting['voters'])
        self.do_store_voter_slots(voting['voter_slots'])
        self.set_voting()
        return self

    def validate_submitted_vote(self, vote):
        keys = set(('voter', 'encrypted_ballot', 'fingerprint',
                    'slot', 'secret'))
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
        if not verify_encryption(modulus, generator, order, alpha,
                                 commitment, challenge, response):
            m = "Invalid vote encryption proof!"
            raise ZeusError(m)

        fingerprint = numbers_hash((modulus, generator, alpha, beta,
                                    commitment, challenge, response))
        if fingerprint != vote['fingerprint']:
            m = "Invalid vote fingerprint!"
            raise ZeusError(m)
        return vote

    def sign_vote(self, vote, comments):
        modulus, generator, order = self.do_get_cryptosystem()
        public = self.do_get_zeus_public()
        secret = self.do_get_zeus_secret()
        signature = sign_vote(vote, comments,
                              modulus, generator, order, public, secret)
        verify_vote_signature(signature, modulus, generator, order, public)
        return signature

    def verify_vote(self, vote):
        if 'signature' not in vote:
            m = "No signature found in vote!"
            raise ZeusError(m)
        signature = vote['signature']

        modulus, generator, order = self.do_get_cryptosystem()
        public = self.do_get_zeus_public()
        info = verify_vote_signature(signature, modulus, generator, order, public)
        election, fingerprint, index, previous = info

        if election != self.do_get_election_public():
            m = "Election mismatch in vote!"
            raise ZeusError(m)

        stored = self.do_get_vote(fingerprint)
        if not stored:
            m = "Cannot find verified vote [%s] in store!" % (fingerprint,)
            raise AssertionError(m)

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

    def cast_vote(self, vote):
        self.do_assert_stage('VOTING')
        vote = self.validate_submitted_vote(vote)

        fingerprint = vote['fingerprint']
        audit_request = self.do_get_audit_request(fingerprint)

        voter_key = vote['voter']
        voter = self.do_get_voter(voter_key)
        slots = self.do_get_voter_slots(voter_key)
        if not voter and not slots:
            m = "Invalid voter key!"
            raise ZeusError(m)
        if not voter or not slots:
            m = "Voter slot inconsistency! Invalid Election."
            raise AssertionError(m)

        voter_secret = vote['secret'] if 'secret' in vote else None
        voter_slot = vote['slot'] if 'slot' in vote else None
        if voter_secret:
            # This is an audit publication
            if not voter_slot:
                m = "Invalid audit vote publication! No slot given."
                raise ZeusError(m)
            if voter_slot in slots:
                m = "Invalid audit vote publication! Invalid slot given."
                raise ZeusError(m)
            if voter_key != audit_request:
                m = "Cannot find prior audit request for publish request!"
                raise ZeusError(m)
            vote['previous'] = ''
            vote['index'] = None
            vote['status'] = V_PUBLIC_AUDIT
            comments = self.custom_audit_publication_message(vote)
            signature = self.sign_vote(vote, comments)
            vote['signature'] = signature
            self.do_store_audit_publication(fingerprint)
            self.do_store_votes((vote,))
            return signature

        if not voter_slot:
            skip_audit = self.do_get_option('skip_audit')
            if skip_audit or skip_audit is None:
                # skips auditing for submission simplicity
                voter_slot = slots[0]
            else:
                m = ("Invalid vote submission! "
                     "No slot given but skip_audit is disabled")
                raise ZeusError(m)

        if voter_slot not in slots:
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

        # first index, then sign?!
        vote['previous'] = previous_fingerprint
        vote['status'] = V_CAST_VOTE
        index = self.do_index_vote(fingerprint)
        vote['index'] = index
        comments = self.custom_cast_vote_message(vote)
        signature = self.sign_vote(vote, comments)
        vote['signature'] = signature
        self.do_append_vote(voter_key, fingerprint)
        self.do_store_votes((vote,))
        return signature

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

            current = teller.get_current()

        with teller.task("Validating audit votes",
                         current=current, total=nr_votes):
            audit_votes = self.do_get_audit_publications()
            for audit_vote in audit_votes:
                if audit_vote not in all_votes:
                    m = "Audit vote [%s] not found in vote archive!" % (audit_vote,)
                    raise AssertionError(m)
                vote = all_votes[audit_vote]
                self.verify_vote(vote)
                del all_votes[audit_vote]
                teller.advance()

            current = teller.get_current()

        with teller.task("Validating audit requests",
                         current=current, total=nr_votes):

            all_audit_requests = self.do_get_audit_requests()
            for audit_request in all_audit_requests.iteritems():
                if audit_request not in all_votes:
                    m = ("Audit request [%s] not found in vote archive!"
                        % (audit_request,))
                    raise AssertionError(m)
                vote = all_votes[audit_vote]
                self.verify_vote(vote)
                del all_votes[audit_vote]
                teller.advance()

            current = teller.get_current()

        if all_votes:
            m = "%d unaccounted votes in archive!" % len(all_votes)
            raise AssertionError(m)
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
        return voting

    def extract_votes_for_mixing(self):
        vote_index = self.do_get_vote_index()
        scratch = [None] * len(vote_index)
        do_get_vote = self.do_get_vote
        vote_count = 0

        for i, fingerprint in enumerate(vote_index):
            vote = dict(do_get_vote(fingerprint))
            index = vote['index']
            if i != index:
                m = "Index mismatch %d != %d. Corrupt index!" % (i, index)
                raise AssertionError(m)
            eb = vote['encrypted_ballot']
            _vote = [eb['alpha'], eb['beta']]
            scratch[i] = _vote
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

        votes_for_mixing = [v for v in scratch if v is not None]
        nr_votes = len(votes_for_mixing)
        if nr_votes != vote_count:
            m = ("Vote count mismatch %d != %d. Corrupt index!"
                % (nr_votes, vote_count))
            raise AssertionError(m)

        crypto = self.do_get_cryptosystem()
        modulus, generator, order = crypto
        public = self.do_get_election_public()
        mix = { 'modulus': modulus,
                'generator': generator,
                'order': order,
                'public': public,
                'original_ciphers': votes_for_mixing,
                'mixed_ciphers' : votes_for_mixing }
        return mix

    def set_mixing(self):
        stage = self.do_get_stage()
        if stage == 'MIXING':
            m = "Already in stage 'MIXING'"
            raise ZeusError(m)
        if stage != 'VOTING':
            m = "Cannot transition from stage '%s' to 'MIXING'" % (stage,)
            raise ZeusError(m)

        self.validate_voting()
        votes_for_mixing = self.extract_votes_for_mixing()
        self.do_store_mix(votes_for_mixing)
        self.do_set_stage('MIXING')

    @classmethod
    def new_at_mixing(cls, mixing, teller=_teller):
        self = cls.new_at_voting(mixing, teller=teller)
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
        self.set_mixing()
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

        if not verify_cipher_mix(mix, teller=teller):
            m = "Invalid mix: proof verification failed!"
            raise ZeusError(m)

    def add_mix(self, mix):
        self.do_assert_stage('MIXING')
        self.validate_mix(mix)
        self.do_store_mix(mix)

    def validate_mixing(self):
        teller = self.teller
        teller.task("Validating state: 'MIXING'")

        crypto = self.do_get_cryptosystem()
        previous = None
        mixes = self.do_get_all_mixes()
        min_mixes = self.get_option('min_mixes') or 2
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

                    if not verify_cipher_mix(mix, teller=teller):
                        m = "Invalid mix proof"
                        raise AssertionError(m)

                    teller.advance()
                else:
                    votes_for_mixing = self.extract_votes_for_mixing()
                    original_ciphers = mix['original_ciphers']
                    if original_ciphers != votes_for_mixing['original_ciphers']:
                        m = "Invalid first mix: Does not mix votes in archive!"
                        raise AssertionError(m)

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

        self.validate_mixing()
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
        return decrypting

    @classmethod
    def new_at_decrypting(cls, decrypting, teller=_teller):
        self = cls.new_at_mixing(decrypting, teller=teller)
        for mix in decrypting['mixes']:
            self.do_store_mix(mix)
        if 'trustee_factors' in decrypting:
            all_trustee_factors = decrypting['trustee_factors']
            for trustee_factors in all_trustee_factors:
                self.do_store_trustee_factors(trustee_factors)
        self.set_decrypting()
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
        if not verify_decryption_factors(modulus, generator, order,
                                         trustee_public,
                                         ciphers, factors, teller=teller):
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

            factors = all_factors[trustee]
            if not verify_decryption_factors(modulus, generator, order,
                                             trustee, mixed_ballots, factors,
                                             teller=teller):
                m = "Invalid trustee factors proof!"
                raise ZeusError(m)

        teller.finish()

    def decrypt_ballots(self):
        mixed_ballots = self.get_mixed_ballots()
        all_factors = self.do_get_all_trustee_factors().values()
        crypto = self.do_get_cryptosystem()
        modulus, generator, order = crypto
        decryption_factors = combine_decryption_factors(modulus, all_factors)
        plaintexts = []
        append = plaintexts.append

        for ballot, factor in izip(mixed_ballots, decryption_factors):
            plaintext = decrypt_with_decryptor(modulus, generator, order,
                                               ballot[BETA], factor)
            append(plaintext)

        self.do_store_results(plaintexts)
        return plaintexts

    def set_finished(self):
        stage = self.do_get_stage()
        if stage == 'FINISHED':
            m = "Already in stage 'FINISHED'"
            raise ZeusError(m)
        if stage != 'DECRYPTING':
            m = "Cannot transition from stage '%s' to 'FINISHED'" % (stage,)
            raise ZeusError(m)

        self.validate_decrypting()
        old_results = self.do_get_results()
        results = self.decrypt_ballots()
        if old_results and old_results != results:
            m = "Old results did not match new results!"
            raise AssertionError(m)

        self.do_set_stage('FINISHED')

    def export_finished(self):
        stage = self.do_get_stage()
        if stage != 'FINISHED':
            m = ("Stage 'FINISHED' must have been reached "
                 "before it can be exported")
            raise ZeusError(m)

        finished = self.export_decrypting()
        finished['results'] = self.do_get_results()
        return finished

    @classmethod
    def new_at_finished(cls, finished, teller=_teller):
        self = cls.new_at_decrypting(finished, teller=teller)
        self.do_store_results(finished['results'])
        self.set_finished()
        return self

    def get_results(self):
        self.do_assert_stage('FINISHED')
        results = self.do_get_results()
        return results

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

    def mk_random_vote(self, selection=None, voter=None, slot=None, audit=None):
        modulus, generator, order = self.do_get_cryptosystem()
        public = self.do_get_election_public()
        candidates = self.do_get_candidates()
        nr_candidates = len(candidates)
        if selection is None:
            selection = get_random_selection(nr_candidates)
        voters = None
        if voter is None:
            voters = self.do_get_voters()
            voter = choice(voters.keys())
        encoded = encode_selection(selection)
        vote = vote_from_encoded(modulus, generator, order, public,
                                 voter, encoded, nr_candidates)
        if audit:
            if voters is None:
                voters = self.do_get_voters()
            if slot is None:
                if voter not in voters:
                    m = ("Given slot audit vote requested but voter "
                         "could not be found!")
                    raise ValueError(m)
                slot = voters[voter][0]
            else:
                if voter not in voters:
                    encoded = None
                elif slot not in voters[voter]:
                    encoded = None
            vote['slot'] = slot
        return vote, selection, encoded

    @classmethod
    def mk_random(cls,  nr_candidates   =   3,
                        nr_trustees     =   2,
                        nr_voters       =   10,
                        nr_votes        =   10,
                        nr_mixes        =   2,
                        nr_rounds       =   8,
                        teller          =   _teller):

        with teller.task("Creating election"):
            candidate_range = xrange(nr_candidates)
            candidates = [("Candidate #%d" % x) for x in candidate_range]
            voter_range = xrange(nr_voters)
            voters = [("Voter #%d" % x) for x in voter_range]

            self = cls(teller=teller)
            election = self
            self.create_zeus_key()
            self.add_candidates(*candidates)
            self.add_voters(*voters)

            trustees = [self.mk_random_trustee() for _ in xrange(nr_trustees)]
            for trustee in trustees:
                self.add_trustee(key_public(trustee), key_proof(trustee))

            trustees = [self.mk_reprove_trustee(key_public(t), key_secret(t))
                        for t in trustees]
            for trustee in trustees:
                self.reprove_trustee(key_public(trustee), key_proof(trustee))

            self._trustees = trustees
            self.set_voting()

        crypto = self.do_get_cryptosystem()
        modulus, generator, order = self.do_get_cryptosystem()

        teller.task("Voting")
        with teller.task("Generating and casting votes", total=nr_votes):
            selections = []
            plaintexts = {}
            votes = []
            for _ in xrange(nr_votes):
                vote, selection, encoded = self.mk_random_vote()
                selections.append(selection)
                if encoded is not None:
                    plaintexts[vote['voter']] = encoded
                votes.append(vote)
                self.cast_vote(vote)
                teller.advance()
            self._selections = selections
            self._plaintexts = plaintexts
            self._votes = votes

        with teller.active():
            self.set_mixing()

        with teller.task("Mixing", total=nr_mixes):
            for _ in xrange(nr_mixes):
                cipher_collection = self.get_last_mix()
                mixed_collection = mix_ciphers(cipher_collection,
                                               nr_rounds=nr_rounds,
                                               teller=teller)
                self.add_mix(mixed_collection)
                teller.advance()

        self.set_decrypting()

        with teller.task("Decrypting"):
            ciphers = self.get_mixed_ballots()
            with teller.task("Calculating and adding decryption factors",
                             total=nr_trustees):
                for trustee in trustees:
                    factors = compute_decryption_factors(
                                        modulus, generator, order,
                                        key_secret(trustee), ciphers,
                                        teller=teller)
                    trustee_factors = {'trustee_public': key_public(trustee),
                                       'decryption_factors': factors,
                                       'modulus': modulus,
                                       'generator': generator,
                                       'order': order}
                    self.add_trustee_factors(trustee_factors)
                    teller.advance()
            self.set_finished()

        with teller.task("Validating results"):
            results = self.get_results()
            if sorted(results) != sorted(self._plaintexts.values()):
                m = ("Invalid Election! "
                     "Casted plaintexts do not match plaintext results!")
                raise AssertionError(m)

        return self


def main():
    import argparse
    description='Zeus Election Reference Implementation and Verifier.'
    epilog="Try 'zeus --generate'"
    parser = argparse.ArgumentParser(description=description, epilog=epilog)

    parser.add_argument('--verbose', action='store_true', default=True,
        help=("Write validation, verification, and notice messages "
              "to standard error"))

    parser.add_argument('--quiet', action='store_false', dest='verbose',
        help=("Be quiet. Cancel --verbose"))

    parser.add_argument('--validate', metavar='infile',
        help="Read a FINISHED election from a JSON file and validate it")

    parser.add_argument('--mix', nargs=2, metavar=('infile', 'outfile'),
        help=("Read a MIXING election from the input file, mix it, "
              "and write the mix to the output file"))

    parser.add_argument('--generate', nargs='*', metavar='outfile',
        help="Generate a random election and write it out in JSON")

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
                        help="Generate: Number of votes")

    parser.add_argument('--mixes', type=int, default=2,
                        dest='nr_mixes',
                        help="Generate: Number of times to mix")

    parser.add_argument('--rounds', type=int, default=3,
                        dest='nr_rounds',
                        help="Generate or Mix: Number of mix rounds")

    args = parser.parse_args()

    class Nullstream(object):
        def read(*args):
            return ''
        def write(*args):
            return

    outstream = sys.stderr if args.verbose else Nullstream()
    teller = Teller(outstream=outstream)
    import json

    if args.generate is not None:
        filename = args.generate
        filename = filename[0] if filename else None

        election = ZeusCoreElection.mk_random(
                            nr_candidates   =   args.nr_candidates,
                            nr_trustees     =   args.nr_trustees,
                            nr_voters       =   args.nr_voters,
                            nr_votes        =   args.nr_votes,

                            teller=teller)
        finished = election.export_finished()
        if not filename:
            name = ("%x" % election.do_get_election_public())[:32]
            filename = 'election-%s.json' % (name,)
            sys.stderr.write("writing out to '%s'\n" % (filename,))
        with open(filename, "w") as f:
            json.dump(finished, f, indent=2)
        return

    if args.validate:
        filename = args.validate
        with open(filename, "r") as f:
            finished = json.load(f)
        election = ZeusCoreElection.new_at_finished(finished, teller=teller)
        return

    if args.mix:
        infile, outfile = args.mix
        with open(infile, "r") as f:
            mixing = json.load(f)

        #election = ZeusCoreElection.new_at_mixing(mixing, teller=teller)
        #cipher_collection = election.get_last_mix()
        #mixed_collection = mix_ciphers(cipher_collection, teller=teller)
        #election.add_mix(mixed_collection)
        #mixed_ballots = election.get_mixed_ballots()

        last_mix = mixing['mixes'][-1]
        ciphers_to_mix = pk_no_proof_from_args(*pk_args(last_mix))
        ciphers_to_mix['mixed_ciphers'] = last_mix['mixed_ciphers']
        mixed_ciphers = mix_ciphers(ciphers_to_mix, nr_rounds=args.nr_rounds,
                                    teller=teller)
        with open(outfile, "w") as f:
            json.dump(mixed_ciphers, f, indent=2)
        return

    parser.print_help()
    return

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

    cfm = { 'modulus': p,
            'generator': g,
            'order': q,
            'public': pk,
            'original_ciphers': cts,
            'mixed_ciphers': cts, }

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

if __name__ == '__main__':
    #verify_gamma_encoding(7)
    #cross_check_encodings(7)
    #test_decryption()
    main()

