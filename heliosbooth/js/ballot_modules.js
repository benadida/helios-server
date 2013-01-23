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

  show: function() {
    this.el.answer = $("#stv_answer");
    this.el.answers = $("li.stv-choice a");
    var ans = this.get_answer();
    var self = this;
    _.each(ans, function(choice){
      self.select_answer(choice);
    });
    this.check_disable_questions();
    if (this.post_show) { this.post_show() }
  },
  
  handle_selected_click: function(e) {
    e.preventDefault();
    var el = $(e.target);
    var choice = parseInt(el.data('absolute-index'));
    var question = parseInt(el.data('question'));
    this.remove_choice(choice);
    this.check_disable_question(question);
    this.update_layout();
    return;
  },

  handle_choice_click: function(e) {
    e.preventDefault();
    var el = $(e.target);
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
  },

  sort_answer: function() {
    if (this.ranked) { return }
    var answer = this.get_answer();
    answer.sort();
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
    _.each(answers, function(ans_list, q){
      if (ans_list.length > parseInt(self.data[q]['max_answers'])) {
        ret = "Invalid choice";
      }
    });
    
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


BM.registry = {
  election: BM.SimpleElection,
  election_parties: BM.PartiesElection,
  //ecounting: BM.EcountingElection
}

