$("document").ready(function(){

	$("form").submit(function(event) { 
            event.preventDefault();
            event.stopImmediatePropagation();
        var form = $(this);
		if (confirm(gettext('Are you sure you want to add this e-mail as an institution admin?'))){
            var email = form.find('input[type=email]').val();
            var url = form.attr('action');
            $.ajax({
                type: "POST",
                url: url,
                data: {'email': email},
                success: function (data) {
                    form.parents('div.div_form').removeClass('has-error');
                    form.parents('div.div_form').addClass('has-success');
                    form.parents('div.div_form').find('span.add_field_result').text(gettext('Email successfully saved.'));
                    $('#institution_users').load($('#institution_users').attr('data-url'));
                },
                error: function (error) {
                    form.parents('div.div_form').removeClass('has-success');
                    form.parents('div.div_form').addClass('has-error');
                    form.parents('div.div_form').find('span.add_field_result').text(gettext('Please, correct the provided value'));
                }
                
            });
            form.find('input[type=email]').val('');
		}
		return false;
	});

/* dropdown menu from http://www.blogwebdesignmicrocamp.com.br/webdesign/aprenda-a-fazer-um-menu-drop-down-simples/ */

    $(".admin_menu").click(function() {
        var X=$(this).attr('id');

        if(X==1) {
            $(".submenu").hide();
            $(this).attr('id', '0');
        } else {
            $(".submenu").show();
            $(this).attr('id', '1');
        }
    });

    $(".submenu").mouseup(function() {
        return false
    });

    $(".admin_menu").mouseup(function() {
        return false
    });

    $(document).mouseup(function() {
        $(".submenu").hide();
        $(".conta_menu").attr('id', '');
    });

})

