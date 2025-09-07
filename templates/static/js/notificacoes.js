// static/js/notificacoes.js

// Espera o DOM carregar para garantir que o HTML do modal exista.
document.addEventListener('DOMContentLoaded', function() {
    const notificationModalEl = document.getElementById('notificationModal');
    
    // Se o elemento do modal não estiver na página, não faz nada.
    if (!notificationModalEl) return;

    const notificationModal = new bootstrap.Modal(notificationModalEl);
    const modalTitle = document.getElementById('notificationModalLabel');
    const modalBody = document.getElementById('notificationModalBody');
    const modalHeader = document.getElementById('notificationModalHeader');

    /**
     * Exibe um modal de notificação genérico. Fica disponível globalmente.
     * @param {string} title - O título do modal.
     * @param {string} message - A mensagem a ser exibida.
     * @param {string} type - O tipo ('success', 'error', ou 'info').
     */
    window.showNotificationModal = function(title, message, type = 'info') {
        if (!notificationModal) {
            // Fallback para alert() caso algo dê muito errado.
            alert(`${title}: ${message}`);
            return;
        }

        modalTitle.textContent = title;
        modalBody.innerHTML = message;

        modalHeader.classList.remove('bg-success', 'bg-danger', 'bg-primary');

        if (type === 'success') {
            modalHeader.classList.add('bg-success');
        } else if (type === 'error') {
            modalHeader.classList.add('bg-danger');
        } else {
            modalHeader.classList.add('bg-primary'); // Cor padrão para 'info'
        }

        notificationModal.show();
    }
});