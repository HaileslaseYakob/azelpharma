# Copyright (C) 2017 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import api, fields, models


class Manufacturer(models.Model):
    _name = 'manufacturer'

    name = fields.Char("Name")


class Countr(models.Model):
    _name = 'countr'

    name = fields.Char("Name")

class BatchCategory(models.Model):
    _name = 'batch.category'

    name = fields.Char("Name")
    product_id=fields.Many2one("product.product")

class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    firmware_version = fields.Char(string="Firmware Version")
    batch_no = fields.Char(string="Batch No ")

    batch_category = fields.Many2one('batch.category', string="Brand",domain="[('product_id','=',product_id)]")
    ref = fields.Char('Code',
                      help="Internal reference number in case it differs from the manufacturer's lot/serial number")
    picasso_number=fields.Char("Picasso Number")
    i_v = fields.Char("Intrinsic Viscosity")

    manf = fields.Many2one('manufacturer', string="Manufacturer ")
    originc = fields.Many2one('countr', string="Country of Origin ")
    prodDate = fields.Date(string="Production Date ")
    expDate = fields.Date(string="Expiry Date")
    reanalysis_date = fields.Date(string="Reanalysis Date")
    supplier_invoice_no = fields.Char(string="Supplier Invoice No.")
    priority = fields.Integer(string="Priority.")
    barrel = fields.Integer(string="No of Barrels.")
    qc_no = fields.Char(string="QC No ")
    name = fields.Char(
        'Lot/Serial Number',
        required=True, help="Unique Lot/Serial Number")

    @api.onchange('product_id')
    def product_changed(self):
        self.with_context(default_prod_id=self.product_id.id)


    @api.onchange('batch_category','ref','i_v')
    def batch_category_changed(self):
        self.name = ""
        if self.batch_category:
            self.name = self.batch_category.name
        if self.ref and self.i_v:
            self.name = self.name + "(" + self.ref + "-" + self.i_v + ")"
        elif self.i_v:
            self.name = self.name+ "(" + self.i_v + ")"
        elif self.ref:
            self.name = self.name + "(" + self.ref + ")"


    @api.onchange('batch_no')
    def batch_no_changed(self):
        self.name = ""
        if self.batch_no and self.qc_no:
            self.name = self.qc_no + "(" + self.batch_no + ")"
        elif self.batch_no:
            self.name = self.batch_no
        elif self.qc_no:
            self.name = self.qc_no

    @api.onchange('qc_no')
    def qc_no_changed(self):
        self.name = ""
        if self.batch_no and self.qc_no:
            self.name = self.qc_no + "(" + self.batch_no + ")"
        elif self.batch_no:
            self.name = self.batch_no
        elif self.qc_no:
            self.name = self.qc_no


    def _domain_product_id(self):
        domain = [
            "('tracking', '!=', 'none')",
            "'|'",
                "('company_id', '=', False)",
                "('company_id', '=', company_id)"
        ]
        if self.env.context.get('default_product_tmpl_id'):
            domain.insert(0,
                ("('product_tmpl_id', '=', %s)" % self.env.context['default_product_tmpl_id'])
            )
        return '[' + ', '.join(domain) + ']'


class QualityTestMaster(models.Model):
    _name = "quality.test.master"

    name = fields.Char(string="Test Name.")




class QualityTestInventory(models.Model):
    _name = "quality.testtype.inventory"

    quality_test_master_id = fields.Many2one('quality.test.master')
    name = fields.Char('Test Code.')
    desc = fields.Char(string='Description')
    product_id = fields.Many2one('product.template')


class QualityTests(models.Model):
    _name = "quality.test"

    @api.onchange('quality_test_master_id')
    def onchange_product_id(self):

        list_master_ids = self.env['quality.testtype.inventory'].search([('product_id', '=',
                                                                          self._context.get('product_id'))])
        master_list = []
        for lst in list_master_ids:
            master_list.append(lst.quality_test_master_id.id)
        if self.quality_test_master_id:
            return {'domain': {'quality_test_master_id': [('id', 'in', master_list)],
                               'quality_testtype_inventory_id': ['&',('quality_test_master_id', '=', self.quality_test_master_id.id),
                                                                 ('product_id', '=',self._context.get('product_id'))]}}
        else:
            return {'domain': {'quality_test_master_id': [('id', 'in', master_list)],
                               'quality_testtype_inventory_id': [('quality_test_master_id', '=', self.quality_test_master_id.id)]}}

    quality_test_master_id = fields.Many2one('quality.test.master')
    quality_testtype_inventory_id = fields.Many2one('quality.testtype.inventory')
    quality_test_desc = fields.Char(related='quality_testtype_inventory_id.desc')
    result = fields.Char('Result')
    quality_check_id = fields.Many2one("quality.check")


class QualityCheckUpdate(models.Model):
    _inherit = "quality.check"

    @api.depends('picking_id')
    def _testthis(self):
        if self.picking_id:
            pickinglist = self.env['stock.move.line'].search([
                ('picking_id', '=', self.picking_id.id)])
            thelist = []
            for x in pickinglist:
                thelist.append(x.lot_id.id)
            domain = [('id', 'in', thelist)]
            return domain

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Set the correct label for `unit_amount`, depending on company UoM """
        result = super(QualityCheckUpdate, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                                 submenu=submenu)
        self._testthis()
        return result

    @api.model
    def view_init(self, fields):
        pickinglist = self.env['stock.move.line'].search([
            ('picking_id', '=', self.picking_id.id)])
        thelist = []
        for x in pickinglist:
            thelist.append(x.lot_id.id)
        domain = {'lot_id': [('id', 'in', thelist)]}
        return {'domain': domain}

    @api.onchange('product_id')
    def onchange_produt_id(self):
        self.quality_tests=[(5, 0, 0)]

    reanalysisDate = fields.Date(string="Reanalysis Date")
    remark = fields.Char(string="Remark.")
    pname = fields.Char(related='product_id.name')
    quality_tests = fields.One2many('quality.test', 'quality_check_id')
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot', domain=_testthis)

    # @api.model
    # def default_get(self, fields):
    #     res = super(MrpProductProduce, self).default_get(fields)

    @api.onchange('product_id')
    def _onchange_pr_id(self):
        pickinglist = self.env['stock.move.line'].search([
            ('picking_id', '=', self.picking_id.id)])
        thelist = []
        for x in pickinglist:
            thelist.append(x.lot_id.id)
        domain = {'lot_id': [('id', 'in', thelist)]}
        return {'domain': domain}

    @api.onchange('picking_id')
    def _onchange_pro_id(self):
        if self.product_id and self.picking_id:
            pickinglist = self.env['stock.move.line'].search([
                ('picking_id', '=', self.picking_id.id)])
            thelist = []
            for x in pickinglist:
                thelist.append(x.lot_id.id)
            domain = {'lot_id': [('id', 'in', thelist)]}
            return {'domain': domain}

    def do_pass(self):
        if self.lot_id:
            self.lot_id.qc_no = self.name
            self.lot_id.name = self.name + "(" + self.lot_id.batch_no + ")"
        self.write({'quality_state': 'pass',
                    'user_id': self.env.user.id,
                    'control_date': datetime.now()})
        if self.env.context.get('no_redirect'):
            return True
        return self.redirect_after_pass_fail()

    def do_fail(self):
        if self.lot_id:
            self.lot_id.qc_no = self.name
            self.lot_id.name = self.name + "(" + self.lot_id.batch_no + ")"

        self.write({
            'quality_state': 'fail',
            'user_id': self.env.user.id,
            'control_date': datetime.now()})
        if self.env.context.get('no_redirect'):
            return True
        return self.redirect_after_pass_fail()
