$(function() {
  function reload() {
    $('td[class^="status"]').each(function () {
      status = $(this).text().trim();
      if (status === 'Ready' || status === 'Deploy Failed') {
        location.reload(true);
      }
    });
  }

  horizon.datatables.update = function () {
    var $rows_to_update = $('tr.status_unknown.ajax-update');
    if ($rows_to_update.length) {
      var interval = $rows_to_update.attr('data-update-interval'),
        $table = $rows_to_update.closest('table'),
        decay_constant = $table.attr('decay_constant');

      // Do not update this row if the action column is expanded
      if ($rows_to_update.find('.actions_column .btn-group.open').length) {
        // Wait and try to update again in next interval instead
        setTimeout(horizon.datatables.update, interval);
        // Remove interval decay, since this will not hit server
        $table.removeAttr('decay_constant');
        return;
      }
      // Trigger the update handlers.
      $rows_to_update.each(function(index, row) {
        var $row = $(this),
          $table = $row.closest('table.datatable');
        horizon.ajax.queue({
          url: $row.attr('data-update-url'),
          error: function (jqXHR, textStatus, errorThrown) {
            switch (jqXHR.status) {
              // A 404 indicates the object is gone, and should be removed from the table
              case 404:
                // Update the footer count and reset to default empty row if needed
                var $footer, row_count, footer_text, colspan, template, params, $empty_row;

                // existing count minus one for the row we're removing
                row_count = horizon.datatables.update_footer_count($table, -1);

                if(row_count === 0) {
                  colspan = $table.find('th[colspan]').attr('colspan');
                  template = horizon.templates.compiled_templates["#empty_row_template"];
                  params = {
                      "colspan": colspan,
                      no_items_label: gettext("No items to display.")
                  };
                  empty_row = template.render(params);
                  $row.replaceWith(empty_row);
                } else {
                  $row.remove();
                }
                // Reset tablesorter's data cache.
                $table.trigger("update");
                // Enable launch action if quota is not exceeded
                horizon.datatables.update_actions();
                break;
              default:
                horizon.utils.log(gettext("An error occurred while updating."));
                $row.removeClass("ajax-update");
                $row.find("i.ajax-updating").remove();
                break;
            }
          },
          success: function (data, textStatus, jqXHR) {
            var $new_row = $(data);

            if ($new_row.hasClass('status_unknown')) {
              var spinner_elm = $new_row.find("td.status_unknown:last");
              var imagePath = $new_row.find('.btn-action-required').length > 0 ?
                "dashboard/img/action_required.png":
                "dashboard/img/loading.gif";
              imagePath = STATIC_URL + imagePath;
              spinner_elm.prepend(
                $("<div>")
                  .addClass("loading_gif")
                  .append($("<img>").attr("src", imagePath)));
            }

            // Only replace row if the html content has changed
            if($new_row.html() !== $row.html()) {
              if($row.find('.table-row-multi-select:checkbox').is(':checked')) {
                // Preserve the checkbox if it's already clicked
                $new_row.find('.table-row-multi-select:checkbox').prop('checked', true);
              }
              $row.replaceWith($new_row);
              // Reset tablesorter's data cache.
              $table.trigger("update");
              // Reset decay constant.
              $table.removeAttr('decay_constant');
              // Check that quicksearch is enabled for this table
              // Reset quicksearch's data cache.
              if ($table.attr('id') in horizon.datatables.qs) {
                horizon.datatables.qs[$table.attr('id')].cache();
              }
            }
            reload();
          },
          complete: function (jqXHR, textStatus) {
            // Revalidate the button check for the updated table
            horizon.datatables.validate_button();

            // Set interval decay to this table, and increase if it already exist
            if(decay_constant === undefined) {
              decay_constant = 1;
            } else {
              decay_constant++;
            }
            $table.attr('decay_constant', decay_constant);
            // Poll until there are no rows in an "unknown" state on the page.
            next_poll = interval * decay_constant;
            // Limit the interval to 30 secs
            if(next_poll > 30 * 1000) { next_poll = 30 * 1000; }
            setTimeout(horizon.datatables.update, next_poll);
          }
        });
      });
    }
  }
})
