/*    Copyright (c) 2013 Mirantis, Inc.

    Licensed under the Apache License, Version 2.0 (the "License"); you may
    not use this file except in compliance with the License. You may obtain
    a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.
*/
$(function() {
  "use strict";

  function mainCheck(div, parameter1, parameter2, text) {
    var msg = "<div class='alert alert-message alert-danger'>" + gettext(text) + '</div>';
    var errorNode = div.find("div.alert-message");
    var notAdded;
    if (errorNode.length) {
      notAdded = false;
      errorNode.text(text);
    } else {
      notAdded = true;

    }
    if (parameter1 !== parameter2 && notAdded) {
      div.addClass("error");
      div.find("label").after(msg);
    } else if (parameter1 === parameter2) {
      div.removeClass("error");
      errorNode.remove();
    }
  }

  function checkPasswordsMatch(event) {
    var $this = $(event.target);
    var password = $this.closest(".form-field,.form-group").prev().find("input").val();
    var confirmPassword = $this.val();
    var div = $this.closest(".form-field,.form-group");
    mainCheck(div, password, confirmPassword, "Passwords do not match");
  }

  function checkStrengthRemoveErrIfMatches(event) {
    var $this = $(event.target);
    var password = $this.val();

    var confirmPassId = $this.attr('id') + '-clone';
    var confirmPassword = $('#' + confirmPassId).val();
    var div = $this.closest(".form-field,.form-group").next();
    if (confirmPassword.length) {
      mainCheck(div, password, confirmPassword, "Passwords do not match");
    }
    var text = "Your password should have at least";
    var meetRequirements = true;
    if (password.length < 7) {
      text += " 7 characters";
      meetRequirements = false;
    }
    if (password.match(/[A-Z]+/) === null) {
      text += " 1 capital letter";
      meetRequirements = false;
    }
    if (password.match(/[a-z]+/) === null) {
      text += " 1 non-capital letter";
      meetRequirements = false;
    }
    if (password.match(/[0-9]+/) === null) {
      text += " 1 digit";
      meetRequirements = false;
    }

    if (password.match(/[!@#$%^&*()_+|\/.,~?><:{}]+/) === null) {
      text += " 1 special character";
      meetRequirements = false;
    }

    div = $this.closest(".form-field,.form-group");
    mainCheck(div, meetRequirements, true, text);
  }

  $("input[id$='password'][type='password']").keyup(checkStrengthRemoveErrIfMatches);
  $("input[id$='password-clone'][type='password']").keyup(checkPasswordsMatch);
});
