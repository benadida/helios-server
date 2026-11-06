/**
 * Web Worker for verifying audited ballots in a background thread.
 * Adapted from heliosbooth/verifierworker.js + heliosbooth/verifier.js
 *
 * Message types:
 * - verify: Verify an audited ballot against an election
 *
 * Response types:
 * - log: Logging message
 * - status: Status update message for display
 * - result: Final verification result (boolean)
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

var status_update = function(msg) {
  self.postMessage({ type: 'status', msg: msg });
};

/**
 * Verify a ballot against an election.
 * Adapted from heliosbooth/verifier.js
 */
function verify_ballot(election_raw_json, encrypted_vote_json, status_cb) {
  var overall_result = true;
  try {
    var election = HELIOS.Election.fromJSONString(election_raw_json);
    var election_hash = election.get_hash();
    status_cb("election fingerprint is " + election_hash);

    var encrypted_vote = HELIOS.EncryptedVote.fromJSONObject(encrypted_vote_json, election);
    status_cb("ballot tracker is " + encrypted_vote.get_hash());

    if (election_hash == encrypted_vote.election_hash) {
      status_cb("election fingerprint matches ballot");
    } else {
      overall_result = false;
      status_cb("PROBLEM = election fingerprint does not match");
    }

    status_cb("Ballot Contents:");
    _(election.questions).each(function(q, qnum) {
      if (q.tally_type != "homomorphic") {
        status_cb("WARNING: the tally type for this question is not homomorphic. Verification may fail because this verifier is only set up to handle homomorphic ballots.");
      }

      var answer_pretty_list = _(encrypted_vote.encrypted_answers[qnum].answer).map(function(aindex) {
        return q.answers[aindex];
      });
      status_cb("Question #" + (qnum + 1) + " - " + q.short_name + " : " + answer_pretty_list.join(", "));
    });

    if (encrypted_vote.verifyEncryption(election.questions, election.public_key)) {
      status_cb("Encryption Verified");
    } else {
      overall_result = false;
      status_cb("PROBLEM = Encryption doesn't match.");
    }

    if (encrypted_vote.verifyProofs(election.public_key, function() {})) {
      status_cb("Proofs ok.");
    } else {
      overall_result = false;
      status_cb("PROBLEM = Proofs don't work.");
    }
  } catch (e) {
    status_cb('problem parsing election or ballot data structures, malformed inputs: ' + e.toString());
    overall_result = false;
  }

  return overall_result;
}

/**
 * Handle verify message.
 */
function do_verify(message) {
  console.log('verifying!');

  var result = verify_ballot(message.election, message.vote, status_update);

  self.postMessage({
    type: 'result',
    result: result
  });
}

/**
 * Message handler.
 */
self.onmessage = function(event) {
  if (event.data.type === 'verify') {
    do_verify(event.data);
  }
};
