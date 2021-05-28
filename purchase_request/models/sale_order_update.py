# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import UserError


class SaleOrderUpdate(models.Model):
    _inherit = "sale.order"

    def get_sales_mrp_count(self):
        count = self.env['sale.mrp'].search_count([('sale_order_id', '=', self.id)])
        self.count = count

    def action_sales_mrp(self):
        values = {
            'customer_id': self.partner_id.id,
            'customer_order': '',
            'sale_order_id': self.id,
            'origin': self.name,
        }

        sale_mrp_id = self.env['sale.mrp'].create(values)
        for line in self.order_line:

            self.env['sale.mrp.line'].create({
                'sale_mrp_id': sale_mrp_id.id,
                'product_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'raw_material': '',
                'specification': '',
                'done_qty': 0,
            })

        return {'type': 'ir.actions.act_window_close'}

    vehicle_transfer_plateno=fields.Char("Vehicle Plate no.")
    sale_mrp_id=fields.One2many('sale.mrp',"sale_order_id")
    count=fields.Integer("Count",compute="get_sales_mrp_count")

_STATES = [
    ("draft", "Draft"),
    ("sales_approved", "Sales Approved"),
    ("production_approved", "Production Approved"),
    ("done", "Done"),
]

class SaleMrp(models.Model):

    _name = "sale.mrp"
    _description = "Production order from Sales"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    @api.model
    def _get_default_picking_type(self):
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        return self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', '=', company_id),

        ], limit=1).id

    def get_sales_mrp_count(self):
        count = self.env['mrp.production.request'].search_count([('sale_mrp_id', '=', self.id)])
        self.count = count

    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        domain="[('code', '=', 'mrp_operation'), ('company_id', '=', company_id)]",
        default=_get_default_picking_type, required=True, check_company=True)

    count=fields.Integer("Count",compute="get_sales_mrp_count")

    sale_order_id = fields.Many2one(
        'sale.order', 'Sales order')

    @api.model
    def _company_get(self):
        return self.env["res.company"].browse(self.env.company.id)

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    @api.model
    def _get_default_name(self):
        return self.env["ir.sequence"].next_by_code("sale.mrp")

    def action_sales_mrp(self):
        values = {
            'customer_id': self.partner_id.id,
            'customer_order': '',
            'origin': self.name,
        }
        sale_mrp_id = self.env['sale.mrp'].create(values)
        for line in self.order_line:

            self.env['sale.mrp.line'].create({
                'sale_mrp_id': sale_mrp_id.id,
                'product_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'raw_material': '',
                'specification': '',
                'done_qty': 0,
            })

        return {'type': 'ir.actions.act_window_close'}

    def button_job_ticket(self):
            for line in self.line_ids:
                product_tmpl=line.product_id.id
                bom = self.env['mrp.bom'].search([('product_tmpl_id','=',product_tmpl)])
                if bom:
                    for b in bom:
                        bom_id = bom.id
                        values = {
                            'origin': self.origin,
                            'sale_mrp_id':self.id,
                            'sale_mrp_line_id':line.id,
                            'requested_by':self.requested_by.id,
                            'product_qty': line.product_qty,
                            'product_id': line.product_id.id,
                            'product_uom_id':line.product_id.uom_id.id,
                            'bom_id':bom_id
                        }
                    self.env['mrp.production.request'].create(values)

            return {'type': 'ir.actions.act_window_close'}

    name = fields.Char(string='Production order no: ', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    #production_request_id = fields.One2many('mrp.production.request','sale_mrp_id', string="Production Request")

    customer_id=fields.Many2one('res.partner',"Customer Name")
    customer_order = fields.Char( "Customer Order")
    origin = fields.Char(string="Purchase Order No: ")
    date_requested = fields.Date(
        string="Delivery date(Sales)",
        help="Date requested by the sales department.",
        default=fields.Date.context_today,
        track_visibility="onchange",
    )
    date_agreed= fields.Datetime(string='Delivery Date(Production)', required=True, readonly=True, index=True,
                                 copy=False,default=fields.Datetime.now)

    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="Requested by(Sales)",
        required=True,
        copy=False,
        track_visibility="onchange",
        default=_get_default_requested_by,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Approver(Production)",
        invisible=True,
        default=_get_default_requested_by,
        track_visibility="onchange",
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref("purchase_request.group_purchase_request_manager").id,
            )
        ],
    )
    description = fields.Text(string="Remark")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=_company_get,
        track_visibility="onchange",
    )
    line_ids = fields.One2many(
        comodel_name="sale.mrp.line",
        inverse_name="sale_mrp_id",
        string="Products to Manufacture",
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




    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)



    @api.model
    def _get_partner_id(self, request):
        user_id = request.assigned_to or self.env.user
        return user_id.partner_id.id


    def button_draft(self):
        self.mapped("line_ids").do_uncancel()
        return self.write({"state": "draft"})

    def button_approve_sales(self):
        return self.write({"state": "sales_approved"})

    def button_approve_production(self):
        return self.write({"state": "production_approved"})




class SaleMrp(models.Model):
    _name = "sale.mrp.line"
    _description = "Production order from Sales lines"


    sale_mrp_id = fields.Many2one('sale.mrp', "Production from Sales ID")
    product_id = fields.Many2one('product.template',"Product ")
    raw_material = fields.Char(string="Raw Material")
    specification = fields.Char(string="Specification")
    product_qty = fields.Char(string="Requested Quantity")
    done_qty = fields.Char(string="Done Quantity")
    packaging_material = fields.Char(string="Packaging Material")
    #production_request_id=fields.One2many('mrp.production.request','sale_mrp_line_id',string="Production Request")
    def get_sales_mrp_count(self):
        count = self.env['mrp.production.request'].search_count([('sale_mrp_line_id', '=', self.id)])
        self.count = count


    count=fields.Integer("Count",compute="get_sales_mrp_count")