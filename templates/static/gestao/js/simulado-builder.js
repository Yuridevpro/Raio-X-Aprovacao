/**
 * SimuladoBuilder.js
 * Orquestra toda a interatividade da página de edição de simulados.
 *
 * Funcionalidades:
 * - Adicionar/Remover questões com feedback visual instantâneo.
 * - Atualizar o resumo (total e por disciplina) em tempo real.
 * - Habilitar reordenação de questões na lista via Drag & Drop.
 * - Comunicação com a API do backend para persistir as mudanças.
 */
class SimuladoBuilder {
    constructor(options) {
        // Inicializa as propriedades com os dados passados pelo template Django
        this.simuladoId = options.simuladoId;
        this.questoesNoSimulado = new Set(JSON.parse(document.getElementById(options.questoesNoSimulado).textContent));
        this.csrfToken = options.csrfToken;

        // Mapeia os elementos do DOM para acesso rápido
        this.cacheElements();
        // Configura todos os listeners de eventos
        this.initListeners();
        // Garante que o resumo inicial esteja correto ao carregar a página
        this.updateSummary();
    }

    cacheElements() {
        this.tabelaQuestoesBody = document.getElementById('tabela-questoes-disponiveis');
        this.listaSelecionadas = document.getElementById('lista-questoes-selecionadas');
        this.placeholderListaVazia = document.getElementById('placeholder-lista-vazia');
        this.badgeTotal = document.getElementById('total-questoes-badge');
        this.summaryDisciplinasContainer = document.getElementById('summary-disciplinas');
    }

    initListeners() {
        // Listener para os botões "Adicionar" / "Remover" na tabela de biblioteca
        if (this.tabelaQuestoesBody) {
            this.tabelaQuestoesBody.addEventListener('click', (e) => {
                const button = e.target.closest('.btn-manage-questao');
                if (button) {
                    const questaoId = button.dataset.questaoId;
                    const action = button.dataset.action;
                    this.gerenciarQuestao(questaoId, action, button);
                }
            });
        }

        // Listener para o botão "Remover" (ícone 'x') na lista de questões adicionadas
        if (this.listaSelecionadas) {
            this.listaSelecionadas.addEventListener('click', (e) => {
                const button = e.target.closest('.btn-remover-da-lista');
                if (button) {
                    const questaoId = button.dataset.questaoId;
                    // Ao remover da lista lateral, a ação é sempre 'remove'
                    this.gerenciarQuestao(questaoId, 'remove', button);
                }
            });
        }

        // Inicializa a funcionalidade de Drag & Drop (usando SortableJS)
        if (this.listaSelecionadas) {
            new Sortable(this.listaSelecionadas, {
                animation: 150,
                ghostClass: 'bg-light' // Estilo do item enquanto é arrastado
            });
        }
    }

    /**
     * Função central que se comunica com o backend via API.
     * @param {string} questaoId - ID da questão a ser gerenciada.
     * @param {string} action - 'add' ou 'remove'.
     * @param {HTMLElement} buttonElement - O botão que foi clicado.
     */
    async gerenciarQuestao(questaoId, action, buttonElement) {
        if (buttonElement) buttonElement.disabled = true;

        try {
            const response = await fetch(`/gestao/simulados/api/gerenciar-questoes/${this.simuladoId}/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
                body: JSON.stringify({ 'action': action, 'questao_id': questaoId })
            });

            if (!response.ok) {
                throw new Error(`Erro na comunicação com o servidor: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.status === 'success') {
                this.updateUIAfterAction(questaoId, action);
            } else {
                showNotificationModal('Erro', data.message || 'Ocorreu um erro inesperado.', 'error');
            }
        } catch (error) {
            showNotificationModal('Erro de Rede', error.message || 'Não foi possível conectar ao servidor.', 'error');
        } finally {
            if (buttonElement) buttonElement.disabled = false;
        }
    }

    /**
     * Atualiza todos os elementos da interface após uma ação bem-sucedida.
     * @param {string} questaoId - ID da questão.
     * @param {string} action - 'add' ou 'remove'.
     */
    updateUIAfterAction(questaoId, action) {
        const questaoIdNum = parseInt(questaoId, 10);
        const tableRow = document.getElementById(`questao-row-${questaoId}`);

        if (action === 'add') {
            this.questoesNoSimulado.add(questaoIdNum);
            if (tableRow) this.adicionarQuestaoNaLista(tableRow);
        } else {
            this.questoesNoSimulado.delete(questaoIdNum);
            this.removerQuestaoDaLista(questaoId);
        }
        
        // Atualiza o botão na tabela principal, se ele estiver visível
        if (tableRow) this.toggleTableButton(tableRow.querySelector('.btn-manage-questao'), action);
        
        // Atualiza o resumo de contadores
        this.updateSummary();
    }

    toggleTableButton(button, action) {
        if (!button) return;
        if (action === 'add') {
            button.textContent = 'Remover';
            button.classList.replace('btn-outline-success', 'btn-outline-danger');
            button.dataset.action = 'remove';
        } else {
            button.textContent = 'Adicionar';
            button.classList.replace('btn-outline-danger', 'btn-outline-success');
            button.dataset.action = 'add';
        }
    }

    adicionarQuestaoNaLista(tableRow) {
        if (this.placeholderListaVazia) this.placeholderListaVazia.style.display = 'none';
        
        const id = tableRow.id.replace('questao-row-', '');
        const codigo = tableRow.dataset.codigo;
        const disciplinaNome = tableRow.dataset.disciplinaNome;
        const disciplinaId = tableRow.dataset.disciplinaId;

        const itemHtml = `
            <div class="list-group-item questao-selecionada-item" id="selecionada-${id}" data-disciplina-id="${disciplinaId}" data-disciplina-nome="${disciplinaNome}">
                <span class="text-truncate me-2" title="${codigo}: ${disciplinaNome}"><strong>${codigo}:</strong> ${disciplinaNome}</span>
                <div class="actions">
                    <button class="btn btn-sm btn-outline-danger py-0 px-1 btn-remover-da-lista" data-questao-id="${id}" title="Remover do Simulado"><i class="fas fa-times"></i></button>
                </div>
            </div>`;
        this.listaSelecionadas.insertAdjacentHTML('beforeend', itemHtml);
    }

    removerQuestaoDaLista(id) {
        const item = document.getElementById(`selecionada-${id}`);
        if (item) item.remove();
        if (this.listaSelecionadas.children.length === 1 && this.placeholderListaVazia) {
            // Se o único filho restante for o placeholder, ele não conta
            this.placeholderListaVazia.style.display = 'block';
        }
    }

    updateSummary() {
        this.badgeTotal.textContent = this.questoesNoSimulado.size;
        
        const disciplinaCounts = {};
        this.listaSelecionadas.querySelectorAll('.questao-selecionada-item').forEach(item => {
            const disciplinaId = item.dataset.disciplinaId;
            const disciplinaNome = item.dataset.disciplinaNome;
            if (!disciplinaCounts[disciplinaId]) {
                disciplinaCounts[disciplinaId] = { nome: disciplinaNome, count: 0 };
            }
            disciplinaCounts[disciplinaId].count++;
        });

        let summaryHtml = '<strong class="d-block mb-1">Por Disciplina:</strong>';
        if (Object.keys(disciplinaCounts).length > 0) {
            for (const id in disciplinaCounts) {
                const item = disciplinaCounts[id];
                summaryHtml += `<span class="badge bg-secondary me-1 mb-1 summary-badge">${item.nome} <span class="badge bg-light text-dark ms-1">${item.count}</span></span>`;
            }
        } else {
            summaryHtml += '<span class="small text-muted">Nenhuma questão adicionada.</span>';
        }
        this.summaryDisciplinasContainer.innerHTML = summaryHtml;
    }
}