export const question_markup = (question_num) =>  
`
<form onsubmit="return false;" class="prettyform" id="answer_form">
<input type="hidden" name="question_num" value=${question_num} />

<p>
<br /> 
<b>${BOOTH.election.questions[question_num].question}</b>
<br />

<span style="font-size: 0.6em;">#${question_num + 1} of ${BOOTH.election.questions.length} &mdash;
 vote for 
${`${BOOTH.election.questions[question_num].min} && (${BOOTH.election.questions[question_num].min} > 0)` ? 

    `${BOOTH.election.questions[question_num].max}` ? 
      `${BOOTH.election.questions[question_num].min} to ${BOOTH.election.questions[question_num].max}`
      : `at least ${BOOTH.election.questions[question_num].min} `

: 
    `${BOOTH.election.questions[question_num].max}` ? 
      `(${BOOTH.election.questions[question_num].max} > 1) up to ${BOOTH.election.questions[question_num].max}`
      : `as many as you approve of`
}

</span>
</p>

${BOOTH.election.questions[question_num].answers.map(
(answer, index) => 
`
  <div id="answer_label_${question_num}_${BOOTH.election.question_answer_orderings[question_num][index]}">
  <input type="checkbox" class="ballot_answer" id="answer_${question_num}_${BOOTH.election.question_answer_orderings[question_num][index]}" name="answer_${question_num}_${BOOTH.election.question_answer_orderings[question_num][index]}" value="yes" onclick='BOOTH.click_checkbox(${question_num}, ${BOOTH.election.question_answer_orderings[question_num][index]}, this.checked);'/>

  <label class="answer" for="answer_${question_num}_${BOOTH.election.question_answer_orderings[question_num][index]}">
    ${BOOTH.election.questions[question_num].answers[BOOTH.election.question_answer_orderings[question_num][index]]}

    ${question.answer_urls && question.answer_urls[BOOTH.election.question_answer_orderings[question_num][index]] && question.answer_urls[BOOTH.election.question_answer_orderings[question_num][index]] != ""}
      &nbsp;&nbsp;
      <span style="font-size: 12pt;">
        [<a target="_blank" href="${question.answer_urls[BOOTH.election.question_answer_orderings[question_num][index]]}" rel="noopener noreferrer">more info</a>]
      </span>

  </label>
</div> 
`
).join('')}


<div id="warning_box" style="color: green; text-align:center; font-size: 0.8em; padding-top:10px; padding-bottom: 10px; height:50px;">
</div>

${BOOTH.all_questions_seen ? 
`<div style="float: right;">
<input type="button" onclick="BOOTH.validate_and_confirm(${question_num});" value="Proceed" />
</div>
`
: '' } 

${question_num != 0 ? 
`<input type="button" onclick="BOOTH.previous(${question_num})" value="Previous" />
&nbsp;
`
: ''}

${question_num < BOOTH.election.questions.length - 1 ?
`<input type="button" onclick="BOOTH.next(${question_num})" value="Next" />
&nbsp;
`
: ''}

<br clear="both" />

</form>
`;




