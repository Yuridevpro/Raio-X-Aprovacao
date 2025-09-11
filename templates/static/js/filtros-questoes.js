// static/js/filtros-questoes.js

document.addEventListener('DOMContentLoaded', function () {
    const formFiltros = document.getElementById('form-filtros');
    if (!formFiltros) return; // Se o formulário de filtros não existe na página, interrompe o script.

    // ===================================================================
    // INICIALIZAÇÃO DE COMPORTAMENTOS DO FORMULÁRIO
    // ===================================================================
    
    // Permite que o usuário submeta o formulário pressionando "Enter" no campo de busca principal.
    const palavraChaveInput = formFiltros.querySelector('input[name="palavra_chave"]');
    if (palavraChaveInput) {
        palavraChaveInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault(); // Previne o comportamento padrão do Enter em formulários.
                formFiltros.submit(); // Submete o formulário.
            }
        });
    }

    // ===================================================================
    // GERENCIAMENTO DINÂMICO DOS ASSUNTOS
    // ===================================================================
    const assuntosUrl = formFiltros.dataset.assuntosUrl;
    const assuntosMarcados = JSON.parse(formFiltros.dataset.selectedAssuntos || '[]');
    const activeFiltersContainer = document.getElementById('active-filters-container');
    const disciplinaCheckboxes = formFiltros.querySelectorAll('input[name="disciplina"]');
    const assuntoOptionsContainer = document.getElementById('options-assunto');
    const assuntoDropdownButton = document.getElementById('dropdownAssunto');

    /**
     * Carrega os assuntos via AJAX com base nas disciplinas selecionadas.
     */
    function loadAssuntos() {
        // Pega os IDs de todas as disciplinas que estão marcadas.
        const selectedDisciplinaIds = Array.from(
            formFiltros.querySelectorAll('input[name="disciplina"]:checked')
        ).map(cb => cb.value);

        assuntoOptionsContainer.innerHTML = ''; // Limpa a lista de assuntos atual.
        assuntoDropdownButton.disabled = selectedDisciplinaIds.length === 0; // Desabilita o dropdown se nenhuma disciplina for selecionada.

        if (selectedDisciplinaIds.length === 0) {
            updateUIFiltros(); // Atualiza a UI para remover tags de assuntos, se houver.
            return;
        }

        // Constrói a URL para a requisição AJAX.
        const url = `${assuntosUrl}?${new URLSearchParams(selectedDisciplinaIds.map(id => ['disciplina_ids[]', id]))}`;
        
        // Faz a chamada fetch para buscar os assuntos.
        fetch(url)
            .then(response => response.json())
            .then(data => {
                // Agrupa os assuntos retornados pelo nome da disciplina.
                const assuntosAgrupados = data.assuntos.reduce((acc, assunto) => {
                    const disciplinaNome = assunto.disciplina__nome;
                    if (!acc[disciplinaNome]) acc[disciplinaNome] = [];
                    acc[disciplinaNome].push(assunto);
                    return acc;
                }, {});

                // Constrói o HTML para cada grupo de assuntos.
                for (const disciplinaNome in assuntosAgrupados) {
                    const grupoHeader = document.createElement('li');
                    grupoHeader.className = 'dropdown-header';
                    grupoHeader.textContent = disciplinaNome;
                    assuntoOptionsContainer.appendChild(grupoHeader);

                    assuntosAgrupados[disciplinaNome].forEach(assunto => {
                        const isChecked = assuntosMarcados.includes(assunto.id);
                        const li = document.createElement('li');
                        li.innerHTML = `
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="assunto" value="${assunto.id}" id="assunto-${assunto.id}" ${isChecked ? 'checked' : ''}>
                                <label class="form-check-label" for="assunto-${assunto.id}">${assunto.nome}</label>
                            </div>`;
                        assuntoOptionsContainer.appendChild(li);
                    });
                }
                updateUIFiltros(); // Atualiza a UI após carregar os assuntos.
            });
    }

    /**
     * Atualiza a seção "Filtros Ativos" com tags para cada filtro selecionado.
     */
    function updateUIFiltros() {
        activeFiltersContainer.innerHTML = '<strong class="me-2">Filtros Ativos:</strong>';
        let hasFilters = false;

        // Adiciona a tag para a palavra-chave, se houver.
        if (palavraChaveInput && palavraChaveInput.value) {
            hasFilters = true;
            createFilterTag('Busca: ' + palavraChaveInput.value, 'palavra_chave', '');
        }

        // Itera sobre os tipos de filtro e cria tags para os selecionados.
        ['disciplina', 'assunto', 'banca', 'instituicao', 'ano'].forEach(name => {
            const checkboxes = formFiltros.querySelectorAll(`input[name="${name}"]:checked`);
            const countSpan = document.getElementById(`count-${name}`);
            
            // Atualiza o contador de filtros no botão do dropdown.
            if (countSpan) {
                countSpan.textContent = checkboxes.length;
                countSpan.style.display = checkboxes.length > 0 ? 'inline-block' : 'none';
            }

            checkboxes.forEach(cb => {
                hasFilters = true;
                const label = cb.closest('.form-check').querySelector('label').textContent;
                createFilterTag(label, name, cb.value);
            });
        });

        // Mostra ou esconde a seção de filtros ativos.
        activeFiltersContainer.style.display = hasFilters ? 'block' : 'none';
    }

    /**
     * Helper para criar uma tag de filtro individual.
     * @param {string} label - O texto da tag.
     * @param {string} name - O nome do campo do filtro (ex: 'disciplina').
     * @param {string} value - O valor do filtro.
     */
    function createFilterTag(label, name, value) {
        const tag = document.createElement('span');
        tag.className = 'badge bg-light text-dark me-2 mb-2 p-2 fw-normal';
        tag.innerHTML = `
            ${label}
            <button type="button" class="btn-close ms-2" style="font-size: .65em;" aria-label="Close" data-name="${name}" data-value="${value}"></button>
        `;
        activeFiltersContainer.appendChild(tag);
    }

    // ===================================================================
    // LISTENERS DE EVENTOS
    // ===================================================================

    // Recarrega os assuntos sempre que uma disciplina é (des)marcada.
    disciplinaCheckboxes.forEach(cb => cb.addEventListener('change', loadAssuntos));
    
    // Listener para remover um filtro ao clicar no 'x' da tag.
    activeFiltersContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('btn-close')) {
            const name = e.target.dataset.name;
            const value = e.target.dataset.value;

            if (name === 'palavra_chave') {
                if (palavraChaveInput) palavraChaveInput.value = '';
            } else {
                const checkboxToUncheck = formFiltros.querySelector(`input[name="${name}"][value="${value}"]`);
                if (checkboxToUncheck) {
                    checkboxToUncheck.checked = false;
                }
            }
            formFiltros.submit(); // Submete o formulário para aplicar a remoção do filtro.
        }
    });

    // Atualiza a UI sempre que um filtro (exceto disciplina) é alterado.
    formFiltros.addEventListener('change', (e) => {
        if (e.target.name !== 'disciplina') {
            updateUIFiltros();
        }
    });
    
    // Carga inicial dos assuntos e da UI de filtros.
    loadAssuntos();
});

// ===================================================================
// FUNÇÃO GLOBAL PARA BUSCA RÁPIDA NOS DROPDOWNS
// ===================================================================
/**
 * Filtra as opções de um dropdown com base no texto digitado no campo de busca.
 * @param {HTMLInputElement} input - O campo de input onde o usuário digita a busca.
 */
function filterDropdownOptions(input) {
    const filter = input.value.toUpperCase();
    const ul = input.nextElementSibling; // A lista <ul> é o próximo irmão do input.
    const items = ul.getElementsByTagName('li');

    for (let i = 0; i < items.length; i++) {
        // Ignora os cabeçalhos de grupo (ex: nome da disciplina).
        if (items[i].classList.contains('dropdown-header')) continue;
        
        const label = items[i].querySelector("label");
        if (label) {
            const txtValue = label.textContent || label.innerText;
            // Mostra ou esconde o item da lista com base na correspondência.
            items[i].style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? "" : "none";
        }
    }
}