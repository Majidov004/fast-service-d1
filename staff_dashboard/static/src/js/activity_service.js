/** @odoo-module **/
import { registry } from "@web/core/registry";

const activityTrackerService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        let currentPath = window.location.pathname;

        // Hər səhifə yüklənişində (web client boot) unikal token yaradılır.
        // Yaddaşda saxlanılır → tam yenidən yükləmədə (link ilə hər giriş, login redirect,
        // tab-ın yenidən açılması) dəyişir, amma SPA daxili naviqasiyada SABİT qalır.
        // Beləcə link ilə hər giriş AYRI sessiya kimi qeyd olunur.
        const clientToken = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

        const sendHeartbeat = async () => {
            try {
                await orm.call("user.login.log", "update_heartbeat", [], {
                    module_path: window.location.pathname,
                    client_token: clientToken,
                });
            } catch (_) {}
        };

        // URL dəyişikliyi izlə
        const checkNavigation = () => {
            if (window.location.pathname !== currentPath) {
                currentPath = window.location.pathname;
                sendHeartbeat();
            }
        };

        // İlk heartbeat
        sendHeartbeat();

        // Hər 2 dəqiqədə heartbeat
        setInterval(sendHeartbeat, 2 * 60 * 1000);

        // Hər 5 saniyədə URL dəyişikliyini yoxla
        setInterval(checkNavigation, 5000);
    },
};

registry.category("services").add("activity_tracker", activityTrackerService);
