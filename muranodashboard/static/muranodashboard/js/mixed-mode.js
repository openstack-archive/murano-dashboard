/**
 * Created with PyCharm.
 * User: tsufiev
 * Date: 12.08.13
 * Time: 12:29
 * To change this template use File | Settings | File Templates.
 */
$(function() {
    function check_mixed_mode(){
        var checked = $("input[id*='mixed_mode']").prop('checked')
        if ( checked === true) {
            $("label[for*='password_field']").parent().css(
                {'display': 'inline-block'});
        } else if (checked === false) {
            $("label[for*='password_field']").parent().css(
                {'display': 'none'});
        }
    }

    $("input[id*='mixed_mode']").change(check_mixed_mode);
    check_mixed_mode();
    $(".checkbox").css({'float': 'left', 'width': 'auto', 'margin-right': '10px'})
});
