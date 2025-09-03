# pratica/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

# Adicionado 'Assunto' ao import
from questoes.models import Questao, Disciplina, Banca, Assunto, Instituicao
from .models import RespostaUsuario, Comentario
import markdown
from .models import FiltroSalvo # ADICIONE ESTE IMPORT
# --- ADICIONE ESTES IMPORTS ---
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


@login_required
def listar_questoes(request):
    # Começa com todas as questões
    lista_questoes = Questao.objects.all().order_by('-id')

    # --- Lógica de Filtragem ---
    palavra_chave = request.GET.get('palavra_chave', '').strip()
    disciplinas_ids = request.GET.getlist('disciplina')
    assuntos_ids = request.GET.getlist('assunto')
    bancas_ids = request.GET.getlist('banca')
    instituicoes_ids = request.GET.getlist('instituicao')
    anos = request.GET.getlist('ano')
    status = request.GET.get('status')
    
    # Aplica os filtros de dropdown primeiro
    if disciplinas_ids:
        lista_questoes = lista_questoes.filter(disciplina_id__in=disciplinas_ids)
    if assuntos_ids:
        lista_questoes = lista_questoes.filter(assunto_id__in=assuntos_ids)
    if bancas_ids:
        lista_questoes = lista_questoes.filter(banca_id__in=bancas_ids)
    if instituicoes_ids:
        lista_questoes = lista_questoes.filter(instituicao_id__in=instituicoes_ids)
    if anos:
        lista_questoes = lista_questoes.filter(ano__in=anos)
    
    # Aplica o filtro de status
    user_profile = request.user.userprofile
    if status == 'favoritas':
        lista_questoes = lista_questoes.filter(pk__in=user_profile.questoes_favoritas.all())
    elif status == 'respondidas':
        respondidas_ids = RespostaUsuario.objects.filter(usuario=request.user).values_list('questao_id', flat=True)
        lista_questoes = lista_questoes.filter(pk__in=respondidas_ids)
    elif status == 'nao_respondidas':
        respondidas_ids = RespostaUsuario.objects.filter(usuario=request.user).values_list('questao_id', flat=True)
        lista_questoes = lista_questoes.exclude(pk__in=respondidas_ids)
    elif status == 'errei':
        erradas_ids = RespostaUsuario.objects.filter(usuario=request.user, foi_correta=False).values_list('questao_id', flat=True)
        lista_questoes = lista_questoes.filter(pk__in=erradas_ids)
    elif status == 'acertei':
        acertos_ids = RespostaUsuario.objects.filter(usuario=request.user, foi_correta=True).values_list('questao_id', flat=True)
        lista_questoes = lista_questoes.filter(pk__in=acertos_ids)
        
    # Por último, aplica o filtro de palavra-chave/código ao resultado já filtrado
    if palavra_chave:
        if palavra_chave.upper().startswith('Q') and palavra_chave[1:].isdigit():
            lista_questoes = lista_questoes.filter(codigo__iexact=palavra_chave)
        else:
            lista_questoes = lista_questoes.filter(enunciado__icontains=palavra_chave)
            
    # Flag para verificar se filtros foram aplicados (agora inclui palavra_chave)
    filters_applied = any([palavra_chave, disciplinas_ids, assuntos_ids, bancas_ids, instituicoes_ids, anos, status])

    # --- LÓGICA DE PAGINAÇÃO ---
    paginator = Paginator(lista_questoes, 25)
    
    if filters_applied:
        page_number = 1
    else:
        page_number = request.GET.get('page', 1)

    try:
        questoes_paginadas = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        questoes_paginadas = paginator.page(paginator.num_pages) if paginator.num_pages > 0 else paginator.page(1)
    
    # --- LÓGICA DE CUSTOMIZAÇÃO DA PAGINAÇÃO ---
    page_numbers = []
    current_page = questoes_paginadas.number
    total_pages = paginator.num_pages

    if total_pages <= 7:
        page_numbers = list(range(1, total_pages + 1))
    else:
        if current_page <= 4:
            page_numbers = list(range(1, 6)) + ['...', total_pages]
        elif current_page >= total_pages - 3:
            page_numbers = [1, '...'] + list(range(total_pages - 4, total_pages + 1))
        else:
            page_numbers = [1, '...', current_page - 1, current_page, current_page + 1, '...', total_pages]
    
    favoritas_ids = user_profile.questoes_favoritas.values_list('id', flat=True)
    filtros_salvos = FiltroSalvo.objects.filter(usuario=request.user)

    disciplinas = Disciplina.objects.all().order_by('nome')
    assuntos = Assunto.objects.all().order_by('nome')
    bancas = Banca.objects.all().order_by('nome')
    instituicoes = Instituicao.objects.all().order_by('nome')
    todos_anos = Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano')

    context = {
        'questoes': questoes_paginadas,
        'disciplinas': disciplinas,
        'assuntos': assuntos,
        'bancas': bancas,
        'instituicoes': instituicoes,
        'anos': todos_anos,
        'favoritas_ids': favoritas_ids,
        'selected_disciplinas': [int(i) for i in disciplinas_ids if i.isdigit()],
        'selected_assuntos': [int(i) for i in assuntos_ids if i.isdigit()],
        'selected_bancas': [int(i) for i in bancas_ids if i.isdigit()],
        'selected_instituicoes': [int(i) for i in instituicoes_ids if i.isdigit()],
        'selected_anos': [int(i) for i in anos if i.isdigit()],
        'filtros_salvos': filtros_salvos,
        'page_numbers': page_numbers,
        'palavra_chave_buscada': palavra_chave, # Adicionado para exibir a tag
    }
    return render(request, 'pratica/listar_questoes.html', context)

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
        
        # --- LINHA MODIFICADA ---
        # Agora, convertemos o markdown para HTML aqui, antes de enviar.
        explicacao_html = markdown.markdown(questao.explicacao) if questao.explicacao else ""
        
        return JsonResponse({
            'status': 'success',
            'correta': correta,
            'gabarito': questao.gabarito,
            # Enviamos o HTML já processado
            'explicacao': explicacao_html 
        })
        # --- FIM DA MODIFICAÇÃO ---

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
    comentarios = questao.comentarios.all().order_by('data_criacao') 
    
    comentarios_data = []
    for comentario in comentarios:
        comentarios_data.append({
            'id': comentario.id, # <--- ADICIONADO
            'usuario': comentario.usuario.userprofile.nome,
            'conteudo': markdown.markdown(comentario.conteudo),
            'conteudo_raw': comentario.conteudo, # <--- ADICIONADO (para edição)
            'data_criacao': comentario.data_criacao.strftime('%d de %B de %Y às %H:%M'),
            'pode_editar': comentario.usuario == request.user # <--- ADICIONADO
        })
    return JsonResponse({'comentarios': comentarios_data})

# pratica/views.py

# pratica/views.py - CÓDIGO CORRIGIDO

@login_required
@require_POST
def adicionar_comentario(request):
    try:
        data = json.loads(request.body)
        questao_id = data.get('questao_id')
        conteudo = data.get('conteudo')

        if not conteudo or not conteudo.strip():
            return JsonResponse({'status': 'error', 'message': 'O comentário não pode estar vazio.'}, status=400)

        questao = get_object_or_404(Questao, id=questao_id)
        
        # --- LINHA CORRIGIDA ---
        # Removemos o argumento 'questao=questao' pois o Django já sabe a qual
        # questão o comentário pertence ao usar o related manager 'questao.comentarios'.
        novo_comentario = questao.comentarios.create(
            usuario=request.user,
            conteudo=conteudo
        )
        # --- FIM DA CORREÇÃO ---

        return JsonResponse({
            'status': 'success',
            'comentario': {
                'id': novo_comentario.id,
                'usuario': novo_comentario.usuario.userprofile.nome,
                'conteudo': markdown.markdown(novo_comentario.conteudo),
                'conteudo_raw': novo_comentario.conteudo,
                'data_criacao': novo_comentario.data_criacao.strftime('%d de %B de %Y às %H:%M'),
                'pode_editar': True
            }
        })

    except Exception as e:
        # É uma boa prática logar o erro no servidor para facilitar a depuração
        # import logging
        # logging.error(f"Erro ao adicionar comentário: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def get_assuntos_por_disciplina(request):
    # Pega a lista de IDs de disciplinas da requisição GET
    disciplina_ids = request.GET.getlist('disciplina_ids[]')
    
    if not disciplina_ids:
        return JsonResponse({'assuntos': []})

    # Filtra os assuntos que pertencem a qualquer uma das disciplinas selecionadas
    assuntos = Assunto.objects.filter(disciplina_id__in=disciplina_ids).values('id', 'nome').order_by('nome')
    
    # Converte o QuerySet para uma lista e retorna como JSON
    return JsonResponse({'assuntos': list(assuntos)})

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