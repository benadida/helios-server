$(document).ready(function() {

  // update election status and admin actions interval
  window.ELECTION_ACTIONS_INTERVAL_SET = window.ELECTION_ACTIONS_INTERVAL_SET || false;
  if ($(".election-actions").length && !window.ELECTION_ACTIONS_INTERVAL_SET) {
    window.ELECTION_ACTIONS_INTERVAL_SET = true;
    function updateElectionActions() {
      $.get(window.location.toString(), function(data) {
        if (window.DISABLE_ELECTION_ACTIONS_INTERVAL) { return }
        var current_status = $(".election-actions").data("status");
        var new_status = $(data).find(".election-actions").data("status");
        if (current_status == new_status) { return }

        var actions = $(data).find(".election-actions");
        var reveals = $(data).find(".reveals");
        if (actions.length) {
          $(".election-actions").replaceWith(actions);
        }
        if (reveals.length) {
          $("#reveals").replaceWith(reveals);
        } 
      });
    }
    var interval = window.setInterval(function() {
      updateElectionActions();
    }, 3000);
  }

  // update polls details
  
});
