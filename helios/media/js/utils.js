$("document").ready(function(){
	$("#remove_helios_as_trustee").click(function() { 
		if (confirm(gettext('Are you sure you want to remove Helios as a trustee?'))){
			return true;
		}
		return false;
	});
	$("#remove_trustee").click(function(){
		if (confirm(gettext('Are you sure you want to remove this Trustee?'))){
			return true;
		}
		return false;
	});
	$("#add_trustee").click(function(){
		if (confirm(gettext('Adding your own trustee requires a good bit more work to tally the election.\n' +
			'You will need to have trustees generate keypairs and safeguard their secret key.\n\n' +
			'If you are not sure what that means, we strongly recommend\n' +
			'clicking Cancel and letting Helios tally the election for you.'))){
			return true;
		}
		return false;
	});
	$("#send_trustee_url").click(function(){
		if (confirm(gettext('Are you sure you want to send this trustee his/her admin URL?'))) {
			return true;
		}
		return false;
	});
})