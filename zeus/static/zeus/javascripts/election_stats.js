(function() {

var ZeusStats = function(uuid) {
  this.uuid = uuid || window.ELECTION || ELECTION;
  this.url = '/helios/elections/' + this.uuid + '/stats';
  this.election_data = {};
  this.votes_data = [];
  this.data = {};
}

ZeusStats.prototype.load = function (cb, eb, before) {
  var self = this;

  $.ajax({
    url: this.url,
    beforeSend: function() { if (before) { before() } },
    error: function() { if (eb) { eb(arguments) } },
    success: function(data) {
      self.election_data = data['election'][0];
      self.votes_data = data['votes'];
      self.results_data = data['results'][0];
      self.data = data;
      self.update_stats();
    }
  });
}

ZeusStats.prototype.update_stats = function() {
  var self = this;
  $.each(window.STATS, function(key, val){
    var graph_key = 'graph_' + key;
    var entry = '<h6>'+val.title+'</h6><div id="'+graph_key+'"></div>'
    var graph = val.graph(self.data, $(".election-public-stats").width(), 400);

    $(".stats").append(entry);
    $("#"+graph_key).append($(graph));

    if (val.css) {
      var css = $('<link rel="stylesheet" type="text/css" media="screen"' +
          'href="/static/helios/phoebus/javascripts/stats/'+val.css+'" />')
          $("head").append(css);
    }
  })
}

window.ZeusStats = ZeusStats;
})();
