/**
 * Função genérica para exibir toasts de gamificação.
 * Usada para XP ganho em questões e simulados.
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


function showRewardModal(title, bodyHtml) {
  let modalElement = document.getElementById('gamificationRewardModal');
  if (!modalElement) {
      document.body.insertAdjacentHTML('beforeend', `
          <div class="modal fade" id="gamificationRewardModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
              <div class="modal-content text-center">
                <div class="modal-header border-0">
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body px-5 pb-5">
                  <h2 class="modal-title h4 mb-3" id="gamificationRewardModalTitle"></h2>
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

  if (window.confetti) {
      confetti({ particleCount: 150, spread: 90, origin: { y: 0.6 } });
  }
}

function triggerLevelUpNotification(levelUpInfo) {
  if (!levelUpInfo) return;
  const title = `<i class="fas fa-star text-warning fa-2x mb-3"></i><br>Você subiu de Nível!`;
  const body = `<p class="lead">Parabéns! Você alcançou o <strong>Nível ${levelUpInfo.novo_level}</strong>.</p><p>Novas recompensas podem ter sido desbloqueadas na sua coleção!</p>`;
  showRewardModal(title, body);
}

function triggerNewRewardsNotification(rewards) {
    if (!rewards || rewards.length === 0) return;

    const title = `<i class="fas fa-gift text-primary fa-2x mb-3"></i><br>Novas Recompensas!`;

    // 1. Agrupa as recompensas recebidas pelo seu tipo
    const groupedRewards = rewards.reduce((acc, reward) => {
        const tipo = reward.tipo || 'Outro'; // Garante um fallback
        if (!acc[tipo]) {
            acc[tipo] = [];
        }
        acc[tipo].push(reward);
        return acc;
    }, {});

    let rewardsHtml = '<p class="lead">Você desbloqueou os seguintes itens:</p>';

    // 2. Monta o HTML para cada grupo de recompensa
    for (const tipo in groupedRewards) {
        const plural = groupedRewards[tipo].length > 1 ? 's' : '';
        const icon = {
            'Avatar': 'fa-user-circle',
            'Borda': 'fa-id-badge',
            'Banner': 'fa-image'
        }[tipo] || 'fa-gem'; // Ícone padrão

        rewardsHtml += `<h6 class="text-start mt-3"><i class="fas ${icon} me-2 text-muted"></i><strong>${tipo}${plural}</strong></h6>`;
        rewardsHtml += '<ul class="list-unstyled">';

        groupedRewards[tipo].forEach(r => {
            rewardsHtml += `<li class="d-flex align-items-center my-2 gap-2">
                              <img src="${r.imagem_url}" width="40" height="40" class="rounded">
                              <span>${r.nome}</span> 
                              <span class="badge bg-light text-dark ms-auto">${r.raridade}</span>
                            </li>`;
        });
        rewardsHtml += '</ul>';
    }

    // 3. Adiciona uma dica final útil
    rewardsHtml += `<hr><p class="small text-muted mt-3">Visite a seção <strong>Minha Coleção</strong> no seu perfil para equipá-los!</p>`;

    showRewardModal(title, rewardsHtml);
}