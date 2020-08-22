# -*- coding: utf-8 -*-
{
    'name': "Hr Appraisal  Forms",
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Surveys',
    'description': """
        Use Appraisal forms during appraisal process.
        This module is integrated with the survey module
        to allow you to define forms for different jobs.
    """,
    'depends': ['survey', 'hr_appraisal' , 'hr_recruitment'],
    'data': [
        'security/hr_appraisal_survey_security.xml',
        'views/hr_job_views.xml',
        'views/hr_applicant_views.xml',
        'views/survey_survey_views.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
}
