/*    Copyright (c) 2015 Mirantis, Inc.

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

// In some cases successfull update events can stack up in case we have lots of apps in an env.
// This might lead to a situation when lots of reloads are scheduled simultaneously.
// The following variable forces reload to be called only once.
var reloadCalled = false;

$(function() {
  "use strict";
  $("table#services.datatable").on("update", function () {
    // If every component has finished installing (with error or success): reloads the page.
    var $rowsToUpdate = $(this).find('tr.status_unknown.ajax-update');
    if ($rowsToUpdate.length === 0) {
      if (reloadCalled === false) {
        reloadCalled = true;
        location.reload(true);
      }
    }
  });
});
