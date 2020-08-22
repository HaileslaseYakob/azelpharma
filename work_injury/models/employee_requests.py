from odoo.exceptions import Warning
from odoo import models, fields, api, _


class EmployeeRequests(models.Model):
    _name = 'hr.employee.request'
    _description = 'Employee Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_employee_domain(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.user.id)], limit=1)
        domain = [('id', '=', employee.id)]
        if self.env.user.has_group('hr.group_hr_user'):
            domain = []
        return domain

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id
            self.resource_calendar_id = self.employee_id.resource_calendar_id
            self.company_id = self.employee_id.company_id

    name = fields.Char(string='Reference')
    employee_id = fields.Many2one('hr.employee', string='Employee',required=True)
    department_id = fields.Many2one('hr.department', string="Department")
    job_id = fields.Many2one('hr.job', string="Job Title")
    request = fields.Text(string='Employee Request')
    requested_date = fields.Datetime(string='Date requested')
    response_given = fields.Text(string='Response Given')
    request_status = fields.Selection([
        ('active_status', 'Active'),
        ('granted', 'Request Granted'),
        ('denied', 'Request Denied'),
    ], string="Status", default='active_status', store=True)
    receiving_employee = fields.Many2one('hr.employee', string='Requested to',
                                  domain=_get_employee_domain, default=lambda self: self.env.user.employee_id.id,
                                  required=False)

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
