/** Chatter Voice Note — voice recorder patch
 *
 * Odoo-nun `VoiceRecorder` komponenti səsli mesajı 60 saniyə ilə məhdudlaşdırır
 * (limit `startRecording()` daxilindəki AudioWorklet handler-inə "hardcode" edilib).
 * Chatter qeydləri üçün bu az olduğundan, super.startRecording() çağırıldıqdan sonra
 * həmin handler-i öz variantımızla əvəz edirik — beləliklə core kodun qalan hissəsi
 * (mikrofon icazəsi, mp3 encoder, təmizləmə) olduğu kimi qalır.
 *
 * Limit: `chatter_voice_note.max_duration` sistem parametri (saniyə), standart 300.
 */
import { VoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

const DEFAULT_MAX_DURATION = 300; // saniyə
const WARNING_BEFORE_END = 10; // son 10 saniyədə sayğac qırmızıya dönür

patch(VoiceRecorder.prototype, {
    /** @returns {number} maksimum yazma müddəti (saniyə) */
    get maxDuration() {
        const configured = parseInt(session.voice_note_max_duration, 10);
        return Number.isInteger(configured) && configured > 0
            ? configured
            : DEFAULT_MAX_DURATION;
    },

    async startRecording() {
        // Brauzer mikrofona yalnız təhlükəsiz kontekstdə (HTTPS / localhost) icazə verir.
        // Əks halda `mediaDevices` ümumiyyətlə mövcud olmur — səbəbi aydın bildirək.
        if (!this.state.recording && !browser.navigator.mediaDevices) {
            this.notification.add(
                _t(
                    "Mikrofona giriş mümkün deyil. Brauzer mikrofona yalnız təhlükəsiz bağlantıda (HTTPS və ya localhost) icazə verir."
                ),
                { type: "warning" }
            );
            return;
        }
        await super.startRecording(...arguments);
        if (!this.state.recording || !this.processor) {
            return; // icazə verilmədi və ya komponent artıq söküldü
        }
        const maxDuration = this.maxDuration;
        this.processor.port.onmessage = (e) => {
            if (!this.state.recording) {
                return;
            }
            if (!this.startTimeStamp) {
                this.startTimeStamp = e.timeStamp;
            }
            const elapsedSeconds = Math.floor((e.timeStamp - this.startTimeStamp) / 1000);
            const second = elapsedSeconds % 60;
            const minute = Math.floor(elapsedSeconds / 60);
            this.state.elapsed =
                (minute < 10 ? "0" + minute : minute) +
                " : " +
                (second < 10 ? "0" + second : second);
            this.state.limitWarning = elapsedSeconds > maxDuration - WARNING_BEFORE_END;
            if (elapsedSeconds >= maxDuration) {
                this.notification.add(
                    _t("Səsli qeydin müddəti %(minutes)s dəqiqə ilə məhdudlaşır.", {
                        minutes: Math.round(maxDuration / 60),
                    }),
                    { type: "warning" }
                );
                this.stopRecording();
                return;
            }
            if (!e.data) {
                return;
            }
            this._encode(e.data);
        };
    },

    /** Fayl adı: "Səsli qeyd" olduğu aydın olsun (chatter-də qoşma adı kimi görünür). */
    filename() {
        const now = new Date();
        const pad = (n) => String(n).padStart(2, "0");
        return (
            "Voice-note-" +
            now.getFullYear() +
            pad(now.getMonth() + 1) +
            pad(now.getDate()) +
            "-" +
            pad(now.getHours()) +
            pad(now.getMinutes()) +
            pad(now.getSeconds()) +
            ".mp3"
        );
    },
});
