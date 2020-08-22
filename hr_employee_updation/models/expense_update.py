from odoo.exceptions import Warning
from odoo import models, fields, api, _

class ExpenseUpdate(models.Model):
    _inherit = 'hr.expense'


    suspense_id = fields.Many2one('hr.suspense', string="Related Suspense")

class SuspenseEntry(models.Model):
    _name = 'hr.suspense'
    _description = 'Employee suspense'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name=fields.Char('Reference no. ')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    required_for = fields.Char(string='Required for')
    amount = fields.Float(string='Amount')
    state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('dept', 'Dept. Approved'), ('hr', 'HR Approved'),
        ('confirm', 'Confirmed'), ('done', 'Done')],
        string='Status', default='draft', readonly=True, required=True, copy=False,
        help="If event is created, the status is 'Draft'. If event is confirmed for the particular dates the status is set to 'Confirmed'. If the event is over, the status is set to 'Done'. If event is cancelled the status is set to 'Cancelled'.")
    expense_id = fields.One2many('hr.expense','suspense_id', string="Suspense",readonly=True)

    def button_draft(self):
        self.write({'state': 'draft'})

    def button_cancel(self):
        self.write({'state': 'cancel'})

    def button_done(self):
        self.write({'state': 'done'})

    def button_dept(self):
        self.write({'state': 'dept'})

    def button_hr(self):
        self.write({'state': 'hr'})

    def button_confirm(self):
        self.write({'state': 'confirm'})



