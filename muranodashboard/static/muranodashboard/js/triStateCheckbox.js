$(function() {
  "use strict";
  //Updates value of hidden input based on state of visible input
  function updateValue ($beautyInput, $valueInput) {
    var value;
    if ($beautyInput.prop('indeterminate')) {
      value = 'None';
    } else if ($beautyInput.prop('checked')) {
      value = 'True';
    } else {
      value = 'False';
    }
    $valueInput.val($valueInput.val().split('=')[0] + '=' + value);
  }
  function makeUpdater(beautyInput, valueInput) {
    return function() {
      updateValue(beautyInput, valueInput);
    };
  }
  var i, len, $beautyInput, $valueInput, updater, value, $inputs;

  $inputs = $('[data-tri-state-checkbox=]');

  for (i = 0, len = $inputs.length; i < len; i++) {
    //Subscribe hidden input to updates of visible input
    $valueInput = $inputs.eq(i);
    $beautyInput = $valueInput.prev();
    updater = makeUpdater($beautyInput, $valueInput);
    $beautyInput.change(updater);

    //Set initial state of visible input
    value = $valueInput.val().split('=')[1];
    if (value === 'True') {
      $beautyInput.prop('checked', true);
      $beautyInput.prop('indeterminate', false);
    } else if (value === 'False') {
      $beautyInput.prop('checked', false);
      $beautyInput.prop('indeterminate', false);
    } else {
      $beautyInput.prop('checked', false);
      $beautyInput.prop('indeterminate', true);
    }
  }
});
