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

  if (window.VOTERS_Q && window.VOTERS_Q.replace(/^\s+|\s+$/g, '') != "") {
    var form = $(document).find("form.action-form[action*=clear]");
    form.removeAttr('onsubmit');
    
    function handleEvent(e) {
      var c = confirm(VOTERS_Q_MSG);
      if (c) { return true }
      $("ul.show-dropdown").removeClass("show-dropdown");
      e.preventDefault();
      return false;
    }
    
    // voters list action confirm
    $(".voters-action").each(function(el) {
      var el = $(this);
      el.bind('click', function(e) {
        return handleEvent(e);
      });
    });

    form.find(".voters-action").unbind('click').removeAttr('onclick');
    form.find(".voters-action").bind('click', function(e) {
      if (handleEvent(e)){
        form.submit();
      }
    });
    
  }

});
