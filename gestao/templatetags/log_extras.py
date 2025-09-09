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
        'USUARIO_PROMOVIDO_SUPERUSER': 'fas fa-rocket text-warning',
        'USUARIO_DESPROMOVIDO_SUPERUSER': 'fas fa-user-minus text-secondary',
        
        # Ações de Solicitação de Exclusão
        'SOLICITACAO_EXCLUSAO_CRIADA': 'fas fa-user-clock text-warning',
        'SOLICITACAO_EXCLUSAO_APROVADA': 'fas fa-user-check text-success',
        'SOLICITACAO_EXCLUSAO_REJEITADA': 'fas fa-user-times text-danger',
        'SOLICITACAO_EXCLUSAO_CANCELADA': 'fas fa-ban text-secondary',
        
        # Ações de Questão
        'QUESTAO_CRIADA': 'fas fa-plus-circle text-success',
        'QUESTAO_EDITADA': 'fas fa-edit text-info',
        'QUESTAO_DELETADA': 'fas fa-trash-alt text-danger',

        # Ações de Entidades (Disciplina, Banca, etc.)
        'ENTIDADE_CRIADA': 'fas fa-folder-plus text-success',
        'ASSUNTO_CRIADO': 'fas fa-tag text-success',

        # Ações de Notificação de Erro
        'NOTIFICACOES_RESOLVIDAS': 'fas fa-check-double text-success',
        'NOTIFICACOES_REJEITADAS': 'fas fa-times-circle text-danger',
        'NOTIFICACOES_DELETADAS': 'fas fa-eraser text-danger',
    }
    return icon_map.get(log.acao, 'fas fa-info-circle text-muted')

@register.filter(name='generate_log_message')
def generate_log_message(log):
    """Gera uma mensagem principal descritiva e profissional para o log."""
    ator = f"<strong>{escape(log.ator.username if log.ator else 'Sistema')}</strong>"
    detalhes = log.detalhes
    
    # Mensagens para Ações de Usuário e Solicitações
    if log.acao == 'USUARIO_DELETADO':
        usuario = f"<strong>{escape(detalhes.get('usuario_deletado', 'N/A'))}</strong>"
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
        message = f"{ator} removeu as permissões de Superusuário do usuário {alvo}."
    
    # Mensagens para Ações de Questão
    elif log.acao == 'QUESTAO_CRIADA':
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        message = f"{ator} criou a questão {codigo}."

    elif log.acao == 'QUESTAO_EDITADA':
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        message = f"{ator} editou a questão {codigo}."

    elif log.acao == 'QUESTAO_DELETADA':
        codigo = f"<strong>{escape(detalhes.get('codigo_questao', 'N/A'))}</strong>"
        message = f"{ator} deletou a questão {codigo}."

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
        
    else:
        # Mensagem padrão caso a ação não tenha uma formatação customizada
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
    if not motivo:
        return ""
        
    motivo_escaped = escape(motivo)
    html = f'<blockquote class="log-reason-quote">{motivo_escaped}</blockquote>'
    
    return mark_safe(html)