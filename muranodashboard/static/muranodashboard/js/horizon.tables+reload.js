$(function() {
  $("table#services.datatable").on("update", function () {
    // If every component has finished installing (with error or success): reloads the page.
    var rows_to_update = $(this).find('tr.status_unknown.ajax-update');
    if (rows_to_update.length === 0) {
      location.reload(true);
    }
  });
});
