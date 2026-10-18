from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TrainingScheduleLine(models.Model):
    _name = 'training.schedule.line'
    _description = 'Training Schedule Line'
    _order = 'day_of_week, start_time'

    group_id = fields.Many2one(
        'training.group',
        string='Training Group',
        required=True,
        ondelete='cascade'
    )
    
    day_of_week = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string='Day of Week', required=True)
    
    start_time = fields.Float(
        string='Start Time',
        required=True,
        help='Time in 24-hour format (e.g., 9.0 = 09:00, 14.5 = 14:30)'
    )
    
    end_time = fields.Float(
        string='End Time',
        required=True,
        help='Time in 24-hour format (e.g., 11.0 = 11:00, 16.5 = 16:30)'
    )
    
    duration = fields.Float(
        string='Duration (hours)',
        compute='_compute_duration',
        store=True
    )
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            record.duration = record.end_time - record.start_time
    
    @api.constrains('start_time', 'end_time')
    def _check_time_validity(self):
        for record in self:
            if record.start_time < 0 or record.start_time >= 24:
                raise ValidationError('Start time must be between 0 and 24!')
            if record.end_time < 0 or record.end_time >= 24:
                raise ValidationError('End time must be between 0 and 24!')
            if record.start_time >= record.end_time:
                raise ValidationError('End time must be after start time!')
    
    def name_get(self):
        result = []
        for record in self:
            start_hour = int(record.start_time)
            start_minute = int((record.start_time - start_hour) * 60)
            end_hour = int(record.end_time)
            end_minute = int((record.end_time - end_hour) * 60)
            
            name = f"{record.day_of_week.capitalize()}: {start_hour:02d}:{start_minute:02d} - {end_hour:02d}:{end_minute:02d}"
            result.append((record.id, name))
        return result
