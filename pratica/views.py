# pratica/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import markdown
from django.db.models import Count, Q
from django.utils import formats
from django.utils.timezone import localtime
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType

# Modelos
from questoes.models import Questao, Disciplina, Banca, Assunto, Instituicao
from .models import RespostaUsuario, Comentario, FiltroSalvo, Notificacao
from usuarios.models import UserProfile # Importação correta do UserProfile

# Serviços e Funções
from gamificacao.services import processar_resposta_gamificacao, _avaliar_e_conceder_recompensas
from questoes.utils import filtrar_e_paginar_questoes
from gamificacao.models import Campanha


@login_required
def listar_questoes(request):
    # 1. Começa com o queryset base.
    lista_questoes = Questao.objects.all()
    user = request.user
    user_profile = user.userprofile

    # =======================================================================
    # INÍCIO DA CORREÇÃO: Lógica completa de filtro por status
    # =======================================================================
    status = request.GET.get('status')
    
    # Obtém os IDs das questões que o usuário já respondeu
    respostas_usuario_pks = RespostaUsuario.objects.filter(usuario=user).values_list('questao__pk', flat=True)

    if status == 'respondidas':
        lista_questoes = lista_questoes.filter(pk__in=respostas_usuario_pks)
    elif status == 'nao_respondidas':
        lista_questoes = lista_questoes.exclude(pk__in=respostas_usuario_pks)
    elif status == 'acertei':
        respostas_corretas_pks = RespostaUsuario.objects.filter(usuario=user, foi_correta=True).values_list('questao__pk', flat=True)
        lista_questoes = lista_questoes.filter(pk__in=respostas_corretas_pks)
    elif status == 'errei':
        respostas_incorretas_pks = RespostaUsuario.objects.filter(usuario=user, foi_correta=False).values_list('questao__pk', flat=True)
        lista_questoes = lista_questoes.filter(pk__in=respostas_incorretas_pks)
    elif status == 'favoritas':
        lista_questoes = lista_questoes.filter(pk__in=user_profile.questoes_favoritas.all())
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================

    # Lógica de Ordenação
    sort_by = request.GET.get('sort_by', '-id')
    sort_options = {
        '-id': 'Mais Recentes',
        'id': 'Mais Antigas',
    }
    
    if sort_by in sort_options:
        lista_questoes = lista_questoes.order_by(sort_by)

    # Chama a função de filtro e paginação
    context = filtrar_e_paginar_questoes(request, lista_questoes, items_per_page=20)
    
    # Adiciona ao contexto as variáveis específicas desta página
    context.update({
        'favoritas_ids': user_profile.questoes_favoritas.values_list('id', flat=True),
        'filtros_salvos': FiltroSalvo.objects.filter(usuario=request.user),
        'disciplinas': Disciplina.objects.all().order_by('nome'),
        'bancas': Banca.objects.all().order_by('nome'),
        'instituicoes': Instituicao.objects.all().order_by('nome'),
        'anos': Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano'),
        'status_param': status,
        'sort_by': sort_by,
        'sort_options': sort_options,
    })

    return render(request, 'pratica/listar_questoes.html', context)


@login_required
@require_POST
def verificar_resposta(request):
    try:
        data = json.loads(request.body)
        questao_id = data.get('questao_id')
        alternativa_selecionada = data.get('alternativa')
        
        if not questao_id or not alternativa_selecionada:
            return JsonResponse({'status': 'error', 'message': "Dados incompletos."}, status=400)
            
        questao = get_object_or_404(Questao, id=questao_id)
        
        gamificacao_eventos = processar_resposta_gamificacao(
            user=request.user, 
            questao=questao, 
            alternativa_selecionada=alternativa_selecionada
        )
        
        nova_conquista_data = None
        if gamificacao_eventos.get('nova_conquista'):
            conquista = gamificacao_eventos['nova_conquista']
            nova_conquista_data = {'nome': conquista.nome, 'icone': conquista.icone, 'cor': conquista.cor}

        explicacao_html = markdown.markdown(questao.explicacao) if questao.explicacao else ""
        
        return JsonResponse({
            'status': 'success',
            'correta': gamificacao_eventos.get('correta'),
            'gabarito': gamificacao_eventos.get('gabarito'),
            'explicacao': explicacao_html,
            'nova_conquista': nova_conquista_data,
            'level_up_info': gamificacao_eventos.get('level_up_info'),
            'meta_completa_info': gamificacao_eventos.get('meta_completa_info'),
            'xp_ganho': gamificacao_eventos.get('xp_ganho', 0),
            'bonus_ativo': gamificacao_eventos.get('bonus_ativo', False),
            'motivo_bloqueio': gamificacao_eventos.get('motivo_bloqueio') # <-- LINHA ADICIONADA
        })
    except Exception as e:
        print(f"Erro inesperado em verificar_resposta: {e}")
        return JsonResponse({'status': 'error', 'message': "Ocorreu um erro interno."}, status=500)

@login_required
@require_POST
def favoritar_questao(request):
    try:
        data = json.loads(request.body)
        questao_id = data.get('questao_id')
        questao = get_object_or_404(Questao, id=questao_id)
        user_profile = request.user.userprofile
        if questao in user_profile.questoes_favoritas.all():
            user_profile.questoes_favoritas.remove(questao)
            favorita = False
        else:
            user_profile.questoes_favoritas.add(questao)
            favorita = True
        return JsonResponse({'status': 'success', 'favorita': favorita})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def carregar_comentarios(request, questao_id):
    """
    Carrega todos os comentários de uma questão, incluindo as respostas aninhadas,
    e os retorna em formato JSON para serem renderizados dinamicamente no front-end.
    """
    questao = get_object_or_404(Questao, id=questao_id)
    sort_by = request.GET.get('sort_by', 'recent')

    # Filtra apenas os comentários principais (que não são respostas a outros)
    comentarios_principais = questao.comentarios.filter(parent__isnull=True)

    # Aplica a ordenação solicitada
    if sort_by == 'likes':
        comentarios_qs = comentarios_principais.annotate(num_likes=Count('likes')).order_by('-num_likes', '-data_criacao')
    else: # 'recent' é o padrão
        comentarios_qs = comentarios_principais.order_by('-data_criacao')

    def formatar_arvore_comentarios(comentario):
        """
        Função recursiva que formata um comentário e todas as suas respostas
        em uma estrutura de dicionário aninhada.
        """
        # Busca e formata as respostas deste comentário
        respostas = comentario.respostas.all().order_by('data_criacao')
        respostas_formatadas = [formatar_arvore_comentarios(r) for r in respostas]

        # Converte a data/hora do banco (UTC) para o fuso horário local
        data_local = localtime(comentario.data_criacao)
        
        # ===================================================================
        # LÓGICA PARA BUSCAR AVATAR E BORDA EQUIPADOS
        # ===================================================================
        avatar_url = None
        borda_url = None
        # Usamos hasattr como uma verificação de segurança
        if hasattr(comentario.usuario, 'userprofile'):
            profile = comentario.usuario.userprofile
            if profile.avatar_equipado:
                avatar_url = profile.avatar_equipado.imagem.url
            if profile.borda_equipada:
                borda_url = profile.borda_equipada.imagem.url
        # ===================================================================

        return {
            'id': comentario.id,
            'usuario': comentario.usuario.userprofile.nome,
            # ===============================================================
            # PASSANDO AS NOVAS URLS PARA O JSON
            # ===============================================================
            'usuario_avatar_url': avatar_url,
            'usuario_borda_url': borda_url,
            'conteudo': markdown.markdown(comentario.conteudo),
            'conteudo_raw': comentario.conteudo,
            'data_criacao': formats.date_format(data_local, "d \\d\\e F \\d\\e Y \\à\\s H:i"),
            'pode_editar': comentario.usuario == request.user,
            'likes_count': comentario.likes.count(),
            'user_liked': request.user in comentario.likes.all(),
            'respostas': respostas_formatadas,
            'respostas_count': len(respostas_formatadas),
            'parent_id': comentario.parent_id
        }

    # Itera sobre os comentários principais para construir a árvore de dados
    comentarios_data = [formatar_arvore_comentarios(c) for c in comentarios_qs]

    return JsonResponse({'comentarios': comentarios_data})

@login_required
@require_POST
def adicionar_comentario(request):
    try:
        data = json.loads(request.body)
        questao_id = data.get('questao_id')
        conteudo = data.get('conteudo')
        parent_id = data.get('parent_id')

        if not conteudo or not conteudo.strip():
            return JsonResponse({'status': 'error', 'message': 'O comentário não pode estar vazio.'}, status=400)

        questao = get_object_or_404(Questao, id=questao_id)
        
        dados_novo_comentario = {
            'usuario': request.user,
            'conteudo': conteudo
        }

        if parent_id:
            try:
                parent_comentario = Comentario.objects.get(id=parent_id)
                if parent_comentario.questao_id != questao.id:
                    return JsonResponse({'status': 'error', 'message': 'Inconsistência de dados detectada.'}, status=400)
                dados_novo_comentario['parent'] = parent_comentario
            except Comentario.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Comentário pai não encontrado.'}, status=404)
        
        novo_comentario = questao.comentarios.create(**dados_novo_comentario)

        # =======================================================================
        # INÍCIO DA ADIÇÃO: Dispara o gatilho de Campanha para comentários
        # =======================================================================
        # O gatilho só é acionado para comentários principais, não para respostas.
        if not novo_comentario.parent:
            _avaliar_e_conceder_recompensas(
                request.user.userprofile, 
                Campanha.Gatilho.COMENTARIO_PUBLICADO, 
                contexto={'comentario_id': novo_comentario.id, 'questao_id': questao_id}
            )
        # =======================================================================
        # FIM DA ADIÇÃO
        # =======================================================================

        return JsonResponse({
            'status': 'success',
            'comentario': {
                'id': novo_comentario.id,
                'usuario': novo_comentario.usuario.userprofile.nome,
                'conteudo': markdown.markdown(novo_comentario.conteudo),
                'conteudo_raw': novo_comentario.conteudo,
                'data_criacao': novo_comentario.data_criacao.strftime('%d de %B de %Y às %H:%M'),
                'pode_editar': True, 'likes_count': 0, 'user_liked': False,
                'respostas': [], 'respostas_count': 0, 'parent_id': novo_comentario.parent_id
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def toggle_like_comentario(request):
    try:
        data = json.loads(request.body)
        comentario_id = data.get('comentario_id')
        comentario = get_object_or_404(Comentario, id=comentario_id)
        user = request.user

        if user in comentario.likes.all():
            comentario.likes.remove(user)
            liked = False
        else:
            comentario.likes.add(user)
            liked = True

            # ===================================================================
            # INÍCIO DA ADIÇÃO: Dispara o gatilho de Campanha ao dar um like
            # ===================================================================
            _avaliar_e_conceder_recompensas(
                request.user.userprofile, 
                Campanha.Gatilho.LIKE_EM_COMENTARIO_CONCEDIDO, 
                contexto={'comentario_id': comentario.id}
            )
            # ===================================================================
            # FIM DA ADIÇÃO
            # ===================================================================

        return JsonResponse({
            'status': 'success',
            'liked': liked,
            'likes_count': comentario.likes.count()
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)



@login_required
@require_POST
def editar_comentario(request):
    try:
        data = json.loads(request.body)
        comentario_id = data.get('comentario_id')
        novo_conteudo = data.get('conteudo')

        comentario = get_object_or_404(Comentario, id=comentario_id)

        # Verifica se o usuário logado é o dono do comentário
        if comentario.usuario != request.user:
            return JsonResponse({'status': 'error', 'message': 'Você não tem permissão para editar este comentário.'}, status=403)
        
        comentario.conteudo = novo_conteudo
        comentario.save()

        return JsonResponse({
            'status': 'success',
            # Retorna o novo conteúdo já convertido para HTML
            'conteudo_html': markdown.markdown(novo_conteudo)
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def excluir_comentario(request):
    try:
        data = json.loads(request.body)
        comentario_id = data.get('comentario_id')
        
        comentario = get_object_or_404(Comentario, id=comentario_id)

        # Verifica se o usuário logado é o dono do comentário
        if comentario.usuario != request.user:
            return JsonResponse({'status': 'error', 'message': 'Você não tem permissão para excluir este comentário.'}, status=403)
            
        comentario.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def salvar_filtro(request):
    try:
        data = json.loads(request.body)
        nome_filtro = data.get('nome')
        parametros_url = data.get('parametros')

        if not nome_filtro or not parametros_url:
            return JsonResponse({'status': 'error', 'message': 'Nome e parâmetros são obrigatórios.'}, status=400)

        # Usamos update_or_create para que o usuário possa sobrescrever um filtro com o mesmo nome
        filtro, created = FiltroSalvo.objects.update_or_create(
            usuario=request.user,
            nome=nome_filtro,
            defaults={'parametros_url': parametros_url}
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Filtro salvo com sucesso!',
            'filtro': {
                'id': filtro.id,
                'nome': filtro.nome,
                'parametros': filtro.parametros_url
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def deletar_filtro(request):
    try:
        data = json.loads(request.body)
        filtro_id = data.get('filtro_id')
        
        filtro = get_object_or_404(FiltroSalvo, id=filtro_id, usuario=request.user)
        filtro.delete()
        
        return JsonResponse({'status': 'success', 'message': 'Filtro deletado com sucesso!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def notificar_erro(request):
    try:
        data = json.loads(request.body)
        # =======================================================================
        # INÍCIO DA MODIFICAÇÃO: Generalizando a view
        # =======================================================================
        tipo_alvo = data.get('tipo_alvo') # 'questao' ou 'comentario'
        alvo_id = data.get('alvo_id')
        tipo_erro = data.get('tipo_erro')
        descricao = data.get('descricao')

        if not all([tipo_alvo, alvo_id, tipo_erro, descricao]):
            return JsonResponse({'status': 'error', 'message': 'Todos os campos são obrigatórios.'}, status=400)

        Model = None
        if tipo_alvo == 'questao':
            Model = Questao
        elif tipo_alvo == 'comentario':
            Model = Comentario
        
        if not Model:
            return JsonResponse({'status': 'error', 'message': 'Tipo de alvo inválido.'}, status=400)

        alvo = get_object_or_404(Model, id=alvo_id)
        # =======================================================================
        # FIM DA MODIFICAÇÃO
        # =======================================================================

        try:
            Notificacao.objects.create(
                alvo=alvo, # Agora usa a relação genérica
                usuario_reportou=request.user,
                tipo_erro=tipo_erro,
                descricao=descricao
            )
            return JsonResponse({'status': 'success', 'message': 'Obrigado! Sua notificação foi enviada e será analisada pela nossa equipe.'})
        
        except IntegrityError:
            return JsonResponse({
                'status': 'error', 
                'message': 'Você já possui uma notificação ativa para este item. Nossa equipe já está ciente e analisará em breve.'
            }, status=409)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)