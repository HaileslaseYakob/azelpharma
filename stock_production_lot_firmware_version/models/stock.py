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


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    firmware_version = fields.Char(string="Firmware Version")
    batch_no = fields.Char(string="Batch No ")
    manf = fields.Many2one('manufacturer', string="Manufacturer ")
    originc = fields.Many2one('countr', string="Country of Origin ")
    prodDate = fields.Date(string="Production Date ")
    expDate = fields.Date(string="Expiry Date")
    supplier_invoice_no = fields.Char(string="Supplier Invoice No.")
    priority = fields.Integer(string="Priority.")
    barrel = fields.Integer(string="No of Barrels.")
    qc_no = fields.Char(string="QC No ")
    name = fields.Char(
        'Lot/Serial Number',
        required=True, help="Unique Lot/Serial Number")

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


class QualityTestMaster(models.Model):
    _name = "quality.test.master"

    name = fields.Char(string="Test Name.")


class QualityTestType(models.Model):
    _name = "quality.test.type"

    name = fields.Char(string="Test code.")
    quality_test_master_id = fields.Char('Test Name.')
    desc = fields.Char(string="Test Description.")


class QualityTestInventory(models.Model):
    _name = "quality.testtype.inventory"



    quality_test_type_id = fields.Many2one('quality.test.type')
    quality_test_master_id = fields.Char('Test Name.')
    desc = fields.Char(related='quality_test_type_id.desc')
    product_id = fields.Many2one('product.template')


class QualityTests(models.Model):
    _name = "quality.test"


    @api.onchange('quality_test_master_id')
    def onchange_product_id(self):
        list_master_ids = self.env['quality.testtype.inventory'].search([('product_id', '=',
                                                                        self._context.get('product_id'))])
        master_list = []
        type_list = []
        for lst in list_master_ids:
            master_list.append(lst.quality_test_master_id)
            type_list.append(lst.quality_test_type_id.id)
        if self.quality_test_master_id:
            return {'domain': {'quality_test_master_id': [('name', 'in', master_list)],
                               'quality_test_type_id': ['&',('id', 'in', type_list),('quality_test_master_id', '=', self.quality_test_master_id.name)]]}}
        else:
            return {'domain': {'quality_test_master_id': [('name', 'in', master_list)],
                               'quality_test_type_id': [('id', 'in', type_list)]}}

    quality_test_master_id = fields.Many2one('quality.test.master')
    quality_item_id = fields.Many2one('quality.testtype.inventory')
    quality_test_type_id = fields.Many2one('quality.test.type')
    quality_test_desc = fields.Char(related='quality_test_type_id.desc')
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

    reanalysisDate = fields.Date(string="Reanalysis Date")
    remark = fields.Char(string="Remark.")
    pname=fields.Char(related='product_id.name')
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
        self.lot_id.qc_no = self.name
        self.lot_id.name = self.name + "(" + self.lot_id.batch_no + ")"
        self.write({'quality_state': 'pass',
                    'user_id': self.env.user.id,
                    'control_date': datetime.now()})
        if self.env.context.get('no_redirect'):
            return True
        return self.redirect_after_pass_fail()

    def do_fail(self):
        self.lot_id.qc_no = self.name
        self.lot_id.name = self.name + "(" + self.lot_id.batch_no + ")"

        self.write({
            'quality_state': 'fail',
            'user_id': self.env.user.id,
            'control_date': datetime.now()})
        if self.env.context.get('no_redirect'):
            return True
        return self.redirect_after_pass_fail()
