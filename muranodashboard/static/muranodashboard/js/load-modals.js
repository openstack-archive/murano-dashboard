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
$(function() {
  "use strict";
  horizon.modals.loadModal = function (url, updateFieldId) {
    // If there's an existing modal request open, cancel it out.
    if (horizon.modals.request && typeof horizon.modals.request.abort !== "undefined") {
      horizon.modals.request.abort();
    }

    horizon.modals.request = $.ajax(url, {
      beforeSend: function () {
        horizon.modals.modal_spinner(gettext("Loading"));
      },
      complete: function () {
        // Clear the global storage;
        horizon.modals.request = null;
        horizon.modals.spinner.modal('hide');
      },
      error: function(jqXHR) {
        if (jqXHR.status === 401) {
          var redirUrl = jqXHR.getResponseHeader("X-Horizon-Location");
          if (redirUrl) {
            location.href = redirUrl;
          } else {
            location.reload(true);
          }
        } else {
          if (!horizon.ajax.get_messages(jqXHR)) {
            // Generic error handler. Really generic.
            horizon.alert("danger", gettext("An error occurred. Please try again later."));
          }
        }
      },
      success: function (data, textStatus, jqXHR) {
        var formUpdateFieldId = updateFieldId;
        var modal, form;
        modal = horizon.modals.success(data, textStatus, jqXHR);
        if (formUpdateFieldId) {
          form = modal.find("form");
          if (form.length) {
            form.attr("data-add-to-field", formUpdateFieldId);
          }
        }
      }
    });
  };

});
