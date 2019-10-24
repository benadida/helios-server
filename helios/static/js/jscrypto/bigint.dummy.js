/*
 * A dummy version of bigint for Helios
 * 
 * no math is done in JavaScript, but the BigInt abstraction exists so that 
 * higher-level data structures can be parsed/serialized appropriately.
 */

// A wrapper for java.math.BigInteger with some appropriate extra functions for JSON and 
// generally being a nice JavaScript object.

BigInt = Class.extend({
	init: function(value, radix) {
	    if (radix != 10)
		throw "in dummy, only radix=10, here radix=" + radix;
	    
	    this.value = value;
	},
  
	toString: function() {
	    return this.value;
	},
  
	toJSONObject: function() {
	    // toString is apparently not overridden in IE, so we reproduce it here.
	    return this.value;
	},
  
	add: function(other) {
	    throw "dummy, no add!";
	},
  
	bitLength: function() {
	    throw "dummy, nobitlength!";
	},
  
	mod: function(modulus) {
	    throw "dummy, no mod!";
	},
  
	equals: function(other) {
	    throw "dummy, no equals!";
	},
  
	modPow: function(exp, modulus) {
	    throw "dummy, no modpow!";
	},
	
	negate: function() {
	    throw "dummy, no negate!";
	},
  
	multiply: function(other) {
	    throw "dummy, no multiply!";
	},
  
	modInverse: function(modulus) {
	    throw "dummy, no modInverse";
	}
  
});

BigInt.ready_p = false;

BigInt.use_applet = false;

BigInt.is_dummy = true;

BigInt.fromJSONObject = function(s) {
  return new BigInt(s, 10);
};

BigInt.fromInt = function(i) {
  return BigInt.fromJSONObject("" + i);
};

// Set up the pointer to the applet if necessary, and some
// basic Big Ints that everyone needs (0, 1, 2, and 42)
BigInt._setup = function() {
  try {
    BigInt.ZERO = new BigInt("0",10);
    BigInt.ONE = new BigInt("1",10);
    BigInt.TWO = new BigInt("2",10);
    BigInt.FORTY_TWO = new BigInt("42",10);
  
    BigInt.ready_p = true;
  } catch (e) {
    // not ready
    // count how many times we've tried
    if (this.num_invocations == null)
      this.num_invocations = 0;

    this.num_invocations += 1;

    if (this.num_invocations > 5) {
      if (BigInt.setup_interval)
        window.clearInterval(BigInt.setup_interval);
      
      if (BigInt.setup_fail) {
        BigInt.setup_fail();
      } else {
        alert('bigint failed!');
      }
    }
    return;
  }
  
  if (BigInt.setup_interval)
    window.clearInterval(BigInt.setup_interval);
    
  if (BigInt.setup_callback)
    BigInt.setup_callback();
};

BigInt.setup = function(callback, fail_callback) {
  if (callback)
    BigInt.setup_callback = callback;
  
  if (fail_callback)
    BigInt.setup_fail = fail_callback;
  
  BigInt.setup_interval = window.setInterval("BigInt._setup()", 1000);
}

// .onload instead of .ready, as I don't think the applet is ready until onload.
// FIXME: something wrong here in the first load
$(document).ready(function() {
	BigInt.use_applet = false;
});

