/**
 * ===================================================================
 * FUNÇÕES GLOBAIS DE FEEDBACK VISUAL
 * ===================================================================
 */

/**
 * Função genérica para exibir toasts de gamificação.
 * Usada para XP ganho, bônus e outras notificações rápidas.
 * @param {string} title - O título do toast.
 * @param {string} bodyContent - O conteúdo HTML do corpo do toast.
 * @param {string} icon - Classes do ícone Font Awesome (ex: 'fas fa-star').
 * @param {string} color - A cor do ícone.
 */
function showGamificationToast(title, bodyContent, icon, color = '#0d6efd') {
  const toastEl = document.getElementById('gamificationToast');
  if (!toastEl) return;

  const toast = bootstrap.Toast.getOrCreateInstance(toastEl);
  const toastTitle = document.getElementById('gamificationToastTitle');
  const toastBody = document.getElementById('gamificationToastBody');
  
  toastTitle.innerHTML = `<i class="${icon} me-2" style="color: ${color};"></i> ${title}`;
  toastBody.innerHTML = bodyContent;
  
  toast.show();
}

/**
 * Função especializada para exibir toasts de ganho de moedas.
 * @param {number} amount - A quantidade de moedas ganhas.
 * @param {string} reason - O motivo do ganho (ex: 'pela sua resposta').
 */
function showCoinToast(amount, reason = '') {
    if (amount <= 0) return;
    showGamificationToast(
        `+${amount} FC!`,
        `Você ganhou <strong>${amount} Fragmentos de Conhecimento</strong> ${reason}!`,
        'fas fa-coins',
        '#ffc107' // Cor amarela para moedas
    );
}

/**
 * Exibe um modal de recompensa centralizado com efeito de confete.
 * Usado para eventos importantes como Level Up ou desbloqueio de múltiplos itens.
 * @param {string} title - O título HTML a ser exibido no modal.
 * @param {string} bodyHtml - O conteúdo HTML do corpo do modal.
 */
function showRewardModal(title, bodyHtml) {
  let modalElement = document.getElementById('gamificationRewardModal');
  if (!modalElement) {
      document.body.insertAdjacentHTML('beforeend', `
          <div class="modal fade" id="gamificationRewardModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
              <div class="modal-content text-center">
                <div class="modal-header border-0 pb-0">
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body px-4 pb-4">
                  <div class="mb-3" id="gamificationRewardModalTitle"></div>
                  <div id="gamificationRewardModalBody"></div>
                </div>
              </div>
            </div>
          </div>
      `);
      modalElement = document.getElementById('gamificationRewardModal');
  }
  
  document.getElementById('gamificationRewardModalTitle').innerHTML = title;
  document.getElementById('gamificationRewardModalBody').innerHTML = bodyHtml;
  
  const modal = new bootstrap.Modal(modalElement);
  modal.show();

  // Dispara o efeito de confete, se a biblioteca estiver carregada.
  if (window.confetti) {
      confetti({ particleCount: 150, spread: 90, origin: { y: 0.6 } });
  }
}

/**
 * ===================================================================
 * FUNÇÕES "TRIGGER" (Acionadores de Notificação)
 * ===================================================================
 */

/**
 * Aciona um modal de notificação de "Level Up".
 * @param {object} levelUpInfo - Objeto com a chave 'novo_level'.
 */
function triggerLevelUpNotification(levelUpInfo) {
  if (!levelUpInfo || !levelUpInfo.novo_level) return;
  const title = `<i class="fas fa-star text-warning fa-3x"></i><h2 class="h3 mt-3">Você subiu de Nível!</h2>`;
  const body = `<p class="lead">Parabéns! Você alcançou o <strong>Nível ${levelUpInfo.novo_level}</strong>.</p><p class="text-muted small">Novos prêmios podem estar te esperando na sua Caixa de Recompensas!</p>`;
  showRewardModal(title, body);
}

/**
 * Aciona um modal notificando que novos prêmios foram enviados para a Caixa de Recompensas.
 * @param {Array} rewards - Uma lista de objetos de recompensa serializados.
 */
function triggerNewPendingRewardsNotification(rewards) {
    if (!rewards || rewards.length === 0) return;

    const title = `<i class="fas fa-gift text-primary fa-3x"></i><h2 class="h3 mt-3">Novos Prêmios Ganhos!</h2>`;
    
    const groupedRewards = rewards.reduce((acc, reward) => {
        const tipo = reward.tipo || 'Outro';
        if (!acc[tipo]) acc[tipo] = [];
        acc[tipo].push(reward);
        return acc;
    }, {});

    let rewardsHtml = '<p class="lead">Você ganhou os seguintes itens por seu desempenho:</p>';

    for (const tipo in groupedRewards) {
        const plural = groupedRewards[tipo].length > 1 ? 's' : '';
        const icon = { 'Avatar': 'fa-user-circle', 'Borda': 'fa-id-badge', 'Banner': 'fa-image' }[tipo] || 'fa-gem';

        rewardsHtml += `<h6 class="text-start mt-3"><i class="fas ${icon} me-2 text-muted"></i><strong>${tipo}${plural}</strong></h6>`;
        rewardsHtml += '<ul class="list-unstyled">';
        groupedRewards[tipo].forEach(r => {
            rewardsHtml += `<li class="d-flex align-items-center my-2 gap-3">
                              <img src="${r.imagem_url}" width="40" height="40" class="rounded shadow-sm">
                              <span>${r.nome}</span> 
                              <span class="badge bg-light text-dark ms-auto">${r.raridade}</span>
                            </li>`;
        });
        rewardsHtml += '</ul>';
    }

    rewardsHtml += `<hr><p class="mt-3">Visite a <strong>Caixa de Recompensas</strong> no seu perfil para resgatá-los!</p>`;

    showRewardModal(title, rewardsHtml);
}

/**
 * ===================================================================
 * FUNÇÕES DE ATUALIZAÇÃO DA INTERFACE (UI)
 * ===================================================================
 */

/**
 * Atualiza o saldo de moedas na barra de navegação com uma animação sutil.
 * @param {number} newBalance - O novo saldo de moedas do usuário.
 */
function updateNavbarCoinBalance(newBalance) {
    const balanceElement = document.getElementById('navbar-coin-balance');
    if (balanceElement) {
        const startValue = parseInt(balanceElement.textContent.replace(/\D/g, ''), 10) || 0;
        const endValue = parseInt(newBalance, 10);
        
        if (startValue === endValue) return;

        const duration = 1000;
        let startTime = null;

        function animationStep(timestamp) {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            const currentValue = Math.floor(progress * (endValue - startValue) + startValue);
            balanceElement.textContent = currentValue;
            if (progress < 1) {
                window.requestAnimationFrame(animationStep);
            }
        }
        window.requestAnimationFrame(animationStep);
        
        // A animação de "flash" requer Animate.css. Se não estiver usando, pode remover este bloco.
        setTimeout(() => {
            if (typeof balanceElement.classList.add === 'function') {
                balanceElement.classList.add('animate__animated', 'animate__flash');
                balanceElement.addEventListener('animationend', () => {
                    balanceElement.classList.remove('animate__animated', 'animate__flash');
                }, { once: true });
            }
        }, duration);
    }
}
// ✅ CORREÇÃO: A chave '}' extra foi removida daqui.