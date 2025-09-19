# gestao/templatetags/log_extras.py

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()

@register.filter(name='get_log_icon')
def get_log_icon(log):
    """Retorna uma classe de ícone do Font Awesome com base na ação do log."""
    icon_map = {
        # Ações de Usuário
        'USUARIO_DELETADO': 'fas fa-user-slash text-danger',
        'PERMISSOES_ALTERADAS': 'fas fa-user-shield text-info',
        'USUARIO_PROMOVIDO_SUPERUSER': 'fas fa-rocket text-success',
        'USUARIO_DESPROMOVIDO_SUPERUSER': 'fas fa-user-minus text-danger',
        
        # Ações de Solicitação de Exclusão (Usuário Comum)
        'SOLICITACAO_EXCLUSAO_CRIADA': 'fas fa-user-clock text-warning',
        'SOLICITACAO_EXCLUSAO_APROVADA': 'fas fa-user-check text-success',
        'SOLICITACAO_EXCLUSAO_REJEITADA': 'fas fa-user-times text-danger',
        'SOLICITACAO_EXCLUSAO_CANCELADA': 'fas fa-ban text-secondary',
        
        # Ações de Solicitação (Superusuário)
        'SOLICITACAO_PROMOCAO_CRIADA': 'fas fa-award text-warning',
        'SOLICITACAO_PROMOCAO_APROVADA': 'fas fa-thumbs-up text-info',
        'SOLICITACAO_PROMOCAO_CANCELADA': 'fas fa-ban text-secondary',
        'SOLICITACAO_DESPROMOCAO_CRIADA': 'fas fa-user-graduate text-warning',
        'SOLICITACAO_DESPROMOCAO_APROVADA': 'fas fa-thumbs-up text-info',
        'SOLICITACAO_DESPROMOCAO_CANCELADA': 'fas fa-ban text-secondary',
        'SOLICITACAO_EXCLUSAO_SUPERUSER_CRIADA': 'fas fa-user-shield text-warning',
        'SOLICITACAO_EXCLUSAO_SUPERUSER_APROVADA': 'fas fa-shield-alt text-info',
        'SOLICITACAO_EXCLUSAO_SUPERUSER_CANCELADA': 'fas fa-ban text-secondary',

        # Ações de Questão
        'QUESTAO_CRIADA': 'fas fa-plus-circle text-success',
        'QUESTAO_EDITADA': 'fas fa-edit text-info',
        'QUESTAO_DELETADA': 'fas fa-trash-alt text-warning',
        'QUESTAO_RESTAURADA': 'fas fa-trash-restore text-success',
        'QUESTAO_DELETADA_PERMANENTEMENTE': 'fas fa-fire text-danger',

        # Ações de Entidades (Disciplina, Banca, etc.)
        'ENTIDADE_CRIADA': 'fas fa-folder-plus text-success',
        'ASSUNTO_CRIADO': 'fas fa-tag text-success',
        
        # Ações de Simulado
        'SIMULADO_CRIADO': 'fas fa-file-alt text-success',
        'SIMULADO_EDITADO': 'fas fa-file-signature text-info',
        'SIMULADO_DELETADO': 'fas fa-file-excel text-danger',
        
        # Ações de Gamificação
        'CONQUISTA_CRIADA': 'fas fa-trophy text-success',
        'CONQUISTA_EDITADA': 'fas fa-award text-info',
        'CONQUISTA_DELETADA': 'fas fa-times-circle text-danger',
        'AVATAR_CRIADO': 'fas fa-user-plus text-success',
        'AVATAR_EDITADO': 'fas fa-user-edit text-info',
        'AVATAR_DELETADO': 'fas fa-user-times text-danger',
        'BORDA_CRIADA': 'fas fa-id-badge text-success',
        'BORDA_EDITADA': 'fas fa-paint-brush text-info',
        'BORDA_DELETADA': 'fas fa-eraser text-danger',
        'BANNER_CRIADO': 'fas fa-image text-success',
        'BANNER_EDITADO': 'fas fa-paint-roller text-info',
        'BANNER_DELETADO': 'fas fa-image-slash text-danger',
        'CONFIG_XP_EDITADA': 'fas fa-cogs text-info',

        # Ações de Notificação de Erro
        'NOTIFICACOES_RESOLVIDAS': 'fas fa-check-double text-success',
        'NOTIFICACOES_REJEITADAS': 'fas fa-times-circle text-danger',
        'NOTIFICACOES_DELETADAS': 'fas fa-eraser text-danger',

        # Ações de Auditoria e Segurança
        'LOG_DELETADO': 'fas fa-eraser text-warning',
        'TENTATIVA_EXCLUSAO_MASSA_EXCEDIDA': 'fas fa-hand-paper text-danger',
        
        # =======================================================================
        # ADIÇÃO DOS ÍCONES PARA AS NOVAS AÇÕES DE EXCLUSÃO DE LOGS
        # =======================================================================
        'SOLICITACAO_EXCLUSAO_LOG_CRIADA': 'fas fa-file-medical-alt text-warning',
        'SOLICITACAO_EXCLUSAO_LOG_APROVADA': 'fas fa-file-signature text-info',
        'LOG_DELETADO_PERMANENTEMENTE': 'fas fa-skull-crossbones text-danger',
        # =======================================================================
    }
    return icon_map.get(log.acao, 'fas fa-info-circle text-muted')

@register.filter(name='generate_log_message')
def generate_log_message(log):
    """Gera uma mensagem principal descritiva e profissional para o log."""
    ator = f"<strong>{escape(log.ator.username if log.ator else 'Sistema')}</strong>"
    detalhes = log.detalhes
    
    alvo_str = detalhes.get('alvo_str') or \
               detalhes.get('nome_simulado') or \
               detalhes.get('codigo_questao') or \
               detalhes.get('usuario_alvo') or \
               detalhes.get('usuario_deletado') or \
               detalhes.get('usuario_excluido') or \
               detalhes.get('nome_conquista') or \
               detalhes.get('nome_recompensa') or \
               detalhes.get('nome') or \
               'N/A'
    alvo_html = f"<strong>{escape(alvo_str)}</strong>"
    
    message = ""

    # Dicionário de mapeamento de ações para mensagens
    # Isso torna o código mais limpo e fácil de manter
    message_map = {
        # Ações de Usuário e Solicitações
        'USUARIO_DELETADO': f"{ator} deletou o usuário {alvo_html}.",
        'SOLICITACAO_EXCLUSAO_CRIADA': f"{ator} criou uma solicitação para excluir o usuário {alvo_html}.",
        'SOLICITACAO_EXCLUSAO_APROVADA': f"{ator} aprovou a solicitação de <strong>{escape(detalhes.get('solicitado_por', 'N/A'))}</strong> para excluir o usuário {alvo_html}.",
        'SOLICITACAO_EXCLUSAO_REJEITADA': f"{ator} rejeitou a solicitação de <strong>{escape(detalhes.get('solicitado_por', 'N/A'))}</strong> para excluir o usuário {alvo_html}.",
        'SOLICITACAO_EXCLUSAO_CANCELADA': f"{ator} cancelou sua própria solicitação para excluir o usuário {alvo_html}.",
        'SOLICITACAO_EXCLUSAO_SUPERUSER_CRIADA': f"{ator} criou uma solicitação para excluir o <strong>superusuário</strong> {alvo_html}.",
        'SOLICITACAO_EXCLUSAO_SUPERUSER_APROVADA': f"{ator} registrou uma aprovação na solicitação para excluir o <strong>superusuário</strong> {alvo_html}.",
        'SOLICITACAO_EXCLUSAO_SUPERUSER_CANCELADA': f"{ator} cancelou sua solicitação para excluir o <strong>superusuário</strong> {alvo_html}.",
        'SOLICITACAO_PROMOCAO_CRIADA': f"{ator} criou uma solicitação de promoção para {alvo_html}.",
        'SOLICITACAO_PROMOCAO_APROVADA': f"{ator} registrou uma aprovação na solicitação de promoção de {alvo_html}.",
        'SOLICITACAO_PROMOCAO_CANCELADA': f"{ator} cancelou sua solicitação de promoção para {alvo_html}.",
        'SOLICITACAO_DESPROMOCAO_CRIADA': f"{ator} criou uma solicitação de despromoção para {alvo_html}.",
        'SOLICITACAO_DESPROMOCAO_APROVADA': f"{ator} registrou uma aprovação na solicitação de despromoção de {alvo_html}.",
        'SOLICITACAO_DESPROMOCAO_CANCELADA': f"{ator} cancelou sua solicitação de despromoção para {alvo_html}.",
        'PERMISSOES_ALTERADAS': f"{ator} alterou as permissões de {alvo_html} de <em>{escape(detalhes.get('de', 'N/A'))}</em> para <em>{escape(detalhes.get('para', 'N/A'))}</em>.",
        'USUARIO_PROMOVIDO_SUPERUSER': f"{ator} promoveu o usuário {alvo_html} a Superusuário.",
        'USUARIO_DESPROMOVIDO_SUPERUSER': f"{ator} removeu as permissões de Superusuário do usuário {alvo_html}.",
        
        # Ações de Conteúdo
        'QUESTAO_CRIADA': f"{ator} criou a questão {alvo_html}.",
        'QUESTAO_EDITADA': f"{ator} editou a questão {alvo_html}.",
        'QUESTAO_RESTAURADA': f"{ator} restaurou a questão {alvo_html} da lixeira.",
        'QUESTAO_DELETADA_PERMANENTEMENTE': f"{ator} excluiu permanentemente a questão {alvo_html}.",
        'ENTIDADE_CRIADA': f"{ator} criou a {escape(detalhes.get('tipo', 'entidade')).lower()} {alvo_html}.",
        'ASSUNTO_CRIADO': f"{ator} criou o assunto <strong>{escape(detalhes.get('assunto', 'N/A'))}</strong> para a disciplina <strong>{escape(detalhes.get('disciplina', 'N/A'))}</strong>.",
        'SIMULADO_CRIADO': f"{ator} criou o simulado {alvo_html}.",
        'SIMULADO_EDITADO': f"{ator} editou o simulado {alvo_html}.",
        'SIMULADO_DELETADO': f"{ator} deletou o simulado {alvo_html}.",

        # Ações de Gamificação
        'CONQUISTA_CRIADA': f"{ator} criou a conquista {alvo_html}.",
        'CONQUISTA_EDITADA': f"{ator} editou a conquista {alvo_html}.",
        'CONQUISTA_DELETADA': f"{ator} deletou a conquista {alvo_html}.",
        'AVATAR_CRIADO': f"{ator} criou o avatar {alvo_html}.",
        'AVATAR_EDITADO': f"{ator} editou o avatar {alvo_html}.",
        'AVATAR_DELETADO': f"{ator} deletou o avatar {alvo_html}.",
        'BORDA_CRIADA': f"{ator} criou a borda de perfil {alvo_html}.",
        'BORDA_EDITADA': f"{ator} editou a borda de perfil {alvo_html}.",
        'BORDA_DELETADA': f"{ator} deletou a borda de perfil {alvo_html}.",
        'BANNER_CRIADO': f"{ator} criou o banner {alvo_html}.",
        'BANNER_EDITADO': f"{ator} editou o banner {alvo_html}.",
        'BANNER_DELETADO': f"{ator} deletou o banner {alvo_html}.",
        'CONFIG_XP_EDITADA': f"{ator} editou as configurações de gamificação.",

        # =======================================================================
        # ADIÇÃO DAS MENSAGENS PARA AS NOVAS AÇÕES DE EXCLUSÃO DE LOGS
        # =======================================================================
        'SOLICITACAO_EXCLUSAO_LOG_CRIADA': f"{ator} criou uma solicitação para excluir permanentemente <strong>{detalhes.get('quantidade', 'N/A')}</strong> registro(s) de log.",
        'SOLICITACAO_EXCLUSAO_LOG_APROVADA': f"{ator} registrou uma aprovação para excluir logs permanentemente.",
        'LOG_DELETADO_PERMANENTEMENTE': f"Com a aprovação final de {ator}, <strong>{detalhes.get('quantidade', 'N/A')}</strong> registro(s) de log foram excluídos permanentemente.",
        # =======================================================================
    }
    
    # Tenta obter a mensagem do mapa
    message = message_map.get(log.acao)

    # Tratamento para casos especiais com lógica mais complexa
    if log.acao == 'QUESTAO_DELETADA':
        if 'count' in detalhes:
            count = detalhes.get('count', 0)
            plural = 'questão' if count == 1 else 'questões'
            message = f"{ator} moveu <strong>{count}</strong> {plural} para a lixeira em massa."
        else:
            message = f"{ator} moveu a questão {alvo_html} para a lixeira."
    
    # Fallback para ações não mapeadas
    if not message:
        message = f"{ator} realizou a ação: {log.get_acao_display().lower()}."
        
    return mark_safe(message)


@register.filter(name='format_log_reason')
def format_log_reason(details_dict):
    """
    Formata e exibe a 'justificativa' de um log, se existir.
    """
    if not isinstance(details_dict, dict):
        return ""
        
    justificativa = details_dict.get('justificativa_fornecida') or details_dict.get('justificativa')
    
    if not justificativa:
        return ""

    content_escaped = escape(justificativa).strip()
    
    html = f'<blockquote class="log-reason-quote small text-muted mt-2">{content_escaped}</blockquote>'
    
    return mark_safe(html)