(function () {
    var DELAY_MS = 10000;                 // через скільки показати (10 сек)
    var HIDE_DAYS = 7;                    // скільки днів не питати після "Не зараз"
    var KEY = 'pushPromptDismissedAt';

    // Браузер не підтримує сповіщення, не показуємо
    if (!('Notification' in window)) return;

    // Уже дозволив або заблокував, не показуємо
    if (Notification.permission !== 'default') return;

    // Нещодавно закрив плашку, не показуємо
    try {
        var t = parseInt(localStorage.getItem(KEY), 10);
        if (t && Date.now() - t < HIDE_DAYS * 24 * 60 * 60 * 1000) return;
    } catch (e) {}

    function buildBar() {
        var bar = document.createElement('div');
        bar.className = 'push-bar';
        bar.innerHTML =
            '<div class="push-bar-icon">🔔</div>' +
            '<div class="push-bar-text">' +
                '<strong>Хочете знати про акції першими?</strong>' +
                'Надсилатимемо лише найцікавіше.' +
            '</div>' +
            '<div class="push-bar-actions">' +
                '<button class="push-btn-yes" type="button">Так, хочу</button>' +
                '<button class="push-btn-no" type="button">Не зараз</button>' +
            '</div>';
        document.body.appendChild(bar);

        // невеличка затримка, щоб спрацювала анімація
        setTimeout(function () { bar.classList.add('show'); }, 50);

        function close() {
            bar.classList.remove('show');
            setTimeout(function () { bar.remove(); }, 500);
        }

        bar.querySelector('.push-btn-yes').addEventListener('click', function () {
            close();
            window.OneSignalDeferred = window.OneSignalDeferred || [];
            OneSignalDeferred.push(function (OneSignal) {
                OneSignal.Notifications.requestPermission();
            });
        });

        bar.querySelector('.push-btn-no').addEventListener('click', function () {
            try { localStorage.setItem(KEY, String(Date.now())); } catch (e) {}
            close();
        });
    }

    setTimeout(function () {
        // Ще раз перевіряємо: можливо, за 10 секунд людина вже підписалась
        if (Notification.permission !== 'default') return;
        buildBar();
    }, DELAY_MS);
})();