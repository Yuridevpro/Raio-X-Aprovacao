// static/js/notificacoes.js

document.addEventListener('DOMContentLoaded', function() {
    // Busca os modais no DOM. É esperado que eles existam no base.html ou no layout principal.
    const notificationModalEl = document.getElementById('notificationModal');
    const confirmationModalEl = document.getElementById('confirmationModal');

    // Avisa no console se um dos modais não for encontrado no HTML, indicando um possível problema no template.
    if (!notificationModalEl) {
        console.warn("Elemento #notificationModal não encontrado. A função 'showNotificationModal' usará 'alert()' como fallback.");
    }
    if (!confirmationModalEl) {
        console.warn("Elemento #confirmationModal não encontrado. A função 'showConfirmationModal' usará 'confirm()' como fallback.");
    }

    /**
     * ===================================================================
     * FUNÇÃO GLOBAL DE NOTIFICAÇÃO
     * ===================================================================
     * Exibe um modal de notificação genérico. Fica disponível globalmente no objeto window.
     * @param {string} title - O título do modal.
     * @param {string} message - A mensagem a ser exibida no corpo.
     * @param {string} [type='info'] - O tipo de notificação ('success', 'error', 'warning', 'info').
     * @param {function | null} [onCloseCallback=null] - (Opcional) Função a ser executada quando o modal for fechado.
     */
    window.showNotificationModal = function(title, message, type = 'info', onCloseCallback = null) {
        // Fallback: Se o elemento do modal não existir no DOM, usa o alert padrão do navegador.
        if (!notificationModalEl) {
            alert(`${title}: ${message}`);
            // Executa o callback mesmo no modo de fallback, se ele for uma função.
            if (typeof onCloseCallback === 'function') {
                onCloseCallback();
            }
            return;
        }

        // Usa o método do Bootstrap 5 para obter a instância do modal ou criá-la se não existir.
        const modal = bootstrap.Modal.getOrCreateInstance(notificationModalEl);
        
        // Seleciona os elementos internos do modal para personalização.
        const modalTitle = notificationModalEl.querySelector('.modal-title');
        const modalBody = notificationModalEl.querySelector('.modal-body');
        const modalHeader = notificationModalEl.querySelector('.modal-header');

        // Define o título e a mensagem.
        modalTitle.textContent = title;
        modalBody.innerHTML = message; // innerHTML para permitir tags como <br> ou <strong>.

        // Reseta as classes de cor do cabeçalho para garantir que apenas uma seja aplicada.
        modalHeader.className = 'modal-header text-white'; 
        
        // Aplica a classe de cor apropriada com base no tipo de notificação.
        switch (type) {
            case 'success':
                modalHeader.classList.add('bg-success');
                break;
            case 'error':
                modalHeader.classList.add('bg-danger');
                break;
            case 'warning':
                modalHeader.classList.add('bg-warning', 'text-dark'); // Texto escuro para melhor contraste com fundo amarelo.
                break;
            default: // 'info' e qualquer outro tipo
                modalHeader.classList.add('bg-primary');
                break;
        }
        
        // Listener para o callback de fechamento.
        // Verifica se um callback foi passado e se é uma função.
        if (typeof onCloseCallback === 'function') {
            // Adiciona um listener para o evento 'hidden.bs.modal', que o Bootstrap dispara
            // assim que o modal termina de ser ocultado.
            // A opção { once: true } é crucial: garante que o listener seja executado apenas uma vez
            // e depois removido automaticamente, evitando chamadas múltiplas em usos futuros do modal.
            notificationModalEl.addEventListener('hidden.bs.modal', onCloseCallback, { once: true });
        }
        
        modal.show();
    }

    /**
     * ===================================================================
     * FUNÇÃO GLOBAL DE CONFIRMAÇÃO
     * ===================================================================
     * Exibe um modal de confirmação e executa um callback se o usuário clicar em "Confirmar".
     * @param {string} title - O título do modal de confirmação.
     * @param {string} message - A pergunta ou mensagem de confirmação.
     * @param {function} onConfirmCallback - A função a ser executada APENAS se o usuário confirmar.
     */
    window.showConfirmationModal = function(title, message, onConfirmCallback) {
        // Fallback: Se o modal não existir, usa o confirm() padrão do navegador.
        if (!confirmationModalEl) {
            if (confirm(message)) {
                onConfirmCallback();
            }
            return;
        }

        const modal = bootstrap.Modal.getOrCreateInstance(confirmationModalEl);
        
        // Personaliza o título e a mensagem do modal.
        confirmationModalEl.querySelector('.modal-title').textContent = title;
        confirmationModalEl.querySelector('.modal-body').textContent = message;
        
        const confirmBtn = confirmationModalEl.querySelector('#btn-confirm-action');
        
        // Técnica para remover listeners de eventos antigos: clonar o botão e substituí-lo.
        // Isso previne que múltiplos callbacks de confirmação fiquem "presos" ao botão.
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        // Adiciona o novo listener de clique ao botão clonado.
        newConfirmBtn.addEventListener('click', () => {
            onConfirmCallback(); // Executa a ação de confirmação.
            modal.hide();      // Esconde o modal.
        }, { once: true }); // Garante que este listener também rode apenas uma vez.

        modal.show();
    }
});