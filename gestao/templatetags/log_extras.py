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

        # Ações de Notificação de Erro
        'NOTIFICACOES_RESOLVIDAS': 'fas fa-check-double text-success',
        'NOTIFICACOES_REJEITADAS': 'fas fa-times-circle text-danger',
        'NOTIFICACOES_DELETADAS': 'fas fa-eraser text-danger',

        # Ações de Auditoria e Segurança
        'LOG_DELETADO': 'fas fa-eraser text-danger',
        'TENTATIVA_EXCLUSAO_MASSA_EXCEDIDA': 'fas fa-hand-paper text-danger',
    }
    return icon_map.get(log.acao, 'fas fa-info-circle text-muted')

@register.filter(name='generate_log_message')
def generate_log_message(log):
    """Gera uma mensagem principal descritiva e profissional para o log."""
    ator = f"<strong>{escape(log.ator.username if log.ator else 'Sistema')}</strong>"
    detalhes = log.detalhes
    
    # Mensagens para Ações de Usuário e Solicitações
    if log.acao == 'USUARIO_DELETADO':
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', detalhes.get('usuario_deletado', 'N/A')))}</strong>"
        if "Confirmação final pelo solicitante" in detalhes.get('motivo', ''):
            message = f"{ator} confirmou sua própria solicitação, excluindo o <strong>superusuário</strong> {usuario}."
        else:
            message = f"{ator} deletou o usuário {usuario}."
    
    elif log.acao == 'SOLICITACAO_EXCLUSAO_CRIADA':
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} criou uma solicitação para excluir o usuário {usuario}."
    
    elif log.acao == 'SOLICITACAO_EXCLUSAO_APROVADA':
        usuario = f"<strong>{escape(detalhes.get('usuario_excluido', 'N/A'))}</strong>"
        solicitante = f"<strong>{escape(detalhes.get('solicitado_por', 'N/A'))}</strong>"
        message = f"{ator} aprovou a solicitação de {solicitante} para excluir o usuário {usuario}."
    
    elif log.acao == 'SOLICITACAO_EXCLUSAO_REJEITADA':
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        solicitante = f"<strong>{escape(detalhes.get('solicitado_por', 'N/A'))}</strong>"
        message = f"{ator} rejeitou a solicitação de {solicitante} para excluir o usuário {usuario}."
        
    elif log.acao == 'SOLICITACAO_EXCLUSAO_CANCELADA':
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} cancelou sua própria solicitação para excluir o usuário {usuario}."

    elif log.acao == 'SOLICITACAO_EXCLUSAO_SUPERUSER_CRIADA':
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} criou uma solicitação para excluir o <strong>superusuário</strong> {usuario}."

    elif log.acao == 'SOLICITACAO_EXCLUSAO_SUPERUSER_APROVADA':
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} registrou uma aprovação na solicitação para excluir o <strong>superusuário</strong> {usuario}."

    elif log.acao == 'SOLICITACAO_EXCLUSAO_SUPERUSER_CANCELADA':
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} cancelou sua solicitação para excluir o <strong>superusuário</strong> {usuario}."

    elif log.acao in ['SOLICITACAO_PROMOCAO_CRIADA', 'SOLICITACAO_DESPROMOCAO_CRIADA']:
        acao_texto = "promoção" if log.acao == 'SOLICITACAO_PROMOCAO_CRIADA' else "despromoção"
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} criou uma solicitação de {acao_texto} para {usuario}."

    elif log.acao in ['SOLICITACAO_PROMOCAO_APROVADA', 'SOLICITACAO_DESPROMOCAO_APROVADA']:
        acao_texto = "promoção" if log.acao == 'SOLICITACAO_PROMOCAO_APROVADA' else "despromoção"
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} registrou uma aprovação na solicitação de {acao_texto} de {usuario}."
    
    elif log.acao == 'SOLICITACAO_PROMOCAO_CANCELADA':
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} cancelou sua solicitação de promoção para {usuario}."
        
    elif log.acao == 'SOLICITACAO_DESPROMOCAO_CANCELADA':
        usuario = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} cancelou sua solicitação de despromoção para {usuario}."

    # Mensagens para Permissões
    elif log.acao == 'PERMISSOES_ALTERADAS':
        alvo = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        de = f"<em>{escape(detalhes.get('de', 'N/A'))}</em>"
        para = f"<em>{escape(detalhes.get('para', 'N/A'))}</em>"
        message = f"{ator} alterou as permissões do usuário {alvo} de {de} para {para}."

    elif log.acao == 'USUARIO_PROMOVIDO_SUPERUSER':
        alvo = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        message = f"{ator} promoveu o usuário {alvo} a Superusuário."

    elif log.acao == 'USUARIO_DESPROMOVIDO_SUPERUSER':
        alvo = f"<strong>{escape(detalhes.get('usuario_alvo', 'N/A'))}</strong>"
        if "Confirmação final pelo solicitante" in detalhes.get('motivo', ''):
            message = f"{ator} confirmou sua própria solicitação, despromovendo o <strong>superusuário</strong> {alvo}."
        else:
            message = f"{ator} removeu as permissões de Superusuário do usuário {alvo}."
    
    # Mensagens para Ações de Questão
    elif log.acao == 'QUESTAO_CRIADA':
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        message = f"{ator} criou a questão {codigo}."

    elif log.acao == 'QUESTAO_EDITADA':
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        message = f"{ator} editou a questão {codigo}."

    # =======================================================================
    # INÍCIO DA MODIFICAÇÃO
    # =======================================================================
    elif log.acao == 'QUESTAO_DELETADA':
        # Verifica se o log é de uma ação em massa (procurando pela chave 'count')
        if 'count' in detalhes:
            count = detalhes.get('count', 0)
            plural = 'questão' if count == 1 else 'questões'
            message = f"{ator} moveu <strong>{count}</strong> {plural} para a lixeira em massa."
        # Senão, trata como uma exclusão individual
        else:
            codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
            message = f"{ator} moveu a questão {codigo} para a lixeira."
    # =======================================================================
    # FIM DA MODIFICAÇÃO
    # =======================================================================

    elif log.acao == 'QUESTAO_RESTAURADA':
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        message = f"{ator} restaurou a questão {codigo} da lixeira."

    elif log.acao == 'QUESTAO_DELETADA_PERMANENTEMENTE':
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        message = f"{ator} excluiu permanentemente a questão {codigo}."
        
    elif log.acao == 'TENTATIVA_EXCLUSAO_MASSA_EXCEDIDA':
        quantidade = detalhes.get('quantidade_tentada', 'N/A')
        limite = detalhes.get('limite', 'N/A')
        message = f"{ator} tentou uma ação em massa com <strong>{quantidade}</strong> itens, mas foi bloqueado pelo limite de <strong>{limite}</strong>."

    # Mensagens para Entidades
    elif log.acao == 'ENTIDADE_CRIADA':
        tipo = escape(detalhes.get('tipo', 'entidade')).lower()
        nome = f"<strong>{escape(detalhes.get('nome', 'N/A'))}</strong>"
        message = f"{ator} criou a {tipo} {nome}."

    elif log.acao == 'ASSUNTO_CRIADO':
        assunto = f"<strong>{escape(detalhes.get('assunto', 'N/A'))}</strong>"
        disciplina = f"<strong>{escape(detalhes.get('disciplina', 'N/A'))}</strong>"
        message = f"{ator} criou o assunto {assunto} para a disciplina {disciplina}."

    # Mensagens para Notificações de Erro
    elif log.acao == 'NOTIFICACOES_RESOLVIDAS':
        count = detalhes.get('count', 0)
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        plural = 'notificação' if count == 1 else 'notificações'
        message = f"{ator} marcou {count} {plural} como resolvidas para a questão {codigo}."

    elif log.acao == 'NOTIFICACOES_REJEITADAS':
        count = detalhes.get('count', 0)
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        plural = 'notificação' if count == 1 else 'notificações'
        message = f"{ator} rejeitou {count} {plural} da questão {codigo}."

    elif log.acao == 'NOTIFICACOES_DELETADAS':
        count = detalhes.get('count', 0)
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        plural = 'notificação' if count == 1 else 'notificações'
        message = f"{ator} deletou {count} {plural} da questão {codigo}."
    
    elif log.acao == 'LOG_DELETADO':
        message = f"{ator} moveu um registro para a lixeira."
        
    else:
        acao = log.get_acao_display()
        message = f"{ator} realizou a ação: {acao.lower()}."
        
    return mark_safe(message)


@register.filter(name='format_log_reason')
def format_log_reason(details_dict):
    """
    Formata e exibe o 'motivo' ou 'justificativa' de um log, se existir.
    """
    if not isinstance(details_dict, dict):
        return ""
        
    motivo = details_dict.get('motivo')
    justificativa = details_dict.get('justificativa')

    content_to_display = None

    if justificativa:
        content_to_display = justificativa
    elif motivo:
        content_to_display = motivo
    
    if not content_to_display:
        return ""

    content_escaped = escape(content_to_display).strip()
    
    system_texts_to_remove = [
        "Confirmação final pelo solicitante (quorum = 1)",
        "Aprovação de solicitação de exclusão #"
    ]
    for text in system_texts_to_remove:
        if text in content_escaped:
            return ""

    if 'Justificativa:' in content_escaped:
        content_escaped = content_escaped.split('Justificativa:', 1)[1].strip()

    if 'Ação de exclusão em massa' == content_escaped:
        return mark_safe(f'<blockquote class="log-reason-quote">{content_escaped}</blockquote>')

    if not content_escaped:
        return ""

    html = f'<blockquote class="log-reason-quote">{content_escaped}</blockquote>'
    
    return mark_safe(html)