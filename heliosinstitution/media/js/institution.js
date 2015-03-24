$("document").ready(function(){

	$("form").submit(function(event) { 
        var form = $(this);
		if (confirm(gettext('Are you sure you want to add this e-mail as an institution admin?'))){
            var email = form.find('input[type=email]').val();
            var url = form.attr('action');
            $.ajax({
                type: "POST",
                url: url,
                data: {'email': email},
                success: function (data) {
                    form.parents('div.div_form').addClass('has-success');
                    form.parents('div.div_form').find('span.add_field_result').text(gettext('Email successfully saved.'));
                    $('#institution_users').load($('#institution_users').attr('data-url'));
                },
                error: function (error) {
                    $("div.div_form").addClass('has-error');
                    $("div.div_form").find('span.add_field_result').text(gettext('Please, correct the provided value'));
                }
            });
		}
		return false;
	});
})

