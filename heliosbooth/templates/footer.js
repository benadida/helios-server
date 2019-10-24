export const footer_markup = `
<span style="float:right; padding-right:20px;">
<a target="_new" href="mailto:${BOOTH.election_metadata.help_email}?subject=help%20with%20election%20{$T.election.name}&body=I%20need%20help%20with%20election%20{$T.election.uuid}">help!</a>
</span>
${BOOTH.election.BOGUS_P ? 'The public key for this election is not yet ready. This election is in preview mode only.' : `Election Fingerprint: <span id="election_hash" style="font-weight:bold;">${BOOTH.election.hash}</span>`}
`
;
