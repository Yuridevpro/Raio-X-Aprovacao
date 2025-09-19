// gestao/static/js/recompensa-form-preview.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('#recompensa-form');
    if (!form) return;

    const tipoItem = form.dataset.tipoItem;
    const imagemInput = document.getElementById('id_imagem');

    // --- LÓGICA 1: Mostrar/Ocultar campos de requisito ---
    function setupToggleFields() {
        const tipoDesbloqueioSelect = document.getElementById('id_tipo_desbloqueio');
        const requisitoNivelDiv = document.getElementById('requisito-nivel');
        const requisitoConquistaDiv = document.getElementById('requisito-conquista');

        if (!tipoDesbloqueioSelect || !requisitoNivelDiv || !requisitoConquistaDiv) return;

        function toggle() {
            const selectedValue = tipoDesbloqueioSelect.value;
            requisitoNivelDiv.style.display = selectedValue === 'NIVEL' ? 'block' : 'none';
            requisitoConquistaDiv.style.display = selectedValue === 'CONQUISTA' ? 'block' : 'none';
        }
        tipoDesbloqueioSelect.addEventListener('change', toggle);
        toggle();
    }

    // --- LÓGICA 2: Pré-visualização Simples para Avatar/Borda ---
    function setupSimplePreview() {
        const previewImage = document.getElementById('avatar-preview-image') || document.getElementById('border-preview-image');
        const previewText = document.getElementById('preview-text');

        if (!imagemInput || !previewImage) return;

        imagemInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                    previewImage.style.display = 'block';
                    if (previewText) previewText.style.display = 'none';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // --- ROTEADOR PRINCIPAL ---
    setupToggleFields();

    // Executa a lógica de preview apenas se for avatar ou borda
    if (tipoItem === 'avatares' || tipoItem === 'bordas') {
        setupSimplePreview();
    }
});