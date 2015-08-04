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
  function checkPreconfiguredAd() {
    var checked = $("input[id*='externalAD']").prop('checked');
    if (checked === true) {
      $("select[id*='-domain']").attr("disabled", "disabled");
      $("label[for*='domainAdminUserName']").parent().css({'display': 'inline-block'});
      $("label[for*='domainAdminPassword']").parent().css({'display': 'inline-block'});
    }
    if (checked === false) {
      $("select[id*='-domain']").removeAttr("disabled");
      $("label[for*='domainAdminUserName']").parent().css({'display': 'none'});
      $("label[for*='domainAdminPassword']").parent().css({'display': 'none'});
    }
  }

  $("input[id*='externalAD']").change(checkPreconfiguredAd);
  checkPreconfiguredAd();
});
