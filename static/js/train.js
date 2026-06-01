// Training page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const startTrainingBtn = document.getElementById('startTraining');
    const trainingStatus = document.getElementById('trainingStatus');
    const trainingResult = document.getElementById('trainingResult');
    const statusText = document.getElementById('statusText');

    startTrainingBtn.addEventListener('click', async function() {
        // Disable button
        startTrainingBtn.disabled = true;
        startTrainingBtn.textContent = 'Training...';

        // Show status
        trainingStatus.style.display = 'block';
        trainingResult.style.display = 'none';
        statusText.textContent = 'Memproses training model... Mohon tunggu.';

        try {
            const response = await fetch('/api/train', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            // Hide status
            trainingStatus.style.display = 'none';

            // Show result
            trainingResult.style.display = 'block';

            if (result.success) {
                trainingResult.className = 'result-box success';
                trainingResult.innerHTML = `
                    <h3>✅ Training Berhasil!</h3>
                    <p>${result.message}</p>
                    <p>Model siap digunakan untuk absensi.</p>
                    <a href="/attendance" class="btn btn-primary">Mulai Absensi</a>
                `;
            } else {
                trainingResult.className = 'result-box error';
                trainingResult.innerHTML = `
                    <h3>❌ Training Gagal</h3>
                    <p>${result.message}</p>
                    <button onclick="location.reload()" class="btn btn-secondary">Coba Lagi</button>
                `;
            }

            // Re-enable button
            startTrainingBtn.disabled = false;
            startTrainingBtn.textContent = '🚀 Mulai Training';

        } catch (error) {
            trainingStatus.style.display = 'none';
            trainingResult.style.display = 'block';
            trainingResult.className = 'result-box error';
            trainingResult.innerHTML = `
                <h3>❌ Error</h3>
                <p>Terjadi kesalahan: ${error.message}</p>
                <button onclick="location.reload()" class="btn btn-secondary">Coba Lagi</button>
            `;

            startTrainingBtn.disabled = false;
            startTrainingBtn.textContent = '🚀 Mulai Training';
        }
    });
});
