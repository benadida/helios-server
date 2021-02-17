
//
// Helios Protocols
// 
// ben@adida.net
//
// FIXME: needs a healthy refactor/cleanup based on Class.extend()
//

// extend jquery to do object keys
// from http://snipplr.com/view.php?codeview&id=10430
/*
$.extend({
    keys: function(obj){
        var a = [];
        $.each(obj, function(k){ a.push(k) });
        return a.sort();
    }
});
*/

var UTILS = {};

UTILS.array_remove_value = function(arr, val) {
  var new_arr = [];
  _(arr).each(function(v, i) {
    if (v != val) {
	new_arr.push(v);
    }
  });

  return new_arr;
};

UTILS.select_element_content = function(element) {
  var range;
  if (window.getSelection) { // FF, Safari, Opera
    var sel = window.getSelection();
    range = document.createRange();
    range.selectNodeContents(element);
    sel.removeAllRanges();
    sel.addRange(range);
  } else {
    document.selection.empty();
    range = document.body.createTextRange();
    range.moveToElementText(el);
    range.select();
  }
};

// a progress tracker
UTILS.PROGRESS = Class.extend({
  init: function() {
    this.n_ticks = 0.0;
    this.current_tick = 0.0;
  },
  
  addTicks: function(n_ticks) {
    this.n_ticks += n_ticks;
  },
  
  tick: function() {
    this.current_tick += 1.0;
  },
  
  progress: function() {
    return Math.round((this.current_tick / this.n_ticks) * 100);
  }
});

// produce the same object but with keys sorted
UTILS.object_sort_keys = function(obj) {
  var new_obj = {};
  _(_.keys(obj)).each(function(k) {
    new_obj[k] = obj[k];
  });
  return new_obj;
};

//
// Helios Stuff
//

HELIOS = {};

// a bogus default public key to allow for ballot previewing, nothing more
// this public key should not be used ever, that's why the secret key is 
// not given.
HELIOS.get_bogus_public_key = function() {
  return ElGamal.PublicKey.fromJSONObject(JSON.parse('{"g": "14887492224963187634282421537186040801304008017743492304481737382571933937568724473847106029915040150784031882206090286938661464458896494215273989547889201144857352611058572236578734319505128042602372864570426550855201448111746579871811249114781674309062693442442368697449970648232621880001709535143047913661432883287150003429802392229361583608686643243349727791976247247948618930423866180410558458272606627111270040091203073580238905303994472202930783207472394578498507764703191288249547659899997131166130259700604433891232298182348403175947450284433411265966789131024573629546048637848902243503970966798589660808533", "p": "16328632084933010002384055033805457329601614771185955389739167309086214800406465799038583634953752941675645562182498120750264980492381375579367675648771293800310370964745767014243638518442553823973482995267304044326777047662957480269391322789378384619428596446446984694306187644767462460965622580087564339212631775817895958409016676398975671266179637898557687317076177218843233150695157881061257053019133078545928983562221396313169622475509818442661047018436264806901023966236718367204710755935899013750306107738002364137917426595737403871114187750804346564731250609196846638183903982387884578266136503697493474682071", "q": "61329566248342901292543872769978950870633559608669337131139375508370458778917", "y": "8049609819434159960341080485505898805169812475728892670296439571117039276506298996734003515763387841154083296559889658342770776712289026341097211553854451556820509582109412351633111518323196286638684857563764318086496248973278960517204721786711381246407429787246857335714789053255852788270719245108665072516217144567856965465184127683058484847896371648547639041764249621310049114411288049569523544645318180042074181845024934696975226908854019646138985505600641910417380245960080668869656287919893859172484656506039729440079008919716011166605004711585860172862472422362509002423715947870815838511146670204726187094944"}'));
};

// election
HELIOS.Election = Class.extend({
  init: function() {
  },
  
  toJSONObject: function() {
    var json_obj = {uuid : this.uuid,
    description : this.description, short_name : this.short_name, name : this.name,
    public_key: this.public_key.toJSONObject(), questions : this.questions,
    cast_url: this.cast_url, frozen_at: this.frozen_at,
    openreg: this.openreg, voters_hash: this.voters_hash,
    use_voter_aliases: this.use_voter_aliases,
    voting_starts_at: this.voting_starts_at,
    voting_ends_at: this.voting_ends_at};
    
    return UTILS.object_sort_keys(json_obj);
  },
  
  get_hash: function() {
    if (this.election_hash)
      return this.election_hash;
    
    // otherwise  
    return b64_sha256(this.toJSON());
  },
  
  toJSON: function() {
    // FIXME: only way around the backslash thing for now.... how ugly
    //return jQuery.toJSON(this.toJSONObject()).replace(/\//g,"\\/");
    return JSON.stringify(this.toJSONObject());
  }
});

HELIOS.Election.fromJSONString = function(raw_json) {
  var json_object = JSON.parse(raw_json);
  
  // let's hash the raw_json
  var election = HELIOS.Election.fromJSONObject(json_object);
  election.election_hash = b64_sha256(raw_json);
  
  return election;
};

HELIOS.Election.fromJSONObject = function(d) {
  var el = new HELIOS.Election();
  _.extend(el, d);
  
  // empty questions
  if (!el.questions)
    el.questions = [];
  
  if (el.public_key) {
    el.public_key = ElGamal.PublicKey.fromJSONObject(el.public_key);
  } else {
    // a placeholder that will allow hashing;
    el.public_key = HELIOS.get_bogus_public_key();
    el.BOGUS_P = true;
  }
    
  return el;
};

HELIOS.Election.setup = function(election) {
  return ELECTION.fromJSONObject(election);
};


// ballot handling
BALLOT = {};

BALLOT.pretty_choices = function(election, ballot) {
    var questions = election.questions;
    var answers = ballot.answers;

    // process the answers
    var choices = _(questions).map(function(q, q_num) {
	    return _(answers[q_num]).map(function(ans) {
	      return questions[q_num].answers[ans];
	    });
    });

    return choices;
};


// open up a new window and do something with it.
UTILS.open_window_with_content = function(content, mime_type) {
    if (!mime_type)
	mime_type = "text/plain";
    if (BigInt.is_ie) {
	    w = window.open("");
	    w.document.open(mime_type);
	    w.document.write(content);
	    w.document.close();
    } else {
	    w = window.open("data:" + mime_type + "," + encodeURIComponent(content));
    }
};

// generate an array of the first few plaintexts
UTILS.generate_plaintexts = function(pk, min, max) {
  var last_plaintext = BigInt.ONE;

  // an array of plaintexts
  var plaintexts = [];
  
  if (min == null)
    min = 0;
  
  // questions with more than one possible answer, add to the array.
  for (var i=0; i<=max; i++) {
    if (i >= min)
      plaintexts.push(new ElGamal.Plaintext(last_plaintext, pk, false));
    last_plaintext = last_plaintext.multiply(pk.g).mod(pk.p);
  }
  
  return plaintexts;
}


//
// crypto
//


HELIOS.EncryptedAnswer = Class.extend({
  init: function(question, answer, pk, progress) {    
    // if nothing in the constructor
    if (question == null)
      return;

    // store answer
    // CHANGE 2008-08-06: answer is now an *array* of answers, not just a single integer
    this.answer = answer;

    // do the encryption
    var enc_result = this.doEncryption(question, answer, pk, null, progress);

    this.choices = enc_result.choices;
    this.randomness = enc_result.randomness;
    this.individual_proofs = enc_result.individual_proofs;
    this.overall_proof = enc_result.overall_proof;    
  },
  
  doEncryption: function(question, answer, pk, randomness, progress) {
    var choices = [];
    var individual_proofs = [];
    var overall_proof = null;
    
    // possible plaintexts [question.min .. , question.max]
    var plaintexts = null;
    if (question.max != null) {
      plaintexts = UTILS.generate_plaintexts(pk, question.min, question.max);
    }
    
    var zero_one_plaintexts = UTILS.generate_plaintexts(pk, 0, 1);
    
    // keep track of whether we need to generate new randomness
    var generate_new_randomness = false;    
    if (!randomness) {
      randomness = [];
      generate_new_randomness = true;
    }
    
    // keep track of number of options selected.
    var num_selected_answers = 0;
    
    // go through each possible answer and encrypt either a g^0 or a g^1.
    for (var i=0; i<question.answers.length; i++) {
      var index, plaintext_index;
      // if this is the answer, swap them so m is encryption 1 (g)
      if (_(answer).include(i)) {
        plaintext_index = 1;
        num_selected_answers += 1;
      } else {
        plaintext_index = 0;
      }

      // generate randomness?
      if (generate_new_randomness) {
        randomness[i] = Random.getRandomInteger(pk.q);        
      }

      choices[i] = ElGamal.encrypt(pk, zero_one_plaintexts[plaintext_index], randomness[i]);
      
      // generate proof
      if (generate_new_randomness) {
        // generate proof that this ciphertext is a 0 or a 1
        individual_proofs[i] = choices[i].generateDisjunctiveProof(zero_one_plaintexts, plaintext_index, randomness[i], ElGamal.disjunctive_challenge_generator);        
      }
      
      if (progress)
        progress.tick();
    }

    if (generate_new_randomness && question.max != null) {
      // we also need proof that the whole thing sums up to the right number
      // only if max is non-null, otherwise it's full approval voting
    
      // compute the homomorphic sum of all the options
      var hom_sum = choices[0];
      var rand_sum = randomness[0];
      for (var i=1; i<question.answers.length; i++) {
        hom_sum = hom_sum.multiply(choices[i]);
        rand_sum = rand_sum.add(randomness[i]).mod(pk.q);
      }
    
      // prove that the sum is 0 or 1 (can be "blank vote" for this answer)
      // num_selected_answers is 0 or 1, which is the index into the plaintext that is actually encoded
      //
      // now that "plaintexts" only contains the array of plaintexts that are possible starting with min
      // and going to max, the num_selected_answers needs to be reduced by min to be the proper index
      var overall_plaintext_index = num_selected_answers;
      if (question.min)
        overall_plaintext_index -= question.min;
      
      overall_proof = hom_sum.generateDisjunctiveProof(plaintexts, overall_plaintext_index, rand_sum, ElGamal.disjunctive_challenge_generator);

      if (progress) {
        for (var i=0; i<question.max; i++)
          progress.tick();
      }
    }
    
    return {
      'choices' : choices,
      'randomness' : randomness,
      'individual_proofs' : individual_proofs,
      'overall_proof' : overall_proof
    };
  },
  
  clearPlaintexts: function() {
    this.answer = null;
    this.randomness = null;
  },
  
  // FIXME: should verifyEncryption really generate proofs? Overkill.
  verifyEncryption: function(question, pk) {
    var result = this.doEncryption(question, this.answer, pk, this.randomness);

    // check that we have the same number of ciphertexts
    if (result.choices.length != this.choices.length) {
      return false;      
    }
      
    // check the ciphertexts
    for (var i=0; i<result.choices.length; i++) {
      if (!result.choices[i].equals(this.choices[i])) {
        // alert ("oy: " + result.choices[i] + "/" + this.choices[i]);
        return false;
      }
    }
    
    // we made it, we're good
    return true;
  },
  
  toString: function() {
    // get each ciphertext as a JSON string
    var choices_strings = _(this.choices).map(function(c) {return c.toString();});
    return choices_strings.join("|");
  },
  
  toJSONObject: function(include_plaintext) {
    var return_obj = {
      'choices' : _(this.choices).map(function(choice) {
        return choice.toJSONObject();
      }),
      'individual_proofs' : _(this.individual_proofs).map(function(disj_proof) {
        return disj_proof.toJSONObject();
      })
    };
    
    if (this.overall_proof != null) {
      return_obj.overall_proof = this.overall_proof.toJSONObject();
    } else {
      return_obj.overall_proof = null;
    }
    
    if (include_plaintext) {
      return_obj.answer = this.answer;
      return_obj.randomness = _(this.randomness).map(function(r) {
        return r.toJSONObject();
      });
    }
    
    return return_obj;
  }
});

HELIOS.EncryptedAnswer.fromJSONObject = function(d, election) {
  var ea = new HELIOS.EncryptedAnswer();
  ea.choices = _(d.choices).map(function(choice) {
    return ElGamal.Ciphertext.fromJSONObject(choice, election.public_key);
  });
  
  ea.individual_proofs = _(d.individual_proofs).map(function (p) {
    return ElGamal.DisjunctiveProof.fromJSONObject(p);
  });
  
  ea.overall_proof = ElGamal.DisjunctiveProof.fromJSONObject(d.overall_proof);
  
  // possibly load randomness and plaintext
  if (d.randomness) {
    ea.randomness = _(d.randomness).map(function(r) {
      return BigInt.fromJSONObject(r);
    });
    ea.answer = d.answer;
  }
  
  return ea;
};

HELIOS.EncryptedVote = Class.extend({
  init: function(election, answers, progress) {
    // empty constructor
    if (election == null)
      return;

    // keep information about the election around
    this.election_uuid = election.uuid;
    this.election_hash = election.get_hash();
    this.election = election;
     
    if (answers == null)
      return;
      
    var n_questions = election.questions.length;
    this.encrypted_answers = [];

    if (progress) {
      // set up the number of ticks
      _(election.questions).each(function(q, q_num) {
        // + 1 for the overall proof
        progress.addTicks(q.answers.length);
        if (q.max != null)
          progress.addTicks(q.max);
      });

      progress.addTicks(0, n_questions);
    }
      
    // loop through questions
    for (var i=0; i<n_questions; i++) {
      this.encrypted_answers[i] = new HELIOS.EncryptedAnswer(election.questions[i], answers[i], election.public_key, progress);
    }    
  },

  toString: function() {
    // for each question, get the encrypted answer as a string
    var answer_strings = _(this.encrypted_answers).map(function(a) {return a.toString();});
    
    return answer_strings.join("//");
  },
  
  clearPlaintexts: function() {
    _(this.encrypted_answers).each(function(ea) {
      ea.clearPlaintexts();
    });
  },
  
  verifyEncryption: function(questions, pk) {
    var overall_result = true;
    _(this.encrypted_answers).each(function(ea, i) {
      overall_result = overall_result && ea.verifyEncryption(questions[i], pk);
    });
    return overall_result;
  },
  
  toJSONObject: function(include_plaintext) {
      var answers = _(this.encrypted_answers).map(function(ea,i) {
      return ea.toJSONObject(include_plaintext);
    });
    
    return {
      answers : answers,
      election_hash : this.election_hash,
      election_uuid : this.election_uuid
    }
  },
  
  get_hash: function() {
     return b64_sha256(JSON.stringify(this.toJSONObject()));
  },
  
  get_audit_trail: function() {
    return this.toJSONObject(true);
  },
  
  verifyProofs: function(pk, outcome_callback) {
    var zero_or_one = UTILS.generate_plaintexts(pk, 0, 1);

    var VALID_P = true;
    
    var self = this;
    
    // for each question and associate encrypted answer
    _(this.encrypted_answers).each(function(enc_answer, ea_num) {
        var overall_result = 1;

        // the max number of answers (decides whether this is approval or not and requires an overall proof)
        var max = self.election.questions[ea_num].max;

        // go through each individual proof
        _(enc_answer.choices).each(function(choice, choice_num) {
          var result = choice.verifyDisjunctiveProof(zero_or_one, enc_answer.individual_proofs[choice_num], ElGamal.disjunctive_challenge_generator);
          outcome_callback(ea_num, choice_num, result, choice);
          
          VALID_P = VALID_P && result;
           
          // keep track of homomorphic product, if needed
          if (max != null)
            overall_result = choice.multiply(overall_result);
        });
        
        if (max != null) {
          // possible plaintexts [0, 1, .. , question.max]
          var plaintexts = UTILS.generate_plaintexts(pk, self.election.questions[ea_num].min, self.election.questions[ea_num].max);
        
          // check the proof on the overall product
          var overall_check = overall_result.verifyDisjunctiveProof(plaintexts, enc_answer.overall_proof, ElGamal.disjunctive_challenge_generator);
          outcome_callback(ea_num, null, overall_check, null);
          VALID_P = VALID_P && overall_check;
        } else {
          // check to make sure the overall_proof is null, since it's approval voting
          VALID_P = VALID_P && (enc_answer.overall_proof == null)
        }
    });
    
    return VALID_P;
  }
});

HELIOS.EncryptedVote.fromJSONObject = function(d, election) {
  if (d == null)
    return null;
    
  var ev = new HELIOS.EncryptedVote(election);
  
  ev.encrypted_answers = _(d.answers).map(function(ea) {
    return HELIOS.EncryptedAnswer.fromJSONObject(ea, election);
  });
  
  ev.election_hash = d.election_hash;
  ev.election_uuid = d.election_uuid;
  
  return ev;
};

// create an encrypted vote from a set of answers
HELIOS.EncryptedVote.fromEncryptedAnswers = function(election, enc_answers) {
    var enc_vote = new HELIOS.EncryptedVote(election, null);
    enc_vote.encrypted_answers = [];
    _(enc_answers).each(function(enc_answer, answer_num) {
	    enc_vote.encrypted_answers[answer_num] = enc_answer;
	});
    return enc_vote;
};

//
// Tally abstraction
//

HELIOS.Tally = Class.extend({
  init: function(raw_tally, num_tallied) {
    this.tally = raw_tally;
    this.num_tallied = num_tallied;
  },
  
  toJSONObject: function() {
    var tally_json_obj = _(this.tally).map(function(one_q) {
      return _(one_q).map(function(one_a) {
        return one_a.toJSONObject();
      });
    });
    
    return {
      num_tallied : this.num_tallied,
      tally: tally_json_obj
    };
  }
  
});

HELIOS.Tally.fromJSONObject = function(d, public_key) {
  var num_tallied = d['num_tallied'];
  
  var raw_tally = _(d['tally']).map(function(one_q) {
    return _(one_q).map(function(one_a) {
      var new_val= ElGamal.Ciphertext.fromJSONObject(one_a, public_key);
      return new_val;
    });
  });
  
  return new HELIOS.Tally(raw_tally, num_tallied);
};

//
// distributed decryption : Trustees
//

// a utility function for jsonifying a list of lists of items
HELIOS.jsonify_list_of_lists = function(lol) {
  if (!lol)
    return null;
    
  return _(lol).map(function(sublist) {return _(sublist).map(function(item) {return item.toJSONObject();})});
};

// a utility function for doing the opposite with an item-level de-jsonifier
HELIOS.dejsonify_list_of_lists = function(lol, item_dejsonifier) {
  if (!lol)
    return null;
    
  return _(lol).map(function(sublist) {return _(sublist).map(function(item) {return item_dejsonifier(item);})});
}

HELIOS.Trustee = Class.extend({
  init: function(uuid, public_key, public_key_hash, pok, decryption_factors, decryption_proofs, email) {
    this.uuid = uuid;
    this.public_key = public_key;
    this.public_key_hash = public_key_hash;
    this.pok = pok;
    this.decryption_factors = decryption_factors;
    this.decryption_proofs = decryption_proofs;
    this.email = email;
  },
  
  toJSONObject: function() {
    return {
      'decryption_factors' : HELIOS.jsonify_list_of_lists(this.decryption_factors),
      'decryption_proofs' : HELIOS.jsonify_list_of_list(this.decryption_proofs),
      'email' : this.email, 'name' : this.name, 'pok' : this.pok.toJSONObject(), 'public_key' : this.public_key.toJSONObject()
    };
  }
});

HELIOS.Trustee.fromJSONObject = function(d) {
  return new HELIOS.Trustee(d.uuid,
    ElGamal.PublicKey.fromJSONObject(d.public_key), d.public_key_hash, ElGamal.DLogProof.fromJSONObject(d.pok),
    HELIOS.dejsonify_list_of_lists(d.decryption_factors, BigInt.fromJSONObject),
    HELIOS.dejsonify_list_of_lists(d.decryption_proofs, ElGamal.Proof.fromJSONObject),
    d.email
   );
};
