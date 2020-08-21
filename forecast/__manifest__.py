# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'forecast',
    'version': '1.0',
    'website': 'https://www.haile.com/',
    'category': 'Manufacturing/Salesforecast',
    'sequence': 16,
    'summary': 'Salesforecast',
    'depends': ['mrp','inventory_update'],
    'description': "",
    'data': [
        'security/ir.model.access.csv',
        'views/forecast_salesforecast_views.xml',
        'report/forecast_report_views_main.xml',
        'report/forecast_salesforecast.xml',
    ],
    'test': [],
    'application': True,
}
