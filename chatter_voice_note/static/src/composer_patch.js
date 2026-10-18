/** Chatter Voice Note — composer patch
 *
 * Odoo standartda mikrofon düyməsini yalnız `discuss.channel` söhbətlərində göstərir
 * (bax: mail/static/src/discuss/voice_message/common/composer_patch.xml).
 * Burada həmin şərti chatter-ə də açırıq: istənilən modelin Log note / Send message
 * composer-ində səsli qeyd yazmaq mümkün olur.
 */
import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    /**
     * Mikrofon düyməsi göstərilsinmi?
     * - qoşma yükləməyə icazə olmalıdır (allowUpload)
     * - thread olmalıdır (yeni, saxlanılmamış qeyddə də composer thread-i olur)
     * - mövcud mesajın redaktəsində göstərmirik (yalnız discuss kanalında standart davranış qalır)
     */
    get hasVoiceNoteRecorder() {
        if (!this.allowUpload || !this.thread) {
            return false;
        }
        if (this.thread.model === "discuss.channel") {
            return true; // Odoo-nun standart davranışı
        }
        return !this.props.composer.message;
    },
});
