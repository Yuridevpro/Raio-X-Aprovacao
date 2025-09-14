/**
 * filtros-questoes-avancado.js
 * Script definitivo para gerenciar filtros com dependências dinâmicas.
 * Combina a persistência de estado pós-filtro com a manutenção do estado durante a interação.
 */
document.addEventListener('DOMContentLoaded', function () {
    const formFiltros = document.getElementById('form-filtros');
    if (!formFiltros) return;

    // --- CONFIGURAÇÃO INICIAL ---
    const prefix = formFiltros.dataset.prefix || '';
    const assuntosUrl = formFiltros.dataset.assuntosUrl;
    
    const assuntoOptionsContainer = document.getElementById(`options-${prefix}assunto`);
    const assuntoDropdownButton = document.getElementById(`dropdown${prefix}Assunto`);
    
    // ✅ CORREÇÃO: Flag para controlar a carga inicial
    let isInitialLoad = true;

    /**
     * ===================================================================
     * FUNÇÃO PRINCIPAL: Carrega e popula os assuntos dinamicamente
     * ===================================================================
     */
    async function loadAssuntos() {
        if (!assuntoOptionsContainer) return;

        // ✅ INÍCIO DA CORREÇÃO: LÓGICA HÍBRIDA PARA A "FONTE DA VERDADE"
        let assuntosSelecionados;

        if (isInitialLoad) {
            // Na carga inicial da página, a fonte da verdade é o backend (data-attribute).
            const serverSelectedAssuntos = JSON.parse(formFiltros.dataset.selectedAssuntos || '[]');
            assuntosSelecionados = new Set(serverSelectedAssuntos.map(String));
            isInitialLoad = false; // Desativa a flag após a primeira execução.
        } else {
            // Durante a interação do usuário, a fonte da verdade são os checkboxes
            // que o próprio usuário já marcou na tela, mesmo que não estejam visíveis.
            assuntosSelecionados = new Set(
                Array.from(formFiltros.querySelectorAll(`input[name="${prefix}assunto"]:checked`)).map(cb => cb.value)
            );
        }
        // ✅ FIM DA CORREÇÃO

        const selectedDisciplinaIds = Array.from(formFiltros.querySelectorAll(`input[name="${prefix}disciplina"]:checked`)).map(cb => cb.value);
        
        assuntoOptionsContainer.innerHTML = ''; 
        if (assuntoDropdownButton) {
            assuntoDropdownButton.disabled = selectedDisciplinaIds.length === 0;
        }

        if (selectedDisciplinaIds.length === 0) {
            updateUI();
            return;
        }

        const url = `${assuntosUrl}?${new URLSearchParams(selectedDisciplinaIds.map(id => ['disciplina_ids[]', id]))}`;
        
        try {
            const response = await fetch(url);
            const data = await response.json();

            const searchInputLi = document.createElement('li');
            searchInputLi.className = 'px-2 py-1 sticky-top bg-light';
            searchInputLi.innerHTML = `<input type="text" class="form-control form-control-sm" placeholder="Busca rápida..." onkeyup="filterDropdownOptions(this)">`;
            assuntoOptionsContainer.appendChild(searchInputLi);

            const assuntosAgrupados = data.assuntos.reduce((acc, assunto) => {
                (acc[assunto.disciplina__nome] = acc[assunto.disciplina__nome] || []).push(assunto);
                return acc;
            }, {});

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
        } finally {
            updateUI();
        }
    }

    /**
     * ===================================================================
     * ATUALIZAÇÃO DA INTERFACE (Contadores)
     * ===================================================================
     */
    function updateUI() {
        ['disciplina', 'assunto', 'banca', 'instituicao', 'ano'].forEach(name => {
            const checkboxes = formFiltros.querySelectorAll(`input[name="${prefix}${name}"]:checked`);
            const countSpan = document.getElementById(`count-${prefix}${name}`);
            if (countSpan) {
                countSpan.style.display = checkboxes.length > 0 ? '' : 'none';
                if (checkboxes.length > 0) {
                    countSpan.textContent = checkboxes.length;
                }
            }
        });
    }

    // --- LISTENERS DE EVENTOS ---
    formFiltros.addEventListener('change', (e) => {
        const target = e.target;
        if (target.matches('input[type="checkbox"]')) {
            if (target.name === `${prefix}disciplina`) {
                loadAssuntos();
            } else {
                updateUI();
            }
        }
    });
    
    // --- CARGA INICIAL ---
    loadAssuntos();
});

// Função global para busca rápida (sem alterações)
function filterDropdownOptions(input) {
    const filter = input.value.toUpperCase();
    const ul = input.closest('ul.dropdown-menu');
    if (!ul) return;
    
    const items = ul.querySelectorAll('li:has(.form-check)');
    items.forEach(item => {
        const label = item.querySelector("label");
        if (label) {
            const txtValue = label.textContent || label.innerText;
            item.style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? "" : "none";
        }
    });
}