# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Job(models.Model):
    _inherit = "hr.job"

    appraisal_survey_id = fields.Many2one(
        'survey.survey', "Appraisal Form",
        domain=[('category', '=', 'hr_appraisal')],
        help="Choose an Apparaisal form for this job position and you will be able to print/answer this to all applicants with this job position")

    probation_survey_id = fields.Many2one(
        'survey.survey', "Probation Form",
        domain=[('category', '=', 'hr_appraisal')],
        help="Choose an Apparaisal form for this job position and you will be able to print/answer this to all applicants with this job position")

    def action_print_survey(self):
        return self.appraisal_survey_id.action_print_survey()
