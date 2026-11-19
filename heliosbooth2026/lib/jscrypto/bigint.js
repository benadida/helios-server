/*
 * This software incorporates components derived from the
 * Secure Remote Password JavaScript demo developed by
 * Tom Wu (tjw@CS.Stanford.EDU).
 *
 * This library is almost entirely re-written by Ben Adida (ben@adida.net)
 * with a BigInt wrapper.
 *
 * IMPORTANT: this library REQUIRES that a variable JSCRYPTO_HOME be set by an HTML file, indicating
 * the complete path to the current directory
 */

// A wrapper for java.math.BigInteger with some appropriate extra functions for JSON and 
// generally being a nice JavaScript object.

// let's try always using SJCL
var USE_SJCL = true;

// let's make this much cleaner
if (USE_SJCL) {
    // why not?
    var BigInt = BigInteger;
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
    BigInt = Class.extend({
	    init: function(value, radix) {
		if (value == null) {
		    throw "null value!";
		}
		
		if (USE_SJCL) {
		    this._java_bigint = new BigInteger(value, radix);
		} else if (BigInt.use_applet) {
		    this._java_bigint = BigInt.APPLET.newBigInteger(value, radix);
		} else {
		    try {
			this._java_bigint = new java.math.BigInteger(value, radix);
		    } catch (e) {
			// alert("oy " + e.toString() + " value=" + value + " , radix=" + radix);
			throw TypeError
		    }
		}
	    },
	    
	    toString: function() {
		return this._java_bigint.toString() + "";
	    },
	    
	    toJSONObject: function() {
		return this.toString();
	    },
	    
	    add: function(other) {
		return BigInt._from_java_object(this._java_bigint.add(other._java_bigint));
	    },
	    
	    bitLength: function() {
		return this._java_bigint.bitLength();
	    },
	    
	    mod: function(modulus) {
		return BigInt._from_java_object(this._java_bigint.mod(modulus._java_bigint));
	    },
	    
	    equals: function(other) {
		return this._java_bigint.equals(other._java_bigint);
	    },
	    
	    modPow: function(exp, modulus) {
		return BigInt._from_java_object(this._java_bigint.modPow(exp._java_bigint, modulus._java_bigint));
	    },
	    
	    negate: function() {
		return BigInt._from_java_object(this._java_bigint.negate());
	    },
	    
	    multiply: function(other) {
		return BigInt._from_java_object(this._java_bigint.multiply(other._java_bigint));
	    },
	    
	    modInverse: function(modulus) {
		return BigInt._from_java_object(this._java_bigint.modInverse(modulus._java_bigint));
	    }
	    
	});
    
    BigInt.ready_p = false;

    //
    // Some Class Methods
    //
    BigInt._from_java_object = function(jo) {
	// bogus object
	var obj = new BigInt("0",10);
	obj._java_bigint = jo;
	return obj;
    };

    //
    // do the applet check
    //
    function check_applet() {
	/* Is this Netscape 4.xx? */
	var is_ns4 = (navigator.appName == "Netscape" && navigator.appVersion < "5");
	
	/* Do we need the toString() workaround (requires applet)? */
	var str_workaround = (navigator.appName == "Opera");
	
	// stuff this in BigInt
	BigInt.is_ie = (navigator.appName == "Microsoft Internet Explorer");
	
	/* Decide whether we need the helper applet or not */
	var use_applet = BigInt.is_ie || (!is_ns4 && navigator.platform.substr(0, 5) == "Linux") || str_workaround || typeof(java) == 'undefined';
	
	// add the applet
	if (use_applet) {
	    var applet_base = JSCRYPTO_HOME;
	    
	    var applet_html = '<applet codebase="' + applet_base + '" mayscript name="bigint" code="bigint.class" width=1 height=1 id="bigint_applet"></applet>';
	    // var applet_html = '<object classid="clsid:8AD9C840-044E-11D1-B3E9-00805F499D93" name="bigint" width="1" height="1" codebase="http://java.sun.com/products/plugin/autodl/jinstall-1_5_0-windows-i586.cab#Version=1,5,0,0"> <param name="code" value="bigint.class"> <param name="codebase" value="' + applet_base + '"> <param name="archive" value="myapplet.jar"> <param name="type" value="application/x-java-applet;version=1.5.0"> <param name="scriptable" value="true"> <param name="mayscript" value="false"> <comment> <embed code="bigint.class" name="bigint" java_codebase="' + applet_base + '" width="1" height="1" scriptable="true" mayscript="false" type="application/x-java-applet;version=1.5.0" pluginspage="http://java.sun.com/j2se/1.5.0/download.html"> <noembed>No Java Support.</noembed> </embed> </comment> </object>';
	    $("#applet_div").html(applet_html);
	}
	
	return use_applet;
    };
    
    // Set up the pointer to the applet if necessary, and some
    // basic Big Ints that everyone needs (0, 1, 2, and 42)
    BigInt._setup = function() {
	if (BigInt.use_applet) {
	    BigInt.APPLET = document.applets["bigint"];
	}
	
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
		// try SJCL
		if (!USE_SJCL) {
		    USE_SJCL = true;
		    this.num_invocations = 1;
		    BigInt.use_applet = false;
		} else {
		    
		    if (BigInt.setup_interval)
			window.clearInterval(BigInt.setup_interval);
		    
		    if (BigInt.setup_fail) {
			BigInt.setup_fail();
		    } else {
			alert('bigint failed!');
		    }
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
}
    
BigInt.fromJSONObject = function(s) {
    return new BigInt(s, 10);
};

BigInt.fromInt = function(i) {
    return BigInt.fromJSONObject("" + i);
};

BigInt.use_applet = false;
