function updateElapsedTimes() {
    const now = Math.floor(Date.now() / 1000);
    let highlighted = false;
    document.querySelectorAll('#kartTable tbody tr').forEach(tr => {
        const td = tr.querySelector('td[data-timestamp]');
        if (!td) return;
        const timestamp = parseInt(td.getAttribute('data-timestamp'));
        const elapsed = now - timestamp;
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        td.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

        tr.classList.remove('highlight');
        if (!highlighted && elapsed >= 180) {
            highlighted = true;
            tr.classList.add('highlight');
        }
        const prev = parseInt(td.getAttribute('data-prev-elapsed') || '0');
        if (prev < 180 && elapsed >= 180) {
            tr.classList.add('blink');
            setTimeout(() => tr.classList.remove('blink'), 1000);
        }
        td.setAttribute('data-prev-elapsed', elapsed);
    });
}

function updateClock() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    document.getElementById('clock').textContent = `${hours}:${minutes}:${seconds}`;
}

setInterval(updateElapsedTimes, 1000);
setInterval(updateClock, 1000);
updateClock();
