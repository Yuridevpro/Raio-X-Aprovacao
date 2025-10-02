/**
 * Lógica de Loader Inteligente
 *
 * Este script implementa um loader que só aparece se o carregamento da página
 * demorar mais do que um tempo mínimo (MIN_DELAY), evitando o "flash" em
 * conexões rápidas. Ele espera o evento 'window.load' (carregamento completo
 * de todos os recursos) para garantir uma transição suave.
 */
(function() {
    // --- CONFIGURAÇÕES ---
    // Tempo em milissegundos que a página precisa demorar para carregar
    // antes que o loader apareça. Um bom valor é entre 200ms e 500ms.
    const MIN_DELAY_TO_SHOW_LOADER = 800;

    // --- ELEMENTOS ---
    const loader = document.getElementById('page-loader');
    const content = document.getElementById('page-content-wrapper');

    // Se os elementos essenciais não existirem, o script não faz nada.
    if (!loader || !content) {
        console.warn('Loader script: Elementos #page-loader ou #page-content-wrapper não encontrados. O loader não será ativado.');
        return;
    }

    let loaderTimer;

    // --- LÓGICA ---

    // 1. Inicia um timer. Se ele terminar ANTES do 'window.load', o loader aparece.
    loaderTimer = setTimeout(() => {
        loader.classList.add('visible');
    }, MIN_DELAY_TO_SHOW_LOADER);

    // 2. Espera a página carregar completamente (incluindo imagens, CSS, etc.).
    window.addEventListener('load', () => {
        // 2a. O carregamento foi rápido! Cancela o timer que iria mostrar o loader.
        // Se o tempo de carregamento foi menor que MIN_DELAY_TO_SHOW_LOADER,
        // o loader nunca chegará a aparecer.
        clearTimeout(loaderTimer);

        // 2b. Esconde o loader (se ele estiver visível) e mostra o conteúdo.
        hideLoaderAndShowContent();
    });

    /**
     * Função que esconde o loader com um efeito de fade-out e
     * mostra o conteúdo principal da página com um fade-in.
     */
    function hideLoaderAndShowContent() {
        if (loader) {
            // A classe 'visible' é removida e a 'hidden' é adicionada
            // para controlar a transição de desaparecimento via CSS.
            loader.classList.remove('visible');
            loader.classList.add('hidden');
        }
        if (content) {
            // Torna o conteúdo visível.
            content.style.opacity = '1';
        }
    }

})(); // Executa a função anônima para proteger o escopo.