/**
 * Web Worker for encrypting ballots in background thread.
 * Adapted from heliosbooth/boothworker-single.js
 *
 * Message types:
 * - setup: Initialize with election JSON
 * - encrypt: Encrypt an answer for a specific question
 *
 * Response types:
 * - log: Logging message
 * - result: Encrypted answer result
 */

// Import crypto libraries - paths relative to worker location
importScripts(
  '../lib/underscore-min.js',
  '../lib/jscrypto/jsbn.js',
  '../lib/jscrypto/jsbn2.js',
  '../lib/jscrypto/sjcl.js',
  '../lib/jscrypto/class.js',
  '../lib/jscrypto/bigint.js',
  '../lib/jscrypto/random.js',
  '../lib/jscrypto/elgamal.js',
  '../lib/jscrypto/sha1.js',
  '../lib/jscrypto/sha2.js',
  '../lib/jscrypto/helios.js'
);

// Console shim - sends logs back to main thread
var console = {
  log: function(msg) {
    self.postMessage({ type: 'log', msg: msg });
  }
};

// Election object - set during setup
var ELECTION = null;

/**
 * Handle setup message - parse and store election.
 */
function do_setup(message) {
  console.log('Setting up encryption worker');
  ELECTION = HELIOS.Election.fromJSONString(message.election);
  console.log('Election loaded: ' + ELECTION.name);
}

/**
 * Handle encrypt message - encrypt answer for a question.
 */
function do_encrypt(message) {
  console.log('Encrypting answer for question ' + message.q_num);

  var encrypted_answer = new HELIOS.EncryptedAnswer(
    ELECTION.questions[message.q_num],
    message.answer,
    ELECTION.public_key
  );

  console.log('Done encrypting question ' + message.q_num);

  // Send result back to main thread
  self.postMessage({
    type: 'result',
    q_num: message.q_num,
    encrypted_answer: encrypted_answer.toJSONObject(true),
    id: message.id
  });
}

/**
 * Message handler - dispatch to appropriate function.
 */
self.onmessage = function(event) {
  if (event.data.type === 'setup') {
    do_setup(event.data);
  } else if (event.data.type === 'encrypt') {
    do_encrypt(event.data);
  }
};
