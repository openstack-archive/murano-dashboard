$(function() {
    function check_preconfigured_ad(){
        var checked = $("input[id*='externalAD']").prop('checked')
        if ( checked== true) {
            $("select[id*='-domain']").attr("disabled", "disabled");
            $("label[for*='domainAdminUserName']").parent().css({'display': 'inline-block'});
            $("label[for*='domainAdminPassword']").parent().css({'display': 'inline-block'});
        }
        if (checked == false) {
            $("select[id*='-domain']").removeAttr("disabled");
            $("label[for*='domainAdminUserName']").parent().css({'display': 'none'});
            $("label[for*='domainAdminPassword']").parent().css({'display': 'none'});
        }
    }

    $("input[id*='externalAD']").change(check_preconfigured_ad);
    check_preconfigured_ad();
});