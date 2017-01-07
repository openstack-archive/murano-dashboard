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
    var msg = "<div class='alert alert-message alert-danger'>" + text + '</div>';
    var errorNode = div.find("div.alert-message");
    var notAdded;
    if (errorNode.length) {
      notAdded = false;
      errorNode.html(text);
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

  function validateField(event) {
    var $this = $(event.target);
    var value = $this.val();
    var arrayPattern = $this.data('validators');
    var text = gettext("");
    var meetRequirements = true;

    arrayPattern.forEach(function(n) {
      var re = new RegExp(n.regex);
      if (value.match(re) === null) {
        text += gettext(n.message) + "<br>";
        meetRequirements = false;
      }
    });

    var div = $this.closest(".form-field,.form-group");
    mainCheck(div, meetRequirements, true, text);
  }

  $(document).on("keyup", "input[data-validators]:not([id$='clone'])", validateField);
});
