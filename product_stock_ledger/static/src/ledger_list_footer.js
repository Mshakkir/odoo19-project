/** @odoo-module **/
import ListRenderer from 'web.ListRenderer';
import core from 'web.core';

const { patch } = require('web.utils'); // fallback if patch is present

// safe monkey-patch for many Odoo versions:
const ListRendererProto = ListRenderer.prototype;

const _orig_renderFooter = ListRendererProto._renderFooter || function () {
    return this._super(...arguments);
};

ListRendererProto._renderFooter = function () {
    const $footer = _orig_renderFooter.apply(this, arguments);
    try {
        // ensure footer exists and we have columns
        if (!$footer || !this.columns) {
            return $footer;
        }

        // Map field name -> column index
        const nameToIndex = {};
        this.columns.forEach((c, idx) => {
            if (c.attrs && c.attrs.name) {
                nameToIndex[c.attrs.name] = idx;
            }
        });

        // Helper to get footer cell text by column idx:
        const getFooterTextAt = (idx) => {
            const $cells = $footer.find('td, th');
            if (idx >= 0 && idx < $cells.length) {
                return $cells.eq(idx).text().trim();
            }
            return '';
        };

        // Build Sub Total row: we will span first 4 columns with label and then put numeric sums in proper columns
        const colCount = this.columns.length;
        const $sub = $('<tr class="o_list_subtotal_row"/>');
        // label cell: colspan 4 or until first numeric column
        const labelColspan = 4;
        $sub.append($('<td/>').attr('colspan', Math.min(labelColspan, colCount)).text('Sub Total'));

        // fill remaining cells with empty placeholders, but pick rec_qty, issue_qty and balance sums from footer cells
        for (let i = (Math.min(labelColspan, colCount)); i < colCount; i++) {
            // find corresponding column attribute name
            const col = this.columns[i];
            const fieldName = (col && col.attrs) ? col.attrs.name : false;
            let value = '';
            // check if field has a footer sum already rendered (widget=sum)
            // we will reuse footer cell text at same column index
            const footerText = getFooterTextAt(i);
            if (footerText) {
                value = footerText;
            }
            $sub.append($('<td/>').addClass('o_list_number').text(value));
        }

        // Append the Sub Total row after the actual footer element
        $footer.after($sub);

        // Build Net Total row: For ledger, net total usually is the last row's balance.
        // Try to read last visible record's balance cell text from tbody
        const $tbody = this.$el.find('tbody');
        let netValue = '';
        if ($tbody && $tbody.length) {
            const $rows = $tbody.find('tr');
            if ($rows.length) {
                // find index of balance field column
                const balanceIndex = nameToIndex['balance'] !== undefined ? nameToIndex['balance'] : (nameToIndex['balance'] || -1);
                if (balanceIndex >= 0) {
                    const $lastRow = $rows.last();
                    // balance cell is at same index
                    const $cells = $lastRow.find('td, th');
                    if ($cells.length > balanceIndex) {
                        netValue = $cells.eq(balanceIndex).text().trim();
                    }
                } else {
                    // fallback: get last cell text
                    netValue = $rows.last().find('td').last().text().trim();
                }
            }
        }

        // create Net Total row
        const $net = $('<tr class="o_list_net_total_row"/>');
        $net.append($('<td/>').attr('colspan', Math.min(labelColspan, colCount)).text('Net Total'));
        for (let i = (Math.min(labelColspan, colCount)); i < colCount; i++) {
            // place netValue only in last column else empty
            const txt = (i === colCount - 1) ? netValue : '';
            $net.append($('<td/>').addClass('o_list_number').text(txt));
        }
        $sub.after($net);

    } catch (err) {
        console.error('ledger_list_footer: error rendering extra footer rows', err);
    }
    return $footer;
};
