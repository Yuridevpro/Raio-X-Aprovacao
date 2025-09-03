// templates/static/admin/js/questao_admin.js

// Garante que o código só rode quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Seleciona o checkbox "É inédita?"
    const ineditaCheckbox = document.querySelector('#id_is_inedita');
    
    // Seleciona as divs que contêm os campos Banca e Ano.
    // O Django admin envolve cada campo em uma div com a classe '.field-<nome_do_campo>'
    const bancaField = document.querySelector('.field-banca');
    const anoField = document.querySelector('.field-ano');

    // Função para mostrar ou esconder os campos
    function toggleCamposOpcionais() {
        if (ineditaCheckbox.checked) {
            // Se for inédita, esconde os campos
            bancaField.style.display = 'none';
            anoField.style.display = 'none';
        } else {
            // Se não for, mostra os campos
            bancaField.style.display = 'block';
            anoField.style.display = 'block';
        }
    }

    // Verifica o estado inicial do checkbox quando a página carrega
    if (ineditaCheckbox && bancaField && anoField) {
        toggleCamposOpcionais();

        // Adiciona um "ouvinte" para o evento de clique no checkbox
        ineditaCheckbox.addEventListener('change', toggleCamposOpcionais);
    }
});