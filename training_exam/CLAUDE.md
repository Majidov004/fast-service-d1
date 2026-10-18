# Odoo 18 | Functional | Training Exam — Exams every 5 lessons

**Module:** `training_exam`
**Version:** 18.0.1.0.0
**Category:** Education
**Author/Tag:** Majidov

**Depends:** `mail`, `trail_lesson`, `training_management`, `lesson_record`

> `trail_lesson` niyə? İmtahan sualları **ortaq Question Bank**-dan (`trail.lesson.question`, stage = Exam) gəlir və qrupun proqram siyahısı (`SYSTEM_SELECTION`) da oradan import olunur.

> Niyə hər ikisindən asılı? `lesson_record` → `training_management` asılılığı var; bu modul "dərs bitdi" anını **real vaxtda** tutmaq üçün `lesson.record`-a, exam tab + generasiya üçün isə `training.group`-a qoşulur — yəni hər ikisi lazımdır.

---

## File Tree

```
training_exam/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── training_exam.py        → training.exam (+ mail.thread) + training.exam.student.line + training.exam.answer
│   ├── training_group.py       → _inherit training.group: yeni sahələr, action_start override, exam RPC
│   └── lesson_record.py        → _inherit lesson.record: action_complete_lesson hook (exam "ready" + bildiriş)
├── security/
│   └── ir.model.access.csv     → 3 model üçün tam CRUD (base.group_user)
├── views/
│   └── training_group_views.xml → group formuna exam_teacher_id/system_choice + Exam tab əlavə edir
└── static/src/
    ├── js/exam_widget.js        → OWL TrainingExamWidget + ExamDialog
    ├── xml/exam_widget.xml       → QWeb: training_exam.TrainingExamWidget / training_exam.ExamDialog
    └── css/exam_widget.css       → bənövşəyi kart teması (Meeting teal-dən fərqli)
```

---

## Models

### training.exam (`models/training_exam.py`)
`_inherit = ['mail.thread', 'mail.activity.mixin']` | `_order = 'group_id, exam_number'`

| Field | Type | Notes |
|---|---|---|
| `name` | Char | readonly; `"{group} — Exam {n} (after Lesson {N})"`; `action_start`-da qurulur |
| `group_id` | Many2one → training.group | required, ondelete=cascade |
| `exam_number` | Integer | readonly; 1,2,3… |
| `after_lesson_number` | Integer | readonly; 5,10,15,20 — hansı dərsdən sonra |
| `teacher_id` | Many2one → hr.employee | related `group_id.teacher_id`, store (dərs keçən müəllim) |
| `exam_teacher_id` | Many2one → hr.employee | related `group_id.exam_teacher_id`, store (imtahan müəllimi) |
| `state` | Selection | `waiting` (Waiting) / `ready` (Exam Time) / `done` (Completed); default=waiting, tracking |
| `student_line_ids` | One2many → training.exam.student.line | |
| `student_count` | Integer | compute, store (`len(student_line_ids)`) |
| `weak_count` | Integer | compute, store (result=='zeif' olanların sayı) |

**Metodlar:**
- `action_set_ready()` — `waiting → ready`, sonra `_notify_exam_ready()`. (`lesson.record` hook-undan çağırılır.)
- `_notify_exam_ready()` — imtahan müəlliminin partner-inə: admin kanalına mention (push) + exam chatter-i + müəllimin user-inə `mail.mail_activity_data_todo` activity ("Conduct exam: …"). Partner yoxdursa skip + log.
- `_mark_done_and_notify()` — `state='done'`. **Yalnız ilk tamamlanmada** (state əvvəl 'done' deyilsə) `result=='zeif'` tələbələr üçün **dərs müəlliminə** (`teacher_id`) bildiriş göndərir. Təkrar "Save Changes"-də yenidən bildiriş GETMİR.
- `_sync_questions()` — Question Bank-dan (`stage='exam'`, `exam_number`, qrupun `system_choice`) uyğun sualları hər tələbə sətri üçün `training.exam.answer` kimi yaradır. **Mövcud sətirlərə toxunmur** (yalnız çatışmayanı əlavə edir), `state=='done'` imtahanda heç nə etmir. `get_exam_detail()`-dən çağırılır (lazy).
- Köməkçilər: `_partner_of_employee(emp)` (user_id.partner_id, yoxsa address_id), `_mention(partner)` (Markup `<a o_mail_redirect>`), `_post_notification(partners, body)` (mail.channel_admin + öz chatter; lesson_record cron-u ilə eyni nümunə).

### training.exam.student.line (`models/training_exam.py`)
`_rec_name = 'student_id'`

| Field | Type | Notes |
|---|---|---|
| `exam_id` | Many2one → training.exam | required, ondelete=cascade |
| `student_id` | Many2one → res.partner | required |
| `result` | Selection | `zeif` (Weak) / `orta` (Average) / `ela` (Excellent); boş ola bilər |
| `note` | Text | suala görə sərbəst qeyd (məs. `1.+ / 2.did yerinə do / …`) |

SQL: `UNIQUE(exam_id, student_id)`. Əlavə: `answer_ids` One2many → `training.exam.answer`.

### training.exam.answer (`models/training_exam.py`)
`_order = 'sequence, id'`

| Field | Type | Notes |
|---|---|---|
| `line_id` | Many2one → training.exam.student.line | required, cascade, index |
| `question_id` | Many2one → trail.lesson.question | hansı bank sualından gəlib (ondelete=set null) |
| `question` | Text | sualın **snapshot**-u (bank sonradan dəyişsə də imtahanda qalır) |
| `answer` | Char | tələbənin cavabı |
| `sequence` | Integer | |

SQL: `UNIQUE(line_id, question_id)`.

---

## training.group genişlənməsi (`models/training_group.py`, _inherit)

**Yeni sahələr:** `exam_teacher_id` (hr.employee), **`system_choice`** (Selection — `SYSTEM_SELECTION`, qrupun proqramı; imtahan suallarını süzür), `exam_view` (Char compute=False — OWL widget mount nöqtəsi).

> **Manager sahəsi SİLİNİB** — qrupda menecer yoxdur, zəif nəticə bildirişi yalnız dərs müəlliminə gedir.

**`action_start()` override:** `super()` (dərsləri yaradır) → sonra hər record üçün `_generate_exams()`.

**`_generate_exams()`:** Əgər qrupda artıq exam varsa, çıxır (təkrar yox). `range(5, lesson_count+1, 5)` üzrə hər milestone üçün bir `training.exam` + hər tələbə üçün `training.exam.student.line` yaradır. 20 dərs → 4 exam; 5-dən kiçik qalıq buraxılır.

**RPC metodları (OWL widget üçün):**
- `get_exam_cards()` — qrupun exam-larının kart datası (id, name, exam_number, after_lesson_number, state, student_count, weak_count).
- `get_exam_detail(exam_id)` — əvvəlcə `exam._sync_questions()` çağırır, sonra hər tələbə üçün `line_id, student_name, result, note` + **`answers`** (answer_id, question, answer) qaytarır. Qrup yoxlaması var.
- `save_exam(exam_id, payload)` — payload.students-dən result+note **və hər sualın cavabını** (`answers[].answer_id/answer`) yazır; `payload.complete` varsa `exam._mark_done_and_notify()`. Həmişə `get_exam_cards()` qaytarır.

---

## lesson.record genişlənməsi (`models/lesson_record.py`, _inherit)

**`action_complete_lesson()` override:** `super()` → `_check_exam_ready()`.

**`_check_exam_ready()`:** Tamamlanmış (`state=='completed'`) və `lesson_number % 5 == 0` olan hər dərs üçün — eyni qrupda `after_lesson_number==lesson_number` və `state=='waiting'` olan exam-ı tapıb `action_set_ready()` çağırır. Dərs həm forma düyməsindən, həm də Meeting widget-dən (`save_meeting_lesson` → `action_complete_lesson`) tamamlana bildiyi üçün hər iki yol tutulur.

---

## Frontend (OWL)

`web.assets_backend`-də qeydiyyatdan keçən field widget: **`training_exam_widget`** (`supportedTypes: ['char']`), group formundakı Exam tab-ında `exam_view` sahəsinə bağlanır.

- **TrainingExamWidget** — `get_exam_cards()` ilə kartları yükləyir; klik → `ExamDialog`. **Manual yaratma yoxdur.**
- **ExamDialog** (`size='xl'`) — **üç sütun**: (1) solda tələbə siyahısı (nəticəyə görə rəngli nöqtə: zeif=qırmızı, orta=narıncı, ela=yaşıl); seçilən tələbənin redaktoru isə `o_te_split` ilə **iki yerə** bölünür: (2) **solda suallar** — bank sualları + hər birinin altında cavab `input`-u (`onAnswer`), (3) **sağda** 3 nəticə düyməsi (Weak/Average/Excellent) + "Comment" `textarea`. Sual yoxdursa Question Bank-a yönləndirən mətn görünür. Dar ekranda sütunlar alt-alta düzülür.
  Footer: "Complete Exam" (ilk dəfə) / "Save Changes" (artıq done). `complete = state !== 'done'`.
- Kart rəngləri: `waiting`=boz (sönük), `ready`=narıncı vurğu, `done`=bənövşəyi (sönük). Border-left #7d4cdb (Meeting #00a09d-dən fərqli).

---

## Security

| Model | Group | R/W/C/D |
|---|---|---|
| training.exam | base.group_user | 1/1/1/1 |
| training.exam.student.line | base.group_user | 1/1/1/1 |
| training.exam.answer | base.group_user | 1/1/1/1 |

> Görmə imtiyazları (imtahan müəllimi dərsləri görməsin, dərs müəllimi exam nəticəsini görsün) **bu modulda EDİLMƏYİB** — qəsdən. Ayrıca imtiyazlar modulunda ediləcək.

---

## Axın (flow)

```
training.group.action_start()
  ├─ super(): lesson.record-lar yaranır
  └─ _generate_exams(): hər 5 dərsə 1 training.exam (state=waiting) + student line-lar

lesson.record.action_complete_lesson()  [forma düyməsi VƏ YA Meeting widget]
  └─ N%5==0 dərs completed → uyğun exam.action_set_ready()
        └─ exam.state=ready + imtahan müəlliminə bildiriş/activity

Exam tab → kart → ExamDialog (get_exam_detail → _sync_questions: Question Bank-dan suallar)
  → solda suallara cavab, sağda nəticə + comment → "Complete Exam"
  └─ save_exam(complete=True) → exam._mark_done_and_notify()
        └─ state=done; result=='zeif' tələbələr üçün teacher_id-ə bildiriş (yalnız ilk dəfə)
```

---

## Important Notes

1. **Bildiriş nümunəsi `lesson_record` cron-u ilə eynidir:** `mail.channel_admin`-ə partner_ids ilə post (push) + öz chatter-i. `base.user_admin` author. `_partner_of_employee` müəllimi partner-ə çevirir.
2. **Zəif bildiriş yalnız bir dəfə:** `_mark_done_and_notify` yalnız ilk `done`-a keçiddə bildiriş göndərir. Exam artıq done olandan sonra nəticə dəyişib tələbə zəifə düşsə, **yenidən bildiriş getmir** (bilinən məhdudiyyət).
3. **`action_modify()` exam-lara toxunmur:** Qrup başladıqdan sonra `action_modify` ilə əlavə edilən yeni tələbələr/dərslər mövcud exam-lara avtomatik düşmür (bilinən məhdudiyyət; lazım olarsa sonra əlavə edilə bilər).
4. **Manual exam yaratma yoxdur:** Exam-lar yalnız `action_start`-da avtomatik yaranır; tab-da yaratma düyməsi yoxdur, ayrıca menyu/act_window da yoxdur — exam yalnız OWL dialoq vasitəsilə redaktə olunur.
5. **`exam_teacher_id`/`teacher_id` təyin olunmayıbsa** uyğun bildiriş sadəcə skip olunur + log yazılır (xəta atmır).
5b. **Qrupun `system_choice`-u boşdursa** imtahana bütün proqramların sualları düşür (filtr tətbiq olunmur) — qrup yaradılanda proqramı seçmək tövsiyə olunur.
6. **5-ə bölünməyən `lesson_count`:** qalıq (məs. 22 → 5,10,15,20) imtahansız buraxılır.
7. **Odoo 18 invisible/readonly:** view-larda Python expression formatı ([[feedback_odoo18_invisible]]).
