# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("done", "Done"),
]


class StoreRequestLine(models.Model):

    _name = "store.request.line"
    _description = "Store Request Line"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Description", track_visibility="onchange")
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="U.O.M",
        track_visibility="onchange",
    )
    product_qty = fields.Float(
        string="Quantity", track_visibility="onchange", digits="Product Unit of Measure"
    )
    request_id = fields.Many2one(
        comodel_name="store.request",
        string="Store Request",
        ondelete="cascade",
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        track_visibility="onchange",
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        related="request_id.requested_by",
        string="Requested by",
        store=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        related="request_id.assigned_to",
        string="Assigned to",
        store=True,
    )
    date_start = fields.Date(related="request_id.date_start", store=True)
    description = fields.Text(
        related="request_id.description",
        string="PR Description",
        store=True,
        readonly=False,
    )
    origin = fields.Char(
        related="request_id.origin", string="Source Document", store=True
    )
    date_required = fields.Date(
        string="Request Date",
        required=True,
        track_visibility="onchange",
        default=fields.Date.context_today,
    )
    is_editable = fields.Boolean(
        string="Is editable", compute="_compute_is_editable", readonly=True
    )
    specifications = fields.Text(string="Specifications")
    request_state = fields.Selection(
        string="Request state",
        related="request_id.state",
        selection=_STATES,
        store=True,
    )
    cancelled = fields.Boolean(
        string="Cancelled", readonly=True, default=False, copy=False
    )

    delivered_qty = fields.Float(
        string="Delivered Qty",
        digits="UOM",
        compute="_compute_delivered_qty",
    )

    stock_move_id = fields.One2many(
        comodel_name="stock.move",
        inverse_name="created_store_request_line_id",
        string="Downstream Moves",
    )

    orderpoint_id = fields.Many2one(
        comodel_name="stock.warehouse.orderpoint", string="Orderpoint"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="request_id.company_id",
        string="Company",
        store=True,
    )

    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        domain=[("purchase_ok", "=", True)],
        track_visibility="onchange",
    )

    @api.depends(
        "product_id",
        "name",
        "product_uom_id",
        "product_qty",
        "analytic_account_id",
        "date_required",
        "specifications",
        "stock_move_id",
    )
    def _compute_is_editable(self):
        for rec in self:
            if rec.request_id.state in ("to_approve", "approved", "rejected", "done"):
                rec.is_editable = False
            else:
                rec.is_editable = True
        for rec in self.filtered(lambda p: p.stock_move_id):
            rec.is_editable = False

    @api.depends("product_id", "product_id.seller_ids")
    def _compute_supplier_id(self):
        for rec in self:
            rec.supplier_id = False
            if rec.product_id:
                if rec.product_id.seller_ids:
                    rec.supplier_id = rec.product_id.seller_ids[0].name

    @api.onchange("product_id")
    def onchange_product_id(self):
        if self.product_id:
            name = self.product_id.name
            if self.product_id.code:
                name = "[{}] {}".format(name, self.product_id.code)
            if self.product_id.description_purchase:
                name += "\n" + self.product_id.description_purchase
            self.product_uom_id = self.product_id.uom_id.id
            self.product_qty = 1
            self.name = name

    def do_cancel(self):
        """Actions to perform when cancelling a purchase request line."""
        self.write({"cancelled": True})

    def do_uncancel(self):
        """Actions to perform when uncancelling a purchase request line."""
        self.write({"cancelled": False})

    def write(self, vals):
        res = super(StoreRequestLine, self).write(vals)
        if vals.get("cancelled"):
            requests = self.mapped("request_id")
            requests.check_auto_reject()
        return res

    def _compute_delivered_qty(self):
        for rec in self:
            rec.delivered_qty = 0.0
            for line in rec.stock_move_id.filtered(lambda x: x.state != "cancel"):
                if rec.product_uom_id and line.product_uom != rec.product_uom_id:
                    rec.delivered_qty += line.product_uom._compute_quantity(
                        line.product_qty, rec.product_uom_id
                    )
                else:
                    rec.delivered_qty += line.product_qty

    @api.depends("stock_move_id.state", "stock_move_id.order_id.state")
    def _compute_purchase_state(self):
        for rec in self:
            temp_purchase_state = False
            if rec.stock_move_id:
                if any([po_line.state == "done" for po_line in rec.stock_move_id]):
                    temp_purchase_state = "done"
                elif all([po_line.state == "cancel" for po_line in rec.stock_move_id]):
                    temp_purchase_state = "cancel"
                elif any(
                    [po_line.state == "purchase" for po_line in rec.stock_move_id]
                ):
                    temp_purchase_state = "purchase"
                elif any(
                    [po_line.state == "to approve" for po_line in rec.stock_move_id]
                ):
                    temp_purchase_state = "to approve"
                elif any([po_line.state == "sent" for po_line in rec.stock_move_id]):
                    temp_purchase_state = "sent"
                elif all(
                    [
                        po_line.state in ("draft", "cancel")
                        for po_line in rec.stock_move_id
                    ]
                ):
                    temp_purchase_state = "draft"
            rec.purchase_state = temp_purchase_state

    @api.model
    def _get_supplier_min_qty(self, product, partner_id=False):
        seller_min_qty = 0.0
        if partner_id:
            seller = product.seller_ids.filtered(lambda r: r.name == partner_id).sorted(
                key=lambda r: r.min_qty
            )
        else:
            seller = product.seller_ids.sorted(key=lambda r: r.min_qty)
        if seller:
            seller_min_qty = seller[0].min_qty
        return seller_min_qty

    @api.model
    def _calc_new_qty(self, request_line, po_line=None, new_pr_line=False):
        purchase_uom = po_line.product_uom or request_line.product_id.uom_po_id
        # TODO: Not implemented yet.
        #  Make sure we use the minimum quantity of the partner corresponding
        #  to the PO. This does not apply in case of dropshipping
        supplierinfo_min_qty = 0.0
        if not po_line.order_id.dest_address_id:
            supplierinfo_min_qty = self._get_supplier_min_qty(
                po_line.product_id, po_line.order_id.partner_id
            )

        rl_qty = 0.0
        # Recompute quantity by adding existing running procurements.
        if new_pr_line:
            rl_qty = po_line.product_uom_qty
        else:
            for prl in po_line.purchase_request_lines:
                for alloc in prl.purchase_request_allocation_ids:
                    rl_qty += alloc.product_uom_id._compute_quantity(
                        alloc.requested_product_uom_qty, purchase_uom
                    )
        qty = max(rl_qty, supplierinfo_min_qty)
        return qty

    def _can_be_deleted(self):
        self.ensure_one()
        return self.request_state == "draft"

    def unlink(self):
        if self.mapped("stock_move_id"):
            raise UserError(
                _("You cannot delete a record that refers to purchase " "lines!")
            )
        for line in self:
            if not line._can_be_deleted():
                raise UserError(
                    _(
                        "You can only delete a purchase request line "
                        "if the purchase request is in draft state."
                    )
                )
        return super(StoreRequestLine, self).unlink()
