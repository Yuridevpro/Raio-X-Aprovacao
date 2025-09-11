# gestao/views.py

# =======================================================================
# BLOCO DE IMPORTAÇÕES
# =======================================================================

# Importações do Django Core
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Count, Max, Prefetch, Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from datetime import datetime, timedelta
import json
import markdown

# Importações de modelos de outros apps
from pratica.models import Notificacao
from questoes.models import Questao, Disciplina, Banca, Instituicao, Assunto

# Importações de forms de outros apps
from questoes.forms import GestaoQuestaoForm, EntidadeSimplesForm, AssuntoForm

# Importações de utils de outros apps
from usuarios.utils import enviar_email_com_template
from questoes.utils import paginar_itens, filtrar_e_paginar_questoes, filtrar_e_paginar_lixeira

# Importações locais do app 'gestao'
from .models import SolicitacaoExclusao, PromocaoSuperuser, LogAtividade, DespromocaoSuperuser, ExclusaoSuperuser
from .forms import StaffUserForm, ExclusaoUsuarioForm
from .utils import criar_log


# =======================================================================
# FUNÇÕES AUXILIARES DE VERIFICAÇÃO DE PERMISSÃO
# =======================================================================

def is_superuser(user):
    """Verifica se o usuário é um superusuário."""
    return user.is_superuser

def is_staff_member(user):
    """Verifica se o usuário é um membro da equipe (staff)."""
    return user.is_staff

# =======================================================================
# BLOKO 1: VIEWS PRINCIPAIS DO PAINEL DE GESTÃO
# =======================================================================

@user_passes_test(is_staff_member)
@login_required
def dashboard_gestao(request):
    """
    Renderiza a página principal do painel de gestão com estatísticas gerais.
    Acessível por todos os membros da equipe (staff e superusers).
    """
    # Contagens gerais para todos os membros da equipe
    total_questoes = Questao.objects.count()
    notificacoes_pendentes = Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count()
    solicitacoes_pendentes_count = SolicitacaoExclusao.objects.filter(status=SolicitacaoExclusao.Status.PENDENTE).count()
    
    # Contagens específicas para superusuários (inicializadas com 0)
    promocoes_pendentes_count = 0
    despromocoes_pendentes_count = 0
    exclusoes_superuser_pendentes_count = 0

    # Se o usuário for superuser, obtém as contagens adicionais
    if request.user.is_superuser:
        promocoes_pendentes_count = PromocaoSuperuser.objects.filter(status=PromocaoSuperuser.Status.PENDENTE).count()
        despromocoes_pendentes_count = DespromocaoSuperuser.objects.filter(status=DespromocaoSuperuser.Status.PENDENTE).count()
        exclusoes_superuser_pendentes_count = ExclusaoSuperuser.objects.filter(status=ExclusaoSuperuser.Status.PENDENTE).count()

    context = {
        'total_questoes': total_questoes,
        'notificacoes_pendentes': notificacoes_pendentes,
        'solicitacoes_pendentes_count': solicitacoes_pendentes_count,
        'promocoes_pendentes_count': promocoes_pendentes_count,
        'despromocoes_pendentes_count': despromocoes_pendentes_count,
        'exclusoes_superuser_pendentes_count': exclusoes_superuser_pendentes_count,
    }
    return render(request, 'gestao/dashboard.html', context)


# =======================================================================
# BLOKO 2: GERENCIAMENTO DE QUESTÕES (CRUD E LIXEIRA)
# =======================================================================

@user_passes_test(is_staff_member)
@login_required
def listar_questoes_gestao(request):
    """
    Lista, filtra e ordena todas as questões ativas (não deletadas).
    Fornece a interface principal para gerenciamento de questões.
    """
    lista_questoes = Questao.objects.all() # O manager padrão já filtra is_deleted=False
    sort_by = request.GET.get('sort_by', '-id')
    sort_options = {
        '-id': 'Mais Recentes', 'id': 'Mais Antigas',
        'disciplina__nome': 'Disciplina (A-Z)', '-ano': 'Ano (Decrescente)', 'ano': 'Ano (Crescente)',
    }
    if sort_by in sort_options:
        lista_questoes = lista_questoes.order_by(sort_by)

    # Função utilitária para aplicar filtros de GET e paginar os resultados
    context = filtrar_e_paginar_questoes(request, lista_questoes, items_per_page=20)
    
    # Contagem de itens na lixeira para exibir no botão da interface
    lixeira_count = Questao.all_objects.filter(is_deleted=True).count()

    # Adiciona dados adicionais ao contexto para os filtros e formulários
    context.update({
        'sort_by': sort_by,
        'sort_options': sort_options,
        'disciplinas_para_filtro': Disciplina.objects.all().order_by('nome'),
        'disciplinas': Disciplina.objects.all().order_by('nome'),
        'bancas': Banca.objects.all().order_by('nome'),
        'instituicoes': Instituicao.objects.all().order_by('nome'),
        'anos': Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano'),
        'entidade_simples_form': EntidadeSimplesForm(),
        'assunto_form': AssuntoForm(),
        'lixeira_count': lixeira_count,
    })
    
    return render(request, 'gestao/listar_questoes.html', context)

@user_passes_test(is_staff_member)
@login_required
def adicionar_questao(request):
    """
    Renderiza e processa o formulário para adicionar uma nova questão.
    Métodos: GET (exibe form), POST (processa form).
    """
    if request.method == 'POST':
        form = GestaoQuestaoForm(request.POST, request.FILES)
        if form.is_valid():
            questao = form.save(commit=False)
            questao.criada_por = request.user
            questao.save()
            criar_log(ator=request.user, acao=LogAtividade.Acao.QUESTAO_CRIADA, alvo=questao, detalhes={'codigo_questao': questao.codigo})
            messages.success(request, 'Questão adicionada com sucesso!')
            return redirect('gestao:listar_questoes')
    else:
        form = GestaoQuestaoForm()
    context = {'form': form, 'titulo': 'Adicionar Nova Questão'}
    return render(request, 'gestao/form_questao.html', context)

@user_passes_test(is_staff_member)
@login_required
def editar_questao(request, questao_id):
    """
    Renderiza e processa o formulário para editar uma questão existente.
    Métodos: GET (exibe form), POST (processa form).
    """
    questao = get_object_or_404(Questao, id=questao_id)
    if request.method == 'POST':
        form = GestaoQuestaoForm(request.POST, request.FILES, instance=questao)
        if form.is_valid():
            form.save()
            criar_log(ator=request.user, acao=LogAtividade.Acao.QUESTAO_EDITADA, alvo=questao, detalhes={'codigo_questao': questao.codigo})
            messages.success(request, 'Questão atualizada com sucesso!')
            return redirect('gestao:listar_questoes')
    else:
        form = GestaoQuestaoForm(instance=questao)
    context = {'form': form, 'titulo': f'Editar Questão ({questao.codigo})'}
    return render(request, 'gestao/form_questao.html', context)

@user_passes_test(is_staff_member)
@login_required
@require_POST
def deletar_questao(request, questao_id):
    """
    Executa um "soft delete" em uma questão, movendo-a para a lixeira.
    Acessível via requisição POST (AJAX).
    """
    questao = get_object_or_404(Questao, id=questao_id)
    try:
        questao_codigo = questao.codigo
        questao.delete(user=request.user) # Chama o método de soft delete do modelo
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.QUESTAO_DELETADA, 
            alvo=None, # O alvo não é mais visível pelo manager padrão
            detalhes={'codigo_questao': questao_codigo}
        )
        return JsonResponse({
            'status': 'success',
            'message': f'A questão "{questao_codigo}" foi movida para a lixeira.',
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Erro: {str(e)}'}, status=500)

@user_passes_test(is_staff_member)
@login_required
@require_POST
@ratelimit(key='user', rate='5/10m', block=True)
@transaction.atomic
def questoes_acoes_em_massa(request):
    """
    Processa ações em massa para questões ativas (atualmente, apenas soft delete).
    Acessível via requisição POST (AJAX) com um corpo JSON.
    Possui proteção contra excesso de volume.
    """
    try:
        data = json.loads(request.body)
        questao_ids = data.get('ids', [])
        action = data.get('action')

        # Proteção para evitar a exclusão de um número excessivo de itens de uma só vez
        LIMITE_MAXIMO_POR_ACAO = 15
        if len(questao_ids) > LIMITE_MAXIMO_POR_ACAO:
            criar_log(
                ator=request.user,
                acao=LogAtividade.Acao.TENTATIVA_EXCLUSAO_MASSA_EXCEDIDA,
                detalhes={'quantidade_tentada': len(questao_ids), 'limite': LIMITE_MAXIMO_POR_ACAO, 'acao': 'mover para lixeira'}
            )
            return JsonResponse({'status': 'error', 'message': f'Ação bloqueada: O limite de itens por operação é de {LIMITE_MAXIMO_POR_ACAO}.'}, status=403)

        if not questao_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)
        
        queryset = Questao.objects.filter(id__in=questao_ids)
        if action == 'delete':
            count = queryset.count()
            for questao in queryset:
                questao.delete(user=request.user) # Soft delete
            
            criar_log(ator=request.user, acao=LogAtividade.Acao.QUESTAO_DELETADA, alvo=None, detalhes={'count': count, 'motivo': 'Ação de exclusão em massa'})
            return JsonResponse({'status': 'success', 'message': f'{count} questões foram movidas para a lixeira.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@user_passes_test(is_staff_member)
@login_required
def listar_questoes_deletadas(request):
    """
    Lista, filtra e ordena as questões que estão na lixeira (is_deleted=True).
    """
    # Usa o manager `all_objects` para incluir as questões com soft delete
    base_queryset = Questao.all_objects.filter(is_deleted=True).select_related(
        'disciplina', 'assunto', 'banca', 'instituicao', 'deleted_by'
    )
    
    sort_by = request.GET.get('sort_by', '-deleted_at')
    sort_options = {
        '-deleted_at': 'Exclusão Mais Recente',
        'deleted_at': 'Exclusão Mais Antiga',
        'disciplina__nome': 'Disciplina (A-Z)',
    }
    if sort_by in sort_options:
        base_queryset = base_queryset.order_by(sort_by)

    # Função utilitária específica para filtrar e paginar a lixeira
    context = filtrar_e_paginar_lixeira(request, base_queryset, items_per_page=20)
    
    # Gera opções de filtro baseadas apenas nas questões que estão na lixeira
    deleted_questoes_ids = base_queryset.values_list('id', flat=True)
    
    context.update({
        'sort_by': sort_by,
        'sort_options': sort_options,
        'disciplinas_para_filtro': Disciplina.objects.filter(questao__id__in=deleted_questoes_ids).distinct().order_by('nome'),
        'bancas_para_filtro': Banca.objects.filter(questao__id__in=deleted_questoes_ids).distinct().order_by('nome'),
        'instituicoes_para_filtro': Instituicao.objects.filter(questao__id__in=deleted_questoes_ids).distinct().order_by('nome'),
        'anos_para_filtro': Questao.all_objects.filter(id__in=deleted_questoes_ids).exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano'),
    })
    
    return render(request, 'gestao/listar_questoes_deletadas.html', context)

@user_passes_test(is_staff_member)
@login_required
@require_POST
def restaurar_questao(request, questao_id):
    """
    Restaura uma questão da lixeira, tornando-a ativa novamente.
    Acessível via requisição POST (AJAX).
    """
    questao = get_object_or_404(Questao.all_objects, id=questao_id, is_deleted=True)
    try:
        questao_codigo = questao.codigo
        questao.restore() # Chama o método de restauração do modelo
        
        criar_log(ator=request.user, acao=LogAtividade.Acao.QUESTAO_RESTAURADA, alvo=questao, detalhes={'codigo_questao': questao_codigo})
        return JsonResponse({'status': 'success', 'message': f'A questão "{questao_codigo}" foi restaurada com sucesso.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Erro: {str(e)}'}, status=500)

@user_passes_test(is_superuser)
@login_required
@require_POST
def deletar_questao_permanente(request, questao_id):
    """
    Exclui permanentemente uma questão do banco de dados.
    Ação restrita a superusuários e com validação de tempo mínimo na lixeira.
    Acessível via requisição POST (AJAX).
    """
    questao = get_object_or_404(Questao.all_objects, id=questao_id, is_deleted=True)
    
    # Validação de segurança no backend para garantir a regra de tempo na lixeira
    if not questao.is_permanently_deletable:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: A questão ainda não completou 20 dias na lixeira.'}, status=403)

    try:
        questao_codigo = questao.codigo
        questao.hard_delete() # Chama a exclusão permanente
        
        criar_log(ator=request.user, acao=LogAtividade.Acao.QUESTAO_DELETADA_PERMANENTEMENTE, alvo=None, detalhes={'codigo_questao': questao_codigo})
        return JsonResponse({'status': 'success', 'message': f'A questão "{questao_codigo}" foi excluída PERMANENTEMENTE.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Erro: {str(e)}'}, status=500)

@user_passes_test(is_staff_member)
@login_required
@require_POST
@ratelimit(key='user', rate='5/10m', block=True)
@transaction.atomic
def questoes_deletadas_acoes_em_massa(request):
    """
    Processa ações em massa para questões na lixeira (restaurar ou deletar permanente).
    Acessível via requisição POST (AJAX) com um corpo JSON.
    Ação de deletar permanentemente é restrita a superusuários.
    """
    try:
        data = json.loads(request.body)
        questao_ids = data.get('ids', [])
        action = data.get('action')

        LIMITE_MAXIMO_POR_ACAO = 100
        if len(questao_ids) > LIMITE_MAXIMO_POR_ACAO:
            # Loga a tentativa de exceder o limite
            criar_log(ator=request.user, acao=LogAtividade.Acao.TENTATIVA_EXCLUSAO_MASSA_EXCEDIDA, detalhes={'quantidade_tentada': len(questao_ids), 'limite': LIMITE_MAXIMO_POR_ACAO, 'acao': action})
            return JsonResponse({'status': 'error', 'message': f'Ação bloqueada: O limite de itens por operação é de {LIMITE_MAXIMO_POR_ACAO}.'}, status=403)

        if not questao_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)
        
        queryset = Questao.all_objects.filter(id__in=questao_ids, is_deleted=True)
        count = queryset.count()

        if action == 'restore':
            for questao in queryset:
                questao.restore()
                criar_log(ator=request.user, acao=LogAtividade.Acao.QUESTAO_RESTAURADA, alvo=questao, detalhes={'codigo_questao': questao.codigo, 'motivo': 'Ação em massa'})
            return JsonResponse({'status': 'success', 'message': f'{count} questões foram restauradas.'})

        elif action == 'delete_permanently':
            if not request.user.is_superuser:
                return JsonResponse({'status': 'error', 'message': 'Você não tem permissão para esta ação.'}, status=403)
            
            # Validação de segurança no backend para cada questão
            for questao in queryset:
                if not questao.is_permanently_deletable:
                    return JsonResponse({'status': 'error', 'message': f'Ação negada: A questão {questao.codigo} ainda não completou 20 dias na lixeira.'}, status=403)

            for questao in queryset:
                criar_log(ator=request.user, acao=LogAtividade.Acao.QUESTAO_DELETADA_PERMANENTEMENTE, alvo=None, detalhes={'codigo_questao': questao.codigo, 'motivo': 'Ação em massa'})
            
            queryset.delete() # Hard delete em massa
            return JsonResponse({'status': 'success', 'message': f'{count} questões foram excluídas permanentemente.'})

        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =======================================================================
# BLOKO 3: VIEWS DE API (ENTIDADES AUXILIARES)
# =======================================================================

@user_passes_test(is_staff_member)
@login_required
@require_POST
def adicionar_entidade_simples(request):
    """
    Cria uma nova entidade simples (Disciplina, Banca, Instituição) via AJAX.
    Usada nos modais da página de listagem de questões.
    """
    form = EntidadeSimplesForm(request.POST)
    if form.is_valid():
        nome = form.cleaned_data['nome']
        tipo_entidade = request.POST.get('tipo_entidade')
        ModelMap = {'disciplina': Disciplina, 'banca': Banca, 'instituicao': Instituicao}
        Model = ModelMap.get(tipo_entidade)

        if not Model or Model.objects.filter(nome__iexact=nome).exists():
            message = 'Tipo de entidade inválido.' if not Model else 'Já existe um item com este nome.'
            return JsonResponse({'status': 'error', 'message': message}, status=400)
        
        entidade = Model.objects.create(nome=nome)
        criar_log(ator=request.user, acao=LogAtividade.Acao.ENTIDADE_CRIADA, alvo=entidade, detalhes={'tipo': tipo_entidade.capitalize(), 'nome': entidade.nome})
        return JsonResponse({'status': 'success', 'entidade': {'id': entidade.id, 'nome': entidade.nome}})
    return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)

@user_passes_test(is_staff_member)
@login_required
@require_POST
def adicionar_assunto(request):
    """
    Cria um novo Assunto via AJAX, associado a uma Disciplina.
    Usada nos modais da página de listagem de questões.
    """
    form = AssuntoForm(request.POST)
    if form.is_valid():
        nome = form.cleaned_data['nome']
        disciplina = form.cleaned_data['disciplina']
        if Assunto.objects.filter(nome__iexact=nome, disciplina=disciplina).exists():
            return JsonResponse({'status': 'error', 'message': 'Já existe um assunto com este nome para esta disciplina.'}, status=400)
        
        assunto = Assunto.objects.create(nome=nome, disciplina=disciplina)
        criar_log(ator=request.user, acao=LogAtividade.Acao.ASSUNTO_CRIADO, alvo=assunto, detalhes={'assunto': assunto.nome, 'disciplina': disciplina.nome})
        return JsonResponse({'status': 'success', 'assunto': {'id': assunto.id, 'nome': assunto.nome, 'disciplina': disciplina.nome}})
    return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)

@user_passes_test(is_staff_member)
@login_required
def visualizar_questao_ajax(request, questao_id):
    """
    Retorna os detalhes de uma questão em formato JSON para visualização em modal.
    O enunciado é renderizado de Markdown para HTML.
    """
    try:
        questao = get_object_or_404(Questao, id=questao_id)
        data = {
            'status': 'success',
            'codigo': questao.codigo,
            'enunciado': markdown.markdown(questao.enunciado),
            'alternativas': questao.get_alternativas_dict(),
            'gabarito': questao.gabarito
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =======================================================================
# BLOKO 4: GERENCIAMENTO DE NOTIFICAÇÕES DE QUESTÕES
# =======================================================================

@user_passes_test(is_staff_member)
@login_required
def listar_notificacoes(request):
    """
    Lista as notificações de problemas em questões, agrupadas por questão.
    Permite filtrar por status (Pendente, Resolvido, Rejeitado) e ordenar.
    """
    status_filtro = request.GET.get('status', 'PENDENTE')
    base_queryset = Questao.objects.annotate(num_notificacoes=Count('notificacoes')).filter(num_notificacoes__gt=0)
    
    # Filtra as questões para mostrar apenas aquelas que têm notificações no status selecionado
    if status_filtro != 'TODAS':
        reports_na_aba_atual = Notificacao.objects.filter(questao_id=OuterRef('pk'), status=status_filtro)
        base_queryset = base_queryset.filter(Exists(reports_na_aba_atual))
    
    filtro_anotacao = Q(notificacoes__status=status_filtro) if status_filtro != 'TODAS' else Q()

    # Lógica de ordenação
    sort_by = request.GET.get('sort_by', '-ultima_notificacao')
    sort_options = {
        '-ultima_notificacao': 'Mais Recentes', 'ultima_notificacao': 'Mais Antigas',
        '-num_reports': 'Mais Reportadas', 'num_reports': 'Menos Reportadas',
    }
    
    # Anota o queryset com o número de reports e a data do último, para ordenação
    questoes_reportadas = base_queryset.annotate(
        num_reports=Count('notificacoes', filter=filtro_anotacao),
        ultima_notificacao=Max('notificacoes__data_criacao', filter=filtro_anotacao)
    )

    if sort_by in sort_options:
        questoes_reportadas = questoes_reportadas.order_by(sort_by)

    # Otimiza a busca das notificações relacionadas usando prefetch_related
    prefetch_queryset = Notificacao.objects.select_related('usuario_reportou__userprofile')
    if status_filtro != 'TODAS':
        prefetch_queryset = prefetch_queryset.filter(status=status_filtro)
    
    questoes_reportadas = questoes_reportadas.prefetch_related(
        Prefetch('notificacoes', queryset=prefetch_queryset.order_by('-data_criacao'), to_attr='reports_filtrados')
    )
    
    page_obj, page_numbers, per_page = paginar_itens(request, questoes_reportadas, 10)
    
    # Estatísticas para as abas da interface
    stats = {
        'pendentes_total': Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count(),
        'resolvidas_total': Notificacao.objects.filter(status=Notificacao.Status.RESOLVIDO).count(),
        'rejeitadas_total': Notificacao.objects.filter(status=Notificacao.Status.REJEITADO).count(),
    }
    
    context = {
        'questoes_agrupadas': page_obj, 'paginated_object': page_obj, 'page_numbers': page_numbers,
        'status_ativo': status_filtro, 'stats': stats, 'per_page': per_page, 'sort_by': sort_by, 'sort_options': sort_options,
    }
    return render(request, 'gestao/listar_notificacoes_agrupadas.html', context)

@require_POST
@user_passes_test(is_staff_member)
@login_required
def notificacao_acao_agrupada(request, questao_id):
    """
    Aplica uma ação (resolver, rejeitar, excluir) a todas as notificações de um mesmo status
    para uma única questão. Acessada via AJAX a partir dos cards de notificação.
    """
    questao = get_object_or_404(Questao, id=questao_id)
    action = request.POST.get('action')
    status_original = request.POST.get('status_original', 'PENDENTE')
    notificacoes = Notificacao.objects.filter(questao=questao, status=status_original)
    count = notificacoes.count()
    
    if action == 'resolver':
        notificacoes.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
        criar_log(ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_RESOLVIDAS, alvo=questao, detalhes={'count': count, 'codigo_questao': questao.codigo})
        message = f'{count} report(s) da questão {questao.codigo} marcados como "Corrigido".'
        return JsonResponse({'status': 'success', 'message': message, 'removed_card_id': f'card-group-{questao.id}'})
    
    elif action == 'rejeitar':
        notificacoes.update(status=Notificacao.Status.REJEITADO)
        criar_log(ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_REJEITADAS, alvo=questao, detalhes={'count': count, 'codigo_questao': questao.codigo})
        message = f'{count} report(s) da questão {questao.codigo} foram rejeitados.'
        return JsonResponse({'status': 'success', 'message': message, 'removed_card_id': f'card-group-{questao.id}'})

    elif action == 'excluir' and status_original in ['RESOLVIDO', 'REJEITADO']:
        count, _ = notificacoes.delete()
        criar_log(ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_DELETADAS, alvo=questao, detalhes={'count': count, 'codigo_questao': questao.codigo, 'status_original': status_original})
        message = f'{count} report(s) da questão {questao.codigo} foram excluídos.'
        return JsonResponse({'status': 'success', 'message': message, 'removed_card_id': f'card-group-{questao.id}'})

    return JsonResponse({'status': 'error', 'message': 'Ação inválida ou não permitida.'}, status=400)

@require_POST
@user_passes_test(is_staff_member)
def notificacoes_acoes_em_massa(request):
    """
    Aplica uma ação (resolver, rejeitar, excluir) a notificações de múltiplas questões
    selecionadas de uma só vez. Acessada via AJAX.
    """
    try:
        data = json.loads(request.body)
        questao_ids = data.get('ids', [])
        action = data.get('action')
        status_original = data.get('status_original', 'PENDENTE')

        if not questao_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)
        
        queryset = Notificacao.objects.filter(questao_id__in=questao_ids, status=status_original)
        
        # Cria um log para cada grupo de notificações (por questão) afetado
        for q_id in questao_ids:
            questao = get_object_or_404(Questao, id=q_id)
            count = queryset.filter(questao_id=q_id).count()
            if count > 0:
                log_acao_map = {'resolver': LogAtividade.Acao.NOTIFICACOES_RESOLVIDAS, 'rejeitar': LogAtividade.Acao.NOTIFICACOES_REJEITADAS, 'excluir': LogAtividade.Acao.NOTIFICACOES_DELETADAS}
                log_acao = log_acao_map.get(action)
                if log_acao:
                    criar_log(ator=request.user, acao=log_acao, alvo=questao, detalhes={'count': count, 'codigo_questao': questao.codigo, 'status_original': status_original, 'motivo': 'Ação em massa'})

        # Executa a ação no banco de dados
        if action == 'resolver':
            queryset.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
        elif action == 'rejeitar':
            queryset.update(status=Notificacao.Status.REJEITADO)
        elif action == 'excluir' and status_original in ['RESOLVIDO', 'REJEITADO']:
            queryset.delete()
        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida ou não permitida.'}, status=400)
        
        return JsonResponse({'status': 'success', 'message': 'Ação aplicada com sucesso.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =======================================================================
# BLOKO 5: GERENCIAMENTO DE USUÁRIOS (GERAL)
# =======================================================================

@login_required
@user_passes_test(is_staff_member)
def listar_usuarios(request):
    """
    Lista, filtra e ordena todos os usuários do sistema.
    Superusuários podem ver todos; membros da equipe não podem ver outros superusuários.
    """
    base_queryset = User.objects.all().select_related('userprofile').exclude(id=request.user.id)
    if not request.user.is_superuser:
        base_queryset = base_queryset.exclude(is_superuser=True)

    # Anotação para identificar usuários com solicitações de exclusão pendentes
    solicitacoes_pendentes = SolicitacaoExclusao.objects.filter(
        usuario_a_ser_excluido=OuterRef('pk'),
        status=SolicitacaoExclusao.Status.PENDENTE
    )
    base_queryset = base_queryset.annotate(tem_solicitacao_pendente=Exists(solicitacoes_pendentes))

    # Lógica de filtragem
    filtro_q = request.GET.get('q', '').strip()
    filtro_permissao = request.GET.get('permissao', '')
    filtro_solicitacao = request.GET.get('solicitacao', '')
    filtro_status = request.GET.get('status', 'ativos')

    if filtro_q:
        base_queryset = base_queryset.filter(Q(username__icontains=filtro_q) | Q(email__icontains=filtro_q))
    if filtro_permissao:
        if filtro_permissao == 'superuser': base_queryset = base_queryset.filter(is_superuser=True)
        elif filtro_permissao == 'staff': base_queryset = base_queryset.filter(is_staff=True, is_superuser=False)
        elif filtro_permissao == 'comum': base_queryset = base_queryset.filter(is_staff=False)
    if filtro_solicitacao == 'pendente':
        base_queryset = base_queryset.filter(tem_solicitacao_pendente=True)
    if filtro_status == 'ativos':
        base_queryset = base_queryset.filter(is_active=True)
    elif filtro_status == 'inativos':
        base_queryset = base_queryset.filter(is_active=False)

    # Lógica de ordenação
    sort_by = request.GET.get('sort_by', 'nivel')
    sort_options = {
        'nivel': 'Nível de Permissão', '-date_joined': 'Mais Recentes', 'date_joined': 'Mais Antigos',
        'username': 'Nome (A-Z)', '-username': 'Nome (Z-A)',
    }
    
    order_fields = [
        '-is_active',                # 1. Ativos primeiro
        '-is_superuser',             # 2. Superusers no topo
        '-is_staff',                 # 3. Staff logo abaixo
        '-tem_solicitacao_pendente', # 4. Com solicitação pendente priorizados
    ]

    if sort_by != 'nivel' and sort_by in sort_options:
        order_fields.append(sort_by)
    else:
        order_fields.append('username') # Ordenação padrão
    
    base_queryset = base_queryset.order_by(*order_fields)

    paginated_object, page_numbers, per_page = paginar_itens(request, base_queryset, items_per_page=9)

    context = {
        'paginated_object': paginated_object, 'page_numbers': page_numbers, 'per_page': per_page,
        'sort_by': sort_by, 'sort_options': sort_options, 'filtro_q': filtro_q, 'filtro_permissao': filtro_permissao,
        'filtro_solicitacao': filtro_solicitacao, 'filtro_status': filtro_status, 'total_usuarios': paginated_object.paginator.count,
    }
    return render(request, 'gestao/listar_usuarios.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def editar_usuario_staff(request, user_id):
    """
    Permite que um superusuário promova ou rebaixe um usuário comum a membro da equipe (staff).
    Acessada via AJAX. Impede a edição de outros superusuários.
    """
    usuario_alvo = get_object_or_404(User, id=user_id)

    # Regra de segurança: Um superuser não pode alterar as permissões de outro superuser por esta via.
    if usuario_alvo.is_superuser and usuario_alvo != request.user:
        messages.error(request, "Você não pode editar as permissões de outro superusuário diretamente. Use os sistemas de despromoção ou exclusão.")
        return redirect('gestao:listar_usuarios')
        
    old_is_staff = usuario_alvo.is_staff
    if request.method == 'POST':
        form = StaffUserForm(request.POST, instance=usuario_alvo)
        if form.is_valid():
            usuario_modificado = form.save()
            if old_is_staff != usuario_modificado.is_staff:
                criar_log(
                    ator=request.user, acao=LogAtividade.Acao.PERMISSOES_ALTERADAS, alvo=usuario_alvo,
                    detalhes={'usuario_alvo': usuario_alvo.username, 'de': 'Usuário Comum' if not old_is_staff else 'Membro da Equipe', 'para': 'Membro da Equipe' if usuario_modificado.is_staff else 'Usuário Comum'}
                )
            return JsonResponse({'status': 'success', 'message': f'Permissões de {usuario_alvo.username} atualizadas.'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
            
    form = StaffUserForm(instance=usuario_alvo)
    context = {'form': form, 'usuario_alvo': usuario_alvo}
    return render(request, 'gestao/form_usuario_staff.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def sugerir_exclusao_usuario(request, user_id):
    """
    Permite que um membro da equipe (staff) sugira a exclusão de um usuário comum.
    Cria uma `SolicitacaoExclusao` que será revisada por um superusuário. Acessada via AJAX.
    """
    usuario_alvo = get_object_or_404(User, id=user_id)
    form = ExclusaoUsuarioForm(request.POST)

    if usuario_alvo.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Membros da equipe não podem sugerir a exclusão de superusuários.'}, status=403)
    if SolicitacaoExclusao.objects.filter(usuario_a_ser_excluido=usuario_alvo, status=SolicitacaoExclusao.Status.PENDENTE).exists():
        return JsonResponse({'status': 'error', 'message': 'Já existe uma solicitação de exclusão pendente para este usuário.'}, status=400)

    form.fields['justificativa'].required = True
        
    if form.is_valid():
        motivo_predefinido_chave = form.cleaned_data['motivo_predefinido']
        motivo_predefinido_texto = dict(form.fields['motivo_predefinido'].choices)[motivo_predefinido_chave]
        justificativa = form.cleaned_data['justificativa']
        motivo_completo = f"Motivo: {motivo_predefinido_texto}\n\nJustificativa: {justificativa}"

        solicitacao = SolicitacaoExclusao.objects.create(usuario_a_ser_excluido=usuario_alvo, solicitado_por=request.user, motivo=motivo_completo)
        
        criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_CRIADA, alvo=solicitacao, detalhes={'usuario_alvo': usuario_alvo.username})
        
        return JsonResponse({'status': 'success', 'message': 'Sua sugestão de exclusão foi enviada para revisão por um superusuário.'})
    
    return JsonResponse({'status': 'error', 'message': 'Por favor, corrija os erros abaixo.', 'field_errors': form.errors}, status=400)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
@transaction.atomic
def deletar_usuario(request, user_id):
    """
    Permite que um superusuário delete diretamente um usuário (comum ou staff).
    Acessada via AJAX.
    """
    usuario_alvo = get_object_or_404(User, id=user_id)
    form = ExclusaoUsuarioForm(request.POST)

    # Regras de segurança
    if usuario_alvo == request.user:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Você não pode excluir sua própria conta.'}, status=403)
    if usuario_alvo.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível excluir o único superusuário do sistema.'}, status=403)

    if form.is_valid():
        motivo_predefinido_chave = form.cleaned_data['motivo_predefinido']
        motivo_predefinido_texto = dict(form.fields['motivo_predefinido'].choices)[motivo_predefinido_chave]
        justificativa = form.cleaned_data.get('justificativa', '')
        motivo_final = f"{motivo_predefinido_texto}" + (f" (Detalhes: {justificativa})" if justificativa else "")
            
        email_alvo = usuario_alvo.email
        username_alvo = usuario_alvo.username

        criar_log(ator=request.user, acao=LogAtividade.Acao.USUARIO_DELETADO, alvo=None, detalhes={'usuario_deletado': usuario_alvo.username, 'motivo': motivo_final})

        message = ""
        # Envia e-mail de notificação se o usuário tiver um e-mail cadastrado
        if email_alvo:
            try:
                enviar_email_com_template(
                    request, subject='Sua conta na plataforma Raio-X da Aprovação foi removida',
                    template_name='gestao/email_conta_excluida.html',
                    context={'user': usuario_alvo, 'motivo_texto': motivo_final},
                    recipient_list=[email_alvo]
                )
                message = f'O usuário "{username_alvo}" foi excluído e notificado por e-mail com sucesso.'
            except Exception as e:
                message = f'O usuário "{username_alvo}" foi excluído, mas ocorreu um erro ao enviar o e-mail: {e}'
        else:
            message = f'O usuário "{username_alvo}" foi excluído. (Nenhuma notificação foi enviada por falta de e-mail).'
        
        usuario_alvo.delete()
        return JsonResponse({'status': 'success', 'message': message, 'deleted_user_id': user_id })
    else:
        return JsonResponse({'status': 'error', 'message': 'Por favor, corrija os erros abaixo.', 'field_errors': form.errors}, status=400)


# =======================================================================
# BLOKO 6: GERENCIAMENTO DE SOLICITAÇÕES DE EXCLUSÃO (Staff -> Superuser)
# =======================================================================

@login_required
@user_passes_test(is_staff_member)
def listar_solicitacoes_exclusao(request):
    """
    Lista as solicitações de exclusão de usuários feitas por membros da equipe
    que estão pendentes de aprovação por um superusuário.
    """
    solicitacoes_list = SolicitacaoExclusao.objects.filter(status=SolicitacaoExclusao.Status.PENDENTE).select_related('usuario_a_ser_excluido', 'solicitado_por')
    sort_by = request.GET.get('sort_by', '-data_solicitacao')
    sort_options = {'-data_solicitacao': 'Mais Recentes', 'data_solicitacao': 'Mais Antigas'}
    if sort_by in sort_options:
        solicitacoes_list = solicitacoes_list.order_by(sort_by)

    solicitacoes_paginadas, page_numbers, per_page = paginar_itens(request, solicitacoes_list, items_per_page=10)

    context = {
        'solicitacoes': solicitacoes_paginadas, 'paginated_object': solicitacoes_paginadas, 'page_numbers': page_numbers,
        'per_page': per_page, 'sort_by': sort_by, 'sort_options': sort_options, 'total_solicitacoes': solicitacoes_paginadas.paginator.count,
    }
    return render(request, 'gestao/listar_solicitacoes_exclusao.html', context)

@login_required
@user_passes_test(is_staff_member)
@require_POST
def cancelar_solicitacao_exclusao(request, solicitacao_id):
    """
    Permite que o autor de uma solicitação de exclusão a cancele enquanto
    ela ainda estiver pendente. Acessada via AJAX.
    """
    try:
        solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, solicitado_por=request.user, status=SolicitacaoExclusao.Status.PENDENTE)
        
        criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_CANCELADA, alvo=solicitacao, detalhes={'usuario_alvo': solicitacao.usuario_a_ser_excluido.username})
        solicitacao.delete()

        return JsonResponse({'status': 'success', 'message': 'Sua solicitação de exclusão foi cancelada com sucesso.', 'solicitacao_id': solicitacao_id})
    except SolicitacaoExclusao.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Solicitação não encontrada ou você não tem permissão para cancelá-la.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def aprovar_solicitacao_exclusao(request, solicitacao_id):
    """
    Permite que um superusuário aprove uma solicitação de exclusão, deletando o usuário alvo.
    Acessada via AJAX.
    """
    solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, status=SolicitacaoExclusao.Status.PENDENTE)
    usuario_a_deletar = solicitacao.usuario_a_ser_excluido

    # Regra de segurança para não excluir o único superusuário
    if User.objects.filter(is_superuser=True, is_active=True).count() <= 1 and usuario_a_deletar.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível aprovar a exclusão do único superusuário.'}, status=403)

    try:
        # Tenta enviar e-mail de notificação
        message = ""
        if usuario_a_deletar.email:
            try:
                enviar_email_com_template(request, subject='Sua conta na plataforma Raio-X da Aprovação foi removida', template_name='gestao/email_conta_excluida.html', context={'user': usuario_a_deletar, 'motivo_texto': solicitacao.motivo}, recipient_list=[usuario_a_deletar.email])
                message = f'A solicitação foi aprovada, o usuário "{usuario_a_deletar.username}" foi excluído e notificado.'
            except Exception as e:
                message = f'A solicitação foi aprovada e o usuário "{usuario_a_deletar.username}" foi excluído, mas o envio de e-mail falhou: {e}'
        else:
            message = f'A solicitação foi aprovada e o usuário "{usuario_a_deletar.username}" foi excluído. (Sem e-mail para notificar).'

        # Verifica se o solicitante original ainda existe, para evitar erros no log
        solicitado_por_username = solicitacao.solicitado_por.username if solicitacao.solicitado_por else "(Usuário solicitante deletado)"
        
        # Cria logs da aprovação e da exclusão
        criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_APROVADA, alvo=solicitacao, detalhes={'usuario_excluido': usuario_a_deletar.username, 'solicitado_por': solicitado_por_username})
        criar_log(ator=request.user, acao=LogAtividade.Acao.USUARIO_DELETADO, alvo=None, detalhes={'usuario_deletado': usuario_a_deletar.username, 'motivo': f'Aprovação da solicitação #{solicitacao.id}'})

        # Atualiza o status da solicitação e deleta o usuário
        solicitacao.status = SolicitacaoExclusao.Status.APROVADO
        solicitacao.revisado_por = request.user
        solicitacao.data_revisao = timezone.now()
        solicitacao.save()
        usuario_a_deletar.delete()

        return JsonResponse({'status': 'success', 'message': message, 'solicitacao_id': solicitacao_id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def rejeitar_solicitacao_exclusao(request, solicitacao_id):
    """
    Permite que um superusuário rejeite uma solicitação de exclusão. O usuário alvo não é alterado.
    Acessada via AJAX.
    """
    solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, status=SolicitacaoExclusao.Status.PENDENTE)
    
    try:
        solicitado_por_username = solicitacao.solicitado_por.username if solicitacao.solicitado_por else "(Usuário solicitante deletado)"
        criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_REJEITADA, alvo=solicitacao, detalhes={'usuario_alvo': solicitacao.usuario_a_ser_excluido.username, 'solicitado_por': solicitado_por_username})
        
        # Atualiza o status da solicitação
        solicitacao.status = SolicitacaoExclusao.Status.REJEITADO
        solicitacao.revisado_por = request.user
        solicitacao.data_revisao = timezone.now()
        solicitacao.save(update_fields=['status', 'revisado_por', 'data_revisao'])

        return JsonResponse({'status': 'success', 'message': f'A solicitação para excluir o usuário "{solicitacao.usuario_a_ser_excluido.username}" foi rejeitada.', 'solicitacao_id': solicitacao_id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro: {str(e)}'}, status=500)

# =======================================================================
# BLOKO 7: SISTEMA DE QUÓRUM PARA PROMOÇÃO A SUPERUSUÁRIO
# =======================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def solicitar_promocao_superuser(request, user_id):
    """
    Renderiza e processa a solicitação para promover um usuário a superusuário.
    A solicitação requer aprovação por quórum de outros superusuários.
    """
    usuario_alvo = get_object_or_404(User, id=user_id, is_superuser=False)
    if request.method == 'POST':
        justificativa = request.POST.get('justificativa')
        if justificativa:
            promocao, created = PromocaoSuperuser.objects.get_or_create(
                usuario_alvo=usuario_alvo, status=PromocaoSuperuser.Status.PENDENTE,
                defaults={'solicitado_por': request.user, 'justificativa': justificativa}
            )
            if created:
                criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_PROMOCAO_CRIADA, alvo=promocao, detalhes={'usuario_alvo': usuario_alvo.username})
                messages.success(request, 'Solicitação de promoção enviada para aprovação.')
            else:
                messages.warning(request, 'Já existe uma solicitação de promoção pendente para este usuário.')
            return redirect('gestao:listar_usuarios')
        else:
            messages.error(request, 'A justificativa é obrigatória.')
    return render(request, 'gestao/solicitar_promocao.html', {'usuario_alvo': usuario_alvo})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_solicitacoes_promocao(request):
    """Lista todas as solicitações de promoção a superusuário pendentes."""
    solicitacoes = PromocaoSuperuser.objects.filter(status=PromocaoSuperuser.Status.PENDENTE).select_related('usuario_alvo', 'solicitado_por')
    context = {'solicitacoes': solicitacoes}
    return render(request, 'gestao/listar_solicitacoes_promocao.html', context)

@require_POST
@login_required
@transaction.atomic
@user_passes_test(lambda u: u.is_superuser)
def aprovar_promocao_superuser(request, promocao_id):
    """
    Registra a aprovação de um superusuário em uma solicitação de promoção.
    Se o quórum for atingido, a promoção é efetivada.
    """
    promocao = get_object_or_404(PromocaoSuperuser, id=promocao_id)
    ja_aprovou = promocao.aprovado_por.filter(pk=request.user.pk).exists()
    
    # A lógica de aprovação e verificação de quórum está no método .aprovar() do modelo
    success, message = promocao.aprovar(request.user)
    
    if not ja_aprovou: # Evita criar logs duplicados se o usuário clicar várias vezes
        log_acao = LogAtividade.Acao.USUARIO_PROMOVIDO_SUPERUSER if success else LogAtividade.Acao.SOLICITACAO_PROMOCAO_APROVADA
        criar_log(ator=request.user, acao=log_acao, alvo=promocao, detalhes={'usuario_alvo': promocao.usuario_alvo.username, 'aprovador_atual': request.user.username, 'quorum_atingido': success})
    
    (messages.success if success else messages.info)(request, message)
    return redirect('gestao:listar_solicitacoes_promocao')

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def cancelar_promocao_superuser(request, promocao_id):
    """
    Permite que o autor de uma solicitação de promoção a cancele.
    """
    try:
        promocao = get_object_or_404(PromocaoSuperuser, id=promocao_id, solicitado_por=request.user, status=PromocaoSuperuser.Status.PENDENTE)
        criar_log(ator=request.user, acao='SOLICITACAO_PROMOCAO_CANCELADA', alvo=promocao, detalhes={'usuario_alvo': promocao.usuario_alvo.username})
        promocao.delete()
        messages.success(request, 'Sua solicitação de promoção foi cancelada com sucesso.')
    except PromocaoSuperuser.DoesNotExist:
        messages.error(request, 'Solicitação não encontrada ou você não tem permissão para cancelá-la.')
    return redirect('gestao:listar_solicitacoes_promocao')

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def promover_diretamente_superuser(request, user_id):
    """
    Caso especial: permite que o único superusuário do sistema promova outro
    diretamente, sem a necessidade de quórum.
    """
    if User.objects.filter(is_superuser=True, is_active=True).count() > 1:
        messages.error(request, "A promoção direta só é permitida quando há apenas um superusuário no sistema.")
        return redirect('gestao:listar_usuarios')

    usuario_alvo = get_object_or_404(User, id=user_id, is_superuser=False)
    
    usuario_alvo.is_superuser = True
    usuario_alvo.is_staff = True
    usuario_alvo.save(update_fields=['is_superuser', 'is_staff'])

    criar_log(ator=request.user, acao=LogAtividade.Acao.USUARIO_PROMOVIDO_SUPERUSER, alvo=usuario_alvo, detalhes={'usuario_alvo': usuario_alvo.username, 'motivo': 'Promoção direta (único superusuário no sistema)'})

    messages.success(request, f'Usuário "{usuario_alvo.username}" promovido a Superusuário diretamente.')
    return redirect('gestao:listar_usuarios')

# =======================================================================
# BLOKO 8: SISTEMA DE QUÓRUM PARA DESPROMOÇÃO DE SUPERUSUÁRIO
# =======================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def solicitar_despromocao_superuser(request, user_id):
    """
    Renderiza e processa a solicitação para despromover (rebaixar) um superusuário.
    A solicitação requer aprovação por quórum.
    """
    usuario_alvo = get_object_or_404(User, id=user_id, is_superuser=True)
    if request.method == 'POST':
        justificativa = request.POST.get('justificativa')
        if justificativa:
            despromocao, created = DespromocaoSuperuser.objects.get_or_create(
                usuario_alvo=usuario_alvo, status=DespromocaoSuperuser.Status.PENDENTE,
                defaults={'solicitado_por': request.user, 'justificativa': justificativa}
            )
            if created:
                criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_DESPROMOCAO_CRIADA, alvo=despromocao, detalhes={'usuario_alvo': usuario_alvo.username})
                messages.success(request, 'Solicitação de despromoção enviada para revisão por outros superusuários.')
            else:
                messages.warning(request, 'Já existe uma solicitação de despromoção pendente para este usuário.')
            return redirect('gestao:listar_usuarios')
        else:
            messages.error(request, "A justificativa é obrigatória.")
    
    context = {'usuario_alvo': usuario_alvo}
    return render(request, 'gestao/solicitar_despromocao.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_solicitacoes_despromocao(request):
    """Lista todas as solicitações de despromoção de superusuários pendentes."""
    solicitacoes = DespromocaoSuperuser.objects.filter(status=DespromocaoSuperuser.Status.PENDENTE).select_related('usuario_alvo', 'solicitado_por')
    context = {'solicitacoes': solicitacoes}
    return render(request, 'gestao/listar_solicitacoes_despromocao.html', context)

@require_POST
@login_required
@transaction.atomic
@user_passes_test(lambda u: u.is_superuser)
def aprovar_despromocao_superuser(request, despromocao_id):
    """
    Registra a aprovação de um superusuário em uma solicitação de despromoção.
    Se o quórum for atingido, a despromoção é efetivada.
    """
    despromocao = get_object_or_404(DespromocaoSuperuser, id=despromocao_id, status=DespromocaoSuperuser.Status.PENDENTE)
    
    # A lógica de aprovação e verificação de quórum está no método .aprovar() do modelo
    status, message = despromocao.aprovar(request.user)

    if status == 'QUORUM_MET':
        # Loga a efetivação da despromoção
        criar_log(ator=request.user, acao=LogAtividade.Acao.USUARIO_DESPROMOVIDO_SUPERUSER, alvo=despromocao, detalhes={'usuario_alvo': despromocao.usuario_alvo.username, 'aprovador_atual': request.user.username, 'quorum_atingido': True})
        
        # Efetiva a despromoção
        usuario_alvo = despromocao.usuario_alvo
        usuario_alvo.is_superuser = False
        usuario_alvo.save(update_fields=['is_superuser'])
        despromocao.save() # Salva o status atualizado da solicitação
        
        messages.success(request, message)

    elif status == 'APPROVAL_REGISTERED':
        # Loga apenas o registro do voto de aprovação
        criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_DESPROMOCAO_APROVADA, alvo=despromocao, detalhes={'usuario_alvo': despromocao.usuario_alvo.username, 'aprovador_atual': request.user.username, 'quorum_atingido': False})
        messages.info(request, message)
    else: # status == 'FAILED'
        messages.error(request, message)
    
    return redirect('gestao:listar_solicitacoes_despromocao')

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def cancelar_despromocao_superuser(request, despromocao_id):
    """
    Permite que o autor de uma solicitação de despromoção a cancele.
    """
    try:
        despromocao = get_object_or_404(DespromocaoSuperuser, id=despromocao_id, solicitado_por=request.user, status=DespromocaoSuperuser.Status.PENDENTE)
        criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_DESPROMOCAO_CANCELADA, alvo=despromocao, detalhes={'usuario_alvo': despromocao.usuario_alvo.username})
        despromocao.delete()
        messages.success(request, 'Sua solicitação de despromoção foi cancelada com sucesso.')
    except DespromocaoSuperuser.DoesNotExist:
        messages.error(request, 'Solicitação não encontrada ou você não tem permissão para cancelá-la.')
    
    return redirect('gestao:listar_solicitacoes_despromocao')


# =======================================================================
# BLOKO 9: SISTEMA DE QUÓRUM PARA EXCLUSÃO DE SUPERUSUÁRIO
# =======================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def solicitar_exclusao_superuser(request, user_id):
    """
    Renderiza e processa a solicitação para excluir um superusuário.
    A solicitação requer aprovação por quórum.
    """
    usuario_alvo = get_object_or_404(User, id=user_id, is_superuser=True)

    # Regras de segurança
    if usuario_alvo == request.user:
        messages.error(request, "Você não pode solicitar sua própria exclusão.")
        return redirect('gestao:listar_usuarios')
    if User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        messages.error(request, "Não é possível solicitar a exclusão do único superusuário do sistema.")
        return redirect('gestao:listar_usuarios')

    if request.method == 'POST':
        justificativa = request.POST.get('justificativa')
        if justificativa:
            exclusao, created = ExclusaoSuperuser.objects.get_or_create(
                usuario_alvo=usuario_alvo, status=ExclusaoSuperuser.Status.PENDENTE,
                defaults={'solicitado_por': request.user, 'justificativa': justificativa}
            )
            if created:
                criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_SUPERUSER_CRIADA, alvo=exclusao, detalhes={'usuario_alvo': usuario_alvo.username})
                messages.success(request, 'Solicitação de exclusão enviada para revisão.')
            else:
                messages.warning(request, 'Já existe uma solicitação de exclusão pendente para este usuário.')
            return redirect('gestao:listar_usuarios')
        else:
            messages.error(request, "A justificativa é obrigatória.")
    
    context = {'usuario_alvo': usuario_alvo}
    return render(request, 'gestao/solicitar_exclusao_superuser.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_solicitacoes_exclusao_superuser(request):
    """Lista todas as solicitações de exclusão de superusuários pendentes."""
    solicitacoes = ExclusaoSuperuser.objects.filter(status=ExclusaoSuperuser.Status.PENDENTE).select_related('usuario_alvo', 'solicitado_por')
    context = {'solicitacoes': solicitacoes}
    return render(request, 'gestao/listar_solicitacoes_exclusao_superuser.html', context)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
@transaction.atomic
def aprovar_exclusao_superuser(request, exclusao_id):
    """
    Registra a aprovação de um superusuário em uma solicitação de exclusão.
    Se o quórum for atingido, a exclusão é efetivada.
    """
    exclusao = get_object_or_404(ExclusaoSuperuser.objects.select_for_update(), id=exclusao_id, status=ExclusaoSuperuser.Status.PENDENTE)
    
    # Verificação de segurança crucial: impede que o sistema fique sem superusuários.
    if User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        messages.error(request, f"Ação negada: A exclusão de '{exclusao.usuario_alvo.username}' deixaria o sistema sem superusuários.")
        return redirect('gestao:listar_solicitacoes_exclusao_superuser')

    # A lógica de aprovação e verificação de quórum está no método .aprovar() do modelo
    status, message = exclusao.aprovar(request.user)

    if status == 'QUORUM_MET':
        # Loga a efetivação da exclusão
        criar_log(ator=request.user, acao=LogAtividade.Acao.USUARIO_DELETADO, alvo=None, detalhes={'usuario_alvo': exclusao.usuario_alvo.username, 'aprovador_atual': request.user.username, 'quorum_atingido': True})
        
        # Efetiva a exclusão
        exclusao.usuario_alvo.delete()
        messages.success(request, message)
        
    elif status == 'APPROVAL_REGISTERED':
        # Loga apenas o registro do voto de aprovação
        criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_SUPERUSER_APROVADA, alvo=exclusao, detalhes={'usuario_alvo': exclusao.usuario_alvo.username, 'aprovador_atual': request.user.username, 'quorum_atingido': False})
        messages.info(request, message)

    else: # status == 'FAILED'
        messages.error(request, message)
    
    return redirect('gestao:listar_solicitacoes_exclusao_superuser')

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def cancelar_exclusao_superuser(request, exclusao_id):
    """
    Permite que o autor de uma solicitação de exclusão de superusuário a cancele.
    """
    try:
        exclusao = get_object_or_404(ExclusaoSuperuser, id=exclusao_id, solicitado_por=request.user, status=ExclusaoSuperuser.Status.PENDENTE)
        criar_log(ator=request.user, acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_SUPERUSER_CANCELADA, alvo=exclusao, detalhes={'usuario_alvo': exclusao.usuario_alvo.username})
        exclusao.delete()
        messages.success(request, 'Sua solicitação de exclusão foi cancelada com sucesso.')
    except ExclusaoSuperuser.DoesNotExist:
        messages.error(request, 'Solicitação não encontrada ou você não tem permissão para cancelá-la.')
    
    return redirect('gestao:listar_solicitacoes_exclusao_superuser')

# =======================================================================
# BLOKO 10: GERENCIAMENTO DE LOGS DE ATIVIDADE (AUDITORIA)
# =======================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_logs_atividade(request):
    """
    Lista, filtra e ordena todos os logs de atividades ativas (não deletadas).
    Restrito a superusuários.
    """
    logs_list = LogAtividade.objects.select_related('ator').all()

    # Lógica de filtragem
    filtro_q = request.GET.get('q', '').strip()
    filtro_acao = request.GET.get('acao', '')
    filtro_data_inicio = request.GET.get('data_inicio', '')
    filtro_data_fim = request.GET.get('data_fim', '')
    
    if filtro_q:
        logs_list = logs_list.filter(Q(ator__username__icontains=filtro_q) | Q(ator__email__icontains=filtro_q))
    if filtro_acao:
        logs_list = logs_list.filter(acao=filtro_acao)
    if filtro_data_inicio:
        logs_list = logs_list.filter(data_criacao__gte=filtro_data_inicio)
    if filtro_data_fim:
        data_fim_obj = datetime.strptime(filtro_data_fim, '%Y-%m-%d') + timedelta(days=1)
        logs_list = logs_list.filter(data_criacao__lt=data_fim_obj)
    
    # Lógica de ordenação
    sort_by = request.GET.get('sort_by', '-data_criacao')
    sort_options = {'-data_criacao': 'Mais Recentes', 'data_criacao': 'Mais Antigos'}
    if sort_by in sort_options:
        logs_list = logs_list.order_by(sort_by)

    logs_paginados, page_numbers, per_page = paginar_itens(request, logs_list, 20)
    
    context = {
        'logs': logs_paginados, 'paginated_object': logs_paginados, 'page_numbers': page_numbers, 'per_page': per_page,
        'sort_by': sort_by, 'sort_options': sort_options, 'filtro_q': filtro_q, 'filtro_acao': filtro_acao,
        'filtro_data_inicio': filtro_data_inicio, 'filtro_data_fim': filtro_data_fim, 'acao_choices': LogAtividade.Acao.choices,
    }
    return render(request, 'gestao/listar_logs_atividade.html', context)

@require_POST
@user_passes_test(lambda u: u.is_superuser)
def deletar_log_atividade(request, log_id):
    """
    Move um registro de log para a lixeira (soft delete).
    Impede que um superusuário delete seus próprios logs. Acessada via AJAX.
    """
    log = get_object_or_404(LogAtividade, id=log_id)
    if log.ator == request.user:
        return JsonResponse({'status': 'error', 'message': 'Você não pode excluir seus próprios registros.'}, status=403)
    log.delete(user=request.user) # Soft delete
    return JsonResponse({'status': 'success', 'message': 'Registro movido para a lixeira.', 'deleted_log_id': log_id})

@require_POST
@user_passes_test(lambda u: u.is_superuser)
def logs_acoes_em_massa(request):
    """
    Move múltiplos registros de log para a lixeira.
    Impede que um superusuário delete seus próprios logs. Acessada via AJAX.
    """
    try:
        data = json.loads(request.body)
        log_ids = data.get('ids', [])
        action = data.get('action')
        if not log_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)
        
        if action == 'delete':
            queryset = LogAtividade.objects.filter(id__in=log_ids).exclude(ator=request.user)
            deleted_ids = list(queryset.values_list('id', flat=True))
            for log in queryset:
                log.delete(user=request.user) # Soft delete
            
            message = f'{len(deleted_ids)} registro(s) foram movidos para a lixeira.'
            if len(deleted_ids) < len(log_ids):
                message += ' Seus próprios registros não foram alterados.'
            
            return JsonResponse({'status': 'success', 'message': message, 'deleted_ids': deleted_ids})
        return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def mover_logs_antigos_para_lixeira(request):
    """
    Move logs ativos mais antigos que um determinado número de dias para a lixeira (soft delete).
    O número de dias é passado via POST.
    """
    try:
        days_threshold = int(request.POST.get('days', 180)) # Padrão de 180 dias
    except (ValueError, TypeError):
        days_threshold = 180 # Fallback de segurança

    threshold_date = timezone.now() - timedelta(days=days_threshold)
    logs_para_mover = LogAtividade.objects.filter(data_criacao__lt=threshold_date)
    
    count = logs_para_mover.count()
    if count == 0:
        messages.info(request, f"Nenhum log com mais de {days_threshold} dias foi encontrado para mover para a lixeira.")
        return redirect('gestao:listar_logs_atividade')
        
    for log in logs_para_mover:
        log.delete(user=request.user) # Soft delete

    messages.success(request, f"{count} registro(s) de log com mais de {days_threshold} dias foram movidos para a lixeira.")
    return redirect('gestao:listar_logs_atividade')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_logs_deletados(request):
    """
    Lista os logs de atividade que estão na lixeira (is_deleted=True).
    Permite filtrar e ordenar.
    """
    logs_list = LogAtividade.all_logs.filter(is_deleted=True).select_related('ator', 'deleted_by')

    # Lógica de filtragem (similar à listagem de logs ativos, mas pode usar `deleted_at`)
    filtro_q = request.GET.get('q', '').strip()
    filtro_acao = request.GET.get('acao', '')
    filtro_data_inicio = request.GET.get('data_inicio', '')
    filtro_data_fim = request.GET.get('data_fim', '')
    
    if filtro_q:
        logs_list = logs_list.filter(Q(ator__username__icontains=filtro_q) | Q(ator__email__icontains=filtro_q))
    if filtro_acao:
        logs_list = logs_list.filter(acao=filtro_acao)
    if filtro_data_inicio:
        logs_list = logs_list.filter(deleted_at__gte=filtro_data_inicio)
    if filtro_data_fim:
        data_fim_obj = datetime.strptime(filtro_data_fim, '%Y-%m-%d') + timedelta(days=1)
        logs_list = logs_list.filter(deleted_at__lt=data_fim_obj)
        
    # Lógica de ordenação focada na data de exclusão
    sort_by = request.GET.get('sort_by', '-deleted_at')
    sort_options = {'-deleted_at': 'Exclusão Mais Recente', 'deleted_at': 'Exclusão Mais Antiga'}
    if sort_by in sort_options:
        logs_list = logs_list.order_by(sort_by)

    logs_paginados, page_numbers, per_page = paginar_itens(request, logs_list, 20)
    
    context = {
        'logs': logs_paginados, 'paginated_object': logs_paginados, 'page_numbers': page_numbers, 'per_page': per_page,
        'sort_by': sort_by, 'sort_options': sort_options, 'filtro_q': filtro_q, 'filtro_acao': filtro_acao,
        'filtro_data_inicio': filtro_data_inicio, 'filtro_data_fim': filtro_data_fim, 'acao_choices': LogAtividade.Acao.choices,
    }
    return render(request, 'gestao/listar_logs_deletados.html', context)