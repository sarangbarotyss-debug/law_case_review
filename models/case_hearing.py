# -*- coding: utf-8 -*-
from odoo import models, fields


class LawCaseHearing(models.Model):
    _name = 'law.case.hearing'
    _description = 'Law Case Hearing'
    _order = 'hearing_date asc'

    case_id = fields.Many2one('law.case', string='Case', required=True, ondelete='cascade')
    hearing_date = fields.Date(string='Hearing Date', required=True)
    court = fields.Char(string='Court')
    judge = fields.Char(string='Judge')
    notes = fields.Text(string='Notes / Outcome')