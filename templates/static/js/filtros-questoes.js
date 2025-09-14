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
    const activeFiltersContainer = document.getElementById('active-filters-container');
    const disciplinaCheckboxes = formFiltros.querySelectorAll('input[name="disciplina"]');
    const assuntoOptionsContainer = document.getElementById('options-assunto');
    const assuntoDropdownButton = document.getElementById('dropdownAssunto');

    /**
     * Carrega os assuntos via AJAX com base nas disciplinas selecionadas.
     */
    function loadAssuntos() {
        // 1. DETERMINAR A FONTE DA VERDADE PARA OS ASSUNTOS SELECIONADOS.
        let assuntosSelecionados;
        
        // Verificamos se a lista de assuntos no DOM ainda não foi construída.
        const isInitialLoad = (assuntoOptionsContainer.innerHTML.trim() === '');

        if (isInitialLoad) {
            // Se for a CARGA INICIAL da página, a fonte da verdade é o atributo data-*
            // que o Django renderizou no HTML.
            const serverSelectedAssuntos = JSON.parse(formFiltros.dataset.selectedAssuntos || '[]');
            // Convertemos os IDs para string para garantir a consistência na comparação dentro do Set.
            assuntosSelecionados = new Set(serverSelectedAssuntos.map(String));
        } else {
            // Se a lista já existe, é uma INTERAÇÃO DO USUÁRIO. A fonte da verdade
            // são os checkboxes que o usuário marcou na página.
            assuntosSelecionados = new Set(
                Array.from(formFiltros.querySelectorAll('input[name="assunto"]:checked'))
                     .map(cb => cb.value)
            );
        }

        // Pega os IDs de todas as disciplinas que estão marcadas.
        const selectedDisciplinaIds = Array.from(
            formFiltros.querySelectorAll('input[name="disciplina"]:checked')
        ).map(cb => cb.value);

        assuntoOptionsContainer.innerHTML = ''; // Limpa a lista de assuntos atual.
        assuntoDropdownButton.disabled = selectedDisciplinaIds.length === 0;

        if (selectedDisciplinaIds.length === 0) {
            updateUIFiltros();
            return;
        }

        const url = `${assuntosUrl}?${new URLSearchParams(selectedDisciplinaIds.map(id => ['disciplina_ids[]', id]))}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                const assuntosAgrupados = data.assuntos.reduce((acc, assunto) => {
                    const disciplinaNome = assunto.disciplina__nome;
                    if (!acc[disciplinaNome]) acc[disciplinaNome] = [];
                    acc[disciplinaNome].push(assunto);
                    return acc;
                }, {});

                for (const disciplinaNome in assuntosAgrupados) {
                    const grupoHeader = document.createElement('li');
                    grupoHeader.className = 'dropdown-header';
                    grupoHeader.textContent = disciplinaNome;
                    assuntoOptionsContainer.appendChild(grupoHeader);

                    assuntosAgrupados[disciplinaNome].forEach(assunto => {
                        // 2. RESTAURAR ESTADO: Usamos nossa variável 'assuntosSelecionados' que agora
                        // contém os dados corretos, seja da carga inicial ou da interação.
                        const isChecked = assuntosSelecionados.has(assunto.id.toString());

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

        if (palavraChaveInput && palavraChaveInput.value) {
            hasFilters = true;
            createFilterTag('Busca: ' + palavraChaveInput.value, 'palavra_chave', '');
        }

        ['disciplina', 'assunto', 'banca', 'instituicao', 'ano'].forEach(name => {
            const checkboxes = formFiltros.querySelectorAll(`input[name="${name}"]:checked`);
            const countSpan = document.getElementById(`count-${name}`);
            
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

        activeFiltersContainer.style.display = hasFilters ? 'block' : 'none';
    }

    /**
     * Helper para criar uma tag de filtro individual.
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

    disciplinaCheckboxes.forEach(cb => cb.addEventListener('change', loadAssuntos));
    
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
                    if (name === 'disciplina') {
                        loadAssuntos();
                    }
                }
            }
            formFiltros.submit();
        }
    });

    formFiltros.addEventListener('change', (e) => {
        if (e.target.name !== 'disciplina') {
            updateUIFiltros();
        }
    });
    
    // Carga inicial dos assuntos e da UI de filtros.
    loadAssuntos();
});

/**
 * Filtra as opções de um dropdown com base no texto digitado no campo de busca.
 */
function filterDropdownOptions(input) {
    const filter = input.value.toUpperCase();
    const container = input.nextElementSibling;
    const items = container.getElementsByTagName('li');

    for (let i = 0; i < items.length; i++) {
        if (items[i].classList.contains('dropdown-header')) continue;
        
        const label = items[i].querySelector("label");
        if (label) {
            const txtValue = label.textContent || label.innerText;
            items[i].style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? "" : "none";
        }
    }
}