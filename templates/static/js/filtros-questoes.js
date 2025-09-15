document.addEventListener('DOMContentLoaded', function () {
    /*
    ✅ ADIÇÃO: FORÇAR DROPDOWNS A ABRIREM SEMPRE PARA BAIXO
    
    Este bloco de código desativa o comportamento "flip" do Bootstrap, que
    faz com que os menus abram para cima. Ele faz isso configurando o Popper.js
    para não ter "planos B" de posicionamento, garantindo que eles sempre
    se expandam para baixo.
    */
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    dropdownToggles.forEach(function (toggle) {
        new bootstrap.Dropdown(toggle, {
            popperConfig: {
                modifiers: [
                    {
                        name: 'flip',
                        options: {
                            fallbackPlacements: [], // Array vazio desativa o "flip"
                        },
                    },
                ],
            },
        });
    });

    // O restante do seu código permanece inalterado abaixo...
    const formFiltros = document.getElementById('form-filtros');
    if (!formFiltros) return;

    const palavraChaveInput = formFiltros.querySelector('input[name="palavra_chave"]');
    if (palavraChaveInput) {
        palavraChaveInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                formFiltros.submit();
            }
        });
    }

    const assuntosUrl = formFiltros.dataset.assuntosUrl;
    const activeFiltersContainer = document.getElementById('active-filters-container');
    const disciplinaCheckboxes = formFiltros.querySelectorAll('input[name="disciplina"]');
    const assuntoOptionsContainer = document.getElementById('options-assunto');
    const assuntoDropdownButton = document.getElementById('dropdownAssunto');

    function loadAssuntos() {
        let assuntosSelecionados;
        const isInitialLoad = (assuntoOptionsContainer.innerHTML.trim() === '');

        if (isInitialLoad) {
            const serverSelectedAssuntos = JSON.parse(formFiltros.dataset.selectedAssuntos || '[]');
            assuntosSelecionados = new Set(serverSelectedAssuntos.map(String));
        } else {
            assuntosSelecionados = new Set(
                Array.from(formFiltros.querySelectorAll('input[name="assunto"]:checked'))
                     .map(cb => cb.value)
            );
        }

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
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                const assuntosAgrupados = data.assuntos.reduce((acc, assunto) => {
                    const disciplinaNome = assunto.disciplina_nome;
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
                updateUIFiltros();
            });
    }

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

    function createFilterTag(label, name, value) {
        const tag = document.createElement('span');
        tag.className = 'badge bg-light text-dark me-2 mb-2 p-2 fw-normal';
        tag.innerHTML = `
            ${label}
            <button type="button" class="btn-close ms-2" style="font-size: .65em;" aria-label="Close" data-name="${name}" data-value="${value}"></button>
        `;
        activeFiltersContainer.appendChild(tag);
    }

    disciplinaCheckboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            updateUIFiltros();
            loadAssuntos();
        });
    });
    
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
                        updateUIFiltros();
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
    
    loadAssuntos();
});

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