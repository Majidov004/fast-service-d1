# chatter_voice_note — Module Map

**Odoo 18 | Technical | Enables Odoo's built-in voice recorder inside the chatter (Log note / Send message) for every model**

Depends: `mail`, `web`

---

## Nə edir?

Odoo 18 səsli mesaj (voice message) infrastrukturunu **artıq daxilində gətirir**, amma mikrofon
düyməsi yalnız Discuss kanallarında (`discuss.channel`) görünür. Bu modul həmin düyməni
istənilən modelin chatter-ində — məsələn `res.partner` (Applicants/Students) formasında —
**Log note** və **Send message** rejimlərində aktiv edir.

Yazılan səs `.mp3` faylı kimi mesaja qoşma (attachment) olur və chatter-də Odoo-nun öz
**dalğa formalı səs pleyeri** (`VoicePlayer`) ilə göstərilir — heç bir yeni model/cədvəl yaradılmır.

**Əlavə:** Odoo-nun 60 saniyəlik yazma limiti genişləndirilib — standart **300 saniyə (5 dəq)**,
`chatter_voice_note.max_duration` sistem parametri ilə tənzimlənir.

---

## File Tree

```
chatter_voice_note/
├── __manifest__.py                        → Metadata, depends (mail, web), asset declarations
├── __init__.py                            → Imports models
│
├── models/
│   ├── __init__.py                        → Imports ir_http
│   └── ir_http.py                         → session_info() override → voice_note_max_duration
│
├── data/
│   └── ir_config_parameter.xml            → Default chatter_voice_note.max_duration = 300 (noupdate)
│
└── static/src/
    ├── composer_patch.js                  → Composer.hasVoiceNoteRecorder getter (düymə görünsünmü?)
    ├── composer_patch.xml                 → mail.Composer.sendButton şablonunda VoiceRecorder-in t-if şərtini əvəz edir
    ├── voice_recorder_patch.js            → Maks. müddət + təhlükəsiz kontekst xəbərdarlığı + fayl adı
    └── voice_note.scss                    → Mikrofon düyməsinin chatter görünüşü (hover / recording)
```

---

## Mexanizm (necə işləyir)

### 1. Düymənin görünməsi — `composer_patch.xml` + `composer_patch.js`

Odoo core (`mail/static/src/discuss/voice_message/common/composer_patch.xml`) `mail.Composer.sendButton`
şablonuna bu düyməni əlavə edir:

```xml
<VoiceRecorder t-if="thread?.model === 'discuss.channel' and allowUpload" ... />
```

Bu modul həmin node-un yalnız `t-if` atributunu əvəz edir (`t-inherit-mode="extension"` + `xpath //VoiceRecorder`):

```xml
<attribute name="t-if">hasVoiceNoteRecorder</attribute>
```

`hasVoiceNoteRecorder` getter-i (`composer_patch.js`, `Composer.prototype`):

| Şərt | Nəticə |
|------|--------|
| `allowUpload` yoxdur / thread yoxdur | `false` |
| `thread.model === 'discuss.channel'` | `true` (Odoo-nun standart davranışı toxunulmaz) |
| digər hallar (chatter) | mövcud mesajın **redaktəsi** deyilsə `true` (`!props.composer.message`) |

> Chatter-də composer `mode="extended"` ilə render olunur → mikrofon **Log / Send düyməsinin solunda** çıxır.
> `props.type` (`"note"` / `"message"`) ilə fərq qoyulmur — düymə hər iki rejimdə görünür.

### 2. Yazma müddəti — `voice_recorder_patch.js`

Core `VoiceRecorder.startRecording()` daxilində `processor.port.onmessage` handler-i 60 saniyəni
"hardcode" edir. Patch `super.startRecording()`-i çağırdıqdan **sonra** həmin handler-i öz variantı ilə
əvəz edir (mikrofon icazəsi, mp3 encoder, cleanup — hamısı core-da qalır):

- `maxDuration` getter → `session.voice_note_max_duration` (yoxdursa 300)
- son 10 saniyədə sayğac qırmızıya dönür (`state.limitWarning`)
- limitə çatanda bildiriş + `stopRecording()`
- `filename()` override → `Voice-note-YYYYMMDD-HHMMSS.mp3`
- `mediaDevices` yoxdursa (HTTP üzərindən açılıb) — aydın izahlı warning bildirişi

### 3. Limitin konfiqurasiyası — `ir_http.py`

`ir.http.session_info()` override-u `voice_note_max_duration` açarını web client session-una əlavə edir.
Dəyər: **Settings → Technical → System Parameters → `chatter_voice_note.max_duration`** (saniyə).
Yanlış/0/mənfi dəyər → 300-ə qayıdır. Dəyişiklikdən sonra brauzeri yeniləmək (F5) kifayətdir.

### 4. Server tərəfi — dəyişiklik YOXDUR

Səs faylı Odoo-nun mövcud axını ilə gedir:

```
VoiceRecorder.stopRecording()
  → attachmentUploader.uploadFile(file, { voice: true })
  → POST /mail/attachment/upload   (thread_model = res.partner və s.)
  → ir.attachment._post_add_create(voice=True) → discuss.voice.metadata yaradılır
  → mesaj post olunanda attachment mesaja bağlanır
  → chatter-də AttachmentList → attachment.voice → <VoicePlayer/>
```

`/mail/attachment/upload` controller-i model-agnostikdir, ona görə `res.partner`, `lesson.record` və
istənilən `mail.thread` modelində eyni işləyir.

---

## Məhdudiyyətlər / Qeydlər

- **HTTPS tələbi:** brauzer `navigator.mediaDevices`-i yalnız təhlükəsiz kontekstdə (HTTPS və ya
  `localhost`) verir. Odoo LAN IP-si üzərindən HTTP ilə açılırsa mikrofon işləməyəcək —
  patch bu halda izahlı bildiriş göstərir.
- Bir mesaja **bir səsli qeyd** yazıla bilər (core davranışı: `composer.voiceAttachment` varsa düymə deaktivdir).
  Növbəti qeyd üçün mövcud səs qoşmasını silmək lazımdır.
- Səs mp3 (128 kbit/s) kimi kodlanır → ~1 MB/dəq. 5 dəqiqə ≈ 5 MB attachment.
- Modul core şablonuna (`mail.Composer.sendButton`) və core komponentinə (`VoiceRecorder`) bağlıdır —
  **Odoo 18.0** üçün yazılıb. Major versiya yüksəlişində bu iki nöqtə yoxlanmalıdır.
- Görmə imtiyazı ayrıca yoxdur: düymə chatter-i olan hər istifadəçidə görünür.
  Lazım gələrsə `hasVoiceNoteRecorder` getter-inə qrup yoxlaması əlavə edilə bilər.

---

## Quraşdırma

1. Modul artıq `addons_path`-dədir (`c:\odoo_modul1`).
2. Apps → **Update Apps List** → "Chatter Voice Note" → Install.
3. Hər hansı kontakt/qeyd formasını aç → **Log note** → mikrofon ikonuna bas → danış → yenidən bas → **Log**.
