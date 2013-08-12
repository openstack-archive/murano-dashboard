/**
 * Created with PyCharm.
 * User: tsufiev
 * Date: 12.08.13
 * Time: 12:25
 * To change this template use File | Settings | File Templates.
 */
$(function() {
    function check_preconfigured_ad(){
        var checked = $("input[id*='external_ad']").prop('checked')
        if ( checked== true) {
            $("select[id*='-domain']").attr("disabled", "disabled");
            $("label[for*='ad_user']").parent().css({'display': 'inline-block'});
            $("label[for*='ad_password']").parent().css({'display': 'inline-block'});
        }
        if (checked == false) {
            $("select[id*='-domain']").removeAttr("disabled");
            $("label[for*='ad_user']").parent().css({'display': 'none'});
            $("label[for*='ad_password']").parent().css({'display': 'none'});
        }
    }

    $("input[id*='external_ad']").change(check_preconfigured_ad);
    check_preconfigured_ad();
});