$("title, #banner h1").content('PAGE_TITLE');

BOOTH = {};
BOOTH.debug = true;
BOOTH.setup_templates = function() {
    if (BOOTH.templates_setup_p)
        return;

    var cache_bust = "?cb=" + new Date().getTime();

    $('#header').setTemplateURL("templates/header.html" + cache_bust);
    $('#election_div').setTemplateURL("templates/election.html" + cache_bust);
    $('#question_div').setTemplateURL("templates/question.html" + cache_bust);
    $('#question_stv_div').setTemplateURL("templates/question_stv.html" + cache_bust);
    $('#confirm_div').setTemplateURL("templates/confirm.html" + cache_bust);
    $('#seal_div').setTemplateURL("templates/seal.html" + cache_bust);
    $('#audit_div').setTemplateURL("templates/audit.html" + cache_bust);
    $('#footer .content').setTemplateURL("templates/footer.html" + cache_bust);

    BOOTH.templates_setup_p = true;
};

// set up the message when navigating away
BOOTH.started_p = false;

window.onbeforeunload = function(evt) {
  
  if (BOOTH.debug) { return; }

  if (!BOOTH.started_p)
    return;

  if (typeof evt == 'undefined') {
    evt = window.event;
  }

  var message = "If you leave this page with an in-progress ballot, your ballot will be lost.";

  if (evt) {
    evt.returnValue = message;
  }

  return message;
};

BOOTH.exit = function() {
    if (confirm("Are you sure you want to exit the booth and lose all information about your current ballot?")) {
        BOOTH.started_p = false;
        window.location = BOOTH.election.cast_url;
    }
};

BOOTH.setup_ballot = function(election) {
  BOOTH.ballot = {};

  // dirty markers for encryption (mostly for async)
  BOOTH.dirty = [];

  // each question starts out with an empty array answer
  // and a dirty bit to make sure we encrypt
  BOOTH.ballot.answers = [];
  $(BOOTH.election.questions).each(function(i,x){
    BOOTH.ballot.answers[i] = [];
    BOOTH.dirty[i] = true;
  });
};

// all ciphertexts to null
BOOTH.reset_ciphertexts = function() {
  _(BOOTH.encrypted_answers).each(function(enc_answer, ea_num) {
    BOOTH.launch_async_encryption_answer(ea_num);
  });
};

BOOTH.log = function(msg) {
  if (typeof(console) != undefined)
    console.log(msg);
};

BOOTH.setup_workers = function(election_raw_json) {
  // async?
  if (!BOOTH.synchronous) {
      // prepare spots for encrypted answers
      // and one worker per question
      BOOTH.encrypted_answers = [];
      BOOTH.answer_timestamps = [];
      BOOTH.workers = [];
      $(BOOTH.election.questions).each(function(q_num, q) {
        BOOTH.encrypted_answers[q_num] = null;
        var new_worker = new window.Worker("boothworker.js?" + (new Date()).getTime());
        new_worker.postMessage({
          'type': 'setup',
          'election' : election_raw_json,
          'question_num' : q_num
        });

        new_worker.onmessage = function(event) {
           // logging
           if (event.data.type == 'log')
             return BOOTH.log(event.data.msg);

           // result of encryption
           if (event.data.type == 'result') {
             // this check ensures that race conditions
             // don't screw up votes.
             if (event.data.id == BOOTH.answer_timestamps[q_num]) {
                BOOTH.encrypted_answers[q_num] = HELIOS.EncryptedAnswer.fromJSONObject(event.data.encrypted_answer, BOOTH.election);
                BOOTH.log("got encrypted answer " + q_num);
             } else {
                BOOTH.log("no way jose");
             }
           }
        };

        BOOTH.workers[q_num] = new_worker;
      });
  }
};

function escape_html(content) {
  return $('<div/>').text(content).html();
}

BOOTH.setup_election = function(raw_json) {
  // IMPORTANT: we use the raw JSON for safer hash computation
  // so that we are using the JSON serialization of the SERVER
  // to compute the hash, not the JSON serialization in JavaScript.
  // the main reason for this is unicode representation: the Python approach
  // appears to be safer.
  BOOTH.election = HELIOS.Election.fromJSONString(raw_json);

    if ($.browser.msie) {
            alert("Το πρόγραμμα πλοήγησης που χρησιμοποιείτε δεν υποστηρίζεται από την πλατφόρμα \"Ζευς\". Χρησιμοποιήστε τις νέες εκδόσεις των προγραμμάτων (browser) Mozilla Firefox ή Google Chrome.\n\nΓια περισσότερες πληροφορίες επικοινωνήστε μαζί μας\n\n" + BOOTH.election.help_phone);
            window.location = '/auth/logout';
        }


  // FIXME: we shouldn't need to set both, but right now we are doing so
  // because different code uses each one. Bah. Need fixing.
  BOOTH.election.hash = b64_sha256(raw_json);
  BOOTH.election.election_hash = BOOTH.election.hash

  // async?
  BOOTH.setup_workers(raw_json);

  document.title += ' - ' + BOOTH.election.name;

  // escape election fields
  $(['description', 'name']).each(function(i, field) {
    BOOTH.election[field] = escape_html(BOOTH.election[field]);
  });

  $('#header').processTemplate({'election' : BOOTH.election});
  $('#footer .content').processTemplate({'election' : BOOTH.election});
  BOOTH.setup_ballot();
};

BOOTH.show = function(el) {
  $('.booth-panel').hide();
  el.show();
  return el;
};

BOOTH.show_election = function() {
  BOOTH.show($('#election_div')).processTemplate({'election' : BOOTH.election});
};

BOOTH.launch_async_encryption_answer = function(question_num) {
   BOOTH.answer_timestamps[question_num] = new Date().getTime();
   BOOTH.encrypted_answers[question_num] = null;
   BOOTH.dirty[question_num] = false;
   BOOTH.workers[question_num].postMessage({
      'type' : 'encrypt',
      'answer' : BOOTH.ballot.answers[question_num],
      'id' : BOOTH.answer_timestamps[question_num]
   });
};

// check if the current question is ok
BOOTH.validate_question = function(question_num) {
  if (BOOTH.election.questions[question_num].tally_type == "stv") {

      var answer = BOOTH.ballot.answers[question_num];
      var question = BOOTH.election.questions[question_num];
      
      if (answer.length > 0) {

        if (answer.length > question.answers.length) {
          alert('You need to select at most ' + BOOTH.election.questions[question_num].answers.length + ' answer(s).');
          return false;
        }

        if (_.intersect(answer[0], answer[0]).length != answer[0].length && answer[0].length > 0) {
          alert('You cannot select the same choice more than once');
          return false;
        }

        if (_.filter(answer[0], function(choice){
          if (choice >= question.answers.length) {
            return false;
          }
          return true;
        }).length < answer[0].length) {

          alert('Invalid selection');
          return false;
        };
      }

  } else {
    // check if enough answers are checked
    if (BOOTH.ballot.answers[question_num].length < BOOTH.election.questions[question_num].min) {
      alert('You need to select at least ' + BOOTH.election.questions[question_num].min + ' answer(s).');
      return false;
    }
  }
  
    // if we need to launch the worker, let's do it
    if (!BOOTH.synchronous) {
       // we need a unique ID for this to ensure that old results
       // don't mess things up. Using timestamp.
       // check if dirty
       if (BOOTH.dirty[question_num]) {
         BOOTH.launch_async_encryption_answer(question_num);
       }
    }

    return true;
};

BOOTH.validate_and_confirm = function(question_num) {
  if (BOOTH.election.questions[question_num].tally_type == "stv") {
      BOOTH.stv_updated(question_num, $("#stv_answer").val());
  }

  if (BOOTH.validate_question(question_num)) {
      BOOTH.audit_password = $("#submit-pass-for-audit").val().replace(/ /g, '');
      BOOTH.show_confirm();
  }
};

BOOTH.next = function(question_num) {
    if (BOOTH.validate_question(question_num)) {
        BOOTH.show_question(question_num + 1);
    }
};

BOOTH.previous = function(question_num) {
    if (BOOTH.validate_question(question_num)) {
        BOOTH.show_question(question_num - 1);
    }
};


BOOTH.stv_handle_choice_click = function(e) {
  var answers = $("#question_stv_div input#stv_answer").val().split(",");
  if (answers[0] == "") { answers = [] };
  var index = $(this).parent().index();
  
  var choice_to_remove = answers[index];
  answer = _.without(answers, choice_to_remove).join(",");
  $("#stv_answer").val(answer);
  BOOTH.update_stv_question();
}

BOOTH.stv_handle_candidate_click = function(e) {
  var index = $(this).parent().index();
  var answer = $("#stv_answer").val();
  var append = "";

  if (answer != "") { append = "," }

  answer = answer + append + index;
  $("#stv_answer").val(answer);
  BOOTH.update_stv_question();
}

BOOTH.update_stv_question = function(question_num) {
  var answers = $("#question_stv_div input#stv_answer").val().split(",");
  if (answers[0] == "") { answers = [] };

  var choices = $(".stv-choices .stv-ballot-choice a");
  var cands = $(".stv-candidates .stv-choice a");
  
  cands.removeClass("secondary").removeClass("disabled").addClass("active");
  choices.find("span.value").text("Κενή");
  choices.addClass("disabled").removeClass("success").addClass("secondary").removeClass("filled");

  choices.find("a.filled").hide().text("");
  _.each(answers, function(answer, index) {
    var cand = $(".stv-candidates .choice-" + answer + " a");
    cand.addClass("secondary").addClass("disabled").removeClass("active");
    
    var choice = $($(".stv-ballot-choice").get(index));
    choice.find("span.value").text(cand.text());
    choice.find("a").addClass("success").removeClass("disabled").removeClass("secondary").addClass("filled");
  });
  
}

BOOTH.show_question = function(question_num) {
  BOOTH.audit_password = '';

  if (!BOOTH.stv_handlers) {
    $("#question_stv_div ul.stv-choices a.filled").live('click', BOOTH.stv_handle_choice_click);
    $("#question_stv_div ul.stv-candidates .stv-choice a.active").live('click', BOOTH.stv_handle_candidate_click);
    $("#question_stv_div li a").live('click', function(e){e.preventDefault()});
    BOOTH.stv_handlers = true;
  }
  BOOTH.started_p = true;

  // the first time we hit the last question, we enable the review all button
  if (question_num == BOOTH.election.questions.length -1) {
    BOOTH.all_questions_seen = true;
  }

  BOOTH.show_progress('1');
  
  if (BOOTH.election.workflow_type == "mixnet") {
    BOOTH.show($('#question_stv_div')).processTemplate({'question_num' : question_num,
                        'last_question_num' : BOOTH.election.questions.length - 1,
                        'question' : BOOTH.election.questions[question_num], 'show_reviewall' : BOOTH.all_questions_seen
                  });
  } else {
    BOOTH.show($('#question_div')).processTemplate({'question_num' : question_num,
                        'last_question_num' : BOOTH.election.questions.length - 1,
                        'question' : BOOTH.election.questions[question_num], 'show_reviewall' : BOOTH.all_questions_seen
                  });
  }

  // fake clicking through the answers, to trigger the disabling if need be
  // first we remove the answers array
  var answer_array = BOOTH.ballot.answers[question_num];
  BOOTH.ballot.answers[question_num] = [];

  // we should not set the dirty bit here, so we save it away
  var old_dirty = BOOTH.dirty[question_num];
  $(answer_array).each(function(i, ans) {
    if (BOOTH.election.workflow_type != "mixnet") {
      BOOTH.click_checkbox_script(question_num, ans, true);
    } else {  
      $("#question_stv_div input#stv_answer").val(ans.join(","));
    }
  });

  BOOTH.update_stv_question(question_num);
  BOOTH.dirty[question_num] = old_dirty;
};



BOOTH.click_checkbox_script = function(question_num, answer_num) {
  document.forms['answer_form']['answer_'+question_num+'_'+answer_num].click();
};

BOOTH.stv_updated = function(question_num, answer) {
  BOOTH.dirty[question_num] = true;
  answer = $.trim(answer).toString();

  if (!answer || answer == "") { 
    BOOTH.ballot.answers[question_num] = [];
  } else {
    answer = answer.toString().split(",");
    answer = _(answer).map(function(e){ return parseInt(e)});
    BOOTH.ballot.answers[question_num] = [answer];
  }
}

BOOTH.click_checkbox = function(question_num, answer_num, checked_p) {
  // keep track of dirty answers that need encrypting
  BOOTH.dirty[question_num] = true;

  if (checked_p) {
     // multiple click events shouldn't screw this up
     if ($(BOOTH.ballot.answers[question_num]).index(answer_num) == -1)
        BOOTH.ballot.answers[question_num].push(answer_num);

     $('#answer_label_' + question_num + "_" + answer_num).addClass('selected');
  } else {
     BOOTH.ballot.answers[question_num] = UTILS.array_remove_value(BOOTH.ballot.answers[question_num], answer_num);
     $('#answer_label_' + question_num + "_" + answer_num).removeClass('selected');
  }

  if (BOOTH.election.questions[question_num].max != null && BOOTH.ballot.answers[question_num].length >= BOOTH.election.questions[question_num].max) {
     // disable the other checkboxes
     $('.ballot_answer').each(function(i, checkbox) {
        if (!checkbox.checked)
            checkbox.disabled = true;
     });
     $('#warning_box').html("Maximum number of options selected.<br />To change your selection, please de-select a current selection first.");
  } else {
     // enable the other checkboxes
     $('.ballot_answer').each(function(i, checkbox) {
       checkbox.disabled = false;
     });
     $('#warning_box').html("");
  }
};

BOOTH.show_processing_before = function(str_to_execute) {
    $('#processing_div').html("<h3 align='center'>Processing...</h3>");
    BOOTH.show($('#processing_div'));

    // add a timeout so browsers like Safari actually display the processing message
    setTimeout(str_to_execute, 250);
};

BOOTH.show_encryption_message_before = function(func_to_execute) {
    BOOTH.show($('#encrypting_div'));

    func_to_execute();
};


BOOTH.setup_help_link = function() {
    var election = BOOTH.election;
    var mailto = "mailto:" +
      election.help_email + "?" +
      "subject=Βοήθεια για \"" + election.name + "\"" +
      "&body=" + "Χρειάζομαι βοήθεια για την ψηφοφορία \"" + election.name + 
      "\" (" + election.uuid + ")\n";

    $("#footer .help").attr("href", mailto)
}
BOOTH.load_and_setup_election = function(election_url) {
    // the hash will be computed within the setup function call now
    $.ajax({
      'url': election_url,
      'dataType': 'html',
      'success': function(raw_json) {
        BOOTH.setup_election(raw_json);
        BOOTH.show_election();
        BOOTH.election_url = election_url;
        BOOTH.setup_help_link()
      },
      'error': function(err) {
        alert("Παρουσιάστικε σφάλμα κατα τη διαδικασία αρχικοποίησης της ψηφιακής κάλπης. Παρακαλούμε ενημερώστε τους διαχειριστές του συστήματος.");
        window.location = 'mailto:help@heliosvoting.org';
      }
    });


    if (USE_SJCL) {
      // get more randomness from server
      $.ajax({
        
        'url': election_url + "/get-randomness", 
        'data': {}, 
        'success': function(result) {
          sjcl.random.addEntropy(result.randomness);
        }, 
        'error': function(err){ 
          window.location = '/';
        }
      });
    }
};

BOOTH.hide_progress = function() {
  $('#progress_div').hide();
};

BOOTH.show_progress = function(step_num) {
    $('#progress_div').show();
    $(['1','2','3','4']).each(function(n, step) {
        if (step == step_num)
            $('#progress_' + step).attr('class', 'active');
        else
            $('#progress_' + step).attr('class', '');
    });
};

BOOTH.so_lets_go = function () {
    BOOTH.hide_progress();
    BOOTH.setup_templates();

    // election URL
    var election_url = $.query.get('election_url');
    BOOTH.load_and_setup_election(election_url);
};

BOOTH.nojava = function() {
    // in the case of Chrome, we get here when Java
    // is disabled, instead of detecting the problem earlier.
    // because navigator.javaEnabled() still returns true.
    // $('#election_div').hide();
    // $('#error_div').show();
    USE_SJCL = true;
    sjcl.random.startCollectors();
    BigInt.setup(BOOTH.so_lets_go);
};

BOOTH.ready_p = false;

$(document).ready(function() {
    if (USE_SJCL) {
      sjcl.random.startCollectors();
    }

    // we're asynchronous if we have SJCL and Worker
    BOOTH.synchronous = !(USE_SJCL && window.Worker);

    // we do in the browser only if it's asynchronous
    BigInt.in_browser = true;

    // set up dummy bigint for fast parsing and serialization
    if (!BigInt.in_browser)
      BigInt = BigIntDummy;

    BigInt.setup(BOOTH.so_lets_go, BOOTH.nojava);
});

BOOTH.show_confirm = function() {
    BOOTH.show_progress('2');
    // process the answers
    //var choices = BALLOT.pretty_choices(BOOTH.election, BOOTH.ballot);
    //BOOTH.show($('#confirm_div')).processTemplate({'questions' : BOOTH.election.questions, 'choices' : choices});
    BOOTH.seal_ballot();
};

BOOTH.check_encryption_status = function() {
  var progress = BOOTH.progress.progress();
  if (progress == "" || progress == null)
    progress = "0";

  $('#percent_done').html(progress);
};

BOOTH._after_ballot_encryption = function() {
    // if already serialized, use that, otherwise serialize
    BOOTH.encrypted_vote_json = BOOTH.encrypted_ballot_serialized || 
        JSON.stringify(BOOTH.encrypted_ballot.toJSONObject());

    var do_hash = function() {
       BOOTH.encrypted_ballot_hash = b64_sha256(BOOTH.encrypted_vote_json); // BOOTH.encrypted_ballot.get_hash();
       window.setTimeout(show_cast, 0);
    };
    var choices = BALLOT.pretty_choices(BOOTH.election, BOOTH.ballot);
      
    var show_cast = function() {
      $('#seal_div').processTemplate({'cast_url': BOOTH.election.cast_url,
        'encrypted_vote_json': BOOTH.encrypted_vote_json,
        'encrypted_vote_hash' : BOOTH.encrypted_ballot_hash,
        'election_uuid' : BOOTH.election.uuid,
        'questions' : BOOTH.election.questions,
        'audit_password' : BOOTH.audit_password,
        'election_hash' : BOOTH.election_hash,
        'choices': choices,
        'election': BOOTH.election});
      BOOTH.show($('#seal_div'));
      BOOTH.check_cast_form();
      BOOTH.show_progress('2');
      BOOTH.encrypted_vote_json = null;
    };

    window.setTimeout(do_hash, 0);
};

BOOTH.total_cycles_waited = 0;

// wait for all workers to be done
BOOTH.wait_for_ciphertexts = function() {
    BOOTH.total_cycles_waited += 1;

    var answers_done = _.reject(BOOTH.encrypted_answers, _.isNull);
    var percentage_done = Math.round((100 * answers_done.length) / BOOTH.encrypted_answers.length);

    if (BOOTH.total_cycles_waited > 250) {
      alert('there appears to be a problem with the encryption process.\nPlease email help@heliosvoting.org and indicate that your encryption process froze at ' + percentage_done + '%');
      return;
    }

    if (percentage_done < 100) {
      setTimeout(BOOTH.wait_for_ciphertexts, 500);
      $('#percent_done').html(percentage_done + '');
      return;
    }

    BOOTH.encrypted_ballot = HELIOS.EncryptedVote.fromEncryptedAnswers(BOOTH.election, BOOTH.encrypted_answers);
    BOOTH._after_ballot_encryption();
};

BOOTH.seal_ballot_raw = function() {
    if (BOOTH.synchronous) {
      BOOTH.progress = new UTILS.PROGRESS();
      var progress_interval = setInterval("BOOTH.check_encryption_status()", 500);
      BOOTH.encrypted_ballot = new HELIOS.EncryptedVote(BOOTH.election, BOOTH.ballot.answers, BOOTH.progress);
      clearInterval(progress_interval);
      BOOTH._after_ballot_encryption();
    } else {
      BOOTH.total_cycles_waited = 0;
      BOOTH.wait_for_ciphertexts();
    }
};

BOOTH.request_ballot_encryption = function() {
    $.post(BOOTH.election_url + "/encrypt-ballot", {'answers_json': $.toJSON(BOOTH.ballot.answers)}, function(result) {
      //BOOTH.encrypted_ballot = HELIOS.EncryptedVote.fromJSONObject($.secureEvalJSON(result), BOOTH.election);
      // rather than deserialize and reserialize, which is inherently slow on browsers
      // that already need to do network requests, just remove the plaintexts

      BOOTH.encrypted_ballot_with_plaintexts_serialized = result;
      var ballot_json_obj = $.secureEvalJSON(BOOTH.encrypted_ballot_with_plaintexts_serialized);
      var answers = ballot_json_obj.answers;
      for (var i=0; i<answers.length; i++) {
         delete answers[i]['answer'];
         delete answers[i]['randomness'];
      }

      BOOTH.encrypted_ballot_serialized = JSON.stringify(ballot_json_obj);

      window.setTimeout(BOOTH._after_ballot_encryption, 0);
    });
};

BOOTH.seal_ballot = function() {
    BOOTH.show_progress('2');
    // if we don't have the ability to do crypto in the browser,
    // we use the server
    if (!BigInt.in_browser) {
      BOOTH.show_encryption_message_before(BOOTH.request_ballot_encryption, true);
    } else {
      BOOTH.show_encryption_message_before(BOOTH.seal_ballot_raw, true);
      $('#percent_done_container').show();
    }
};

BOOTH.audit_ballot = function() {
    BOOTH.audit_trail = BOOTH.encrypted_ballot_with_plaintexts_serialized || $.toJSON(BOOTH.encrypted_ballot.get_audit_trail());

    BOOTH.show($('#audit_div')).processTemplate({'audit_trail' : BOOTH.audit_trail, 'election_url' : BOOTH.election_url});
};

BOOTH.post_audited_ballot = function() {
  $.post(BOOTH.election_url + "/post-audited-ballot", {'audited_ballot': BOOTH.audit_trail}, function(result) {
    alert('This audited ballot has been posted.\nRemember, this vote will only be used for auditing and will not be tallied.\nClick "back to voting" and cast a new ballot to make sure your vote counts.');
  });
};

BOOTH.cast_ballot = function() {

    if ($("#required-to-cast-2:checked").length > 0) {
    } else {
        alert("Παρακαλούμε αποδεχθείτε τους όρους της ψηφοφορίας.");
        return;
    }

    // show progress spinner
    $('#loading_div').html('<img src="loading.gif" id="proceed_loading_img" />');
    $('#proceed_button').attr('disabled', 'disabled');


    // submit the form
    var data = $('#send_ballot_form').serialize();
    var url = $('#send_ballot_form').attr("action");

    $.ajax({
      url: url,
      data: data,
      type: 'POST',
      dataType: 'json',
      success: function(data, status, xhr) {
        if (data.audit) {
          BOOTH.audit_ballot();
        } else {
          // at this point, we delete the plaintexts by resetting the ballot
          BOOTH.setup_ballot(BOOTH.election);

          // clear the plaintext from the encrypted
          if (BOOTH.encrypted_ballot) {
            BOOTH.encrypted_ballot.clearPlaintexts();
          }

          BOOTH.encrypted_ballot_serialized = null;
          BOOTH.encrypted_ballot_with_plaintexts_serialized = null;

          // remove audit trail
          BOOTH.audit_trail = null;

          // we're ready to leave the site
          BOOTH.started_p = false;
          window.location = data.cast_url;
        }
      },
      error: function(xhr, status, error) {
        alert("Προέκυψε σφάλμα στην καταχώρηση της ψήφου σας, παρακαλούμε" +
              " δοκιμάστε ξανά.");
        BOOTH.show_question(0);
      }
    })
};

BOOTH.show_receipt = function() {
    UTILS.open_window_with_content("Αναγνωριστικό ψήφου για την ψηφοφορία '" + BOOTH.election.name + "': " + BOOTH.encrypted_ballot_hash);
};

BOOTH.do_done = function() {
  BOOTH.started_p = false;
};

BOOTH.check_cast_form = function() {
  $(".form-row").removeClass("checked");
  var submit = $("button#proceed_button");

  if ($("#required-to-cast-2:checked").length > 0) {
      $("#required-to-cast-2").closest(".form-row").addClass("checked");
  }
  if ($("#required-to-cast-2:checked").length > 0) {
      submit.removeClass("secondary");
  } else {
      submit.addClass("secondary");
  }
}

//window.setTimeout(function(){
  //// do some js testing here
  //$("button.start-voting").click();
//}, 100);

//window.setTimeout(function(){
  //// do some js testing here
  //$(".stv-choice.choice-1 a").click();
  ////window.setTimeout(function(){
    ////$("#submit-stv").click();
    ////window.setTimeout(function(){
      ////$("#confirm-vote").click();
    ////},300);
  ////}, 300);
//}, 300);

$("span.election-desc-toggle").live("click", function(){
  $('#election-description-modal').reveal();
})

$(".audit-button").live("click", function() {
  $("#auditbody").slideToggle();
})

$(".show-audit-form").live("click", function(e) {
  e.preventDefault();
  $(".audit-form").slideToggle();
  $(this).toggleClass("active");
  $("#submit-pass-for-audit").focus();
  $("#submit-pass-for-audit").val("");
});

window.BOOTH = BOOTH;
