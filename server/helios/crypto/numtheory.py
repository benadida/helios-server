##################################################
# ent.py -- Element Number Theory 
# (c) William Stein, 2004
##################################################




from random import randrange
from math import log, sqrt




##################################################
## Greatest Common Divisors
##################################################

def gcd(a, b):                                        # (1)
    """
    Returns the greatest commond divisor of a and b.
    Input:
        a -- an integer
        b -- an integer
    Output:
        an integer, the gcd of a and b
    Examples:
    >>> gcd(97,100)
    1
    >>> gcd(97 * 10**15, 19**20 * 97**2)              # (2)
    97L
    """
    if a < 0:  a = -a
    if b < 0:  b = -b
    if a == 0: return b
    if b == 0: return a
    while b != 0: 
        (a, b) = (b, a%b)
    return a



##################################################
## Enumerating Primes
##################################################

def primes(n):
    """
    Returns a list of the primes up to n, computed 
    using the Sieve of Eratosthenes.
    Input:
        n -- a positive integer
    Output:
        list -- a list of the primes up to n
    Examples:
    >>> primes(10)
    [2, 3, 5, 7]
    >>> primes(45)
    [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43]
    """
    if n <= 1: return []
    X = [i for i in range(3,n+1) if i%2 != 0]     # (1)
    P = [2]                                       # (2)
    sqrt_n = sqrt(n)                              # (3)
    while len(X) > 0 and X[0] <= sqrt_n:          # (4)
        p = X[0]                                  # (5)
        P.append(p)                               # (6)
        X = [a for a in X if a%p != 0]            # (7)
    return P + X                                  # (8)




##################################################
## Integer Factorization
##################################################

def trial_division(n, bound=None):
    """
    Return the smallest prime divisor <= bound of the 
    positive integer n, or n if there is no such prime.  
    If the optional argument bound is omitted, then bound=n.
    Input:
        n -- a positive integer
        bound - (optional) a positive integer
    Output:
        int -- a prime p<=bound that divides n, or n if
               there is no such prime.
    Examples:
    >>> trial_division(15)
    3
    >>> trial_division(91)
    7
    >>> trial_division(11)
    11
    >>> trial_division(387833, 300)   
    387833
    >>> # 300 is not big enough to split off a 
    >>> # factor, but 400 is.
    >>> trial_division(387833, 400)  
    389
    """
    if n == 1: return 1
    for p in [2, 3, 5]:
        if n%p == 0: return p
    if bound == None: bound = n
    dif = [6, 4, 2, 4, 2, 4, 6, 2]
    m = 7; i = 1
    while m <= bound and m*m <= n:
        if n%m == 0:
            return m
        m += dif[i%8]
        i += 1
    return n

def factor(n):
    """
    Returns the factorization of the integer n as 
    a sorted list of tuples (p,e), where the integers p
    are output by the split algorithm.  
    Input:
        n -- an integer
    Output:
        list -- factorization of n
    Examples:
    >>> factor(500)
    [(2, 2), (5, 3)]
    >>> factor(-20)
    [(2, 2), (5, 1)]
    >>> factor(1)
    []
    >>> factor(2004)
    [(2, 2), (3, 1), (167, 1)]
    """
    if n in [-1, 0, 1]: return []
    if n < 0: n = -n
    F = []
    while n != 1:
        p = trial_division(n)
        e = 1
        n /= p
        while n%p == 0:
            e += 1; n /= p
        F.append((p,e))
    F.sort()
    return F



##################################################
## Linear Equations Modulo $n$
##################################################

def xgcd(a, b):
    """
    Returns g, x, y such that g = x*a + y*b = gcd(a,b).
    Input:
        a -- an integer
        b -- an integer
    Output:
        g -- an integer, the gcd of a and b
        x -- an integer
        y -- an integer
    Examples:
    >>> xgcd(2,3)
    (1, -1, 1)
    >>> xgcd(10, 12)
    (2, -1, 1)
    >>> g, x, y = xgcd(100, 2004)
    >>> print g, x, y
    4 -20 1
    >>> print x*100 + y*2004
    4
    """
    if a == 0 and b == 0: return (0, 0, 1)
    if a == 0: return (abs(b), 0, b/abs(b))
    if b == 0: return (abs(a), a/abs(a), 0)
    x_sign = 1; y_sign = 1
    if a < 0: a = -a; x_sign = -1
    if b < 0: b = -b; y_sign = -1
    x = 1; y = 0; r = 0; s = 1
    while b != 0:
        (c, q) = (a%b, a/b)
        (a, b, r, s, x, y) = (b, c, x-q*r, y-q*s, r, s)
    return (a, x*x_sign, y*y_sign)

def inversemod(a, n):
    """
    Returns the inverse of a modulo n, normalized to
    lie between 0 and n-1.  If a is not coprime to n,
    raise an exception (this will be useful later for 
    the elliptic curve factorization method).
    Input:
        a -- an integer coprime to n
        n -- a positive integer
    Output:
        an integer between 0 and n-1.
    Examples:
    >>> inversemod(1,1)
    0
    >>> inversemod(2,5)
    3
    >>> inversemod(5,8)
    5
    >>> inversemod(37,100)
    73
    """
    g, x, y = xgcd(a, n)
    if g != 1:
        raise ZeroDivisionError, (a,n)
    assert g == 1, "a must be coprime to n."
    return x%n

def solve_linear(a,b,n):
    """
    If the equation ax = b (mod n) has a solution, return a 
    solution normalized to lie between 0 and n-1, otherwise
    returns None.
    Input:
        a -- an integer
        b -- an integer
        n -- an integer
    Output:
        an integer or None
    Examples:
    >>> solve_linear(4, 2, 10)
    8
    >>> solve_linear(2, 1, 4) == None
    True
    """
    g, c, _ = xgcd(a,n)                 # (1)
    if b%g != 0: return None
    return ((b/g)*c) % n                

def crt(a, b, m, n):
    """
    Return the unique integer between 0 and m*n - 1 
    that reduces to a modulo n and b modulo m, where
    the integers m and n are coprime. 
    Input:
        a, b, m, n -- integers, with m and n coprime
    Output:
        int -- an integer between 0 and m*n - 1.
    Examples:
    >>> crt(1, 2, 3, 4)
    10
    >>> crt(4, 5, 10, 3)
    14
    >>> crt(-1, -1, 100, 101)
    10099
    """
    g, c, _ = xgcd(m, n)                       
    assert g == 1, "m and n must be coprime."
    return (a + (b-a)*c*m) % (m*n)


##################################################
## Computation of Powers
##################################################

def powermod(a, m, n):
    """
    The m-th power of a modulo n.
    Input:
        a -- an integer
        m -- a nonnegative integer
        n -- a positive integer
    Output:
        int -- an integer between 0 and n-1
    Examples:
    >>> powermod(2,25,30)
    2
    >>> powermod(19,12345,100)
    99
    """
    assert m >= 0, "m must be nonnegative."   # (1)
    assert n >= 1, "n must be positive."      # (2)
    ans = 1
    apow = a
    while m != 0:
        if m%2 != 0:
            ans = (ans * apow) % n            # (3)
        apow = (apow * apow) % n              # (4)
        m /= 2   
    return ans % n


##################################################
## Finding a Primitive Root
##################################################

def primitive_root(p):
    """
    Returns first primitive root modulo the prime p.
    (If p is not prime, this return value of this function
    is not meaningful.)
    Input:
        p -- an integer that is assumed prime
    Output:
        int -- a primitive root modulo p
    Examples:
    >>> primitive_root(7)
    3
    >>> primitive_root(389)
    2
    >>> primitive_root(5881)
    31
    """
    if p == 2: return 1
    F = factor(p-1)
    a = 2
    while a < p:
        generates = True
        for q, _ in F:
            if powermod(a, (p-1)/q, p) == 1:
                generates = False
                break
        if generates: return a
        a += 1
    assert False, "p must be prime."


##################################################
## Determining Whether a Number is Prime
##################################################

def is_pseudoprime(n, bases = [2,3,5,7]):
    """
    Returns True if n is a pseudoprime to the given bases,
    in the sense that n>1 and b**(n-1) = 1 (mod n) for each 
    elements b of bases, with b not a multiple of n, and 
    False otherwise.   
    Input:
        n -- an integer
        bases -- a list of integers
    Output:
        bool 
    Examples:
    >>> is_pseudoprime(91)
    False
    >>> is_pseudoprime(97)
    True
    >>> is_pseudoprime(1)
    False
    >>> is_pseudoprime(-2)
    True
    >>> s = [x for x in range(10000) if is_pseudoprime(x)]
    >>> t = primes(10000)
    >>> s == t 
    True
    >>> is_pseudoprime(29341) # first non-prime pseudoprime
    True
    >>> factor(29341)
    [(13, 1), (37, 1), (61, 1)]
    """
    if n < 0: n = -n                                
    if n <= 1: return False
    for b in bases:                       
        if b%n != 0 and powermod(b, n-1, n) != 1:       
            return False
    return True


def miller_rabin(n, num_trials=4):
    """
    True if n is likely prime, and False if n 
    is definitely not prime.  Increasing num_trials
    increases the probability of correctness.
    (One can prove that the probability that this 
    function returns True when it should return
    False is at most (1/4)**num_trials.)
    Input:
        n -- an integer
        num_trials -- the number of trials with the 
                      primality test.   
    Output:
        bool -- whether or not n is probably prime.
    Examples:    
    >>> miller_rabin(91)
    False                         #rand
    >>> miller_rabin(97)
    True                          #rand
    >>> s = [x for x in range(1000) if miller_rabin(x, 1)]
    >>> t = primes(1000)
    >>> print len(s), len(t)  # so 1 in 25 wrong
    175 168                       #rand
    >>> s = [x for x in range(1000) if miller_rabin(x)]
    >>> s == t                    
    True                          #rand
    """
    if n < 0: n = -n
    if n in [2,3]: return True
    if n <= 4: return False
    m = n - 1
    k = 0
    while m%2 == 0:
        k += 1; m /= 2
    # Now n - 1 = (2**k) * m with m odd
    for i in range(num_trials):
        a = randrange(2,n-1)                  # (1)
        apow = powermod(a, m, n)
        if not (apow in [1, n-1]):            
            some_minus_one = False
            for r in range(k-1):              # (2)
                apow = (apow**2)%n
                if apow == n-1:
                    some_minus_one = True
                    break                     # (3)
        if (apow in [1, n-1]) or some_minus_one:
            prob_prime = True
        else:
            return False
    return True


##################################################
## The Diffie-Hellman Key Exchange
##################################################

def random_prime(num_digits, is_prime = miller_rabin):
    """
    Returns a random prime with num_digits digits.
    Input:
        num_digits -- a positive integer
        is_prime -- (optional argment)
                    a function of one argument n that
                    returns either True if n is (probably)
                    prime and False otherwise.
    Output:
        int -- an integer
    Examples:
    >>> random_prime(10)
    8599796717L              #rand
    >>> random_prime(40)
    1311696770583281776596904119734399028761L  #rand
    """ 
    n = randrange(10**(num_digits-1), 10**num_digits)
    if n%2 == 0: n += 1
    while not is_prime(n): n += 2
    return n

def dh_init(p):
    """
    Generates and returns a random positive
    integer n < p and the power 2^n (mod p). 
    Input:
        p -- an integer that is prime
    Output:
        int -- a positive integer < p,  a secret
        int -- 2^n (mod p), send to other user
    Examples:
    >>> p = random_prime(20)
    >>> dh_init(p)
    (15299007531923218813L, 4715333264598442112L)   #rand
    """
    n = randrange(2,p)
    return n, powermod(2,n,p)

def dh_secret(p, n, mpow):
    """
    Computes the shared Diffie-Hellman secret key.
    Input:
        p -- an integer that is prime
        n -- an integer: output by dh_init for this user
        mpow-- an integer: output by dh_init for other user
    Output:
        int -- the shared secret key.
    Examples:
    >>> p = random_prime(20)
    >>> n, npow = dh_init(p)    
    >>> m, mpow = dh_init(p)
    >>> dh_secret(p, n, mpow) 
    15695503407570180188L      #rand
    >>> dh_secret(p, m, npow)    
    15695503407570180188L      #rand
    """
    return powermod(mpow,n,p)






##################################################
## Encoding Strings as Lists of Integers
##################################################

def str_to_numlist(s, bound):
    """
    Returns a sequence of integers between 0 and bound-1 
    that encodes the string s.   Randomization is included, 
    so the same string is very likely to encode differently 
    each time this function is called. 
    Input:
        s -- a string
        bound -- an integer >= 256
    Output:
        list -- encoding of s as a list of integers 
    Examples:
    >>> str_to_numlist("Run!", 1000)
    [82, 117, 110, 33]               #rand
    >>> str_to_numlist("TOP SECRET", 10**20)
    [4995371940984439512L, 92656709616492L]   #rand
    """
    assert bound >= 256, "bound must be at least 256."
    n = int(log(bound) / log(256))          # (1)
    salt = min(int(n/8) + 1, n-1)           # (2)
    i = 0; v = []
    while i < len(s):                       # (3)
        c = 0; pow = 1
        for j in range(n):                  # (4)
            if j < salt:
                c += randrange(1,256)*pow   # (5)
            else:
                if i >= len(s): break 
                c += ord(s[i])*pow          # (6)
                i += 1
            pow *= 256                      
        v.append(c)
    return v

def numlist_to_str(v, bound):
    """
    Returns the string that the sequence v of 
    integers encodes. 
    Input:
        v -- list of integers between 0 and bound-1
        bound -- an integer >= 256
    Output:
        str -- decoding of v as a string
    Examples:
    >>> print numlist_to_str([82, 117, 110, 33], 1000)
    Run!
    >>> x = str_to_numlist("TOP SECRET MESSAGE", 10**20)
    >>> print numlist_to_str(x, 10**20)
    TOP SECRET MESSAGE
    """
    assert bound >= 256, "bound must be at least 256."
    n = int(log(bound) / log(256))
    s = ""
    salt = min(int(n/8) + 1, n-1)
    for x in v:
        for j in range(n):
            y = x%256
            if y > 0 and j >= salt:
                s += chr(y)
            x /= 256
    return s


##################################################
## The RSA Cryptosystem
##################################################

def rsa_init(p, q):
    """
    Returns defining parameters (e, d, n) for the RSA
    cryptosystem defined by primes p and q.  The
    primes p and q may be computed using the 
    random_prime functions.
    Input:
        p -- a prime integer
        q -- a prime integer
    Output:
        Let m be (p-1)*(q-1). 
        e -- an encryption key, which is a randomly
             chosen integer between 2 and m-1
        d -- the inverse of e modulo eulerphi(p*q), 
             as an integer between 2 and m-1
        n -- the product p*q.
    Examples:
    >>> p = random_prime(20); q = random_prime(20)
    >>> print p, q
    37999414403893878907L 25910385856444296437L #rand
    >>> e, d, n = rsa_init(p, q)
    >>> e
    5                                           #rand
    >>> d
    787663591619054108576589014764921103213L    #rand
    >>> n
    984579489523817635784646068716489554359L    #rand
    """
    m = (p-1)*(q-1)
    e = 3
    while gcd(e, m) != 1: e += 1
    d = inversemod(e, m)                  
    return e, d, p*q

def rsa_encrypt(plain_text, e, n):
    """
    Encrypt plain_text using the encrypt
    exponent e and modulus n.  
    Input:
        plain_text -- arbitrary string
        e -- an integer, the encryption exponent
        n -- an integer, the modulus
    Output:
        str -- the encrypted cipher text
    Examples:
    >>> e = 1413636032234706267861856804566528506075
    >>> n = 2109029637390047474920932660992586706589
    >>> rsa_encrypt("Run Nikita!", e, n)
    [78151883112572478169375308975376279129L]    #rand
    >>> rsa_encrypt("Run Nikita!", e, n)
    [1136438061748322881798487546474756875373L]  #rand
    """
    plain = str_to_numlist(plain_text, n)
    return [powermod(x, e, n) for x in plain]

def rsa_decrypt(cipher, d, n):
    """
    Decrypt the cipher_text using the decryption
    exponent d and modulus n.
    Input:
        cipher_text -- list of integers output 
                       by rsa_encrypt
    Output:
        str -- the unencrypted plain text
    Examples:
    >>> d = 938164637865370078346033914094246201579
    >>> n = 2109029637390047474920932660992586706589
    >>> msg1 = [1071099761433836971832061585353925961069]
    >>> msg2 = [1336506586627416245118258421225335020977]
    >>> rsa_decrypt(msg1, d, n)
    'Run Nikita!'
    >>> rsa_decrypt(msg2, d, n)
    'Run Nikita!'
    """
    plain = [powermod(x, d, n) for x in cipher]
    return numlist_to_str(plain, n)


##################################################
## Computing the Legendre Symbol
##################################################

def legendre(a, p):
    """
    Returns the Legendre symbol a over p, where
    p is an odd prime.
    Input:
        a -- an integer
        p -- an odd prime (primality not checked)
    Output:
        int: -1 if a is not a square mod p,
              0 if gcd(a,p) is not 1
              1 if a is a square mod p.
    Examples:
    >>> legendre(2, 5)
    -1
    >>> legendre(3, 3)
    0
    >>> legendre(7, 2003)
    -1
    """
    assert p%2 == 1, "p must be an odd prime."
    b = powermod(a, (p-1)/2, p)
    if b == 1: return 1
    elif b == p-1: return -1
    return 0


##################################################
## In this section we implement the algorithm
##################################################

def sqrtmod(a, p):
    """
    Returns a square root of a modulo p.
    Input:
        a -- an integer that is a perfect 
             square modulo p (this is checked)
        p -- a prime
    Output:
        int -- a square root of a, as an integer
               between 0 and p-1.
    Examples:
    >>> sqrtmod(4, 5)              # p == 1 (mod 4)
    3              #rand
    >>> sqrtmod(13, 23)            # p == 3 (mod 4)
    6              #rand
    >>> sqrtmod(997, 7304723089)   # p == 1 (mod 4)
    761044645L     #rand
    """
    a %= p
    if p == 2: return a 
    assert legendre(a, p) == 1, "a must be a square mod p."
    if p%4 == 3: return powermod(a, (p+1)/4, p)

    def mul(x, y):   # multiplication in R       # (1)
        return ((x[0]*y[0] + a*y[1]*x[1]) % p, \
                (x[0]*y[1] + x[1]*y[0]) % p)
    def pow(x, n):   # exponentiation in R       # (2)
        ans = (1,0)
        xpow = x
        while n != 0:
           if n%2 != 0: ans = mul(ans, xpow)
           xpow = mul(xpow, xpow)
           n /= 2
        return ans

    while True:
        z = randrange(2,p)
        u, v = pow((1,z), (p-1)/2)
        if v != 0:
            vinv = inversemod(v, p)
            for x in [-u*vinv, (1-u)*vinv, (-1-u)*vinv]:
                if (x*x)%p == a: return x%p
            assert False, "Bug in sqrtmod."


##################################################
## Continued Fractions
##################################################

def convergents(v):
    """
    Returns the partial convergents of the continued 
    fraction v.
    Input:
        v -- list of integers [a0, a1, a2, ..., am]
    Output:
        list -- list [(p0,q0), (p1,q1), ...] 
                of pairs (pm,qm) such that the mth 
                convergent of v is pm/qm.
    Examples:
    >>> convergents([1, 2])
    [(1, 1), (3, 2)]
    >>> convergents([3, 7, 15, 1, 292])
    [(3, 1), (22, 7), (333, 106), (355, 113), (103993, 33102)]
    """
    w = [(0,1), (1,0)]
    for n in range(len(v)):
        pn = v[n]*w[n+1][0] + w[n][0]
        qn = v[n]*w[n+1][1] + w[n][1]
        w.append((pn, qn))
    del w[0]; del w[0]  # remove first entries of w
    return w

def contfrac_rat(numer, denom):
    """
    Returns the continued fraction of the rational 
    number numer/denom.
    Input:
        numer -- an integer
        denom -- a positive integer coprime to num
    Output
        list -- the continued fraction [a0, a1, ..., am]
                of the rational number num/denom.
    Examples:
    >>> contfrac_rat(3, 2)
    [1, 2]
    >>> contfrac_rat(103993, 33102)
    [3, 7, 15, 1, 292]
    """
    assert denom > 0, "denom must be positive"
    a = numer; b = denom
    v = []
    while b != 0:
        v.append(a/b)
        (a, b) = (b, a%b)
    return v

def contfrac_float(x):
    """
    Returns the continued fraction of the floating
    point number x, computed using the continued
    fraction procedure, and the sequence of partial
    convergents.
    Input:
        x -- a floating point number (decimal)
    Output:
        list -- the continued fraction [a0, a1, ...]
                obtained by applying the continued 
                fraction procedure to x to the 
                precision of this computer.
        list -- the list [(p0,q0), (p1,q1), ...] 
                of pairs (pm,qm) such that the mth 
                convergent of continued fraction 
                is pm/qm.
    Examples:
    >>> v, w = contfrac_float(3.14159); print v
    [3, 7, 15, 1, 25, 1, 7, 4]
    >>> v, w = contfrac_float(2.718); print v
    [2, 1, 2, 1, 1, 4, 1, 12]
    >>> contfrac_float(0.3)
    ([0, 3, 2, 1], [(0, 1), (1, 3), (2, 7), (3, 10)])
    """
    v = []
    w = [(0,1), (1,0)] # keep track of convergents
    start = x
    while True:
        a = int(x)                                  # (1)
        v.append(a)
        n = len(v)-1
        pn = v[n]*w[n+1][0] + w[n][0]
        qn = v[n]*w[n+1][1] + w[n][1]
        w.append((pn, qn))
        x -= a
        if abs(start - float(pn)/float(qn)) == 0:    # (2)
            del w[0]; del w[0]                       # (3)
            return v, w
        x = 1/x

def sum_of_two_squares(p):
    """
    Uses continued fractions to efficiently compute 
    a representation of the prime p as a sum of
    two squares.   The prime p must be 1 modulo 4.
    Input:
        p -- a prime congruent 1 modulo 4.
    Output:
        integers a, b such that p is a*a + b*b
    Examples:
    >>> sum_of_two_squares(5)
    (1, 2)
    >>> sum_of_two_squares(389)
    (10, 17)
    >>> sum_of_two_squares(86295641057493119033)
    (789006548L, 9255976973L)
    """
    assert p%4 == 1, "p must be 1 modulo 4"
    r = sqrtmod(-1, p)                                # (1)
    v = contfrac_rat(-r, p)                           # (2)
    n = int(sqrt(p))                          
    for a, b in convergents(v):                       # (3)
        c = r*b + p*a                                 # (4)
        if -n <= c and c <= n: return (abs(b),abs(c))
    assert False, "Bug in sum_of_two_squares."        # (5)


##################################################
## Arithmetic
##################################################

def ellcurve_add(E, P1, P2):
    """
    Returns the sum of P1 and P2 on the elliptic 
    curve E.
    Input:
         E -- an elliptic curve over Z/pZ, given by a 
              triple of integers (a, b, p), with p odd.
         P1 --a pair of integers (x, y) or the 
              string "Identity".
         P2 -- same type as P1
    Output:
         R -- same type as P1
    Examples:
    >>> E = (1, 0, 7)   # y**2 = x**3 + x over Z/7Z
    >>> P1 = (1, 3); P2 = (3, 3)
    >>> ellcurve_add(E, P1, P2)
    (3, 4)
    >>> ellcurve_add(E, P1, (1, 4))
    'Identity'
    >>> ellcurve_add(E, "Identity", P2)
    (3, 3)
    """ 
    a, b, p = E
    assert p > 2, "p must be odd."
    if P1 == "Identity": return P2
    if P2 == "Identity": return P1
    x1, y1 = P1; x2, y2 = P2
    x1 %= p; y1 %= p; x2 %= p; y2 %= p
    if x1 == x2 and y1 == p-y2: return "Identity"
    if P1 == P2:
        if y1 == 0: return "Identity"
        lam = (3*x1**2+a) * inversemod(2*y1,p)
    else:
        lam = (y1 - y2) * inversemod(x1 - x2, p)
    x3 = lam**2 - x1 - x2
    y3 = -lam*x3 - y1 + lam*x1
    return (x3%p, y3%p)

def ellcurve_mul(E, m, P):
    """
    Returns the multiple m*P of the point P on 
    the elliptic curve E.
    Input:
        E -- an elliptic curve over Z/pZ, given by a 
             triple (a, b, p).
        m -- an integer
        P -- a pair of integers (x, y) or the 
             string "Identity"
    Output:
        A pair of integers or the string "Identity".
    Examples:
    >>> E = (1, 0, 7)
    >>> P = (1, 3)
    >>> ellcurve_mul(E, 5, P)
    (1, 3)
    >>> ellcurve_mul(E, 9999, P)
    (1, 4)
    """   
    assert m >= 0, "m must be nonnegative."
    power = P
    mP = "Identity"
    while m != 0:
        if m%2 != 0: mP = ellcurve_add(E, mP, power)
        power = ellcurve_add(E, power, power)
        m /= 2
    return mP


##################################################
## Integer Factorization
##################################################

def lcm_to(B):
    """
    Returns the least common multiple of all 
    integers up to B.
    Input:
        B -- an integer
    Output:
        an integer
    Examples:
    >>> lcm_to(5)
    60
    >>> lcm_to(20)
    232792560
    >>> lcm_to(100)
    69720375229712477164533808935312303556800L
    """
    ans = 1
    logB = log(B)
    for p in primes(B):
        ans *= p**int(logB/log(p))
    return ans

def pollard(N, m):
    """
    Use Pollard's (p-1)-method to try to find a
    nontrivial divisor of N.
    Input:
        N -- a positive integer
        m -- a positive integer, the least common
             multiple of the integers up to some 
             bound, computed using lcm_to.
    Output:
        int -- an integer divisor of n
    Examples:
    >>> pollard(5917, lcm_to(5))
    61
    >>> pollard(779167, lcm_to(5))
    779167
    >>> pollard(779167, lcm_to(15))
    2003L
    >>> pollard(187, lcm_to(15))
    11
    >>> n = random_prime(5)*random_prime(5)*random_prime(5)
    >>> pollard(n, lcm_to(100))
    315873129119929L     #rand
    >>> pollard(n, lcm_to(1000))
    3672986071L          #rand
    """
    for a in [2, 3]:
        x = powermod(a, m, N) - 1
        g = gcd(x, N)
        if g != 1 and g != N:
            return g
    return N

def randcurve(p):
    """
    Construct a somewhat random elliptic curve 
    over Z/pZ and a random point on that curve.
    Input:
        p -- a positive integer
    Output:
        tuple -- a triple E = (a, b, p) 
        P -- a tuple (x,y) on E
    Examples:
    >>> p = random_prime(20); p
    17758176404715800329L    #rand
    >>> E, P = randcurve(p)
    >>> print E
    (15299007531923218813L, 1, 17758176404715800329L)  #rand
    >>> print P
    (0, 1)
    """
    assert p > 2, "p must be > 2."
    a = randrange(p)
    while gcd(4*a**3 + 27, p) != 1:
        a = randrange(p)
    return (a, 1, p), (0,1)

def elliptic_curve_method(N, m, tries=5):
    """
    Use the elliptic curve method to try to find a
    nontrivial divisor of N.
    Input:
        N -- a positive integer
        m -- a positive integer, the least common
             multiple of the integers up to some
             bound, computed using lcm_to.
        tries -- a positive integer, the number of
             different elliptic curves to try
    Output:
        int -- a divisor of n
    Examples:
    >>> elliptic_curve_method(5959, lcm_to(20))
    59L       #rand
    >>> elliptic_curve_method(10007*20011, lcm_to(100))
    10007L   #rand
    >>> p = random_prime(9); q = random_prime(9)
    >>> n = p*q; n
    117775675640754751L   #rand
    >>> elliptic_curve_method(n, lcm_to(100))
    117775675640754751L   #rand
    >>> elliptic_curve_method(n, lcm_to(500))
    117775675640754751L   #rand
    """
    for _ in range(tries):                     # (1)
        E, P = randcurve(N)                    # (2)
        try:                                   # (3)
            Q = ellcurve_mul(E, m, P)          # (4)
        except ZeroDivisionError, x:           # (5)
            g = gcd(x[0],N)                    # (6)
            if g != 1 or g != N: return g      # (7)
    return N             


##################################################
## ElGamal Elliptic Curve Cryptosystem
##################################################

def elgamal_init(p):
    """
    Constructs an ElGamal cryptosystem over Z/pZ, by
    choosing a random elliptic curve E over Z/pZ, a 
    point B in E(Z/pZ), and a random integer n.  This
    function returns the public key as a 4-tuple 
    (E, B, n*B) and the private key n.
    Input:
        p -- a prime number
    Output:
        tuple -- the public key as a 3-tuple
                 (E, B, n*B), where E = (a, b, p) is an 
                 elliptic curve over Z/pZ, B = (x, y) is
                 a point on E, and n*B = (x',y') is
                 the sum of B with itself n times.
        int -- the private key, which is the pair (E, n)
    Examples:
    >>> p = random_prime(20); p
    17758176404715800329L    #rand
    >>> public, private = elgamal_init(p)
    >>> print "E =", public[0]
    E = (15299007531923218813L, 1, 17758176404715800329L)   #rand
    >>> print "B =", public[1]
    B = (0, 1)
    >>> print "nB =", public[2]
    nB = (5619048157825840473L, 151469105238517573L)   #rand
    >>> print "n =", private[1]
    n = 12608319787599446459    #rand
    """
    E, B = randcurve(p)
    n = randrange(2,p)    
    nB = ellcurve_mul(E, n, B)
    return (E, B, nB), (E, n)

def elgamal_encrypt(plain_text, public_key):
    """
    Encrypt a message using the ElGamal cryptosystem
    with given public_key = (E, B, n*B).
    Input:
       plain_text -- a string
       public_key -- a triple (E, B, n*B), as output
                     by elgamal_init.
    Output:
       list -- a list of pairs of points on E that 
               represent the encrypted message
    Examples:
    >>> public, private = elgamal_init(random_prime(20))
    >>> elgamal_encrypt("RUN", public)
    [((6004308617723068486L, 15578511190582849677L), \ #rand
     (7064405129585539806L, 8318592816457841619L))]    #rand
    """
    E, B, nB = public_key
    a, b, p = E 
    assert p > 10000, "p must be at least 10000."
    v = [1000*x for x in \
           str_to_numlist(plain_text, p/1000)]       # (1)
    cipher = []
    for x in v:
        while not legendre(x**3+a*x+b, p)==1:        # (2)
            x = (x+1)%p  
        y = sqrtmod(x**3+a*x+b, p)                   # (3)
        P = (x,y)    
        r = randrange(1,p)
        encrypted = (ellcurve_mul(E, r, B), \
                ellcurve_add(E, P, ellcurve_mul(E,r,nB)))
        cipher.append(encrypted)
    return cipher   

def elgamal_decrypt(cipher_text, private_key):
    """
    Encrypt a message using the ElGamal cryptosystem
    with given public_key = (E, B, n*B).
    Input:
        cipher_text -- list of pairs of points on E output
                       by elgamal_encrypt.
    Output:
        str -- the unencrypted plain text
    Examples:
    >>> public, private = elgamal_init(random_prime(20))
    >>> v = elgamal_encrypt("TOP SECRET MESSAGE!", public)
    >>> print elgamal_decrypt(v, private)
    TOP SECRET MESSAGE!
    """
    E, n = private_key
    p = E[2]
    plain = []
    for rB, P_plus_rnB in cipher_text:
        nrB = ellcurve_mul(E, n, rB)
        minus_nrB = (nrB[0], -nrB[1])
        P = ellcurve_add(E, minus_nrB, P_plus_rnB)
        plain.append(P[0]/1000)
    return numlist_to_str(plain, p/1000)


##################################################
## Associativity of the Group Law
##################################################

# The variable order is x1, x2, x3, y1, y2, y3, a, b
class Poly:                                     # (1)
    def __init__(self, d):                      # (2)
        self.v = dict(d)                        
    def __cmp__(self, other):                   # (3)
        self.normalize(); other.normalize()     # (4)
        if self.v == other.v: return 0
        return -1

    def __add__(self, other):                   # (5)
        w = Poly(self.v)
        for m in other.monomials():
            w[m] += other[m]
        return w
    def __sub__(self, other):
        w = Poly(self.v)
        for m in other.monomials():
            w[m] -= other[m]
        return w
    def __mul__(self, other):
        if len(self.v) == 0 or len(other.v) == 0: 
            return Poly([])
        m1 = self.monomials(); m2 = other.monomials()
        r = Poly([])
        for m1 in self.monomials():
            for m2 in other.monomials():
                z = [m1[i] + m2[i] for i in range(8)]
                r[z] += self[m1]*other[m2]
        return r
    def __neg__(self):
        v = {}
        for m in self.v.keys():
            v[m] = -self.v[m]
        return Poly(v)
    def __div__(self, other):
        return Frac(self, other)

    def __getitem__(self, m):                   # (6)
        m = tuple(m)
        if not self.v.has_key(m): self.v[m] = 0
        return self.v[m]
    def __setitem__(self, m, c):
        self.v[tuple(m)] = c
    def __delitem__(self, m):
        del self.v[tuple(m)]

    def monomials(self):                        # (7)
        return self.v.keys()
    def normalize(self):                        # (8)
        while True:
            finished = True
            for m in self.monomials():
                if self[m] == 0:
                    del self[m]
                    continue
                for i in range(3):
                    if m[3+i] >= 2:  
                        finished = False
                        nx0 = list(m); nx0[3+i] -= 2; 
                        nx0[7] += 1
                        nx1 = list(m); nx1[3+i] -= 2; 
                        nx1[i] += 1; nx1[6] += 1
                        nx3 = list(m); nx3[3+i] -= 2; 
                        nx3[i] += 3
                        c = self[m]
                        del self[m]
                        self[nx0] += c; 
                        self[nx1] += c; 
                        self[nx3] += c
                # end for
            # end for
            if finished: return
        # end while

one = Poly({(0,0,0,0,0,0,0,0):1})               # (9)

class Frac:                                     # (10)
    def __init__(self, num, denom=one):         
        self.num = num; self.denom = denom
    def __cmp__(self, other):                   # (11)
        if self.num * other.denom == self.denom * other.num:
            return 0
        return -1

    def __add__(self, other):                   # (12)
        return Frac(self.num*other.denom + \
                    self.denom*other.num, 
                    self.denom*other.denom)
    def __sub__(self, other):
        return Frac(self.num*other.denom - \
                    self.denom*other.num,
                    self.denom*other.denom)
    def __mul__(self, other):
        return Frac(self.num*other.num, \
                    self.denom*other.denom)
    def __div__(self, other):
        return Frac(self.num*other.denom, \
                    self.denom*other.num)
    def __neg__(self):
        return Frac(-self.num,self.denom)

def var(i):                                     # (14)
    v = [0,0,0,0,0,0,0,0]; v[i]=1; 
    return Frac(Poly({tuple(v):1}))

def prove_associative():                        # (15)
    x1 = var(0); x2 = var(1); x3 = var(2)
    y1 = var(3); y2 = var(4); y3 = var(5)
    a  = var(6); b  = var(7)
    
    lambda12 = (y1 - y2)/(x1 - x2)              
    x4       = lambda12*lambda12 - x1 - x2
    nu12     = y1 - lambda12*x1   
    y4       = -lambda12*x4 - nu12
    lambda23 = (y2 - y3)/(x2 - x3)
    x5       = lambda23*lambda23 - x2 - x3
    nu23     = y2 - lambda23*x2
    y5       = -lambda23*x5 - nu23
    s1 = (x1 - x5)*(x1 - x5)*((y3 - y4)*(y3 - y4) \
                   - (x3 + x4)*(x3 - x4)*(x3 - x4))
    s2 = (x3 - x4)*(x3 - x4)*((y1 - y5)*(y1 - y5) \
                   - (x1 + x5)*(x1 - x5)*(x1 - x5))
    print "Associative?"
    print s1 == s2                              # (17)















##########################################################
# The following are all the examples not in functions.   #
##########################################################

def examples():
    """
    >>> from ent import *
    >>> 7/5
    1
    >>> -2/3
    -1
    >>> 1.0/3
    0.33333333333333331
    >>> float(2)/3
    0.66666666666666663
    >>> 100**2
    10000
    >>> 10**20
    100000000000000000000L
    >>> range(10)            # range(n) is from 0 to n-1       
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    >>> range(3,10)          # range(a,b) is from a to b-1
    [3, 4, 5, 6, 7, 8, 9]
    >>> [x**2 for x in range(10)]
    [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
    >>> [x**2 for x in range(10) if x%4 == 1]
    [1, 25, 81]
    >>> [1,2,3] + [5,6,7]    # concatenation
    [1, 2, 3, 5, 6, 7]
    >>> len([1,2,3,4,5])     # length of a list
    5
    >>> x = [4,7,10,'gcd']   # mixing types is fine
    >>> x[0]                 # 0-based indexing
    4
    >>> x[3]
    'gcd'
    >>> x[3] = 'lagrange'    # assignment
    >>> x.append("fermat")   # append to end of list
    >>> x
    [4, 7, 10, 'lagrange', 'fermat']
    >>> del x[3]             # delete entry 3 from list
    >>> x
    [4, 7, 10, 'fermat']
    >>> v = primes(10000)
    >>> len(v)    # this is pi(10000)
    1229
    >>> len([x for x in v if x < 1000])   # pi(1000)
    168
    >>> len([x for x in v if x < 5000])   # pi(5000)
    669
    >>> x=(1, 2, 3)       # creation
    >>> x[1]
    2
    >>> (1, 2, 3) + (4, 5, 6)  # concatenation
    (1, 2, 3, 4, 5, 6)
    >>> (a, b) = (1, 2)        # assignment assigns to each member
    >>> print a, b
    1 2
    >>> for (c, d) in [(1,2), (5,6)]:   
    ...     print c, d
    1 2
    5 6
    >>> x = 1, 2          # parentheses optional in creation
    >>> x
    (1, 2)
    >>> c, d = x          # parentheses also optional 
    >>> print c, d
    1 2
    >>> P = [p for p in range(200000) if is_pseudoprime(p)]
    >>> Q = primes(200000)
    >>> R = [x for x in P if not (x in Q)]; print R
    [29341, 46657, 75361, 115921, 162401]
    >>> [n for n in R if is_pseudoprime(n,[2,3,5,7,11,13])]
    [162401]
    >>> factor(162401)
    [(17, 1), (41, 1), (233, 1)]
    >>> p = random_prime(50)
    >>> p
    13537669335668960267902317758600526039222634416221L #rand
    >>> n, npow = dh_init(p)
    >>> n
    8520467863827253595224582066095474547602956490963L  #rand
    >>> npow
    3206478875002439975737792666147199399141965887602L  #rand
    >>> m, mpow = dh_init(p)
    >>> m
    3533715181946048754332697897996834077726943413544L  #rand
    >>> mpow
    3465862701820513569217254081716392362462604355024L  #rand
    >>> dh_secret(p, n, mpow)
    12931853037327712933053975672241775629043437267478L #rand
    >>> dh_secret(p, m, npow)
    12931853037327712933053975672241775629043437267478L #rand
    >>> prove_associative()
    Associative?
    True
    >>> len(primes(10000))
    1229
    >>> 10000/log(10000)
    1085.73620476
    >>> powermod(3,45,100)
    43
    >>> inversemod(37, 112)
    109
    >>> powermod(102, 70, 113)
    98
    >>> powermod(99, 109, 113)
    60
    >>> P = primes(1000)
    >>> Q = [p for p in P if primitive_root(p) == 2]
    >>> print len(Q), len(P)
    67 168
    >>> P = primes(50000)
    >>> Q = [primitive_root(p) for p in P]
    >>> Q.index(37)
    3893
    >>> P[3893]
    36721
    >>> for n in range(97):
    ...     if powermod(5,n,97)==3: print n
    70
    >>> factor(5352381469067)
    [(141307, 1), (37877681L, 1)]
    >>> d=inversemod(4240501142039, (141307-1)*(37877681-1))
    >>> d
    5195621988839L
    >>> convergents([-3,1,1,1,1,3])
    [(-3, 1), (-2, 1), (-5, 2), (-7, 3), \
              (-12, 5), (-43, 18)]
    >>> convergents([0,2,4,1,8,2])
    [(0, 1), (1, 2), (4, 9), (5, 11), \
              (44, 97), (93, 205)]
    >>> import math
    >>> e = math.exp(1)
    >>> v, convs = contfrac_float(e)
    >>> [(a,b) for a, b in convs if \
           abs(e - a*1.0/b) < 1/(math.sqrt(5)*b**2)]
    [(3, 1), (19, 7), (193, 71), (2721, 1001),\
     (49171, 18089), (1084483, 398959),\
     (28245729, 10391023), (325368125, 119696244)]
    >>> factor(12345)
    [(3, 1), (5, 1), (823, 1)]
    >>> factor(729)
    [(3, 6)]
    >>> factor(5809961789)
    [(5809961789L, 1)]
    >>> 5809961789 % 4
    1L
    >>> sum_of_two_squares(5809961789)
    (51542L, 56155L)
    >>> N = [60 + s for s in range(-15,16)]
    >>> def is_powersmooth(B, x):
    ...     for p, e in factor(x):
    ...         if p**e > B: return False
    ...     return True
    >>> Ns = [x for x in N if is_powersmooth(20, x)]
    >>> print len(Ns), len(N), len(Ns)*1.0/len(N)
    14 31 0.451612903226
    >>> P = [x for x in range(10**12, 10**12+1000)\
             if miller_rabin(x)]
    >>> Ps = [x for x in P if \
             is_powersmooth(10000, x-1)]  
    >>> print len(Ps), len(P), len(Ps)*1.0/len(P)
    2 37 0.0540540540541
    
    """


if __name__ ==  '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
