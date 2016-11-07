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

// In some cases successful update events can stack up in case we have lots of apps in an env.
// This might lead to a situation when lots of reloads are scheduled simultaneously.
// The following variable forces reload to be called only once.
var reloadCalled = false;

$(function() {
  "use strict";
  $("table#services.datatable").on("update", function () {
    // If every component has finished installing (with error or success): reloads the page.
    var $rowsToUpdate = $(this).find('tr.warning.ajax-update');
    if ($rowsToUpdate.length === 0) {
      if (reloadCalled === false) {
        reloadCalled = true;
        location.reload(true);
      }
    }
  });
});

// Reload page using horizon ajax_poll_interval
// until deployment of empty environment is finished
$(function() {
  "use strict";
  if ($("div#environment_details__services").find("div.drop_component").length === 0 &&
      $("table#services.datatable").find("tr.empty").length &&
      $("button#services__action_deploy_env").length === 0) {
    var $pollInterval = $("input#pollInterval")[0].value;
    setTimeout(function () {
      if (reloadCalled === false) {
        reloadCalled = true;
        location.reload(true);
      }
    }, $pollInterval);
  }
});

var reloadEnvironmentCalled = false;
var lastStatuses = [];

// Reload page after table update if no more environments left
// or status of some environment changed
$(function() {
  "use strict";
  $("table#environments").on("update", function () {
    var $environmentsRows = $(this).find('tbody tr:visible').not('.empty');
    if ($environmentsRows.length === 0) {
      if (reloadEnvironmentCalled === false) {
        reloadEnvironmentCalled = true;
        location.reload(true);
      }
    } else {
      var $statuses = [];
      for (var $i = 0; $i < $environmentsRows.length; $i++) {
        var $row = $($environmentsRows[$i]);
        var $rowStatus = getRowStatus($row);
        $statuses.push($rowStatus);
      }
      if (lastStatuses.length !== 0 && areArraysEqual($statuses, lastStatuses) === false) {
        if (reloadEnvironmentCalled === false) {
          reloadEnvironmentCalled = true;
          location.reload(true);
        }
      } else {
        lastStatuses = $statuses;
      }
    }
  });
});

function getRowStatus($row) {
  "use strict";
  if ($row.hasClass('warning')) {
    return "in process";
  } else {
    return $row.attr("status");
  }
}

function areArraysEqual($arr1, $arr2) {
  "use strict";
  if ($arr1.length !== $arr2.length) {
    return false;
  }
  for (var $i = 0; $i < $arr1.length; $i++) {
    if ($arr1[$i] !== $arr2[$i]) {
      return false;
    }
  }
  return true;
}

// Disable action buttons according to the statuses of checked environments
$(function() {
  "use strict";
  var $statuses = {
    environments__deploy: ['pending', 'deploy failure'],
    environments__delete: ['ready', 'pending', 'new', 'deploy failure', 'delete failure'],
    environments__abandon: ['ready', 'in process', 'deploy failure', 'delete failure']
  };

  // Change of individual checkboxes or table update
  // TODO(vakovalchuk): improve checkbox detection on the deploying rows
  // Deploying rows don't react to selectors less broad than table body, e.g.:
  // $("table#environments tbody input[type='checkbox']").change(enableButtons);
  $("table#environments tbody").click(enableButtons);
  $("table#environments").on("update", enableButtons);

  function enableButtons() {
    var $buttons = $("table#environments div.table_actions").find('button[name="action"]');
    var $environmentsRows = $("table#environments").find('tbody tr:visible').not('.empty');
    for (var $i = 0; $i < $buttons.length; $i++) {
      var $buttonValue = $buttons[$i].value;
      for (var $j = 0; $j < $environmentsRows.length; $j++) {
        var $row = $($environmentsRows[$j]);
        var $checkbox = $row.find("input.table-row-multi-select").first();
        if ($checkbox.prop('checked')) {
          var $rowStatus = getRowStatus($row);
          if ($statuses[$buttonValue].indexOf($rowStatus) === -1) {
            $($buttons[$i]).prop("disabled", true);
            break;
          }
        } else {
          $($buttons[$i]).prop("disabled", false);
        }
      }
    }
  }

  // Change of all checkboxes at once
  $("table#environments thead input.table-row-multi-select:checkbox").change(function () {
    var $buttons = $("table#environments div.table_actions").find('button[name="action"]');
    var $environmentsRows = $("table#environments").find('tbody tr:visible').not('.empty');
    if ($(this).prop('checked')) {
      for (var $j = 0; $j < $buttons.length; $j++) {
        var $buttonValue = $buttons[$j].value;
        for (var $k = 0; $k < $environmentsRows.length; $k++) {
          var $row = $($environmentsRows[$k]);
          var $rowStatus = getRowStatus($row);
          if ($statuses[$buttonValue].indexOf($rowStatus) === -1) {
            $($buttons[$j]).prop("disabled", true);
            break;
          }
        }
      }
    } else {
      for (var $l = 0; $l < $buttons.length; $l++) {
        $($buttons[$l]).prop("disabled", false);
      }
    }
  });
});
