# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LawCasePlaybookMatch(models.Model):
    _name = 'law.case.playbook.match'
    _description = 'Law Case Playbook Comparison Result'
    _order = 'match_type_sequence asc, score desc'

    case_id = fields.Many2one('law.case', string='Case', required=True, ondelete='cascade')
    clause_id = fields.Many2one('law.playbook.clause', string='Matched Clause', required=True, ondelete='cascade')
    match_type = fields.Selection([
        ('violation', 'Potential Violation'),
        ('defense', 'Supports Defense'),
        ('related', 'Related / Contextual'),
    ], string='Match Type', required=True)
    explanation = fields.Text(string='AI Explanation')
    score = fields.Float(string='Similarity Score')
    confidence = fields.Selection([
        ('strong', 'Strong Match'),
        ('possible', 'Possible Match'),
    ], string='Confidence')
    match_type_sequence = fields.Integer(
        string='Match Type Priority',
        compute='_compute_match_type_sequence',
        store=True,
    )

    clause_number = fields.Char(related='clause_id.clause_number', string='Clause Number', readonly=True)
    clause_title = fields.Char(related='clause_id.title', string='Clause Title', readonly=True)

    _MATCH_TYPE_PRIORITY = {
        'violation': 1,
        'defense': 2,
        'related': 3,
    }

    @api.depends('match_type')
    def _compute_match_type_sequence(self):
        for record in self:
            record.match_type_sequence = self._MATCH_TYPE_PRIORITY.get(record.match_type, 99)