from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TrainingGroup(models.Model):
    _name = 'training.group'
    _description = 'Training Group'
    _order = 'name desc'

    name = fields.Char(
        string='Group Name',
        required=True,
        copy=False,
    )
    
    lesson_count = fields.Integer(
        string='Lesson Count',
        required=True,
        default=20
    )
    
    teacher_id = fields.Many2one(
        'hr.employee',
        string='Teacher',
        required=True
    )
    
    training_start_date = fields.Date(
        string='Training Start Date',
        required=False,
        default=fields.Date.context_today
    )
    
    start_day_of_week = fields.Char(
        string='Day of Week',
        compute='_compute_start_day_of_week',
        store=True,
        readonly=True
    )
    
    state = fields.Selection([
        ('pending', 'Waiting'),
        ('in_progress', 'Started'),
        ('done', 'Completed')
    ], string='Status', default='pending', required=True, tracking=True)
    
    schedule_line_ids = fields.One2many(
        'training.schedule.line',
        'group_id',
        string='Schedule'
    )
    
    student_line_ids = fields.One2many(
        'training.student.line',
        'group_id',
        string='Students'
    )
    
    student_count = fields.Integer(
        string='Total Students',
        compute='_compute_student_count',
        store=True
    )

    # Mount point for the OWL Meeting widget (no real data; widget loads via RPC)
    meeting_view = fields.Char(
        string='Meeting',
        compute='_compute_meeting_view'
    )

    def _compute_meeting_view(self):
        for record in self:
            record.meeting_view = False

    @api.depends('student_line_ids')
    def _compute_student_count(self):
        for record in self:
            record.student_count = len(record.student_line_ids)
    
    @api.depends('training_start_date')
    def _compute_start_day_of_week(self):
        days = {
            0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
            4: 'Friday', 5: 'Saturday', 6: 'Sunday'
        }
        for record in self:
            if record.training_start_date:
                day_num = record.training_start_date.weekday()
                record.start_day_of_week = days.get(day_num, '')
            else:
                record.start_day_of_week = ''
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'schedule_line_ids' in fields_list:
            days = [
                'monday', 'tuesday', 'wednesday',
                'thursday', 'friday', 'saturday', 'sunday',
            ]
            res['schedule_line_ids'] = [
                (0, 0, {'day_of_week': day, 'start_time': 9.0, 'end_time': 10.0})
                for day in days
            ]
        return res

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)
    
    @api.onchange('lesson_count')
    def _onchange_lesson_count(self):
        if self.student_line_ids:
            for line in self.student_line_ids:
                if not line.lesson_count or line.lesson_count == self._origin.lesson_count:
                    line.lesson_count = self.lesson_count
    
    @api.constrains('lesson_count')
    def _check_lesson_count(self):
        for record in self:
            if record.lesson_count < 1:
                raise ValidationError('Lesson count must be at least 1!')
    
    def action_start(self):
        for record in self:
            if not record.schedule_line_ids:
                raise ValidationError('Please add schedule before starting the training!')
            if not record.student_line_ids:
                raise ValidationError('Please add students before starting the training!')
            
            day_order = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            schedules = record.schedule_line_ids.sorted(
                key=lambda s: (day_order.get(s.day_of_week, 7), s.start_time)
            )
            
            if not schedules:
                raise ValidationError('No valid schedule found!')
            
            current_date = record.training_start_date
            lesson_count = record.lesson_count
            
            for lesson_num in range(1, lesson_count + 1):
                schedule_index = (lesson_num - 1) % len(schedules)
                schedule = schedules[schedule_index]
                
                if lesson_num == 1:
                    start_weekday = current_date.weekday()
                    target_weekday = day_order.get(schedule.day_of_week, 0)
                    if target_weekday >= start_weekday:
                        days_to_add = target_weekday - start_weekday
                    else:
                        days_to_add = 7 - start_weekday + target_weekday
                    lesson_date = current_date + timedelta(days=days_to_add)
                else:
                    prev_schedule = schedules[(lesson_num - 2) % len(schedules)]
                    prev_weekday = day_order.get(prev_schedule.day_of_week, 0)
                    current_weekday = day_order.get(schedule.day_of_week, 0)
                    if current_weekday > prev_weekday:
                        days_to_add = current_weekday - prev_weekday
                    else:
                        days_to_add = 7 - prev_weekday + current_weekday
                    lesson_date = current_date + timedelta(days=days_to_add)
                
                current_date = lesson_date
                
                lesson = self.env['lesson.record'].create({
                    'lesson_number': lesson_num,
                    'group_id': record.id,
                    'lesson_date': lesson_date,
                    'start_time': schedule.start_time,
                    'end_time': schedule.end_time,
                })
                
                for student_line in record.student_line_ids:
                    self.env['lesson.student.line'].create({
                        'lesson_id': lesson.id,
                        'student_id': student_line.student_id.id,
                    })
            
            record.state = 'in_progress'
        
        return True
    
    def action_complete(self):
        """Mark the whole group as Completed (state only; lessons untouched)."""
        for record in self:
            if record.state != 'in_progress':
                raise ValidationError('Only a started training can be completed!')
            record.state = 'done'
        return True

    def _get_next_lesson_date(self, current_date, last_schedule_index, next_schedule_index, schedules, day_order):
        """Helper: calculate next lesson date based on schedule rotation"""
        prev_schedule = schedules[last_schedule_index]
        next_schedule = schedules[next_schedule_index]
        prev_weekday = day_order.get(prev_schedule.day_of_week, 0)
        curr_weekday = day_order.get(next_schedule.day_of_week, 0)

        if curr_weekday > prev_weekday:
            days_to_add = curr_weekday - prev_weekday
        else:
            days_to_add = 7 - prev_weekday + curr_weekday

        return current_date + timedelta(days=days_to_add)

    def _next_slot_after(self, lesson, schedules, day_order):
        """Return (date, start_time, end_time) of the schedule slot following `lesson`.

        Used when inserting an extra (topic-repeat) lesson: figures out which
        schedule slot the given lesson occupies, then rotates to the next slot.
        """
        self.ensure_one()
        weekday_name = {v: k for k, v in day_order.items()}.get(lesson.lesson_date.weekday())
        idx = 0
        for i, schedule in enumerate(schedules):
            if (schedule.day_of_week == weekday_name
                    and abs(schedule.start_time - lesson.start_time) < 0.001):
                idx = i
                break
        next_idx = (idx + 1) % len(schedules)
        next_date = self._get_next_lesson_date(
            lesson.lesson_date, idx, next_idx, schedules, day_order
        )
        sched = schedules[next_idx]
        return (next_date, sched.start_time, sched.end_time)

    def action_modify(self):
        """
        Modify logic (reference = today):
        1. For each student, count how many lessons they are assigned to in this group.
        2. If assigned < student.lesson_count:
           a. First, fill the student into existing future (>= today) lessons they are missing from.
           b. If still not enough, create NEW lesson records continuing from the last existing lesson,
              adding ONLY the students who need those extra lessons.
        """
        for record in self:
            if record.state != 'in_progress':
                raise ValidationError('Training must be in progress to modify!')

            today = fields.Date.context_today(self)

            day_order = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }

            schedules = record.schedule_line_ids.sorted(
                key=lambda s: (day_order.get(s.day_of_week, 7), s.start_time)
            )

            if not schedules:
                raise ValidationError('No valid schedule found!')

            schedule_count = len(schedules)

            for student_line in record.student_line_ids:
                student_id = student_line.student_id.id
                required = student_line.lesson_count

                # All lessons for this group (ordered)
                all_lessons = self.env['lesson.record'].search(
                    [('group_id', '=', record.id)],
                    order='lesson_date asc, start_time asc'
                )

                # How many lessons is this student currently in?
                assigned = self.env['lesson.student.line'].search([
                    ('lesson_id', 'in', all_lessons.ids),
                    ('student_id', '=', student_id),
                ])
                current_count = len(assigned)

                if current_count >= required:
                    continue  # This student already has enough lessons

                deficit = required - current_count

                # ── STEP 1: Add student to existing FUTURE lessons they are missing from ──
                assigned_lesson_ids = assigned.mapped('lesson_id').ids
                future_unassigned = all_lessons.filtered(
                    lambda l: l.lesson_date >= today and l.id not in assigned_lesson_ids
                )

                for lesson in future_unassigned:
                    if deficit <= 0:
                        break
                    self.env['lesson.student.line'].create({
                        'lesson_id': lesson.id,
                        'student_id': student_id,
                    })
                    deficit -= 1

                if deficit <= 0:
                    continue

                # ── STEP 2: Create NEW lesson records beyond the last existing lesson ──
                # Re-fetch to get the latest state (another student loop may have added records)
                all_lessons = self.env['lesson.record'].search(
                    [('group_id', '=', record.id)],
                    order='lesson_date asc, start_time asc'
                )

                total_existing = len(all_lessons)

                if total_existing > 0:
                    current_date = all_lessons[-1].lesson_date
                    # Determine which schedule slot was used for the last lesson
                    last_schedule_index = (total_existing - 1) % schedule_count
                else:
                    # No lessons at all — start from today
                    current_date = today
                    last_schedule_index = schedule_count - 1  # next call will yield index 0

                while deficit > 0:
                    next_schedule_index = (last_schedule_index + 1) % schedule_count

                    lesson_date = self._get_next_lesson_date(
                        current_date, last_schedule_index, next_schedule_index,
                        schedules, day_order
                    )

                    # Re-fetch fresh to avoid stale data
                    all_lessons = self.env['lesson.record'].search(
                        [('group_id', '=', record.id)],
                        order='lesson_date asc, start_time asc'
                    )

                    # Check if this exact slot already exists (created for another student earlier)
                    target_schedule = schedules[next_schedule_index]
                    existing_slot = all_lessons.filtered(
                        lambda l, ld=lesson_date, st=target_schedule.start_time:
                            l.lesson_date == ld and l.start_time == st
                    )

                    if existing_slot:
                        lesson = existing_slot[0]
                        already_in = self.env['lesson.student.line'].search([
                            ('lesson_id', '=', lesson.id),
                            ('student_id', '=', student_id),
                        ], limit=1)
                        if not already_in:
                            self.env['lesson.student.line'].create({
                                'lesson_id': lesson.id,
                                'student_id': student_id,
                            })
                    else:
                        # Brand new lesson — ONLY this student is added
                        lesson = self.env['lesson.record'].create({
                            'lesson_number': len(all_lessons) + 1,
                            'group_id': record.id,
                            'lesson_date': lesson_date,
                            'start_time': target_schedule.start_time,
                            'end_time': target_schedule.end_time,
                        })
                        self.env['lesson.student.line'].create({
                            'lesson_id': lesson.id,
                            'student_id': student_id,
                        })

                    current_date = lesson_date
                    last_schedule_index = next_schedule_index
                    deficit -= 1

        return True
    def unlink(self):
        lesson_records = self.env['lesson.record'].search(
            [('group_id', 'in', self.ids)]
        )
        lesson_records.unlink()
        return super().unlink()

    # ── MEETING TAB (OWL widget RPC) ─────────────────────────────────────────

    def _fmt_dt(self, dt):
        """Format a stored UTC datetime into the user's local 'dd-mm-YYYY HH:MM'."""
        if not dt:
            return ''
        local_dt = fields.Datetime.context_timestamp(self, dt)
        return local_dt.strftime('%d-%m-%Y %H:%M')

    def get_meeting_lessons(self):
        """Mini lesson cards for the Meeting tab (this group's lessons)."""
        self.ensure_one()
        lessons = self.env['lesson.record'].search(
            [('group_id', '=', self.id)],
            order='lesson_number asc, sub_number asc, lesson_date asc, start_time asc'
        )
        return [{
            'id': lesson.id,
            'name': lesson.name,
            'lesson_number': lesson.lesson_number,
            'sub_number': lesson.sub_number,
            'number_display': (f"{lesson.lesson_number}.{lesson.sub_number}"
                               if lesson.sub_number else str(lesson.lesson_number)),
            'is_extra': lesson.is_extra,
            'date': lesson.lesson_date.strftime('%d-%m-%Y') if lesson.lesson_date else '',
            'time': lesson.lesson_time_display or '',
            'state': lesson.state,
            'student_count': lesson.student_count,
            'present_count': lesson.present_count,
            'absent_count': lesson.absent_count,
        } for lesson in lessons]

    def delete_extra_lesson(self, lesson_id):
        """Delete a scheduled extra lesson from the Meeting tab; reload the cards."""
        self.ensure_one()
        lesson = self.env['lesson.record'].browse(lesson_id)
        if lesson.exists() and lesson.group_id.id == self.id:
            lesson.action_delete_extra_lesson()
        return self.get_meeting_lessons()

    def get_meeting_lesson_detail(self, lesson_id):
        """Full lesson detail (students + notes) for the popup."""
        self.ensure_one()
        lesson = self.env['lesson.record'].browse(lesson_id)
        if not lesson.exists() or lesson.group_id.id != self.id:
            return {}
        students = [{
            'line_id': line.id,
            'student_id': line.student_id.id,
            'student_name': line.student_id.name or '',
            'attendance': line.attendance,
            'comment': line.comment or '',
            'comment_create_date': self._fmt_dt(line.comment_create_date),
            'comment_write_date': self._fmt_dt(line.comment_write_date),
        } for line in lesson.student_line_ids]
        return {
            'id': lesson.id,
            'name': lesson.name,
            'date': lesson.lesson_date.strftime('%d-%m-%Y') if lesson.lesson_date else '',
            'time': lesson.lesson_time_display or '',
            'state': lesson.state,
            'teacher_comment': lesson.teacher_comment or '',
            'teacher_comment_create_date': self._fmt_dt(lesson.teacher_comment_create_date),
            'teacher_comment_write_date': self._fmt_dt(lesson.teacher_comment_write_date),
            'students': students,
        }

    def save_meeting_lesson(self, lesson_id, payload):
        """Persist notes + attendance from the popup; optionally complete the lesson."""
        self.ensure_one()
        lesson = self.env['lesson.record'].browse(lesson_id)
        if not lesson.exists() or lesson.group_id.id != self.id:
            return self.get_meeting_lessons()

        payload = payload or {}

        if 'teacher_comment' in payload:
            lesson.write({'teacher_comment': payload.get('teacher_comment') or False})

        for student in payload.get('students', []):
            line = self.env['lesson.student.line'].browse(student.get('line_id'))
            if not line.exists() or line.lesson_id.id != lesson.id:
                continue
            line.write({
                'attendance': student.get('attendance') or 'present',
                'comment': student.get('comment') or False,
            })

        if payload.get('complete'):
            lesson.action_complete_lesson()
            # "no new topic tomorrow" → spawn an extra topic-repeat lesson (e.g. 5.1)
            if not payload.get('next_topic', True):
                lesson._create_next_topic_lesson()

        return self.get_meeting_lessons()