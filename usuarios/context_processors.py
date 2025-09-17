# usuarios/context_processors.py

def avatar_equipado_processor(request):
    """
    Injeta as URLs do avatar e da borda equipados do usuário logado
    em todos os templates.
    """
    contexto = {
        'avatar_equipado_url': None,
        'borda_equipada_url': None,
    }
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        profile = request.user.userprofile
        if profile.avatar_equipado:
            contexto['avatar_equipado_url'] = profile.avatar_equipado.imagem.url
        # =======================================================================
        # ADIÇÃO: Inclui a URL da borda no contexto
        # =======================================================================
        if profile.borda_equipada:
            contexto['borda_equipada_url'] = profile.borda_equipada.imagem.url
            
    return contexto