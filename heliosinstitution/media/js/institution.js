$("document").ready(function(){

	$("form.add_inst_email").submit(function(event) { 
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
    
    $('.remove_institution_user').click(function(event) {
        event.preventDefault();
        event.stopImmediatePropagation();
		if (confirm(gettext('Are you sure you want to delete this user?'))){
            var url = $(this).attr('href');
            var element = $(this);
            $.ajax({
                type: "POST",
                url: url,
                success: function (data) {
                    element.parents('tr').remove();
                },
                error: function (error) {
                    form.parents('div.div_form').addClass('has-error');
                    form.parents('div.div_form').find('span.add_field_result').text(gettext('Please, correct the provided value'));
                }
            });
		}
		return false;
    });

    $('.expires_at').datepicker({
        todayBtn: "linked",
        autoclose: true,
        dateFormat: 'dd-mm-yy'
     });

    var rowNum = 0;
    $('.add_cafe_attribute').click(function(){
        rowNum ++;
        var row = $('#attribute_0').clone();
        $(row).children('input[name=cafe_attribute_values[]]').attr('value','');
        $(row).attr('id','attribute_' + rowNum);
        $(row).children('span:last').attr('class','remove_cafe_attribute input-group-addon  glyphicon glyphicon-minus');
        $(row).insertAfter('#attribute_' + (rowNum - 1));
    });

    $('.remove_cafe_attribute').live('click', function(){
       $(this).parent('div').remove();    
       rowNum --;
       $('.cafe_attribute').each(function(index){ $(this).attr('id', 'attribute_'+ index)});
    });

    $('#update_voter_reg').click(function(event) {
        user_type = $('input[name="user_type"]').val();
        eligibility = $('input[name="eligibility"]:checked').val();
        if (eligibility == "limitedreg" & user_type == "shibboleth") {
            event.preventDefault();
            event.stopImmediatePropagation();
            categories = {}
            var url = $('form#eligibility-form').attr('action');
            $('div.cafe_attribute').each(function(){
                key = $(this).find('select option:selected').text();
                value = $(this).find('input[name="cafe_attribute_values[]"]').val();
                categories[key] = value;
            });          
        }
        data = { 
            'eligibility': eligibility,
            'category_id': categories,
        }  
        $.ajax({
            type: "POST",
            url: url,
            dataType: "json",
            data: JSON.stringify(data),   
            success: function (data) {
                $('div.shib-attr-panel').removeClass('has-error');
                $('div.shib-attr-panel').addClass('has-success');
                $('span.add_attr_result').addClass('label-success');
                $('span.add_attr_result').text(gettext('Attributes successfully saved.'));
            },
            error: function (error) {
                $('div.shib-attr-panel').removeClass('has-success');
                $('div.shib-attr-panel').addClass('has-error');
                $('span.add_attr_result').addClass('label-danger');
                $('span.add_attr_result').text(gettext('Please, correct the provided values.'));
            }
        });
    });

})
