$("document").ready(function(){

	$("form.add_inst_email").submit(function(event) { 
        event.preventDefault();
        event.stopImmediatePropagation();
        var form = $(this);
        var msg = gettext('Are you sure you want to add this e-mail as an election admin?');
        if ($(this).attr('id') == 'add_inst_mngt_email'){
            msg = gettext('Are you sure you want to add this e-mail as an institution admin?')
        }
		if (confirm(msg)){
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

    $('#inst_details').on('click', '#edit_inst_button', function(event){
        $('#readonly_inst').addClass('hidden');
        $('#edit_inst').addClass('panel-body');
        $('#edit_inst').removeClass('hidden');
    });

    $('#inst_details').on('click', '#save_inst_data', function(event){
        var url = $('#form_edit_inst').attr('action');
        var inst_data = {}
        $('p.inst_data').each(function(){
            inst_data[$(this).children('.form-control').attr('name')] = $(this).children('.form-control').val();
        });
        $.ajax({
            type: "POST",
            url: url,
            data: inst_data,
            success: function (data) {
                $('#inst_details').load($('#inst_details').attr('data-url'));
            },
            error: function (error) {

            }

        });
        return false;
    });

    $("#institution_users").on("click", ".date_expires_at", function(){
        $(".date_expires_at").datepicker({
        format: "dd/mm/yyyy",
        startDate: "now",
        autoclose: true,
        todayHighlight: true
        })
        .on('changeDate', function(e){

            var expires_at = $(this);
            var expires_at_text = expires_at.parent().children('.date');
            var url= expires_at.data('url');

            data = {
                'expires_at' : expires_at.datepicker('getFormattedDate'),
            }

            $.ajax({
                type: "POST",
                url: url,
                dataType: "json",
                data: data,   

                success: function (data) {

                    expires_at
                        .removeClass('text-danger')
                        .addClass('text-success');

                    expires_at_text
                        .text(expires_at.datepicker('getFormattedDate'))
                        .removeClass('text-danger')
                        .addClass('text-success');
                },

                error: function (error) {

                    expires_at
                        .removeClass('text-danger')
                        .addClass('text-danger');

                    expires_at_text
                        .removeClass('text-danger')
                        .addClass('text-danger');
                },
            });
        });
    });

    var table;
    function draw_election_list () {
        table = $('#list').DataTable({
            "language": {
                "lengthMenu": gettext("Display _MENU_ records per page"),
                "zeroRecords": gettext("Nothing found - sorry"),
                "info": gettext("Showing page _PAGE_ of _PAGES_"),
                "infoEmpty": gettext("No records available"),
                "infoFiltered": gettext("(filtered from _MAX_ total records)"),
                "search": gettext("Search:"),
                "Previous": gettext("Previous"),
                "next": gettext("Next"),
                "paginate": {
                    "next": gettext("Next"),
                    "previous": gettext("Previous"),
                }
            }
        });
    }

    $('.slice-institutions').on('click', '.get-filtered', function (e) {
        if (! $.fn.dataTable.isDataTable( '#list' ) ) {
            draw_election_list();
        }
        var url = $(this).data('url');
        var institution_name = $(this).parents('tr').data('institution');
        var election_type = $(this).data('type');
	var year = $('select[name=year] option:selected').val();
	if (year) { url = url + year}
        table.clear();
        $.getJSON(url, function(data) {
            $.each( data.elections, function( i, item ) {
                $('.modal-title').text(institution_name + ' - ' + election_type);
                table.row.add([
                    '<a href='+ item.url + '>' + item.name + '</a>',
                    item.started_at,
                    item.ended_at
                ]).draw();
            });
        });
    });

    $('select[name="year"]').on('change', function() {
        var url = $('.get-by-year').data('url');
        var year = $('select[name=year] option:selected').val();
        $('.slice-institutions').load($('.slice-institutions').attr('data-url')+ year);
    });

})
