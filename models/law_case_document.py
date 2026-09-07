# -*- coding: utf-8 -*-
import base64
import requests
import json
from odoo.exceptions import UserError
from ..services import ai_provider_service
from odoo import models, fields, api, _


class LawCaseDocument(models.Model):
    _name = 'law.case.document'
    _description = 'Law Case Document'

    name = fields.Char(string='Document Name', required=True)
    case_id = fields.Many2one('law.case', string='Case', required=True, ondelete='cascade', readonly=True)
    document_type = fields.Selection([
        ('filing', 'Filing'),
        ('evidence', 'Evidence'),
        ('correspondence', 'Correspondence'),
        ('court_order', 'Court Order'),
        ('other', 'Other'),
    ], string='Document Type', default='other')
    file = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    state = fields.Selection([
        ('uploaded', 'Uploaded'),
        ('extracting', 'Extracting'),
        ('pending_review', 'Pending Review'),
        ('confirmed', 'Confirmed'),
        ('error', 'Error'),
    ], string='Status', default='uploaded')
    ocr_text = fields.Text(string='Extracted Text')
    extracted_case_number = fields.Char(string='Case Number')
    extracted_client_name = fields.Char(string='Client Name')
    extracted_filing_date = fields.Char(string='Filing Date')
    timeline_extracted = fields.Boolean(string='Timeline Extracted', default=False, copy=False)
    timeline_extraction_queued = fields.Boolean(string='Timeline Extraction Queued', default=False, copy=False)
    text_extraction_queued = fields.Boolean(string='Text Extraction Queued', default=False, copy=False)

    def write(self, vals):
        result = super().write(vals)
        if vals.get('state') == 'confirmed':
            from .case_document_ingestion_service import chunk_and_embed_document
            for doc in self:
                chunk_and_embed_document(self.env, doc)
                doc.case_id._touch_qa_content_version()
        return result

    def unlink(self):
        cases = self.filtered(lambda d: d.state == 'confirmed').mapped('case_id')
        result = super().unlink()
        cases._touch_qa_content_version()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for doc in records:
            if doc.file and doc.case_id.dms_directory_id:
                self.env['dms.file'].create({
                    'name': (doc.file_name or doc.name).replace('/', '-'),
                    'directory_id': doc.case_id.dms_directory_id.id,
                    'content': doc.file,
                })
        return records

    def action_extract_text_async(self):
        for doc in self:
            if not doc.file:
                raise UserError('Please upload a file first.')
            doc.text_extraction_queued = True
            doc.with_delay(description='Extract text for %s' % doc.name).action_extract_text_job()

    def action_extract_text_job(self):
        self.ensure_one()
        try:
            self.action_extract_text()
        finally:
            self.text_extraction_queued = False

    def action_extract_text(self):
        self.ensure_one()
        if not self.file:
            raise UserError('Please upload a file first.')

        try:
            file_content = base64.b64decode(self.file)
            docling_url = self.env['ir.config_parameter'].sudo().get_param(
                'law_case_review.docling_service_url', default='http://localhost:8500'
            )
            response = requests.post(
                f'{docling_url}/extract-text',
                files={'file': (self.file_name, file_content)},
                timeout=1800,
            )
            if response.status_code != 200:
                self.state = 'error'
                raise UserError('OCR extraction failed.')

            ocr_text = response.json().get('text') or ''
            prompt = (
                "Read this document text and extract the following fields as JSON only, "
                "with no extra explanation, no markdown, just raw JSON:\n"
                "{\"case_number\": \"\", \"client_name\": \"\", \"filing_date\": \"\"}\n\n"
                "Document text:\n" + ocr_text
            )
            answer = ai_provider_service.call_llm(self.env, prompt)
            extracted_data = json.loads(answer)
            self.write({
                'ocr_text': ocr_text,
                'extracted_case_number': extracted_data.get('case_number'),
                'extracted_client_name': extracted_data.get('client_name'),
                'extracted_filing_date': extracted_data.get('filing_date'),
                'state': 'confirmed',
            })
        except UserError:
            raise
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'law_case_review',
                'type': 'server',
                'level': 'ERROR',
                'message': 'Text extraction failed for document %s: %s' % (self.id, str(e)),
                'path': 'law_case_review.law_case_document',
                'func': 'action_extract_text',
                'line': '0',
            })
            self.state = 'error'
            raise UserError('Extraction failed unexpectedly.')

    def action_save_new(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'law.case.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_case_id': self.case_id.id},
        }

    def action_extract_timeline(self):
        from ..services import timeline_extraction_service
        for doc in self:
            if not doc.case_id:
                continue
            events = timeline_extraction_service.extract_timeline_events(self.env, doc)
            for event in events:
                event['case_id'] = doc.case_id.id
                event['document_id'] = doc.id
                event['state'] = 'draft'
            if events:
                self.env['law.case.timeline.event'].create(events)
            doc.timeline_extracted = True

    def action_extract_timeline_async(self):
        for doc in self:
            doc.timeline_extraction_queued = True
            doc.with_delay(description='Extract timeline events for %s' % doc.name).action_extract_timeline_job()

    def action_extract_timeline_job(self):
        try:
            self.action_extract_timeline()
        finally:
            self.timeline_extraction_queued = False