$("document").ready(function(){

    var rowNum = 0;
    $('.add_cafe_attribute').click(function(){
        rowNum ++;
        var row = $('#attribute_0').clone();
        $(row).children('input[name=cafe_attribute_values[]]').attr('value','');
        $(row).attr('id','attribute_' + rowNum);
        $(row).children('span:last').attr('class','remove_cafe_attribute input-group-addon  glyphicon glyphicon-minus');
        $(row).insertAfter('#attribute_' + (rowNum - 1));
    });

    $('.remove_cafe_attribute').click(function(){
       $(this).parent('div').remove();    
       rowNum --;
       $('.cafe_attribute').each(function(index){ $(this).attr('id', 'attribute_'+ index)});
    });

    $('#update_voter_reg').click(function(event) {
        user_type = $('input[name="user_type"]').val();
        eligibility = $('input[name="eligibility"]:checked').val();
        categories = {}
        if (eligibility == "limitedreg" & user_type == "shibboleth") {
            event.preventDefault();
            event.stopImmediatePropagation();
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
                $('label.who_can_vote').html(gettext('Only voters with the specified attributes')); 
            },
            error: function (error) {
                $('div.shib-attr-panel').removeClass('has-success');
                $('div.shib-attr-panel').addClass('has-error');
                $('span.add_attr_result').addClass('label-danger');
                $('span.add_attr_result').text(gettext('Please, correct the provided values.'));
            }
        });
    });

    $('input#idp_type').click(function(){
        $('div.shib-attr-panel').removeClass('hidden');
        $('a#upload_voters').addClass('hidden');
    });

    $('input#csv_type').click(function(){
        $('div.shib-attr-panel').addClass('hidden');
        $('a#upload_voters').removeClass('hidden');
    });

    $('input#logged_type').click(function(){
        $('div.shib-attr-panel').addClass('hidden');
        $('a#upload_voters').addClass('hidden');
    });
})