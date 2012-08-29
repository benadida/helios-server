
/*
 * A simple applet for generating Bigints from JavaScript
 *
 * inspired from Stanford's SRP, and extended for Prime Number generation.
 */

public class bigint extends java.applet.Applet {
    public java.security.SecureRandom newSecureRandom() {
	    return new java.security.SecureRandom();
    }

    public java.math.BigInteger newBigInteger(String value, int radix) {
	    return new java.math.BigInteger(value, radix);
    }

    public java.math.BigInteger randomBigInteger(int bitlen, java.util.Random rng) {
	    return new java.math.BigInteger(bitlen, rng);
    }

    public java.math.BigInteger randomPrimeBigInteger(int bitlen, int certainty, java.util.Random rng) {
	    return new java.math.BigInteger(bitlen, certainty, rng);
    }
}
 
