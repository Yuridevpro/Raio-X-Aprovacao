document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('#recompensa-form');
    if (!form) return;

    const tipoItem = form.dataset.tipoItem;

    function setupToggleFields() {
        const tipoDesbloqueioSelect = document.getElementById('id_tipo_desbloqueio');
        const requisitoNivelDiv = document.getElementById('requisito-nivel');
        const requisitoConquistaDiv = document.getElementById('requisito-conquista');
        if (!tipoDesbloqueioSelect || !requisitoNivelDiv || !requisitoConquistaDiv) return;
        function toggle() {
            const selected = tipoDesbloqueioSelect.value;
            requisitoNivelDiv.style.display = selected === 'NIVEL' ? 'block' : 'none';
            requisitoConquistaDiv.style.display = selected === 'CONQUISTA' ? 'block' : 'none';
        }
        tipoDesbloqueioSelect.addEventListener('change', toggle);
        toggle();
    }

    function setupBannerPreview() {
        const imagemInput = document.getElementById('id_imagem');
        const bannerPreview = document.getElementById('banner-preview-header');
        const previewText = document.getElementById('preview-text');
        const positionInput = document.getElementById('id_background_position');
        const sizeInput = document.getElementById('id_background_size');
        
        // ADIÇÃO 1: Selecionar o botão que vai disparar a seleção de arquivo.
        const fileTriggerBtn = document.getElementById('file-trigger-btn');

        if (!imagemInput || !bannerPreview) return;

        // ADIÇÃO 2: Adicionar um evento de clique ao botão customizado.
        // Quando clicado, ele aciona o clique no input de arquivo real, que está oculto.
        if (fileTriggerBtn) {
            fileTriggerBtn.addEventListener('click', function() {
                imagemInput.click();
            });
        }

        // Atualiza preview ao selecionar a imagem
        imagemInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    bannerPreview.style.backgroundImage = `url('${e.target.result}')`;
                    
                    // ADIÇÃO 3: Garantir que a área de preview fique visível ao selecionar uma nova imagem.
                    bannerPreview.style.display = 'flex'; 
                    
                    if (previewText) previewText.style.display = 'none';
                };
                reader.readAsDataURL(file);
            }
        });

        // Permite arrastar a imagem para definir o ponto focal
        let isDragging = false;
        let startX = 0, startY = 0;
        
        // Inicializa a posição com o valor do input, se existir, senão usa 50% 50%
        let currentPosStr = positionInput.value || '50% 50%';
        let currentPosArr = currentPosStr.replace(/%/g, '').split(' ').map(parseFloat);
        let startPos = { x: currentPosArr[0] || 50, y: currentPosArr[1] || 50 };

        bannerPreview.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            bannerPreview.style.cursor = 'grabbing'; // Melhora a UX
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            e.preventDefault(); // Previne seleção de texto indesejada
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            startX = e.clientX;
            startY = e.clientY;

            // Atualiza posição percentual
            const rect = bannerPreview.getBoundingClientRect();
            startPos.x += (dx / rect.width) * 100;
            startPos.y += (dy / rect.height) * 100;
            startPos.x = Math.max(0, Math.min(100, startPos.x));
            startPos.y = Math.max(0, Math.min(100, startPos.y));

            const newPosition = `${startPos.x.toFixed(2)}% ${startPos.y.toFixed(2)}%`;
            bannerPreview.style.backgroundPosition = newPosition;
            if (positionInput) positionInput.value = newPosition;
        });

        document.addEventListener('mouseup', () => {
            if(isDragging) {
                isDragging = false;
                bannerPreview.style.cursor = 'grab'; // Restaura o cursor
            }
        });

        // Zoom simples via roda do mouse
        bannerPreview.addEventListener('wheel', (e) => {
            e.preventDefault();
            let sizeStr = sizeInput.value || '100%';
            let size = parseFloat(sizeStr.replace('%',''));

            // Normaliza o delta para funcionar de forma mais consistente entre navegadores
            const delta = Math.sign(e.deltaY);

            size -= delta * 5; // Aumenta ou diminui em passos de 5%
            size = Math.max(100, Math.min(300, size)); // Limita o zoom entre 100% e 300%

            const newSize = `${size.toFixed(2)}%`;
            bannerPreview.style.backgroundSize = newSize;
            if (sizeInput) sizeInput.value = newSize;
        });
        
        // ADIÇÃO 4: Define o cursor inicial para indicar que a área é interativa
        if (bannerPreview.style.backgroundImage) {
             bannerPreview.style.cursor = 'grab';
        }
    }

    // --- Roteador Principal ---
    setupToggleFields();
    if (tipoItem === 'banners') {
        setupBannerPreview();
    }
});