// In some cases successfull update events can stack up in case we have lots of apps in an env.
// This might lead to a situation when lots of reloads are scheduled simultaneously.
// The following variable forces reload to be called only once.
var reload_called = false;
$(function() {
  $("table#services.datatable").on("update", function () {
    // If every component has finished installing (with error or success): reloads the page.
    var rows_to_update = $(this).find('tr.status_unknown.ajax-update');
    if (rows_to_update.length === 0) {
      if (reload_called === false) {
        reload_called = true;
        location.reload(true);
      }
    }
  });
});
