export const auditdiv_markup =
`
<h3>Your audited ballot</h3>

<p>
<b><u>IMPORTANT</u></b>: this ballot, now that it has been audited, <em>will not be tallied</em>.<br />
To cast a ballot, you must click the "Back to Voting" button below, re-encrypt it, and choose "cast" instead of "audit."
</p>

<p>
<b>Why?</b> Helios prevents you from auditing and casting the same ballot to provide you with some protection against coercion.
</p>

<p>
<b>Now what?</b> <a onclick="document.getElementById('audit_trail').select();" href="#">Select your ballot audit info</a>, copy it to your clipboard, then use the <a target="_blank" href="single-ballot-verify.html?election_url=${BOOTH.election_url}">ballot verifier</a> to verify it.<br />
Once you're satisfied, click the "back to voting" button to re-encrypt and cast your ballot.
</p>

<form action="#">
<textarea name="audit_trail" id="audit_trail" cols="80" rows="10" wrap="soft">
${BOOTH.audit_trail}
</textarea>
<br /><br />
Before going back to voting,<br />
you can post this audited ballot to the Helios tracking center so that others might double-check the verification of this ballot.
<br /><br />
<b>Even if you post your audited ballot, you must go back to voting and choose "cast" if you want your vote to count.</b>
<br /><br />
<input type="button" value="back to voting" onclick="BOOTH.reset_ciphertexts();BOOTH.seal_ballot();" class="pretty" />
&nbsp; &nbsp;&nbsp;
<input type="button" value="post audited ballot to tracking center" onclick="(this).attr('disabled', 'disabled'); BOOTH.post_audited_ballot();" id="post_audited_ballot_button" class="pretty" style="font-size:0.8em;"/>

</form>
`
;



