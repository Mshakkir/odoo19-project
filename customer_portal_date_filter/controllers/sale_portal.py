from odoo import _
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class SalePortal(CustomerPortal):

    def _get_searchbar_date_range(self):
        """Define the date range filter configuration"""
        return {"label": _("Order Date"), "field": "date_order"}

    def _prepare_sale_portal_rendering_values(
            self,
            page=1,
            date_begin=None,
            date_end=None,
            sortby=None,
            quotation_page=False,
            searchbar_date_range_from=None,
            searchbar_date_range_to=None,
            **kwargs,
    ):
        """
        Prepare values for sale portal rendering with date range filtering

        Extended to support custom date range filtering on order_date field
        """
        SaleOrder = request.env["sale.order"]

        # Default sorting
        if not sortby:
            sortby = "date"

        partner = request.env.user.partner_id
        values = self._prepare_portal_layout_values()

        # Determine URL and domain based on page type
        if quotation_page:
            url = "/my/quotes"
            domain = self._prepare_quotations_domain(partner)
        else:
            url = "/my/orders"
            domain = self._prepare_orders_domain(partner)

        searchbar_sortings = self._get_sale_searchbar_sortings()
        searchbar_date_range = self._get_searchbar_date_range()

        sort_order = searchbar_sortings[sortby]["order"]

        # Apply legacy date filters (if used)
        if date_begin and date_end:
            domain += [
                ("create_date", ">", date_begin),
                ("create_date", "<=", date_end),
            ]

        # Apply custom date range filter
        if date_range_field := searchbar_date_range.get("field"):
            if searchbar_date_range_from:
                domain += [(date_range_field, ">=", searchbar_date_range_from)]
            if searchbar_date_range_to:
                domain += [(date_range_field, "<=", searchbar_date_range_to)]

        # Prepare pagination
        pager_values = portal_pager(
            url=url,
            total=SaleOrder.search_count(domain),
            page=page,
            step=self._items_per_page,
            url_args={
                "date_begin": date_begin,
                "date_end": date_end,
                "sortby": sortby,
                "searchbar_date_range_from": searchbar_date_range_from,
                "searchbar_date_range_to": searchbar_date_range_to,
            },
        )

        # Search orders with pagination
        orders = SaleOrder.search(
            domain,
            order=sort_order,
            limit=self._items_per_page,
            offset=pager_values["offset"],
        )

        # Update values dictionary
        values.update(
            {
                "date": date_begin,
                "quotations": orders.sudo() if quotation_page else SaleOrder,
                "orders": orders.sudo() if not quotation_page else SaleOrder,
                "page_name": "quote" if quotation_page else "order",
                "pager": pager_values,
                "default_url": url,
                "searchbar_sortings": searchbar_sortings,
                "searchbar_date_range": searchbar_date_range,
                "sortby": sortby,
                "searchbar_date_range_from": searchbar_date_range_from,
                "searchbar_date_range_to": searchbar_date_range_to,
            }
        )

        return values