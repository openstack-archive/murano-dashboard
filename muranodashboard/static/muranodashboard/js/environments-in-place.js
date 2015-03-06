$(function() {
  $('.add_env').on('click', 'a', createEnv);
  $('.table_actions').on('click', 'a', createEnv);
  function createEnv(ev) {
    function showSpinner() {
      horizon.modals.modal_spinner(gettext("Working"));
    }
    function hideSpinner() {
      horizon.modals.spinner.modal('hide');
    }

    var $tbody = $('table tbody'),
        CREATE_URL = $(this).attr('href');

    $.ajax({
      type: 'GET',
      url: CREATE_URL,
      async: false,
      beforeSend: showSpinner,
      complete: hideSpinner,
      success: drawWorkflowInline
    });

    function drawWorkflowInline(data, validationFailed) {
      var $form = $(data).find('form'),
          $name = $form.find('div.form-group');

      if ( validationFailed ) {
        $tbody.find('tr.new_env').remove();
      }

      var $newEnvTr = $('<tr class="new_env">' +
      '<td id="input_create_env" class="normal_column"></td>' +
      '<td class="normal_column">New</td>' +
      '<td class="actions_column">' +
      '<div class="btn-group">' +
      '<button id="confirm_create_env" class="btn btn-primary">Create</button>' +
      '<button id="cancel_create_env" class="btn btn-default">Cancel</button>' +
      '</div></td></tr>');
      $name.appendTo($newEnvTr.find('td#input_create_env'));

      var $emptyRow = $tbody.find('tr.empty');
      $emptyRow.hide();
      $newEnvTr.prependTo($tbody);

      $name.find('input#id_name').focus()

      $('button#cancel_create_env').on('click', function(ev) {
        $newEnvTr.remove();
        $emptyRow.show();
        ev.preventDefault();
      });
      $('button#confirm_create_env').on('click', function(ev) {
        // putting name group back to detached form to serialize it
        $name.appendTo($form);
        $.ajax({
          method: 'POST',
          url: CREATE_URL,
          async: false,
          data: $form.serialize(),
          beforeSend: showSpinner,
          error: function() {
            $newEnvTr.remove();
            hideSpinner();
            horizon.alert('error',
                'There was an error submitting the form. Please try again.')
          },
          success: function(data, status, xhr) {
            if ( data === '' ) {
              // environment was created successfully
              var redirUrl = xhr.getResponseHeader('X-Horizon-Location');
              $newEnvTr.remove();
              window.location.replace(redirUrl);
            } else {
              // environment wasn't created because data is invalid
              // FIXME: recursion is used, so in case user repeatedly enters
              // invalid Env name (a LOT of attempts), maximum stack depth
              // could be exceeded
              hideSpinner();
              drawWorkflowInline(data, true);
            }
          }
        });
        ev.preventDefault();
      });
    }
    ev.preventDefault();
  }
});
