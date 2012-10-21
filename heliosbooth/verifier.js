// helper functions for verifying a ballot
// assumes all of Helios machinery is loaded

function verify_ballot(election_raw_json, encrypted_vote_json, status_cb) {
    var overall_result = true;
	election = HELIOS.Election.fromJSONString(election_raw_json);
	var election_hash = election.get_hash();
	status_cb("Αναγνωριστικό ψηφοφορίας: " + election_hash);
	
	// display ballot fingerprint
	encrypted_vote = HELIOS.EncryptedVote.fromJSONObject(encrypted_vote_json, election);
	status_cb("Το αναγνωριστικό της ψήφου σας είναι: " + encrypted_vote.get_hash());
	
      // check the hash
      //if (election_hash == encrypted_vote.election_hash) {
          //status_cb("Το αναγνωριστικό ψηφοφορίας είναι έγκυρο.");
      //} else {
          //overall_result = false;
          //status_cb("ΠΡΟΒΛΗΜΑ: Το αναγνωριστικό ψηφοφορίας ΔΕΝ είναι έγκυρο");          
      //}
      
      // display the ballot as it is claimed to be
      status_cb("Ballot Contents:");
      _(election.questions).each(function(q, qnum) {
          if (q.tally_type == "homomorphic") {
            var answer_pretty_list = _(encrypted_vote.encrypted_answers[qnum].answer).map(function(aindex, anum) {
                return q.answers[aindex];
            });
          } else {
            var abs_answers = STV.to_absolute_answers(encrypted_vote.encrypted_answers[qnum].answer[0], 
                                                             q.answers.length);

            var answer_pretty_list = _(abs_answers).map(function(aindex, anum) {
              return q.answers[aindex];
            })
          }
	      status_cb("Question #" + (qnum+1) + " - " + q.short_name + " : " + answer_pretty_list.join(", "));
      });
      
      // verify the encryption
      if (encrypted_vote.verifyEncryption(election.questions, election.public_key)) {
          status_cb("Η κρυπτογράφηση είναι έγκυρη.");
      } else {
          overall_result = false;
          status_cb("ΠΡΟΒΛΗΜΑ = Η κρυπτογράφηση ΔΕΝ είναι έγκυρη.");
      }
      
      // verify the proofs
      if (election.workflow_type == "homomorphic") {
        if (encrypted_vote.verifyProofs(election.public_key, function(ea_num, choice_num, result) {
        })) {
            status_cb("Proofs ok.");
        } else {
            overall_result = false;
            status_cb("PROBLEM = Proofs don't work.");
        }
      }

    return overall_result;
}
