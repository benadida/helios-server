
/*
 * Random Number generation, now uses the glue to Java
 */

Random = {};

Random.GENERATOR = null;

Random.setupGenerator = function() {
    if (Random.GENERATOR == null) {
	    if (BigInt.use_applet) {
	      var foo = BigInt.APPLET.newSecureRandom();
	      Random.GENERATOR = BigInt.APPLET.newSecureRandom();
	    } else {
	      // we do it twice because of some weird bug;
	      var foo = new java.security.SecureRandom();
	      Random.GENERATOR = new java.security.SecureRandom();
	    }
    }
};

Random.getRandomInteger = function(max) {
  Random.setupGenerator();
  var bit_length = max.bitLength();
  var random;
  if (BigInt.use_applet) {
      random = BigInt.APPLET.randomBigInteger(bit_length, Random.GENERATOR);
  } else {
      random = new java.math.BigInteger(bit_length, Random.GENERATOR);
  }
  
  return BigInt._from_java_object(random).mod(max);
};

Random.getRandomPrime = function(n_bits) {
  Random.setupGenerator();
  var certainty = 80;
  var prime;
  if (BigInt.use_applet) {
      prime = BigInt.APPLET.randomPrimeBigInteger(n_bits, certainty, Random.GENERATOR);
  } else {
      prime = new java.math.BigInteger(n_bits, certainty, Random.GENERATOR);
  }
  
  return BigInt._from_java_object(prime);
};

