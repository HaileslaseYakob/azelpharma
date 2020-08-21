# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EmployeeMasterInherit(models.Model):
    _inherit = 'purchase.order'


    @api.depends('entry_checklist')
    def entry_progress(self):
        for each in self:
            total_len = self.env['purchase.checklist'].search_count([('document_type', '=', 'entry')])
            entry_len = len(each.entry_checklist)
            if total_len != 0:
                each.entry_progress = (entry_len * 100) / total_len

    entry_checklist = fields.Many2many('purchase.checklist', 'entry_objj', 'check_hr_re', 'hr_check_re',
                                       string='Entry Process',
                                       domain=[('document_type', '=', 'entry')], help="Entry Checklist's")

    entry_progress = fields.Float(compute=entry_progress, string='Entry Progress', store=True, default=0.0,
                                  help="Percentage of Entry Checklists's")

    maximum_rate = fields.Integer(default=100)
    check_list_enable = fields.Boolean(invisible=True, copy=False)


class EmployeeDocumentInherit(models.Model):
    _inherit = 'purchase.order.document'

    @api.model
    def create(self, vals):
        result = super(EmployeeDocumentInherit, self).create(vals)
        if result.document_name.document_type == 'entry':
            result.purchase_ref.write({'entry_checklist': [(4, result.document_name.id)]})
        return result

    def unlink(self):
        for result in self:
            if result.document_name.document_type == 'entry':
                result.purchase_ref.write({'entry_checklist': [(5, result.document_name.id)]})
        res = super(EmployeeDocumentInherit, self).unlink()
        return res


class EmployeeChecklistInherit(models.Model):
    _inherit = 'purchase.checklist'

    entry_objj = fields.Many2many('purchase.order', 'entry_checklist', 'hr_check_re', 'check_hr_re',
                                 invisible=1)
