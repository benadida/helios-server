export var heliosBlob = `
/* From class.js  */
(function(){
    var initializing = false, fnTest = /xyz/.test(function(){xyz;}) ? /\b_super\b/ : /.*/;
  
    // The base Class implementation (does nothing)
    globalThis.Class = function(){};
   
    // Create a new Class that inherits from this class
    Class.extend = function extender(prop) {
      var _super = this.prototype;
     
      // Instantiate a base class (but only create the instance,
      // don't run the init constructor)
      initializing = true;
      var prototype = new this();
      initializing = false;
     
      // Copy the properties over onto the new prototype
      for (var name in prop) {
        // Check if we're overwriting an existing function
        prototype[name] = typeof prop[name] == "function" &&
          typeof _super[name] == "function" && fnTest.test(prop[name]) ?
          (function(name, fn){
            return function() {
              var tmp = this._super;
             
              // Add a new ._super() method that is the same method
              // but on the super-class
              this._super = _super[name];
             
              // The method only need to be bound temporarily, so we
              // remove it when we're done executing
              var ret = fn.apply(this, arguments);       
              this._super = tmp;
             
              return ret;
            };
          })(name, prop[name]) :
          prop[name];
      }
     
      // The dummy class constructor
      function Class() {
        // All construction is actually done in the init method
        if ( !initializing && this.init )
          this.init.apply(this, arguments);
      }
     
      // Populate our constructed prototype object
      Class.prototype = prototype;
     
      // Enforce the constructor to be what we expect
      Class.constructor = Class;
  
      // And make this class extendable
      Class.extend = extender;
     
      return Class;
    };
  })();

  /* From elgamal.js  */
  var ElGamal = {};

  ElGamal.Params = Class.extend({
    init: function(p, q, g) {
      this.p = p;
      this.q = q;
      this.g = g;
    },
    
    generate: function() {
      // get the value x
      var x = Random.getRandomInteger(this.q);
      var y = this.g.modPow(x, this.p);
      var pk = new ElGamal.PublicKey(this.p, this.q, this.g, y);
      var sk = new ElGamal.SecretKey(x, pk);
      return sk;
    },
    
    toJSONObject: function() {
      return {g: this.g.toJSONObject(), p: this.p.toJSONObject(), q: this.q.toJSONObject()};
    }
  });
  
  ElGamal.Params.fromJSONObject = function(d) {
    var params = new ElGamal.Params();
    params.p = BigInt.fromJSONObject(d.p);
    params.q = BigInt.fromJSONObject(d.q);
    params.g = BigInt.fromJSONObject(d.g);
    return params;
  };
  
  ElGamal.PublicKey = Class.extend({
    init : function(p,q,g,y) {
      this.p = p;
      this.q = q;
      this.g = g;
      this.y = y;
    },
    
    toJSONObject: function() {
      return {g : this.g.toJSONObject(), p : this.p.toJSONObject(), q : this.q.toJSONObject(), y : this.y.toJSONObject()};
    },
    
    verifyKnowledgeOfSecretKey: function(proof, challenge_generator) {
      // if challenge_generator is present, we have to check that the challenge was properly generated.
      if (challenge_generator != null) {
        if (!proof.challenge.equals(challenge_generator(proof.commitment))) {
          return false;
        }
      }
      
      // verify that g^response = s * y^challenge
      var check = this.g.modPow(proof.response, this.p).equals(this.y.modPow(proof.challenge, this.p).multiply(proof.commitment).mod(this.p));
      
      return check;
    },
    
    // check if the decryption factor is correct for this public key, given the proof
    verifyDecryptionFactor: function(ciphertext, decryption_factor, decryption_proof, challenge_generator) {
      return decryption_proof.verify(this.g, ciphertext.alpha, this.y, decryption_factor, this.p, this.q, challenge_generator);
    },
    
    multiply: function(other) {
      // base condition
      if (other == 0 || other == 1) {
        return this;
      }
      
      // check params
      if (!this.p.equals(other.p))
        throw "mismatched params";
      if (!this.g.equals(other.g))
        throw "mismatched params";
      
      var new_pk = new ElGamal.PublicKey(this.p, this.q, this.g, this.y.multiply(other.y).mod(this.p));
      return new_pk;
    },
    
    equals: function(other) {
      return (this.p.equals(other.p) && this.q.equals(other.q) && this.g.equals(other.g) && this.y.equals(other.y));
    }
    
  });
  
  ElGamal.PublicKey.fromJSONObject = function(d) {
    var pk = new ElGamal.PublicKey();
    pk.p = BigInt.fromJSONObject(d.p);
    pk.q = BigInt.fromJSONObject(d.q);
    pk.g = BigInt.fromJSONObject(d.g);
    pk.y = BigInt.fromJSONObject(d.y);
    return pk;
  };
  
  ElGamal.SecretKey = Class.extend({
    init: function(x, pk) {
      this.x = x;
      this.pk = pk;
    },
    
    toJSONObject: function() {
      return {public_key: this.pk.toJSONObject(), x: this.x.toJSONObject()};
    },
    
    // a decryption factor is *not yet* mod-inverted, because it needs to be part of the proof.
    decryptionFactor: function(ciphertext) {
      var decryption_factor = ciphertext.alpha.modPow(this.x, this.pk.p);
      return decryption_factor;
    },
    
    decrypt: function(ciphertext, decryption_factor) {
      if (!decryption_factor)
        decryption_factor = this.decryptionFactor(ciphertext);
  
      // use the ciphertext's built-in decryption given a list of decryption factors.
      return ciphertext.decrypt([decryption_factor]);
    },
    
    decryptAndProve: function(ciphertext, challenge_generator) {
      var dec_factor_and_proof = this.decryptionFactorAndProof(ciphertext, challenge_generator);
      
      // decrypt, but using the already computed decryption factor
      var plaintext = this.decrypt(ciphertext, dec_factor_and_proof.decryption_factor);
  
      return {
        'plaintext': plaintext,
        'proof': dec_factor_and_proof.decryption_proof
      };
    },
    
    decryptionFactorAndProof: function(ciphertext, challenge_generator) {
      var decryption_factor = this.decryptionFactor(ciphertext);
      
      // the DH tuple we need to prove, given the secret key x, is:
      // g, alpha, y, beta/m
      var proof = ElGamal.Proof.generate(this.pk.g, ciphertext.alpha, this.x, this.pk.p, this.pk.q, challenge_generator);
      
      return {
        'decryption_factor' : decryption_factor,
        'decryption_proof' : proof
      }
    },
    
    // generate a proof of knowledge of the secret exponent x
    proveKnowledge: function(challenge_generator) {
      // generate random w
      var w = Random.getRandomInteger(this.pk.q);
  
      // compute s = g^w for random w.
      var s = this.pk.g.modPow(w, this.pk.p);
      
      // get challenge
      var challenge = challenge_generator(s);
      
      // compute response = w +  x * challenge
      var response = w.add(this.x.multiply(challenge)).mod(this.pk.q);
      
      return new ElGamal.DLogProof(s, challenge, response);
    }
  });
  
  ElGamal.SecretKey.fromJSONObject = function(d) {
    var sk = new ElGamal.SecretKey();
    sk.pk = ElGamal.PublicKey.fromJSONObject(d.public_key);
    sk.x = BigInt.fromJSONObject(d.x);
    return sk;
  }
  
  ElGamal.Ciphertext = Class.extend({
    init: function(alpha, beta, pk) {
      this.alpha = alpha;
      this.beta = beta;
      this.pk = pk;
    },
    
    toString: function() {
      return this.alpha.toString() + ',' + this.beta.toString();
    },
    
    toJSONObject: function() {
      return {alpha: this.alpha.toJSONObject(), beta: this.beta.toJSONObject()}
    },
    
    multiply: function(other) {
      // special case if other is 1 to enable easy aggregate ops
      if (other == 1)
        return this;
      
      // homomorphic multiply
      return new ElGamal.Ciphertext(this.alpha.multiply(other.alpha).mod(this.pk.p),
                                    this.beta.multiply(other.beta).mod(this.pk.p),
                                    this.pk);
    },
    
    // a decryption method by decryption factors
    decrypt: function(list_of_dec_factors) {
      var running_decryption = this.beta;
      var self = this;
      // Converted
      (list_of_dec_factors).forEach(function(dec_factor) {
        running_decryption = dec_factor.modInverse(self.pk.p).multiply(running_decryption).mod(self.pk.p);    
      });
      
      return new ElGamal.Plaintext(running_decryption, this.pk, false);    
    },
    
    generateProof: function(plaintext, randomness, challenge_generator) {
      // DH tuple to prove is 
      // g, y, alpha, beta/m
      // with dlog randomness
      var proof = ElGamal.Proof.generate(this.pk.g, this.pk.y, randomness, this.pk.p, this.pk.q, challenge_generator);
      
      return proof;
    },
    
    simulateProof: function(plaintext, challenge) {
      // compute beta/plaintext, the completion of the DH tuple
      var beta_over_plaintext = this.beta.multiply(plaintext.m.modInverse(this.pk.p)).mod(this.pk.p);
      
      // the DH tuple we are simulating here is
      // g, y, alpha, beta/m
      return ElGamal.Proof.simulate(this.pk.g, this.pk.y, this.alpha, beta_over_plaintext, this.pk.p, this.pk.q, challenge);
    },
    
    verifyProof: function(plaintext, proof, challenge_generator) {
      // DH tuple to verify is 
      // g, y, alpha, beta/m
      var beta_over_m = this.beta.multiply(plaintext.m.modInverse(this.pk.p)).mod(this.pk.p);
      
      return proof.verify(this.pk.g, this.pk.y, this.alpha, beta_over_m, this.pk.p, this.pk.q, challenge_generator);
    },
  
    verifyDecryptionProof: function(plaintext, proof, challenge_generator) {
      // DH tuple to verify is 
      // g, alpha, y, beta/m
      // since the proven dlog is the secret key x, y=g^x.
      var beta_over_m = this.beta.multiply(plaintext.m.modInverse(this.pk.p)).mod(this.pk.p);
  
      return proof.verify(this.pk.g, this.alpha, this.pk.y, beta_over_m, this.pk.p, this.pk.q, challenge_generator);
    },
    
    generateDisjunctiveProof: function(list_of_plaintexts, real_index, randomness, challenge_generator) {
      // go through all plaintexts and simulate the ones that must be simulated.
      // note how the interface is as such so that the result does not reveal which is the real proof.
      var self = this;
      
      var proofs = (list_of_plaintexts).map(function(plaintext, p_num) {
        if (p_num == real_index) {
          // no real proof yet
          return {};
        } else {
          // simulate!
          return self.simulateProof(plaintext);
        }
      });
      
      // do the real proof
      var real_proof = this.generateProof(list_of_plaintexts[real_index], randomness, function(commitment) {
        // now we generate the challenge for the real proof by first determining
        // the challenge for the whole disjunctive proof.
        
        // set up the partial real proof so we're ready to get the hash;
        proofs[real_index] = {'commitment' : commitment};
  
        // get the commitments in a list and generate the whole disjunctive challenge
        var commitments = (proofs).map(function(proof) {
          return proof.commitment;
        });
        
        var disjunctive_challenge = challenge_generator(commitments);
        
        // now we must subtract all of the other challenges from this challenge.
        var real_challenge = disjunctive_challenge;
        (proofs).forEach(function(proof, proof_num) {
          if (proof_num != real_index)
            real_challenge = real_challenge.add(proof.challenge.negate());
        });
        
        // make sure we mod q, the exponent modulus
        return real_challenge.mod(self.pk.q);
      });
      
      // set the real proof
      proofs[real_index] = real_proof;
      return new ElGamal.DisjunctiveProof(proofs);
    },
    
    verifyDisjunctiveProof: function(list_of_plaintexts, disj_proof, challenge_generator) {
      var result = true;
      var proofs = disj_proof.proofs;
      
      // for loop because we want to bail out of the inner loop
      // if we fail one of the verifications.
      for (var i=0; i < list_of_plaintexts.length; i++) {
        if (!this.verifyProof(list_of_plaintexts[i], proofs[i]))
          return false;
      }
      
      // check the overall challenge
      
      // first the one expected from the proofs
      var commitments = (proofs).map(function(proof) {return proof.commitment;});
      var expected_challenge = challenge_generator(commitments);
      
      // then the one that is the sum of the previous one.
      var sum = new BigInt("0", 10); var self = this;
      (proofs).forEach(function(proof) {sum = sum.add(proof.challenge).mod(self.pk.q);});
      
      return expected_challenge.equals(sum);    
    },
    
    equals: function(other) {
      return (this.alpha.equals(other.alpha) && this.beta.equals(other.beta));
    }
  });
  
  ElGamal.Ciphertext.fromJSONObject = function(d, pk) {
    return new ElGamal.Ciphertext(BigInt.fromJSONObject(d.alpha), BigInt.fromJSONObject(d.beta), pk);
  };
  
  // we need the public key to figure out how to encode m
  ElGamal.Plaintext = Class.extend({
    init: function(m, pk, encode_m) {
      if (m == null) {
        alert('oy null m');
          return;
      }
  
      this.pk = pk;
  
      if (encode_m) {
        // need to encode the message given that p = 2q+1
        var y = m.add(BigInt.ONE);
        var test = y.modPow(pk.q, pk.p);
        if (test.equals(BigInt.ONE)) {
            this.m = y;
        } else {
            this.m = y.negate().mod(pk.p);
        }
      } else {
        this.m = m;
      }    
    },
    
    getPlaintext: function() {
      var y;
  
      // if m < q
      if (this.m.compareTo(this.pk.q) < 0) {
          y = this.m;
      } else {
          y = this.m.negate().mod(this.pk.p);
      }
  
      return y.subtract(BigInt.ONE);
    },
    
    getM: function() {
      return this.m;
    }
    
  });
  
  //
  // Proof abstraction
  //
  
  ElGamal.Proof = Class.extend({
    init: function(A, B, challenge, response) {
      this.commitment = {};
      this.commitment.A = A;
      this.commitment.B = B;
      this.challenge = challenge;
      this.response = response;
    },
    
    toJSONObject: function() {
      return {
        challenge : this.challenge.toJSONObject(),
        commitment : {A: this.commitment.A.toJSONObject(), B: this.commitment.B.toJSONObject()},
        response : this.response.toJSONObject()
      }
    },
    
    // verify a DH tuple proof
    verify: function(little_g, little_h, big_g, big_h, p, q, challenge_generator) {
      // check that little_g^response = A * big_g^challenge
      var first_check = little_g.modPow(this.response, p).equals(big_g.modPow(this.challenge, p).multiply(this.commitment.A).mod(p));
  
      // check that little_h^response = B * big_h^challenge
      var second_check = little_h.modPow(this.response, p).equals(big_h.modPow(this.challenge, p).multiply(this.commitment.B).mod(p));
      
      var third_check = true;
      
      if (challenge_generator) {
        third_check = this.challenge.equals(challenge_generator(this.commitment));
      }
      
      return (first_check && second_check && third_check);
    }
  });
  
  ElGamal.Proof.fromJSONObject = function(d) {
    return new ElGamal.Proof(
      BigInt.fromJSONObject(d.commitment.A),
      BigInt.fromJSONObject(d.commitment.B),
      BigInt.fromJSONObject(d.challenge),
      BigInt.fromJSONObject(d.response));
  };
  
  // a generic way to prove that four values are a DH tuple.
  // a DH tuple is g,h,G,H where G = g^x and H=h^x
  // challenge generator takes a commitment, whose subvalues are A and B
  // all modulo p, with group order q, which we provide just in case.
  // as it turns out, G and H are not necessary to generate this proof, given that they're implied by x.
  ElGamal.Proof.generate = function(little_g, little_h, x, p, q, challenge_generator) {
    // generate random w
    var w = Random.getRandomInteger(q);
    
    // create a proof instance
    var proof = new ElGamal.Proof();
    
    // compute A=little_g^w, B=little_h^w
    proof.commitment.A = little_g.modPow(w, p);
    proof.commitment.B = little_h.modPow(w, p);
    
    // Get the challenge from the callback that generates it
    proof.challenge = challenge_generator(proof.commitment);
    
    // Compute response = w + x * challenge
    proof.response = w.add(x.multiply(proof.challenge)).mod(q);
    
    return proof;
  };
  
  // simulate a a DH-tuple proof, with a potentially assigned challenge (but can be null)
  ElGamal.Proof.simulate = function(little_g, little_h, big_g, big_h, p, q, challenge) {
    // generate a random challenge if not provided
    if (challenge == null) {
      challenge = Random.getRandomInteger(q);
    }
    
    // random response, does not even need to depend on the challenge
    var response = Random.getRandomInteger(q);
  
    // now we compute A and B
    // A = little_g ^ w, and at verification time, g^response = G^challenge * A, so A = (G^challenge)^-1 * g^response
    var A = big_g.modPow(challenge, p).modInverse(p).multiply(little_g.modPow(response, p)).mod(p);
  
    // B = little_h ^ w, and at verification time, h^response = H^challenge * B, so B = (H^challenge)^-1 * h^response
    var B = big_h.modPow(challenge, p).modInverse(p).multiply(little_h.modPow(response, p)).mod(p);
  
    return new ElGamal.Proof(A, B, challenge, response);  
  };
  
  ElGamal.DisjunctiveProof = Class.extend({
    init: function(list_of_proofs) {
      this.proofs = list_of_proofs;
    },
    
    toJSONObject: function() {
      return (this.proofs).map(function(proof) {
        return proof.toJSONObject();
      });
    }
  });
  
  ElGamal.DisjunctiveProof.fromJSONObject = function(d) {
    if (d==null)
      return null;
      
    return new ElGamal.DisjunctiveProof(
      (d).map(function(p) {
        return ElGamal.Proof.fromJSONObject(p);
      })
    );
  };
  
  ElGamal.encrypt = function(pk, plaintext, r) {
    if (plaintext.getM().equals(BigInt.ZERO))
      throw "Can't encrypt 0 with El Gamal"
  
    if (!r)
      r = Random.getRandomInteger(pk.q);
    
    var alpha = pk.g.modPow(r, pk.p);
    var beta = (pk.y.modPow(r, pk.p)).multiply(plaintext.m).mod(pk.p);
    
    return new ElGamal.Ciphertext(alpha, beta, pk);
  };
  
  //
  // DLog Proof
  //
  ElGamal.DLogProof = Class.extend({
    init: function(commitment, challenge, response) {
      this.commitment = commitment;
      this.challenge = challenge;
      this.response = response;
    },
    
    toJSONObject: function() {
      return {'challenge' : this.challenge.toJSONObject(), 'commitment': this.commitment.toJSONObject(), 'response': this.response.toJSONObject()};
    }
  });
  
  ElGamal.DLogProof.fromJSONObject = function(d) {
    return new ElGamal.DLogProof(BigInt.fromJSONObject(d.commitment || d.s), BigInt.fromJSONObject(d.challenge), BigInt.fromJSONObject(d.response));
  };
  
  // a challenge generator based on a list of commitments of
  // proofs of knowledge of plaintext. Just appends A and B with commas.
  ElGamal.disjunctive_challenge_generator = function(commitments) {
    var strings_to_hash = [];
  
    // go through all proofs and append the commitments
    (commitments).forEach(function(commitment) {
      // toJSONObject instead of toString because of IE weirdness.
      strings_to_hash[strings_to_hash.length] = commitment.A.toJSONObject();
      strings_to_hash[strings_to_hash.length] = commitment.B.toJSONObject();
    });
    
    // console.log(strings_to_hash);
    // STRINGS = strings_to_hash;
    return new BigInt(hex_sha1(strings_to_hash.join(",")), 16);
  };
  
  // a challenge generator for Fiat-Shamir
  ElGamal.fiatshamir_challenge_generator = function(commitment) {
    return ElGamal.disjunctive_challenge_generator([commitment]);
  };
  
  ElGamal.fiatshamir_dlog_challenge_generator = function(commitment) {
    return new BigInt(hex_sha1(commitment.toJSONObject()), 16);
  };

  /* From jsbn.js  */
  
  var dbits;

// JavaScript engine analysis
var canary = 0xdeadbeefcafe;
var j_lm = ((canary&0xffffff)==0xefcafe);

// (public) Constructor
function BigInteger(a,b,c) {
  this.arr = new Array();
  if(a != null)
    if("number" == typeof a) this.fromNumber(a,b,c);
    else if(b == null && "string" != typeof a) this.fromString(a,256);
    else this.fromString(a,b);
}

// return new, unset BigInteger
function nbi() { return new BigInteger(null); }

// am: Compute w_j += (x*this_i), propagate carries,
// c is initial carry, returns final carry.
// c < 3*dvalue, x < 2*dvalue, this_i < dvalue
// We need to select the fastest one that works in this environment.

// am1: use a single mult and divide to get the high bits,
// max digit bits should be 26 because
// max internal value = 2*dvalue^2-2*dvalue (< 2^53)
function am1(i,x,w,j,c,n) {
  while(--n >= 0) {
    var v = x*this.arr[i++]+w.arr[j]+c;
    c = Math.floor(v/0x4000000);
    w.arr[j++] = v&0x3ffffff;
  }
  return c;
}
// am2 avoids a big mult-and-extract completely.
// Max digit bits should be <= 30 because we do bitwise ops
// on values up to 2*hdvalue^2-hdvalue-1 (< 2^31)
function am2(i,x,w,j,c,n) {
  var xl = x&0x7fff, xh = x>>15;
  while(--n >= 0) {
    var l = this.arr[i]&0x7fff;
    var h = this.arr[i++]>>15;
    var m = xh*l+h*xl;
    l = xl*l+((m&0x7fff)<<15)+w.arr[j]+(c&0x3fffffff);
    c = (l>>>30)+(m>>>15)+xh*h+(c>>>30);
    w.arr[j++] = l&0x3fffffff;
  }
  return c;
}
// Alternately, set max digit bits to 28 since some
// browsers slow down when dealing with 32-bit numbers.
function am3(i,x,w,j,c,n) {
  var xl = x&0x3fff, xh = x>>14;
  while(--n >= 0) {
    var l = this.arr[i]&0x3fff;
    var h = this.arr[i++]>>14;
    var m = xh*l+h*xl;
    l = xl*l+((m&0x3fff)<<14)+w.arr[j]+c;
    c = (l>>28)+(m>>14)+xh*h;
    w.arr[j++] = l&0xfffffff;
  }
  return c;
}
if(j_lm && (navigator.appName == "Microsoft Internet Explorer")) {
  BigInteger.prototype.am = am2;
  dbits = 30;
}
else if(j_lm && (navigator.appName != "Netscape")) {
  BigInteger.prototype.am = am1;
  dbits = 26;
}
else { // Mozilla/Netscape seems to prefer am3
  BigInteger.prototype.am = am3;
  dbits = 28;
}

BigInteger.prototype.DB = dbits;
BigInteger.prototype.DM = ((1<<dbits)-1);
BigInteger.prototype.DV = (1<<dbits);

var BI_FP = 52;
BigInteger.prototype.FV = Math.pow(2,BI_FP);
BigInteger.prototype.F1 = BI_FP-dbits;
BigInteger.prototype.F2 = 2*dbits-BI_FP;

// Digit conversions
var BI_RM = "0123456789abcdefghijklmnopqrstuvwxyz";
var BI_RC = new Array();
var rr,vv;
rr = "0".charCodeAt(0);
for(vv = 0; vv <= 9; ++vv) BI_RC[rr++] = vv;
rr = "a".charCodeAt(0);
for(vv = 10; vv < 36; ++vv) BI_RC[rr++] = vv;
rr = "A".charCodeAt(0);
for(vv = 10; vv < 36; ++vv) BI_RC[rr++] = vv;

function int2char(n) { return BI_RM.charAt(n); }
function intAt(s,i) {
  var c = BI_RC[s.charCodeAt(i)];
  return (c==null)?-1:c;
}

// (protected) copy this to r
function bnpCopyTo(r) {
  for(var i = this.t-1; i >= 0; --i) r.arr[i] = this.arr[i];
  r.t = this.t;
  r.s = this.s;
}

// (protected) set from integer value x, -DV <= x < DV
function bnpFromInt(x) {
  this.t = 1;
  this.s = (x<0)?-1:0;
  if(x > 0) this.arr[0] = x;
  else if(x < -1) this.arr[0] = x+DV;
  else this.t = 0;
}

// return bigint initialized to value
function nbv(i) { var r = nbi(); r.fromInt(i); return r; }

// (protected) set from string and radix
function bnpFromString(s,b) {
  var k;
  if(b == 16) k = 4;
  else if(b == 8) k = 3;
  else if(b == 256) k = 8; // byte array
  else if(b == 2) k = 1;
  else if(b == 32) k = 5;
  else if(b == 4) k = 2;
  else { this.fromRadix(s,b); return; }
  this.t = 0;
  this.s = 0;
  var i = s.length, mi = false, sh = 0;
  while(--i >= 0) {
    var x = (k==8)?s[i]&0xff:intAt(s,i);
    if(x < 0) {
      if(s.charAt(i) == "-") mi = true;
      continue;
    }
    mi = false;
    if(sh == 0)
      this.arr[this.t++] = x;
    else if(sh+k > this.DB) {
      this.arr[this.t-1] |= (x&((1<<(this.DB-sh))-1))<<sh;
      this.arr[this.t++] = (x>>(this.DB-sh));
    }
    else
      this.arr[this.t-1] |= x<<sh;
    sh += k;
    if(sh >= this.DB) sh -= this.DB;
  }
  if(k == 8 && (s[0]&0x80) != 0) {
    this.s = -1;
    if(sh > 0) this.arr[this.t-1] |= ((1<<(this.DB-sh))-1)<<sh;
  }
  this.clamp();
  if(mi) BigInteger.ZERO.subTo(this,this);
}

// (protected) clamp off excess high words
function bnpClamp() {
  var c = this.s&this.DM;
  while(this.t > 0 && this.arr[this.t-1] == c) --this.t;
}

// (public) return string representation in given radix
function bnToString(b) {
  if(this.s < 0) return "-"+this.negate().toString(b);
  var k;
  if(b == 16) k = 4;
  else if(b == 8) k = 3;
  else if(b == 2) k = 1;
  else if(b == 32) k = 5;
  else if(b == 4) k = 2;
  else return this.toRadix(b);
  var km = (1<<k)-1, d, m = false, r = "", i = this.t;
  var p = this.DB-(i*this.DB)%k;
  if(i-- > 0) {
    if(p < this.DB && (d = this.arr[i]>>p) > 0) { m = true; r = int2char(d); }
    while(i >= 0) {
      if(p < k) {
        d = (this.arr[i]&((1<<p)-1))<<(k-p);
        d |= this.arr[--i]>>(p+=this.DB-k);
      }
      else {
        d = (this.arr[i]>>(p-=k))&km;
        if(p <= 0) { p += this.DB; --i; }
      }
      if(d > 0) m = true;
      if(m) r += int2char(d);
    }
  }
  return m?r:"0";
}

// (public) -this
function bnNegate() { var r = nbi(); BigInteger.ZERO.subTo(this,r); return r; }

// (public) |this|
function bnAbs() { return (this.s<0)?this.negate():this; }

// (public) return + if this > a, - if this < a, 0 if equal
function bnCompareTo(a) {
  var r = this.s-a.s;
  if(r != 0) return r;
  var i = this.t;
  r = i-a.t;
  if(r != 0) return r;
  while(--i >= 0) if((r=this.arr[i]-a.arr[i]) != 0) return r;
  return 0;
}

// returns bit length of the integer x
function nbits(x) {
  var r = 1, t;
  if((t=x>>>16) != 0) { x = t; r += 16; }
  if((t=x>>8) != 0) { x = t; r += 8; }
  if((t=x>>4) != 0) { x = t; r += 4; }
  if((t=x>>2) != 0) { x = t; r += 2; }
  if((t=x>>1) != 0) { x = t; r += 1; }
  return r;
}

// (public) return the number of bits in "this"
function bnBitLength() {
  if(this.t <= 0) return 0;
  return this.DB*(this.t-1)+nbits(this.arr[this.t-1]^(this.s&this.DM));
}

// (protected) r = this << n*DB
function bnpDLShiftTo(n,r) {
  var i;
  for(i = this.t-1; i >= 0; --i) r.arr[i+n] = this.arr[i];
  for(i = n-1; i >= 0; --i) r.arr[i] = 0;
  r.t = this.t+n;
  r.s = this.s;
}

// (protected) r = this >> n*DB
function bnpDRShiftTo(n,r) {
  for(var i = n; i < this.t; ++i) r.arr[i-n] = this.arr[i];
  r.t = Math.max(this.t-n,0);
  r.s = this.s;
}

// (protected) r = this << n
function bnpLShiftTo(n,r) {
  var bs = n%this.DB;
  var cbs = this.DB-bs;
  var bm = (1<<cbs)-1;
  var ds = Math.floor(n/this.DB), c = (this.s<<bs)&this.DM, i;
  for(i = this.t-1; i >= 0; --i) {
    r.arr[i+ds+1] = (this.arr[i]>>cbs)|c;
    c = (this.arr[i]&bm)<<bs;
  }
  for(i = ds-1; i >= 0; --i) r.arr[i] = 0;
  r.arr[ds] = c;
  r.t = this.t+ds+1;
  r.s = this.s;
  r.clamp();
}

// (protected) r = this >> n
function bnpRShiftTo(n,r) {
  r.s = this.s;
  var ds = Math.floor(n/this.DB);
  if(ds >= this.t) { r.t = 0; return; }
  var bs = n%this.DB;
  var cbs = this.DB-bs;
  var bm = (1<<bs)-1;
  r.arr[0] = this.arr[ds]>>bs;
  for(var i = ds+1; i < this.t; ++i) {
    r.arr[i-ds-1] |= (this.arr[i]&bm)<<cbs;
    r.arr[i-ds] = this.arr[i]>>bs;
  }
  if(bs > 0) r.arr[this.t-ds-1] |= (this.s&bm)<<cbs;
  r.t = this.t-ds;
  r.clamp();
}

// (protected) r = this - a
function bnpSubTo(a,r) {
  var i = 0, c = 0, m = Math.min(a.t,this.t);
  while(i < m) {
    c += this.arr[i]-a.arr[i];
    r.arr[i++] = c&this.DM;
    c >>= this.DB;
  }
  if(a.t < this.t) {
    c -= a.s;
    while(i < this.t) {
      c += this.arr[i];
      r.arr[i++] = c&this.DM;
      c >>= this.DB;
    }
    c += this.s;
  }
  else {
    c += this.s;
    while(i < a.t) {
      c -= a.arr[i];
      r.arr[i++] = c&this.DM;
      c >>= this.DB;
    }
    c -= a.s;
  }
  r.s = (c<0)?-1:0;
  if(c < -1) r.arr[i++] = this.DV+c;
  else if(c > 0) r.arr[i++] = c;
  r.t = i;
  r.clamp();
}

// (protected) r = this * a, r != this,a (HAC 14.12)
// "this" should be the larger one if appropriate.
function bnpMultiplyTo(a,r) {
  var x = this.abs(), y = a.abs();
  var i = x.t;
  r.t = i+y.t;
  while(--i >= 0) r.arr[i] = 0;
  for(i = 0; i < y.t; ++i) r.arr[i+x.t] = x.am(0,y.arr[i],r,i,0,x.t);
  r.s = 0;
  r.clamp();
  if(this.s != a.s) BigInteger.ZERO.subTo(r,r);
}

// (protected) r = this^2, r != this (HAC 14.16)
function bnpSquareTo(r) {
  var x = this.abs();
  var i = r.t = 2*x.t;
  while(--i >= 0) r.arr[i] = 0;
  for(i = 0; i < x.t-1; ++i) {
    var c = x.am(i,x.arr[i],r,2*i,0,1);
    if((r.arr[i+x.t]+=x.am(i+1,2*x.arr[i],r,2*i+1,c,x.t-i-1)) >= x.DV) {
      r.arr[i+x.t] -= x.DV;
      r.arr[i+x.t+1] = 1;
    }
  }
  if(r.t > 0) r.arr[r.t-1] += x.am(i,x.arr[i],r,2*i,0,1);
  r.s = 0;
  r.clamp();
}

// (protected) divide this by m, quotient and remainder to q, r (HAC 14.20)
// r != q, this != m.  q or r may be null.
function bnpDivRemTo(m,q,r) {
  var pm = m.abs();
  if(pm.t <= 0) return;
  var pt = this.abs();
  if(pt.t < pm.t) {
    if(q != null) q.fromInt(0);
    if(r != null) this.copyTo(r);
    return;
  }
  if(r == null) r = nbi();
  var y = nbi(), ts = this.s, ms = m.s;
  var nsh = this.DB-nbits(pm.arr[pm.t-1]);	// normalize modulus
  if(nsh > 0) { pm.lShiftTo(nsh,y); pt.lShiftTo(nsh,r); }
  else { pm.copyTo(y); pt.copyTo(r); }
  var ys = y.t;
  var y0 = y.arr[ys-1];
  if(y0 == 0) return;
  var yt = y0*(1<<this.F1)+((ys>1)?y.arr[ys-2]>>this.F2:0);
  var d1 = this.FV/yt, d2 = (1<<this.F1)/yt, e = 1<<this.F2;
  var i = r.t, j = i-ys, t = (q==null)?nbi():q;
  y.dlShiftTo(j,t);
  if(r.compareTo(t) >= 0) {
    r.arr[r.t++] = 1;
    r.subTo(t,r);
  }
  BigInteger.ONE.dlShiftTo(ys,t);
  t.subTo(y,y);	// "negative" y so we can replace sub with am later
  while(y.t < ys) y.arr[y.t++] = 0;
  while(--j >= 0) {
    // Estimate quotient digit
    var qd = (r.arr[--i]==y0)?this.DM:Math.floor(r.arr[i]*d1+(r.arr[i-1]+e)*d2);
    if((r.arr[i]+=y.am(0,qd,r,j,0,ys)) < qd) {	// Try it out
      y.dlShiftTo(j,t);
      r.subTo(t,r);
      while(r.arr[i] < --qd) r.subTo(t,r);
    }
  }
  if(q != null) {
    r.drShiftTo(ys,q);
    if(ts != ms) BigInteger.ZERO.subTo(q,q);
  }
  r.t = ys;
  r.clamp();
  if(nsh > 0) r.rShiftTo(nsh,r);	// Denormalize remainder
  if(ts < 0) BigInteger.ZERO.subTo(r,r);
}

// (public) this mod a
function bnMod(a) {
  var r = nbi();
  this.abs().divRemTo(a,null,r);
  if(this.s < 0 && r.compareTo(BigInteger.ZERO) > 0) a.subTo(r,r);
  return r;
}

// Modular reduction using "classic" algorithm
function Classic(m) { this.m = m; }
function cConvert(x) {
  if(x.s < 0 || x.compareTo(this.m) >= 0) return x.mod(this.m);
  else return x;
}
function cRevert(x) { return x; }
function cReduce(x) { x.divRemTo(this.m,null,x); }
function cMulTo(x,y,r) { x.multiplyTo(y,r); this.reduce(r); }
function cSqrTo(x,r) { x.squareTo(r); this.reduce(r); }

Classic.prototype.convert = cConvert;
Classic.prototype.revert = cRevert;
Classic.prototype.reduce = cReduce;
Classic.prototype.mulTo = cMulTo;
Classic.prototype.sqrTo = cSqrTo;

// (protected) return "-1/this % 2^DB"; useful for Mont. reduction
// justification:
//         xy == 1 (mod m)
//         xy =  1+km
//   xy(2-xy) = (1+km)(1-km)
// x.arr[y(2-xy)] = 1-k^2m^2
// x.arr[y(2-xy)] == 1 (mod m^2)
// if y is 1/x mod m, then y(2-xy) is 1/x mod m^2
// should reduce x and y(2-xy) by m^2 at each step to keep size bounded.
// JS multiply "overflows" differently from C/C++, so care is needed here.
function bnpInvDigit() {
  if(this.t < 1) return 0;
  var x = this.arr[0];
  if((x&1) == 0) return 0;
  var y = x&3;		// y == 1/x mod 2^2
  y = (y*(2-(x&0xf)*y))&0xf;	// y == 1/x mod 2^4
  y = (y*(2-(x&0xff)*y))&0xff;	// y == 1/x mod 2^8
  y = (y*(2-(((x&0xffff)*y)&0xffff)))&0xffff;	// y == 1/x mod 2^16
  // last step - calculate inverse mod DV directly;
  // assumes 16 < DB <= 32 and assumes ability to handle 48-bit ints
  y = (y*(2-x*y%this.DV))%this.DV;		// y == 1/x mod 2^dbits
  // we really want the negative inverse, and -DV < y < DV
  return (y>0)?this.DV-y:-y;
}

// Montgomery reduction
function Montgomery(m) {
  this.m = m;
  this.mp = m.invDigit();
  this.mpl = this.mp&0x7fff;
  this.mph = this.mp>>15;
  this.um = (1<<(m.DB-15))-1;
  this.mt2 = 2*m.t;
}

// xR mod m
function montConvert(x) {
  var r = nbi();
  x.abs().dlShiftTo(this.m.t,r);
  r.divRemTo(this.m,null,r);
  if(x.s < 0 && r.compareTo(BigInteger.ZERO) > 0) this.m.subTo(r,r);
  return r;
}

// x/R mod m
function montRevert(x) {
  var r = nbi();
  x.copyTo(r);
  this.reduce(r);
  return r;
}

// x = x/R mod m (HAC 14.32)
function montReduce(x) {
  while(x.t <= this.mt2)	// pad x so am has enough room later
    x.arr[x.t++] = 0;
  for(var i = 0; i < this.m.t; ++i) {
    // faster way of calculating u0 = x.arr[i]*mp mod DV
    var j = x.arr[i]&0x7fff;
    var u0 = (j*this.mpl+(((j*this.mph+(x.arr[i]>>15)*this.mpl)&this.um)<<15))&x.DM;
    // use am to combine the multiply-shift-add into one call
    j = i+this.m.t;
    x.arr[j] += this.m.am(0,u0,x,i,0,this.m.t);
    // propagate carry
    while(x.arr[j] >= x.DV) { x.arr[j] -= x.DV; x.arr[++j]++; }
  }
  x.clamp();
  x.drShiftTo(this.m.t,x);
  if(x.compareTo(this.m) >= 0) x.subTo(this.m,x);
}

// r = "x^2/R mod m"; x != r
function montSqrTo(x,r) { x.squareTo(r); this.reduce(r); }

// r = "xy/R mod m"; x,y != r
function montMulTo(x,y,r) { x.multiplyTo(y,r); this.reduce(r); }

Montgomery.prototype.convert = montConvert;
Montgomery.prototype.revert = montRevert;
Montgomery.prototype.reduce = montReduce;
Montgomery.prototype.mulTo = montMulTo;
Montgomery.prototype.sqrTo = montSqrTo;

// (protected) true iff this is even
function bnpIsEven() { return ((this.t>0)?(this.arr[0]&1):this.s) == 0; }

// (protected) this^e, e < 2^32, doing sqr and mul with "r" (HAC 14.79)
function bnpExp(e,z) {
  if(e > 0xffffffff || e < 1) return BigInteger.ONE;
  var r = nbi(), r2 = nbi(), g = z.convert(this), i = nbits(e)-1;
  g.copyTo(r);
  while(--i >= 0) {
    z.sqrTo(r,r2);
    if((e&(1<<i)) > 0) z.mulTo(r2,g,r);
    else { var t = r; r = r2; r2 = t; }
  }
  return z.revert(r);
}

// (public) this^e % m, 0 <= e < 2^32
function bnModPowInt(e,m) {
  var z;
  if(e < 256 || m.isEven()) z = new Classic(m); else z = new Montgomery(m);
  return this.exp(e,z);
}

// protected
BigInteger.prototype.copyTo = bnpCopyTo;
BigInteger.prototype.fromInt = bnpFromInt;
BigInteger.prototype.fromString = bnpFromString;
BigInteger.prototype.clamp = bnpClamp;
BigInteger.prototype.dlShiftTo = bnpDLShiftTo;
BigInteger.prototype.drShiftTo = bnpDRShiftTo;
BigInteger.prototype.lShiftTo = bnpLShiftTo;
BigInteger.prototype.rShiftTo = bnpRShiftTo;
BigInteger.prototype.subTo = bnpSubTo;
BigInteger.prototype.multiplyTo = bnpMultiplyTo;
BigInteger.prototype.squareTo = bnpSquareTo;
BigInteger.prototype.divRemTo = bnpDivRemTo;
BigInteger.prototype.invDigit = bnpInvDigit;
BigInteger.prototype.isEven = bnpIsEven;
BigInteger.prototype.exp = bnpExp;

// public
BigInteger.prototype.toString = bnToString;
BigInteger.prototype.negate = bnNegate;
BigInteger.prototype.abs = bnAbs;
BigInteger.prototype.compareTo = bnCompareTo;
BigInteger.prototype.bitLength = bnBitLength;
BigInteger.prototype.mod = bnMod;
BigInteger.prototype.modPowInt = bnModPowInt;

// "constants"
BigInteger.ZERO = nbv(0);
BigInteger.ONE = nbv(1);

// (public)
function bnClone() { var r = nbi(); this.copyTo(r); return r; }

// (public) return value as integer
function bnIntValue() {
  if(this.s < 0) {
    if(this.t == 1) return this.arr[0]-this.DV;
    else if(this.t == 0) return -1;
  }
  else if(this.t == 1) return this.arr[0];
  else if(this.t == 0) return 0;
  // assumes 16 < DB < 32
  return ((this.arr[1]&((1<<(32-this.DB))-1))<<this.DB)|this.arr[0];
}

// (public) return value as byte
function bnByteValue() { return (this.t==0)?this.s:(this.arr[0]<<24)>>24; }

// (public) return value as short (assumes DB>=16)
function bnShortValue() { return (this.t==0)?this.s:(this.arr[0]<<16)>>16; }

// (protected) return x s.t. r^x < DV
function bnpChunkSize(r) { return Math.floor(Math.LN2*this.DB/Math.log(r)); }

// (public) 0 if this == 0, 1 if this > 0
function bnSigNum() {
  if(this.s < 0) return -1;
  else if(this.t <= 0 || (this.t == 1 && this.arr[0] <= 0)) return 0;
  else return 1;
}

// (protected) convert to radix string
function bnpToRadix(b) {
  if(b == null) b = 10;
  if(this.signum() == 0 || b < 2 || b > 36) return "0";
  var cs = this.chunkSize(b);
  var a = Math.pow(b,cs);
  var d = nbv(a), y = nbi(), z = nbi(), r = "";
  this.divRemTo(d,y,z);
  while(y.signum() > 0) {
    r = (a+z.intValue()).toString(b).substr(1) + r;
    y.divRemTo(d,y,z);
  }
  return z.intValue().toString(b) + r;
}

// (protected) convert from radix string
function bnpFromRadix(s,b) {
  this.fromInt(0);
  if(b == null) b = 10;
  var cs = this.chunkSize(b);
  var d = Math.pow(b,cs), mi = false, j = 0, w = 0;
  for(var i = 0; i < s.length; ++i) {
    var x = intAt(s,i);
    if(x < 0) {
      if(s.charAt(i) == "-" && this.signum() == 0) mi = true;
      continue;
    }
    w = b*w+x;
    if(++j >= cs) {
      this.dMultiply(d);
      this.dAddOffset(w,0);
      j = 0;
      w = 0;
    }
  }
  if(j > 0) {
    this.dMultiply(Math.pow(b,j));
    this.dAddOffset(w,0);
  }
  if(mi) BigInteger.ZERO.subTo(this,this);
}

// (protected) alternate constructor
function bnpFromNumber(a,b,c) {
  if("number" == typeof b) {
    // new BigInteger(int,int,RNG)
    if(a < 2) this.fromInt(1);
    else {
      this.fromNumber(a,c);
      if(!this.testBit(a-1))	// force MSB set
        this.bitwiseTo(BigInteger.ONE.shiftLeft(a-1),op_or,this);
      if(this.isEven()) this.dAddOffset(1,0); // force odd
      while(!this.isProbablePrime(b)) {
        this.dAddOffset(2,0);
        if(this.bitLength() > a) this.subTo(BigInteger.ONE.shiftLeft(a-1),this);
      }
    }
  }
  else {
    // new BigInteger(int,RNG)
    var x = new Array(), t = a&7;
    x.length = (a>>3)+1;
    b.nextBytes(x);
    if(t > 0) x.arr[0] &= ((1<<t)-1); else x.arr[0] = 0;
    this.fromString(x,256);
  }
}

// (public) convert to bigendian byte array
function bnToByteArray() {
  var i = this.t, r = new Array();
  r.arr[0] = this.s;
  var p = this.DB-(i*this.DB)%8, d, k = 0;
  if(i-- > 0) {
    if(p < this.DB && (d = this.arr[i]>>p) != (this.s&this.DM)>>p)
      r.arr[k++] = d|(this.s<<(this.DB-p));
    while(i >= 0) {
      if(p < 8) {
        d = (this.arr[i]&((1<<p)-1))<<(8-p);
        d |= this.arr[--i]>>(p+=this.DB-8);
      }
      else {
        d = (this.arr[i]>>(p-=8))&0xff;
        if(p <= 0) { p += this.DB; --i; }
      }
      if((d&0x80) != 0) d |= -256;
      if(k == 0 && (this.s&0x80) != (d&0x80)) ++k;
      if(k > 0 || d != this.s) r.arr[k++] = d;
    }
  }
  return r;
}

function bnEquals(a) { return(this.compareTo(a)==0); }
function bnMin(a) { return(this.compareTo(a)<0)?this:a; }
function bnMax(a) { return(this.compareTo(a)>0)?this:a; }

// (protected) r = this op a (bitwise)
function bnpBitwiseTo(a,op,r) {
  var i, f, m = Math.min(a.t,this.t);
  for(i = 0; i < m; ++i) r.arr[i] = op(this.arr[i],a.arr[i]);
  if(a.t < this.t) {
    f = a.s&this.DM;
    for(i = m; i < this.t; ++i) r.arr[i] = op(this.arr[i],f);
    r.t = this.t;
  }
  else {
    f = this.s&this.DM;
    for(i = m; i < a.t; ++i) r.arr[i] = op(f,a.arr[i]);
    r.t = a.t;
  }
  r.s = op(this.s,a.s);
  r.clamp();
}

// (public) this & a
function op_and(x,y) { return x&y; }
function bnAnd(a) { var r = nbi(); this.bitwiseTo(a,op_and,r); return r; }

// (public) this | a
function op_or(x,y) { return x|y; }
function bnOr(a) { var r = nbi(); this.bitwiseTo(a,op_or,r); return r; }

// (public) this ^ a
function op_xor(x,y) { return x^y; }
function bnXor(a) { var r = nbi(); this.bitwiseTo(a,op_xor,r); return r; }

// (public) this & ~a
function op_andnot(x,y) { return x&~y; }
function bnAndNot(a) { var r = nbi(); this.bitwiseTo(a,op_andnot,r); return r; }

// (public) ~this
function bnNot() {
  var r = nbi();
  for(var i = 0; i < this.t; ++i) r.arr[i] = this.DM&~this.arr[i];
  r.t = this.t;
  r.s = ~this.s;
  return r;
}

// (public) this << n
function bnShiftLeft(n) {
  var r = nbi();
  if(n < 0) this.rShiftTo(-n,r); else this.lShiftTo(n,r);
  return r;
}

// (public) this >> n
function bnShiftRight(n) {
  var r = nbi();
  if(n < 0) this.lShiftTo(-n,r); else this.rShiftTo(n,r);
  return r;
}

// return index of lowest 1-bit in x, x < 2^31
function lbit(x) {
  if(x == 0) return -1;
  var r = 0;
  if((x&0xffff) == 0) { x >>= 16; r += 16; }
  if((x&0xff) == 0) { x >>= 8; r += 8; }
  if((x&0xf) == 0) { x >>= 4; r += 4; }
  if((x&3) == 0) { x >>= 2; r += 2; }
  if((x&1) == 0) ++r;
  return r;
}

// (public) returns index of lowest 1-bit (or -1 if none)
function bnGetLowestSetBit() {
  for(var i = 0; i < this.t; ++i)
    if(this.arr[i] != 0) return i*this.DB+lbit(this.arr[i]);
  if(this.s < 0) return this.t*this.DB;
  return -1;
}

// return number of 1 bits in x
function cbit(x) {
  var r = 0;
  while(x != 0) { x &= x-1; ++r; }
  return r;
}

// (public) return number of set bits
function bnBitCount() {
  var r = 0, x = this.s&this.DM;
  for(var i = 0; i < this.t; ++i) r += cbit(this.arr[i]^x);
  return r;
}

// (public) true iff nth bit is set
function bnTestBit(n) {
  var j = Math.floor(n/this.DB);
  if(j >= this.t) return(this.s!=0);
  return((this.arr[j]&(1<<(n%this.DB)))!=0);
}

// (protected) this op (1<<n)
function bnpChangeBit(n,op) {
  var r = BigInteger.ONE.shiftLeft(n);
  this.bitwiseTo(r,op,r);
  return r;
}

// (public) this | (1<<n)
function bnSetBit(n) { return this.changeBit(n,op_or); }

// (public) this & ~(1<<n)
function bnClearBit(n) { return this.changeBit(n,op_andnot); }

// (public) this ^ (1<<n)
function bnFlipBit(n) { return this.changeBit(n,op_xor); }

// (protected) r = this + a
function bnpAddTo(a,r) {
  var i = 0, c = 0, m = Math.min(a.t,this.t);
  while(i < m) {
    c += this.arr[i]+a.arr[i];
    r.arr[i++] = c&this.DM;
    c >>= this.DB;
  }
  if(a.t < this.t) {
    c += a.s;
    while(i < this.t) {
      c += this.arr[i];
      r.arr[i++] = c&this.DM;
      c >>= this.DB;
    }
    c += this.s;
  }
  else {
    c += this.s;
    while(i < a.t) {
      c += a.arr[i];
      r.arr[i++] = c&this.DM;
      c >>= this.DB;
    }
    c += a.s;
  }
  r.s = (c<0)?-1:0;
  if(c > 0) r.arr[i++] = c;
  else if(c < -1) r.arr[i++] = this.DV+c;
  r.t = i;
  r.clamp();
}

// (public) this + a
function bnAdd(a) { var r = nbi(); this.addTo(a,r); return r; }

// (public) this - a
function bnSubtract(a) { var r = nbi(); this.subTo(a,r); return r; }

// (public) this * a
function bnMultiply(a) { var r = nbi(); this.multiplyTo(a,r); return r; }

// (public) this / a
function bnDivide(a) { var r = nbi(); this.divRemTo(a,r,null); return r; }

// (public) this % a
function bnRemainder(a) { var r = nbi(); this.divRemTo(a,null,r); return r; }

// (public) [this/a,this%a]
function bnDivideAndRemainder(a) {
  var q = nbi(), r = nbi();
  this.divRemTo(a,q,r);
  return new Array(q,r);
}

// (protected) this *= n, this >= 0, 1 < n < DV
function bnpDMultiply(n) {
  this.arr[this.t] = this.am(0,n-1,this,0,0,this.t);
  ++this.t;
  this.clamp();
}

// (protected) this += n << w words, this >= 0
function bnpDAddOffset(n,w) {
  if(n == 0) return;
  while(this.t <= w) this.arr[this.t++] = 0;
  this.arr[w] += n;
  while(this.arr[w] >= this.DV) {
    this.arr[w] -= this.DV;
    if(++w >= this.t) this.arr[this.t++] = 0;
    ++this.arr[w];
  }
}

// A "null" reducer
function NullExp() {}
function nNop(x) { return x; }
function nMulTo(x,y,r) { x.multiplyTo(y,r); }
function nSqrTo(x,r) { x.squareTo(r); }

NullExp.prototype.convert = nNop;
NullExp.prototype.revert = nNop;
NullExp.prototype.mulTo = nMulTo;
NullExp.prototype.sqrTo = nSqrTo;

// (public) this^e
function bnPow(e) { return this.exp(e,new NullExp()); }

// (protected) r = lower n words of "this * a", a.t <= n
// "this" should be the larger one if appropriate.
function bnpMultiplyLowerTo(a,n,r) {
  var i = Math.min(this.t+a.t,n);
  r.s = 0; // assumes a,this >= 0
  r.t = i;
  while(i > 0) r.arr[--i] = 0;
  var j;
  for(j = r.t-this.t; i < j; ++i) r.arr[i+this.t] = this.am(0,a.arr[i],r,i,0,this.t);
  for(j = Math.min(a.t,n); i < j; ++i) this.am(0,a.arr[i],r,i,0,n-i);
  r.clamp();
}

// (protected) r = "this * a" without lower n words, n > 0
// "this" should be the larger one if appropriate.
function bnpMultiplyUpperTo(a,n,r) {
  --n;
  var i = r.t = this.t+a.t-n;
  r.s = 0; // assumes a,this >= 0
  while(--i >= 0) r.arr[i] = 0;
  for(i = Math.max(n-this.t,0); i < a.t; ++i)
    r.arr[this.t+i-n] = this.am(n-i,a.arr[i],r,0,0,this.t+i-n);
  r.clamp();
  r.drShiftTo(1,r);
}

// Barrett modular reduction
function Barrett(m) {
  // setup Barrett
  this.r2 = nbi();
  this.q3 = nbi();
  BigInteger.ONE.dlShiftTo(2*m.t,this.r2);
  this.mu = this.r2.divide(m);
  this.m = m;
}

function barrettConvert(x) {
  if(x.s < 0 || x.t > 2*this.m.t) return x.mod(this.m);
  else if(x.compareTo(this.m) < 0) return x;
  else { var r = nbi(); x.copyTo(r); this.reduce(r); return r; }
}

function barrettRevert(x) { return x; }

// x = x mod m (HAC 14.42)
function barrettReduce(x) {
  x.drShiftTo(this.m.t-1,this.r2);
  if(x.t > this.m.t+1) { x.t = this.m.t+1; x.clamp(); }
  this.mu.multiplyUpperTo(this.r2,this.m.t+1,this.q3);
  this.m.multiplyLowerTo(this.q3,this.m.t+1,this.r2);
  while(x.compareTo(this.r2) < 0) x.dAddOffset(1,this.m.t+1);
  x.subTo(this.r2,x);
  while(x.compareTo(this.m) >= 0) x.subTo(this.m,x);
}

// r = x^2 mod m; x != r
function barrettSqrTo(x,r) { x.squareTo(r); this.reduce(r); }

// r = x*y mod m; x,y != r
function barrettMulTo(x,y,r) { x.multiplyTo(y,r); this.reduce(r); }

Barrett.prototype.convert = barrettConvert;
Barrett.prototype.revert = barrettRevert;
Barrett.prototype.reduce = barrettReduce;
Barrett.prototype.mulTo = barrettMulTo;
Barrett.prototype.sqrTo = barrettSqrTo;

// (public) this^e % m (HAC 14.85)
function bnModPow(e,m) {
  var i = e.bitLength(), k, r = nbv(1), z;
  if(i <= 0) return r;
  else if(i < 18) k = 1;
  else if(i < 48) k = 3;
  else if(i < 144) k = 4;
  else if(i < 768) k = 5;
  else k = 6;
  if(i < 8)
    z = new Classic(m);
  else if(m.isEven())
    z = new Barrett(m);
  else
    z = new Montgomery(m);

  // precomputation
  var g = new Array(), n = 3, k1 = k-1, km = (1<<k)-1;
  g[1] = z.convert(this);
  if(k > 1) {
    var g2 = nbi();
    z.sqrTo(g[1],g2);
    while(n <= km) {
      g[n] = nbi();
      z.mulTo(g2,g[n-2],g[n]);
      n += 2;
    }
  }

  var j = e.t-1, w, is1 = true, r2 = nbi(), t;
  i = nbits(e.arr[j])-1;
  while(j >= 0) {
    if(i >= k1) w = (e.arr[j]>>(i-k1))&km;
    else {
      w = (e.arr[j]&((1<<(i+1))-1))<<(k1-i);
      if(j > 0) w |= e.arr[j-1]>>(this.DB+i-k1);
    }

    n = k;
    while((w&1) == 0) { w >>= 1; --n; }
    if((i -= n) < 0) { i += this.DB; --j; }
    if(is1) {	// ret == 1, don't bother squaring or multiplying it
      g[w].copyTo(r);
      is1 = false;
    }
    else {
      while(n > 1) { z.sqrTo(r,r2); z.sqrTo(r2,r); n -= 2; }
      if(n > 0) z.sqrTo(r,r2); else { t = r; r = r2; r2 = t; }
      z.mulTo(r2,g[w],r);
    }

    while(j >= 0 && (e.arr[j]&(1<<i)) == 0) {
      z.sqrTo(r,r2); t = r; r = r2; r2 = t;
      if(--i < 0) { i = this.DB-1; --j; }
    }
  }
  return z.revert(r);
}

// (public) gcd(this,a) (HAC 14.54)
function bnGCD(a) {
  var x = (this.s<0)?this.negate():this.clone();
  var y = (a.s<0)?a.negate():a.clone();
  if(x.compareTo(y) < 0) { var t = x; x = y; y = t; }
  var i = x.getLowestSetBit(), g = y.getLowestSetBit();
  if(g < 0) return x;
  if(i < g) g = i;
  if(g > 0) {
    x.rShiftTo(g,x);
    y.rShiftTo(g,y);
  }
  while(x.signum() > 0) {
    if((i = x.getLowestSetBit()) > 0) x.rShiftTo(i,x);
    if((i = y.getLowestSetBit()) > 0) y.rShiftTo(i,y);
    if(x.compareTo(y) >= 0) {
      x.subTo(y,x);
      x.rShiftTo(1,x);
    }
    else {
      y.subTo(x,y);
      y.rShiftTo(1,y);
    }
  }
  if(g > 0) y.lShiftTo(g,y);
  return y;
}

// (protected) this % n, n < 2^26
function bnpModInt(n) {
  if(n <= 0) return 0;
  var d = this.DV%n, r = (this.s<0)?n-1:0;
  if(this.t > 0)
    if(d == 0) r = this.arr[0]%n;
    else for(var i = this.t-1; i >= 0; --i) r = (d*r+this.arr[i])%n;
  return r;
}

// (public) 1/this % m (HAC 14.61)
function bnModInverse(m) {
  var ac = m.isEven();
  if((this.isEven() && ac) || m.signum() == 0) return BigInteger.ZERO;
  var u = m.clone(), v = this.clone();
  var a = nbv(1), b = nbv(0), c = nbv(0), d = nbv(1);
  while(u.signum() != 0) {
    while(u.isEven()) {
      u.rShiftTo(1,u);
      if(ac) {
        if(!a.isEven() || !b.isEven()) { a.addTo(this,a); b.subTo(m,b); }
        a.rShiftTo(1,a);
      }
      else if(!b.isEven()) b.subTo(m,b);
      b.rShiftTo(1,b);
    }
    while(v.isEven()) {
      v.rShiftTo(1,v);
      if(ac) {
        if(!c.isEven() || !d.isEven()) { c.addTo(this,c); d.subTo(m,d); }
        c.rShiftTo(1,c);
      }
      else if(!d.isEven()) d.subTo(m,d);
      d.rShiftTo(1,d);
    }
    if(u.compareTo(v) >= 0) {
      u.subTo(v,u);
      if(ac) a.subTo(c,a);
      b.subTo(d,b);
    }
    else {
      v.subTo(u,v);
      if(ac) c.subTo(a,c);
      d.subTo(b,d);
    }
  }
  if(v.compareTo(BigInteger.ONE) != 0) return BigInteger.ZERO;
  if(d.compareTo(m) >= 0) return d.subtract(m);
  if(d.signum() < 0) d.addTo(m,d); else return d;
  if(d.signum() < 0) return d.add(m); else return d;
}

var lowprimes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181,191,193,197,199,211,223,227,229,233,239,241,251,257,263,269,271,277,281,283,293,307,311,313,317,331,337,347,349,353,359,367,373,379,383,389,397,401,409,419,421,431,433,439,443,449,457,461,463,467,479,487,491,499,503,509];
var lplim = (1<<26)/lowprimes[lowprimes.length-1];

// (public) test primality with certainty >= 1-.5^t
function bnIsProbablePrime(t) {
  var i, x = this.abs();
  if(x.t == 1 && x.arr[0] <= lowprimes[lowprimes.length-1]) {
    for(i = 0; i < lowprimes.length; ++i)
      if(x.arr[0] == lowprimes[i]) return true;
    return false;
  }
  if(x.isEven()) return false;
  i = 1;
  while(i < lowprimes.length) {
    var m = lowprimes[i], j = i+1;
    while(j < lowprimes.length && m < lplim) m *= lowprimes[j++];
    m = x.modInt(m);
    while(i < j) if(m%lowprimes[i++] == 0) return false;
  }
  return x.millerRabin(t);
}

// (protected) true if probably prime (HAC 4.24, Miller-Rabin)
function bnpMillerRabin(t) {
  var n1 = this.subtract(BigInteger.ONE);
  var k = n1.getLowestSetBit();
  if(k <= 0) return false;
  var r = n1.shiftRight(k);
  t = (t+1)>>1;
  if(t > lowprimes.length) t = lowprimes.length;
  var a = nbi();
  for(var i = 0; i < t; ++i) {
    a.fromInt(lowprimes[i]);
    var y = a.modPow(r,this);
    if(y.compareTo(BigInteger.ONE) != 0 && y.compareTo(n1) != 0) {
      var j = 1;
      while(j++ < k && y.compareTo(n1) != 0) {
        y = y.modPowInt(2,this);
        if(y.compareTo(BigInteger.ONE) == 0) return false;
      }
      if(y.compareTo(n1) != 0) return false;
    }
  }
  return true;
}

// protected
BigInteger.prototype.chunkSize = bnpChunkSize;
BigInteger.prototype.toRadix = bnpToRadix;
BigInteger.prototype.fromRadix = bnpFromRadix;
BigInteger.prototype.fromNumber = bnpFromNumber;
BigInteger.prototype.bitwiseTo = bnpBitwiseTo;
BigInteger.prototype.changeBit = bnpChangeBit;
BigInteger.prototype.addTo = bnpAddTo;
BigInteger.prototype.dMultiply = bnpDMultiply;
BigInteger.prototype.dAddOffset = bnpDAddOffset;
BigInteger.prototype.multiplyLowerTo = bnpMultiplyLowerTo;
BigInteger.prototype.multiplyUpperTo = bnpMultiplyUpperTo;
BigInteger.prototype.modInt = bnpModInt;
BigInteger.prototype.millerRabin = bnpMillerRabin;

// public
BigInteger.prototype.clone = bnClone;
BigInteger.prototype.intValue = bnIntValue;
BigInteger.prototype.byteValue = bnByteValue;
BigInteger.prototype.shortValue = bnShortValue;
BigInteger.prototype.signum = bnSigNum;
BigInteger.prototype.toByteArray = bnToByteArray;
BigInteger.prototype.equals = bnEquals;
BigInteger.prototype.min = bnMin;
BigInteger.prototype.max = bnMax;
BigInteger.prototype.and = bnAnd;
BigInteger.prototype.or = bnOr;
BigInteger.prototype.xor = bnXor;
BigInteger.prototype.andNot = bnAndNot;
BigInteger.prototype.not = bnNot;
BigInteger.prototype.shiftLeft = bnShiftLeft;
BigInteger.prototype.shiftRight = bnShiftRight;
BigInteger.prototype.getLowestSetBit = bnGetLowestSetBit;
BigInteger.prototype.bitCount = bnBitCount;
BigInteger.prototype.testBit = bnTestBit;
BigInteger.prototype.setBit = bnSetBit;
BigInteger.prototype.clearBit = bnClearBit;
BigInteger.prototype.flipBit = bnFlipBit;
BigInteger.prototype.add = bnAdd;
BigInteger.prototype.subtract = bnSubtract;
BigInteger.prototype.multiply = bnMultiply;
BigInteger.prototype.divide = bnDivide;
BigInteger.prototype.remainder = bnRemainder;
BigInteger.prototype.divideAndRemainder = bnDivideAndRemainder;
BigInteger.prototype.modPow = bnModPow;
BigInteger.prototype.modInverse = bnModInverse;
BigInteger.prototype.pow = bnPow;
BigInteger.prototype.gcd = bnGCD;
BigInteger.prototype.isProbablePrime = bnIsProbablePrime;

/*  From  bigint.js  */

  var USE_SJCL = true;
  
  // let's make this much cleaner
  if (USE_SJCL) {
      // why not?
      BigInt = BigInteger;
      // ZERO AND ONE are already taken care of
      BigInt.TWO = new BigInt("2",10);
  
      BigInt.setup = function(callback, fail_callback) {
      // nothing to do but go
      callback();
      }
  
      BigInt.prototype.toJSONObject = function() {
      return this.toString();
      };	    
  
  } else {
    // Removed this.  Not going to use the java applet - WM
  }
      
  BigInt.fromJSONObject = function(s) {
      return new BigInt(s, 10);
  };
  
  BigInt.fromInt = function(i) {
      return BigInt.fromJSONObject("" + i);
  };
  
  BigInt.use_applet = false;
  
  /* From random.js */ 

  /*
  * Random Number generation, now uses the glue to Java
  */
 
var Random = {};
 
 Random.GENERATOR = null;
 
 Random.setupGenerator = function() {
   // no longer needed
 /*    if (Random.GENERATOR == null && !USE_SJCL) {
         if (BigInt.use_applet) {
           var foo = BigInt.APPLET.newSecureRandom();
           Random.GENERATOR = BigInt.APPLET.newSecureRandom();
         } else {
           // we do it twice because of some weird bug;
           var foo = new java.security.SecureRandom();
           Random.GENERATOR = new java.security.SecureRandom();
         }
     }
     */
 };
 
 Random.getRandomInteger = function(max) {
   var bit_length = max.bitLength();
   Random.setupGenerator();
   var random;
   random = sjcl.random.randomWords(Math.ceil(bit_length / 32) + 2, 6);
   // we get a bit array instead of a BigInteger in this case
   var rand_bi = new BigInt(sjcl.codec.hex.fromBits(random), 16);
   return rand_bi.mod(max);
 };
 
 /*  From helios.js  */

var UTILS = {};

UTILS.array_remove_value = function(arr, val) {
  var new_arr = [];
 // _(arr).each(function(v, i) {
  arr.forEach(function(v, i) {  
  if (v != val) {
    new_arr.push(v);
    }
  });

  return new_arr;
};

UTILS.select_element_content = function(element) {
  var range;
  if (window.getSelection) { // FF, Safari, Opera
    var sel = window.getSelection();
    range = document.createRange();
    range.selectNodeContents(element);
    sel.removeAllRanges();
    sel.addRange(range);
  } else {
    document.selection.empty();
    range = document.body.createTextRange();
    range.moveToElementText(el);
    range.select();
  }
};

// a progress tracker
// UTILS.PROGRESS = Class.extend({
//   init: function() {
//     this.n_ticks = 0.0;
//     this.current_tick = 0.0;
//   },
  
//   addTicks: function(n_ticks) {
//     this.n_ticks += n_ticks;
//   },
  
//   tick: function() {
//     this.current_tick += 1.0;
//   },
  
//   progress: function() {
//     return Math.round((this.current_tick / this.n_ticks) * 100);
//   }
// });

// produce the same object but with keys sorted
UTILS.object_sort_keys = function(obj) {
  var new_obj = {};
  // _(_.keys(obj)).each(function(k) {
  //   new_obj[k] = obj[k];
  // });

  // Not sure this is correct
  Object.keys(obj).forEach(function(key) {
    new_obj[key] = obj[key];
  })
  return new_obj;
};

//
// Helios Stuff
//

var HELIOS = {};

// a bogus default public key to allow for ballot previewing, nothing more
// this public key should not be used ever, that's why the secret key is 
// not given.
HELIOS.get_bogus_public_key = function() {
  return ElGamal.PublicKey.fromJSONObject(JSON.parse('{"g": "14887492224963187634282421537186040801304008017743492304481737382571933937568724473847106029915040150784031882206090286938661464458896494215273989547889201144857352611058572236578734319505128042602372864570426550855201448111746579871811249114781674309062693442442368697449970648232621880001709535143047913661432883287150003429802392229361583608686643243349727791976247247948618930423866180410558458272606627111270040091203073580238905303994472202930783207472394578498507764703191288249547659899997131166130259700604433891232298182348403175947450284433411265966789131024573629546048637848902243503970966798589660808533", "p": "16328632084933010002384055033805457329601614771185955389739167309086214800406465799038583634953752941675645562182498120750264980492381375579367675648771293800310370964745767014243638518442553823973482995267304044326777047662957480269391322789378384619428596446446984694306187644767462460965622580087564339212631775817895958409016676398975671266179637898557687317076177218843233150695157881061257053019133078545928983562221396313169622475509818442661047018436264806901023966236718367204710755935899013750306107738002364137917426595737403871114187750804346564731250609196846638183903982387884578266136503697493474682071", "q": "61329566248342901292543872769978950870633559608669337131139375508370458778917", "y": "8049609819434159960341080485505898805169812475728892670296439571117039276506298996734003515763387841154083296559889658342770776712289026341097211553854451556820509582109412351633111518323196286638684857563764318086496248973278960517204721786711381246407429787246857335714789053255852788270719245108665072516217144567856965465184127683058484847896371648547639041764249621310049114411288049569523544645318180042074181845024934696975226908854019646138985505600641910417380245960080668869656287919893859172484656506039729440079008919716011166605004711585860172862472422362509002423715947870815838511146670204726187094944"}'));
};

// election
HELIOS.Election = Class.extend({
  init: function() {
  },
  
  toJSONObject: function() {
    var json_obj = {uuid : this.uuid,
    description : this.description, short_name : this.short_name, name : this.name,
    public_key: this.public_key.toJSONObject(), questions : this.questions,
    cast_url: this.cast_url, frozen_at: this.frozen_at,
    openreg: this.openreg, voters_hash: this.voters_hash,
    use_voter_aliases: this.use_voter_aliases,
    voting_starts_at: this.voting_starts_at,
    voting_ends_at: this.voting_ends_at};
    
    return UTILS.object_sort_keys(json_obj);
  },
  
  get_hash: function() {
    if (this.election_hash)
      return this.election_hash;
    
    // otherwise  
    return b64_sha256(this.toJSON());
  },
  
  toJSON: function() {
    // FIXME: only way around the backslash thing for now.... how ugly
    //return jQuery.toJSON(this.toJSONObject()).replace(/\//g,"\\/");
    return JSON.stringify(this.toJSONObject());
  }
});

HELIOS.Election.fromJSONString = function(raw_json) {
  var json_object = JSON.parse(raw_json);
  
  // let's hash the raw_json
  var election = HELIOS.Election.fromJSONObject(json_object);
  election.election_hash = b64_sha256(raw_json);
  
  return election;
};

HELIOS.Election.fromJSONObject = function(d) {
  var el = new HELIOS.Election();
  // _.extend(el, d);
  // convert from underscore.js
  for (var i in d) {
    el[i] = d[i];
  }
  
  // empty questions
  if (!el.questions)
    el.questions = [];
  
  if (el.public_key) {
    el.public_key = ElGamal.PublicKey.fromJSONObject(el.public_key);
  } else {
    // a placeholder that will allow hashing;
    el.public_key = HELIOS.get_bogus_public_key();
    el.BOGUS_P = true;
  }
    
  return el;
};

HELIOS.Election.setup = function(election) {
  return ELECTION.fromJSONObject(election);
};


// ballot handling
var BALLOT = {};

BALLOT.pretty_choices = function(election, ballot) {
    var questions = election.questions;
    var answers = ballot.answers;

    // process the answers
    // Converted
    var choices = (questions).map(function(q, q_num) {
	    return (answers[q_num]).map(function(ans) {
	      return questions[q_num].answers[ans];
	    });
    });

    return choices;
};


// open up a new window and do something with it.
UTILS.open_window_with_content = function(content, mime_type) {
    if (!mime_type)
	mime_type = "text/plain";
    if (BigInt.is_ie) {
	    w = window.open("");
	    w.document.open(mime_type);
	    w.document.write(content);
	    w.document.close();
    } else {
	    w = window.open("data:" + mime_type + "," + encodeURIComponent(content));
    }
};

// generate an array of the first few plaintexts
UTILS.generate_plaintexts = function(pk, min, max) {
  var last_plaintext = BigInt.ONE;

  // an array of plaintexts
  var plaintexts = [];
  
  if (min == null)
    min = 0;
  
  // questions with more than one possible answer, add to the array.
  for (var i=0; i<=max; i++) {
    if (i >= min)
      plaintexts.push(new ElGamal.Plaintext(last_plaintext, pk, false));
    last_plaintext = last_plaintext.multiply(pk.g).mod(pk.p);
  }
  
  return plaintexts;
}


//
// crypto
//


HELIOS.EncryptedAnswer = Class.extend({
  init: function(question, answer, pk, progress) {    
    // if nothing in the constructor
    if (question == null)
      return;

    // store answer
    // CHANGE 2008-08-06: answer is now an *array* of answers, not just a single integer
    this.answer = answer;

    // do the encryption
    var enc_result = this.doEncryption(question, answer, pk, null, progress);

    this.choices = enc_result.choices;
    this.randomness = enc_result.randomness;
    this.individual_proofs = enc_result.individual_proofs;
    this.overall_proof = enc_result.overall_proof;    
  },
  
  doEncryption: function(question, answer, pk, randomness, progress) {
    var choices = [];
    var individual_proofs = [];
    var overall_proof = null;
    
    // possible plaintexts [question.min .. , question.max]
    var plaintexts = null;
    if (question.max != null) {
      plaintexts = UTILS.generate_plaintexts(pk, question.min, question.max);
    }
    
    var zero_one_plaintexts = UTILS.generate_plaintexts(pk, 0, 1);
    
    // keep track of whether we need to generate new randomness
    var generate_new_randomness = false;    
    if (!randomness) {
      randomness = [];
      generate_new_randomness = true;
    }
    
    // keep track of number of options selected.
    var num_selected_answers = 0;
    
    // go through each possible answer and encrypt either a g^0 or a g^1.
    for (var i=0; i<question.answers.length; i++) {
      var index, plaintext_index;
      // if this is the answer, swap them so m is encryption 1 (g)
      if ((answer).includes(i)) {
        plaintext_index = 1;
        num_selected_answers += 1;
      } else {
        plaintext_index = 0;
      }

      // generate randomness?
      if (generate_new_randomness) {
        randomness[i] = Random.getRandomInteger(pk.q);        
      }

      choices[i] = ElGamal.encrypt(pk, zero_one_plaintexts[plaintext_index], randomness[i]);
      
      // generate proof
      if (generate_new_randomness) {
        // generate proof that this ciphertext is a 0 or a 1
        individual_proofs[i] = choices[i].generateDisjunctiveProof(zero_one_plaintexts, plaintext_index, randomness[i], ElGamal.disjunctive_challenge_generator);        
      }
      
      if (progress)
        progress.tick();
    }

    if (generate_new_randomness && question.max != null) {
      // we also need proof that the whole thing sums up to the right number
      // only if max is non-null, otherwise it's full approval voting
    
      // compute the homomorphic sum of all the options
      var hom_sum = choices[0];
      var rand_sum = randomness[0];
      for (var i=1; i<question.answers.length; i++) {
        hom_sum = hom_sum.multiply(choices[i]);
        rand_sum = rand_sum.add(randomness[i]).mod(pk.q);
      }
    
      // prove that the sum is 0 or 1 (can be "blank vote" for this answer)
      // num_selected_answers is 0 or 1, which is the index into the plaintext that is actually encoded
      //
      // now that "plaintexts" only contains the array of plaintexts that are possible starting with min
      // and going to max, the num_selected_answers needs to be reduced by min to be the proper index
      var overall_plaintext_index = num_selected_answers;
      if (question.min)
        overall_plaintext_index -= question.min;
      
      overall_proof = hom_sum.generateDisjunctiveProof(plaintexts, overall_plaintext_index, rand_sum, ElGamal.disjunctive_challenge_generator);

      if (progress) {
        for (var i=0; i<question.max; i++)
          progress.tick();
      }
    }
    
    return {
      'choices' : choices,
      'randomness' : randomness,
      'individual_proofs' : individual_proofs,
      'overall_proof' : overall_proof
    };
  },
  
  clearPlaintexts: function() {
    this.answer = null;
    this.randomness = null;
  },
  
  // FIXME: should verifyEncryption really generate proofs? Overkill.
  verifyEncryption: function(question, pk) {
    var result = this.doEncryption(question, this.answer, pk, this.randomness);

    // check that we have the same number of ciphertexts
    if (result.choices.length != this.choices.length) {
      return false;      
    }
      
    // check the ciphertexts
    for (var i=0; i<result.choices.length; i++) {
      if (!result.choices[i].equals(this.choices[i])) {
        // alert ("oy: " + result.choices[i] + "/" + this.choices[i]);
        return false;
      }
    }
    
    // we made it, we're good
    return true;
  },
  
  toString: function() {
    // get each ciphertext as a JSON string
    // Converted
    var choices_strings = (this.choices).map(function(c) {return c.toString();});
    return choices_strings.join("|");
  },
  
  toJSONObject: function(include_plaintext) {
    var return_obj = {
      // Converted
      'choices' : (this.choices).map(function(choice) {
        return choice.toJSONObject();
      }),
      'individual_proofs' : (this.individual_proofs).map(function(disj_proof) {
        return disj_proof.toJSONObject();
      })
    };
    
    if (this.overall_proof != null) {
      return_obj.overall_proof = this.overall_proof.toJSONObject();
    } else {
      return_obj.overall_proof = null;
    }
    
    if (include_plaintext) {
      return_obj.answer = this.answer;
      // Converted
      return_obj.randomness = (this.randomness).map(function(r) {
        return r.toJSONObject();
      });
    }
    
    return return_obj;
  }
});

HELIOS.EncryptedAnswer.fromJSONObject = function(d, election) {
  var ea = new HELIOS.EncryptedAnswer();
  // Converted
  ea.choices = (d.choices).map(function(choice) {
    return ElGamal.Ciphertext.fromJSONObject(choice, election.public_key);
  });
  
  ea.individual_proofs = (d.individual_proofs).map(function (p) {
    return ElGamal.DisjunctiveProof.fromJSONObject(p);
  });
  
  ea.overall_proof = ElGamal.DisjunctiveProof.fromJSONObject(d.overall_proof);
  
  // possibly load randomness and plaintext
  if (d.randomness) {
    // Converted
    ea.randomness = (d.randomness).map(function(r) {
      return BigInt.fromJSONObject(r);
    });
    ea.answer = d.answer;
  }
  
  return ea;
};

HELIOS.EncryptedVote = Class.extend({
  init: function(election, answers, progress) {
    // empty constructor
    if (election == null)
      return;

    // keep information about the election around
    this.election_uuid = election.uuid;
    this.election_hash = election.get_hash();
    this.election = election;
     
    if (answers == null)
      return;
      
    var n_questions = election.questions.length;
    this.encrypted_answers = [];

    if (progress) {
      // set up the number of ticks
      // _(election.questions).each(function(q, q_num) {
        // Converted
        (election.questions).forEach(function(q) {
        // + 1 for the overall proof
        progress.addTicks(q.answers.length);
        if (q.max != null)
          progress.addTicks(q.max);
      });

      progress.addTicks(0, n_questions);
    }
      
    // loop through questions
    for (var i=0; i<n_questions; i++) {
      this.encrypted_answers[i] = new HELIOS.EncryptedAnswer(election.questions[i], answers[i], election.public_key, progress);
    }    
  },

  toString: function() {
    // for each question, get the encrypted answer as a string
    // Converted
    var answer_strings = (this.encrypted_answers).map(function(a) {return a.toString();});
    
    return answer_strings.join("//");
  },
  
  clearPlaintexts: function() {
    // _(this.encrypted_answers).each(function(ea) {
      // Converted
      (this.encrypted_answers).forEach(function(ea) {
      ea.clearPlaintexts();
    });
  },
  
  verifyEncryption: function(questions, pk) {
    var overall_result = true;
    // _(this.encrypted_answers).each(function(ea, i) {
    // Converted
    (this.encrypted_answers).forEach(function(ea, i) {
      overall_result = overall_result && ea.verifyEncryption(questions[i], pk);
    });
    return overall_result;
  },
  
  toJSONObject: function(include_plaintext) {
    // Converted
      var answers = (this.encrypted_answers).map(function(ea,i) {
      return ea.toJSONObject(include_plaintext);
    });
    
    return {
      answers : answers,
      election_hash : this.election_hash,
      election_uuid : this.election_uuid
    }
  },
  
  get_hash: function() {
     return b64_sha256(JSON.stringify(this.toJSONObject()));
  },
  
  get_audit_trail: function() {
    return this.toJSONObject(true);
  },
  
  verifyProofs: function(pk, outcome_callback) {
    var zero_or_one = UTILS.generate_plaintexts(pk, 0, 1);

    var VALID_P = true;
    
    var self = this;
    
    // for each question and associate encrypted answer
    // _(this.encrypted_answers).each(function(enc_answer, ea_num) {
      // Converted
      (this.encrypted_answers).forEach(function(enc_answer, ea_num) {
        var overall_result = 1;

        // the max number of answers (decides whether this is approval or not and requires an overall proof)
        var max = self.election.questions[ea_num].max;

        // go through each individual proof
        // _(enc_answer.choices).each(function(choice, choice_num) {
        // Converted
        (enc_answer.choices).forEach(function(choice, choice_num) {
          var result = choice.verifyDisjunctiveProof(zero_or_one, enc_answer.individual_proofs[choice_num], ElGamal.disjunctive_challenge_generator);
          outcome_callback(ea_num, choice_num, result, choice);
          
          VALID_P = VALID_P && result;
           
          // keep track of homomorphic product, if needed
          if (max != null)
            overall_result = choice.multiply(overall_result);
        });
        
        if (max != null) {
          // possible plaintexts [0, 1, .. , question.max]
          var plaintexts = UTILS.generate_plaintexts(pk, self.election.questions[ea_num].min, self.election.questions[ea_num].max);
        
          // check the proof on the overall product
          var overall_check = overall_result.verifyDisjunctiveProof(plaintexts, enc_answer.overall_proof, ElGamal.disjunctive_challenge_generator);
          outcome_callback(ea_num, null, overall_check, null);
          VALID_P = VALID_P && overall_check;
        } else {
          // check to make sure the overall_proof is null, since it's approval voting
          VALID_P = VALID_P && (enc_answer.overall_proof == null)
        }
    });
    
    return VALID_P;
  }
});

HELIOS.EncryptedVote.fromJSONObject = function(d, election) {
  if (d == null)
    return null;
    
  var ev = new HELIOS.EncryptedVote(election);
  // Converted
  ev.encrypted_answers = (d.answers).map(function(ea) {
    return HELIOS.EncryptedAnswer.fromJSONObject(ea, election);
  });
  
  ev.election_hash = d.election_hash;
  ev.election_uuid = d.election_uuid;
  
  return ev;
};

// create an encrypted vote from a set of answers
HELIOS.EncryptedVote.fromEncryptedAnswers = function(election, enc_answers) {
    var enc_vote = new HELIOS.EncryptedVote(election, null);
    enc_vote.encrypted_answers = [];
    // _(enc_answers).each(function(enc_answer, answer_num) {
    // Converted
    (enc_answers).forEach(function(enc_answer, answer_num) {
	    enc_vote.encrypted_answers[answer_num] = enc_answer;
    });
    return enc_vote;
};

//
// Tally abstraction
//

HELIOS.Tally = Class.extend({
  init: function(raw_tally, num_tallied) {
    this.tally = raw_tally;
    this.num_tallied = num_tallied;
  },
  
  toJSONObject: function() {
    // Converted
    var tally_json_obj = (this.tally).map(function(one_q) {
      return (one_q).map(function(one_a) {
        return one_a.toJSONObject();
      });
    });
    
    return {
      num_tallied : this.num_tallied,
      tally: tally_json_obj
    };
  }
  
});

HELIOS.Tally.fromJSONObject = function(d, public_key) {
  var num_tallied = d['num_tallied'];
  // Converted
  var raw_tally = (d['tally']).map(function(one_q) {
    return (one_q).map(function(one_a) {
      var new_val= ElGamal.Ciphertext.fromJSONObject(one_a, public_key);
      return new_val;
    });
  });
  
  return new HELIOS.Tally(raw_tally, num_tallied);
};

//
// distributed decryption : Trustees
//

// a utility function for jsonifying a list of lists of items
HELIOS.jsonify_list_of_lists = function(lol) {
  if (!lol)
    return null;
    
  // return _(lol).map(function(sublist) {return _(sublist).map(function(item) {return item.toJSONObject();})});
  // Converted
  return (lol).map(function(sublist) {return (sublist).map(function(item) {return item.toJSONObject();})});
};

// a utility function for doing the opposite with an item-level de-jsonifier
HELIOS.dejsonify_list_of_lists = function(lol, item_dejsonifier) {
  if (!lol)
    return null;
  // Converted
  return (lol).map(function(sublist) {return (sublist).map(function(item) {return item_dejsonifier(item);})});
}

HELIOS.Trustee = Class.extend({
  init: function(uuid, public_key, public_key_hash, pok, decryption_factors, decryption_proofs) {
    this.uuid = uuid;
    this.public_key = public_key;
    this.public_key_hash = public_key_hash;
    this.pok = pok;
    this.decryption_factors = decryption_factors;
    this.decryption_proofs = decryption_proofs;
  },
  
  toJSONObject: function() {
    return {
      'decryption_factors' : HELIOS.jsonify_list_of_lists(this.decryption_factors),
      'decryption_proofs' : HELIOS.jsonify_list_of_list(this.decryption_proofs),
      'email' : this.email, 'name' : this.name, 'pok' : this.pok.toJSONObject(), 'public_key' : this.public_key.toJSONObject()
    };
  }
});

HELIOS.Trustee.fromJSONObject = function(d) {
  return new HELIOS.Trustee(d.uuid,
    ElGamal.PublicKey.fromJSONObject(d.public_key), d.public_key_hash, ElGamal.DLogProof.fromJSONObject(d.pok),
    HELIOS.dejsonify_list_of_lists(d.decryption_factors, BigInt.fromJSONObject),
    HELIOS.dejsonify_list_of_lists(d.decryption_proofs, ElGamal.Proof.fromJSONObject));
};

/*  From sjcl.js  */

"use strict";function q(a){throw a;}var t=void 0,u=!1; 
var sjcl={cipher:{},hash:{},keyexchange:{},mode:{},misc:{},codec:{},exception:{corrupt:function(a){this.toString=function(){return"CORRUPT: "+this.message};this.message=a},invalid:function(a){this.toString=function(){return"INVALID: "+this.message};this.message=a},bug:function(a){this.toString=function(){return"BUG: "+this.message};this.message=a},notReady:function(a){this.toString=function(){return"NOT READY: "+this.message};this.message=a}}};
"undefined"!=typeof module&&module.exports&&(module.exports=sjcl);
sjcl.cipher.aes=function(a){this.j[0][0][0]||this.D();var b,c,d,e,f=this.j[0][4],g=this.j[1];b=a.length;var h=1;4!==b&&(6!==b&&8!==b)&&q(new sjcl.exception.invalid("invalid aes key size"));this.a=[d=a.slice(0),e=[]];for(a=b;a<4*b+28;a++){c=d[a-1];if(0===a%b||8===b&&4===a%b)c=f[c>>>24]<<24^f[c>>16&255]<<16^f[c>>8&255]<<8^f[c&255],0===a%b&&(c=c<<8^c>>>24^h<<24,h=h<<1^283*(h>>7));d[a]=d[a-b]^c}for(b=0;a;b++,a--)c=d[b&3?a:a-4],e[b]=4>=a||4>b?c:g[0][f[c>>>24]]^g[1][f[c>>16&255]]^g[2][f[c>>8&255]]^g[3][f[c&
255]]};
sjcl.cipher.aes.prototype={encrypt:function(a){return y(this,a,0)},decrypt:function(a){return y(this,a,1)},j:[[[],[],[],[],[]],[[],[],[],[],[]]],D:function(){var a=this.j[0],b=this.j[1],c=a[4],d=b[4],e,f,g,h=[],l=[],k,n,m,p;for(e=0;0x100>e;e++)l[(h[e]=e<<1^283*(e>>7))^e]=e;for(f=g=0;!c[f];f^=k||1,g=l[g]||1){m=g^g<<1^g<<2^g<<3^g<<4;m=m>>8^m&255^99;c[f]=m;d[m]=f;n=h[e=h[k=h[f]]];p=0x1010101*n^0x10001*e^0x101*k^0x1010100*f;n=0x101*h[m]^0x1010100*m;for(e=0;4>e;e++)a[e][f]=n=n<<24^n>>>8,b[e][m]=p=p<<24^p>>>8}for(e=
0;5>e;e++)a[e]=a[e].slice(0),b[e]=b[e].slice(0)}};
function y(a,b,c){4!==b.length&&q(new sjcl.exception.invalid("invalid aes block size"));var d=a.a[c],e=b[0]^d[0],f=b[c?3:1]^d[1],g=b[2]^d[2];b=b[c?1:3]^d[3];var h,l,k,n=d.length/4-2,m,p=4,s=[0,0,0,0];h=a.j[c];a=h[0];var r=h[1],v=h[2],w=h[3],x=h[4];for(m=0;m<n;m++)h=a[e>>>24]^r[f>>16&255]^v[g>>8&255]^w[b&255]^d[p],l=a[f>>>24]^r[g>>16&255]^v[b>>8&255]^w[e&255]^d[p+1],k=a[g>>>24]^r[b>>16&255]^v[e>>8&255]^w[f&255]^d[p+2],b=a[b>>>24]^r[e>>16&255]^v[f>>8&255]^w[g&255]^d[p+3],p+=4,e=h,f=l,g=k;for(m=0;4>
m;m++)s[c?3&-m:m]=x[e>>>24]<<24^x[f>>16&255]<<16^x[g>>8&255]<<8^x[b&255]^d[p++],h=e,e=f,f=g,g=b,b=h;return s}
sjcl.bitArray={bitSlice:function(a,b,c){a=sjcl.bitArray.O(a.slice(b/32),32-(b&31)).slice(1);return c===t?a:sjcl.bitArray.clamp(a,c-b)},extract:function(a,b,c){var d=Math.floor(-b-c&31);return((b+c-1^b)&-32?a[b/32|0]<<32-d^a[b/32+1|0]>>>d:a[b/32|0]>>>d)&(1<<c)-1},concat:function(a,b){if(0===a.length||0===b.length)return a.concat(b);var c=a[a.length-1],d=sjcl.bitArray.getPartial(c);return 32===d?a.concat(b):sjcl.bitArray.O(b,d,c|0,a.slice(0,a.length-1))},bitLength:function(a){var b=a.length;return 0===
b?0:32*(b-1)+sjcl.bitArray.getPartial(a[b-1])},clamp:function(a,b){if(32*a.length<b)return a;a=a.slice(0,Math.ceil(b/32));var c=a.length;b&=31;0<c&&b&&(a[c-1]=sjcl.bitArray.partial(b,a[c-1]&2147483648>>b-1,1));return a},partial:function(a,b,c){return 32===a?b:(c?b|0:b<<32-a)+0x10000000000*a},getPartial:function(a){return Math.round(a/0x10000000000)||32},equal:function(a,b){if(sjcl.bitArray.bitLength(a)!==sjcl.bitArray.bitLength(b))return u;var c=0,d;for(d=0;d<a.length;d++)c|=a[d]^b[d];return 0===
c},O:function(a,b,c,d){var e;e=0;for(d===t&&(d=[]);32<=b;b-=32)d.push(c),c=0;if(0===b)return d.concat(a);for(e=0;e<a.length;e++)d.push(c|a[e]>>>b),c=a[e]<<32-b;e=a.length?a[a.length-1]:0;a=sjcl.bitArray.getPartial(e);d.push(sjcl.bitArray.partial(b+a&31,32<b+a?c:d.pop(),1));return d},k:function(a,b){return[a[0]^b[0],a[1]^b[1],a[2]^b[2],a[3]^b[3]]}};
sjcl.codec.utf8String={fromBits:function(a){var b="",c=sjcl.bitArray.bitLength(a),d,e;for(d=0;d<c/8;d++)0===(d&3)&&(e=a[d/4]),b+=String.fromCharCode(e>>>24),e<<=8;return decodeURIComponent(escape(b))},toBits:function(a){a=unescape(encodeURIComponent(a));var b=[],c,d=0;for(c=0;c<a.length;c++)d=d<<8|a.charCodeAt(c),3===(c&3)&&(b.push(d),d=0);c&3&&b.push(sjcl.bitArray.partial(8*(c&3),d));return b}};
sjcl.codec.hex={fromBits:function(a){var b="",c;for(c=0;c<a.length;c++)b+=((a[c]|0)+0xf00000000000).toString(16).substr(4);return b.substr(0,sjcl.bitArray.bitLength(a)/4)},toBits:function(a){var b,c=[],d;a=a.replace(/\s|0x/g,"");d=a.length;a+="00000000";for(b=0;b<a.length;b+=8)c.push(parseInt(a.substr(b,8),16)^0);return sjcl.bitArray.clamp(c,4*d)}};
sjcl.codec.base64={I:"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",fromBits:function(a,b,c){var d="",e=0,f=sjcl.codec.base64.I,g=0,h=sjcl.bitArray.bitLength(a);c&&(f=f.substr(0,62)+"-_");for(c=0;6*d.length<h;)d+=f.charAt((g^a[c]>>>e)>>>26),6>e?(g=a[c]<<6-e,e+=26,c++):(g<<=6,e-=6);for(;d.length&3&&!b;)d+="=";return d},toBits:function(a,b){a=a.replace(/\s|=/g,"");var c=[],d,e=0,f=sjcl.codec.base64.I,g=0,h;b&&(f=f.substr(0,62)+"-_");for(d=0;d<a.length;d++)h=f.indexOf(a.charAt(d)),
0>h&&q(new sjcl.exception.invalid("this isn't base64!")),26<e?(e-=26,c.push(g^h>>>e),g=h<<32-e):(e+=6,g^=h<<32-e);e&56&&c.push(sjcl.bitArray.partial(e&56,g,1));return c}};sjcl.codec.base64url={fromBits:function(a){return sjcl.codec.base64.fromBits(a,1,1)},toBits:function(a){return sjcl.codec.base64.toBits(a,1)}};sjcl.hash.sha256=function(a){this.a[0]||this.D();a?(this.q=a.q.slice(0),this.m=a.m.slice(0),this.g=a.g):this.reset()};sjcl.hash.sha256.hash=function(a){return(new sjcl.hash.sha256).update(a).finalize()};
sjcl.hash.sha256.prototype={blockSize:512,reset:function(){this.q=this.M.slice(0);this.m=[];this.g=0;return this},update:function(a){"string"===typeof a&&(a=sjcl.codec.utf8String.toBits(a));var b,c=this.m=sjcl.bitArray.concat(this.m,a);b=this.g;a=this.g=b+sjcl.bitArray.bitLength(a);for(b=512+b&-512;b<=a;b+=512)z(this,c.splice(0,16));return this},finalize:function(){var a,b=this.m,c=this.q,b=sjcl.bitArray.concat(b,[sjcl.bitArray.partial(1,1)]);for(a=b.length+2;a&15;a++)b.push(0);b.push(Math.floor(this.g/
4294967296));for(b.push(this.g|0);b.length;)z(this,b.splice(0,16));this.reset();return c},M:[],a:[],D:function(){function a(a){return 0x100000000*(a-Math.floor(a))|0}var b=0,c=2,d;a:for(;64>b;c++){for(d=2;d*d<=c;d++)if(0===c%d)continue a;8>b&&(this.M[b]=a(Math.pow(c,0.5)));this.a[b]=a(Math.pow(c,1/3));b++}}};
function z(a,b){var c,d,e,f=b.slice(0),g=a.q,h=a.a,l=g[0],k=g[1],n=g[2],m=g[3],p=g[4],s=g[5],r=g[6],v=g[7];for(c=0;64>c;c++)16>c?d=f[c]:(d=f[c+1&15],e=f[c+14&15],d=f[c&15]=(d>>>7^d>>>18^d>>>3^d<<25^d<<14)+(e>>>17^e>>>19^e>>>10^e<<15^e<<13)+f[c&15]+f[c+9&15]|0),d=d+v+(p>>>6^p>>>11^p>>>25^p<<26^p<<21^p<<7)+(r^p&(s^r))+h[c],v=r,r=s,s=p,p=m+d|0,m=n,n=k,k=l,l=d+(k&n^m&(k^n))+(k>>>2^k>>>13^k>>>22^k<<30^k<<19^k<<10)|0;g[0]=g[0]+l|0;g[1]=g[1]+k|0;g[2]=g[2]+n|0;g[3]=g[3]+m|0;g[4]=g[4]+p|0;g[5]=g[5]+s|0;g[6]=
g[6]+r|0;g[7]=g[7]+v|0}
sjcl.mode.ccm={name:"ccm",encrypt:function(a,b,c,d,e){var f,g=b.slice(0),h=sjcl.bitArray,l=h.bitLength(c)/8,k=h.bitLength(g)/8;e=e||64;d=d||[];7>l&&q(new sjcl.exception.invalid("ccm: iv must be at least 7 bytes"));for(f=2;4>f&&k>>>8*f;f++);f<15-l&&(f=15-l);c=h.clamp(c,8*(15-f));b=sjcl.mode.ccm.K(a,b,c,d,e,f);g=sjcl.mode.ccm.n(a,g,c,b,e,f);return h.concat(g.data,g.tag)},decrypt:function(a,b,c,d,e){e=e||64;d=d||[];var f=sjcl.bitArray,g=f.bitLength(c)/8,h=f.bitLength(b),l=f.clamp(b,h-e),k=f.bitSlice(b,
h-e),h=(h-e)/8;7>g&&q(new sjcl.exception.invalid("ccm: iv must be at least 7 bytes"));for(b=2;4>b&&h>>>8*b;b++);b<15-g&&(b=15-g);c=f.clamp(c,8*(15-b));l=sjcl.mode.ccm.n(a,l,c,k,e,b);a=sjcl.mode.ccm.K(a,l.data,c,d,e,b);f.equal(l.tag,a)||q(new sjcl.exception.corrupt("ccm: tag doesn't match"));return l.data},K:function(a,b,c,d,e,f){var g=[],h=sjcl.bitArray,l=h.k;e/=8;(e%2||4>e||16<e)&&q(new sjcl.exception.invalid("ccm: invalid tag length"));(0xffffffff<d.length||0xffffffff<b.length)&&q(new sjcl.exception.bug("ccm: can't deal with 4GiB or more data"));
f=[h.partial(8,(d.length?64:0)|e-2<<2|f-1)];f=h.concat(f,c);f[3]|=h.bitLength(b)/8;f=a.encrypt(f);if(d.length){c=h.bitLength(d)/8;65279>=c?g=[h.partial(16,c)]:0xffffffff>=c&&(g=h.concat([h.partial(16,65534)],[c]));g=h.concat(g,d);for(d=0;d<g.length;d+=4)f=a.encrypt(l(f,g.slice(d,d+4).concat([0,0,0])))}for(d=0;d<b.length;d+=4)f=a.encrypt(l(f,b.slice(d,d+4).concat([0,0,0])));return h.clamp(f,8*e)},n:function(a,b,c,d,e,f){var g,h=sjcl.bitArray;g=h.k;var l=b.length,k=h.bitLength(b);c=h.concat([h.partial(8,
f-1)],c).concat([0,0,0]).slice(0,4);d=h.bitSlice(g(d,a.encrypt(c)),0,e);if(!l)return{tag:d,data:[]};for(g=0;g<l;g+=4)c[3]++,e=a.encrypt(c),b[g]^=e[0],b[g+1]^=e[1],b[g+2]^=e[2],b[g+3]^=e[3];return{tag:d,data:h.clamp(b,k)}}};
sjcl.mode.ocb2={name:"ocb2",encrypt:function(a,b,c,d,e,f){128!==sjcl.bitArray.bitLength(c)&&q(new sjcl.exception.invalid("ocb iv must be 128 bits"));var g,h=sjcl.mode.ocb2.G,l=sjcl.bitArray,k=l.k,n=[0,0,0,0];c=h(a.encrypt(c));var m,p=[];d=d||[];e=e||64;for(g=0;g+4<b.length;g+=4)m=b.slice(g,g+4),n=k(n,m),p=p.concat(k(c,a.encrypt(k(c,m)))),c=h(c);m=b.slice(g);b=l.bitLength(m);g=a.encrypt(k(c,[0,0,0,b]));m=l.clamp(k(m.concat([0,0,0]),g),b);n=k(n,k(m.concat([0,0,0]),g));n=a.encrypt(k(n,k(c,h(c))));d.length&&
(n=k(n,f?d:sjcl.mode.ocb2.pmac(a,d)));return p.concat(l.concat(m,l.clamp(n,e)))},decrypt:function(a,b,c,d,e,f){128!==sjcl.bitArray.bitLength(c)&&q(new sjcl.exception.invalid("ocb iv must be 128 bits"));e=e||64;var g=sjcl.mode.ocb2.G,h=sjcl.bitArray,l=h.k,k=[0,0,0,0],n=g(a.encrypt(c)),m,p,s=sjcl.bitArray.bitLength(b)-e,r=[];d=d||[];for(c=0;c+4<s/32;c+=4)m=l(n,a.decrypt(l(n,b.slice(c,c+4)))),k=l(k,m),r=r.concat(m),n=g(n);p=s-32*c;m=a.encrypt(l(n,[0,0,0,p]));m=l(m,h.clamp(b.slice(c),p).concat([0,0,0]));
k=l(k,m);k=a.encrypt(l(k,l(n,g(n))));d.length&&(k=l(k,f?d:sjcl.mode.ocb2.pmac(a,d)));h.equal(h.clamp(k,e),h.bitSlice(b,s))||q(new sjcl.exception.corrupt("ocb: tag doesn't match"));return r.concat(h.clamp(m,p))},pmac:function(a,b){var c,d=sjcl.mode.ocb2.G,e=sjcl.bitArray,f=e.k,g=[0,0,0,0],h=a.encrypt([0,0,0,0]),h=f(h,d(d(h)));for(c=0;c+4<b.length;c+=4)h=d(h),g=f(g,a.encrypt(f(h,b.slice(c,c+4))));c=b.slice(c);128>e.bitLength(c)&&(h=f(h,d(h)),c=e.concat(c,[-2147483648,0,0,0]));g=f(g,c);return a.encrypt(f(d(f(h,
d(h))),g))},G:function(a){return[a[0]<<1^a[1]>>>31,a[1]<<1^a[2]>>>31,a[2]<<1^a[3]>>>31,a[3]<<1^135*(a[0]>>>31)]}};
sjcl.mode.gcm={name:"gcm",encrypt:function(a,b,c,d,e){var f=b.slice(0);b=sjcl.bitArray;d=d||[];a=sjcl.mode.gcm.n(!0,a,f,d,c,e||128);return b.concat(a.data,a.tag)},decrypt:function(a,b,c,d,e){var f=b.slice(0),g=sjcl.bitArray,h=g.bitLength(f);e=e||128;d=d||[];e<=h?(b=g.bitSlice(f,h-e),f=g.bitSlice(f,0,h-e)):(b=f,f=[]);a=sjcl.mode.gcm.n(u,a,f,d,c,e);g.equal(a.tag,b)||q(new sjcl.exception.corrupt("gcm: tag doesn't match"));return a.data},U:function(a,b){var c,d,e,f,g,h=sjcl.bitArray.k;e=[0,0,0,0];f=b.slice(0);
for(c=0;128>c;c++){(d=0!==(a[Math.floor(c/32)]&1<<31-c%32))&&(e=h(e,f));g=0!==(f[3]&1);for(d=3;0<d;d--)f[d]=f[d]>>>1|(f[d-1]&1)<<31;f[0]>>>=1;g&&(f[0]^=-0x1f000000)}return e},f:function(a,b,c){var d,e=c.length;b=b.slice(0);for(d=0;d<e;d+=4)b[0]^=0xffffffff&c[d],b[1]^=0xffffffff&c[d+1],b[2]^=0xffffffff&c[d+2],b[3]^=0xffffffff&c[d+3],b=sjcl.mode.gcm.U(b,a);return b},n:function(a,b,c,d,e,f){var g,h,l,k,n,m,p,s,r=sjcl.bitArray;m=c.length;p=r.bitLength(c);s=r.bitLength(d);h=r.bitLength(e);g=b.encrypt([0,
0,0,0]);96===h?(e=e.slice(0),e=r.concat(e,[1])):(e=sjcl.mode.gcm.f(g,[0,0,0,0],e),e=sjcl.mode.gcm.f(g,e,[0,0,Math.floor(h/0x100000000),h&0xffffffff]));h=sjcl.mode.gcm.f(g,[0,0,0,0],d);n=e.slice(0);d=h.slice(0);a||(d=sjcl.mode.gcm.f(g,h,c));for(k=0;k<m;k+=4)n[3]++,l=b.encrypt(n),c[k]^=l[0],c[k+1]^=l[1],c[k+2]^=l[2],c[k+3]^=l[3];c=r.clamp(c,p);a&&(d=sjcl.mode.gcm.f(g,h,c));a=[Math.floor(s/0x100000000),s&0xffffffff,Math.floor(p/0x100000000),p&0xffffffff];d=sjcl.mode.gcm.f(g,d,a);l=b.encrypt(e);d[0]^=l[0];
d[1]^=l[1];d[2]^=l[2];d[3]^=l[3];return{tag:r.bitSlice(d,0,f),data:c}}};sjcl.misc.hmac=function(a,b){this.L=b=b||sjcl.hash.sha256;var c=[[],[]],d,e=b.prototype.blockSize/32;this.o=[new b,new b];a.length>e&&(a=b.hash(a));for(d=0;d<e;d++)c[0][d]=a[d]^909522486,c[1][d]=a[d]^1549556828;this.o[0].update(c[0]);this.o[1].update(c[1])};sjcl.misc.hmac.prototype.encrypt=sjcl.misc.hmac.prototype.mac=function(a){a=(new this.L(this.o[0])).update(a).finalize();return(new this.L(this.o[1])).update(a).finalize()};
sjcl.misc.pbkdf2=function(a,b,c,d,e){c=c||1E3;(0>d||0>c)&&q(sjcl.exception.invalid("invalid params to pbkdf2"));"string"===typeof a&&(a=sjcl.codec.utf8String.toBits(a));e=e||sjcl.misc.hmac;a=new e(a);var f,g,h,l,k=[],n=sjcl.bitArray;for(l=1;32*k.length<(d||1);l++){e=f=a.encrypt(n.concat(b,[l]));for(g=1;g<c;g++){f=a.encrypt(f);for(h=0;h<f.length;h++)e[h]^=f[h]}k=k.concat(e)}d&&(k=n.clamp(k,d));return k};
sjcl.prng=function(a){this.b=[new sjcl.hash.sha256];this.h=[0];this.F=0;this.t={};this.C=0;this.J={};this.N=this.c=this.i=this.T=0;this.a=[0,0,0,0,0,0,0,0];this.e=[0,0,0,0];this.A=t;this.B=a;this.p=u;this.z={progress:{},seeded:{}};this.l=this.S=0;this.u=1;this.w=2;this.Q=0x10000;this.H=[0,48,64,96,128,192,0x100,384,512,768,1024];this.R=3E4;this.P=80};
sjcl.prng.prototype={randomWords:function(a,b){var c=[],d;d=this.isReady(b);var e;d===this.l&&q(new sjcl.exception.notReady("generator isn't seeded"));if(d&this.w){d=!(d&this.u);e=[];var f=0,g;this.N=e[0]=(new Date).valueOf()+this.R;for(g=0;16>g;g++)e.push(0x100000000*Math.random()|0);for(g=0;g<this.b.length&&!(e=e.concat(this.b[g].finalize()),f+=this.h[g],this.h[g]=0,!d&&this.F&1<<g);g++);this.F>=1<<this.b.length&&(this.b.push(new sjcl.hash.sha256),this.h.push(0));this.c-=f;f>this.i&&(this.i=f);this.F++;
this.a=sjcl.hash.sha256.hash(this.a.concat(e));this.A=new sjcl.cipher.aes(this.a);for(d=0;4>d&&!(this.e[d]=this.e[d]+1|0,this.e[d]);d++);}for(d=0;d<a;d+=4)0===(d+1)%this.Q&&A(this),e=B(this),c.push(e[0],e[1],e[2],e[3]);A(this);return c.slice(0,a)},setDefaultParanoia:function(a){this.B=a},addEntropy:function(a,b,c){c=c||"user";var d,e,f=(new Date).valueOf(),g=this.t[c],h=this.isReady(),l=0;d=this.J[c];d===t&&(d=this.J[c]=this.T++);g===t&&(g=this.t[c]=0);this.t[c]=(this.t[c]+1)%this.b.length;switch(typeof a){case "number":b===
t&&(b=1);this.b[g].update([d,this.C++,1,b,f,1,a|0]);break;case "object":c=Object.prototype.toString.call(a);if("[object Uint32Array]"===c){e=[];for(c=0;c<a.length;c++)e.push(a[c]);a=e}else{"[object Array]"!==c&&(l=1);for(c=0;c<a.length&&!l;c++)"number"!=typeof a[c]&&(l=1)}if(!l){if(b===t)for(c=b=0;c<a.length;c++)for(e=a[c];0<e;)b++,e>>>=1;this.b[g].update([d,this.C++,2,b,f,a.length].concat(a))}break;case "string":b===t&&(b=a.length);this.b[g].update([d,this.C++,3,b,f,a.length]);this.b[g].update(a);
break;default:l=1}l&&q(new sjcl.exception.bug("random: addEntropy only supports number, array of numbers or string"));this.h[g]+=b;this.c+=b;h===this.l&&(this.isReady()!==this.l&&C("seeded",Math.max(this.i,this.c)),C("progress",this.getProgress()))},isReady:function(a){a=this.H[a!==t?a:this.B];return this.i&&this.i>=a?this.h[0]>this.P&&(new Date).valueOf()>this.N?this.w|this.u:this.u:this.c>=a?this.w|this.l:this.l},getProgress:function(a){a=this.H[a?a:this.B];return this.i>=a?1:this.c>a?1:this.c/
a},startCollectors:function(){this.p||(window.addEventListener?(window.addEventListener("load",this.r,u),window.addEventListener("mousemove",this.s,u)):document.attachEvent?(document.attachEvent("onload",this.r),document.attachEvent("onmousemove",this.s)):q(new sjcl.exception.bug("can't attach event")),this.p=!0)},stopCollectors:function(){this.p&&(window.removeEventListener?(window.removeEventListener("load",this.r,u),window.removeEventListener("mousemove",this.s,u)):window.detachEvent&&(window.detachEvent("onload",
this.r),window.detachEvent("onmousemove",this.s)),this.p=u)},addEventListener:function(a,b){this.z[a][this.S++]=b},removeEventListener:function(a,b){var c,d,e=this.z[a],f=[];for(d in e)e.hasOwnProperty(d)&&e[d]===b&&f.push(d);for(c=0;c<f.length;c++)d=f[c],delete e[d]},s:function(a){sjcl.random.addEntropy([a.x||a.clientX||a.offsetX||0,a.y||a.clientY||a.offsetY||0],2,"mouse")},r:function(){sjcl.random.addEntropy((new Date).valueOf(),2,"loadtime")}};
function C(a,b){var c,d=sjcl.random.z[a],e=[];for(c in d)d.hasOwnProperty(c)&&e.push(d[c]);for(c=0;c<e.length;c++)e[c](b)}function A(a){a.a=B(a).concat(B(a));a.A=new sjcl.cipher.aes(a.a)}function B(a){for(var b=0;4>b&&!(a.e[b]=a.e[b]+1|0,a.e[b]);b++);return a.A.encrypt(a.e)}sjcl.random=new sjcl.prng(6);try{var D=new Uint32Array(32);crypto.getRandomValues(D);sjcl.random.addEntropy(D,1024,"crypto['getRandomValues']")}catch(E){}
sjcl.json={defaults:{v:1,iter:1E3,ks:128,ts:64,mode:"ccm",adata:"",cipher:"aes"},encrypt:function(a,b,c,d){c=c||{};d=d||{};var e=sjcl.json,f=e.d({iv:sjcl.random.randomWords(4,0)},e.defaults),g;e.d(f,c);c=f.adata;"string"===typeof f.salt&&(f.salt=sjcl.codec.base64.toBits(f.salt));"string"===typeof f.iv&&(f.iv=sjcl.codec.base64.toBits(f.iv));(!sjcl.mode[f.mode]||!sjcl.cipher[f.cipher]||"string"===typeof a&&100>=f.iter||64!==f.ts&&96!==f.ts&&128!==f.ts||128!==f.ks&&192!==f.ks&&0x100!==f.ks||2>f.iv.length||
4<f.iv.length)&&q(new sjcl.exception.invalid("json encrypt: invalid parameters"));"string"===typeof a&&(g=sjcl.misc.cachedPbkdf2(a,f),a=g.key.slice(0,f.ks/32),f.salt=g.salt);"string"===typeof b&&(b=sjcl.codec.utf8String.toBits(b));"string"===typeof c&&(c=sjcl.codec.utf8String.toBits(c));g=new sjcl.cipher[f.cipher](a);e.d(d,f);d.key=a;f.ct=sjcl.mode[f.mode].encrypt(g,b,f.iv,c,f.ts);return e.encode(f)},decrypt:function(a,b,c,d){c=c||{};d=d||{};var e=sjcl.json;b=e.d(e.d(e.d({},e.defaults),e.decode(b)),
c,!0);var f;c=b.adata;"string"===typeof b.salt&&(b.salt=sjcl.codec.base64.toBits(b.salt));"string"===typeof b.iv&&(b.iv=sjcl.codec.base64.toBits(b.iv));(!sjcl.mode[b.mode]||!sjcl.cipher[b.cipher]||"string"===typeof a&&100>=b.iter||64!==b.ts&&96!==b.ts&&128!==b.ts||128!==b.ks&&192!==b.ks&&0x100!==b.ks||!b.iv||2>b.iv.length||4<b.iv.length)&&q(new sjcl.exception.invalid("json decrypt: invalid parameters"));"string"===typeof a&&(f=sjcl.misc.cachedPbkdf2(a,b),a=f.key.slice(0,b.ks/32),b.salt=f.salt);"string"===
typeof c&&(c=sjcl.codec.utf8String.toBits(c));f=new sjcl.cipher[b.cipher](a);c=sjcl.mode[b.mode].decrypt(f,b.ct,b.iv,c,b.ts);e.d(d,b);d.key=a;return sjcl.codec.utf8String.fromBits(c)},encode:function(a){var b,c="{",d="";for(b in a)if(a.hasOwnProperty(b))switch(b.match(/^[a-z0-9]+$/i)||q(new sjcl.exception.invalid("json encode: invalid property name")),c+=d+'"'+b+'":',d=",",typeof a[b]){case "number":case "boolean":c+=a[b];break;case "string":c+='"'+escape(a[b])+'"';break;case "object":c+='"'+sjcl.codec.base64.fromBits(a[b],
0)+'"';break;default:q(new sjcl.exception.bug("json encode: unsupported type"))}return c+"}"},decode:function(a){a=a.replace(/\s/g,"");a.match(/^\{.*\}$/)||q(new sjcl.exception.invalid("json decode: this isn't json!"));a=a.replace(/^\{|\}$/g,"").split(/,/);var b={},c,d;for(c=0;c<a.length;c++)(d=a[c].match(/^(?:(["']?)([a-z][a-z0-9]*)\l):(?:(\d+)|"([a-z0-9+\/%*_.@=\-]*)")$/i))||q(new sjcl.exception.invalid("json decode: this isn't json!")),b[d[2]]=d[3]?parseInt(d[3],10):d[2].match(/^(ct|salt|iv)$/)?
sjcl.codec.base64.toBits(d[4]):unescape(d[4]);return b},d:function(a,b,c){a===t&&(a={});if(b===t)return a;for(var d in b)b.hasOwnProperty(d)&&(c&&(a[d]!==t&&a[d]!==b[d])&&q(new sjcl.exception.invalid("required parameter overridden")),a[d]=b[d]);return a},X:function(a,b){var c={},d;for(d in a)a.hasOwnProperty(d)&&a[d]!==b[d]&&(c[d]=a[d]);return c},W:function(a,b){var c={},d;for(d=0;d<b.length;d++)a[b[d]]!==t&&(c[b[d]]=a[b[d]]);return c}};sjcl.encrypt=sjcl.json.encrypt;sjcl.decrypt=sjcl.json.decrypt;
sjcl.misc.V={};sjcl.misc.cachedPbkdf2=function(a,b){var c=sjcl.misc.V,d;b=b||{};d=b.iter||1E3;c=c[a]=c[a]||{};d=c[d]=c[d]||{firstSalt:b.salt&&b.salt.length?b.salt.slice(0):sjcl.random.randomWords(2,0)};c=b.salt===t?d.firstSalt:b.salt;d[c]=d[c]||sjcl.misc.pbkdf2(a,c,b.iter);return{key:d[c].slice(0),salt:c.slice(0)}};

// ####### Had to substitute \l for \\1 on third to last line above - perhaps have to escape all backslashes

/*  From sha1.js  */

var hexcase = 0;  /* hex output format. 0 - lowercase; 1 - uppercase        */
var b64pad  = ""; /* base-64 pad character. "=" for strict RFC compliance   */
var chrsz   = 8;  /* bits per input character. 8 - ASCII; 16 - Unicode      */

/*
 * These are the functions you'll usually want to call
 * They take string arguments and return either hex or base-64 encoded strings
 */
function hex_sha1(s){return binb2hex(core_sha1(str2binb(s),s.length * chrsz));}
function b64_sha1(s){return binb2b64(core_sha1(str2binb(s),s.length * chrsz));}
function str_sha1(s){return binb2str(core_sha1(str2binb(s),s.length * chrsz));}
function hex_hmac_sha1(key, data){ return binb2hex(core_hmac_sha1(key, data));}
function b64_hmac_sha1(key, data){ return binb2b64(core_hmac_sha1(key, data));}
function str_hmac_sha1(key, data){ return binb2str(core_hmac_sha1(key, data));}

/*
 * Perform a simple self-test to see if the VM is working
 */
function sha1_vm_test()
{
  return hex_sha1("abc") == "a9993e364706816aba3e25717850c26c9cd0d89d";
}

/*
 * Calculate the SHA-1 of an array of big-endian words, and a bit length
 */
function core_sha1(x, len)
{
  /* append padding */
  x[len >> 5] |= 0x80 << (24 - len % 32);
  x[((len + 64 >> 9) << 4) + 15] = len;

  var w = Array(80);
  var a =  1732584193;
  var b = -271733879;
  var c = -1732584194;
  var d =  271733878;
  var e = -1009589776;

  for(var i = 0; i < x.length; i += 16)
  {
    var olda = a;
    var oldb = b;
    var oldc = c;
    var oldd = d;
    var olde = e;

    for(var j = 0; j < 80; j++)
    {
      if(j < 16) w[j] = x[i + j];
      else w[j] = rol(w[j-3] ^ w[j-8] ^ w[j-14] ^ w[j-16], 1);
      var t = safe_add(safe_add(rol(a, 5), sha1_ft(j, b, c, d)),
                       safe_add(safe_add(e, w[j]), sha1_kt(j)));
      e = d;
      d = c;
      c = rol(b, 30);
      b = a;
      a = t;
    }

    a = safe_add(a, olda);
    b = safe_add(b, oldb);
    c = safe_add(c, oldc);
    d = safe_add(d, oldd);
    e = safe_add(e, olde);
  }
  return Array(a, b, c, d, e);

}

/*
 * Perform the appropriate triplet combination function for the current
 * iteration
 */
function sha1_ft(t, b, c, d)
{
  if(t < 20) return (b & c) | ((~b) & d);
  if(t < 40) return b ^ c ^ d;
  if(t < 60) return (b & c) | (b & d) | (c & d);
  return b ^ c ^ d;
}

/*
 * Determine the appropriate additive constant for the current iteration
 */
function sha1_kt(t)
{
  return (t < 20) ?  1518500249 : (t < 40) ?  1859775393 :
         (t < 60) ? -1894007588 : -899497514;
}

/*
 * Calculate the HMAC-SHA1 of a key and some data
 */
function core_hmac_sha1(key, data)
{
  var bkey = str2binb(key);
  if(bkey.length > 16) bkey = core_sha1(bkey, key.length * chrsz);

  var ipad = Array(16), opad = Array(16);
  for(var i = 0; i < 16; i++)
  {
    ipad[i] = bkey[i] ^ 0x36363636;
    opad[i] = bkey[i] ^ 0x5C5C5C5C;
  }

  var hash = core_sha1(ipad.concat(str2binb(data)), 512 + data.length * chrsz);
  return core_sha1(opad.concat(hash), 512 + 160);
}

/*
 * Add integers, wrapping at 2^32. This uses 16-bit operations internally
 * to work around bugs in some JS interpreters.
 */
function safe_add(x, y)
{
  var lsw = (x & 0xFFFF) + (y & 0xFFFF);
  var msw = (x >> 16) + (y >> 16) + (lsw >> 16);
  return (msw << 16) | (lsw & 0xFFFF);
}

/*
 * Bitwise rotate a 32-bit number to the left.
 */
function rol(num, cnt)
{
  return (num << cnt) | (num >>> (32 - cnt));
}

/*
 * Convert an 8-bit or 16-bit string to an array of big-endian words
 * In 8-bit function, characters >255 have their hi-byte silently ignored.
 */
function str2binb(str)
{
  var bin = Array();
  var mask = (1 << chrsz) - 1;
  for(var i = 0; i < str.length * chrsz; i += chrsz)
    bin[i>>5] |= (str.charCodeAt(i / chrsz) & mask) << (32 - chrsz - i%32);
  return bin;
}

/*
 * Convert an array of big-endian words to a string
 */
function binb2str(bin)
{
  var str = "";
  var mask = (1 << chrsz) - 1;
  for(var i = 0; i < bin.length * 32; i += chrsz)
    str += String.fromCharCode((bin[i>>5] >>> (32 - chrsz - i%32)) & mask);
  return str;
}

/*
 * Convert an array of big-endian words to a hex string.
 */
function binb2hex(binarray)
{
  var hex_tab = hexcase ? "0123456789ABCDEF" : "0123456789abcdef";
  var str = "";
  for(var i = 0; i < binarray.length * 4; i++)
  {
    str += hex_tab.charAt((binarray[i>>2] >> ((3 - i%4)*8+4)) & 0xF) +
           hex_tab.charAt((binarray[i>>2] >> ((3 - i%4)*8  )) & 0xF);
  }
  return str;
}

/*
 * Convert an array of big-endian words to a base-64 string
 */
function binb2b64(binarray)
{
  var tab = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  var str = "";
  for(var i = 0; i < binarray.length * 4; i += 3)
  {
    var triplet = (((binarray[i   >> 2] >> 8 * (3 -  i   %4)) & 0xFF) << 16)
                | (((binarray[i+1 >> 2] >> 8 * (3 - (i+1)%4)) & 0xFF) << 8 )
                |  ((binarray[i+2 >> 2] >> 8 * (3 - (i+2)%4)) & 0xFF);
    for(var j = 0; j < 4; j++)
    {
      if(i * 8 + j * 6 > binarray.length * 32) str += b64pad;
      else str += tab.charAt((triplet >> 6*(3-j)) & 0x3F);
    }
  }
  return str;
}

var chrsz   = 8;  /* bits per input character. 8 - ASCII; 16 - Unicode      */
var hexcase = 0;/* hex output format. 0 - lowercase; 1 - uppercase        */

function safe_add (x, y) {
  var lsw = (x & 0xFFFF) + (y & 0xFFFF);
  var msw = (x >> 16) + (y >> 16) + (lsw >> 16);
  return (msw << 16) | (lsw & 0xFFFF);
}

function S (X, n) {return ( X >>> n ) | (X << (32 - n));}

function R (X, n) {return ( X >>> n );}

function Ch(x, y, z) {return ((x & y) ^ ((~x) & z));}

function Maj(x, y, z) {return ((x & y) ^ (x & z) ^ (y & z));}

function Sigma0256(x) {return (S(x, 2) ^ S(x, 13) ^ S(x, 22));}

function Sigma1256(x) {return (S(x, 6) ^ S(x, 11) ^ S(x, 25));}

function Gamma0256(x) {return (S(x, 7) ^ S(x, 18) ^ R(x, 3));}

function Gamma1256(x) {return (S(x, 17) ^ S(x, 19) ^ R(x, 10));}

function Sigma0512(x) {return (S(x, 28) ^ S(x, 34) ^ S(x, 39));}

function Sigma1512(x) {return (S(x, 14) ^ S(x, 18) ^ S(x, 41));}

function Gamma0512(x) {return (S(x, 1) ^ S(x, 8) ^ R(x, 7));}

function Gamma1512(x) {return (S(x, 19) ^ S(x, 61) ^ R(x, 6));}

function core_sha256 (m, l) {
    var K = new Array(0x428A2F98,0x71374491,0xB5C0FBCF,0xE9B5DBA5,0x3956C25B,0x59F111F1,0x923F82A4,0xAB1C5ED5,0xD807AA98,0x12835B01,0x243185BE,0x550C7DC3,0x72BE5D74,0x80DEB1FE,0x9BDC06A7,0xC19BF174,0xE49B69C1,0xEFBE4786,0xFC19DC6,0x240CA1CC,0x2DE92C6F,0x4A7484AA,0x5CB0A9DC,0x76F988DA,0x983E5152,0xA831C66D,0xB00327C8,0xBF597FC7,0xC6E00BF3,0xD5A79147,0x6CA6351,0x14292967,0x27B70A85,0x2E1B2138,0x4D2C6DFC,0x53380D13,0x650A7354,0x766A0ABB,0x81C2C92E,0x92722C85,0xA2BFE8A1,0xA81A664B,0xC24B8B70,0xC76C51A3,0xD192E819,0xD6990624,0xF40E3585,0x106AA070,0x19A4C116,0x1E376C08,0x2748774C,0x34B0BCB5,0x391C0CB3,0x4ED8AA4A,0x5B9CCA4F,0x682E6FF3,0x748F82EE,0x78A5636F,0x84C87814,0x8CC70208,0x90BEFFFA,0xA4506CEB,0xBEF9A3F7,0xC67178F2);
    var HASH = new Array(0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19);
    var W = new Array(64);
    var a, b, c, d, e, f, g, h, i, j;
    var T1, T2;

    /* append padding */
    m[l >> 5] |= 0x80 << (24 - l % 32);
    m[((l + 64 >> 9) << 4) + 15] = l;

    for ( var i = 0; i<m.length; i+=16 ) {
        a = HASH[0];
        b = HASH[1];
        c = HASH[2];
        d = HASH[3];
        e = HASH[4];
        f = HASH[5];
        g = HASH[6];
        h = HASH[7];

        for ( var j = 0; j<64; j++) {
            if (j < 16) W[j] = m[j + i];
            else W[j] = safe_add(safe_add(safe_add(Gamma1256(W[j - 2]), W[j - 7]), Gamma0256(W[j - 15])), W[j - 16]);

            T1 = safe_add(safe_add(safe_add(safe_add(h, Sigma1256(e)), Ch(e, f, g)), K[j]), W[j]);
            T2 = safe_add(Sigma0256(a), Maj(a, b, c));

            h = g;
            g = f;
            f = e;
            e = safe_add(d, T1);
            d = c;
            c = b;
            b = a;
            a = safe_add(T1, T2);
        }
        
        HASH[0] = safe_add(a, HASH[0]);
        HASH[1] = safe_add(b, HASH[1]);
        HASH[2] = safe_add(c, HASH[2]);
        HASH[3] = safe_add(d, HASH[3]);
        HASH[4] = safe_add(e, HASH[4]);
        HASH[5] = safe_add(f, HASH[5]);
        HASH[6] = safe_add(g, HASH[6]);
        HASH[7] = safe_add(h, HASH[7]);
    }
    return HASH;
}

function core_sha512 (m, l) {
    var K = new Array(0x428a2f98d728ae22, 0x7137449123ef65cd, 0xb5c0fbcfec4d3b2f, 0xe9b5dba58189dbbc, 0x3956c25bf348b538, 0x59f111f1b605d019, 0x923f82a4af194f9b, 0xab1c5ed5da6d8118, 0xd807aa98a3030242, 0x12835b0145706fbe, 0x243185be4ee4b28c, 0x550c7dc3d5ffb4e2, 0x72be5d74f27b896f, 0x80deb1fe3b1696b1, 0x9bdc06a725c71235, 0xc19bf174cf692694, 0xe49b69c19ef14ad2, 0xefbe4786384f25e3, 0x0fc19dc68b8cd5b5, 0x240ca1cc77ac9c65, 0x2de92c6f592b0275, 0x4a7484aa6ea6e483, 0x5cb0a9dcbd41fbd4, 0x76f988da831153b5, 0x983e5152ee66dfab, 0xa831c66d2db43210, 0xb00327c898fb213f, 0xbf597fc7beef0ee4, 0xc6e00bf33da88fc2, 0xd5a79147930aa725, 0x06ca6351e003826f, 0x142929670a0e6e70, 0x27b70a8546d22ffc, 0x2e1b21385c26c926, 0x4d2c6dfc5ac42aed, 0x53380d139d95b3df, 0x650a73548baf63de, 0x766a0abb3c77b2a8, 0x81c2c92e47edaee6, 0x92722c851482353b, 0xa2bfe8a14cf10364, 0xa81a664bbc423001, 0xc24b8b70d0f89791, 0xc76c51a30654be30, 0xd192e819d6ef5218, 0xd69906245565a910, 0xf40e35855771202a, 0x106aa07032bbd1b8, 0x19a4c116b8d2d0c8, 0x1e376c085141ab53, 0x2748774cdf8eeb99, 0x34b0bcb5e19b48a8, 0x391c0cb3c5c95a63, 0x4ed8aa4ae3418acb, 0x5b9cca4f7763e373, 0x682e6ff3d6b2b8a3, 0x748f82ee5defb2fc, 0x78a5636f43172f60, 0x84c87814a1f0ab72, 0x8cc702081a6439ec, 0x90befffa23631e28, 0xa4506cebde82bde9, 0xbef9a3f7b2c67915, 0xc67178f2e372532b, 0xca273eceea26619c, 0xd186b8c721c0c207, 0xeada7dd6cde0eb1e, 0xf57d4f7fee6ed178, 0x06f067aa72176fba, 0x0a637dc5a2c898a6, 0x113f9804bef90dae, 0x1b710b35131c471b, 0x28db77f523047d84, 0x32caab7b40c72493, 0x3c9ebe0a15c9bebc, 0x431d67c49c100d4c, 0x4cc5d4becb3e42b6, 0x597f299cfc657e2a, 0x5fcb6fab3ad6faec, 0x6c44198c4a475817);
    var HASH = new Array(0x6a09e667f3bcc908, 0xbb67ae8584caa73b, 0x3c6ef372fe94f82b, 0xa54ff53a5f1d36f1, 0x510e527fade682d1, 0x9b05688c2b3e6c1f, 0x1f83d9abfb41bd6b, 0x5be0cd19137e2179);
    var W = new Array(80);
    var a, b, c, d, e, f, g, h, i, j;
    var T1, T2;

}

function str2binb (str) {
  var bin = Array();
  var mask = (1 << chrsz) - 1;
  for(var i = 0; i < str.length * chrsz; i += chrsz)
    bin[i>>5] |= (str.charCodeAt(i / chrsz) & mask) << (24 - i%32);
  return bin;
}

function binb2str (bin) {
  var str = "";
  var mask = (1 << chrsz) - 1;
  for(var i = 0; i < bin.length * 32; i += chrsz)
    str += String.fromCharCode((bin[i>>5] >>> (24 - i%32)) & mask);
  return str;
}

function binb2hex (binarray) {
  var hex_tab = hexcase ? "0123456789ABCDEF" : "0123456789abcdef";
  var str = "";
  for(var i = 0; i < binarray.length * 4; i++)
  {
    str += hex_tab.charAt((binarray[i>>2] >> ((3 - i%4)*8+4)) & 0xF) +
           hex_tab.charAt((binarray[i>>2] >> ((3 - i%4)*8  )) & 0xF);
  }
  return str;
}

function binb2b64 (binarray) {
  var tab = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  var str = "";
  for(var i = 0; i < binarray.length * 4; i += 3)
  {
    var triplet = (((binarray[i   >> 2] >> 8 * (3 -  i   %4)) & 0xFF) << 16)
                | (((binarray[i+1 >> 2] >> 8 * (3 - (i+1)%4)) & 0xFF) << 8 )
                |  ((binarray[i+2 >> 2] >> 8 * (3 - (i+2)%4)) & 0xFF);
    for(var j = 0; j < 4; j++)
    {
      if(i * 8 + j * 6 > binarray.length * 32) str += b64pad;
      else str += tab.charAt((triplet >> 6*(3-j)) & 0x3F);
    }
  }
  return str;
}

/*  From sha2.js*/

var chrsz   = 8;  /* bits per input character. 8 - ASCII; 16 - Unicode      */
var hexcase = 0;/* hex output format. 0 - lowercase; 1 - uppercase        */

function safe_add (x, y) {
  var lsw = (x & 0xFFFF) + (y & 0xFFFF);
  var msw = (x >> 16) + (y >> 16) + (lsw >> 16);
  return (msw << 16) | (lsw & 0xFFFF);
}

function S (X, n) {return ( X >>> n ) | (X << (32 - n));}

function R (X, n) {return ( X >>> n );}

function Ch(x, y, z) {return ((x & y) ^ ((~x) & z));}

function Maj(x, y, z) {return ((x & y) ^ (x & z) ^ (y & z));}

function Sigma0256(x) {return (S(x, 2) ^ S(x, 13) ^ S(x, 22));}

function Sigma1256(x) {return (S(x, 6) ^ S(x, 11) ^ S(x, 25));}

function Gamma0256(x) {return (S(x, 7) ^ S(x, 18) ^ R(x, 3));}

function Gamma1256(x) {return (S(x, 17) ^ S(x, 19) ^ R(x, 10));}

function Sigma0512(x) {return (S(x, 28) ^ S(x, 34) ^ S(x, 39));}

function Sigma1512(x) {return (S(x, 14) ^ S(x, 18) ^ S(x, 41));}

function Gamma0512(x) {return (S(x, 1) ^ S(x, 8) ^ R(x, 7));}

function Gamma1512(x) {return (S(x, 19) ^ S(x, 61) ^ R(x, 6));}

function core_sha256 (m, l) {
    var K = new Array(0x428A2F98,0x71374491,0xB5C0FBCF,0xE9B5DBA5,0x3956C25B,0x59F111F1,0x923F82A4,0xAB1C5ED5,0xD807AA98,0x12835B01,0x243185BE,0x550C7DC3,0x72BE5D74,0x80DEB1FE,0x9BDC06A7,0xC19BF174,0xE49B69C1,0xEFBE4786,0xFC19DC6,0x240CA1CC,0x2DE92C6F,0x4A7484AA,0x5CB0A9DC,0x76F988DA,0x983E5152,0xA831C66D,0xB00327C8,0xBF597FC7,0xC6E00BF3,0xD5A79147,0x6CA6351,0x14292967,0x27B70A85,0x2E1B2138,0x4D2C6DFC,0x53380D13,0x650A7354,0x766A0ABB,0x81C2C92E,0x92722C85,0xA2BFE8A1,0xA81A664B,0xC24B8B70,0xC76C51A3,0xD192E819,0xD6990624,0xF40E3585,0x106AA070,0x19A4C116,0x1E376C08,0x2748774C,0x34B0BCB5,0x391C0CB3,0x4ED8AA4A,0x5B9CCA4F,0x682E6FF3,0x748F82EE,0x78A5636F,0x84C87814,0x8CC70208,0x90BEFFFA,0xA4506CEB,0xBEF9A3F7,0xC67178F2);
    var HASH = new Array(0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19);
    var W = new Array(64);
    var a, b, c, d, e, f, g, h, i, j;
    var T1, T2;

    /* append padding */
    m[l >> 5] |= 0x80 << (24 - l % 32);
    m[((l + 64 >> 9) << 4) + 15] = l;

    for ( var i = 0; i<m.length; i+=16 ) {
        a = HASH[0];
        b = HASH[1];
        c = HASH[2];
        d = HASH[3];
        e = HASH[4];
        f = HASH[5];
        g = HASH[6];
        h = HASH[7];

        for ( var j = 0; j<64; j++) {
            if (j < 16) W[j] = m[j + i];
            else W[j] = safe_add(safe_add(safe_add(Gamma1256(W[j - 2]), W[j - 7]), Gamma0256(W[j - 15])), W[j - 16]);

            T1 = safe_add(safe_add(safe_add(safe_add(h, Sigma1256(e)), Ch(e, f, g)), K[j]), W[j]);
            T2 = safe_add(Sigma0256(a), Maj(a, b, c));

            h = g;
            g = f;
            f = e;
            e = safe_add(d, T1);
            d = c;
            c = b;
            b = a;
            a = safe_add(T1, T2);
        }
        
        HASH[0] = safe_add(a, HASH[0]);
        HASH[1] = safe_add(b, HASH[1]);
        HASH[2] = safe_add(c, HASH[2]);
        HASH[3] = safe_add(d, HASH[3]);
        HASH[4] = safe_add(e, HASH[4]);
        HASH[5] = safe_add(f, HASH[5]);
        HASH[6] = safe_add(g, HASH[6]);
        HASH[7] = safe_add(h, HASH[7]);
    }
    return HASH;
}

function core_sha512 (m, l) {
    var K = new Array(0x428a2f98d728ae22, 0x7137449123ef65cd, 0xb5c0fbcfec4d3b2f, 0xe9b5dba58189dbbc, 0x3956c25bf348b538, 0x59f111f1b605d019, 0x923f82a4af194f9b, 0xab1c5ed5da6d8118, 0xd807aa98a3030242, 0x12835b0145706fbe, 0x243185be4ee4b28c, 0x550c7dc3d5ffb4e2, 0x72be5d74f27b896f, 0x80deb1fe3b1696b1, 0x9bdc06a725c71235, 0xc19bf174cf692694, 0xe49b69c19ef14ad2, 0xefbe4786384f25e3, 0x0fc19dc68b8cd5b5, 0x240ca1cc77ac9c65, 0x2de92c6f592b0275, 0x4a7484aa6ea6e483, 0x5cb0a9dcbd41fbd4, 0x76f988da831153b5, 0x983e5152ee66dfab, 0xa831c66d2db43210, 0xb00327c898fb213f, 0xbf597fc7beef0ee4, 0xc6e00bf33da88fc2, 0xd5a79147930aa725, 0x06ca6351e003826f, 0x142929670a0e6e70, 0x27b70a8546d22ffc, 0x2e1b21385c26c926, 0x4d2c6dfc5ac42aed, 0x53380d139d95b3df, 0x650a73548baf63de, 0x766a0abb3c77b2a8, 0x81c2c92e47edaee6, 0x92722c851482353b, 0xa2bfe8a14cf10364, 0xa81a664bbc423001, 0xc24b8b70d0f89791, 0xc76c51a30654be30, 0xd192e819d6ef5218, 0xd69906245565a910, 0xf40e35855771202a, 0x106aa07032bbd1b8, 0x19a4c116b8d2d0c8, 0x1e376c085141ab53, 0x2748774cdf8eeb99, 0x34b0bcb5e19b48a8, 0x391c0cb3c5c95a63, 0x4ed8aa4ae3418acb, 0x5b9cca4f7763e373, 0x682e6ff3d6b2b8a3, 0x748f82ee5defb2fc, 0x78a5636f43172f60, 0x84c87814a1f0ab72, 0x8cc702081a6439ec, 0x90befffa23631e28, 0xa4506cebde82bde9, 0xbef9a3f7b2c67915, 0xc67178f2e372532b, 0xca273eceea26619c, 0xd186b8c721c0c207, 0xeada7dd6cde0eb1e, 0xf57d4f7fee6ed178, 0x06f067aa72176fba, 0x0a637dc5a2c898a6, 0x113f9804bef90dae, 0x1b710b35131c471b, 0x28db77f523047d84, 0x32caab7b40c72493, 0x3c9ebe0a15c9bebc, 0x431d67c49c100d4c, 0x4cc5d4becb3e42b6, 0x597f299cfc657e2a, 0x5fcb6fab3ad6faec, 0x6c44198c4a475817);
    var HASH = new Array(0x6a09e667f3bcc908, 0xbb67ae8584caa73b, 0x3c6ef372fe94f82b, 0xa54ff53a5f1d36f1, 0x510e527fade682d1, 0x9b05688c2b3e6c1f, 0x1f83d9abfb41bd6b, 0x5be0cd19137e2179);
    var W = new Array(80);
    var a, b, c, d, e, f, g, h, i, j;
    var T1, T2;

}

function str2binb (str) {
  var bin = Array();
  var mask = (1 << chrsz) - 1;
  for(var i = 0; i < str.length * chrsz; i += chrsz)
    bin[i>>5] |= (str.charCodeAt(i / chrsz) & mask) << (24 - i%32);
  return bin;
}

function binb2str (bin) {
  var str = "";
  var mask = (1 << chrsz) - 1;
  for(var i = 0; i < bin.length * 32; i += chrsz)
    str += String.fromCharCode((bin[i>>5] >>> (24 - i%32)) & mask);
  return str;
}

function binb2hex (binarray) {
  var hex_tab = hexcase ? "0123456789ABCDEF" : "0123456789abcdef";
  var str = "";
  for(var i = 0; i < binarray.length * 4; i++)
  {
    str += hex_tab.charAt((binarray[i>>2] >> ((3 - i%4)*8+4)) & 0xF) +
           hex_tab.charAt((binarray[i>>2] >> ((3 - i%4)*8  )) & 0xF);
  }
  return str;
}

function binb2b64 (binarray) {
  var tab = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  var str = "";
  for(var i = 0; i < binarray.length * 4; i += 3)
  {
    var triplet = (((binarray[i   >> 2] >> 8 * (3 -  i   %4)) & 0xFF) << 16)
                | (((binarray[i+1 >> 2] >> 8 * (3 - (i+1)%4)) & 0xFF) << 8 )
                |  ((binarray[i+2 >> 2] >> 8 * (3 - (i+2)%4)) & 0xFF);
    for(var j = 0; j < 4; j++)
    {
      if(i * 8 + j * 6 > binarray.length * 32) str += b64pad;
      else str += tab.charAt((triplet >> 6*(3-j)) & 0x3F);
    }
  }
  return str;
}

function hex_sha256(s){return binb2hex(core_sha256(str2binb(s),s.length * chrsz));}
function b64_sha256(s){return binb2b64(core_sha256(str2binb(s),s.length * chrsz));}
function str_sha256(s){return binb2str(core_sha256(str2binb(s),s.length * chrsz));}



`

