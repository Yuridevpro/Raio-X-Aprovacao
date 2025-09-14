# pratica/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import markdown
from django.db.models import Count, Q
from .models import Notificacao # Adicione a importação do novo modelo
from django.utils import formats # <-- 1. ADICIONE ESTA IMPORTAÇÃO
from django.utils.timezone import localtime # <-- 1. ADICIONE ESTA IMPORTAÇÃO
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
# Modelos
from questoes.models import Questao, Disciplina, Banca, Assunto, Instituicao
from .models import RespostaUsuario, Comentario, FiltroSalvo

# =======================================================================
# IMPORTAÇÃO DA NOSSA NOVA FUNÇÃO CENTRALIZADA
# =======================================================================
from questoes.utils import filtrar_e_paginar_questoes


# pratica/views.py


from questoes.utils import filtrar_e_paginar_questoes

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


# =======================================================================
# AS OUTRAS VIEWS PERMANECEM EXATAMENTE IGUAIS, POIS SÃO ÚNICAS DESTE APP
# A view 'get_assuntos_por_disciplina' foi removida, pois agora está em 'questoes/views.py'
# =======================================================================

@login_required
@require_POST
def verificar_resposta(request):
    try:
        data = json.loads(request.body)
        questao_id = data.get('questao_id')
        alternativa_selecionada = data.get('alternativa')
        questao = get_object_or_404(Questao, id=questao_id)
        correta = (alternativa_selecionada == questao.gabarito)
        RespostaUsuario.objects.update_or_create(
            usuario=request.user,
            questao=questao,
            defaults={'alternativa_selecionada': alternativa_selecionada, 'foi_correta': correta}
        )
        explicacao_html = markdown.markdown(questao.explicacao) if questao.explicacao else ""
        return JsonResponse({
            'status': 'success',
            'correta': correta,
            'gabarito': questao.gabarito,
            'explicacao': explicacao_html 
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
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
    questao = get_object_or_404(Questao, id=questao_id)
    sort_by = request.GET.get('sort_by', 'recent')

    comentarios_principais = questao.comentarios.filter(parent__isnull=True)

    if sort_by == 'likes':
        comentarios_qs = comentarios_principais.annotate(num_likes=Count('likes')).order_by('-num_likes', '-data_criacao')
    else:
        comentarios_qs = comentarios_principais.order_by('-data_criacao')

    def formatar_arvore_comentarios(comentario):
        respostas = comentario.respostas.all().order_by('data_criacao')
        respostas_formatadas = [formatar_arvore_comentarios(r) for r in respostas]

        # ===================================================================
        # INÍCIO DA CORREÇÃO
        # 1. Converte a data/hora do banco (UTC) para o fuso horário local.
        # ===================================================================
        data_local = localtime(comentario.data_criacao)
        # ===================================================================
        # FIM DA CORREÇÃO
        # ===================================================================

        return {
            'id': comentario.id,
            'usuario': comentario.usuario.userprofile.nome,
            'conteudo': markdown.markdown(comentario.conteudo),
            'conteudo_raw': comentario.conteudo,
            # 2. Usa a data/hora já convertida para formatar o texto em português.
            'data_criacao': formats.date_format(data_local, "d \\d\\e F \\d\\e Y \\à\\s H:i"),
            'pode_editar': comentario.usuario == request.user,
            'likes_count': comentario.likes.count(),
            'user_liked': request.user in comentario.likes.all(),
            'respostas': respostas_formatadas,
            'respostas_count': len(respostas_formatadas),
            'parent_id': comentario.parent_id
        }

    comentarios_data = [formatar_arvore_comentarios(c) for c in comentarios_qs]

    return JsonResponse({'comentarios': comentarios_data})



# pratica/views.py

# ... (outros imports e views) ...

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

                # =======================================================================
                # INÍCIO DA ADIÇÃO DE SEGURANÇA E INTEGRIDADE
                # =======================================================================
                # Verifica se o comentário pai realmente pertence à questão informada.
                # Isso impede que uma resposta seja criada em uma árvore de comentários de outra questão.
                if parent_comentario.questao_id != questao.id:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Inconsistência de dados detectada. A resposta não corresponde à questão principal.'
                    }, status=400) # 400 Bad Request é apropriado aqui.
                # =======================================================================
                # FIM DA ADIÇÃO
                # =======================================================================

                dados_novo_comentario['parent'] = parent_comentario
            except Comentario.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Comentário pai não encontrado.'}, status=404)
        
        novo_comentario = questao.comentarios.create(**dados_novo_comentario)

        return JsonResponse({
            'status': 'success',
            'comentario': {
                'id': novo_comentario.id,
                'usuario': novo_comentario.usuario.userprofile.nome,
                'conteudo': markdown.markdown(novo_comentario.conteudo),
                'conteudo_raw': novo_comentario.conteudo,
                'data_criacao': novo_comentario.data_criacao.strftime('%d de %B de %Y às %H:%M'),
                'pode_editar': True,
                'likes_count': 0,
                'user_liked': False,
                'respostas': [],
                'respostas_count': 0,
                'parent_id': novo_comentario.parent_id
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# ... (resto do arquivo pratica/views.py) ...

# --- INÍCIO DA NOVA VIEW PARA LIKE ---
@login_required
@require_POST
def toggle_like_comentario(request):
    try:
        data = json.loads(request.body)
        comentario_id = data.get('comentario_id')
        comentario = get_object_or_404(Comentario, id=comentario_id)
        user = request.user

        if user in comentario.likes.all():
            # Se já curtiu, remove o like
            comentario.likes.remove(user)
            liked = False
        else:
            # Se não curtiu, adiciona o like
            comentario.likes.add(user)
            liked = True

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

# pratica/views.py

# pratica/views.py

@login_required
def get_assuntos_por_disciplina(request):
    disciplina_ids = request.GET.getlist('disciplina_ids[]')
    if not disciplina_ids:
        return JsonResponse({'assuntos': []})

    # --- LINHA ALTERADA ---
    # Usamos .values() para pegar id, nome e o nome da disciplina relacionada
    # A ordenação garante que os grupos no frontend fiquem corretos.
    assuntos = Assunto.objects.filter(disciplina_id__in=disciplina_ids).values('id', 'nome', 'disciplina__nome').order_by('disciplina__nome', 'nome')
    
    return JsonResponse({'assuntos': list(assuntos)})

# pratica/views.py

from django.db import IntegrityError # Adicione esta importação
# ... (outras importações)

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