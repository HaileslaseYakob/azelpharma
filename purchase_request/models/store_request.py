# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("done", "Done"),
]


class StoreRequest(models.Model):

    _name = "store.request"
    _description = "Store Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    @api.model
    def _company_get(self):
        return self.env["res.company"].browse(self.env.company.id)

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    @api.model
    def _get_default_name(self):
        return self.env["ir.sequence"].next_by_code("store.request")

    @api.model
    def _default_picking_type(self):
        type_obj = self.env["stock.picking.type"]
        company_id = self.env.context.get("company_id") or self.env.company.id
        types = type_obj.search(
            [("sequence_code", "=", "SIV"), ("warehouse_id.company_id", "=", company_id)]
        )
        if not types:
            types = type_obj.search(
                [("sequence_code", "=", "SIV"), ("warehouse_id", "=", False)]
            )
        return types[:1]

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ("to_approve", "approved", "rejected", "done"):
                rec.is_editable = False
            else:
                rec.is_editable = True

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))

    origin = fields.Char(string="Source Document")
    date_start = fields.Date(
        string="Creation date",
        help="Date when the user initiated the " "request.",
        default=fields.Date.context_today,
        track_visibility="onchange",
    )
    date_order = fields.Datetime(string='Order Date', required=True, readonly=True, index=True,
                                 states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=False,
                                 default=fields.Datetime.now)

    picking_count = fields.Integer(compute='_compute_picking', string='Picking count', default=0, store=True)
    picking_ids = fields.One2many(
        "stock.picking","store_request_id",compute='_compute_picking', string='Issued SIV', copy=False,store=True )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="Requested by",
        required=True,
        copy=False,
        track_visibility="onchange",
        default=_get_default_requested_by,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        track_visibility="onchange",
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref("purchase_request.group_purchase_request_manager").id,
            )
        ],
    )
    description = fields.Text(string="Description")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=_company_get,
        track_visibility="onchange",
    )
    line_ids = fields.One2many(
        comodel_name="store.request.line",
        inverse_name="request_id",
        string="Materials requested",
        readonly=False,
        copy=True,
        track_visibility="onchange",
    )

    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        track_visibility="onchange",
        required=True,
        copy=False,
        default="draft",
    )
    is_editable = fields.Boolean(
        string="Is editable", compute="_compute_is_editable", readonly=True
    )
    to_approve_allowed = fields.Boolean(compute="_compute_to_approve_allowed")
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Picking Type",
        required=True,
        default=_default_picking_type,
    )

    location_id = fields.Many2one('stock.location', 'Destination Location', required=True, check_company=True)
    location_src_id = fields.Many2one('stock.location', 'Source Location', check_company=True)
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Deliver To: ', readonly=True, required=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)



    @api.onchange('picking_type_id')
    def _onchange_picking_type(self):
        self.location_src_id = self.picking_type_id.default_location_src_id.id
        self.location_id = self.picking_type_id.default_location_dest_id.id


    @api.depends('picking_ids.date_done')
    def _compute_effective_date(self):
        for order in self:
            pickings = order.picking_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
            dates_list = [date for date in pickings.mapped('date_done') if date]
            order.effective_date = min(dates_list).date() if dates_list else False




    def _action_confirm(self):
        self.order_line._action_launch_stock_rule()
        return super(StoreRequest, self)._action_confirm()

    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_count = len(order.picking_ids)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)



    def action_view_picking(self):
        """ This function returns an action that display existing picking orders of given purchase order ids. When only one found, show the picking immediately.
        """
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'default_picking_type_id': self.picking_type_id.id}
        pick_ids = self.mapped('picking_ids')
        # choose the view_mode accordingly
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state,view) for state,view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = pick_ids.id
        return result

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.mapped("line_ids"))

    def action_view_store_request_line(self):
        action = self.env.ref(
            "purchase_request.store_request_line_form_action"
        ).read()[0]
        lines = self.mapped("line_ids")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [
                (self.env.ref("purchase_request.store_request_line_form").id, "form")
            ]
            action["res_id"] = lines.ids[0]
        return action

    @api.depends("state", "line_ids.product_qty", "line_ids.cancelled")
    def _compute_to_approve_allowed(self):
        for rec in self:
            rec.to_approve_allowed = rec.state == "draft" and any(
                [not line.cancelled and line.product_qty for line in rec.line_ids]
            )

    def copy(self, default=None):
        default = dict(default or {})
        self.ensure_one()
        default.update(
            {
                "state": "draft",
                "name": self.env["ir.sequence"].next_by_code("store.request"),
            }
        )
        return super(StoreRequest, self).copy(default)

    @api.model
    def _get_partner_id(self, request):
        user_id = request.assigned_to or self.env.user
        return user_id.partner_id.id

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'store.request', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('store.request', sequence_date=seq_date) or _('New')

        request = super(StoreRequest, self).create(vals)
        if vals.get("assigned_to"):
            partner_id = self._get_partner_id(request)
            request.message_subscribe(partner_ids=[partner_id])
        return request

    def write(self, vals):
        res = super(StoreRequest, self).write(vals)
        for request in self:
            if vals.get("assigned_to"):
                partner_id = self._get_partner_id(request)
                request.message_subscribe(partner_ids=[partner_id])
        return res

    def create_transfer(self):
        for re in self:
            picking = self.env['stock.picking'].create({
                'location_id': self.location_src_id.id,
                'location_dest_id': self.location_id.id,
                'partner_id': re.partner_shipping_id.id,
                'picking_type_id': re.picking_type_id.id,
                'store_request_id' : re.id,
                'immediate_transfer': False,
            })
            for li in re.line_ids:
                move_receipt_1 = self.env['stock.move'].create({
                'name':li.product_id.name,
                'product_id': li.product_id.id,
                'product_uom_qty': li.product_qty,
                'product_uom': li.product_uom_id.id,
                'picking_id': picking.id,
                'picking_type_id': re.picking_type_id.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.location_id.id,
                })
            picking.action_confirm()
            return self.write({"state": "done"})
    def _can_be_deleted(self):
        self.ensure_one()
        return self.state == "draft"

    def unlink(self):
        for request in self:
            if not request._can_be_deleted():
                raise UserError(
                    _("You cannot delete a store request which is not draft.")
                )
        return super(StoreRequest, self).unlink()

    def button_draft(self):
        self.mapped("line_ids").do_uncancel()
        return self.write({"state": "draft"})

    def button_to_approve(self):
        self.to_approve_allowed_check()
        return self.write({"state": "to_approve"})

    def button_approved(self):
        return self.write({"state": "approved"})

    def button_rejected(self):
        self.mapped("line_ids").do_cancel()
        return self.write({"state": "rejected"})

    def button_done(self):
        return self.write({"state": "done"})

    def check_auto_reject(self):
        """When all lines are cancelled the store request should be
        auto-rejected."""
        for pr in self:
            if not pr.line_ids.filtered(lambda l: l.cancelled is False):
                pr.write({"state": "rejected"})

    def to_approve_allowed_check(self):
        for rec in self:
            if not rec.to_approve_allowed:
                raise UserError(
                    _(
                        "You can't request an approval for a store request "
                        "which is empty. (%s)"
                    )
                    % rec.name
                )
