from odoo.exceptions import Warning
from odoo import models, fields, api, _

# class ExpenseUpdate(models.Model):
#     _inherit = 'hr.expense'
#
#
#     suspense_id = fields.Many2one('hr.suspense', string="Related Suspense")

class WorkInjury(models.Model):
    _name = 'work.injury'
    _description = 'Work Injury'
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

    location = fields.Char(string='Injury Location')
    description = fields.Text(string='Incident description')
    date_injury = fields.Datetime(string='Accident Date and Time')
    supervisor_name = fields.Many2one('hr.employee', string='Supervisor name',
                                  domain=_get_employee_domain, default=lambda self: self.env.user.employee_id.id,
                                  required=False)

    date_hr_notified = fields.Date(string='HR notified Date and Time')

    state = fields.Selection([
        ('draft', 'Supervisor Approved'), ('cancel', 'Cancelled'),
        ('dept', 'Dept. Approved'), ('hr', 'HR Approved'),
        ('confirm', 'GM Confirmed'), ('done', 'Done')],
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

    def button_confirm(self):
        self.write({'state': 'confirm'})

class ClinicName(models.Model):
    _name = 'work.injury.clinic'
    _description = 'Clinic Name'

    name = fields.Char(string='Name')

class ClinicReport(models.Model):
    _name = 'work.injury.clinic.report'
    _description = 'Clinic report'
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
    remark = fields.Text(string='Remark')
    date_sent = fields.Datetime(string='Sent on')
    clinic_id = fields.Many2one('work.injury.clinic', string='Clinic',required=True)
    supervisor_name = fields.Many2one('hr.employee', string='Sent By',
                                  domain=_get_employee_domain, default=lambda self: self.env.user.employee_id.id,
                                  required=False)

    state = fields.Selection([
        ('draft', 'Supervisor Approved'), ('cancel', 'Cancelled'),
        ('dept', 'Dept. Approved'), ('hr', 'HR Approved'),
        ('confirm', 'GM Confirmed'), ('done', 'Done')],
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

    def button_confirm(self):
        self.write({'state': 'confirm'})



