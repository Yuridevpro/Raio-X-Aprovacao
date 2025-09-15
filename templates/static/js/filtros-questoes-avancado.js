/**
 * filtros-questoes-avancado.js
 * Script definitivo para gerenciar filtros com dependências dinâmicas.
 */

/*
  ========================================================================
  ✅ CORREÇÃO DEFINITIVA: FORÇAR DROPDOWNS A ABRIREM SEMPRE PARA BAIXO
  ========================================================================
  Este bloco de código desativa o comportamento "flip" do Bootstrap, que
  faz com que os menus abram para cima. Ele faz isso configurando o Popper.js
  para não ter "planos B" de posicionamento.
*/
document.addEventListener('DOMContentLoaded', function () {
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

    /* O restante do seu código original continua abaixo... */
    document.querySelectorAll('[data-assuntos-url]').forEach(formFiltros => {

        // --- CONFIGURAÇÃO INICIAL ---
        const prefix = formFiltros.dataset.prefix || '';
        const assuntosUrl = formFiltros.dataset.assuntosUrl;
        
        const assuntoOptionsContainer = formFiltros.querySelector(`#options-${prefix}assunto`);
        const assuntoDropdownButton = formFiltros.querySelector(`#dropdown${prefix}Assunto`);
        
        const activeFiltersContainer = formFiltros.querySelector(`#active-filters-container-${prefix}`) || formFiltros.querySelector(`#active-filters-container`);
        
        let isInitialLoad = true;

        async function loadAssuntos() {
            if (!assuntoOptionsContainer) return;

            let assuntosSelecionados;
            if (isInitialLoad) {
                const serverSelectedAssuntos = JSON.parse(formFiltros.dataset.selectedAssuntos || '[]');
                assuntosSelecionados = new Set(serverSelectedAssuntos.map(String));
                isInitialLoad = false;
            } else {
                assuntosSelecionados = new Set(
                    Array.from(formFiltros.querySelectorAll(`input[name="${prefix}assunto"]:checked`)).map(cb => cb.value)
                );
            }

            const selectedDisciplinaIds = Array.from(formFiltros.querySelectorAll(`input[name="${prefix}disciplina"]:checked`)).map(cb => cb.value);
            
            assuntoOptionsContainer.innerHTML = ''; 
            if (assuntoDropdownButton) {
                assuntoDropdownButton.disabled = selectedDisciplinaIds.length === 0;
            }

            if (selectedDisciplinaIds.length === 0) {
                assuntoOptionsContainer.innerHTML = `<li class="p-3 text-center text-muted"><small>Selecione uma disciplina.</small></li>`;
                updateUI();
                return;
            }

            const url = `${assuntosUrl}?${new URLSearchParams(selectedDisciplinaIds.map(id => ['disciplina_ids[]', id]))}`;
            
            try {
                const response = await fetch(url);
                if (!response.ok) throw new Error('Falha na resposta da rede');
                const data = await response.json();

                const searchInputLi = document.createElement('li');
                searchInputLi.className = 'search-input-container';
                searchInputLi.innerHTML = `<input type="text" class="form-control form-control-sm" placeholder="Busca rápida..." onkeyup="filterDropdownOptions(this)">`;
                assuntoOptionsContainer.appendChild(searchInputLi);

                const assuntosAgrupados = (data.assuntos || []).reduce((acc, assunto) => {
                    const disciplinaNome = assunto.disciplina_nome;
                    if (disciplinaNome) {
                        (acc[disciplinaNome] = acc[disciplinaNome] || []).push(assunto);
                    }
                    return acc;
                }, {});
                
                delete assuntosAgrupados.undefined;

                for (const disciplinaNome in assuntosAgrupados) {
                    const header = document.createElement('li');
                    header.className = 'dropdown-header';
                    header.textContent = disciplinaNome;
                    assuntoOptionsContainer.appendChild(header);

                    assuntosAgrupados[disciplinaNome].forEach(assunto => {
                        const isChecked = assuntosSelecionados.has(assunto.id.toString());
                        const li = document.createElement('li');
                        li.innerHTML = `
                            <div class="form-check dropdown-item-text">
                                <input class="form-check-input" type="checkbox" name="${prefix}assunto" value="${assunto.id}" id="${prefix}assunto-${assunto.id}" ${isChecked ? 'checked' : ''}>
                                <label class="form-check-label" for="${prefix}assunto-${assunto.id}">${assunto.nome}</label>
                            </div>`;
                        assuntoOptionsContainer.appendChild(li);
                    });
                }
            } catch (error) {
                console.error("Erro ao carregar assuntos:", error);
                assuntoOptionsContainer.innerHTML = `<li class="p-3 text-center text-danger"><small>Erro ao carregar.</small></li>`;
            } finally {
                updateUI();
            }
        }

        function updateUI() {
            ['disciplina', 'assunto', 'banca', 'instituicao', 'ano'].forEach(name => {
                const checkboxes = formFiltros.querySelectorAll(`input[name="${prefix}${name}"]:checked`);
                const countSpan = formFiltros.querySelector(`#count-${prefix}${name}`);
                const dropdownButton = formFiltros.querySelector(`#dropdown${prefix}${name.charAt(0).toUpperCase() + name.slice(1)}`);

                if (countSpan && dropdownButton) {
                    const hasSelection = checkboxes.length > 0;
                    countSpan.style.display = hasSelection ? '' : 'none';
                    if (hasSelection) countSpan.textContent = checkboxes.length;
                    dropdownButton.classList.toggle('active', hasSelection);
                }
            });
            
            updateActiveFiltersDisplay();
        }

        function updateActiveFiltersDisplay() {
            if (!activeFiltersContainer) return;

            activeFiltersContainer.innerHTML = '';
            let hasActiveFilters = false;

            const checkedCheckboxes = formFiltros.querySelectorAll('input[type="checkbox"]:checked');
            
            checkedCheckboxes.forEach(checkbox => {
                const label = formFiltros.querySelector(`label[for="${checkbox.id}"]`);
                if (label) {
                    hasActiveFilters = true;
                    const pill = document.createElement('div');
                    pill.className = 'filter-pill';
                    pill.innerHTML = `
                        <span>${label.textContent}</span>
                        <button type="button" class="remove-filter-btn" 
                                data-name="${checkbox.name}" 
                                data-value="${checkbox.value}" 
                                aria-label="Remover filtro">&times;</button>
                    `;
                    activeFiltersContainer.appendChild(pill);
                }
            });

            activeFiltersContainer.style.display = hasActiveFilters ? 'flex' : 'none';
            activeFiltersContainer.style.flexWrap = 'wrap';
            activeFiltersContainer.style.gap = '0.5rem';
        }

        formFiltros.addEventListener('change', (e) => {
            if (e.target.matches('input[type="checkbox"]')) {
                if (e.target.name === `${prefix}disciplina`) {
                    loadAssuntos();
                } else {
                    updateUI();
                }
            }
        });

        if (activeFiltersContainer) {
            activeFiltersContainer.addEventListener('click', function(e) {
                if (e.target.classList.contains('remove-filter-btn')) {
                    const name = e.target.dataset.name;
                    const value = e.target.dataset.value;
                    const checkboxToUncheck = formFiltros.querySelector(`input[name="${name}"][value="${value}"]`);
                    
                    if (checkboxToUncheck) {
                        checkboxToUncheck.checked = false;
                        checkboxToUncheck.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            });
        }
        
        loadAssuntos();
    });
});

function filterDropdownOptions(input) {
    const filter = input.value.toUpperCase();
    const ul = input.closest('ul.dropdown-menu');
    if (!ul) return;
    
    const items = ul.querySelectorAll('li:not(.search-input-container):not(.dropdown-header)');
    items.forEach(item => {
        const label = item.querySelector("label");
        if (label) {
            const txtValue = label.textContent || label.innerText;
            item.style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? "" : "none";
        }
    });
}