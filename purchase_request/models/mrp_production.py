# Copyright 2017 Eficent Business and IT Consulting Services S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime, date


from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools import float_compare


class InheritBom(models.Model):
    _inherit = 'mrp.bom'

    product_tmpl_id = fields.Many2one(
        'product.template', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('categ_id', '=', 1), ('company_id', '=', company_id)]",
        required=True)

class MrpProduction(models.Model):
    _inherit = "mrp.production"
    @api.model
    def _get_default_name(self):
        return self.env["ir.sequence"].next_by_code("mrp.batch")
    def action_confirm(self):
        self.batch_no = self._get_default_name()
        super().action_confirm()
    batch_no=fields.Char(
        string="Batch No")