# -*- coding: utf-8 -*-
###################################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Jesni Banu (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
from datetime import datetime, timedelta
from odoo import models, fields, _, api

GENDER_SELECTION = [('male', 'Male'),
                    ('female', 'Female'),
                    ('other', 'Other')]


class HrDepartmentSection(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.department.section'
    _description = 'Section'
    department_id = fields.Many2one('hr.department', string="Department", help="Department",
                                    required=True)
    name = fields.Char(string='Section')

class HrZone(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.zone'
    _description = 'Zone'
    name = fields.Char(string='Sub city')


class HrSubzone(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.subzone'
    _description = 'Sub zone'
    name = fields.Char(string='Sub zone')



class EmployeeRelationInfo(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.relation'

    name = fields.Char(string="Relationship", help="Relationship with the employee")

class HrVillage(models.Model):
        """Table for keep employee family information"""

        _name = 'hr.employee.village'
        _description = 'Village'
        name = fields.Char(string='Village')

class HrVillage(models.Model):
        """Table for keep employee family information"""

        _name = 'hr.employee.round'
        _description = 'Round'
        name = fields.Char(string='Round')

class HrEmployeeFamilyInfo(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.family'
    _description = 'HR Employee Family'

    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee',
                                  invisible=1)
    member_name = fields.Char(string='Name')
    birth_date = fields.Date(string="DOB", tracking=True)



class HrEmployeeFEmergencyContact(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.emergency'
    _description = 'HR Employee Emergency contact info'

    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee',
                                  invisible=1)
    relation_id = fields.Many2one('hr.employee.relation', string="Relation", help="Relationship with the employee")
    contact_name = fields.Char(string='Name')
    contact_phone = fields.Char(string='Phone No')
    zone = fields.Many2one('hr.employee.zone', string="Zone")
    subzone = fields.Many2one('hr.employee.subzone', string="Sub zone")
    village = fields.Many2one('hr.employee.village', string="Village")
    house_no=fields.Char(string="House No")




class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    section_id = fields.Many2one('hr.department.section', string="Section")
    round_id = fields.Many2one('hr.employee.round', string="Round")
    personal_mobile = fields.Char(string='Mobile', related='address_home_id.mobile', store=True,
                  help="Personal mobile number of the employee")
    mothername = fields.Char(string='Mother Name')
    employee_status = fields.Selection([
        ('permanentstaff', 'Permanent Staff'),
        ('probation1', 'Probation Period 1'),
        ('probation2', 'Probation Period 2'),
        ('nationalservice', 'National Service'),
        ('rcc', 'RCC'),
        ('temporary', 'Temporary'),
        ('terminated', 'Terminated'),
    ], default='permanentstaff', string="Status")


    termination_reason = fields.Selection([
        ('abscond', 'Abscond'),
        ('Demobilized', 'Demobilized'),
        ('Exempted', 'Exempted'),
        ('released', 'Released from EDF'),
        ('resign', 'Resign'),
        ('returntomoh', 'Return to MOH'),
        ('returntoedf', 'Return to EDF'),
        ('returntorcc', 'Return to RCC'),
        ('terminated', 'Terminated'),
        ('sickness', 'Due to sickness'),
    ], default='terminated', string="Termination Reason")
    employee_type = fields.Selection([
        ('civil', 'Civil'),
        ('demobilized', 'Demobilized'),
        ('fighter', 'Fighter'),
        ('nationalservice', 'National Service'),
    ], default='demobilized', string="Status")
    name_tigrigna = fields.Char(string='Tigrigna Name')
    er_id = fields.Char(string='ER ID')
    zone = fields.Many2one('hr.employee.zone', string="Zone")
    subzone = fields.Many2one('hr.employee.subzone', string="Sub zone")
    village = fields.Many2one('hr.employee.village', string="Village")
    house_no=fields.Char(string="House No")
    joining_date = fields.Date(string='Hiring Date', help="Employee joining date computed from the contract start date",compute='compute_joining', store=True)
    id_attachment_id = fields.Many2many('ir.attachment', 'id_attachment_rel', 'id_ref', 'attach_ref',
                                        string="Attachment", help='You can attach the copy of your Id')
    passport_attachment_id = fields.Many2many('ir.attachment', 'passport_attachment_rel', 'passport_ref', 'attach_ref1',
                                              string="Attachment",
                                              help='You can attach the copy of Passport')
    fam_ids = fields.One2many('hr.employee.family', 'employee_id', string='Family', help='Family Information')
    emergency_contact_ids = fields.One2many('hr.employee.emergency', 'employee_id', string='Emergency contact', help='Emergency contact info')

    @api.depends('contract_id')
    def compute_joining(self):
        if self.contract_id:
            date = min(self.contract_id.mapped('date_start'))
            self.joining_date = date
        else:
            self.joining_date = False

    @api.onchange('spouse_complete_name', 'spouse_birthdate')
    def onchange_spouse(self):
        relation = self.env.ref('hr_employee_updation.employee_relationship')
        lines_info = []
        spouse_name = self.spouse_complete_name
        date = self.spouse_birthdate
        if spouse_name and date:
            lines_info.append((0, 0, {
                'member_name': spouse_name,
                'relation_id': relation.id,
                'birth_date': date,
            })
                              )
            self.fam_ids = [(6, 0, 0)] + lines_info


class SalaryGrade(models.Model):
    _name = "hr.grade"
    _description = "Salary Grade"

    name = fields.Char("Grade name")
    salary_grade_levels=fields.One2many('hr.grade.levels','salary_grade_id',"Grade Levels")


class SalaryGradeLevels(models.Model):
    _name = "hr.grade.levels"
    _description = "Grade levels"

    salary_grade_id = fields.Many2one('hr.grade', string='Grade')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    name = fields.Char("Level name")
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    wage = fields.Monetary('Wage', required=True, tracking=True, help="Employee's monthly gross wage.")


class HrEmployee(models.Model):
    _inherit = 'hr.job'

    no_of_recruitment = fields.Integer(string='Expected New', copy=False,
        help='Number of new employees you expect to recruit.', default=1)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    salary_grade_id = fields.Many2one('hr.grade', string="Grade")
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type")
    scheduled_on_budget = fields.Integer("Scheduled on Budget")
    experience_required=fields.Char("Experience required")
    education_required = fields.Char("Education required")
    @api.depends('scheduled_on_budget','no_of_employee')
    def _compute_vaccant(self):
       for cur in self:
            if not cur.scheduled_on_budget:
                cur.scheduled_on_budget=0

            vaccants = cur.scheduled_on_budget - cur.no_of_employee
            if vaccants < 1:
               vaccants=0
            cur.vaccant=vaccants

    vaccant = fields.Integer("vaccant", compute='_compute_vaccant',store=True)


