# Helios Frontend Randomness Generation Analysis

## Executive Summary

The Helios voting booth uses **Stanford JavaScript Crypto Library (SJCL)** for generating cryptographic randomness to seed ElGamal encryption. The system employs a multi-source entropy collection approach combining browser APIs, server-provided randomness, and user interaction events.

## Architecture Overview

### Primary Components

1. **SJCL PRNG** (`heliosbooth/js/jscrypto/sjcl.js`)
   - Main pseudo-random number generator
   - Based on Fortuna PRNG design
   - Uses AES-256 in counter mode

2. **Random Module** (`heliosbooth/js/jscrypto/random.js`)
   - Wrapper interface for randomness generation
   - Provides `Random.getRandomInteger(max)` function
   - Calls SJCL under the hood

3. **ElGamal Encryption** (`heliosbooth/js/jscrypto/elgamal.js`)
   - Uses randomness for encryption operations
   - Line 487: `r = Random.getRandomInteger(pk.q)` when no randomness provided

## Entropy Sources

### 1. Browser Crypto API (Primary Source)
**Location:** `heliosbooth/js/jscrypto/sjcl.js:40`

```javascript
try {
  var D = new Uint32Array(32);
  crypto.getRandomValues(D);
  sjcl.random.addEntropy(D, 1024, "crypto['getRandomValues']");
} catch(E) {}
```

- **Method:** `crypto.getRandomValues()` - Standard Web Crypto API
- **Entropy:** 1024 bits (32 × 32-bit words)
- **Quality:** High - uses OS-level CSPRNG (Cryptographically Secure PRNG)
- **Availability:** Modern browsers (Chrome, Firefox, Safari, Edge)
- **Fallback:** If unavailable, relies on other sources

### 2. Server-Provided Randomness
**Location:** `heliosbooth/vote.html:387-392`

```javascript
if (USE_SJCL) {
  // get more randomness from server
  $.get(election_url + "/get-randomness", {}, function(raw_json) {
    sjcl.random.addEntropy(JSON.parse(raw_json).randomness);
  });
}
```

**Server Implementation:** `helios/views.py:630-636`

```python
@election_view()
@return_json
def get_randomness(request, election):
  """
  get some randomness to sprinkle into the sjcl entropy pool
  """
  return {
    "randomness": base64.b64encode(os.urandom(32)).decode('utf-8')
  }
```

- **Method:** Server generates 32 bytes via `os.urandom()`
- **Entropy:** 256 bits
- **Quality:** High - OS-level CSPRNG
- **Purpose:** Additional entropy mixing
- **Timing:** Fetched when election booth loads

### 3. User Interaction Events (Event Collectors)
**Location:** `heliosbooth/vote.html:434` and `426`

```javascript
sjcl.random.startCollectors();
```

**SJCL Implementation:** Collects entropy from:

a) **Mouse Movement**
```javascript
s: function(a) {
  sjcl.random.addEntropy([
    a.x || a.clientX || a.offsetX || 0,
    a.y || a.clientY || a.offsetY || 0
  ], 2, "mouse")
}
```
- Captures X/Y coordinates of mouse movements
- Entropy estimate: 2 bits per event
- Continuously collected during booth session

b) **Page Load Timing**
```javascript
r: function() {
  sjcl.random.addEntropy((new Date).valueOf(), 2, "loadtime")
}
```
- Captures timestamp at page load
- Entropy estimate: 2 bits
- One-time collection

### 4. Answer Shuffle Randomness
**Location:** `heliosbooth/vote.html:276`

```javascript
randomIndex = Math.floor(Math.random() * currentIndex);
```

- **Purpose:** Shuffling candidate order (if enabled)
- **Source:** JavaScript's `Math.random()`
- **Note:** NOT used for cryptographic operations
- **Security Impact:** Low - only affects display order

## Randomness Flow

### Initialization Sequence

1. **Document Ready** (`vote.html:432-441`)
   ```
   1. Set USE_SJCL = true
   2. Call sjcl.random.startCollectors()
      - Attach mouse movement listener
      - Attach load timing collector
   3. SJCL auto-initialization seeds from crypto.getRandomValues()
   4. Server randomness fetched via AJAX
   ```

2. **Encryption Time** (`helios.js:273`)
   ```
   randomness[i] = Random.getRandomInteger(pk.q)
     ↓
   sjcl.random.randomWords(Math.ceil(bit_length / 32) + 2, 6)
     ↓
   SJCL Fortuna PRNG generates output
   ```

### Random Integer Generation
**Location:** `heliosbooth/js/jscrypto/random.js:25-33`

```javascript
Random.getRandomInteger = function(max) {
  var bit_length = max.bitLength();
  Random.setupGenerator();
  var random;
  // Generate random words with paranoia level 6
  random = sjcl.random.randomWords(Math.ceil(bit_length / 32) + 2, 6);
  // Convert bit array to hex, then to BigInt
  var rand_bi = new BigInt(sjcl.codec.hex.fromBits(random), 16);
  return rand_bi.mod(max);
};
```

- **Paranoia Level:** 6 (second parameter to `randomWords`)
- **SJCL Paranoia Levels:**
  - 0: No requirement (use what's available)
  - 6: High paranoia (requires more entropy in pool)
- **Modular Reduction:** Uses modulo to fit range (potential bias for small ranges)

## Security Considerations

### Strengths

✅ **Multiple Entropy Sources:** Defense in depth approach
✅ **Crypto API Priority:** Uses browser's CSPRNG as primary source
✅ **Server Mixing:** Additional entropy from server's OS CSPRNG
✅ **High Paranoia Level:** SJCL configured with paranoia=6
✅ **AES-256 Based:** SJCL uses strong cipher for output generation

### Potential Concerns

⚠️ **Modular Bias:**
- `rand_bi.mod(max)` can introduce bias if `max` doesn't divide evenly into 2^n
- Impact: Minimal for large primes (ElGamal q parameter)
- Mitigation: ElGamal q is typically very large (~256 bits)

⚠️ **Mouse Entropy Quality:**
- Mouse movements assigned only 2 bits entropy per event
- Low entropy density compared to hardware RNG
- Impact: Minimal - supplementary source only

⚠️ **Network Timing:**
- Server randomness fetched asynchronously
- May not be available before first encryption
- Mitigation: crypto.getRandomValues() provides strong seed immediately

⚠️ **Fallback Behavior:**
- If crypto.getRandomValues() fails, relies on weaker sources
- No explicit warning to user
- Impact: Unlikely in modern browsers

### Recommendations

1. **Verify Entropy Level:**
   - Add check for SJCL entropy pool readiness before encryption
   - Display warning if insufficient entropy collected

2. **Timing Attack Prevention:**
   - Ensure server randomness is fetched before allowing encryption
   - Add explicit wait or check in encryption flow

3. **Modular Bias Mitigation:**
   - Consider rejection sampling for small moduli
   - For ElGamal parameters, current approach is acceptable

4. **Browser Compatibility:**
   - Add explicit check for crypto.getRandomValues()
   - Warn users on old browsers lacking secure RNG

## Code References

| Component | File | Lines |
|-----------|------|-------|
| SJCL Library | `heliosbooth/js/jscrypto/sjcl.js` | All |
| Random Module | `heliosbooth/js/jscrypto/random.js` | 25-33 |
| ElGamal Encrypt | `heliosbooth/js/jscrypto/elgamal.js` | 482-493 |
| Booth Initialization | `heliosbooth/vote.html` | 387-392, 426-441 |
| Encrypted Answer | `heliosbooth/js/jscrypto/helios.js` | 271-276 |
| Server Endpoint | `helios/views.py` | 630-636 |

## Conclusion

The Helios frontend employs a **robust multi-source entropy collection strategy** for seeding cryptographic operations. The primary reliance on `crypto.getRandomValues()` provides strong security guarantees in modern browsers, while server-provided randomness and user interaction events offer additional entropy mixing.

The system is **cryptographically sound** for its intended purpose, with the main security relying on the browser's Web Crypto API implementation and the SJCL Fortuna PRNG design.
