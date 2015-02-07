$(function() {

  horizon.modals.loadModal = function (url, updateFieldId) {
    // If there's an existing modal request open, cancel it out.
    if (horizon.modals._request && typeof(horizon.modals._request.abort) !== undefined) {
      horizon.modals._request.abort();
    }

    horizon.modals._request = $.ajax(url, {
      beforeSend: function () {
        horizon.modals.modal_spinner(gettext("Loading"));
      },
      complete: function () {
        // Clear the global storage;
        horizon.modals._request = null;
        horizon.modals.spinner.modal('hide');
      },
      error: function(jqXHR, status, errorThrown) {
        if (jqXHR.status === 401){
          var redir_url = jqXHR.getResponseHeader("X-Horizon-Location");
          if (redir_url){
            location.href = redir_url;
          } else {
            location.reload(true);
          }
        }
        else {
          if (!horizon.ajax.get_messages(jqXHR)) {
            // Generic error handler. Really generic.
            horizon.alert("danger", gettext("An error occurred. Please try again later."));
          }
        }
      },
      success: function (data, textStatus, jqXHR) {
        var update_field_id = updateFieldId,
          modal,
          form;
        modal = horizon.modals.success(data, textStatus, jqXHR);
        if (update_field_id) {
          form = modal.find("form");
          if (form.length) {
            form.attr("data-add-to-field", update_field_id);
          }
        }
      }
    });
  };

});
