/*    Copyright (c) 2013 Mirantis, Inc.

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
    var MAX_NODES = 5,
        MIN_NODES = 2;

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
            alert('There cannot be less than ' + MIN_NODES + ' nodes');
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
                isSync: getInputVal($(tr).children().eq(1)),
                isMaster: getInputVal($(tr).children().eq(2))
            })
        });
        $('input.gridfield-hidden').val(JSON.stringify(data));
    })

    // temporarily disable all controls which are bugged
    $('table.datagrid th.edit-columns').remove();
    $('div.datagrid-titlebox').remove();
});
