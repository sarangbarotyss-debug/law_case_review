# -*- coding: utf-8 -*-

from odoo import api, models, fields
import requests
import base64
import json
from ..services import ai_provider_service

class LawClientRequest(models.Model):
    _name = 'law.client.request'
    _description = 'Client Request'

    name = fields.Char(string='Name')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone Number')
    mobile = fields.Char(string='Mobile Number')

    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP')
    country_id = fields.Many2one('res.country', string='Country')
    company_id=fields.Many2one('res.company', string='Company', default = lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Client', readonly=True, copy=False)
    lawyer_id = fields.Many2one('res.users', string='Assigned Lawyer', default=lambda self: self.env.user)
    case_id = fields.Many2one('law.case', string='Case', readonly=True, copy=False)
    matter_type = fields.Char(string='Type of Matter')
    description = fields.Text(string='Description of Matter')
    state = fields.Selection([
        ('request', 'Request For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='request')
    file = fields.Binary(string="Document", attachment=True)
    file_name=fields.Char(string="File Name")
    ocr_text = fields.Text(string='OCR Text')
    processing_state = fields.Selection([
        ('pending', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], default='pending', readonly=True)
    is_case_manager = fields.Boolean(compute='_compute_is_case_manager')

    def _compute_is_case_manager(self):
        is_manager = self.env.user.has_group('law_case_review.group_law_case_manager')
        for rec in self:
            rec.is_case_manager = is_manager

    def action_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'client.request.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_client_request_ids': self.ids},
        }

    def action_reject(self):
        self.state = "rejected"

    def button_process_extraction_job(self):
        self.ensure_one()
        try:
            file_bytes = base64.b64decode(self.file)
            docling_url = self.env['ir.config_parameter'].sudo().get_param(
                'law_case_review.docling_service_url', default='http://localhost:8500'
            )
            response = requests.post(
                f"{docling_url}/extract-text",
                files={'file': (self.file_name, file_bytes)},
                timeout=1800,
            )
            if response.status_code != 200:
                raise Exception('OCR Extraction Failed')
            ocr_text = response.json().get('text', '')

            prompt = f"""
            Read the following document text and extract these fields as raw JSON only,
            no markdown, no explanation:
            {{
              "name": "...",
              "email": "...",
              "phone": "...",
              "mobile": "...",
              "street": "...",
              "street2": "...",
              "city": "...",
              "zip": "...",
              "matter_type": "...",
              "description": "..."
            }}
            If a field is not found in the text, leave it as an empty string.
            Document text:
            {ai_provider_service.wrap_untrusted_text(ocr_text)}
            """
            ai_response = ai_provider_service.call_llm(self.env, prompt)
            data = json.loads(ai_response)

            self.write({
                'name': data.get('name', ''),
                'email': data.get('email', ''),
                'phone': data.get('phone', ''),
                'mobile': data.get('mobile', ''),
                'street': data.get('street', ''),
                'street2': data.get('street2', ''),
                'city': data.get('city', ''),
                'zip': data.get('zip', ''),
                'matter_type': data.get('matter_type', ''),
                'description': data.get('description', ''),
                'ocr_text': ocr_text,
                'processing_state': 'done',
            })
        except Exception as e:
            file_name = self.file_name
            self.env['ir.logging'].sudo().create({
                'name': 'law_case_review',
                'type': 'server',
                'level': 'ERROR',
                'message': 'Client request extraction failed for file %s: %s' % (file_name, str(e)),
                'path': 'law_case_review.law_client_request',
                'func': 'button_process_extraction_job',
                'line': '0',
            })
            self.env.cr.commit()
            self.unlink()