/*
 * JavaScript HTML 5 Worker for BOOTH
 */

// import needed resources
importScripts('js/underscore.min.js');

importScripts(
	'js/jscrypto/jsbn.js',
	'js/jscrypto/jsbn2.js',
	'js/jscrypto/sjcl.js',
	'js/jscrypto/class.js',
	'js/jscrypto/bigint.js',
	'js/jscrypto/random.js',
	'js/jscrypto/elgamal.js',
	'js/jscrypto/sha1.js',
	'js/jscrypto/sha2.js',
	'js/jscrypto/helios.js'
);

var console = {
  'log' : function(msg) {
		self.postMessage({'type': 'log', 'msg': msg});
  }
};

var ELECTION = null;
var Q_NUM = null;
var PROGRESS = 0;

function do_setup(message) {
	console.log('Setting up worker ' + message.question_num);

	ELECTION = HELIOS.Election.fromJSONString(message.election);
	Q_NUM = message.question_num;
}

function do_encrypt(message) {
  console.log('Encrypting answers for question ' + Q_NUM);

	var start = new Date().getTime();
  var encrypted_answer = new HELIOS.EncryptedAnswer(ELECTION.questions[Q_NUM], message.answer, ELECTION.public_key, null, self);
	var end = new Date().getTime();
	var encrypting_time = end-start;

	console.log('Done encrypting in ' + String(encrypting_time) + ' ms');

  // send the result back
  self.postMessage({
	  'type': 'result',
		'encrypted_answer': encrypted_answer.toJSONObject(true),
		'id': message.id
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
