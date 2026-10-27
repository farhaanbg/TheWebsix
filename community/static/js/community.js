document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-comment-toggle]').forEach(function (button) {
        button.addEventListener('click', function () {
            var panel = document.getElementById(button.getAttribute('aria-controls'));
            if (!panel) {
                return;
            }

            var isOpen = !panel.hidden;
            panel.hidden = isOpen;
            button.setAttribute('aria-expanded', String(!isOpen));
            if (!isOpen) {
                panel.querySelector('textarea').focus();
            }
        });
    });
});
