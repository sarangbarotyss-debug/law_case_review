# -*- coding: utf-8 -*-
from odoo import models, fields


class LawCaseQALog(models.Model):
    _name = 'law.case.qa.log'
    _description = 'Law Case Question Answer Log'
    _order = 'create_date desc'

    case_id = fields.Many2one('law.case', string='Case', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Asked By', default=lambda self: self.env.user, readonly=True)
    question = fields.Text(string='Question', required=True)
    answer = fields.Text(string='Answer')
    source_write_date = fields.Datetime(string='Case Snapshot Date')
    cited_chunk_ids = fields.Many2many('law.case.document.chunk', string='Cited Document Sections')
    cited_clause_ids = fields.Many2many('law.playbook.clause', string='Cited Playbook Clauses')
    hidden_from_chat = fields.Boolean(string='Cleared From Chat', default=False)