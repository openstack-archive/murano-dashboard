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

/* The fix was borrowed from
http://www.hagenburger.net/BLOG/HTML5-Input-Placeholder-Fix-With-jQuery.html
 */
$(function() {
  "use strict";
  var getIeVersion = function() {
    if (/MSIE (\d+\.\d+);/.test(navigator.userAgent)) { //test for MSIE x.x;
      var ieVersion = Number(RegExp.$1); // capture x.x portion and store as a number
      return ieVersion;
    }
  };
  if (getIeVersion() < 10) {
    // placeholder attribute for optional drop-down fields doesn't work
    // very well together with this fix - so remove placeholder
    // attribute for every drop-down list.
    $('select').filter('[placeholder]').removeAttr('placeholder');
    $('[placeholder]').focus(function() {
      var input = $(this);
      if (input.val() === input.attr('placeholder')) {
        input.val('');
        input.removeClass('placeholder');
      }
    }).blur(function() {
      var input = $(this);
      if (input.val() === '' || input.val() === input.attr('placeholder')) {
        input.addClass('placeholder');
        input.val(input.attr('placeholder'));
      }
    }).blur();

    $('[placeholder]').parents('form').submit(function() {
      $(this).find('[placeholder]').each(function() {
        var input = $(this);
        if (input.val() === input.attr('placeholder')) {
          input.val('');
        }
      });
    });
  }
});
