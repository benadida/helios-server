/*
 * JavaScript HTML 5 Worker for BOOTH
 */

// import needed resources
importScripts("../underscore-min.js");

importScripts("jsbn.js",
	      "jsbn2.js",
	      "sjcl.js",
	      "class.js",
	      "bigint.js",
	      "random.js",
	      "elgamal.js",
	      "sha1.js",
	      "sha2.js",
	      "helios.js");


var status_update = function(msg) {
    self.postMessage({'type' : 'status', 'msg' : msg});
};

var ELECTION = null;
var VOTE = null;

function do_decrypt(message) {
    var console = {
        'log' : function(msg) {
          self.postMessage({'type':'log','msg':msg});
        }
    };
    console.log("decrypting!");
    
    var d = new Date;
    var secret_key = ElGamal.SecretKey.fromJSONObject(message.sk);
    var choice_tally = ElGamal.Ciphertext.fromJSONObject(message.choice);
    var one_choice_result = secret_key.decryptionFactorAndProof(choice_tally, 
                                                ElGamal.fiatshamir_challenge_generator);

    var result = {};
    result['factor'] = one_choice_result['decryption_factor'].toJSONObject();
    result['proof'] = one_choice_result['decryption_proof'].toJSONObject();
    result['index'] = message.index;
    result['time'] = (new Date) - d;

    // send the result back
    self.postMessage({
	    'type': 'result',
		'result': result
    });
}

// receive either
// a) an election and an integer position of the question
// that this worker will be used to encrypt
// {'type': 'setup', 'question_num' : 2, 'election' : election_json}
//
// b) an answer that needs encrypting
// {'type': 'encrypt', 'answer' : answer_json}
//
self.onmessage = function(event) {
    // dispatch to method
    self['do_' + event.data.type](event.data);
}

