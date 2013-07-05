$(function() {
    function check_mixed_mode(){
        var checked = $("input[id*='mixedModeAuth']").prop('checked')
        if ( checked === true) {
            $("label[for*='saPassword']").parent().css({'display': 'inline-block'});
        } else if (checked === false) {
            $("label[for*='saPassword']").parent().css({'display': 'none'});
        }
    }

    $("input[id*='mixedModeAuth']").change(check_mixed_mode);
    check_mixed_mode();
    $(".checkbox").css({'float': 'left', 'width': 'auto', 'margin-right': '10px'})
});
