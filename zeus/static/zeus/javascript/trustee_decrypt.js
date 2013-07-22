if(!Array.prototype.indexOf) {
    Array.prototype.indexOf = function(what, i) {
        i = i || 0;
        var L = this.length;
        while (i < L) {
            if(this[i] === what) return i;
            ++i;
        }
        return -1;
    };
}


Array.prototype.remove = function() {
    var what, a = arguments, L = a.length, ax;
    while (L && this.length) {
        what = a[--L];
        while ((ax = this.indexOf(what)) !== -1) {
            this.splice(ax, 1);
        }
    }
    return this;
};


var decryptionWorkersCount = 8;


function Poll(options) {
  this.options = options;
  this.el = options.el;
  this.post_url = options.post_url;
  this.get_url = options.get_url;
  this.secret_key = options.secret_key;
  this.init();
}

Poll.prototype = {
  
  get_actions: function() {
    return this.el.find('td a');
  },

  init: function() {
    if (!this.get_actions().length) {
      return;
    }
    var actions = this.get_actions();
    actions.filter('.decrypt').bind('click', _.bind(this.decrypt, this))
    actions.filter('.upload').bind('click', _.bind(this.upload, this))
    actions.filter('.download').bind('click', _.bind(this.download, this))
    actions.filter('.download').hide();
    this.status = actions.filter('.download').parent().append("<span class='status'></span>");
  },
  
  set_status: function(status) {
    this.status.text(status);
  },

  hide_actions: function() {
    this.get_actions().hide();
    this.status.show();
  },

  show_actions: function() {
    var actions = this.get_actions();
    actions.show();
    this.status.hide();
    actions.filter('.download').hide();
  },

  decrypt: function() {
    this.hide_actions();
    this.set_status("Downloading...")
    this.download_ciphers(_.bind(function(content){
      this.poll = content.poll;
      this.public_key = ElGamal.PublicKey.fromJSONObject(this.poll.public_key);
      this.tally = HELIOS.Tally.fromJSONObject(content.tally, this.pk);
      this.decrypt_tally()
      this.set_status(this.tally.num_tallied + " ciphers downloaded");
    }, this), _.bind(function() {
      this.show_actions();
    }, this));
  },
  
  decrypt_tally: function() {
    this.set_status("Decrypting...");
    decrypt_and_prove_tally(this.tally, this.public_key, 
                            this.secret_key, 
                            _.bind(this.decrypt_callback, this));
  },
  
  decrypt_callback: function(data) {
    this.decription = data;
    this.set_status("Uploading...");
    
    $.ajax({
      type: 'POST',
      url: this.post_url,
      timeout: 300000,
      data: {'factors_and_proofs': $.toJSON(data)},
      success: _.bind(function(result) {
        if (result != "FAILURE") {
          this.set_status("Completed")
        } else {
          this.set_status("Invalid secret key")
        }
      }, this),
      error: _.bind(function() {
        this.set_status("Error uploading");
        this.get_actions().filter('.download').show();
      }, this)
    });
  },

  upload: function() {
  },

  download: function() {
  },

  download_ciphers: function(success, error) {
    $.ajax({
      url: this.get_url,
      success: _.bind(success, this),
      error: _.bind(error, this),
      dataType: 'json'
    })
  }

}


function TrusteeDecrypt(options) {
  this.polls_table = $(options.table);
  this.secret_key = options.secret_key;
  this.init_polls();
}


TrusteeDecrypt.prototype = {

  init_polls: function() {
    var polls = this.polls = {};
    var self = this;
    this.polls_table.find('tr.poll').each(function(){
      var url = $(this).data('poll-url');
      var uuid = $(this).data('poll-uuid');
      var options = {
        'el': $(this),
        'post_url': url + '/post-decryptions',
        'get_url': url + '/encrypted-tally',
        'uuid': uuid,
        'secret_key': self.secret_key
      }
      var poll = new Poll(options);
      polls[uuid] = poll;
    })
  }
}


function initLayout() {
  $(".polls-list").hide();
  $("#sk-textarea").hide();
}

$(document).ready(function() {
    initLayout();

    try {
      $("#sk-file-input").fileReaderJS(secret_key_filereader_options);
    } catch (err) {
      console.error(err);
      $("#sk-textarea").show();
    }
    
    BigInt.setup(function() {
      $(window).bind("sk-loaded", function() {
          var secret_key = get_secret_key();
          if (!secret_key) { 
            alert("Invalid key");
          } else {
            $(".sk-form").hide();
            window.pollsView = new TrusteeDecrypt({
              table: '.polls-list',
              secret_key: secret_key
            });
            $(".polls-list").show();
          }
      });
      // DEBUG
      var secret_key = get_secret_key();
      if (secret_key) {

            $(".sk-form").hide();
            window.pollsView = new TrusteeDecrypt({
              table: '.polls-list',
              secret_key: secret_key
            });
            $(".polls-list").show();
      }
    });
});

function save_decryptions(name) {
    try {
      var filetype = "text/plain;charset=utf-8";
      var data = $("#result_textarea").val();

      if (!data) { 
          alert("Το περιεχόμενο της αποκρυπτογράφησης είναι κενό");
          return false;
      }

      bb = new BlobBuilder;
      bb.append(data);
      saveAs(bb.getBlob(filetype), name);
      } catch (err) {
        UTILS.open_window_with_content(data, "application/json");
      }
    return false;
}

var BATCH_SIZE = 5;
var TOTAL_VOTES = 0;

function decrypt_and_prove_tally(tally, public_key, secret_key, callback) {
    // we need to keep track of the values of g^{voter_num} for decryption
    var DISCRETE_LOGS = {};
    var CURRENT_EXP = 0;
    var CURRENT_RESULT = BigInt.ONE;
    DISCRETE_LOGS[CURRENT_RESULT.toString()] = CURRENT_EXP;
    
    // go through the num_tallied
    while (CURRENT_EXP < tally.num_tallied) {
      CURRENT_EXP += 1;
      CURRENT_RESULT = CURRENT_RESULT.multiply(public_key.g).mod(public_key.p);
      DISCRETE_LOGS[CURRENT_RESULT.toString()] = CURRENT_EXP;      
    }
    
    // initialize the arrays
    var decryption_factors= [[]];
    var decryption_proofs= [[]];
    
    function update_progress() {
        var met = $(".progress .meter");
        var perc = (100 * computed) / tally.num_tallied;
    }

    var computed = 0;
    var computed_perc = 0;

    var batches = [];
    var batch_med_time = 0;
    var batches_completed = 0;
    window.TOTAL_VOTES = tally.num_tallied;

    _.each(_.range(tally.num_tallied/BATCH_SIZE), function(i){
        var from, to, batch;
        from = i * BATCH_SIZE;
        to = from + BATCH_SIZE;
        if (to >= tally.num_tallied) {
            to = tally.num_tallied;
        }
        batch = tally.tally[0].slice(from, to);
        if (batch.length) {
            batches.push(batch); 
        }
      });

    var batches_count = batches.length;
    var remaining = 0;
    var choice_num = 0;
    
    function _decrypt(from, to) {
        var dbatch = batches.pop();
        var time = new Date
        
        if (!dbatch) {
            callback({
                'decryption_factors': decryption_factors,
                'decryption_proofs': decryption_proofs
              });
            return;
        }
        $(dbatch).each(function(index, q_tally) {
          $(q_tally).each(function(choice_tally_index, choice_tally) {
              var choice_tally = tally.tally[0][choice_num];
                var one_choice_result = secret_key.decryptionFactorAndProof(choice_tally, 
                                                ElGamal.fiatshamir_challenge_generator);
               decryption_factors[0][choice_num] = one_choice_result.decryption_factor
               decryption_proofs[0][choice_num] = one_choice_result.decryption_proof;
               choice_num++;
           });
       });

       batch_time = new Date - time;
       batches_completed++;
       batch_med_time = (batch_med_time + batch_time) / 2;
       time_remaining = batch_med_time * (batches_count - batches_completed + 1);
       var percentage_done = (100*batches_completed) / batches_count
       batch_complete_callback(dbatch, batches_completed, batch_time, 
                               batch_med_time, time_remaining, 
                               batches_count, percentage_done);
        return;
       window.setTimeout(_decrypt, 100);
        
    };
    
    function _init_worker(id, callback) {
      var worker = new window.Worker(TRUSTEE.worker + '?' + (new Date()).getTime());
      worker.onmessage = function(event) {
        if (event && event.data && event.data.type == "result") {
          var result = event.data.result;
          var index = result.index;
          var proof = ElGamal.Proof.fromJSONObject(result.proof);
          var factor = new BigInt(result.factor, 10);
          decryption_factors[0][index] = factor;
          decryption_proofs[0][index] = proof;
          _worker_decrypt(worker, id);
          callback(result.time);
          //console.log("WORKER", id, "decrypted", index,".", decryption_factors[0].length, "decrypted so far", );
        } 
      }
      return worker;
    }
    
    var pending_indexes = [];
    
    function _check_workers_finished() {
      var interval = undefined;
      var check = function() {
        if (pending_indexes.length == 0){
          if (decryption_factors[0].length == tally.tally[0].length &&
              decryption_proofs[0].length == tally.tally[0].length) {
              callback({
                  'decryption_factors': decryption_factors,
                  'decryption_proofs': decryption_proofs
                });
              window.clearInterval(interval);
              return;
          }
        }
      }
      interval = window.setInterval(check, 2000);
    }
    
    var _sk = secret_key.toJSONObject();
    function _worker_decrypt(worker, id) {
        var index = pending_indexes.pop();
        if (!tally.tally[0][index]) {
            return;
        }
        //console.log("WORKER", id,  "POST", index);
      worker.postMessage({
        'type': 'decrypt',
        'sk' : _sk,
        'choice' : tally.tally[0][index].toJSONObject(),
        'index': index
      });

      window.setTimeout(function() {
        if (!decryption_factors[0][index] || !decryption_proofs[0][index]) {
            if (!tally.tally[0][index]) { return }
           // console.log("INDEX", index, "TIMED OUT");
          pending_indexes.push(index);
          _worker_decrypt(worker, id);
        }
      }, 80000);
    }

  
   var tally_size = tally.tally[0].length;
   if (window.Worker) {
      var batch_med_time = 0;
      var time_remaining = 0;
      var _worker_stats_callback = function(time) {
        if (batch_med_time == 0) { 
          batch_med_time = time;
        } else { 
          batch_med_time = (batch_med_time + time) / 2;
        };
        var completed = tally_size - pending_indexes.length;
        if (pending_indexes.length % 10 == 0 || time_remaining == 0) {
            time_remaining = (pending_indexes.length * batch_med_time) / decryptionWorkersCount;
        }
        var percentage_done = (100*completed) / tally_size;
        batch_complete_callback([], completed, time, batch_med_time, time_remaining,
                               tally_size, percentage_done)
      }

      var pending_indexes = _.range(tally.tally[0].length);
      BATCH_SIZE = 1;
      pending_indexes.reverse();
      _check_workers_finished();
      _.map(_.range(decryptionWorkersCount), function(ri,i) {
        var worker = _init_worker(i, _worker_stats_callback);
        _worker_decrypt(worker, i);
      });
   } else {
     window.setTimeout(_decrypt, 100);
   }
}


function batch_complete_callback(batch, batch_index, time, median_time, 
                                 time_remaining, total_batches, percentage) {
    //console.log("BATCH", batch_index, " of ", total_batches, 
                //" finished in ", time/1000, "seconds. Approx. time:", 
                //time_remaining, " Percentage:", percentage);
    
    if (batch_index > 3) {
      $(".progress-message").show();
    }
    $(".progress .meter").css({'width': percentage + '%'});

    var time_msg = parseInt(time_remaining/1000) + " δευτερόλεπτα.";
    if (time_remaining/1000 > 120) {
      time_msg = parseInt(time_remaining/1000/60) + " λεπτά.";
  }

  time_msg += " (" + batch_index*BATCH_SIZE + "/" + TOTAL_VOTES + ")";

    $(".progress-message .time").text(time_msg);
}


function get_secret_key() {
    try {
      return ElGamal.SecretKey.fromJSONObject(
          $.secureEvalJSON($('#sk-textarea').val()));
    } catch (err) {
        console.error(err);
        return undefined;
    }
}


function do_tally() {
  $('#sk_section').hide();
  $('#waiting_div').show();

  $(".progress").show();
  $(".progress .meter").width(10);
  
  var secret_key = get_secret_key();
  if (!secret_key) { alert("Secret key error") }

  function callback(factors_and_proof) {

      $(".progress-message").hide();
      $(".progress-message .time").text("");

      // json'ify it
      var factors = factors_and_proof.decryption_factors
      var decryption_proofs = $(factors_and_proof.decryption_proofs).map(function(i, q_proof) {
          return $(q_proof).map(function(j, a_proof){
             return a_proof.toJSONObject(); 
          });
      });
      
      var factors_and_proofs = {'decryption_factors': factors, 'decryption_proofs': decryption_proofs};
      var factors_and_proofs_json = $.toJSON(factors_and_proofs);
      
      // clear stuff
      secret_key = null;
      $('#sk_textarea').val("");
      
      // display the result in a text area.
      $('#waiting_div').hide();
      
      $('#result_textarea').val(factors_and_proofs_json);
      $('#result_div').show();
      $('#first-step-success').show();
  }

  decrypt_and_prove_tally(TALLY, ELECTION_PK, secret_key, callback);
}

function submit_result() {
  $('#result_div').hide();
  $('#waiting_submit_div').show();

  var result = $('#result_textarea').val();
  
  // do the post
  $.ajax({
      type: 'POST',
      url: "./upload-decryption",
      timeout: 300000,
      data: {'factors_and_proofs': result},
      success: function(result) {
        $('#waiting_submit_div').hide();
        if (result != "FAILURE") {
          $('#done_div').show();
        } else {
          alert('Η επαλήθευση απέτυχε. Πιθανώς δώσατε εσφαλμένο Κωδικό.');
          reset();
        }
      },
      error: function(error) {
          $('#waiting_submit_div').hide();
          $('#error_div').show();
      }
  });
}

function skip_to_second_step() {
  $('#sk_section').hide();
  $('#result_div').show();
  $('#result_textarea').html('');
  $('#skip_to_second_step_instructions').hide();
}

function reset() {
  $('#result_div').hide();
  $('#skip_to_second_step_instructions').show();
  $('#sk_section').show();
  $('#result_textarea').html('');
  $('#first-step-success').hide();
}

var secret_key_filereader_options = {
    dragClass: "drag",
    accept: false,
    readAsMap: {
        'text/*' : 'Text'
    },
    readAsDefault: 'Text',
    on: {
        load: function(e, file) {
            // Native ProgressEvent
            if (e.srcElement && e.srcElement.result) {
                $("textarea#sk-textarea").val(e.srcElement.result);
            } else if (e.currentTarget && e.currentTarget.result) {
                $("textarea#sk-textarea").val(e.currentTarget.result);
            } else {
                $("textarea#sk-textarea").show();
            }
            $(window).trigger("sk-loaded")
        },
    }
};

var stored_decryption_filereader_options = {
    dragClass: "drag",
    accept: false,
    readAsMap: {
        'text/*' : 'Text'
    },
    readAsDefault: 'Text',
    on: {
        beforestart: function() {
            $(".local_loading").show();
        },
        load: function(e, file) {
            $(".local_loading").hide();
            // Native ProgressEvent
            if (e.srcElement && e.srcElement.result) {
              $("textarea#result_textarea").val(e.srcElement.result);
            } else if (e.currentTarget && e.currentTarget.result) {
              $("textarea#result_textarea").val(e.currentTarget.result);
            } else {
              $("textarea#result_textarea").show();
            }

        },
    }
};

function show_decrypt_results() {
    $("textarea#result_textarea").toggle();
}

//$(document).ready(function(){
    //try {
        //$("#stored-decryption-input").fileReaderJS(get_stored_decryption_opts);
    //} catch (err) {
        //console.log(err);
    //}
//})
