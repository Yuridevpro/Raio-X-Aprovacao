# gestao/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db.models import Q, Count, Max, Prefetch, Exists, OuterRef
from django.utils import timezone
from datetime import datetime, timedelta
import json
import markdown
import boto3
import os
from django.db import transaction

# Importações de outros apps
from pratica.models import Notificacao
from usuarios.utils import enviar_email_com_template
from questoes.models import Questao, Disciplina, Banca, Instituicao, Assunto
from questoes.forms import GestaoQuestaoForm, EntidadeSimplesForm, AssuntoForm
from questoes.utils import paginar_itens, filtrar_e_paginar_questoes
from .models import DespromocaoSuperuser, ExclusaoSuperuser # Não se esqueça de importar o novo modelo


# Importações locais do app 'gestao'
from .models import SolicitacaoExclusao, PromocaoSuperuser, LogAtividade
from .forms import StaffUserForm, ExclusaoUsuarioForm
from .utils import arquivar_logs_antigos_no_s3, criar_log


from django.contrib.auth.models import User


# Função auxiliar para decorators
def is_staff_member(user):
    return user.is_staff

# Função auxiliar centralizada para criar logs
def criar_log(ator, acao, alvo=None, detalhes={}):
    """
    Cria uma nova entrada no Registro de Atividades de forma centralizada.
    """
    LogAtividade.objects.create(
        ator=ator,
        acao=acao,
        alvo=alvo,
        detalhes=detalhes
    )

# =======================================================================
# VIEWS PRINCIPAIS DO PAINEL DE GESTÃO
# =======================================================================

@user_passes_test(is_staff_member)
@login_required
def dashboard_gestao(request):
    total_questoes = Questao.objects.count()
    notificacoes_pendentes = Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count()
    solicitacoes_pendentes_count = SolicitacaoExclusao.objects.filter(status=SolicitacaoExclusao.Status.PENDENTE).count()
    
    promocoes_pendentes_count = 0
    despromocoes_pendentes_count = 0
    # =======================================================================
    # INÍCIO DA ADIÇÃO
    # =======================================================================
    exclusoes_superuser_pendentes_count = 0
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================

    if request.user.is_superuser:
        promocoes_pendentes_count = PromocaoSuperuser.objects.filter(status=PromocaoSuperuser.Status.PENDENTE).count()
        despromocoes_pendentes_count = DespromocaoSuperuser.objects.filter(status=DespromocaoSuperuser.Status.PENDENTE).count()
        # =======================================================================
        # INÍCIO DA ADIÇÃO
        # =======================================================================
        exclusoes_superuser_pendentes_count = ExclusaoSuperuser.objects.filter(status=ExclusaoSuperuser.Status.PENDENTE).count()
        # =======================================================================
        # FIM DA ADIÇÃO
        # =======================================================================

    context = {
        'total_questoes': total_questoes,
        'notificacoes_pendentes': notificacoes_pendentes,
        'solicitacoes_pendentes_count': solicitacoes_pendentes_count,
        'promocoes_pendentes_count': promocoes_pendentes_count,
        'despromocoes_pendentes_count': despromocoes_pendentes_count,
        # =======================================================================
        # INÍCIO DA ADIÇÃO
        # =======================================================================
        'exclusoes_superuser_pendentes_count': exclusoes_superuser_pendentes_count,
        # =======================================================================
        # FIM DA ADIÇÃO
        # =======================================================================
    }
    return render(request, 'gestao/dashboard.html', context)


# =======================================================================
# VIEWS DE GERENCIAMENTO DE QUESTÕES
# =======================================================================

@user_passes_test(is_staff_member)
@login_required
def listar_questoes_gestao(request):
    # Queryset base
    lista_questoes = Questao.objects.all()

    # =======================================================================
    # INÍCIO DA ADIÇÃO: Lógica de Ordenação
    # =======================================================================
    sort_by = request.GET.get('sort_by', '-id') # Padrão: mais recentes
    sort_options = {
        '-id': 'Mais Recentes',
        'id': 'Mais Antigas',
        'disciplina__nome': 'Disciplina (A-Z)',
        '-ano': 'Ano (Decrescente)',
        'ano': 'Ano (Crescente)',
    }
    
    # Aplica a ordenação ao queryset base ANTES de filtrar e paginar
    if sort_by in sort_options:
        lista_questoes = lista_questoes.order_by(sort_by)
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================

    # A função de filtro e paginação agora recebe o queryset já ordenado
    context = filtrar_e_paginar_questoes(request, lista_questoes, items_per_page=20)
    
    # Adiciona as variáveis de ordenação e outras informações específicas da página ao contexto
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
    })
    
    return render(request, 'gestao/listar_questoes.html', context)

@user_passes_test(is_staff_member)
@login_required
def adicionar_questao(request):
    if request.method == 'POST':
        form = GestaoQuestaoForm(request.POST, request.FILES)
        if form.is_valid():
            questao = form.save(commit=False)
            questao.criada_por = request.user
            questao.save()
            criar_log(
                ator=request.user,
                acao=LogAtividade.Acao.QUESTAO_CRIADA,
                alvo=questao,
                detalhes={'codigo_questao': questao.codigo}
            )
            messages.success(request, 'Questão adicionada com sucesso!')
            return redirect('gestao:listar_questoes')
    else:
        form = GestaoQuestaoForm()
    context = {'form': form, 'titulo': 'Adicionar Nova Questão'}
    return render(request, 'gestao/form_questao.html', context)

@user_passes_test(is_staff_member)
@login_required
def editar_questao(request, questao_id):
    questao = get_object_or_404(Questao, id=questao_id)
    if request.method == 'POST':
        form = GestaoQuestaoForm(request.POST, request.FILES, instance=questao)
        if form.is_valid():
            form.save()
            criar_log(
                ator=request.user,
                acao=LogAtividade.Acao.QUESTAO_EDITADA,
                alvo=questao,
                detalhes={'codigo_questao': questao.codigo}
            )
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
    questao = get_object_or_404(Questao, id=questao_id)
    try:
        questao_codigo = questao.codigo
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.QUESTAO_DELETADA,
            alvo=None,
            detalhes={'codigo_questao': questao_codigo}
        )
        questao.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'A questão "{questao_codigo}" foi excluída com sucesso.',
            'deleted_questao_id': questao_id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Não foi possível excluir a questão. Erro: {str(e)}'}, status=500)

@user_passes_test(is_staff_member)
@login_required
@require_POST
def questoes_acoes_em_massa(request):
    try:
        data = json.loads(request.body)
        questao_ids = data.get('ids', [])
        action = data.get('action')
        if not questao_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)
        
        queryset = Questao.objects.filter(id__in=questao_ids)
        if action == 'delete':
            for questao in queryset:
                criar_log(
                    ator=request.user,
                    acao=LogAtividade.Acao.QUESTAO_DELETADA,
                    alvo=None,
                    detalhes={'codigo_questao': questao.codigo, 'motivo': 'Ação de exclusão em massa'}
                )
            count, _ = queryset.delete()
            return JsonResponse({'status': 'success', 'message': f'{count} questões foram excluídas com sucesso.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =======================================================================
# VIEWS DE API (DISCIPLINA, ASSUNTO, ETC.)
# =======================================================================

@user_passes_test(is_staff_member)
@login_required
@require_POST
def adicionar_entidade_simples(request):
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
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.ENTIDADE_CRIADA,
            alvo=entidade,
            detalhes={'tipo': tipo_entidade.capitalize(), 'nome': entidade.nome}
        )
        return JsonResponse({'status': 'success', 'entidade': {'id': entidade.id, 'nome': entidade.nome}})
    return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)

@user_passes_test(is_staff_member)
@login_required
@require_POST
def adicionar_assunto(request):
    form = AssuntoForm(request.POST)
    if form.is_valid():
        nome = form.cleaned_data['nome']
        disciplina = form.cleaned_data['disciplina']
        if Assunto.objects.filter(nome__iexact=nome, disciplina=disciplina).exists():
            return JsonResponse({'status': 'error', 'message': 'Já existe um assunto com este nome para esta disciplina.'}, status=400)
        
        assunto = Assunto.objects.create(nome=nome, disciplina=disciplina)
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.ASSUNTO_CRIADO,
            alvo=assunto,
            detalhes={'assunto': assunto.nome, 'disciplina': disciplina.nome}
        )
        return JsonResponse({'status': 'success', 'assunto': {'id': assunto.id, 'nome': assunto.nome, 'disciplina': disciplina.nome}})
    return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)

@user_passes_test(is_staff_member)
@login_required
def visualizar_questao_ajax(request, questao_id):
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
# VIEWS DE GERENCIAMENTO DE NOTIFICAÇÕES
# =======================================================================

@user_passes_test(is_staff_member)
@login_required
def listar_notificacoes(request):
    status_filtro = request.GET.get('status', 'PENDENTE')
    base_queryset = Questao.objects.annotate(num_notificacoes=Count('notificacoes')).filter(num_notificacoes__gt=0)
    
    if status_filtro != 'TODAS':
        reports_na_aba_atual = Notificacao.objects.filter(questao_id=OuterRef('pk'), status=status_filtro)
        base_queryset = base_queryset.filter(Exists(reports_na_aba_atual))
    
    filtro_anotacao = Q(notificacoes__status=status_filtro) if status_filtro != 'TODAS' else Q()

    # --- LÓGICA DE ORDENAÇÃO ---
    sort_by = request.GET.get('sort_by', '-ultima_notificacao')
    sort_options = {
        '-ultima_notificacao': 'Mais Recentes',
        'ultima_notificacao': 'Mais Antigas',
        '-num_reports': 'Mais Reportadas',
        'num_reports': 'Menos Reportadas',
    }
    
    questoes_reportadas = base_queryset.annotate(
        num_reports=Count('notificacoes', filter=filtro_anotacao),
        ultima_notificacao=Max('notificacoes__data_criacao', filter=filtro_anotacao)
    )

    if sort_by in sort_options:
        questoes_reportadas = questoes_reportadas.order_by(sort_by)

    # --- Lógica de Prefetch e Paginação ---
    prefetch_queryset = Notificacao.objects.select_related('usuario_reportou__userprofile')
    if status_filtro != 'TODAS':
        prefetch_queryset = prefetch_queryset.filter(status=status_filtro)
    
    questoes_reportadas = questoes_reportadas.prefetch_related(
        Prefetch('notificacoes', queryset=prefetch_queryset.order_by('-data_criacao'), to_attr='reports_filtrados')
    )
    
    page_obj, page_numbers, per_page = paginar_itens(request, questoes_reportadas, 10)
    
    stats = {
        'pendentes_total': Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count(),
        'resolvidas_total': Notificacao.objects.filter(status=Notificacao.Status.RESOLVIDO).count(),
        'rejeitadas_total': Notificacao.objects.filter(status=Notificacao.Status.REJEITADO).count(),
    }
    
    context = {
        'questoes_agrupadas': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'status_ativo': status_filtro,
        'stats': stats,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_options': sort_options,
    }
    return render(request, 'gestao/listar_notificacoes_agrupadas.html', context)

@require_POST
@user_passes_test(is_staff_member)
@login_required
def notificacao_acao_agrupada(request, questao_id):
    # (Esta view já estava correta, sem necessidade de alterações)
    questao = get_object_or_404(Questao, id=questao_id)
    action = request.POST.get('action')
    status_original = request.POST.get('status_original', 'PENDENTE')
    notificacoes = Notificacao.objects.filter(questao=questao, status=status_original)
    count = notificacoes.count()
    message = ""
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
    # (Esta view já estava correta, sem necessidade de alterações)
    try:
        data = json.loads(request.body)
        questao_ids = data.get('ids', [])
        action = data.get('action')
        status_original = data.get('status_original', 'PENDENTE')
        if not questao_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)
        
        queryset = Notificacao.objects.filter(questao_id__in=questao_ids, status=status_original)
        
        for q_id in questao_ids:
            questao = get_object_or_404(Questao, id=q_id)
            count = queryset.filter(questao_id=q_id).count()
            if count > 0:
                log_acao_map = {'resolver': LogAtividade.Acao.NOTIFICACOES_RESOLVIDAS, 'rejeitar': LogAtividade.Acao.NOTIFICACOES_REJEITADAS, 'excluir': LogAtividade.Acao.NOTIFICACOES_DELETADAS}
                log_acao = log_acao_map.get(action)
                if log_acao:
                    criar_log(ator=request.user, acao=log_acao, alvo=questao, detalhes={'count': count, 'codigo_questao': questao.codigo, 'status_original': status_original, 'motivo': 'Ação em massa'})

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
# VIEWS DE GERENCIAMENTO DE USUÁRIOS
# =======================================================================

# gestao/views.py

# gestao/views.py

# gestao/views.py

@login_required
@user_passes_test(is_staff_member)
def listar_usuarios(request):
    base_queryset = User.objects.exclude(id=request.user.id)
    if not request.user.is_superuser:
        base_queryset = base_queryset.exclude(is_superuser=True)

    solicitacoes_pendentes = SolicitacaoExclusao.objects.filter(
        usuario_a_ser_excluido=OuterRef('pk'),
        status=SolicitacaoExclusao.Status.PENDENTE
    )
    base_queryset = base_queryset.annotate(
        tem_solicitacao_pendente=Exists(solicitacoes_pendentes)
    )

    # --- LÓGICA DE FILTRAGEM (sem alterações) ---
    filtro_q = request.GET.get('q', '').strip()
    filtro_permissao = request.GET.get('permissao', '')
    filtro_solicitacao = request.GET.get('solicitacao', '')
    if filtro_q:
        base_queryset = base_queryset.filter(
            Q(username__icontains=filtro_q) | Q(email__icontains=filtro_q)
        )
    if filtro_permissao:
        if filtro_permissao == 'superuser':
            base_queryset = base_queryset.filter(is_superuser=True)
        elif filtro_permissao == 'staff':
            base_queryset = base_queryset.filter(is_staff=True, is_superuser=False)
        elif filtro_permissao == 'comum':
            base_queryset = base_queryset.filter(is_staff=False)
    if filtro_solicitacao == 'pendente':
        base_queryset = base_queryset.filter(tem_solicitacao_pendente=True)

    # =======================================================================
    # INÍCIO DA CORREÇÃO FINAL: Lógica de Ordenação Hierárquica
    # =======================================================================
    sort_by = request.GET.get('sort_by', 'nivel')
    sort_options = {
        'nivel': 'Nível de Permissão',
        '-date_joined': 'Mais Recentes',
        'date_joined': 'Mais Antigos',
        'username': 'Nome (A-Z)',
        '-username': 'Nome (Z-A)',
    }
    
    # Define a hierarquia de ordenação correta.
    # A permissão é o critério principal. A solicitação é o secundário.
    order_fields = [
        '-is_superuser',             # 1. Superusuários sempre no topo.
        '-is_staff',                 # 2. Membros da equipe logo abaixo.
        '-tem_solicitacao_pendente', # 3. DENTRO de cada grupo, priorizar quem tem solicitação.
    ]

    # Adiciona o critério de desempate final, que é a escolha do usuário.
    if sort_by != 'nivel' and sort_by in sort_options:
        order_fields.append(sort_by)
    else:
        # Se a ordenação for por 'nivel' (padrão), o desempate final é o nome de usuário.
        order_fields.append('username')
    
    base_queryset = base_queryset.order_by(*order_fields)
    # =======================================================================
    # FIM DA CORREÇÃO FINAL
    # =======================================================================

    # --- LÓGICA DE PAGINAÇÃO ---
    paginated_object, page_numbers, per_page = paginar_itens(request, base_queryset, items_per_page=9)

    context = {
        'usuarios': paginated_object,
        'paginated_object': paginated_object,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_options': sort_options,
        'filtro_q': filtro_q,
        'filtro_permissao': filtro_permissao,
        'filtro_solicitacao': filtro_solicitacao,
        'total_usuarios': paginated_object.paginator.count,
    }
    return render(request, 'gestao/listar_usuarios.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def editar_usuario_staff(request, user_id):
    # (Esta view já estava correta, sem necessidade de alterações)
    usuario_alvo = get_object_or_404(User, id=user_id)

    # --- INÍCIO DA ADIÇÃO DE SEGURANÇA ---
    # Impede que um superusuário edite as permissões de outro superusuário.
    # Essas ações devem passar exclusivamente pelo sistema de quórum.
    if usuario_alvo.is_superuser and usuario_alvo != request.user:
        messages.error(request, "Você não pode editar as permissões de outro superusuário diretamente. Use os sistemas de despromoção ou exclusão.")
        return redirect('gestao:listar_usuarios')
    # --- FIM DA ADIÇÃO DE SEGURANÇA ---
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


# =======================================================================
# VIEWS DE PROMOÇÃO DE SUPERUSER (SISTEMA DE QUORUM)
# =======================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def solicitar_promocao_superuser(request, user_id):
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
    solicitacoes = PromocaoSuperuser.objects.filter(status=PromocaoSuperuser.Status.PENDENTE).select_related('usuario_alvo', 'solicitado_por')
    context = {'solicitacoes': solicitacoes}
    return render(request, 'gestao/listar_solicitacoes_promocao.html', context)

@require_POST
@login_required
@transaction.atomic
@user_passes_test(lambda u: u.is_superuser)
def aprovar_promocao_superuser(request, promocao_id):
    promocao = get_object_or_404(PromocaoSuperuser, id=promocao_id)
    ja_aprovou = promocao.aprovado_por.filter(pk=request.user.pk).exists()
    
    success, message = promocao.aprovar(request.user)
    
    if not ja_aprovou:
        log_acao = LogAtividade.Acao.USUARIO_PROMOVIDO_SUPERUSER if success else LogAtividade.Acao.SOLICITACAO_PROMOCAO_APROVADA
        criar_log(
            ator=request.user, acao=log_acao, alvo=promocao, 
            detalhes={'usuario_alvo': promocao.usuario_alvo.username, 'aprovador_atual': request.user.username, 'quorum_atingido': success}
        )
    
    (messages.success if success else messages.info)(request, message)
    return redirect('gestao:listar_solicitacoes_promocao')


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def cancelar_promocao_superuser(request, promocao_id):
    try:
        promocao = get_object_or_404(
            PromocaoSuperuser, id=promocao_id, 
            solicitado_por=request.user, status=PromocaoSuperuser.Status.PENDENTE
        )
        # Crie a Ação 'SOLICITACAO_PROMOCAO_CANCELADA' no seu modelo LogAtividade se ainda não existir
        criar_log(
            ator=request.user, acao='SOLICITACAO_PROMOCAO_CANCELADA', 
            alvo=promocao, detalhes={'usuario_alvo': promocao.usuario_alvo.username}
        )
        promocao.delete()
        messages.success(request, 'Sua solicitação de promoção foi cancelada com sucesso.')
    except PromocaoSuperuser.DoesNotExist:
        messages.error(request, 'Solicitação não encontrada ou você não tem permissão para cancelá-la.')
    return redirect('gestao:listar_solicitacoes_promocao')

# =======================================================================
# VIEWS DE GERENCIAMENTO DE LOGS (AUDITORIA)
# =======================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_logs_atividade(request):
    logs_list = LogAtividade.objects.select_related('ator').all()

    # --- LÓGICA DE FILTRAGEM ---
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
    
    # --- LÓGICA DE ORDENAÇÃO ---
    sort_by = request.GET.get('sort_by', '-data_criacao')
    sort_options = {
        '-data_criacao': 'Mais Recentes',
        'data_criacao': 'Mais Antigos',
    }
    if sort_by in sort_options:
        logs_list = logs_list.order_by(sort_by)

    # --- LÓGICA DE PAGINAÇÃO ---
    logs_paginados, page_numbers, per_page = paginar_itens(request, logs_list, 20)
    
    context = {
        'logs': logs_paginados,
        'paginated_object': logs_paginados,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_options': sort_options,
        'filtro_q': filtro_q,
        'filtro_acao': filtro_acao,
        'filtro_data_inicio': filtro_data_inicio,
        'filtro_data_fim': filtro_data_fim,
        'acao_choices': LogAtividade.Acao.choices,
    }
    return render(request, 'gestao/listar_logs_atividade.html', context)

@require_POST
@user_passes_test(lambda u: u.is_superuser)
def deletar_log_atividade(request, log_id):
    log = get_object_or_404(LogAtividade, id=log_id)
    if log.ator == request.user:
        return JsonResponse({'status': 'error', 'message': 'Você não pode excluir seus próprios registros.'}, status=403)
    log.delete(user=request.user)
    return JsonResponse({'status': 'success', 'message': 'Registro movido para a lixeira.', 'deleted_log_id': log_id})

@require_POST
@user_passes_test(lambda u: u.is_superuser)
def logs_acoes_em_massa(request):
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
                log.delete(user=request.user)
            
            message = f'{len(deleted_ids)} registro(s) foram movidos para a lixeira.'
            if len(deleted_ids) < len(log_ids):
                message += ' Seus próprios registros não foram alterados.'
            
            return JsonResponse({'status': 'success', 'message': message, 'deleted_ids': deleted_ids})
        return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



@login_required
@user_passes_test(is_staff_member)
def listar_solicitacoes_exclusao(request):
    solicitacoes_list = SolicitacaoExclusao.objects.filter(
        status=SolicitacaoExclusao.Status.PENDENTE
    ).select_related('usuario_a_ser_excluido', 'solicitado_por')

    # --- LÓGICA DE ORDENAÇÃO ---
    sort_by = request.GET.get('sort_by', '-data_solicitacao')
    sort_options = {
        '-data_solicitacao': 'Mais Recentes',
        'data_solicitacao': 'Mais Antigas',
    }
    if sort_by in sort_options:
        solicitacoes_list = solicitacoes_list.order_by(sort_by)

    # --- LÓGICA DE PAGINAÇÃO ---
    solicitacoes_paginadas, page_numbers, per_page = paginar_itens(request, solicitacoes_list, items_per_page=10)

    context = {
        'solicitacoes': solicitacoes_paginadas,
        'paginated_object': solicitacoes_paginadas,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_options': sort_options,
        'total_solicitacoes': solicitacoes_paginadas.paginator.count,
    }
    return render(request, 'gestao/listar_solicitacoes_exclusao.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def sugerir_exclusao_usuario(request, user_id):
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

        solicitacao = SolicitacaoExclusao.objects.create(
            usuario_a_ser_excluido=usuario_alvo,
            solicitado_por=request.user,
            motivo=motivo_completo
        )
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_CRIADA,
            alvo=solicitacao,
            detalhes={'usuario_alvo': usuario_alvo.username}
        )
        
        return JsonResponse({'status': 'success', 'message': 'Sua sugestão de exclusão foi enviada para revisão por um superusuário.'})
    
    return JsonResponse({'status': 'error', 'message': 'Por favor, corrija os erros abaixo.', 'field_errors': form.errors}, status=400)

@login_required
@user_passes_test(is_staff_member)
@require_POST
def cancelar_solicitacao_exclusao(request, solicitacao_id):
    try:
        solicitacao = get_object_or_404(
            SolicitacaoExclusao, 
            id=solicitacao_id, 
            solicitado_por=request.user, 
            status=SolicitacaoExclusao.Status.PENDENTE
        )
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_CANCELADA,
            alvo=solicitacao,
            detalhes={'usuario_alvo': solicitacao.usuario_a_ser_excluido.username}
        )

        solicitacao.delete()

        return JsonResponse({
            'status': 'success',
            'message': 'Sua solicitação de exclusão foi cancelada com sucesso.',
            'solicitacao_id': solicitacao_id
        })
    except SolicitacaoExclusao.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Solicitação não encontrada ou você não tem permissão para cancelá-la.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro: {str(e)}'}, status=500)

# gestao/views.py

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def aprovar_solicitacao_exclusao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, status=SolicitacaoExclusao.Status.PENDENTE)
    usuario_a_deletar = solicitacao.usuario_a_ser_excluido

    if User.objects.filter(is_superuser=True, is_active=True).count() <= 1 and usuario_a_deletar.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível aprovar a exclusão do único superusuário.'}, status=403)

    email_alvo = usuario_a_deletar.email
    username_alvo = usuario_a_deletar.username
    motivo_texto = solicitacao.motivo
    message = ""

    try:
        # Lógica de notificação por e-mail...
        if email_alvo:
            try:
                enviar_email_com_template(
                    request,
                    subject='Sua conta na plataforma Raio-X da Aprovação foi removida',
                    template_name='gestao/email_conta_excluida.html',
                    context={'user': usuario_a_deletar, 'motivo_texto': motivo_texto},
                    recipient_list=[email_alvo]
                )
                message = f'A solicitação foi aprovada, o usuário "{username_alvo}" foi excluído e notificado.'
            except Exception as e:
                message = f'A solicitação foi aprovada e o usuário "{username_alvo}" foi excluído, mas o envio de e-mail falhou: {e}'
        else:
            message = f'A solicitação foi aprovada e o usuário "{username_alvo}" foi excluído. (Sem e-mail para notificar).'

        # =======================================================================
        # INÍCIO DA CORREÇÃO: Verificação de existência do solicitante
        # =======================================================================
        solicitado_por_username = solicitacao.solicitado_por.username if solicitacao.solicitado_por else "(Usuário solicitante deletado)"
        # =======================================================================
        # FIM DA CORREÇÃO
        # =======================================================================

        # Criação de logs...
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_APROVADA,
            alvo=solicitacao,
            detalhes={'usuario_excluido': usuario_a_deletar.username, 'solicitado_por': solicitado_por_username}
        )
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.USUARIO_DELETADO,
            alvo=None,
            detalhes={'usuario_deletado': usuario_a_deletar.username, 'motivo': f'Aprovação da solicitação #{solicitacao.id}'}
        )

        # Atualização e exclusão...
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
    solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, status=SolicitacaoExclusao.Status.PENDENTE)
    
    try:
        # =======================================================================
        # INÍCIO DA CORREÇÃO: Verificação de existência do solicitante
        # =======================================================================
        solicitado_por_username = solicitacao.solicitado_por.username if solicitacao.solicitado_por else "(Usuário solicitante deletado)"
        # =======================================================================
        # FIM DA CORREÇÃO
        # =======================================================================

        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_REJEITADA,
            alvo=solicitacao,
            detalhes={
                'usuario_alvo': solicitacao.usuario_a_ser_excluido.username, 
                'solicitado_por': solicitado_por_username
            }
        )

        solicitacao.status = SolicitacaoExclusao.Status.REJEITADO
        solicitacao.revisado_por = request.user
        solicitacao.data_revisao = timezone.now()
        solicitacao.save(update_fields=['status', 'revisado_por', 'data_revisao'])

        return JsonResponse({
            'status': 'success',
            'message': f'A solicitação para excluir o usuário "{solicitacao.usuario_a_ser_excluido.username}" foi rejeitada.',
            'solicitacao_id': solicitacao_id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def rejeitar_solicitacao_exclusao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, status=SolicitacaoExclusao.Status.PENDENTE)
    
    try:
        # =======================================================================
        # INÍCIO DA CORREÇÃO: Verificação de existência do solicitante
        # =======================================================================
        solicitado_por_username = solicitacao.solicitado_por.username if solicitacao.solicitado_por else "(Usuário solicitante deletado)"
        # =======================================================================
        # FIM DA CORREÇÃO
        # =======================================================================

        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_REJEITADA,
            alvo=solicitacao,
            detalhes={
                'usuario_alvo': solicitacao.usuario_a_ser_excluido.username, 
                'solicitado_por': solicitado_por_username
            }
        )

        solicitacao.status = SolicitacaoExclusao.Status.REJEITADO
        solicitacao.revisado_por = request.user
        solicitacao.data_revisao = timezone.now()
        solicitacao.save(update_fields=['status', 'revisado_por', 'data_revisao'])

        return JsonResponse({
            'status': 'success',
            'message': f'A solicitação para excluir o usuário "{solicitacao.usuario_a_ser_excluido.username}" foi rejeitada.',
            'solicitacao_id': solicitacao_id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro: {str(e)}'}, status=500)
    
@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
@transaction.atomic
def deletar_usuario(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)
    form = ExclusaoUsuarioForm(request.POST)

    if usuario_alvo == request.user:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Você não pode excluir sua própria conta.'}, status=403)
    if usuario_alvo.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível excluir o único superusuário do sistema.'}, status=403)

    if form.is_valid():
        motivo_predefinido_chave = form.cleaned_data['motivo_predefinido']
        motivo_predefinido_texto = dict(form.fields['motivo_predefinido'].choices)[motivo_predefinido_chave]
        justificativa = form.cleaned_data.get('justificativa', '')
        
        motivo_final_para_email = f"{motivo_predefinido_texto}"
        if justificativa:
            motivo_final_para_email += f" (Detalhes: {justificativa})"
            
        email_alvo = usuario_alvo.email
        username_alvo = usuario_alvo.username

        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.USUARIO_DELETADO,
            alvo=None,
            detalhes={
                'usuario_deletado': usuario_alvo.username,
                'motivo': motivo_final_para_email
            }
        )

        message = ""
        if email_alvo:
            try:
                enviar_email_com_template(
                    request,
                    subject='Sua conta na plataforma Raio-X da Aprovação foi removida',
                    template_name='gestao/email_conta_excluida.html',
                    context={'user': usuario_alvo, 'motivo_texto': motivo_final_para_email},
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
    


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def promover_diretamente_superuser(request, user_id):
    """
    View para o caso especial onde há apenas 1 superuser,
    permitindo a promoção direta sem quorum.
    """
    if User.objects.filter(is_superuser=True, is_active=True).count() > 1:
        messages.error(request, "A promoção direta só é permitida quando há apenas um superusuário no sistema.")
        return redirect('gestao:listar_usuarios')

    usuario_alvo = get_object_or_404(User, id=user_id, is_superuser=False)
    
    usuario_alvo.is_superuser = True
    usuario_alvo.is_staff = True
    usuario_alvo.save(update_fields=['is_superuser', 'is_staff'])

    criar_log(
        ator=request.user,
        acao=LogAtividade.Acao.USUARIO_PROMOVIDO_SUPERUSER,
        alvo=usuario_alvo,
        detalhes={
            'usuario_alvo': usuario_alvo.username,
            'motivo': 'Promoção direta (único superusuário no sistema)'
        }
    )

    messages.success(request, f'Usuário "{usuario_alvo.username}" promovido a Superusuário diretamente.')
    return redirect('gestao:listar_usuarios')





@login_required
@user_passes_test(lambda u: u.is_superuser)
def solicitar_despromocao_superuser(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id, is_superuser=True)
    if request.method == 'POST':
        justificativa = request.POST.get('justificativa')
        if justificativa:
            despromocao, created = DespromocaoSuperuser.objects.get_or_create(
                usuario_alvo=usuario_alvo,
                status=DespromocaoSuperuser.Status.PENDENTE,
                defaults={'solicitado_por': request.user, 'justificativa': justificativa}
            )
            if created:
                criar_log(
                    ator=request.user, 
                    acao=LogAtividade.Acao.SOLICITACAO_DESPROMOCAO_CRIADA, 
                    alvo=despromocao, 
                    detalhes={'usuario_alvo': usuario_alvo.username}
                )
                messages.success(request, 'Solicitação de despromoção enviada para revisão por outros superusuários.')
            else:
                messages.warning(request, 'Já existe uma solicitação de despromoção pendente para este usuário.')
            return redirect('gestao:listar_usuarios') # Redireciona para a lista de usuários com a mensagem
        else:
            messages.error(request, "A justificativa é obrigatória.")
    
    context = {'usuario_alvo': usuario_alvo}
    return render(request, 'gestao/solicitar_despromocao.html', context)



@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_solicitacoes_despromocao(request):
    solicitacoes = DespromocaoSuperuser.objects.filter(status=DespromocaoSuperuser.Status.PENDENTE).select_related('usuario_alvo', 'solicitado_por')
    context = {'solicitacoes': solicitacoes}
    return render(request, 'gestao/listar_solicitacoes_despromocao.html', context)

@require_POST
@login_required
@transaction.atomic
@user_passes_test(lambda u: u.is_superuser)
def aprovar_despromocao_superuser(request, despromocao_id):
    despromocao = get_object_or_404(DespromocaoSuperuser, id=despromocao_id, status=DespromocaoSuperuser.Status.PENDENTE)
    
    usuario_alvo_username = despromocao.usuario_alvo.username
    usuario_alvo_obj = despromocao.usuario_alvo

    status, message = despromocao.aprovar(request.user)

    if status == 'QUORUM_MET':
        is_self_approval = (request.user == usuario_alvo_obj)
        log_details = {
            'usuario_alvo': usuario_alvo_username,
            'aprovador_atual': request.user.username,
            'quorum_atingido': True,
            'motivo': "Confirmação final (quorum atingido)" if not is_self_approval else "Usuário confirmou a própria despromoção (quorum=1)"
        }
        
        # 1. Cria o log ANTES de qualquer alteração final
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.USUARIO_DESPROMOVIDO_SUPERUSER,
            alvo=despromocao,
            detalhes=log_details
        )
        
        # 2. Executa as ações finais de salvamento
        usuario_alvo_obj.is_superuser = False
        usuario_alvo_obj.save(update_fields=['is_superuser'])
        despromocao.save(update_fields=['status'])
        
        # 3. Define a mensagem de sucesso
        final_message = f"Você confirmou sua própria despromoção." if is_self_approval else message
        messages.success(request, final_message)

    elif status == 'APPROVAL_REGISTERED':
        criar_log(
            ator=request.user, 
            acao=LogAtividade.Acao.SOLICITACAO_DESPROMOCAO_APROVADA, 
            alvo=despromocao,
            detalhes={
                'usuario_alvo': usuario_alvo_username, 
                'aprovador_atual': request.user.username,
                'quorum_atingido': False
            }
        )
        messages.info(request, message)
    else: # status == 'FAILED'
        messages.error(request, message)
    
    return redirect('gestao:listar_solicitacoes_despromocao')

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def cancelar_despromocao_superuser(request, despromocao_id):
    try:
        despromocao = get_object_or_404(
            DespromocaoSuperuser,
            id=despromocao_id,
            solicitado_por=request.user,
            status=DespromocaoSuperuser.Status.PENDENTE
        )
        # =======================================================================
        # INÍCIO DA ADIÇÃO: Log de cancelamento
        # =======================================================================
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_DESPROMOCAO_CANCELADA,
            alvo=despromocao,
            detalhes={'usuario_alvo': despromocao.usuario_alvo.username}
        )
        # =======================================================================
        # FIM DA ADIÇÃO
        # =======================================================================
        despromocao.delete()
        messages.success(request, 'Sua solicitação de despromoção foi cancelada com sucesso.')
    except DespromocaoSuperuser.DoesNotExist:
        messages.error(request, 'Solicitação não encontrada ou você não tem permissão para cancelá-la.')
    
    return redirect('gestao:listar_solicitacoes_despromocao')



@login_required
@user_passes_test(lambda u: u.is_superuser)
def solicitar_exclusao_superuser(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id, is_superuser=True)

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
                usuario_alvo=usuario_alvo,
                status=ExclusaoSuperuser.Status.PENDENTE,
                defaults={'solicitado_por': request.user, 'justificativa': justificativa}
            )
            if created:
                criar_log(
                    ator=request.user, 
                    acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_SUPERUSER_CRIADA, 
                    alvo=exclusao, 
                    detalhes={'usuario_alvo': usuario_alvo.username}
                )
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
    solicitacoes = ExclusaoSuperuser.objects.filter(status=ExclusaoSuperuser.Status.PENDENTE).select_related('usuario_alvo', 'solicitado_por')
    context = {'solicitacoes': solicitacoes}
    return render(request, 'gestao/listar_solicitacoes_exclusao_superuser.html', context)

# gestao/views.py

# gestao/views.py

# ... (outros imports e views) ...

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
@transaction.atomic
def aprovar_exclusao_superuser(request, exclusao_id):
    exclusao = get_object_or_404(ExclusaoSuperuser.objects.select_for_update(), id=exclusao_id, status=ExclusaoSuperuser.Status.PENDENTE)
    
    usuario_alvo_username = exclusao.usuario_alvo.username
    usuario_alvo_obj = exclusao.usuario_alvo

    # =======================================================================
    # CORREÇÃO FINAL DA LÓGICA DE SEGURANÇA
    # =======================================================================
    # A verificação de segurança é feita ANTES de chamar .aprovar()
    # A regra é: NÃO permitir que a contagem de superusuários chegue a ZERO.
    # Portanto, bloqueamos a exclusão apenas se a contagem atual for 1.
    if User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        messages.error(request, f"Ação negada: A exclusão de '{usuario_alvo_username}' deixaria o sistema sem superusuários, o que não é permitido.")
        return redirect('gestao:listar_solicitacoes_exclusao_superuser')
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================

    status, message = exclusao.aprovar(request.user)

    if status == 'QUORUM_MET':
        is_self_approval = (request.user == usuario_alvo_obj)
        log_details = {
            'usuario_alvo': usuario_alvo_username,
            'aprovador_atual': request.user.username,
            'quorum_atingido': True,
            'motivo': "Confirmação final (quorum atingido)" if not is_self_approval else "Usuário confirmou a própria exclusão (quorum=1)"
        }
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.USUARIO_DELETADO,
            alvo=None,
            detalhes=log_details
        )
        
        usuario_alvo_obj.delete()
        
        final_message = f"Você confirmou sua própria exclusão. Sua conta foi removida." if is_self_approval else message
        messages.success(request, final_message)
        
    elif status == 'APPROVAL_REGISTERED':
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_SUPERUSER_APROVADA,
            alvo=exclusao,
            detalhes={
                'usuario_alvo': usuario_alvo_username,
                'aprovador_atual': request.user.username,
                'quorum_atingido': False
            }
        )
        messages.info(request, message)

    else: # status == 'FAILED'
        messages.error(request, message)
    
    return redirect('gestao:listar_solicitacoes_exclusao_superuser')


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def cancelar_exclusao_superuser(request, exclusao_id):
    try:
        exclusao = get_object_or_404(
            ExclusaoSuperuser,
            id=exclusao_id,
            solicitado_por=request.user,
            status=ExclusaoSuperuser.Status.PENDENTE
        )
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_SUPERUSER_CANCELADA,
            alvo=exclusao,
            detalhes={'usuario_alvo': exclusao.usuario_alvo.username}
        )
        exclusao.delete()
        messages.success(request, 'Sua solicitação de exclusão foi cancelada com sucesso.')
    except ExclusaoSuperuser.DoesNotExist:
        messages.error(request, 'Solicitação não encontrada ou você não tem permissão para cancelá-la.')
    
    return redirect('gestao:listar_solicitacoes_exclusao_superuser')



    
# gestao/views.py

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def mover_logs_antigos_para_lixeira(request):
    """
    Move logs ativos com mais de 'days_threshold' dias para a lixeira (soft delete).
    O número de dias é passado via POST.
    """
    try:
        # Pega o valor do formulário, com 180 como padrão de segurança
        days_threshold = int(request.POST.get('days', 180))
    except (ValueError, TypeError):
        days_threshold = 180 # Fallback se o valor for inválido

    threshold_date = timezone.now() - timedelta(days=days_threshold)
    
    logs_para_mover = LogAtividade.objects.filter(data_criacao__lt=threshold_date)
    
    count = logs_para_mover.count()
    if count == 0:
        messages.info(request, f"Nenhum log com mais de {days_threshold} dias foi encontrado para mover para a lixeira.")
        return redirect('gestao:listar_logs_atividade')
        
    for log in logs_para_mover:
        log.delete(user=request.user) # Chama o soft delete

    messages.success(request, f"{count} registro(s) de log com mais de {days_threshold} dias foram movidos para a lixeira com sucesso.")
    return redirect('gestao:listar_logs_atividade')

# gestao/views.py

@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_logs_deletados(request):
    logs_list = LogAtividade.all_logs.filter(is_deleted=True).select_related('ator', 'deleted_by')

    # --- LÓGICA DE FILTRAGEM ---
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
        
    # --- LÓGICA DE ORDENAÇÃO ---
    sort_by = request.GET.get('sort_by', '-deleted_at')
    sort_options = {
        '-deleted_at': 'Exclusão Mais Recente',
        'deleted_at': 'Exclusão Mais Antiga',
    }
    if sort_by in sort_options:
        logs_list = logs_list.order_by(sort_by)

    # --- LÓGICA DE PAGINAÇÃO ---
    logs_paginados, page_numbers, per_page = paginar_itens(request, logs_list, 20)
    
    context = {
        'logs': logs_paginados,
        'paginated_object': logs_paginados,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_options': sort_options,
        'filtro_q': filtro_q,
        'filtro_acao': filtro_acao,
        'filtro_data_inicio': filtro_data_inicio,
        'filtro_data_fim': filtro_data_fim,
        'acao_choices': LogAtividade.Acao.choices,
    }
    return render(request, 'gestao/listar_logs_deletados.html', context)