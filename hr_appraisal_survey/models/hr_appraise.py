# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Appraise(models.Model):
    _inherit = "hr.appraisal"
    job_id = fields.Many2one('hr.job', string="Job", related="employee_id.job_id")
    probation_id = fields.Many2one('survey.survey', related='job_id.appraisal_survey_id', string="Probation Survey",
                                readonly=True)
    survey_id = fields.Many2one('survey.survey', related='job_id.probation_survey_id', string="Appraisal Survey", readonly=True)
    response_id = fields.Many2one('survey.user_input', "Response", ondelete="set null")
    quiz_score=fields.Float("Appraisal score", related='response_id.quizz_score')
    probation_appraisal=fields.Boolean("Probation appraisal")
    def action_start_survey(self):
        self.ensure_one()
        # create a response and link it to this applicant
        if not self.response_id:
            if self.probation_appraisal:
                response = self.probation_id._create_answer(partner=self.env.user.partner_id)
            else:
                response = self.survey_id._create_answer(partner=self.env.user.partner_id)
            self.response_id = response.id
        else:
            response = self.response_id
        # grab the token of the response and start surveying
        return self.survey_id.with_context(survey_token=response.token).action_start_survey()

    def action_print_survey(self):
        """ If response is available then print this response otherwise print survey form (print template of the survey) """
        self.ensure_one()
        if not self.response_id:
            return self.survey_id.action_print_survey()
        else:
            response = self.response_id
            return self.survey_id.with_context(survey_token=response.token).action_print_survey()
