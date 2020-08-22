import pandas as pd
import pytz
from odoo import fields, models,api


class Canteen(models.Model):
    _name = 'hr.canteen'
    _description = 'Canteen master info'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def list_summary(self):

        list_items=[]
        for re in self.canteen_detail:

             obje = {
                    'employee_id': re.employee_id.id,
                    'price': re.price}
             list_items.append(obje)


        data=pd.DataFrame(list_items)
        grpd=data.groupby('employee_id').agg({'price':'sum'}).reset_index()
        list_grouped=grpd.to_dict('r')

        lst = []
        lst.append((5, 0, 0))
        for re in list_grouped:
            lst.append((0,0,re))
        self.canteen_summary = lst

    name = fields.Char(
        'Periodic Indicator name', copy=False, readonly=False)
    canteen_detail = fields.One2many('hr.canteen.detail', 'canteen_id', 'Canteen List')
    canteen_summary = fields.One2many('hr.canteen.summary', 'canteen_id', 'Canteen Summary')

    state = fields.Selection([
        ('draft', 'Supervisor Approved'), ('cancel', 'Cancelled'),
        ('dept', 'Dept. Approved'), ('hr', 'HR Approved'),
        ('done', 'Done')],
        string='Status', default='draft', readonly=True, required=True, copy=False)

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



class CanteenDetail(models.Model):
    _name = 'hr.canteen.detail'
    _description = 'Canteen Description'

    company_id = fields.Many2one('res.company', string='Company', help="Company")
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    canteen_id = fields.Many2one('hr.canteen', string='Canteen')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    price = fields.Monetary('Price', required=True, store=True, help="Employee's monthly gross wage.")
    canteen_date = fields.Date(string='Date requested', default=fields.Date.today)



class CanteenSummary(models.Model):
    _name = 'hr.canteen.summary'
    _description = 'Canteen Summary'

    company_id = fields.Many2one('res.company', string='Company', help="Company")
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    canteen_id = fields.Many2one('hr.canteen', string='Canteen')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    price = fields.Monetary('Price', required=True, store=True, help="Employee's monthly gross wage.")


class Hr_employee_inherit_(models.Model):
    _inherit = "hr.employee"

    def get_canteen(self, id, start_date, end_date):

        canteen_rec = self.env['hr.canteen.detail'].search(
            [('employee_id', '=', self.id), ('canteen_date', '>=', start_date),
             ('canteen_date', '<=', end_date), ('state', '=', 'done')])
        total = 0.0
        for line in canteen_rec:
                total = total + line.price
        return total*.4