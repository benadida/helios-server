// Take the difference between one array and a number of other arrays.
// Only the elements present in just the first array will remain.
_.difference = function(array) {
  var rest = Array.prototype.concat.apply(Array.prototype, Array.prototype.slice.call(arguments, 1));
  return _.filter(array, function(value){ return !_.contains(rest, value); });
};

var BM = {};

BM.get_module = function(m) {
  return BM.registry[m];
}

BM.ModuleBase = {
  _init: function(election) {
    this.election = election;
    this.data = election.questions_data;
    this.el = {};
    this.ranked = false;
  },

  init_events: function () {
    $(".stv-choice a.enabled").live('click', _.bind(this.handle_choice_click, this));
    $(".stv-choice a.selected").live('click', _.bind(this.handle_selected_click, this));
    $(".stv-choice a.disabled").live('click', function(e){e.preventDefault()});
    if (this.post_init_events) { this.post_init_events() }
  },
  
  update_submit_value: function() {
    var choices = this.get_answer();
    if (choices.length == 0) {
      this.el.submit.val("Λευκό");
    } else {
      this.el.submit.val("Συνέχεια");
    }
  },

  show: function() {
    this.el.answer = $("#stv_answer");
    this.el.answers = $("li.stv-choice a");
    this.el.submit = $("#submit-stv");
    var ans = this.get_answer();
    var self = this;
    _.each(ans, function(choice){
      self.select_answer(choice);
    });
    this.check_disable_questions();
    this.update_submit_value();
    if (this.post_show) { this.post_show() }
  },
  
  handle_selected_click: function(e) {
    e.preventDefault();
    var el = $(e.target).closest("a");
    var choice = parseInt(el.data('absolute-index'));
    var question = parseInt(el.data('question'));
    this.remove_choice(choice);
    this.check_disable_question(question);
    this.update_layout();
    return;
  },

  handle_choice_click: function(e) {
    e.preventDefault();
    var el = $(e.target).closest("a");
    var choice = parseInt(el.data('absolute-index'));
    var question = parseInt(el.data('question'));
    var max = this.data[question].max_answers;
    if (this.choice_voted(choice)) { return };
    if (this.can_add(choice, question)) {
      this.add_choice(parseInt(choice));
    }
    this.check_disable_question(question);
    this.update_layout();
    return;
  },

  add_choice: function(choice) {
    var value = this.el.answer.val();
    if (value == "") {
      this.el.answer.val(choice);
    } else {
      this.el.answer.val(value + "," + choice);
    }
    this.select_answer(choice);
    this.sort_answer();
  },

  remove_choice: function(choice) {
    choice = parseInt(choice);
    var choices = this.get_answer();
    this.set_answer(_.without(choices, choice));
    this.enable_answer(choice);
    this.sort_answer();
  },
  
  check_disable_questions: function() {
    var self = this;
    _.each(this.data, function(q,i){
      self.check_disable_question(i);
    })
  }, 

  check_disable_question: function(q) {
    var max = this.data[q].max_answers;
    var self = this;
    if (this.get_questions_answers()[q].length >= max) {
      this.el.answers.filter("[data-question="+q+"]").filter('.enabled').each(function(i, el){
        self.disable_answer($(el).data('absolute-index'));
      });
    } else {
      this.el.answers.filter("[data-question="+q+"]").filter('.disabled').each(function(i, el){
        self.enable_answer($(el).data('absolute-index'));
      });

    }
  },

  get_answer: function() {
    var value = this.get_answer_value();
    if (value == "") { return [] }
    return _.map(this.get_answer_value().split(","), function(i){
      return parseInt(i);
    });
  },

  set_answer: function(choices) {
    this.el.answer.val(choices.join(","));
    this.update_submit_value();
  },

  sort_answer: function() {
    if (this.ranked) { return }
    var answer = this.get_answer();
    answer.sort(function(a,b){return a-b});
    this.set_answer(answer);
  },

  get_answer_value: function() {
    return $.trim(this.el.answer.val());
  },

  choice_voted: function(choice) {
    return _.contains(this.get_answer(), parseInt(choice));
  },

  get_answer_el: function(choice) {
    return this.el.answers.filter('[data-absolute-index='+choice+']');
  },

  disable_question: function() {
  },

  enable_question: function() {
  },

  disable_answer: function(choice) {
    this.get_answer_el(choice).removeClass().addClass('secondary button small disabled');
  },

  enable_answer: function(choice) {
    this.get_answer_el(choice).removeClass().addClass('button small enabled');
  },
  
  select_answer: function(choice) {
    this.get_answer_el(choice).removeClass().addClass('success button small selected');
  },
  
  get_answers_map: function() {
    var map = {};
    _.each(this.data, function(q, i) {
      _.each(_.range(q.answers_index, q.answers_index + q.answers.length), function(j) {
        map[j] = i;
      });
    });
    return map;
  },

  get_questions_answers: function(q) {
    var answers = _.map(this.data, function(){ return []});
    var qmaps = this.get_answers_map();
    _.each(this.get_answer(), function(ans) {
      answers[qmaps[ans]].push(ans);
    });
    return answers;
  },

  validate: function() {
    var answers = this.get_questions_answers();
    var ret = true;
    var self = this;
    _.each(answers, function(ans_list, q) {

      var data = self.data[q];
      if (ans_list.length && ans_list.length > parseInt(self.data[q]['max_answers'])) {
        ret = this.election.module_params.max_limit_error.format(data.question, data.max_answers);
      }
      if (ans_list.length && ans_list.length < parseInt(self.data[q]['min_answers'])) {
        var q = self.data[q];
        ret = this.election.module_params.min_limit_error.format(data.question, data.min_answers);
      }
    }, this);
    
    if (ret !== true) {
      return ret;
    }
    if (this.post_validate){
      return this.post_validate();
    }
    return ret;
  }

}


BM.PartiesElection = function(election) {
  this._init(election);
}

_.extend(BM.PartiesElection.prototype,
BM.ModuleBase,
{
  tpl: 'question_parties',

  can_add: function(choice, question) {
    if (!_.contains(this.party_choices, choice)) {
      this.remove_choice(this.party_choices[this.selected_party()]);
    };
    var max = this.data[question]['max_answers'];
    if (this.get_questions_answers()[question].length >= max) {
      return false;
    }
    return true;
  },
  
  selected_party: function(raise) {
    var parties = this.get_questions_answers();
    var party = undefined;
    _.each(parties, function(p, i){
      if (p.length > 0) {
        if (party !== undefined && raise) { 
          throw "Invalid party selection"; 
        }
        party = i;
      }
    });
    return party;
  },
  
  selected_party_choice: function() {
    return this.party_choices[this.selected_party()];
  },

  post_show: function() {
    this.party_choices = _.map(this.data, function(q){return q.answers_index});
    $(".stv-choices").hide();
    $(".stv-candidates").removeClass("five").addClass("twelve");
    this.update_layout();
  },
 
  fix_parties_styles: function() {
      this.el.answers.filter("[data-is-party='yes']").removeClass("small").addClass("medium");
      this.el.answers.filter(".selected[data-is-party='yes']").addClass("party");
      this.el.answers.filter(".selected[data-is-party='yes']").removeClass("small").addClass("chosen");

      if (this.selected_party() !== undefined) {
        this.el.answers.filter("[data-is-party='yes'][data-question="+this.selected_party()+"]").addClass("chosen-party").removeClass("disabled").removeClass("secondary").removeClass("enabled");
      }
  },

  fix_parties: function() {
      var p = this.selected_party();
      var self = this;
      if (p !== undefined) {
        _.each(this.data, function(q,i) {
          if (i != p) {
            _.each(_.range(q.answers.length), function(ind){
              self.disable_answer(ind+q.answers_index);
            });
          }
        })
      } else {
        this.reset_answers();
      }
  },
  
  fix_party_vote: function() {
    var answer = this.get_answer();
    var self = this;
    if (_.contains(this.get_answer(), this.party_choices[this.selected_party()]) && answer.length == 1) {
      this.el.answers.filter("[data-is-candidate='yes'][data-question="+this.selected_party()+"]").each(function(e){
        self.enable_answer($(this).data('absolute-index'));
      });
    }
  },

  reset_answers: function() {
      var self = this;
      this.el.answers.filter("[data-is-candidate='yes']").each(function(e){
        self.disable_answer($(this).data('absolute-index'));
      });
      this.el.answers.filter("[data-is-party='yes']").each(function(e){
        self.enable_answer($(this).data('absolute-index'));
      });
  },

  update_layout: function() {
    var self = this;
    this.fix_parties();
    this.fix_parties_styles();
    this.fix_party_vote();
  },
  
  reset: function() {
    this.set_answer([]);
  },

  post_init_events: function() {
    $(".stv-candidates").removeClass("five").addClass("twelve");
    var self = this;
    $(".chosen-party").live('click', function(e) {
      e.preventDefault();
      self.reset();
      self.update_layout();
    });
  },

  post_validate: function() {
    try {
      var p = this.selected_party(1);
    } catch (err) {
      return "Invalid party selection";
    }
    return true;
  }
  
});


BM.SimpleElection = function(election) {
  this._init(election);
}

_.extend(BM.SimpleElection.prototype,
BM.ModuleBase,
{
  tpl: 'question_plain',
  can_add: function(choice, question) {
    var max = this.data[question]['max_answers'];
    if (this.get_questions_answers()[question].length >= max) {
      return false;
    }
    return true;
  },
  
  post_init_events: function() {
    $(".stv-candidates").removeClass("five").addClass("twelve");
  },

  post_show: function() {
    $(".stv-choices").hide();
    $(".stv-candidates").removeClass("five").addClass("twelve");
    this.update_layout();
  },
  
  reset: function() {
    $(".stv-choice a").removeClass().addClass("button small enabled");
  },

  update_layout: function() {
  }
});


BM.ScoreElection = function(election) {

  this._init(election);

  // initalize score_map with empty questions
  this.score_map = {};
  _.each(this.data, function(q, qindex) {
    this.score_map[qindex] = {};
    _.each(q.answers, function(a, aindex) {
      this.score_map[qindex][aindex] = undefined;
    }, this);
  }, this);
  
  var answers = election.questions[0].answers;
  var pos = 0;
  this.scores_indexes = _.map(this.data, function(q, i) {
    var scores = {};
    _.each(q.scores, function(s) {
      scores[s] = _.indexOf(answers, ''+(parseInt(s)+100*i)) ;
    });
    return scores;
  });

  this.answers_indexes = _.map(this.data, function(q, i) {
    var _answers = {};
    _.each(q.answers, function(s) {
      _answers[s] = _.indexOf(answers, q.question + ": " + s);
    });
    return _answers;
  });
}

_.extend(BM.ScoreElection.prototype,
BM.ModuleBase,
{
  tpl: 'question_score',
  
  get_answers_map: function() {
    var map = {};
    _.each(this.answers_indexes, function(indexes, i) {
      _.each(indexes, function(i) {
        map[i] = i;
      });
    });
    return map;
  },
  
  remaining_scores: function() {
    return _.map(this.data, function(q, i) {
      var remaining = [];
      var scores_chosen = _.filter(_.values(this.score_map[i]), function(s) { return s });
      scores_chosen = _.map(scores_chosen, function(s) { return s+"" });
      var scores = q.scores;
      remaining = _.difference(scores, scores_chosen).join(",");
      return remaining;
    }, this);
  },

  all_scores_chosen: function() {
    return _.filter(this.remaining_scores(), function(i) { return i.length > 0 }).length === 0;
  },

  validate: function() {
    if (!this.all_scores_chosen() && this.election.module_params.all_scores_required) {
      var remaining = this.remaining_scores()[0];
      return this.election.module_params.invalid_scores_selection.format(remaining);
    }
    return true;
  },

  update_submit_value: function() {
    var choices = this.get_answer();
    if (choices.length == 0) {
      this.el.submit.val("Λευκό");
    } else {
      this.el.submit.val("Συνέχεια");
    }
    if (!this.all_scores_chosen() && this.get_answer().length > 0) {
      this.el.submit.addClass("disabled").removeClass("success");
    } else {
      this.el.submit.removeClass("disabled").addClass("success");
    }
  },

  post_init_events: function() {
    $(".stv-candidates").removeClass("five").addClass("twelve");
  },

  post_show: function() {
    $(".stv-choices").hide();
    $(".stv-candidates").removeClass("five").addClass("twelve");
    this.update_layout();
  },
  
  reset: function() {
    $(".stv-choice a").removeClass().addClass("button small enabled");
  },

  update_layout: function() {
    _.each(this.score_map, function(q, index) { this.update_question(index) }, this);
    this._update_answer();
  },

  _update_answer: function() {
    var _answers = [];
    _.each(this.score_map, function(answers, qindex) {
      _.each(answers, function(score, aindex) {
        if (score !== undefined) {
          var answer = this.data[parseInt(qindex)].answers[parseInt(aindex)];
          var answer_index = this.answers_indexes[qindex][answer];
          var score_index = this.scores_indexes[qindex][score];
          if (answer_index >= 0 && score_index >= 0 ) {
            _answers.push(answer_index);
            _answers.push(score_index);
          }
        }
      }, this);
    }, this);
  
    var e_answers = this.election.questions[0].answers;

    var scores = [];
    _.each(_answers, function(index, i) {
      if (_.isNumber(parseInt(e_answers[index]))) {
        scores[parseInt(e_answers[index])] = [_answers[i-1], index];
      }
    });
    var keys = _.map(_.keys(scores), function(i) { return parseInt(i) });
    keys = keys.sort(function(a,b) { return parseInt(a) > parseInt(b)} ).reverse();
    
    var sorted_answers = _.flatten(_.map(keys, function(s) { return scores[s] }));
    this.set_answer(sorted_answers);
  },

  answer_els: function(qindex) {
    return $("#question-" + qindex).find(".score-answer")
  },

  update_question: function(qindex) {
    var available_scores = this.available_scores(qindex);
    _.each(this.score_map[qindex], function(score, index) {
      this.update_question_answer(qindex, parseInt(index), score, available_scores);
    }, this);
  },

  update_question_answer: function(qindex, ansindex, score, available) {
    var answer_el = $(this.answer_els(qindex).filter(".score-answer-"+(ansindex)));

    answer_el.find("input").attr("disabled", true).attr("checked", false);
    answer_el.find("label").addClass("disabled");

    _.each(available, function(s) {
      var input = answer_el.find("input[data-score="+s+"]");
      input.prev().removeClass("disabled");
      input.attr("disabled", false);
    });

    if (score !== undefined) {
      var score_input = answer_el.find("input[data-score="+score+"]");
      score_input.attr("disabled", false).attr("checked", true);
      score_input.prev().removeClass("disabled");
    }
  },

  question_scores: function(qindex) {
    return _.map(this.data[qindex].scores, function(s,i) { return parseInt(s) });
  },

  unavailable_scores: function(qindex) {
    var scores = this.question_scores(qindex);
    var available = scores;
    _.each(this.score_map[qindex], function(score) {
      available = _.without(available, score)
    });
    return available;
  },

  available_scores: function(qindex) {
    var scores = this.question_scores(qindex);
    var available = scores;
    _.each(this.score_map[qindex], function(score) {
      available = _.without(available, score)
    });
    return available;
  },

  handle_choice_click: function(e) {
    
    var score_el = $(e.target);
    if (score_el.prop("tagName") == "LABEL") {
      score_el = $(e.target).next();
    }
    if (score_el.is("disabled")) { return };
    
    var answer_el = score_el.prev().prev();
    var answer_index = parseInt(answer_el.data('relative-index'));
    var score = parseInt(answer_el.data('score'));
    var question = parseInt(answer_el.data('question'));
    var checked = score_el.attr("checked");

    if (checked) {
      this.handle_score_select(question, answer_index, score);
    } else {
      this.handle_score_deselect(question, answer_index, score);
    }
  },

  handle_score_select: function(question, answer, score) {
    // deselect score
    _.each(this.score_map[question], function(s, index) {
      if (score === s) {
        this.score_map[question][index] = undefined;
      }
    }, this);
    this.score_map[question][answer] = score;
    this.update_layout();
  },

  check_disable_question: function(q) {
    return;
  },

  handle_score_deselect: function(question, answer) {
    this.score_map[question][answer] = undefined;
    this.update_layout();
  },

  init_events: function () {
    $(".stv-choice input").live('click', _.bind(this.handle_choice_click, this));
    if (this.post_init_events) { this.post_init_events() }
  },

  pretty_choices: function(ballot) {
    var _choices = [];
    var choices = ballot.answers[0][0];
    _.each(this.data, function(q, qi) {
      _.each(q.answers, function(a, ai) {
        var ans_index = this.answers_indexes[qi][a];
        var chosen = _.indexOf(choices, ans_index);
        if (chosen >= 0) {
          var score_index = choices[chosen+1];
          var score = _.filter(_.keys(this.scores_indexes[qi]), function(key, score) { 
            return this.scores_indexes[qi][parseInt(key)] == score_index;
          }, this)[0];
          _choices.push(q.question + ": " + a + ": " + score);
        }
      }, this);
    }, this);

    return [_choices]
  },

  seal_tpl: 'seal_score.html'
});

BM.registry = {
  simple: BM.SimpleElection,
  parties: BM.PartiesElection,
  score: BM.ScoreElection,
  //ecounting: BM.EcountingElection
}

