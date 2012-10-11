;(function(){

  var TEXTS = {
    'PAGE_TITLE': 'Ηλεκτρονική κάλπη "Ζευς"'
  }
  
  var Content = function(data) {
    this.data = data;
  }

  Content.prototype.get = function(key) {
    return this.data[key];
  }
  
  var content = new Content(TEXTS);

  $.fn.extend({
    content: function(key) {
      return this.each(function(){
        $(this).text(content.get(key));
      })
    }
  })
})();
