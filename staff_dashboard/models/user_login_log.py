# -*- coding: utf-8 -*-
import pytz
from datetime import datetime
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import AccessError
from odoo.tools import html2plaintext


class UserLoginLog(models.Model):
    _name = 'user.login.log'
    _description = 'User Login Log'
    _order = 'login_time desc'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', string='User')
    login_time = fields.Datetime(required=True, default=fields.Datetime.now, string='Login Time')
    last_activity = fields.Datetime(default=fields.Datetime.now, string='Last Activity')
    session_end = fields.Datetime(string='Session End')  # logout zamanı doldurulur — bağlı sessiya
    session_token = fields.Char(string='Session', index=True)  # brauzer session id (sid) — sessiyanı unikal ayırır
    current_module = fields.Char(string='Current Module')
    duration_display = fields.Char(compute='_compute_duration', string='Duration')

    @api.depends('login_time', 'last_activity')
    def _compute_duration(self):
        for rec in self:
            if rec.login_time and rec.last_activity:
                delta = rec.last_activity - rec.login_time
                total = int(delta.total_seconds() / 60)
                h, m = divmod(total, 60)
                rec.duration_display = f"{h}h {m}m" if h else f"{m}m"
            else:
                rec.duration_display = '—'

    @api.model
    def _check_dashboard_access(self):
        """Dashboard data metodları üçün giriş yoxlaması. Yalnız Dashboard Access
        qrupu və ya admin oxuya bilər (menyu gizli olsa da endpoint qorunur)."""
        if self.env.user.has_group('base.group_system') or \
                self.env.user.has_group('staff_dashboard.group_dashboard_user'):
            return
        raise AccessError(_("Bu məlumatı görmək üçün icazəniz yoxdur."))

    @api.model
    def _current_sid(self):
        """Cari HTTP sessiyasının id-si (sid). Hər login-də Odoo yeni sid verir,
        ona görə bu, login sessiyalarını dəqiq ayırmağa imkan verir.
        HTTP konteksti olmayan hallarda (cron/test) False qaytarır."""
        try:
            from odoo.http import request
            if request and getattr(request, 'session', None):
                return request.session.sid
        except Exception:
            pass
        return False

    @api.model
    def update_heartbeat(self, module_path='', client_token=False):
        """JS heartbeat — cari səhifə yüklənişinin (client_token) logunu yenilə,
        yoxdursa yeni sessiya yarat.

        Sessiya `session_token` ilə eyniləşdirilir. Açar `client_token`-dur:
        frontend hər tam səhifə yüklənişində (= link ilə hər giriş) yeni token verir.
        - Eyni səhifənin bütün heartbeat-ləri EYNI sətri yeniləyir → dublikat olmur.
        - Link ilə yeni giriş / login redirect / tab yenidən açılması → yeni token →
          AYRI sətir yaranır → yeni sessiya görünür (real logout tələb olunmur).
        client_token gəlməyəndə sid, o da yoxdursa son açıq sessiya (15 dəq) fallback-dır.
        """
        uid = self.env.uid
        if not uid:
            return
        now = fields.Datetime.now()
        key = client_token or self._current_sid()

        if key:
            log = self.sudo().search(
                [('user_id', '=', uid),
                 ('session_token', '=', key),
                 ('session_end', '=', False)],
                order='login_time desc', limit=1,
            )
        else:
            # Fallback: açar yoxdursa son açıq sessiyanı təkrar istifadə et (sətir spam-ı olmasın)
            log = self.sudo().search(
                [('user_id', '=', uid), ('session_end', '=', False)],
                order='login_time desc', limit=1,
            )
            if log and log.last_activity and (now - log.last_activity).total_seconds() >= 15 * 60:
                log = False

        if log:
            vals = {'last_activity': now}
            if module_path:
                vals['current_module'] = module_path
            log.write(vals)
        else:
            self.sudo().create({
                'user_id': uid,
                'login_time': now,
                'last_activity': now,
                'session_token': key or False,
                'current_module': module_path or False,
            })

    @api.model
    def clear_activity_logs(self):
        """Dashboard-dakı 'Clear' düyməsi — bütün login loglarını silir.
        Yalnız administrator (base.group_system) icra edə bilər."""
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Yalnız administrator aktivlik qeydlərini silə bilər."))
        self.sudo().search([]).unlink()
        return True

    @api.model
    def close_session(self, uid=None):
        """Logout zamanı çağırılır — istifadəçinin son açıq sessiyasını bağlayır
        (session_end təyin edir) ki, müddət dəqiq saxlanılsın."""
        uid = uid or self.env.uid
        if not uid:
            return
        now = fields.Datetime.now()
        log = self.sudo().search(
            [('user_id', '=', uid), ('session_end', '=', False)],
            order='login_time desc', limit=1,
        )
        if log:
            log.write({'session_end': now, 'last_activity': now})

    def _calc_duration_mins(self, log, now, is_latest_for_user=False):
        if not log.login_time:
            return 0
        # Yalnız istifadəçinin ən son sessiyası aktiv ola bilər
        if is_latest_for_user and log.last_activity and (now - log.last_activity).total_seconds() < 15 * 60:
            delta = now - log.login_time
        else:
            delta = (log.last_activity or log.login_time) - log.login_time
        return max(0, int(delta.total_seconds() / 60))

    @staticmethod
    def _fmt(total_mins):
        h, m = divmod(total_mins, 60)
        return f"{h}h {m}m" if h else f"{m}m"

    # ── APPLICANT ANALYTICS ──────────────────────────────────────────────────
    # Funnel order (journey) + labels. Losses (No Answer / Not Want /
    # Trial - No Contact) sit near the end; Paid is the successful outcome.
    _ANALYTICS_STAGES = [
        ('interested',         'Interested'),
        ('needs_to_be_called', 'Needs to be Called'),
        ('called',             'Messaged'),
        ('wait',               'Wait'),
        ('planned_trial',      'Planned Trial'),
        ('trial_no_contact',   'Trial - No Contact'),
        ('planned_remember',   'Planned Remember'),
        ('remember',           'Remember'),
        ('no_answer',          'No Answer'),
        ('not_want',           'Not Want'),
        ('paid',               'Paid'),
    ]

    # Hover tooltip text per funnel stage.
    _STAGE_HELP = {
        'interested':         "Showed interest but not contacted yet.",
        'needs_to_be_called': "Marked to be called; a trial teacher is assigned.",
        'called':             "The applicant has been messaged / contacted.",
        'wait':               "Waiting on the applicant's response or decision.",
        'planned_trial':      "A trial lesson has been scheduled.",
        'trial_no_contact':   "Couldn't reach the applicant around the trial (legacy).",
        'planned_remember':   "A follow-up reminder is scheduled for a later date.",
        'remember':           "Kept for later follow-up.",
        'no_answer':          "The applicant did not answer.",
        'not_want':           "The applicant declined / is not interested.",
        'paid':               "Converted to a paying student (success).",
    }

    @staticmethod
    def _analytics_pct(cur, prev):
        """Percentage change vs the previous month. No baseline -> not shown."""
        if not prev:
            return {'has': False, 'value': 0, 'dir': 'flat'}
        diff = (cur - prev) / float(prev) * 100.0
        direction = 'up' if diff > 0 else ('down' if diff < 0 else 'flat')
        return {'has': True, 'value': round(abs(diff)), 'dir': direction}

    @api.model
    def get_applicant_analytics(self):
        """Applicant funnel data for the current month with the change vs the
        previous month. Counted by create_date + current applicant_state.
        Guarded: contact_customization provides applicant_state/is_* fields."""
        self._check_dashboard_access()
        Partner = self.env['res.partner']
        if 'applicant_state' not in Partner._fields:
            return {'available': False}

        tz = pytz.timezone(self.env.user.tz or 'UTC')
        now_local = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        cur_start = now_local.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        prev_start = cur_start - relativedelta(months=1)
        next_start = cur_start + relativedelta(months=1)

        def to_utc(dt_local):
            return dt_local.astimezone(pytz.UTC).replace(tzinfo=None)

        def counts_for(start_dt, end_dt):
            groups = Partner.read_group(
                [
                    ('applicant_state', '!=', False),
                    ('create_date', '>=', start_dt),
                    ('create_date', '<', end_dt),
                ],
                ['applicant_state'],
                ['applicant_state'],
            )
            out = {}
            for g in groups:
                out[g['applicant_state']] = (
                    g.get('__count') or g.get('applicant_state_count') or 0
                )
            return out

        cur_counts = counts_for(to_utc(cur_start), to_utc(next_start))
        prev_counts = counts_for(to_utc(prev_start), to_utc(cur_start))

        stages = []
        for key, label in self._ANALYTICS_STAGES:
            cur = cur_counts.get(key, 0)
            prev = prev_counts.get(key, 0)
            stages.append({
                'key': key,
                'label': label,
                'count': cur,
                'prev_count': prev,
                'pct': self._analytics_pct(cur, prev),
                'help': self._STAGE_HELP.get(key, ''),
            })

        totals = {
            'people': Partner.search_count(
                ['|', ('is_student', '=', True), ('is_applicant', '=', True)]
            ),
            'students': Partner.search_count([('is_student', '=', True)]),
            'applicants': Partner.search_count([('is_applicant', '=', True)]),
        }

        # ── helpers ──
        def rate(part, whole):
            return round(part / whole * 100) if whole else 0

        def kpi(label, cur, prev, suffix='', good_up=True, tip=''):
            if cur > prev:
                change = 'up'
            elif cur < prev:
                change = 'down'
            else:
                change = 'flat'
            if change == 'flat':
                tone = 'flat'
            else:
                tone = 'good' if ((change == 'up') == good_up) else 'bad'
            return {'label': label, 'value': cur, 'suffix': suffix,
                    'prev': prev, 'change': change, 'tone': tone, 'help': tip}

        # ── A. Conversion KPIs ──
        reg_cur, reg_prev = sum(cur_counts.values()), sum(prev_counts.values())
        paid_cur, paid_prev = cur_counts.get('paid', 0), prev_counts.get('paid', 0)

        def loss(c):
            return c.get('no_answer', 0) + c.get('not_want', 0) + c.get('trial_no_contact', 0)
        loss_cur, loss_prev = loss(cur_counts), loss(prev_counts)
        active_cur = reg_cur - paid_cur - loss_cur
        active_prev = reg_prev - paid_prev - loss_prev

        rates = [
            kpi('Conversion Rate', rate(paid_cur, reg_cur), rate(paid_prev, reg_prev), '%',
                tip="Share of this month's registered applicants who became paying "
                    "students (Paid ÷ Registered). Higher is better."),
            kpi('Loss Rate', rate(loss_cur, reg_cur), rate(loss_prev, reg_prev), '%', good_up=False,
                tip="Share lost this month (No Answer + Not Want + Trial-No Contact) "
                    "÷ Registered. Lower is better."),
            kpi('Active Pipeline', active_cur, active_prev,
                tip="Applicants still open this month (Registered − Paid − Lost) "
                    "— work still to do."),
            kpi('New Registrations', reg_cur, reg_prev,
                tip="Applicants who entered the funnel this month (intake volume)."),
        ]

        # ── B. Lead sources (this month) ──
        sources = []
        if 'reference_source' in Partner._fields:
            src_sel = dict(Partner._fields['reference_source'].selection)
            base_dom = [('create_date', '>=', to_utc(cur_start)),
                        ('create_date', '<', to_utc(next_start)),
                        ('reference_source', '!=', False)]
            reg_g = Partner.read_group(base_dom, ['reference_source'], ['reference_source'])
            paid_g = Partner.read_group(
                base_dom + [('applicant_state', '=', 'paid')],
                ['reference_source'], ['reference_source'])
            reg_map = {g['reference_source']: (g.get('__count') or 0) for g in reg_g}
            paid_map = {g['reference_source']: (g.get('__count') or 0) for g in paid_g}
            for key, cnt in reg_map.items():
                paid = paid_map.get(key, 0)
                sources.append({
                    'label': src_sel.get(key, key), 'count': cnt,
                    'paid': paid, 'conv': rate(paid, cnt),
                })
            sources.sort(key=lambda x: x['count'], reverse=True)

        # ── C. Trial lessons (by lesson_datetime within the month) ──
        trials = None
        if 'trail.lesson' in self.env:
            TL = self.env['trail.lesson'].sudo()

            def trial_states(start_dt, end_dt):
                g = TL.read_group(
                    [('lesson_datetime', '>=', start_dt), ('lesson_datetime', '<', end_dt)],
                    ['state'], ['state'])
                return {x['state']: (x.get('__count') or 0) for x in g}
            tc = trial_states(to_utc(cur_start), to_utc(next_start))
            tp = trial_states(to_utc(prev_start), to_utc(cur_start))
            dec_g = TL.read_group(
                [('state', '=', 'completed'),
                 ('lesson_datetime', '>=', to_utc(cur_start)),
                 ('lesson_datetime', '<', to_utc(next_start))],
                ['decision'], ['decision'])
            dec = {x['decision']: (x.get('__count') or 0) for x in dec_g}
            trials = {
                'total': sum(tc.values()),
                'total_prev': sum(tp.values()),
                'planned': tc.get('planned', 0),
                'completed': tc.get('completed', 0),
                'missing': tc.get('missing', 0),
                'joining': dec.get('joining', 0),
                'thinking': dec.get('thinking', 0),
                'not_joining': dec.get('not_joining', 0),
            }

        # ── E. 6-month trend (registered vs paid) ──
        trend = []
        for i in range(5, -1, -1):
            m_start = cur_start - relativedelta(months=i)
            m_end = m_start + relativedelta(months=1)
            c = counts_for(to_utc(m_start), to_utc(m_end))
            trend.append({
                'label': m_start.strftime('%b %y'),
                'registered': sum(c.values()),
                'paid': c.get('paid', 0),
            })

        # ── F. Students overview ──
        new_stu_cur = Partner.search_count([
            ('is_student', '=', True),
            ('create_date', '>=', to_utc(cur_start)), ('create_date', '<', to_utc(next_start))])
        new_stu_prev = Partner.search_count([
            ('is_student', '=', True),
            ('create_date', '>=', to_utc(prev_start)), ('create_date', '<', to_utc(cur_start))])
        lead = []
        if 'lead_state' in Partner._fields:
            lead_sel = dict(Partner._fields['lead_state'].selection)
            lg = Partner.read_group(
                [('is_student', '=', True), ('lead_state', '!=', False)],
                ['lead_state'], ['lead_state'])
            lmap = {g['lead_state']: (g.get('__count') or 0) for g in lg}
            lead = [{'label': lbl, 'count': lmap.get(k, 0)} for k, lbl in lead_sel.items()]
        active_groups = 0
        if 'training.group' in self.env:
            active_groups = self.env['training.group'].sudo().search_count(
                [('state', '=', 'in_progress')])
        students = {
            'total': totals['students'],
            'new': kpi('New Students', new_stu_cur, new_stu_prev,
                       tip="Students created this month."),
            'lead': lead,
            'active_groups': active_groups,
        }

        return {
            'available': True,
            'month_label': cur_start.strftime('%B %Y'),
            'prev_month_label': prev_start.strftime('%B %Y'),
            'totals': totals,
            'stages': stages,
            'rates': rates,
            'sources': sources,
            'trials': trials,
            'trend': trend,
            'students': students,
        }

    @api.model
    def get_dashboard_activity(self, limit=200):
        """User+gün qruplaşdırılmış login məlumatları."""
        self._check_dashboard_access()
        logs = self.search([], order='login_time desc', limit=limit)
        now = fields.Datetime.now()

        # Hər istifadəçinin ən son login_time-ı — yalnız o aktiv sayılır
        latest_per_user = {}
        for log in logs:
            uid = log.user_id.id
            if uid not in latest_per_user:
                latest_per_user[uid] = log.id

        groups = defaultdict(lambda: {'sessions': [], 'user_name': '', 'total_mins': 0})
        order = []

        for log in logs:
            if not log.login_time:
                continue
            # UTC → lokal vaxt
            login_local = fields.Datetime.context_timestamp(log, log.login_time)
            date_key = login_local.strftime('%Y-%m-%d')
            gkey = f"{log.user_id.id}_{date_key}"
            if gkey not in groups or not groups[gkey]['user_name']:
                groups[gkey]['user_name'] = log.user_id.name or ''
                groups[gkey]['user_id'] = log.user_id.id
                groups[gkey]['date_sort'] = date_key
                if gkey not in order:
                    order.append(gkey)
            is_latest = (latest_per_user.get(log.user_id.id) == log.id)
            mins = self._calc_duration_mins(log, now, is_latest_for_user=is_latest)
            groups[gkey]['total_mins'] += mins
            groups[gkey]['sessions'].append({
                'login_time': login_local.strftime('%H:%M'),
                'duration': self._fmt(mins),
                'active': is_latest,
            })

        result = []
        for gkey in order:
            g = groups[gkey]
            date_display = datetime.strptime(g['date_sort'], '%Y-%m-%d').strftime('%d %b %Y')
            result.append({
                'key': gkey,
                'user_id': g.get('user_id'),
                'user_name': g['user_name'],
                'date': date_display,
                'total_duration': self._fmt(g['total_mins']),
                'sessions': g['sessions'],
            })
        return result

    def _fmt_comment_date(self, rec, written_at):
        """Verilən datetime/date dəyərini lokal vaxta çevirib (str, sort_str) qaytarır."""
        if written_at and hasattr(written_at, 'hour'):
            local = fields.Datetime.context_timestamp(rec, written_at)
            s = local.strftime('%Y-%m-%d %H:%M')
            return s, s
        if written_at:
            return str(written_at), str(written_at)
        return '', ''

    def _collect_all_comments(self, cap=1000):
        """Bütün modullardan qeydləri VAHID struktura yığır (filtrsiz).
        Filtrləmə üçün əlavə sahələr: source (modul), student_id, group_id/group_name, date_key.
        """
        rows = []

        def add(rec, written_at, vals):
            vals['date'], vals['date_sort'] = self._fmt_comment_date(rec, written_at)
            vals['date_key'] = (vals['date_sort'] or '')[:10]
            rows.append(vals)

        # 1) Dərs — tələbə qeydi
        lines = self.env['lesson.student.line'].search(
            [('comment', '!=', False), ('comment', '!=', '')], limit=cap,
        )
        for line in lines:
            lesson = line.lesson_id
            add(line, line.write_date or lesson.lesson_date, {
                'type': 'student',
                'type_label': 'Lesson - Comment for Student',
                'icon': 'fa-graduation-cap',
                'source': 'Lesson Record',
                'res_model': 'lesson.record',
                'res_id': lesson.id,
                'title': lesson.name or '',
                'author_name': line.write_uid.name if line.write_uid else '',
                'teacher_name': lesson.teacher_id.name if lesson.teacher_id else '',
                'student_name': line.student_id.name if line.student_id else '',
                'contact_name': None,
                'student_id': line.student_id.id if line.student_id else False,
                'teacher_id': lesson.teacher_id.id if lesson.teacher_id else False,
                'group_id': lesson.group_id.id if lesson.group_id else False,
                'group_name': lesson.group_id.name if lesson.group_id else '',
                'comment': line.comment,
            })

        # 2) Dərs — müəllimin ümumi qeydi
        lessons = self.env['lesson.record'].search(
            [('teacher_comment', '!=', False), ('teacher_comment', '!=', '')], limit=cap,
        )
        for lesson in lessons:
            add(lesson, lesson.write_date or lesson.lesson_date, {
                'type': 'teacher',
                'type_label': 'Lesson - Comment for Lesson',
                'icon': 'fa-book',
                'source': 'Lesson Record',
                'res_model': 'lesson.record',
                'res_id': lesson.id,
                'title': lesson.name or '',
                'author_name': lesson.write_uid.name if lesson.write_uid else '',
                'teacher_name': lesson.teacher_id.name if lesson.teacher_id else '',
                'student_name': None,
                'contact_name': None,
                'student_id': False,
                'teacher_id': lesson.teacher_id.id if lesson.teacher_id else False,
                'group_id': lesson.group_id.id if lesson.group_id else False,
                'group_name': lesson.group_id.name if lesson.group_id else '',
                'comment': lesson.teacher_comment,
            })

        # 3) Kontakt qeydləri (contact_notes modulu)
        if 'contact.note' in self.env:
            notes = self.env['contact.note'].search([], limit=cap)
            for note in notes:
                add(note, note.date, {
                    'type': 'contact',
                    'type_label': 'Student Note',
                    'icon': 'fa-address-book-o',
                    'source': 'Contact Notes',
                    'res_model': 'res.partner',
                    'res_id': note.partner_id.id,
                    'title': '',
                    'author_name': note.employee_id.name if note.employee_id else '',
                    'teacher_name': None,
                    'student_name': note.partner_id.name if note.partner_id else None,
                    'contact_name': None,
                    'student_id': note.partner_id.id if note.partner_id else False,
                    'teacher_id': False,
                    'group_id': False,
                    'group_name': '',
                    'comment': note.text,
                })

        # 4) Sınaq dərsi qeydləri (trail_lesson modulu) — notes (Html) + complete_notes (Text)
        #    trail.lesson CSV-də 0 ACL olduğu üçün sudo ilə oxunur
        if 'trail.lesson' in self.env:
            trials = self.env['trail.lesson'].sudo().search(
                ['|', '&', ('notes', '!=', False), ('notes', '!=', '<p><br></p>'),
                 '&', ('complete_notes', '!=', False), ('complete_notes', '!=', '')],
                limit=cap,
            )
            for tl in trials:
                parts = []
                if tl.complete_notes and tl.complete_notes.strip():
                    parts.append(tl.complete_notes.strip())
                if tl.notes:
                    plain = html2plaintext(tl.notes).strip()
                    if plain:
                        parts.append(plain)
                text = '\n\n'.join(parts)
                if not text:
                    continue
                add(tl, tl.write_date or tl.lesson_datetime, {
                    'type': 'trial',
                    'type_label': 'Trial Lesson',
                    'icon': 'fa-flask',
                    'source': 'Trail Lesson',
                    'res_model': 'trail.lesson',
                    'res_id': tl.id,
                    'title': tl.name or '',
                    'author_name': tl.write_uid.name if tl.write_uid else '',
                    'teacher_name': tl.teacher_id.name if tl.teacher_id else '',
                    'student_name': tl.student_id.name if tl.student_id else '',
                    'contact_name': None,
                    'student_id': tl.student_id.id if tl.student_id else False,
                    'teacher_id': tl.teacher_id.id if tl.teacher_id else False,
                    'group_id': False,
                    'group_name': '',
                    'comment': text,
                })

        return rows

    @api.model
    def get_dashboard_comments(self, filters=None, limit=200):
        """Filtrlənmiş vahid qeyd/comment lenti + dropdown-lar üçün filter seçimləri.

        filters (hamısı opsional):
          - text       : comment mətnində axtarış (ilike)
          - author     : müəllifin adı (dəqiq uyğunluq)
          - student_id : res.partner id (qeyd kimə aiddir)
          - group_id   : training.group id
          - source     : modul adı ('Lesson Record' / 'Contact Notes' / 'Trail Lesson')
          - date_from  : 'YYYY-MM-DD' (daxil) — tarix aralığının başı
          - date_to    : 'YYYY-MM-DD' (daxil) — tarix aralığının sonu

        Qaytarır: {'comments': [...], 'options': {authors, students, groups, sources}}
        """
        self._check_dashboard_access()
        filters = filters or {}
        rows = self._collect_all_comments()

        # Dropdown seçimləri — HƏMİŞƏ tam dəstdən (filtrlərdən asılı olmayaraq)
        authors = sorted({r['author_name'] for r in rows if r['author_name']})
        sources = sorted({r['source'] for r in rows if r.get('source')})
        students_map = {}
        for r in rows:
            if r.get('student_id'):
                students_map[r['student_id']] = r.get('student_name') or r.get('title') or ''
        teachers_map = {}
        for r in rows:
            if r.get('teacher_id'):
                teachers_map[r['teacher_id']] = r.get('teacher_name') or ''
        groups_map = {}
        for r in rows:
            if r.get('group_id'):
                groups_map[r['group_id']] = r.get('group_name') or ''
        options = {
            'authors': authors,
            'sources': sources,
            'students': sorted(
                [{'id': k, 'name': v} for k, v in students_map.items()],
                key=lambda x: (x['name'] or '').lower(),
            ),
            'teachers': sorted(
                [{'id': k, 'name': v} for k, v in teachers_map.items()],
                key=lambda x: (x['name'] or '').lower(),
            ),
            'groups': sorted(
                [{'id': k, 'name': v} for k, v in groups_map.items()],
                key=lambda x: (x['name'] or '').lower(),
            ),
        }

        def _aslist(v):
            # Tək dəyəri də, massivi də qəbul edir (geriyə uyğunluq).
            if not v:
                return []
            return list(v) if isinstance(v, (list, tuple)) else [v]

        text = (filters.get('text') or '').strip().lower()
        authors_f = _aslist(filters.get('author'))
        student_ids = _aslist(filters.get('student_id'))
        teacher_ids = _aslist(filters.get('teacher_id'))
        group_ids = _aslist(filters.get('group_id'))
        sources_f = _aslist(filters.get('source'))
        date_from = filters.get('date_from') or ''
        date_to = filters.get('date_to') or ''

        def keep(r):
            if text and text not in (r.get('comment') or '').lower():
                return False
            # çoxseçimli: dəyər seçilmiş siyahıda olmalıdır (OR)
            if authors_f and r.get('author_name') not in authors_f:
                return False
            if student_ids and r.get('student_id') not in student_ids:
                return False
            if teacher_ids and r.get('teacher_id') not in teacher_ids:
                return False
            if group_ids and r.get('group_id') not in group_ids:
                return False
            if sources_f and r.get('source') not in sources_f:
                return False
            dk = r.get('date_key') or ''
            if date_from and dk < date_from:
                return False
            if date_to and dk > date_to:
                return False
            return True

        filtered = [r for r in rows if keep(r)]
        filtered.sort(key=lambda x: x['date_sort'], reverse=True)
        return {'comments': filtered[:limit], 'options': options}

        result.sort(key=lambda x: x['date_sort'], reverse=True)
        return result[:limit]
