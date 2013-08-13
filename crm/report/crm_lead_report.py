# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp import tools
from openerp.addons.crm import crm

MONTHS = [
    ('01', 'January'),
    ('02', 'February'),
    ('03', 'March'),
    ('04', 'April'),
    ('05', 'May'),
    ('06', 'June'),
    ('07', 'July'),
    ('08', 'August'),
    ('09', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December')
]

class crm_lead_report(osv.osv):
    """ CRM Lead Analysis """
    _name = "crm.lead.report"
    _auto = False
    _description = "CRM Lead Analysis"
    _rec_name = 'deadline_day'

    def _compute_amounts_in_user_currency(self, cr, uid, ids, field_names=[], args={}, context=None):
        """Compute the amounts in the currency of the user
        """
        res = {}
        currency_obj = self.pool.get('res.currency')
        user_currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = {
                'user_currency_planned_revenue': currency_obj.compute(cr, uid, item.company_id.currency_id.id, user_currency_id, item.planned_revenue, context=context),
                'user_currency_probable_revenue': currency_obj.compute(cr, uid, item.company_id.currency_id.id, user_currency_id, item.probable_revenue, context=context),
            }
        return res

    _columns = {
        # grouping fields based on Deadline Date
        'deadline_year': fields.char('Ex. Closing Year', size=10, readonly=True, help="Expected closing year"),
        'deadline_month':fields.selection(MONTHS, 'Exp. Closing Month', readonly=True, help="Expected closing month"),
        'deadline_day': fields.char('Exp. Closing Day', size=10, readonly=True, help="Expected closing day"),

        # grouping fields based on Create Date
        'creation_year': fields.char('Creation Year', size=10, readonly=True, help="Creation year"),
        'creation_month': fields.selection(MONTHS, 'Creation Month', readonly=True, help="Creation month"),
        'creation_day': fields.char('Creation Day', size=10, readonly=True, help="Creation day"),

        # other date fields
        'create_date': fields.datetime('Create Date', readonly=True),
        'opening_date': fields.date('Assignation Date', readonly=True),
        'date_closed': fields.date('Close Date', readonly=True),
        'date_last_stage_update': fields.datetime('Last Stage Update', readonly=True),

        # durations
        'delay_open': fields.float('Delay to Assign',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to open the case"),
        'delay_close': fields.float('Delay to Close',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'delay_expected': fields.float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg"),

        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'country_id':fields.many2one('res.country', 'Country', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Sales Team', readonly=True),
        'channel_id':fields.many2one('crm.case.channel', 'Channel', readonly=True),
        'type_id':fields.many2one('crm.case.resource.type', 'Campaign', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'probability': fields.float('Probability',digits=(16,2),readonly=True, group_operator="avg"),
        'planned_revenue': fields.float('Planned Revenue',digits=(16,2),readonly=True),
        'user_currency_planned_revenue': fields.function(_compute_amounts_in_user_currency, string="Planned Revenue", type='float',digits=(16,2), multi="_compute_amounts", readonly=True),
        'probable_revenue': fields.float('Probable Revenue', digits=(16,2),readonly=True),
        'user_currency_probable_revenue': fields.function(_compute_amounts_in_user_currency, string="Probable Revenue", type='float',digits=(16,2), multi="_compute_amounts",readonly=True),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', readonly=True, domain="[('section_ids', '=', section_id)]"),
        'partner_id': fields.many2one('res.partner', 'Partner' , readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'type':fields.selection([
            ('lead','Lead'),
            ('opportunity','Opportunity'),
        ],'Type', help="Type is used to separate Leads and Opportunities"),
    }

    #FIX:To show sum of values of function fields in groupby
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        res = super(crm_lead_report, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby)
        for group in res:
            group['user_currency_probable_revenue'] = 0
            group['user_currency_planned_revenue'] = 0
            if group.get('__domain'):
                group_ids = self.search(cr, uid, group.get('__domain'),context=context)
                record = self._compute_amounts_in_user_currency(cr, uid, group_ids, context=context)
                for id, rec in record.iteritems():
                    group['user_currency_planned_revenue'] += rec['user_currency_planned_revenue']
                    group['user_currency_probable_revenue'] += rec['user_currency_probable_revenue']
        return res
    
    def init(self, cr):
        """
            CRM Lead Report
            @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(cr, 'crm_lead_report')
        cr.execute("""
            CREATE OR REPLACE VIEW crm_lead_report AS (
                SELECT
                    id,
                    to_char(c.date_deadline, 'YYYY') as deadline_year,
                    to_char(c.date_deadline, 'MM') as deadline_month,
                    to_char(c.date_deadline, 'YYYY-MM-DD') as deadline_day,

                    to_char(c.create_date, 'YYYY') as creation_year,
                    to_char(c.create_date, 'MM') as creation_month,
                    to_char(c.create_date, 'YYYY-MM-DD') as creation_day,

                    to_char(c.date_open, 'YYYY-MM-DD') as opening_date,
                    to_char(c.date_closed, 'YYYY-mm-dd') as date_closed,

                    date_trunc('day',c.date_last_stage_update) as date_last_stage_update,

                    c.user_id,
                    c.probability,
                    c.stage_id,
                    c.type,
                    c.company_id,
                    c.priority,
                    c.section_id,
                    c.channel_id,
                    c.type_id,
                    c.partner_id,
                    c.country_id,
                    c.planned_revenue,
                    c.planned_revenue*(c.probability/100) as probable_revenue,
                    1 as nbr,
                    date_trunc('day',c.create_date) as create_date,
                    extract('epoch' from (c.date_closed-c.create_date))/(3600*24) as  delay_close,
                    abs(extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24)) as  delay_expected,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open
                FROM
                    crm_lead c
                WHERE c.active = 'true'
            )""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
