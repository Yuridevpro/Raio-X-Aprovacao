// static/js/filtros-questoes.js

document.addEventListener('DOMContentLoaded', function () {
    const formFiltros = document.getElementById('form-filtros');
    if (!formFiltros) return;

    // // Garante que o dropdown sempre abra para baixo
    // const dropdownToggleButtons = formFiltros.querySelectorAll('.dropdown-toggle');
    // dropdownToggleButtons.forEach(function (toggle) {
    //     new bootstrap.Dropdown(toggle, {
    //         popperConfig: function (defaultConfig) {
    //             return {
    //                 ...defaultConfig,
    //                 strategy: 'fixed',
    //                 modifiers: [
    //                     ...defaultConfig.modifiers,
    //                     { name: 'flip', enabled: false }
    //                 ]
    //             };
    //         }
    //     });
    // });

    // ===================================================================
    // ADIÇÃO 2: Faz o "Enter" funcionar na barra de busca principal
    // ===================================================================
    const palavraChaveInput = formFiltros.querySelector('input[name="palavra_chave"]');
    if (palavraChaveInput) {
        palavraChaveInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                formFiltros.submit();
            }
        });
    }

    // Restante do script de filtros...
    const assuntosUrl = formFiltros.dataset.assuntosUrl;
    const assuntosMarcados = JSON.parse(formFiltros.dataset.selectedAssuntos || '[]');
    const activeFiltersContainer = document.getElementById('active-filters-container');
    const disciplinaCheckboxes = formFiltros.querySelectorAll('input[name="disciplina"]');
    const assuntoOptionsContainer = document.getElementById('options-assunto');
    const assuntoDropdownButton = document.getElementById('dropdownAssunto');

    function loadAssuntos() {
        const selectedDisciplinaIds = Array.from(
            formFiltros.querySelectorAll('input[name="disciplina"]:checked')
        ).map(cb => cb.value);

        assuntoOptionsContainer.innerHTML = '';
        assuntoDropdownButton.disabled = selectedDisciplinaIds.length === 0;

        if (selectedDisciplinaIds.length === 0) {
            updateUIFiltros();
            return;
        }

        const url = `${assuntosUrl}?${new URLSearchParams(selectedDisciplinaIds.map(id => ['disciplina_ids[]', id]))}`;
        
        fetch(url).then(response => response.json()).then(data => {
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
            updateUIFiltros();
        });
    }

    function updateUIFiltros() {
        activeFiltersContainer.innerHTML = '<strong class="me-2">Filtros Ativos:</strong>';
        let hasFilters = false;

        if (palavraChaveInput && palavraChaveInput.value) {
            hasFilters = true;
            const tag = document.createElement('span');
            tag.className = 'badge bg-light text-dark me-2 mb-2 p-2 fw-normal';
            tag.innerHTML = `
                Busca: ${palavraChaveInput.value}
                <button type="button" class="btn-close ms-2" style="font-size: .65em;" aria-label="Close" data-name="palavra_chave" data-value=""></button>
            `;
            activeFiltersContainer.appendChild(tag);
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
                const tag = document.createElement('span');
                tag.className = 'badge bg-light text-dark me-2 mb-2 p-2 fw-normal';
                tag.innerHTML = `
                   ${label}
                    <button type="button" class="btn-close ms-2" style="font-size: .65em;" aria-label="Close" data-name="${name}" data-value="${cb.value}"></button>
                `;
                activeFiltersContainer.appendChild(tag);
            });
        });
        activeFiltersContainer.style.display = hasFilters ? 'block' : 'none';
    }

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
    
    loadAssuntos();
});

// ===================================================================
// ADIÇÃO 1: Função para a "Busca Rápida" dentro dos dropdowns
// ===================================================================
function filterDropdownOptions(input) {
    const filter = input.value.toUpperCase();
    const ul = input.nextElementSibling;
    const items = ul.getElementsByTagName('li');
    for (let i = 0; i < items.length; i++) {
        if (items[i].classList.contains('dropdown-header')) continue;
        
        const label = items[i].querySelector("label");
        if (label) {
            const txtValue = label.textContent || label.innerText;
            items[i].style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? "" : "none";
        }
    }
}