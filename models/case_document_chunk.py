# -*- coding: utf-8 -*-
from odoo import models, fields


class LawCaseDocumentChunk(models.Model):
    _name = 'law.case.document.chunk'
    _description = 'Law Case Document Chunk (for semantic search)'

    document_id = fields.Many2one('law.case.document', string='Document', required=True, ondelete='cascade')

    case_id = fields.Many2one('law.case', string='Case', related='document_id.case_id', store=True, readonly=True)

    chunk_text = fields.Text(string='Chunk Text')

    chunk_index = fields.Integer(string='Chunk Order')
    
    embedding_model = fields.Char(string='Embedding Model Used')