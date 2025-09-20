# usuarios/context_processors.py (função alterada)

def avatar_equipado_processor(request):
    """
    Injeta as URLs do avatar/borda, saldo de moedas e contagem de
    prêmios pendentes do usuário logado em todos os templates.
    """
    contexto = {
        'avatar_equipado_url': None,
        'borda_equipada_url': None,
        'saldo_moedas_usuario': 0,
        'recompensas_pendentes_count': 0, # Valor padrão
    }
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        profile = request.user.userprofile
        if profile.avatar_equipado:
            contexto['avatar_equipado_url'] = profile.avatar_equipado.imagem.url
        if profile.borda_equipada:
            contexto['borda_equipada_url'] = profile.borda_equipada.imagem.url
        
        if hasattr(profile, 'gamificacao_data'):
            contexto['saldo_moedas_usuario'] = profile.gamificacao_data.moedas

        # Conta as recompensas pendentes
        contexto['recompensas_pendentes_count'] = profile.recompensas_pendentes.filter(resgatado_em__isnull=True).count()
            
    return contexto