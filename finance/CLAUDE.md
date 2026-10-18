# finance — Module Map

**Odoo 18 | Application | Simple cash management: Cash In / Cash Out, transfers, OWL dashboard**

Depends: `base`, `mail`, `hr`, `contact_customization`

> **Niyə `contact_customization`-dan asılı:** `finance.cash.move.student_id` domain-i `[('is_student','=',True)]` istifadə edir — `is_student` sahəsi `contact_customization`-dadır. Bu, bütün zənciri (`lesson_record` → `training_management`, `trail_lesson`) gətirir.

---

## File Tree

```
finance/
├── __manifest__.py
├── __init__.py
├── security/
│   └── ir.model.access.csv          → 6 model, hamısına base.group_user tam CRUD
├── data/
│   ├── finance_sequence.xml         → CIN/ , COUT/ , TRF/ sequence-ləri
│   └── finance_data.xml             → seed: ödəniş üsulları (Nağd/Köçürmə/Kart) + nümunə kateqoriyalar
├── models/
│   ├── finance_cash_register.py     → Kassa + balans + dashboard helper-ləri
│   ├── finance_payment_method.py    → ödəniş üsulu lookup
│   ├── finance_expense.py           → Xərc maddələri ("Xərc Modulu")
│   ├── finance_category.py          → Gəlir/Xərc qrupları + detail_type kaskadı
│   ├── finance_cash_move.py         → Cash In / Cash Out sənədi
│   ├── finance_transfer.py          → kassalar arası transfer
│   └── res_currency.py              → res.currency genişləndirmə: sadə `finance_rate` (bir sahə) məzənnə
├── views/
│   ├── finance_cash_register_views.xml
│   ├── finance_payment_method_views.xml
│   ├── finance_expense_views.xml
│   ├── finance_category_views.xml
│   ├── finance_cash_move_views.xml      → list/form/search + Cash In & Cash Out action-ları
│   ├── finance_transfer_views.xml
│   ├── finance_dashboard_action.xml     → ir.actions.client (tag: finance.Dashboard)
│   └── finance_menus.xml                → Finance app: Dashboard / Əməliyyat / Configuration
└── static/src/
    ├── js/finance_dashboard.js          → OWL FinanceDashboard (client action)
    ├── xml/finance_dashboard.xml         → QWeb finance.Dashboard
    └── css/finance_dashboard.css
```

---

## Models

### finance.cash.register (Kassa)
`_order = 'name'`

| Field | Type | Notes |
|---|---|---|
| `name` | Char | required |
| `currency_id` | Many2one res.currency | required, default = company currency — **kassanın öz valyutası** |
| `responsible_user_id` | Many2one res.users | |
| `active` | Boolean | default True |
| `note` | Text | |
| `balance` | Monetary (compute, `currency_field='currency_id'`) | non-stored; sənəddə göstərilmir, yalnız dashboard/Configuration |

**`_compute_balance()`** (depends YOX → hər oxunuşda hesablanır): təsdiqlənmiş `cash_in.amount_register` − `cash_out.amount_register` − `transfer.amount`(from) + `transfer.amount_to`(to). Hamısı kassa valyutasında.

**Dashboard helper-ləri:**
- `_period_ranges(period)` → ((cur_from,cur_to),(prev_from,prev_to),prev_label); period ∈ `day`/`week`/`month`. prev_label: dünənə / keçən həftəyə / keçən aya.
- `_sum_io(date_from, date_to)` → (money_in, money_out) — təsdiqlənmiş, `amount_register` cəmi, tarix aralığında.
- `_pct(cur, prev)` (staticmethod) → `{has, value, dir}` (dir: up/down/flat); prev=0 olduqda `has=False`.
- `_card_payload(period)` → kart üçün dict (id, name, balance_fmt, money_in/out_fmt, in_pct/out_pct, prev_label, …). Məbləğlər `"{:,.2f} {symbol}"` formatında.
- **`get_dashboard(period='month')`** (`@api.model`) → bütün kassalar üçün kart siyahısı.
- **`get_card_data(period)`** (instance) → tək kassa kartı (kartın period-u dəyişəndə OWL bunu çağırır).

### finance.payment.method
`name`, `sequence` (default 10), `active`. Default ödəniş üsulu = ən kiçik sequence (seed-də **Nağd**=1).

### finance.expense ("Xərc Modulu")
`name`, `note`, `active`. Cash Out kateqoriyası `expense` olduqda seçilən detal.

### finance.category (Gəlir/Xərc qrupları)
| Field | Type | Notes |
|---|---|---|
| `name` | Char | required |
| `direction` | Selection income/expense | required (income → Cash In, expense → Cash Out) |
| `detail_type` | Selection none/expense/employee/student/partner | required, default none — sənəddə açılan detal sahəsini təyin edir |
| `active` | Boolean | |

### finance.cash.move (Cash In / Cash Out)
`_inherit = ['mail.thread','mail.activity.mixin']` | `_order = 'date desc, id desc'`

| Field | Type | Notes |
|---|---|---|
| `name` | Char | auto-seq (CIN/… və ya COUT/…), readonly, default 'New' |
| `move_type` | Selection cash_in/cash_out | required, default cash_in (action context-dən) |
| `date` | Date | default today |
| `register_id` | Many2one finance.cash.register | required |
| `register_currency_id` | Many2one (related register.currency_id, store) | |
| `currency_id` | Many2one res.currency | required, default company; register seçiləndə onchange ilə register valyutasına dəyişir |
| `amount` | Monetary (`currency_field='currency_id'`) | required |
| `amount_register` | Monetary (compute, **non-stored**, `currency_field='register_currency_id'`) | **amount-un kassa valyutasına çevrilmişi** (`currency._convert`, sənəd tarixinə görə); balans bunu istifadə edir. **Stored deyil** → məzənnə düzələndə avtomatik yenilənir |
| `amount_company` | Monetary (compute, **non-stored**, `currency_field='company_currency_id'`) | amount-un şirkət valyutasına çevrilmişi; dashboard KPI/kateqoriya cəmləri bunu istifadə edir |
| `category_id` | Many2one finance.category | domain `[('direction','=',category_direction)]` |
| `category_direction` | Selection (compute from move_type) | income/expense |
| `detail_type` | Selection (related category_id.detail_type) | view görünürlüyü üçün |
| `expense_id` / `employee_id` / `student_id` / `partner_id` | Many2one | kaskad — yalnız `detail_type`-a uyğun biri görünür/required olur (`student_id` domain: is_student) |
| `payment_method_id` | Many2one | default = ilk (Nağd) |
| `note` | Text | |
| `state` | Selection draft/confirmed/cancelled | default draft, tracking |

**Metodlar:** `_compute_category_direction` (move_type→direction), `_compute_amount_register` (eyni valyuta→bərabər, fərqli→`_convert`), onchange `register_id` (currency=register currency), onchange `move_type` (uyğunsuz kateqoriyanı sıfırla), onchange `category_id` (detal sahələri sıfırla), constrain amount>0, `create` (sequence move_type-a görə), `action_confirm`/`action_draft`/`action_cancel`.

### finance.transfer (kassalar arası)
`_inherit=['mail.thread']`. `from_register_id`/`to_register_id` (fərqli olmalı), `amount` (from valyutada), `amount_to` (compute → to valyutaya `_convert`), `date`, `state`. `action_confirm`/`draft`/`cancel`. Sequence TRF/.

---

## Dashboard (OWL client action)

- **Action:** `ir.actions.client`, tag `finance.Dashboard` (`finance_dashboard_action.xml`).
- **Component:** `FinanceDashboard` (`actions` registry). Chart.js `loadJS("/web/static/lib/Chart/Chart.js")` ilə yüklənir.
- **Üst global period** (Gün/Həftə/Ay) — KPI + qrafik + kateqoriyaları idarə edir (`state.period`, default month).
- Bölmələr:
  1. **KPI zolağı** — Ümumi Balans (bütün kassalar şirkət valyutasına çevrilmiş, `amount_company`), period üzrə Daxil / Xaric / Net, təsdiq gözləyən qaralama sayı.
  2. **Orta sıra — sol panel: Kassalar** (scroll) — hər kassa bir kart, **per-card period** (`setCardPeriod` → `get_card_data`), Daxil/Xaric + % trend + tooltip. *(Əvvəlki Chart.js trend qrafiki ÇIXARILIB.)*
  3. **Orta sıra — sağ panel: Category Breakdown by Register** (scroll) — hər kassa bir kart, içində **cədvəl**: `Category | In | Out` sütunları, hər kateqoriya bir sətir (öz In/Out məbləği, olmayan tərəf `—`), altda **Total** sətri. Məbləğlər `amount_register` (kassa valyutası). Backend item: `{id, name, in_fmt, out_fmt}` + register-də `total_in_fmt`/`total_out_fmt`.
  4. **Recent Transactions** — son 10 Cash In/Out cədvəli (klik → sənədi açır, `action` service).
- **Bütün etiketlər İngilis dilindədir**; "period" sözü UI-dan çıxarılıb. Trend faizinin tooltip-i İngiliscə (`prev_label`: yesterday / last week / last month).
- **Backend metodları:** `get_overview(period)` (KPI + `categories_by_register` + recent), `get_dashboard(period)` (kartlar), `get_card_data(period)` (tək kart). Qrafik/`_chart_buckets` artıq yoxdur.

---

## Menus (`finance_menus.xml`)

```
Finance (root, sequence 20)
├── Dashboard            (action_finance_dashboard, seq 1)
├── Əməliyyat            (seq 10)
│   ├── Cash In          (action_finance_cash_in — domain move_type=cash_in, default cash_in)
│   ├── Cash Out         (action_finance_cash_out)
│   └── Transfer         (action_finance_transfer)
└── Configuration        (seq 90)
    ├── Cash Registers
    ├── Categories
    ├── Expense Items
    ├── Payment Methods
    └── Currencies        (action_finance_currency — sadələşdirilmiş, yalnız base.group_system)
```

> **Valyuta (sadələşdirilmiş):** `res.currency` Odoo core-dur, amma Finance öz **sadə ekranını** verir (`finance_currency_views.xml` + `res_currency.py`). Standart qəliz "Rates" tab-ı əvəzinə yalnız bir **`finance_rate`** sahəsi var: *"1 [şirkət valyutası] = X [bu valyuta]"* (bugünkü məzənnə). Yazıldıqda inverse metod bugünkü tarixlə `res.currency.rate` sətrini yaradır/yeniləyir (`sudo`). Əsas/şirkət valyutası (`is_company_currency`) həmişə 1, readonly. Action `{'active_test': False}` ilə arxiv valyutaları da göstərir ki, aktivləşdirə biləsən.

---

## Security

`ir.model.access.csv` — 6 modelin hamısına `base.group_user` tam CRUD (1,1,1,1). Rol ayrımı yoxdur.

---

## Applicant → Student konversiyası & müştəri borcu (Finance report)

İki yoldan finance sənədləri yaranır; hər ikisi `finance` modulundadır (dövri asılılıqdan qaçmaq üçün — `trail_lesson`/`contact_customization` finance-i tanımır):

- **`finance.student.charge`** (`finance_student_charge.py`) — tələbənin borc sənədi (`student_id`, `amount`, `source`: trial/manual). `get_customer_report(period, date_from, date_to, partner_id, move_type)` müştəri ledgerini qurur (OWL `customer_report.js` mənbəyi). **Filtrlər** operations report-dakı kimi: period presetlər (day/week/month/last_3m/6m/1y/between/all) + From/To, **Student** (yazıb-axtarmalı — `FilterSelect`-ə əlavə olunmuş `searchable` prop, "All Students"), tip (Debt/Cash In/Cash Out); `_period_ranges` `finance.cash.register`-dən təkrar istifadə olunur. Əlavə **"With activity only"** toggle (client-side, `state.hideEmpty` → `visibleCustomers` getter) seçilmiş filtrlərə uyğun sətri olmayan müştəriləri gizlədir. **Sütunlar:** `Date | Document | Type | Currency | Opening Balance | Charges | Payments | Refunds | Closing Balance` (standart customer statement terminologiyası). Müştərinin **ad sətrində** Opening Balance (period başından əvvəlki net borc = Σ charge − Σ Cash In + Σ Cash Out), period üzrə **Charges/Payments/Refunds cəmləri** və Closing Balance (= Opening + Charges − Payments + Refunds) göstərilir; **əməliyyat sətirləri** öz Charges **və ya** Payments/Refunds dəyərini daşıyır (charge → Charges; Cash In → Payments; Cash Out → Refunds; Opening/Closing xanaları boş). Type sütunundakı badge-lər `Debt/Cash In/Cash Out` qalır. Bütün məbləğlər şirkət valyutasına normallaşdırılır (`amount_company`), Currency sütunu sənədin öz valyutasını göstərir. Opening/cəm/Remaining **bütün tipləri** əhatə edir — tip filtri yalnız görünən sətirləri daraldır. Borc müsbət (`o_debt` qırmızı), 0/mənfi `o_clear_amt` yaşıl.
- **Yol 1 — Sınaq tamamlama wizard-ı** (`trail_lesson_complete_wizard.py`, `_inherit='trail.lesson.complete.wizard'`): `action_confirm`-də `_finance_create_documents()` **yalnız joining+now deyil**, həm də tələbə **hər hansı ödəniş edibsə** (`payment_amount>0`), borc varsa (`total_payment_amount>0`) və ya gələcək vəd (`promise_due_date`) verilibsə çağırılır. **Payment Type (full/deposit):** `full` seçiləndə view-da yalnız `total_payment_amount` + `register_id` görünür və `action_confirm` super()-dən ƏVVƏL `payment_amount = total_payment_amount` təyin edir (tam məbləğə charge + tam məbləğə Cash In → qalıq borc 0); `deposit` seçiləndə `payment_amount` (indi ödənilən) + `promise_due_date` də görünür (**`promise_note` sahəsi SİLİNİB** — promise-in note-u avtomatik "Rest of the trial payment (TL/…)" mətnidir). Həmçinin `payment_type == 'full'` olanda **Join Timing sətri gizlənir** və `join_timing` avtomatik `now` olur (trail_lesson tərəfindəki onchange). Beləcə sonraya qoşulan amma **depozit/hissə ödəyən** tələbənin ödənişi də finance-ə düşür (Cash In `student_id` applicant olsa belə kodla yazılır; customer report applicant-ları da əhatə edir). → total üçün charge + ödəniş üçün təsdiqli Cash In + vəd üçün promise.
- **Yol 2 — Applicant "Paid" düyməsi** (`applicant_paid_wizard.py` + `res_partner.py`): `res.partner.action_set_paid` finance-də override olunub — `skip_finance_wizard` context-i yoxdursa birbaşa çevirmir, **`finance.applicant.paid.wizard`** dialoqunu açır. **Payment Type əsaslı sadə axın:** dialoq ilkin olaraq yalnız **2 sahə** göstərir — `payment_type` (full/deposit) + `current_debt` (read-only, **bold**). Payment Type seçilməyincə qalan sahələr gizlidir. **`full`** seçiləndə `paid_now` borc məbləği ilə öncədən doldurulur (redaktə oluna bilər) + `register_id` açılır; `paid_now` borcdan **az** edilərsə onchange avtomatik `payment_type='deposit'`-ə keçir. **`deposit`** seçiləndə `paid_now` (0 ola bilər) + `register_id` + `promise_due_date` + `note` görünür. `paid_now>0` olduqda təsdiqli Cash In, `promise_due_date` varsa promise yaranır. `payment_method_id`/`category_id` gizli, default-larla. **Borc yaratma:** `create_charge` (compute, borc yoxdursa avtomatik işarələnir) + `charge_amount` step-2-də qalır; işarələnəndə yeni `finance.student.charge` yaranır. Köməkçi `total_due` = `current_debt` + (yeni borc) — `full` ödənişdə `paid_now` bununla öncədən doldurulur (charge_amount dəyişəndə onchange yenidən hesablayır). Təsdiqdə wizard `partner.with_context(skip_finance_wizard=True).action_set_paid()` çağırır → əsl konversiya (contact_customization-dakı orijinal metod). **Konversiya yalnız təsdiqdə baş verir** — imtina edilərsə müraciətçi applicant qalır. Default kassa/kateqoriya `finance.default_register_id` / `finance.student_payment_category_id` config param-larından (`res_config_settings.py`).

## Ödəniş vədləri / hissə-hissə ödəniş (`finance.payment.promise`)

Tələbə bir hissəni indi ödəyib qalanını gələcəkdə (məs. "1 həftə sonra") vəd edəndə, hər vəd üçün xatırlatma qurulur.

- **Model `finance.payment.promise`** (`finance_payment_promise.py`, `mail.thread`+`mail.activity.mixin`, seq `VED/`): `student_id`, `amount`/`currency_id`, `due_date`, `state` (pending/paid/cancelled), `register_id`, `charge_id` (əlaqəli borc), `responsible_user_id`, `cash_move_id`, `reminder_sent`.
  - **`create()`** → `_schedule_reminder()`: `due_date`-ə **To-Do mail.activity** (`mail.mail_activity_data_todo`) məsul istifadəçiyə təyin edir → Odoo systray/Activities-də "Today/Overdue" göstərir.
  - **`action_register_payment()`**: təsdiqli Cash In yaradır (`student_id`, student payment kateqoriyası), `cash_move_id` təyin edir, `state='paid'`, activity-ni done edir, chatter-ə mesaj.
  - **`action_cancel()` / `action_reset_pending()`**.
  - **Cron `_cron_payment_promise_reminders()`** (`finance_cron.xml`, gündəlik): `due_date <= bugün` olan, hələ `reminder_sent=False` pending vədlər üçün chatter-də məsul şəxsi tag edən aktiv mesaj göndərir, sonra `reminder_sent=True` (təkrar yox). Activity passiv, cron aktiv mesaj.
  - `amount` **ixtiyaridir** (vəd sadəcə tarix xatırlatmasıdır; məbləğ sonradan, ödənişi qeydə alanda təyin olunur — `action_register_payment` məbləğ 0-dırsa UserError verir).
- **Hər iki wizard** tarix verilərsə təsdiqdə bir promise yaradır (List/One2many YOXDUR). `trail_lesson_complete_wizard`-da yalnız `promise_due_date` (note avtomatik yazılır); `applicant_paid_wizard`-da `promise_due_date` + ümumi `note`.
- **Menyu:** Finance → Əməliyyat → **Payment Promises** (default Pending filtri; siyahıda overdue=qırmızı, bugün=sarı, paid=yaşıl).

## Important Notes

1. **Valyuta məntiqi:** Kassanın öz valyutası var; sənəddə fərqli valyuta seçilə bilər. `amount_register` = amount-un kassa valyutasına çevrilmişi (read-only, yalnız valyutalar fərqli olduqda formada görünür). Balans **həmişə** kassa valyutasında (`amount_register` üzərindən). Konvertasiya **Odoo-nun `_convert`-i ilə YOX**, `res.currency.finance_convert(amount, to_currency)` ilə edilir — bu, Currencies ekranındakı `finance_rate` (bugünkü məzənnə) üzərindən deterministik hesablayır: `amount * (to.finance_rate / from.finance_rate)`. Beləcə formada görünən nəticə Currencies siyahısındakı məzənnə ilə tam üst-üstə düşür (Odoo-nun tarix/şirkət əsaslı məzənnə seçim qəlizliyi aradan qalxır). `amount_register`/`amount_company`/`transfer.amount_to` **non-stored** — məzənnə düzələndə bütün sənədlər avtomatik yenilənir.
2. **Balans sənəddə göstərilmir** — yalnız Dashboard kartlarında və kassa formasında (`balance` compute).
3. **Təsdiq balansa təsir edir:** balans yalnız `state='confirmed'` sənədləri sayır. Posting/journal entry yoxdur — balans hər oxunuşda hesablanır.
4. **Kateqoriya kaskadı:** `category_id.detail_type` formada bir detal sahəsi açır (expense/employee/student/partner) və onu required edir; qalanları gizlədir. move_type kateqoriya `direction`-ı filtrləyir (cash_in→income, cash_out→expense).
5. **Sequence-lər:** CIN/%(year)s/, COUT/%(year)s/, TRF/%(year)s/ — `create`-də `move_type`-a görə seçilir.
6. **`contact_customization` asılılığı** sırf `is_student` domain-i üçündür (student detal sahəsi). Tək valyuta/sadə versiya istənilsə bu asılılıq yenidən qiymətləndirilə bilər.
7. **Odoo 18:** `invisible`/`required` Python expression; list-də `<list>`, Monetary üçün currency sahəsi view-da (column_invisible olsa belə) mövcud olmalıdır.
