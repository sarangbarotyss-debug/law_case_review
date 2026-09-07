# -*- coding: utf-8 -*-
from odoo import api, models, fields


class ClientRequestUploadWizard(models.TransientModel):
    _name = "client.request.upload.wizard"
    _description = "client_request_upload_wizard"

    file = fields.Binary(string="Document", required=True)
    file_name = fields.Char(string="File Name")
    stage = fields.Selection([
        ('upload', 'Upload'),
        ('progress', 'Progress'),
    ], default='upload')
    error_message = fields.Char(readonly=True)
    client_request_id = fields.Many2one('law.client.request', readonly=True)

    def action_extract_and_create(self):
        self.ensure_one()
        self.error_message = False

        record = self.env['law.client.request'].create({
            'file': self.file,
            'file_name': self.file_name,
            'processing_state': 'pending',
        })
        record.with_delay(
            description="Extract client request document: %s" % self.file_name
        ).button_process_extraction_job()

        self.write({
            'stage': 'progress',
            'client_request_id': record.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'client.request.upload.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_handle_failure(self):
        self.ensure_one()
        if self.client_request_id:
            self.client_request_id.unlink()
        self.write({
            'stage': 'upload',
            'error_message': "Extraction failed, please try again.",
            'client_request_id': False,
        })