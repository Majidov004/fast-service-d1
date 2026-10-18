from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LessonRecord(models.Model):
    _name = 'lesson.record'
    _description = 'Lesson Record'
    _order = 'lesson_date desc, lesson_number desc, sub_number desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _DAY_ORDER = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6,
    }

    name = fields.Char(
        string='Lesson Name',
        required=True,
        readonly=True,
        copy=False,
        default='New'
    )

    lesson_number = fields.Integer(
        string='Lesson Number',
        readonly=True,
        default=0,
        tracking=True
    )

    sub_number = fields.Integer(
        string='Sub Number',
        readonly=True,
        default=0,
        copy=False,
        help='0 = main lesson; 1 = ".1", 2 = ".2" — extra topic-repeat lessons.'
    )

    is_extra = fields.Boolean(
        string='Extra Lesson',
        default=False,
        readonly=True,
        copy=False,
        tracking=True,
        help='Created from the "new topic tomorrow = No" question. '
             'Can be deleted while still scheduled.'
    )

    group_id = fields.Many2one(
        'training.group',
        string='Group Name',
        required=True,
        ondelete='cascade'
    )

    teacher_id = fields.Many2one(
        'hr.employee',
        string='Teacher',
        related='group_id.teacher_id',
        store=True,
        readonly=True
    )

    lesson_date = fields.Date(
        string='Lesson Date',
        required=True,
        tracking=True
    )

    start_time = fields.Float(
        string='Start Time',
        required=True,
        tracking=True
    )

    end_time = fields.Float(
        string='End Time',
        required=True,
        tracking=True
    )

    lesson_time_display = fields.Char(
        string='Lesson Time',
        compute='_compute_lesson_time_display',
        store=True
    )

    state = fields.Selection([
        ('scheduled', 'Lesson Not Held'),
        ('completed', 'Lesson Held')
    ], string='Status', default='scheduled', required=True, tracking=True)

    student_line_ids = fields.One2many(
        'lesson.student.line',
        'lesson_id',
        string='Students'
    )

    teacher_comment = fields.Text(
        string='Teacher Comment'
    )

    teacher_comment_create_date = fields.Datetime(
        string='Lesson Note Created On',
        readonly=True,
        copy=False
    )

    teacher_comment_write_date = fields.Datetime(
        string='Lesson Note Last Edited On',
        readonly=True,
        copy=False
    )

    student_count = fields.Integer(
        string='Total Students',
        compute='_compute_student_count',
        store=True
    )

    present_count = fields.Integer(
        string='Present',
        compute='_compute_attendance_count',
        store=True
    )

    absent_count = fields.Integer(
        string='Absent',
        compute='_compute_attendance_count',
        store=True
    )

    # ── SOURCE ───────────────────────────────────────────────────────────────
    source = fields.Selection([
        ('group', 'Training Group'),
        ('manual', 'Manual'),
    ], string='Source', default='manual', readonly=True, copy=False)

    # ── COMPUTES ─────────────────────────────────────────────────────────────

    @api.depends('start_time', 'end_time')
    def _compute_lesson_time_display(self):
        for record in self:
            if record.start_time and record.end_time:
                sh = int(record.start_time)
                sm = int((record.start_time - sh) * 60)
                eh = int(record.end_time)
                em = int((record.end_time - eh) * 60)
                record.lesson_time_display = f"{sh:02d}:{sm:02d} - {eh:02d}:{em:02d}"
            else:
                record.lesson_time_display = ''

    @api.depends('student_line_ids')
    def _compute_student_count(self):
        for record in self:
            record.student_count = len(record.student_line_ids)

    @api.depends('student_line_ids.attendance')
    def _compute_attendance_count(self):
        for record in self:
            record.present_count = len(
                record.student_line_ids.filtered(lambda l: l.attendance == 'present')
            )
            record.absent_count = len(
                record.student_line_ids.filtered(lambda l: l.attendance == 'absent')
            )

    # ── CREATE ─────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                group = self.env['training.group'].browse(vals.get('group_id'))
                lesson_num = vals.get('lesson_number', 1)
                sub = vals.get('sub_number', 0)
                num_str = f"{lesson_num}.{sub}" if sub else f"{lesson_num}"
                vals['name'] = f"{group.name} - Lesson {num_str}"
            if vals.get('teacher_comment'):
                vals.setdefault('teacher_comment_create_date', now)
                vals.setdefault('teacher_comment_write_date', now)
        return super().create(vals_list)

    def write(self, vals):
        if 'teacher_comment' not in vals:
            return super().write(vals)
        now = fields.Datetime.now()
        new_comment = vals.get('teacher_comment') or ''
        for record in self:
            rec_vals = dict(vals)
            if new_comment != (record.teacher_comment or ''):
                rec_vals['teacher_comment_write_date'] = now
                if new_comment and not record.teacher_comment_create_date:
                    rec_vals['teacher_comment_create_date'] = now
            super(LessonRecord, record).write(rec_vals)
        return True

    # ── BUTTON ACTIONS ────────────────────────────────────────────────────────

    def action_complete_lesson(self):
        for record in self:
            record.state = 'completed'
        return True

    # ── EXTRA (TOPIC-REPEAT) LESSONS ────────────────────────────────────────────

    def _future_lessons(self):
        """Lessons in the same group strictly after this one (chronological)."""
        self.ensure_one()
        return self.env['lesson.record'].search([
            ('group_id', '=', self.group_id.id),
            '|',
            ('lesson_date', '>', self.lesson_date),
            '&', ('lesson_date', '=', self.lesson_date),
            ('start_time', '>', self.start_time),
        ], order='lesson_date asc, start_time asc')

    def _create_next_topic_lesson(self):
        """Insert an extra topic-repeat lesson right after this one.

        The new lesson (e.g. "5.1") takes the next lesson's slot and every
        following lesson is pushed forward by one slot, so the group gains one
        lesson. Called when the teacher answers "no new topic tomorrow".
        """
        self.ensure_one()
        group = self.group_id
        schedules = group.schedule_line_ids.sorted(
            key=lambda s: (self._DAY_ORDER.get(s.day_of_week, 7), s.start_time)
        )
        if not schedules:
            raise ValidationError('Cannot add an extra lesson without a schedule!')

        # Next sub-number for this base lesson number (5 → 5.1, 5.1 → 5.2)
        existing_subs = self.env['lesson.record'].search([
            ('group_id', '=', group.id),
            ('lesson_number', '=', self.lesson_number),
            ('sub_number', '>', 0),
        ])
        new_sub = (max(existing_subs.mapped('sub_number')) if existing_subs else 0) + 1

        future = self._future_lessons()
        # Current (date, start, end) slots of all following lessons …
        slots = [(l.lesson_date, l.start_time, l.end_time) for l in future]
        # … plus one fresh slot beyond the very last lesson.
        anchor = future[-1] if future else self
        slots.append(group._next_slot_after(anchor, schedules, self._DAY_ORDER))

        # New extra lesson takes the first freed slot
        nd, ns, ne = slots[0]
        new_lesson = self.create({
            'group_id': group.id,
            'lesson_number': self.lesson_number,
            'sub_number': new_sub,
            'is_extra': True,
            'lesson_date': nd,
            'start_time': ns,
            'end_time': ne,
            'source': self.source,
        })
        for st_line in group.student_line_ids:
            self.env['lesson.student.line'].create({
                'lesson_id': new_lesson.id,
                'student_id': st_line.student_id.id,
            })

        # Push every following lesson forward by one slot
        for i, lesson in enumerate(future):
            nd, ns, ne = slots[i + 1]
            lesson.write({'lesson_date': nd, 'start_time': ns, 'end_time': ne})

        group.lesson_count = group.lesson_count + 1
        return new_lesson

    def action_delete_extra_lesson(self):
        """Delete a still-scheduled extra lesson and pull subsequent lessons back.

        Inverse of `_create_next_topic_lesson`: each following lesson moves back
        into the freed slot, the last slot disappears and the group loses one
        lesson. Only allowed for extra lessons that are not yet held.
        """
        self.ensure_one()
        if not self.is_extra:
            raise ValidationError('Only extra lessons can be deleted this way!')
        if self.state != 'scheduled':
            raise ValidationError('A completed lesson cannot be deleted!')

        group = self.group_id
        future = self._future_lessons()
        # Slots to restore: this lesson's slot first, then each following lesson's
        slots = [(self.lesson_date, self.start_time, self.end_time)]
        slots += [(l.lesson_date, l.start_time, l.end_time) for l in future]

        self.unlink()  # cascade removes its student lines

        for i, lesson in enumerate(future):
            nd, ns, ne = slots[i]
            lesson.write({'lesson_date': nd, 'start_time': ns, 'end_time': ne})

        if group.lesson_count > 1:
            group.lesson_count = group.lesson_count - 1

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lesson.record',
            'view_mode': 'list,form',
            'target': 'main',
        }

    @api.constrains('start_time', 'end_time')
    def _check_time_validity(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError('End time must be after start time!')

    def _needaction_domain_get(self):
        return [('state', '=', 'scheduled')]