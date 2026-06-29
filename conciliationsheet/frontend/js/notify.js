function notify(message, type) {
    type = type || 'info';
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;

    const icons = { success: '✓', error: '✘', warning: '⚠', info: 'ℹ' };
    toast.innerHTML = '<span class="toast-icon">' + (icons[type] || '') + '</span>' +
        '<span class="toast-msg">' + message + '</span>';

    container.appendChild(toast);

    setTimeout(function () {
        toast.classList.add('toast-fade');
        setTimeout(function () { toast.remove(); }, 300);
    }, 4000);
}
