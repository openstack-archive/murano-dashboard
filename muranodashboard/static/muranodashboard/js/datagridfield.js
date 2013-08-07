/**
 * Created with PyCharm.
 * User: tsufiev
 * Date: 30.07.13
 * Time: 20:27
 * To change this template use File | Settings | File Templates.
 */
$(function() {
    var MAX_NODES = 5,
        MIN_NODES = 1;

    function trimLabel(label) {
        return $.trim(label.replace(/(\r\n|\r|\n|↵)/gm, ''));
    }

    function getMaxLabel() {
        var labels = [],
            max = 0,
            base = '';
        $('table.datagrid tbody tr td:first-child').each(function(i, td) {
            labels.push(trimLabel($(td).text()));
        });
        labels.forEach(function(label) {
            var match = /([a-zA-z]+)([0-9]+)/.exec(label),
                n = +match[2];
            base = match[1];
            if ( n > max )
                max = n;
        });
        return [base, max]
    }

    function getNextLabel() {
        var baseMax = getMaxLabel();
        return baseMax[0]+(+baseMax[1]+1);
    }

    function getNumOfSync() {
        var checked = 0;
        $('table.datagrid tbody td input:checkbox').each(function(index, cb) {
            if ( $(cb).attr('checked') )
                checked++;
        });
        return checked;
    }

    function validate_sync(event) {
        var checkbox = $(event.target);

        if ( checkbox.attr('checked') ) {
            if ( getNumOfSync() > 2 ) {
                alert('No more than 2 nodes can be in sync-mode!')
                checkbox.attr('checked', false);
            }
        } else if ( checkbox.parents().eq(1).find('input:radio').attr('checked') ) {
            alert('Primary node is always in sync-mode!');
            checkbox.attr('checked', true);
        }
    }

    var primary = $('table.datagrid tbody input:radio[checked="checked"]').parents().eq(1);

    function validate_primary(event) {
        var radio = $(event.target),
            checkbox = radio.parents().eq(1).find('input:checkbox');
        if ( !checkbox.attr('checked') ) {
            if ( getNumOfSync() == 2 )
                primary.find('input:checkbox').attr('checked', false);
            checkbox.attr('checked', true);
        }
        primary = radio.parents().eq(1);
    }

    $('table.datagrid tbody td input:checkbox').click(validate_sync);
    $('table.datagrid tbody td input:radio').click(validate_primary);

    $('button#node-add').click(function() {
        //debugger;
        if ( $('table.datagrid tbody tr').length >= MAX_NODES ) {
            alert('Maximum number of nodes ('+MAX_NODES+') already reached.');
            return;
        }
        var lastRow = $('table.datagrid tbody tr:last-child'),
            clone = lastRow.clone();
        clone.toggleClass('even').toggleClass('odd');
        clone.find('td:first-child').text(getNextLabel());
        // toggle of sync and primary buttons of clone
        clone.find('input:checkbox').attr('checked', false);
        clone.find('input:checkbox').click(validate_sync);
        clone.find('input:radio').attr('checked', false);
        clone.find('input:radio').click(validate_primary);
        lastRow.after(clone);
    });

    $('button#node-remove').click(function() {
        if ( $('table.datagrid tbody tr').length <= MIN_NODES ) {
            alert('Cannot remove the only node');
            return;
        }
        var labelNum = getMaxLabel(),
            label = labelNum.join(''),
            rowRef = 'table.datagrid tbody tr:contains('+label+')';
        if ( rowRef + ' :radio[checked="checked"]' ) {
            label = labelNum[0] + (labelNum[1] - 1);
            $('table.datagrid tbody tr:contains('+label+') :radio').attr(
                'checked', 'checked');
        }
        $(rowRef).remove();
    });

    $('.modal-footer input.btn-primary').click(function() {
        var data = [];
        $('table.datagrid tbody tr').each(function(i, tr) {
            function getInputVal(td) {
                return td.find('input').attr('checked') == 'checked';
            }
            data.push({
                name: trimLabel($(tr).children().eq(0).text()),
                is_sync: getInputVal($(tr).children().eq(1)),
                is_primary: getInputVal($(tr).children().eq(2))
            })
        });
        $('input.gridfield-hidden').val(JSON.stringify(data));
    })

    // temporarily disable all controls which are bugged
    $('table.datagrid th.edit-columns').remove();
    $('div.datagrid-titlebox').remove();
});
