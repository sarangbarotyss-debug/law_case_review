# -*- coding: utf-8 -*-
from odoo import models, fields
from .playbook_ingestion_service import split_and_dispatch_chunks, process_single_chunk

class LawPlaybookSource(models.Model):
    _name = 'law.playbook.source'
    _description = 'Law Playbook Source Document'


    name = fields.Char(string='Title', required=True)

    source_type = fields.Selection([
        ('constitution', 'Constitution'),
        ('statute', 'Statute / Act'),
        ('regulation', 'Regulation'),
        ('other', 'Other'),
    ], string='Source Type', default='other')

    file = fields.Binary(string='File', attachment=True)

    file_name = fields.Char(string='File Name')

    ocr_text = fields.Text(string='Extracted Text')

    state = fields.Selection([
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='Status', default='uploaded')

    clause_ids = fields.One2many('law.playbook.clause', 'source_id', string='Clauses')

    clause_count = fields.Integer(string='Clause Count', compute='_compute_clause_count')

    chunk_count = fields.Integer(string='Total Chunks', default=0, readonly=True)
    
    chunk_done_count = fields.Integer(string='Chunks Completed', default=0, readonly=True)

    def _compute_clause_count(self):
        for record in self:
            record.clause_count = len(record.clause_ids)

    def action_view_clauses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Clauses',
            'res_model': 'law.playbook.clause',
            'view_mode': 'list,form',
            'domain': [('source_id', '=', self.id)],
        }

    def action_process(self):
        self.ensure_one()
        if not self.file:
            from odoo.exceptions import UserError
            raise UserError("Please upload a file before processing.")
        self.with_delay(description="Process playbook source: %s" % self.name).button_process_job()

    def button_process_job(self):
        self.ensure_one()
        split_and_dispatch_chunks(self.env, self)

    def button_process_chunk_job(self, chunk_index, chunk_text):
        self.ensure_one()
        process_single_chunk(self.env, self, chunk_index, chunk_text)