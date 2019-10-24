
export const seal_markup = 
`
${BOOTH.election_metadata.use_advanced_audit_features ?
    `
    <div style="float: right; background: lightyellow; margin-left: 20px; padding: 0px 10px 10px 10px; border: 1px solid #ddd; width:200px;">
    <h4><a onclick="document.getElementById('auditbody').setAttribute('style', 'display: block;')" href="#">Audit</a> <span style="font-size: 0.8em; color: #444">[optional]</span></h4>
    <div id="auditbody" style="display:none;">
    <p>
    If you choose, you can audit your ballot and reveal how your choices were encrypted.
    </p>
    <p>
    You will then be guided to re-encrypt your choices for final casting.
    </p>
    <input type="button" value="Verify Encryption" onclick="BOOTH.audit_ballot();" class="pretty" />
    </p>
    </div>
    </div>
    `
    : ``
}

<h3>Review your Ballot</h3>


<div style="padding: 10px; margin-bottom: 10px; background-color: #eee; border: 1px #ddd solid; max-width: 340px;">

${BOOTH.election.questions.map((question, index) =>
`
    <b>Question #${index + 1}: ${question.short_name}</b><br>
    ${BALLOT.pretty_choices(BOOTH.election, BOOTH.ballot)[index].length == 0 ?
        `<div style="margin-left: 15px;">&#x2610; <i>No choice selected</i></div>`
        : ``
    }

    ${BALLOT.pretty_choices(BOOTH.election, BOOTH.ballot)[index].map(choice =>
        `<div style="margin-left: 15px;">&#x2713; ${choice}</div>`
    )}
    ${BALLOT.pretty_choices(BOOTH.election, BOOTH.ballot)[index].length < question.max ?
        `[you under-voted: you may select up to ${question.max}]`
        : ``
    }
    [<a onclick="BOOTH.show_question(${index}); return false;" href="#">edit responses</a>]
    ${index < question.max ? `<br /><br />` : ``}
`
)}

</div>


<p><p>Your ballot tracker is <b><tt style="font-size: 11pt;">${BOOTH.encrypted_ballot_hash}</tt></b>, and you can <a onclick="BOOTH.show_receipt(); return false;" href="#">print</a> it.<br /><br /></p>

<p>
Once you click "Submit", the unencrypted version of your ballot will be destroyed, and only the encrypted version will remain.  The encrypted version will be submitted to the Helios server.</p>

<button id="proceed_button" onclick="BOOTH.cast_ballot();">Submit this Vote!</button><br />
<div id="loading_div"><img src="loading.gif" id="proceed_loading_img" /></div>



<form method="POST" action="${BOOTH.election.cast_url}" id="send_ballot_form" class="prettyform">
<input type="hidden" name="election_uuid" value="${BOOTH.election.uuid}" />
<input type="hidden" name="election_hash" value="${BOOTH.election_hash}" />
<textarea name="encrypted_vote" style="display: none;">
${BOOTH.encrypted_vote_json}
</textarea>
</form>
`;