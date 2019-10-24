export const question_markup = 
`
${QUESTIONS.map(
  (question, index) =>
  `
  <div id="q_view_${index}">
    <h4>
      ${
        `${ADMIN_P}` ?
        `
        [
          ${`${index} > 0 ` ? `<a href="javascript:question_move_up(${index});">^</a>]&nbsp;[` : ''}
          <a onclick="return confirm('Are you sure you want to remove this question?');" href="javascript:question_remove(${index})">x</a>] [<a href="javascript:question_edit(${index})">edit</a>] 
        `
          : `''`
      }
      ${index + 1}. ${question.question} (${question.choice_type}, select between ${question.min} and ${`${question.max != null}` ? `${question.max}` : `unlimited`} answers, result type ${question.result_type}.)
    </h4>
    <ul>
      ${question.answers.map(
        (answer, index) =>
        `
        <li> ${answer}
        ${`{question.answer_urls}[${index}]` ?
          `[<a target="_new" href="${question.answer_urls}[${index}]">more</a>]` : `''`
        }
        </li>
        `
      ).join('')}
    </ul>
  </div>
  <div id="q_edit_${index}" style="display:none;"> 
    <form id="question_edit_${index}_form" onsubmit="question_update(${index}, this); return false;" action="#">
      <p>
      <!--
        Type of Question:
        <select name="choice_type">
          <option selected>approval</option>
        </select>
      -->
      <input type="hidden" name="choice_type" value="approval" />
      <b>${index + 1}.</b> &nbsp;&nbsp;&nbsp;Select between &nbsp;&nbsp;
      <select name="min">
        <option selected>0</option>
        ${Array(20).fill().map( (item, idx) =>
          ` <option>${idx + 1}</option>`
          )}
      </select>

      &nbsp;&nbsp; and  &nbsp;&nbsp;

      <select name="max">
        <option>0</option>
        <option selected>1</option>

        ${Array(49).fill().map( (item, idx) =>
        ` <option>${idx + 2}</option>`
        )}

        <option value="">- (approval)</option>
      </select>

      &nbsp;&nbsp;
      answers.

      &nbsp;&nbsp;
      &nbsp;&nbsp;
      Result Type:&nbsp;
      <select name="result_type">
          <option selected>absolute</option>
          <option>relative</option>
      </select>

      </p>

      <table id="answer_table_${index}">
        <tbody>
          <tr><th colspan="2">Question:</th><td><input type="text" name="question" size="70" /></td></tr>
          <tr><th>&nbsp;</th><th>&nbsp;</th><th>&nbsp;</th></tr>
        </tbody>
        <tfoot>
          <tr><th colspan="2"></th><th><a href="javascript:add_answers(document.getElementById('answer_table_${index}'),5)">add 5 more answers</a></th></tr>
          <tr><td colspan="3"><input type="submit" value="update question" /> &nbsp; <input type="reset" value="cancel" onclick="question_edit_cancel(${index});" /></td></tr>
        </tfoot>

      </table>
    </form>
  </div>
`
).join('')}
${QUESTIONS.length == 0 ? `no questions yet` : ''}
${`${ADMIN_P} ` ?
`
  <h4>Add a Question:</h4>
  <form id="question_form" onsubmit="question_add(this); return false;" action="#">
    <p>
    <!--
      Type of Question:
      <select name="choice_type">
        <option selected>approval</option>
      </select>
    -->
    <input type="hidden" name="choice_type" value="approval" />
    &nbsp;&nbsp;&nbsp;Select between &nbsp;&nbsp;
    <select name="min">
        <option selected>0</option>
        ${Array(20).fill().map( (item, idx) =>
          ` <option>${idx + 1}</option>`
          )}
    </select>

    &nbsp;&nbsp; and  &nbsp;&nbsp;

    <select name="max">
        <option>0</option>
        <option selected>1</option>

        ${Array(49).fill().map( (item, idx) =>
        ` <option>${idx + 2}</option>`
        )}

        <option value="">- (approval)</option>
    </select>

    &nbsp;&nbsp;
    answers.

    &nbsp;&nbsp;
    &nbsp;&nbsp;
    Result Type:&nbsp;
    <select name="result_type">
        <option selected>absolute</option>
        <option>relative</option>
    </select>

    </p>

    <table id="answer_table" style="width:100%;">
      <tbody>
        <tr><th colspan="2">Question:</th><td><input type="text" name="question" size="70" /></td></tr>
        <tr><th>&nbsp;</th><th>&nbsp;</th><th>&nbsp;</th></tr>
      </tbody>
      <tfoot>
        <tr><th colspan="2"></th><th><a href="javascript:add_answers(document.getElementById('answer_table'), 5)">add 5 more answers</a></th></tr>
        <tr><td colspan="2"><input type="submit" value="add question" /></td></tr>
      </tfoot>

    </table>
  </form>
`
: `''` }
`;