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
        //debugger;
        var data = [];
        $('table.datagrid tbody tr').each(function(i, tr) {
            function getInputVal(td) {
                return td.find('input').attr('checked') == 'checked';
            }
            data.push({
                name: trimLabel($(tr).children().eq(0).text()),
                is_sync: getInputVal($(tr).children().eq(1)),
                is_primary: getInputVal($(tr).children().eq(3))
            })
        });
        $('input.gridfield-hidden').val(JSON.stringify(data));
    })

    // temporarily disable all controls which are bugged
    $('table.datagrid th.edit-columns').remove();
    $('div.datagrid-titlebox').remove();
});
