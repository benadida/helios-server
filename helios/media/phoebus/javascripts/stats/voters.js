(function() {
var VoterStats = function (data, cont_width, cont_height, margin) {
  
  var svg = undefined;
  var svg_el = undefined;

  var cont_width = cont_width || 960;
  var cont_height = cont_height || 500;

  var margin = margin || {top: 20, right: 40, bottom: 30, left: 50};
  var width = cont_width - margin.left - margin.right;
  var height = cont_height - margin.top - margin.bottom;

  /* x location of pop-up tooltip. */
  var tooltipX = 100;

  /* y location of pop-up tooltip. */
  var tooltipY = 100;

  /* Default parse date format. */
  var dateFormat = d3.time.format("%Y-%m-%dT%H:%M:%S");

  /*
   * Return a Date object from a string formatted as 012-11-12T09:09:59.244303
   * with the milliseconds being optional; precision is at the seconds level
   * so the milliseconds part is ignored if present.
   * 
   */
  function parseDate(d) {
      var dateAtSeconds = d.replace(/\.\d+$/, "");
      return dateFormat.parse(dateAtSeconds);
  }

  /*
   * x scale (time scale).
   */
  var x = d3.time.scale()
      .range([0, width]);

  /*
   * x bar scale (ordinal, each point a time interval.
   */
  var barX = d3.scale.ordinal();

  /*
   * y scale, the total number of votes cast at a given point in time.
   */
  var y = d3.scale.linear()
      .range([height, 0]);

  /*
   * y bar scale, the number of votes cast at a given time interval.
   */
  var barY = d3.scale.linear()
      .range([height, 0]);

  /*
   * x time axis at the bottom.
   */
  var xAxis = d3.svg.axis()
      .scale(x)
      .orient("bottom");

  /*
   * y total votes axis at the right.
   */
  var yAxis = d3.svg.axis()
      .scale(y)
      .orient("right");

  /*
   * y votes cast at time interval at the left.
   */
  var yBarAxis = d3.svg.axis()
      .scale(barY)
      .orient("left");

  /*
   * Total votes line.
   */
  var line = d3.svg.line()
      .interpolate("basis")
      .x(function(d) { return x(d.dateTime); })
      .y(function(d) { return y(d.total); });

  /*
   * Half width of the area around the total votes line that will be used
   * for making pointing ton the votes line easier.
   */

  var traceHalfWidth = 5;

  /*
   * Area around the total votes line. Used to make pointing on the votes line
   * easier.
   */
  var area = d3.svg.area()
      .x(function(d) { return x(d.dateTime); })
      .y0(function(d) { return y(d.total) - traceHalfWidth; })
      .y1(function(d) { return y(d.total) + traceHalfWidth; });

  /*
   * Show toolbar info when on a bar.
   */ 
  function showBarInfo(d, i, dateTimeStart, millisDiff, mousePos) {

      var intervalStart =
          new Date(dateTimeStart.getTime() + (i + 1) * millisDiff);

      svg.select("#svg-tooltip")
          .append("text")
          .attr("x", tooltipX)
          .attr("y", tooltipY)
          .text(intervalStart + ": " + d);
  }

  /*
   * Hide toolbar info.
   */
  function hideTooltipInfo(d, mousePos) { 
          svg.select("#svg-tooltip").text("");
          svg.select("#line-trace circle").remove();
  }

  /*
   * Show toolbar info when on the votes line.
   */
  function showLineInfo(d, mousePos) {

      svg.select("#svg-tooltip").text("");
      svg.select("#line-trace circle").remove();
      
      svg.select("#line-trace")
          .append("circle")
          .attr("cx", mousePos[0])
          .attr("cy", mousePos[1])
          .attr("r", 5)

      var xIndex = 0;
      var dateTime = x.invert(mousePos[0]);
      for (var i = 0; i < d.length; i++) {
          if (d[i].dateTime.getTime() >= dateTime.getTime()) {
              xIndex = i;
              break;
          }
      }
      svg.select("#svg-tooltip")
          .append("text")
          .attr("x", tooltipX)
          .attr("y", tooltipY)
          .text(x.invert(mousePos[0]) + ": " + d[xIndex].total);

  }
  
  svg_el = d3.select("body").append("svg");
  svg = svg_el.attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  /*
   * Collect the votes cast at each specific time point.
   */
  var previousVoteDateTime =
      parseDate(data.votes[data.votes.length - 1].date);
  var votes = [{
      cast: 0,
      total: 0,
      dateTime: previousVoteDateTime
  }];
  /* Voters we have encountered so far. */
  var voters = {};
  for (var i = data.votes.length - 1, j = 0; i >= 0; i--) {
      var currentVoteDateTime = parseDate(data.votes[i].date);
      if (currentVoteDateTime.getTime() == previousVoteDateTime.getTime()) {
          votes[j].cast++;
      } else {
          previousVoteDateTime = currentVoteDateTime;
          votes[++j] = {
              cast: 1,
              total: votes[j - 1].total,
              dateTime: currentVoteDateTime
          };
      }
      var voter = data.votes[i].name;
      if (!voters[voter]) {
          votes[j].total++;
          voters[voter] = 1;
      } else {
          voters[voter]++;
      }
  }

  /*
   * Collect votes cast per intervals.
   */
  var dateTimeStart = parseDate(data.election[0].voting_started_at);
  var dateTimeEnd = votes[votes.length - 1].dateTime;
  var minutesDiff = 5;
  var millisDiff = minutesDiff * 60000;
  var numIntervals =
      Math.floor((dateTimeEnd - dateTimeStart) / millisDiff) + 1;
  var dateTimeLimit = new Date(2012, 10, 12, 9, 0 + minutesDiff);
  var intervals = new Array(numIntervals);
  for (var i = 0; i < numIntervals; i++) {
      intervals[i] = 0;
  }
  for (var i = 0; i < votes.length; i++) {
      var interval =
          Math.floor((votes[i].dateTime - dateTimeStart) / millisDiff);
      intervals[interval] = intervals[interval] + votes[i].cast;
  }

  /*
   * Set range and domains.
   */
  x.domain(d3.extent(votes, function(d) { return d.dateTime; }));
  var start = 0;
  var stop = width;
  var step = (stop - start) / (intervals.length);
  var range = d3.range(intervals.length).map(function(i) {
      return start + step * i;
  });
  barX.domain(d3.range(intervals.length));
  barX.rangePoints(d3.extent(range), 5);
  
  y.domain([0, data.election[0].voters_count]);
  barY.domain([0, d3.max(intervals, function(d) { return d; })]);
      
  var xAxisSVG = svg.append("g");
  
  xAxisSVG.attr("class", "x axis")
      .attr("transform", "translate(0," + height + ")")
      .call(xAxis)
      .append("text")
      .attr("y", 30)
      .style("text-anchor", "start")
      .text(parseDate(data.election[0].voting_started_at));
  
  xAxisSVG.append("text")
      .attr("y", 30)
      .attr("dx", width)
      .style("text-anchor", "end")
      .text("Last vote: " + x.domain()[1]);

  svg.append("g")
      .attr("class", "y axis")    
      .call(yBarAxis)
      .append("text")
      .attr("dx", "2em")
      .attr("transform", "rotate(-90)")
      .attr("y", -36)
      .attr("dy", ".71em")
      .style("text-anchor", "end")
      .text("Votes at " + minutesDiff + "' interval");
  
  svg.append("g")
      .attr("class", "y axis")
      .attr("transform", "translate(" + width + ")")
      .call(yAxis)
      .append("text")
      .attr("y", 6)
      .attr("dy", "-0.7em")
      .attr("dx", "-1em")
      .style("text-anchor", "end")
      .text("Voters (" + data.election[0].cast_count
            + "/" + data.election[0].voters_count +")");

  svg.selectAll(".bar")
      .data(intervals)
      .enter().append("rect")
      .attr("class", "bar")
      .attr("x", function(d, i) { return barX(i); })
      .attr("width", step)
      .attr("y", function(d) {
          return barY(d); })
      .attr("height", function(d) { return height - barY(d); })
      .on("mouseover", function(d, i) {
          d3.select(this).classed("active", true);
          showBarInfo(d, i, dateTimeStart, millisDiff, d3.mouse(this)); } )
      .on("mouseout", function(d) {
          d3.select(this).classed("active", false);
          hideTooltipInfo(d, d3.mouse(this));
      });

  svg.append("path")
      .datum(votes)
      .attr("class", "line")
      .attr("d", line);

  svg.append("path")
      .attr("class", "trace-area");

  svg.select("path.trace-area")
      .data([votes])
      .attr("d", area)
      .on("mousemove", function(d) {
          showLineInfo(d, d3.mouse(this)); } )
      .on("mouseout", function(d) { hideTooltipInfo(d, d3.mouse(this)); } );

  /* SVG element for the tooltip. */
  svg.append("g")
      .attr("id", "svg-tooltip")
      .attr("class", "svg-tooltip");

  /* SVG element for the line trace circle */
  svg.append("g")
      .attr("id", "line-trace")
      .attr("class", "line-trace");

  return svg_el[0];

};



window.STATS = window.STATS || {};
window.STATS['voters'] = {'title': 'Ιστορικό ψήφων', 'graph': VoterStats, 'css': 'voters.css'};

})();
