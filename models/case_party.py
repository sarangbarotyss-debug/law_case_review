# -*- coding: utf-8 -*-
from odoo import models, fields


class LawCaseParty(models.Model):
    _name = 'law.case.party'
    _description = 'Law Case Party'

    case_id = fields.Many2one('law.case', string='Case', required=True, ondelete='cascade')
    name = fields.Char(string='Name', required=True)
    role = fields.Selection([
        ('plaintiff', 'Plaintiff'),
        ('defendant', 'Defendant'),
        ('petitioner', 'Petitioner'),
        ('respondent', 'Respondent'),
        ('witness', 'Witness'),
        ('opposing_counsel', 'Opposing Counsel'),
        ('other', 'Other'),
    ], string='Role', required=True)
    contact_phone = fields.Char(string='Phone')
    contact_email = fields.Char(string='Email')
    notes = fields.Text(string='Notes')