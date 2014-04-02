(function ($) {
    $(document).ready(function () {
        $('[data-help]:visible').each(function (i, element) {
            $('body').append(
                $('<div>', {'class': 'help-question-mark'}).html('?').css({
                    'width': 20,
                    'height': 20,
                    'margin-top': $(element).is(':checkbox') ? '-4px' : '8px',
                    'margin-left': $(element).is(':checkbox') ? '12px' : '30px',
                    'font-size': '16px',
                    'background': '#333',
                    'border-radius': 10,
                    'text-align': 'center',
                    'line-height': '20px',
                    'color': '#fff',
                    'cursor': 'pointer',
                    'position': 'absolute',
                    'top': $(this).offset().top,
                    'left': $(this).offset().left + $(this).width(),
                    'opacity': 0
                }).animate({'opacity': 1}, 500).data('text', $(this).data('help')).click(showHelpModal)
            );
        });

        function showHelpModal(e) {
            var modal = $('<div>', {'class': 'reveal-modal'}).attr('data-reveal', '').append(
                $('<h3>').html('Help'),
                $('<p>').html($(e.target).data('text')),
                $('<a>', {'class': 'close-reveal-modal'}).html('&#215;')
            );
            $('body').append(modal);
            $(document).foundation();
            modal.foundation('reveal', 'open');;
        }
    });
}) (jQuery);