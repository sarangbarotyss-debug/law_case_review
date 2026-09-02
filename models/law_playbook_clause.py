# -*- coding: utf-8 -*-
from odoo import models, fields


class LawPlaybookClause(models.Model):
    _name = 'law.playbook.clause'
    _description = 'Law Playbook Clause'

    source_id = fields.Many2one('law.playbook.source', string='Source', required=True, ondelete='cascade')
    clause_number = fields.Char(string='Clause Number', required=True)
    title = fields.Char(string='Title')
    text = fields.Text(string='Full Text', required=True)

    
    embedding_model = fields.Char(string='Embedding Model Used')