// static/js/notificacoes.js

document.addEventListener('DOMContentLoaded', function() {
    // Busca os dois modais no DOM
    const notificationModalEl = document.getElementById('notificationModal');
    const confirmationModalEl = document.getElementById('confirmationModal');

    // Avisa no console se um dos modais não for encontrado no HTML
    if (!notificationModalEl) {
        console.warn("Elemento #notificationModal não encontrado. A função showNotificationModal usará alerts como fallback.");
    }
    if (!confirmationModalEl) {
        console.warn("Elemento #confirmationModal não encontrado. A função showConfirmationModal usará confirm() como fallback.");
    }

    /**
     * ===================================================================
     * INÍCIO DA MUDANÇA: A função agora aceita um 'callback'.
     * ===================================================================
     * Exibe um modal de notificação genérico. Fica disponível globalmente.
     * @param {string} title - O título do modal.
     * @param {string} message - A mensagem a ser exibida.
     * @param {string} type - O tipo ('success', 'error', 'warning' ou 'info').
     * @param {function | null} [onCloseCallback=null] - Função a ser executada quando o modal for fechado.
     */
    window.showNotificationModal = function(title, message, type = 'info', onCloseCallback = null) {
        if (!notificationModalEl) {
            alert(`${title}: ${message}`);
            // Executa o callback mesmo no modo de fallback
            if (typeof onCloseCallback === 'function') {
                onCloseCallback();
            }
            return;
        }

        const modal = bootstrap.Modal.getOrCreateInstance(notificationModalEl);
        
        const modalTitle = notificationModalEl.querySelector('.modal-title');
        const modalBody = notificationModalEl.querySelector('.modal-body');
        const modalHeader = notificationModalEl.querySelector('.modal-header');

        modalTitle.textContent = title;
        modalBody.innerHTML = message;

        modalHeader.className = 'modal-header text-white'; 
        
        if (type === 'success') modalHeader.classList.add('bg-success');
        else if (type === 'error') modalHeader.classList.add('bg-danger');
        else if (type === 'warning') modalHeader.classList.add('bg-warning', 'text-dark');
        else modalHeader.classList.add('bg-primary');
        
        // >>> PONTO-CHAVE DA CORREÇÃO <<<
        // Verifica se um callback foi passado. Se sim, adiciona um listener
        // para o evento 'hidden.bs.modal', que dispara quando o modal é fechado.
        // A opção { once: true } garante que o listener seja removido após o primeiro uso,
        // evitando que ele seja chamado múltiplas vezes.
        if (typeof onCloseCallback === 'function') {
            notificationModalEl.addEventListener('hidden.bs.modal', onCloseCallback, { once: true });
        }
        
        modal.show();
    }
    // ===================================================================
    // FIM DA MUDANÇA
    // ===================================================================

    /**
     * Exibe um modal de confirmação e executa um callback quando o usuário confirma.
     */
    window.showConfirmationModal = function(title, message, onConfirmCallback) {
        if (!confirmationModalEl) {
            if (confirm(message)) {
                onConfirmCallback();
            }
            return;
        }
        const modal = bootstrap.Modal.getOrCreateInstance(confirmationModalEl);
        confirmationModalEl.querySelector('.modal-title').textContent = title;
        confirmationModalEl.querySelector('.modal-body').textContent = message;
        const confirmBtn = confirmationModalEl.querySelector('#btn-confirm-action');
        
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        newConfirmBtn.addEventListener('click', () => {
            onConfirmCallback();
            modal.hide();
        }, { once: true });

        modal.show();
    }
});