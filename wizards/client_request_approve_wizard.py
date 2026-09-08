# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from ..models.case_document_ingestion_service import chunk_and_embed_document


class ClientRequestApproveWizard(models.TransientModel):
    _name = 'client.request.approve.wizard'
    _description = 'Approve Client Request — Select Playbook Sources'

    client_request_ids = fields.Many2many(
        'law.client.request',
        string='Client Requests',
    )
    playbook_source_ids = fields.Many2many(
        'law.playbook.source',
        string='Relevant Playbook Sources',
        required=True,
        help="Select which reference documents (e.g. Constitution, specific statutes) "
             "the resulting case(s) should be compared against.",
    )

    def action_confirm_approve(self):
        self.ensure_one()
        for rec in self.client_request_ids:
            partner = False
            if rec.email:
                partner = self.env['res.partner'].search([('email', '=', rec.email)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': rec.name,
                    'email': rec.email,
                    'phone': rec.phone or rec.mobile,
                    'street': rec.street,
                    'street2': rec.street2,
                    'city': rec.city,
                    'state_id': rec.state_id.id,
                    'zip': rec.zip,
                    'country_id': rec.country_id.id,
                })
            rec.partner_id = partner
            case = self.env['law.case'].create({
                'client_id': partner.id,
                'description': rec.description,
                'matter_type': rec.matter_type,
                'playbook_source_ids': [(6, 0, self.playbook_source_ids.ids)],
                'lawyer_id': rec.lawyer_id.id,
            })

            if rec.file:
                new_document = self.env['law.case.document'].create({
                    'name':rec.file_name or rec.name,
                    'case_id':case.id,
                    'file':rec.file,
                    'file_name':rec.file_name,
                    'ocr_text':rec.ocr_text,
                    'state':'confirmed',
                })

            chunk_and_embed_document(self.env, new_document)
            rec.case_id = case
            rec.state = "approved"