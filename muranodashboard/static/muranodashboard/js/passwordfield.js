/**
 * Created with PyCharm.
 * User: tsufiev
 * Date: 12.08.13
 * Time: 11:34
 * To change this template use File | Settings | File Templates.
 */
$(function() {
    function main_check(div, parameter1, parameter2, text){
        var msg = "<span class='help-inline'>" + gettext(text) + '</span>'
        var error_node = div.find("span.help-inline")
        var not_added;
        if (error_node.length) {
            not_added = false;
            error_node.text(text);
        } else {
            not_added = true;

        };
        if (parameter1 != parameter2 && not_added) {
            div.addClass("error");
            div.find("label").after(msg)
        } else if (parameter1 == parameter2) {
            div.removeClass("error");
            error_node.remove();
        }
    }

    function check_passwords_match() {
        var $this = $(this);
        var password = $this.closest(".form-field").prev().find(".password").val();
        var confirm_password = $this.val();
        var div = $this.closest(".form-field");
        main_check(div, password,confirm_password, "Passwords do not match")
    }

    function check_strength_remove_err_if_matches(){
        var $this = $(this)
        var password = $this.val();
        var div_confirm = $this.closest(".form-field").next();
        var confirm_password = div_confirm.find(".confirm_password").val();
        var div = $this.closest(".form-field").next();
        if (confirm_password.length){
            main_check(div, password, confirm_password, "Passwords do not match");
        }
        var text = "Your password should have at least"
        var meet_requirements = true;
        if (password.length<7){
            text += " 7 characters";
            meet_requirements = false;
        }
        if (password.match(/[A-Z]+/) == null){
            text += " 1 capital letter";
            meet_requirements = false;
        }
        if (password.match(/[a-z]+/) == null) {
            text += " 1 non-capital letter";
            meet_requirements = false;
        }
        if (password.match(/[0-9]+/) == null){
            text += " 1 digit";
            meet_requirements = false;
        }

        if (password.match(/[!@#$%^&*()_+|\/.,~?><:{}]+/) == null) {
            text += " 1 specical character";
            meet_requirements = false;
        }
        var div = $this.closest(".form-field")
        main_check(div, meet_requirements, true, text);
    };

    $(".confirm_password").change(check_passwords_match);
    $(".password").change(check_strength_remove_err_if_matches);

});
