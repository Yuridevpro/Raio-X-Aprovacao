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
from django.http import HttpResponseBadRequest
from django.urls import reverse
from collections import defaultdict
from .forms import SimuladoWizardForm, SimuladoForm
from .forms import SimuladoMetaForm # Adicionar importação
from gamificacao.models import Conquista, Avatar, Borda

from django.contrib.auth.models import User
from .models import LogAtividade, ExclusaoLogPermanente
from .utils import criar_log

from simulados.models import Simulado, StatusSimulado
from django.views.decorators.http import require_POST # Adicione este import

from gamificacao.models import Conquista, Avatar, Borda, Banner
from .forms import ConquistaForm, AvatarForm, BordaForm, BannerForm
from django.template.loader import render_to_string # Adicionar importação

# Importações de modelos de outros apps
from pratica.models import Notificacao
from questoes.models import Questao, Disciplina, Banca, Instituicao, Assunto

# Importações de forms de outros apps
from questoes.forms import GestaoQuestaoForm, EntidadeSimplesForm, AssuntoForm

# Importações de utils de outros apps
from usuarios.utils import enviar_email_com_template
from questoes.utils import paginar_itens, filtrar_e_paginar_questoes, filtrar_e_paginar_lixeira, filtrar_e_paginar_questoes_com_prefixo

# Importações locais do app 'gestao'
from .models import SolicitacaoExclusao, PromocaoSuperuser, LogAtividade, DespromocaoSuperuser, ExclusaoSuperuser
from .forms import StaffUserForm, ExclusaoUsuarioForm
from .utils import criar_log

from pratica.models import Comentario
from gamificacao.models import Conquista
from simulados.models import Simulado
from .forms import StaffUserForm, ExclusaoUsuarioForm, ConquistaForm, SimuladoForm
from django.contrib.contenttypes.models import ContentType

from .forms import SimuladoForm # A view agora usa o SimuladoForm

from gamificacao.models import Conquista
from .forms import ConquistaForm

from gamificacao.models import Conquista, Avatar, Borda, Banner, GamificationSettings
from .forms import ConquistaForm, AvatarForm, BordaForm, BannerForm, GamificationSettingsForm

from django.utils import timezone
from django.db.models import OuterRef, Subquery, Max


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
    """
    total_questoes = Questao.objects.count()
    notificacoes_pendentes = Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count()
    solicitacoes_pendentes_count = SolicitacaoExclusao.objects.filter(status=SolicitacaoExclusao.Status.PENDENTE).count()
    total_simulados = Simulado.objects.filter(is_oficial=True).count()
    
    # =======================================================================
    # ADIÇÃO: Contagem de todos os itens de gamificação
    # =======================================================================
    total_conquistas = Conquista.objects.count()
    total_avatares = Avatar.objects.count()
    total_bordas = Borda.objects.count()
    total_banners = Banner.objects.count()
    total_gamificacao = total_conquistas + total_avatares + total_bordas + total_banners
    # =======================================================================

    promocoes_pendentes_count = 0
    despromocoes_pendentes_count = 0
    exclusoes_superuser_pendentes_count = 0

    if request.user.is_superuser:
        promocoes_pendentes_count = PromocaoSuperuser.objects.filter(status=PromocaoSuperuser.Status.PENDENTE).count()
        despromocoes_pendentes_count = DespromocaoSuperuser.objects.filter(status=DespromocaoSuperuser.Status.PENDENTE).count()
        exclusoes_superuser_pendentes_count = ExclusaoSuperuser.objects.filter(status=ExclusaoSuperuser.Status.PENDENTE).count()

    context = {
        'total_questoes': total_questoes,
        'notificacoes_pendentes': notificacoes_pendentes,
        'solicitacoes_pendentes_count': solicitacoes_pendentes_count,
        'total_simulados': total_simulados,
        # Passando as novas contagens para o template
        'total_conquistas': total_conquistas,
        'total_avatares': total_avatares,
        'total_bordas': total_bordas,
        'total_banners': total_banners,
        'total_gamificacao': total_gamificacao,
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
    
    # =======================================================================
    # INÍCIO DA CORREÇÃO
    # As chaves do dicionário foram renomeadas para corresponderem
    # exatamente ao que o template _filtros_questoes.html espera.
    # Ex: 'disciplinas_para_filtro' virou 'disciplinas'.
    # =======================================================================
    context.update({
        'sort_by': sort_by,
        'sort_options': sort_options,
        'disciplinas': Disciplina.objects.filter(questao__id__in=deleted_questoes_ids).distinct().order_by('nome'),
        'bancas': Banca.objects.filter(questao__id__in=deleted_questoes_ids).distinct().order_by('nome'),
        'instituicoes': Instituicao.objects.filter(questao__id__in=deleted_questoes_ids).distinct().order_by('nome'),
        'anos': Questao.all_objects.filter(id__in=deleted_questoes_ids).exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano'),
    })
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================
    
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

# gestao/views.py

# ... (todos os seus outros imports devem estar aqui)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Count, Q, Max, Prefetch
from django.contrib.contenttypes.models import ContentType
from pratica.models import Notificacao, Questao, Comentario
from questoes.utils import paginar_itens
# ... (etc)


@user_passes_test(is_staff_member)
@login_required
def listar_notificacoes(request):
    """
    Renderiza o Painel de Moderação, com a lógica de contagem e da aba "Todos" corrigida.
    """
    tipo_ativo = request.GET.get('tipo', 'questao')
    status_filtro = request.GET.get('status', 'PENDENTE')
    sort_by = request.GET.get('sort_by')
    
    objetos_reportados = None
    sort_options = {}

    filtro_status_q = Q(notificacoes__status=status_filtro) if status_filtro != 'TODAS' else Q()
    
    # Busca os ContentTypes uma vez para usar em toda a view
    ct_questao = ContentType.objects.get_for_model(Questao)
    ct_comentario = ContentType.objects.get_for_model(Comentario)

    if tipo_ativo == 'questao':
        base_queryset = Questao.objects.filter(filtro_status_q).distinct()
        
        sort_by = sort_by or '-ultima_notificacao'
        sort_options = {
            '-ultima_notificacao': 'Mais Recentes', 'ultima_notificacao': 'Mais Antigas',
            '-num_reports': 'Mais Reportadas',
        }
        
        objetos_reportados = base_queryset.annotate(
            num_reports=Count('notificacoes', filter=filtro_status_q),
            ultima_notificacao=Max('notificacoes__data_criacao', filter=filtro_status_q)
        ).order_by(sort_by)

        prefetch_queryset = Notificacao.objects.select_related('usuario_reportou__userprofile')
        if status_filtro != 'TODAS':
            prefetch_queryset = prefetch_queryset.filter(status=status_filtro)
        
        objetos_reportados = objetos_reportados.prefetch_related(
            Prefetch('notificacoes', queryset=prefetch_queryset.order_by('-data_criacao'), to_attr='reports_filtrados')
        )
        
    elif tipo_ativo == 'comentario':
        base_queryset = Comentario.objects.filter(filtro_status_q).distinct()

        sort_by = sort_by or '-ultima_notificacao'
        sort_options = {'-ultima_notificacao': 'Mais Recentes', '-num_reports': 'Mais Reportados'}
        
        objetos_reportados = base_queryset.annotate(
            num_reports=Count('notificacoes', filter=filtro_status_q),
            ultima_notificacao=Max('notificacoes__data_criacao', filter=filtro_status_q)
        ).select_related('usuario__userprofile', 'questao').order_by(sort_by)

        prefetch_queryset = Notificacao.objects.select_related('usuario_reportou__userprofile')
        if status_filtro != 'TODAS':
            prefetch_queryset = prefetch_queryset.filter(status=status_filtro)
        
        objetos_reportados = objetos_reportados.prefetch_related(
            Prefetch('notificacoes', queryset=prefetch_queryset.order_by('-data_criacao'), to_attr='reports_filtrados')
        )
    
    else:
        objetos_reportados = Questao.objects.none()

    page_obj, page_numbers, per_page = paginar_itens(request, objetos_reportados, 10)
    
    stats = {
        'pendentes_questao': Notificacao.objects.filter(status='PENDENTE', content_type=ct_questao).count(),
        'pendentes_comentario': Notificacao.objects.filter(status='PENDENTE', content_type=ct_comentario).count(),
        'resolvidas_total': Notificacao.objects.filter(status='RESOLVIDO').count(),
        'rejeitadas_total': Notificacao.objects.filter(status='REJEITADO').count(),
    }

    context = {
        'objetos_agrupados': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_options': sort_options,
        'stats': stats,
        'tipo_ativo': tipo_ativo,
        'status_ativo': status_filtro,
    }

    # =======================================================================
    # INÍCIO DA ADIÇÃO: Passando o ID do ContentType para o contexto
    # =======================================================================
    # Adiciona o ID do ContentType de Comentário ao contexto se essa for a aba ativa.
    # Isso torna a informação disponível para o template do card de denúncia.
    if tipo_ativo == 'comentario':
        context['comentario_content_type_id'] = ct_comentario.id
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================

    return render(request, 'gestao/listar_notificacoes_agrupadas.html', context)

@require_POST
@user_passes_test(is_staff_member)
@login_required
@transaction.atomic # Adiciona transação para garantir a integridade de todas as operações
def notificacao_acao_agrupada(request, content_type_id, object_id):
    """
    Aplica uma ação a todas as notificações de um mesmo alvo e envia os e-mails
    apropriados para os usuários envolvidos (quem reportou e/ou o autor do conteúdo).
    """
    try:
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        alvo = content_type.get_object_for_this_type(pk=object_id)
    except:
        return JsonResponse({'status': 'error', 'message': 'Alvo da notificação não encontrado.'}, status=404)

    action = request.POST.get('action')
    status_original = request.POST.get('status_original', 'PENDENTE')
    
    # Busca as notificações relacionadas, otimizando a busca dos perfis de usuário
    notificacoes = Notificacao.objects.filter(
        content_type=content_type, 
        object_id=object_id, 
        status=status_original
    ).select_related('usuario_reportou__userprofile')

    count = notificacoes.count()
    alvo_log_str = alvo.codigo if isinstance(alvo, Questao) else str(alvo)
    log_details = {'count': count, 'alvo_str': alvo_log_str}
    
    # --- LÓGICA DE AÇÕES E NOTIFICAÇÕES POR E-MAIL ---
    
    if action == 'resolver':
        # Para erros de questão, notifica todos que reportaram que o problema foi corrigido.
        if isinstance(alvo, Questao):
            for n in notificacoes:
                if n.usuario_reportou and n.usuario_reportou.email:
                    enviar_email_com_template(
                        request, 
                        'Sua Notificação foi Resolvida!',
                        'gestao/email_notificacao_resolvida.html',
                        {'user': n.usuario_reportou, 'questao': alvo},
                        [n.usuario_reportou.email]
                    )
        
        # Atualiza o status das notificações
        notificacoes.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
        criar_log(ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_RESOLVIDAS, alvo=alvo, detalhes=log_details)
        message = f'{count} notificação(ões) para o item "{alvo}" foram marcadas como "Resolvido".'
    
    elif action == 'rejeitar':
        notificacoes.update(status=Notificacao.Status.REJEITADO)
        criar_log(ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_REJEITADAS, alvo=alvo, detalhes=log_details)
        message = f'{count} notificação(ões) para o item "{alvo}" foram rejeitadas.'

    elif action == 'deletar_comentario_e_resolver' and isinstance(alvo, Comentario):
        comentario = alvo
        autor = comentario.usuario
        
        # 1. Notifica o autor do comentário sobre a remoção
        if autor and autor.email:
            enviar_email_com_template(
                request,
                'Aviso Sobre Seu Comentário',
                'gestao/email_comentario_removido.html',
                {
                    'user_profile': autor.userprofile,
                    'questao': comentario.questao,
                    'comentario_conteudo': comentario.conteudo
                },
                [autor.email]
            )
        
        # 2. Deleta o comentário e resolve todas as denúncias associadas a ele
        comentario_conteudo_log = comentario.conteudo
        comentario.delete()
        notificacoes.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
        
        # 3. Cria um log detalhado da ação
        log_details['comentario_deletado'] = comentario_conteudo_log
        log_details['autor_notificado'] = autor.username if autor else 'N/A'
        criar_log(ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_RESOLVIDAS, alvo=None, detalhes=log_details)
        message = f'O comentário foi deletado, o autor notificado e {count} denúncia(s) foram resolvidas.'

    elif action == 'excluir' and status_original in ['RESOLVIDO', 'REJEITADO']:
        log_details['status_original'] = status_original
        count, _ = notificacoes.delete()
        criar_log(ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_DELETADAS, alvo=alvo, detalhes=log_details)
        message = f'{count} notificação(ões) para o item "{alvo}" foram excluídas.'
    else:
        return JsonResponse({'status': 'error', 'message': 'Ação inválida ou não permitida.'}, status=400)
        
    removed_card_id = f'card-group-{content_type.model}-{alvo.id}'
    return JsonResponse({'status': 'success', 'message': message, 'removed_card_id': removed_card_id})



@require_POST
@user_passes_test(is_staff_member)
def notificacoes_acoes_em_massa(request):
    """
    Aplica uma ação em massa a notificações de múltiplos alvos
    (sejam eles Questões ou Comentários).
    """
    try:
        data = json.loads(request.body)
        alvo_ids = data.get('ids', [])
        action = data.get('action')
        status_original = data.get('status_original', 'PENDENTE')
        tipo_alvo = data.get('tipo_alvo')

        if not all([alvo_ids, action, status_original, tipo_alvo]):
            return JsonResponse({'status': 'error', 'message': 'Parâmetros ausentes.'}, status=400)
        
        if tipo_alvo == 'questao':
            ct = ContentType.objects.get_for_model(Questao)
        elif tipo_alvo == 'comentario':
            ct = ContentType.objects.get_for_model(Comentario)
        else:
            return JsonResponse({'status': 'error', 'message': 'Tipo de alvo inválido.'}, status=400)
        
        queryset = Notificacao.objects.filter(content_type=ct, object_id__in=alvo_ids, status=status_original)
        
        alvos_afetados = ct.model_class().objects.filter(pk__in=alvo_ids)
        for alvo in alvos_afetados:
            count = queryset.filter(object_id=alvo.pk).count()
            if count > 0:
                log_acao_map = {
                    'resolver': LogAtividade.Acao.NOTIFICACOES_RESOLVIDAS, 
                    'rejeitar': LogAtividade.Acao.NOTIFICACOES_REJEITADAS, 
                    'excluir': LogAtividade.Acao.NOTIFICACOES_DELETADAS
                }
                log_acao = log_acao_map.get(action)
                if log_acao:
                    # =======================================================================
                    # INÍCIO DA CORREÇÃO: Usar .codigo para Questões no log em massa
                    # =======================================================================
                    alvo_log_str = alvo.codigo if isinstance(alvo, Questao) else str(alvo)
                    log_details = {'count': count, 'alvo_str': alvo_log_str, 'motivo': 'Ação em massa'}
                    # =======================================================================
                    # FIM DA CORREÇÃO
                    # =======================================================================
                    if action == 'excluir':
                        log_details['status_original'] = status_original
                    criar_log(ator=request.user, acao=log_acao, alvo=alvo, detalhes=log_details)

        if action == 'resolver':
            updated_count = queryset.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
        elif action == 'rejeitar':
            updated_count = queryset.update(status=Notificacao.Status.REJEITADO)
        elif action == 'excluir' and status_original in ['RESOLVIDO', 'REJEITADO']:
            updated_count, _ = queryset.delete()
        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida ou não permitida.'}, status=400)
        
        return JsonResponse({'status': 'success', 'message': f'{updated_count} notificação(ões) foram atualizadas com sucesso.'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@user_passes_test(is_staff_member)
def listar_usuarios(request):
    """
    Lista, filtra e ordena todos os usuários do sistema, agora incluindo
    informações sobre o tempo de inatividade.
    """
    base_queryset = User.objects.all().select_related('userprofile').exclude(id=request.user.id)
    if not request.user.is_superuser:
        base_queryset = base_queryset.exclude(is_superuser=True)

    # =======================================================================
    # ADIÇÃO: Subquery para buscar a data do último login
    # Isso é muito mais performático do que um loop no template.
    # =======================================================================
    # O Django não armazena o último login de forma simples, então usamos uma
    # anotação para buscar a data máxima de login do histórico de logs (se você tiver um)
    # ou usamos o campo 'last_login' padrão do User.
    # Vamos usar o 'last_login' que é mais direto.
    base_queryset = base_queryset.annotate(
        ultimo_login=Max('last_login')
    )
    # =======================================================================

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
    
    # Filtro de status melhorado
    if filtro_status == 'ativos':
        base_queryset = base_queryset.filter(is_active=True)
    elif filtro_status == 'inativos':
        base_queryset = base_queryset.filter(is_active=False)
    # se for 'todos', não aplica filtro

    # Lógica de ordenação
    sort_by = request.GET.get('sort_by', 'nivel')
    sort_options = {
        'nivel': 'Nível de Permissão',
        '-date_joined': 'Mais Recentes',
        'date_joined': 'Mais Antigos',
        'username': 'Nome (A-Z)',
        'ultimo_login': 'Menos Tempo Inativo', # Nova opção
        '-ultimo_login': 'Mais Tempo Inativo', # Nova opção
    }
    
    order_fields = []
    if sort_by == 'nivel':
         order_fields = ['-is_active', '-is_superuser', '-is_staff', '-tem_solicitacao_pendente', 'username']
    elif sort_by in sort_options:
        order_fields.append(sort_by)
    else:
        order_fields.append('username')
    
    base_queryset = base_queryset.order_by(*order_fields)

    paginated_object, page_numbers, per_page = paginar_itens(request, base_queryset, items_per_page=9)

    context = {
        'paginated_object': paginated_object,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_options': sort_options,
        'filtro_q': filtro_q,
        'filtro_permissao': filtro_permissao,
        'filtro_solicitacao': filtro_solicitacao,
        'filtro_status': filtro_status,
        'total_usuarios': paginated_object.paginator.count,
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
    
    # =======================================================================
    # ADIÇÃO: Contagem de solicitações pendentes para o botão
    # =======================================================================
    solicitacoes_pendentes_count = ExclusaoLogPermanente.objects.filter(status=ExclusaoLogPermanente.Status.PENDENTE).count()
    # =======================================================================
    
    context = {
        'logs': logs_paginados, 'paginated_object': logs_paginados, 'page_numbers': page_numbers, 'per_page': per_page,
        'sort_by': sort_by, 'sort_options': sort_options, 'filtro_q': filtro_q, 'filtro_acao': filtro_acao,
        'filtro_data_inicio': filtro_data_inicio, 'filtro_data_fim': filtro_data_fim, 'acao_choices': LogAtividade.Acao.choices,
        'solicitacoes_exclusao_logs_pendentes': solicitacoes_pendentes_count, # Passando para o template
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
    Lista, filtra e ordena os logs de atividade que estão na lixeira.
    """
    logs_list = LogAtividade.all_logs.filter(is_deleted=True).select_related('ator', 'deleted_by')

    # Lógica de filtragem (similar à listagem de logs ativos)
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
        # Adiciona 1 dia para incluir o dia final completo na busca
        data_fim_obj = datetime.strptime(filtro_data_fim, '%Y-%m-%d') + timedelta(days=1)
        logs_list = logs_list.filter(deleted_at__lt=data_fim_obj)
        
    # Lógica de Ordenação completa
    sort_by = request.GET.get('sort_by', '-deleted_at')
    sort_options = {
        '-deleted_at': 'Exclusão Mais Recente',
        'deleted_at': 'Exclusão Mais Antiga',
        'acao': 'Tipo de Ação (A-Z)',
        'deleted_by__username': 'Excluído Por (A-Z)',
    }
    if sort_by in sort_options:
        logs_list = logs_list.order_by(sort_by)

    logs_paginados, page_numbers, per_page = paginar_itens(request, logs_list, 20)
    
    # Contexto completo para o template
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
        # =======================================================================
        # ADIÇÃO: Passando a lista de dias para o template
        # =======================================================================
        'dias_para_limpeza': [15, 30, 60, 90, 180],
    }
    
    return render(request, 'gestao/listar_logs_deletados.html', context)


@require_POST
@user_passes_test(is_superuser)
@login_required
def limpar_lixeira_logs(request):
    """
    Cria uma solicitação de exclusão permanente para todos os logs na lixeira
    que são mais antigos que um determinado número de dias.
    """
    try:
        dias = int(request.POST.get('dias'))
        justificativa = f"Limpeza automática de registros na lixeira com mais de {dias} dias."
    except (ValueError, TypeError):
        messages.error(request, "Período de tempo inválido selecionado.")
        return redirect('gestao:listar_logs_deletados')

    limite_data = timezone.now() - timedelta(days=dias)
    
    # Seleciona apenas os logs que já podem ser excluídos permanentemente
    logs_para_excluir = LogAtividade.all_logs.filter(
        is_deleted=True,
        deleted_at__lt=limite_data
    ).filter(id__in=[log.id for log in LogAtividade.all_logs.filter(is_deleted=True) if log.is_permanently_deletable])

    if not logs_para_excluir.exists():
        messages.info(request, f"Não há registros na lixeira com mais de {dias} dias que possam ser excluídos permanentemente.")
        return redirect('gestao:listar_logs_deletados')

    log_ids = list(logs_para_excluir.values_list('id', flat=True))
    log_ids_str = ','.join(map(str, log_ids))
    
    # Reutiliza a lógica da view solicitar_exclusao_logs (adaptada)
    total_superusers = User.objects.filter(is_superuser=True, is_active=True).count()

    if total_superusers <= 1:
        count = logs_para_excluir.count()
        logs_para_excluir.delete()
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.LOG_DELETADO_PERMANENTEMENTE,
            detalhes={
                'quantidade': count, 
                'motivo': f'Limpeza direta de logs com mais de {dias} dias (único superusuário).',
                'justificativa_fornecida': justificativa
            }
        )
        messages.success(request, f"{count} registro(s) antigos foram excluídos permanentemente.")
        return redirect('gestao:listar_logs_deletados')

    # Cria a solicitação para quórum
    solicitacao = ExclusaoLogPermanente.objects.create(
        solicitado_por=request.user,
        justificativa=justificativa,
        log_ids=log_ids_str
    )
    criar_log(
        ator=request.user,
        acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_LOG_CRIADA,
        alvo=solicitacao,
        detalhes={'quantidade': len(log_ids), 'motivo': 'Limpeza por período'}
    )
    
    messages.success(request, f"Uma solicitação para excluir {len(log_ids)} registro(s) antigos foi enviada para aprovação.")
    return redirect('gestao:listar_solicitacoes_exclusao_logs')

@login_required
def ranking(request):
    """
    Exibe a página de ranking dos usuários, com base em critérios de desempenho
    como total de acertos e sequência de prática (streak).
    """
    # 1. Obter parâmetros de filtro e ordenação da URL
    sort_by = request.GET.get('sort_by', 'acertos') # 'acertos' como padrão

    # 2. Construir o queryset base, otimizado para performance.
    # Filtramos para incluir apenas usuários ativos e que não são da equipe de gestão.
    base_queryset = UserProfile.objects.filter(
        user__is_active=True,
        user__is_staff=False
    ).select_related(
        'streak_data' # Usa JOIN para buscar os dados de streak na mesma query
    ).annotate(
        # Conta o total de respostas do usuário
        total_respostas=Count('user__respostausuario'),
        # Conta apenas as respostas corretas
        total_acertos=Count('user__respostausuario', filter=Q(user__respostausuario__foi_correta=True))
    ).filter(
        total_respostas__gt=0 # Exibe apenas usuários que já responderam pelo menos uma questão
    )

    # 3. Definir as opções de ordenação e aplicar a selecionada
    sort_options = {
        'acertos': ('-total_acertos', '-streak_data__current_streak'),
        'streak': ('-streak_data__current_streak', '-total_acertos'),
        'respostas': ('-total_respostas', '-total_acertos'),
    }
    
    # Define a ordenação padrão se um parâmetro inválido for passado
    ordenacao = sort_options.get(sort_by, sort_options['acertos'])
    
    # Anotação com a função de janela `Rank` para calcular a posição de cada usuário
    # A ordenação dentro do Rank() deve ser a mesma do order_by() final.
    queryset_ranqueado = base_queryset.annotate(
        rank=Window(
            expression=Rank(),
            order_by=[F(field[1:]).desc() if field.startswith('-') else F(field).asc() for field in ordenacao]
        )
    ).order_by(*ordenacao)

    # 4. Encontrar a posição do usuário logado no ranking
    # Como já temos o rank anotado, podemos simplesmente filtrar e pegar o valor.
    posicao_usuario_logado = queryset_ranqueado.filter(user=request.user).first()

    # 5. Paginar os resultados
    page_obj, page_numbers, per_page = paginar_itens(request, queryset_ranqueado, 25) # 25 usuários por página

    context = {
        'ranking_list': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': sort_by,
        'posicao_usuario_logado': posicao_usuario_logado,
    }
    
    return render(request, 'gamificacao/ranking.html', context)


@user_passes_test(is_staff_member)
@login_required
def visualizar_comentario_ajax(request, comentario_id):
    """
    Retorna os detalhes de um comentário e da sua questão associada
    em formato JSON para visualização em um modal.
    """
    try:
        comentario = get_object_or_404(
            Comentario.objects.select_related('usuario__userprofile', 'questao'), 
            id=comentario_id
        )
        questao = comentario.questao
        
        data = {
            'status': 'success',
            'comentario': {
                'id': comentario.id,
                'autor': comentario.usuario.userprofile.nome,
                'conteudo_html': markdown.markdown(comentario.conteudo),
                'data_criacao': comentario.data_criacao.strftime("%d/%m/%Y às %H:%M"),
            },
            'questao': {
                'id': questao.id,
                'codigo': questao.codigo,
                'enunciado_html': markdown.markdown(questao.enunciado),
            }
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    

@user_passes_test(is_staff_member)
@login_required
def listar_simulados_gestao(request):
    """
    Lista, filtra, busca e ordena todos os simulados oficiais usando
    um layout de cards detalhados com paginação.
    """
    base_queryset = Simulado.objects.filter(is_oficial=True)

    # --- Lógica de Busca ---
    termo_busca = request.GET.get('q', '').strip()
    if termo_busca:
        base_queryset = base_queryset.filter(
            Q(nome__icontains=termo_busca) | Q(codigo__iexact=termo_busca)
        )

    # --- Lógica de Filtragem Expandida ---
    filtro_status = request.GET.get('status')
    filtro_disciplinas = request.GET.getlist('disciplina')
    filtro_bancas = request.GET.getlist('banca')
    filtro_assuntos = request.GET.getlist('assunto')
    # ✅ ADIÇÃO: Captura dos novos filtros
    filtro_instituicoes = request.GET.getlist('instituicao')
    filtro_anos = request.GET.getlist('ano')

    if filtro_status:
        base_queryset = base_queryset.filter(status=filtro_status)
    if filtro_disciplinas:
        base_queryset = base_queryset.filter(questoes__disciplina__id__in=filtro_disciplinas).distinct()
    if filtro_bancas:
        base_queryset = base_queryset.filter(questoes__banca__id__in=filtro_bancas).distinct()
    if filtro_assuntos:
        base_queryset = base_queryset.filter(questoes__assunto__id__in=filtro_assuntos).distinct()
    # ✅ ADIÇÃO: Aplicação dos novos filtros na queryset
    if filtro_instituicoes:
        base_queryset = base_queryset.filter(questoes__instituicao__id__in=filtro_instituicoes).distinct()
    if filtro_anos:
        base_queryset = base_queryset.filter(questoes__ano__in=filtro_anos).distinct()

    # --- Lógica de Ordenação ---
    sort_by = request.GET.get('sort_by', '-data_criacao')
    sort_options = {
        '-data_criacao': 'Mais Recentes',
        'data_criacao': 'Mais Antigos',
        'nome': 'Nome (A-Z)',
        '-num_questoes': 'Nº de Questões (Maior)',
    }
    
    # --- Otimização com Prefetch ---
    prefetch_disciplinas = Prefetch(
        'questoes',
        queryset=Questao.objects.select_related('disciplina'),
        to_attr='questoes_com_disciplinas'
    )

    simulados_list = base_queryset.annotate(
        num_questoes=Count('questoes')
    ).select_related('criado_por').prefetch_related(prefetch_disciplinas)

    if sort_by in sort_options:
        simulados_list = simulados_list.order_by(sort_by)

    # --- Paginação ---
    page_obj, page_numbers, per_page = paginar_itens(request, simulados_list, items_per_page=9)

    # --- Contexto para o Template ---
    context = {
        'simulados': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_options': sort_options,
        'sort_by': sort_by,
        'status_choices': StatusSimulado.choices,
        'active_filters': request.GET,
        
        # Dados para popular os dropdowns de filtro
        'disciplinas_filtro': Disciplina.objects.all().order_by('nome'),
        'bancas_filtro': Banca.objects.all().order_by('nome'),
        'assuntos_url': reverse('questoes:get_assuntos_por_disciplina'),
        # ✅ ADIÇÃO: Novos dados para os filtros de Instituição e Ano
        'instituicoes_filtro': Instituicao.objects.all().order_by('nome'),
        'anos_filtro': Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano'),
        
        # IDs selecionados para manter o estado do filtro na interface
        'selected_disciplinas': [int(i) for i in filtro_disciplinas if i.isdigit()],
        'selected_bancas': [int(i) for i in filtro_bancas if i.isdigit()],
        'selected_assuntos': [int(i) for i in filtro_assuntos if i.isdigit()],
        'selected_assuntos_json': json.dumps([int(i) for i in filtro_assuntos if i.isdigit()]),
        # ✅ ADIÇÃO: Passando os IDs selecionados dos novos filtros
        'selected_instituicoes': [int(i) for i in filtro_instituicoes if i.isdigit()],
        'selected_anos': filtro_anos, # Anos são strings, não precisam de conversão
    }
    return render(request, 'gestao/listar_simulados.html', context)

@user_passes_test(is_staff_member)
@login_required
def criar_simulado(request):
    """
    ETAPA 1 DO ASSISTENTE: Define o nome, dificuldade e filtros iniciais do simulado.
    """
    if request.method == 'POST':
        form = SimuladoWizardForm(request.POST)
        if form.is_valid():
            # =======================================================================
            # INÍCIO DA CORREÇÃO: Adicionar 'dificuldade' ao criar o objeto
            # =======================================================================
            simulado = Simulado.objects.create(
                nome=form.cleaned_data['nome'],
                dificuldade=form.cleaned_data['dificuldade'],
                criado_por=request.user,
                is_oficial=True
            )
            # =======================================================================
            # FIM DA CORREÇÃO
            # =======================================================================
            
            filtros = {
                'disciplinas': [int(d) for d in request.POST.getlist('disciplina')],
                'assuntos': [int(a) for a in request.POST.getlist('assunto')],
                'bancas': [int(b) for b in request.POST.getlist('banca')],
                'instituicoes': [int(i) for i in request.POST.getlist('instituicao')],
                'anos': request.POST.getlist('ano'),
            }
            simulado.filtros_iniciais = filtros
            simulado.save()

            criar_log(ator=request.user, acao=LogAtividade.Acao.SIMULADO_CRIADO, alvo=simulado, detalhes={'nome_simulado': simulado.nome, 'filtros_definidos': True})
            messages.info(request, f'Simulado "{simulado.nome}" criado. Agora, selecione as questões que farão parte dele.')
            
            return redirect('gestao:editar_simulado', simulado_id=simulado.id)
    else:
        form = SimuladoWizardForm()

    context = {
        'form': form, 
        'titulo': 'Criar Novo Simulado (Etapa 1 de 2)',
        'form_action_url': reverse('gestao:criar_simulado'),
        'prefix': '',
        'disciplinas': Disciplina.objects.all().order_by('nome'),
        'bancas': Banca.objects.all().order_by('nome'),
        'instituicoes': Instituicao.objects.all().order_by('nome'),
        'anos': Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano'),
        'assuntos_url': reverse('questoes:get_assuntos_por_disciplina'),
        'selected_disciplinas': [],
        'selected_assuntos': [],
        'selected_bancas': [],
        'selected_instituicoes': [],
        'selected_anos': [],
        'selected_assuntos_json': "[]",
        'palavra_chave_buscada': "",
        'exibir_filtro_palavra': False,  
        'form_classes': 'hide-palavra'
    }
    return render(request, 'gestao/form_criar_simulado_etapa1.html', context)

@user_passes_test(is_staff_member)
@login_required
def editar_simulado(request, simulado_id):
    """ ETAPA 2 DO ASSISTENTE: Workspace para selecionar e gerenciar questões. """
    simulado = get_object_or_404(
        Simulado.objects.prefetch_related(
            Prefetch('questoes', queryset=Questao.objects.select_related('disciplina'))
        ), 
        id=simulado_id, 
        is_oficial=True
    )
    
    if request.method == 'POST' and 'nome' in request.POST:
        form = SimuladoForm(request.POST, instance=simulado, fields_to_show=['nome'])
        if form.is_valid():
            simulado_salvo = form.save()
            # =======================================================================
            # INÍCIO DA CORREÇÃO: A chave 'novo_nome' foi trocada para 'nome_simulado'
            # para padronizar com as outras ações.
            # =======================================================================
            criar_log(
                ator=request.user, 
                acao=LogAtividade.Acao.SIMULADO_EDITADO, 
                alvo=simulado_salvo, 
                detalhes={'campo_alterado': 'nome', 'nome_simulado': simulado_salvo.nome}
            )
            # =======================================================================
            # FIM DA CORREÇÃO
            # =======================================================================
            messages.success(request, 'O nome do simulado foi atualizado com sucesso!')
            return redirect(f"{request.path}?{request.GET.urlencode()}")
    else:
        form = SimuladoForm(instance=simulado, fields_to_show=['nome'])

    # O restante desta view permanece inalterado...
    questoes_disponiveis = Questao.objects.all()
    filtros_iniciais_info = {}
    if simulado.filtros_iniciais:
        filtros = simulado.filtros_iniciais
        if filtros.get('disciplinas'):
            questoes_disponiveis = questoes_disponiveis.filter(disciplina_id__in=filtros['disciplinas'])
        if filtros.get('assuntos'):
            questoes_disponiveis = questoes_disponiveis.filter(assunto_id__in=filtros['assuntos'])
        if filtros.get('bancas'):
            questoes_disponiveis = questoes_disponiveis.filter(banca_id__in=filtros['bancas'])
        if filtros.get('instituicoes'):
            questoes_disponiveis = questoes_disponiveis.filter(instituicao_id__in=filtros['instituicoes'])
        if filtros.get('anos'):
            questoes_disponiveis = questoes_disponiveis.filter(ano__in=filtros['anos'])

        filtros_iniciais_info = {
            'Disciplinas': Disciplina.objects.filter(id__in=filtros.get('disciplinas', [])).values_list('nome', flat=True),
            'Assuntos': Assunto.objects.filter(id__in=filtros.get('assuntos', [])).values_list('nome', flat=True),
            'Bancas': Banca.objects.filter(id__in=filtros.get('bancas', [])).values_list('nome', flat=True),
            'Instituições': Instituicao.objects.filter(id__in=filtros.get('instituicoes', [])).values_list('nome', flat=True),
            'Anos': filtros.get('anos', [])
        }

    context_filtro = filtrar_e_paginar_questoes_com_prefixo(
        request, 
        questoes_disponiveis.select_related('disciplina', 'banca'), 
        items_per_page=10, 
        prefix='q_'
    )
    
    context_filtro.update({
        'disciplinas': Disciplina.objects.all().order_by('nome'),
        'bancas': Banca.objects.all().order_by('nome'),
        'instituicoes': Instituicao.objects.all().order_by('nome'),
        'anos': Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano'),
        'form_action_url': request.path,
        'assuntos_url': reverse('questoes:get_assuntos_por_disciplina'),
        'selected_assuntos_json': json.dumps(context_filtro.get('selected_assuntos', []))
    })

    context = {
        'form': form,
        'titulo': f'Editor de Simulado: {simulado.nome}',
        'simulado': simulado,
        'questoes_no_simulado_ids': list(simulado.questoes.values_list('id', flat=True)),
        'questoes_no_simulado': simulado.questoes.all(),
        'filtros_iniciais_info': filtros_iniciais_info
    }
    
    context.update(context_filtro)
    
    return render(request, 'gestao/form_simulado_editor.html', context)

@user_passes_test(is_staff_member)
@login_required
@require_POST
def deletar_simulado(request, simulado_id):
    simulado = get_object_or_404(Simulado, id=simulado_id, is_oficial=True) 
    
    nome_simulado = simulado.nome
    
    # =======================================================================
    # CORREÇÃO: Padronizando a chave para 'nome_simulado'.
    # =======================================================================
    criar_log(
        ator=request.user,
        acao=LogAtividade.Acao.SIMULADO_DELETADO,
        alvo=None,
        detalhes={'nome_simulado': nome_simulado, 'simulado_id': simulado.id}
    )
    
    simulado.delete()
    messages.success(request, f'O simulado "{nome_simulado}" foi deletado com sucesso.')
    return redirect('gestao:listar_simulados_gestao')


@user_passes_test(is_staff_member)
@login_required
def editar_simulado_meta_ajax(request, simulado_id):
    """
    Gerencia a edição dos metadados de um simulado (nome, status, dificuldade) via AJAX.
    """
    simulado = get_object_or_404(Simulado, id=simulado_id, is_oficial=True)

    if request.method == 'POST':
        form = SimuladoMetaForm(request.POST, instance=simulado)
        if form.is_valid():
            form.save()
            criar_log(ator=request.user, acao=LogAtividade.Acao.SIMULADO_EDITADO, alvo=simulado, detalhes={'nome_simulado': simulado.nome, 'campos_alterados': list(form.changed_data)})
            
            # =======================================================================
            # INÍCIO DA CORREÇÃO: Adicionar os dados de dificuldade na resposta AJAX
            # =======================================================================
            return JsonResponse({
                'status': 'success',
                'message': 'Dados do simulado atualizados com sucesso!',
                'simulado_data': {
                    'nome': simulado.nome,
                    'status_display': simulado.get_status_display(),
                    'status_class': f'bg-status-{simulado.status.lower()}',
                    'dificuldade_display': simulado.get_dificuldade_display(),
                    'dificuldade_class': f'bg-{simulado.dificuldade.lower()}-soft text-{simulado.dificuldade.lower()}'
                }
            })
            # =======================================================================
            # FIM DA CORREÇÃO
            # =======================================================================
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    
    # Se a requisição for GET
    form = SimuladoMetaForm(instance=simulado)
    form_html = render_to_string('gestao/includes/_form_simulado_meta.html', {'form': form}, request=request)
    
    return JsonResponse({'status': 'success', 'form_html': form_html})


# Nova API para adicionar/remover questões do simulado via AJAX
@require_POST
@user_passes_test(is_staff_member)
@login_required
def gerenciar_questoes_simulado_ajax(request, simulado_id):
    simulado = get_object_or_404(Simulado, id=simulado_id)
    try:
        data = json.loads(request.body)
        questao_id = data.get('questao_id')
        action = data.get('action') # 'add' ou 'remove'

        if not all([questao_id, action]):
            return HttpResponseBadRequest("Parâmetros ausentes.")

        if action == 'add':
            simulado.questoes.add(questao_id)
        elif action == 'remove':
            simulado.questoes.remove(questao_id)
        else:
            return HttpResponseBadRequest("Ação inválida.")
        
        total_questoes = simulado.questoes.count()
        return JsonResponse({'status': 'success', 'total_questoes': total_questoes})

    except (json.JSONDecodeError, Questao.DoesNotExist):
        return HttpResponseBadRequest("Requisição inválida.")


@user_passes_test(is_staff_member)
@require_POST
def api_contar_questoes_filtro(request):
    """
    API para contar quantas questões correspondem a um conjunto de filtros.
    """
    try:
        data = json.loads(request.body)
        qs = Questao.objects.all()

        if data.get('disciplinas'):
            qs = qs.filter(disciplina_id__in=data['disciplinas'])
        # ✅ CORREÇÃO: Adiciona o filtro de assunto à contagem
        if data.get('assuntos'):
            qs = qs.filter(assunto_id__in=data['assuntos'])
        if data.get('bancas'):
            qs = qs.filter(banca_id__in=data['bancas'])
        if data.get('instituicoes'):
            qs = qs.filter(instituicao_id__in=data['instituicoes'])
        
        anos = data.get('anos', [])
        if anos:
            anos_int = [int(ano) for ano in anos if ano and ano.isdigit()]
            if anos_int:
                qs = qs.filter(ano__in=anos_int)
        
        return JsonResponse({'status': 'success', 'count': qs.count()})
    except Exception as e:
        # Para depuração, é útil logar o erro
        print(f"Erro na API de contagem: {e}")
        return JsonResponse({'status': 'error', 'message': 'Filtros inválidos.'}, status=400)
    
    
@user_passes_test(is_staff_member)
@login_required
def listar_conquistas(request):
    """Lista todas as conquistas cadastradas no sistema."""
    conquistas_list = Conquista.objects.all().order_by('nome')
    paginated_object, page_numbers, per_page = paginar_itens(request, conquistas_list, 15)
    
    context = {
        'conquistas': paginated_object,
        'paginated_object': paginated_object,
        'page_numbers': page_numbers,
        'per_page': per_page,
    }
    return render(request, 'gestao/listar_conquistas.html', context)

@user_passes_test(is_staff_member)
@login_required
def criar_conquista(request):
    """Cria uma nova conquista."""
    if request.method == 'POST':
        form = ConquistaForm(request.POST)
        if form.is_valid():
            conquista = form.save()
            
            # =======================================================================
            # CORREÇÃO: Passando o nome do objeto nos detalhes do log.
            # =======================================================================
            criar_log(
                ator=request.user, 
                acao=LogAtividade.Acao.CONQUISTA_CRIADA, 
                alvo=conquista,
                detalhes={'nome': conquista.nome} # <-- LINHA CORRIGIDA/ADICIONADA
            )
            # =======================================================================

            messages.success(request, f'A conquista "{conquista.nome}" foi criada com sucesso.')
            return redirect('gestao:listar_conquistas')
    else:
        form = ConquistaForm()
        
    context = {'form': form, 'titulo': 'Criar Nova Conquista'}
    return render(request, 'gestao/form_conquista.html', context)

@user_passes_test(is_staff_member)
@login_required
def editar_conquista(request, conquista_id):
    """Edita uma conquista existente."""
    conquista = get_object_or_404(Conquista, id=conquista_id)
    if request.method == 'POST':
        form = ConquistaForm(request.POST, instance=conquista)
        if form.is_valid():
            form.save()

            # =======================================================================
            # CORREÇÃO: Passando o nome do objeto nos detalhes do log.
            # =======================================================================
            criar_log(
                ator=request.user, 
                acao=LogAtividade.Acao.CONQUISTA_EDITADA, 
                alvo=conquista,
                detalhes={'nome': conquista.nome} # <-- LINHA CORRIGIDA/ADICIONADA
            )
            # =======================================================================

            messages.success(request, f'A conquista "{conquista.nome}" foi atualizada com sucesso.')
            return redirect('gestao:listar_conquistas')
    else:
        form = ConquistaForm(instance=conquista)

    context = {'form': form, 'titulo': f'Editando: {conquista.nome}', 'conquista': conquista}
    return render(request, 'gestao/form_conquista.html', context)

@user_passes_test(is_staff_member)
@require_POST
@login_required
def deletar_conquista(request, conquista_id):
    """Deleta uma conquista."""
    conquista = get_object_or_404(Conquista, id=conquista_id)
    nome_conquista = conquista.nome
    
    criar_log(ator=request.user, acao=LogAtividade.Acao.CONQUISTA_DELETADA, alvo=None, detalhes={'nome_conquista': nome_conquista})
    conquista.delete()
    
    messages.success(request, f'A conquista "{nome_conquista}" foi deletada com sucesso.')
    return redirect('gestao:listar_conquistas')


@user_passes_test(is_staff_member)
@login_required
def gerenciar_gamificacao_settings(request):
    settings = GamificationSettings.load()
    if request.method == 'POST':
        form = GamificationSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            # =======================================================================
            # ADIÇÃO: Criando o log para a edição das configurações
            # =======================================================================
            if form.changed_data: # Apenas cria o log se algo realmente mudou
                criar_log(
                    ator=request.user,
                    acao=LogAtividade.Acao.CONFIG_XP_EDITADA,
                    alvo=settings,
                    detalhes={'campos_alterados': form.changed_data}
                )
            # =======================================================================
            messages.success(request, 'As configurações de gamificação foram atualizadas com sucesso.')
            return redirect('gestao:gerenciar_gamificacao_settings')
    else:
        form = GamificationSettingsForm(instance=settings)

    context = {
        'form': form,
        'titulo': 'Configurações de Gamificação',
        'active_tab': 'configuracoes'
    }
    return render(request, 'gestao/form_gamificacao_settings.html', context)


@user_passes_test(is_staff_member)
@login_required
def listar_recompensas(request, tipo):
    """
    Lista Avatares, Bordas ou Banners com base no tipo,
    adicionando filtro por raridade.
    """
    ModelMap = {
        'avatares': (Avatar, 'Gerenciar Avatares'),
        'bordas': (Borda, 'Gerenciar Bordas de Perfil'),
        'banners': (Banner, 'Gerenciar Banners de Perfil'),
    }
    if tipo not in ModelMap:
        return redirect('gestao:listar_conquistas')

    Model, titulo = ModelMap[tipo]
    
    base_queryset = Model.objects.all().select_related('conquista_necessaria')

    # Filtro por raridade
    filtro_raridade = request.GET.get('raridade')
    if filtro_raridade:
        base_queryset = base_queryset.filter(raridade=filtro_raridade)

    recompensas_list = base_queryset.order_by('nome')
    paginated_object, page_numbers, per_page = paginar_itens(request, recompensas_list, 12)
    
    context = {
        'recompensas': paginated_object,
        'paginated_object': paginated_object,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'tipo': tipo,
        'titulo': titulo,
        'raridade_choices': Model.Raridade.choices,
        'filtro_raridade_ativo': filtro_raridade,
    }
    return render(request, 'gestao/listar_recompensas.html', context)

@user_passes_test(is_staff_member)
@login_required
def criar_recompensa(request, tipo):
    """Cria um novo Avatar, Borda ou Banner."""
    if tipo == 'avatares':
        FormClass = AvatarForm
        titulo = 'Adicionar Novo Avatar'
        log_acao = LogAtividade.Acao.AVATAR_CRIADO
    elif tipo == 'bordas':
        FormClass = BordaForm
        titulo = 'Adicionar Nova Borda'
        log_acao = LogAtividade.Acao.BORDA_CRIADA
    elif tipo == 'banners':
        FormClass = BannerForm
        titulo = 'Adicionar Novo Banner'
        log_acao = LogAtividade.Acao.BANNER_CRIADO
    else:
        # Fallback seguro caso um tipo inválido seja passado na URL
        messages.error(request, "Tipo de recompensa inválido.")
        return redirect('gestao:listar_conquistas')

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES)
        if form.is_valid():
            recompensa = form.save()
            
            # =======================================================================
            # CORREÇÃO: Passando o nome do objeto nos detalhes do log
            # Isso garante que a mensagem do log seja gerada corretamente.
            # =======================================================================
            criar_log(
                ator=request.user, 
                acao=log_acao, 
                alvo=recompensa,
                detalhes={'nome': recompensa.nome} # <-- LINHA CORRIGIDA/ADICIONADA
            )
            # =======================================================================
            
            messages.success(request, f'Item "{recompensa.nome}" foi criado com sucesso.')
            return redirect('gestao:listar_recompensas', tipo=tipo)
    else:
        form = FormClass()
        
    context = {'form': form, 'titulo': titulo, 'tipo': tipo}
    return render(request, 'gestao/form_recompensa.html', context)


@user_passes_test(is_staff_member)
@login_required
def editar_recompensa(request, tipo, recompensa_id):
    """Edita um Avatar, Borda ou Banner existente."""
    if tipo == 'avatares':
        Model = Avatar
        FormClass = AvatarForm
        log_acao = LogAtividade.Acao.AVATAR_EDITADO
    elif tipo == 'bordas':
        Model = Borda
        FormClass = BordaForm
        log_acao = LogAtividade.Acao.BORDA_EDITADA
    elif tipo == 'banners':
        Model = Banner
        FormClass = BannerForm
        log_acao = LogAtividade.Acao.BANNER_EDITADO
    else:
        # Fallback seguro caso um tipo inválido seja passado na URL
        messages.error(request, "Tipo de recompensa inválido.")
        return redirect('gestao:listar_conquistas')

    recompensa = get_object_or_404(Model, id=recompensa_id)
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=recompensa)
        if form.is_valid():
            form.save()
            
            # =======================================================================
            # CORREÇÃO: Passando o nome do objeto nos detalhes do log
            # Isso garante que a mensagem do log seja gerada corretamente.
            # =======================================================================
            criar_log(
                ator=request.user, 
                acao=log_acao, 
                alvo=recompensa,
                detalhes={'nome': recompensa.nome} # <-- LINHA CORRIGIDA/ADICIONADA
            )
            # =======================================================================
            
            messages.success(request, f'Item "{recompensa.nome}" foi atualizado com sucesso.')
            return redirect('gestao:listar_recompensas', tipo=tipo)
    else:
        form = FormClass(instance=recompensa)

    context = {'form': form, 'titulo': f'Editando: {recompensa.nome}', 'tipo': tipo}
    return render(request, 'gestao/form_recompensa.html', context)


@user_passes_test(is_staff_member)
@require_POST
@login_required
def deletar_recompensa(request, tipo, recompensa_id):
    """Deleta um Avatar, Borda ou Banner."""
    if tipo == 'avatares':
        Model = Avatar
        log_acao = LogAtividade.Acao.AVATAR_DELETADO
    elif tipo == 'bordas':
        Model = Borda
        log_acao = LogAtividade.Acao.BORDA_DELETADA
    # =======================================================================
    # ADIÇÃO: Lógica para o tipo "banners"
    # =======================================================================
    elif tipo == 'banners':
        Model = Banner
        log_acao = LogAtividade.Acao.BANNER_DELETADO
    else:
        return redirect('gestao:listar_conquistas')
        
    recompensa = get_object_or_404(Model, id=recompensa_id)
    nome_recompensa = recompensa.nome
    
    criar_log(ator=request.user, acao=log_acao, alvo=None, detalhes={'nome_recompensa': nome_recompensa})
    recompensa.delete()
    
    messages.success(request, f'O item "{nome_recompensa}" foi deletado com sucesso.')
    return redirect('gestao:listar_recompensas', tipo=tipo)

@require_POST
@user_passes_test(is_superuser)
@login_required
@transaction.atomic
def solicitar_exclusao_logs(request):
    """
    Cria uma solicitação de exclusão permanente para logs da lixeira,
    respeitando a regra de tempo mínimo.
    """
    log_ids_str = request.POST.get('log_ids')
    justificativa = request.POST.get('justificativa')

    if not log_ids_str or not justificativa:
        messages.error(request, "É necessário selecionar pelo menos um log e fornecer uma justificativa.")
        return redirect('gestao:listar_logs_deletados')

    log_ids = [int(id_str) for id_str in log_ids_str.split(',') if id_str.isdigit()]
    
    # =======================================================================
    # ADIÇÃO: Validação da regra de tempo mínimo na lixeira
    # =======================================================================
    logs_para_verificar = LogAtividade.all_logs.filter(id__in=log_ids)
    for log in logs_para_verificar:
        if not log.is_permanently_deletable:
            messages.error(request, f"Ação negada: O registro de log #{log.id} ainda não completou 30 dias na lixeira para poder ser excluído permanentemente.")
            return redirect('gestao:listar_logs_deletados')
    # =======================================================================

    total_superusers = User.objects.filter(is_superuser=True, is_active=True).count()
    
    # Cenário de único superusuário: exclusão direta
    if total_superusers <= 1:
        logs_para_deletar = LogAtividade.all_logs.filter(id__in=log_ids)
        count = logs_para_deletar.count()
        logs_para_deletar.delete()

        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.LOG_DELETADO_PERMANENTEMENTE,
            alvo=None,
            detalhes={
                'quantidade': count, 
                'motivo': 'Exclusão direta (único superusuário no sistema)',
                'justificativa_fornecida': justificativa
            }
        )
        messages.success(request, f"{count} registro(s) de log foram excluídos permanentemente.")
        return redirect('gestao:listar_logs_deletados')

    # Cenário de múltiplos superusuários: sistema de quórum
    pendentes = ExclusaoLogPermanente.objects.filter(status=ExclusaoLogPermanente.Status.PENDENTE)
    for p in pendentes:
        if any(log_id in p.get_log_ids_as_list() for log_id in log_ids):
            messages.warning(request, "Um ou mais dos logs selecionados já fazem parte de uma solicitação de exclusão pendente.")
            return redirect('gestao:listar_logs_deletados')

    solicitacao = ExclusaoLogPermanente.objects.create(
        solicitado_por=request.user,
        justificativa=justificativa,
        log_ids=log_ids_str
    )
    
    criar_log(
        ator=request.user,
        acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_LOG_CRIADA,
        alvo=solicitacao,
        detalhes={'quantidade': len(log_ids)}
    )
    
    messages.success(request, f"Sua solicitação para excluir {len(log_ids)} registro(s) foi enviada para aprovação.")
    return redirect('gestao:listar_solicitacoes_exclusao_logs')

@user_passes_test(is_superuser)
@login_required
def listar_solicitacoes_exclusao_logs(request):
    """
    Lista todas as solicitações de exclusão permanente de logs pendentes.
    """
    solicitacoes = ExclusaoLogPermanente.objects.filter(status=ExclusaoLogPermanente.Status.PENDENTE).order_by('-data_solicitacao')
    context = {'solicitacoes': solicitacoes}
    return render(request, 'gestao/listar_solicitacoes_exclusao_logs.html', context)


@require_POST
@user_passes_test(is_superuser)
@login_required
@transaction.atomic
def aprovar_exclusao_logs(request, solicitacao_id):
    """
    Aprova uma solicitação de exclusão. Se o quórum for atingido,
    os logs são deletados permanentemente.
    """
    solicitacao = get_object_or_404(ExclusaoLogPermanente, id=solicitacao_id, status=ExclusaoLogPermanente.Status.PENDENTE)
    
    # A lógica de aprovação e verificação de quórum está no método .aprovar() do modelo
    status, message = solicitacao.aprovar(request.user)

    if status == 'QUORUM_MET':
        log_ids_para_deletar = solicitacao.get_log_ids_as_list()
        
        # Deleta os logs permanentemente do banco de dados
        LogAtividade.all_logs.filter(id__in=log_ids_para_deletar).delete()
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.LOG_DELETADO_PERMANENTEMENTE, # <-- ADICIONE ESTA AÇÃO AO MODELO
            alvo=solicitacao,
            detalhes={'quantidade': len(log_ids_para_deletar), 'aprovador_final': request.user.username}
        )
        messages.success(request, message)
        
    elif status == 'APPROVAL_REGISTERED':
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_LOG_APROVADA, # <-- ADICIONE ESTA AÇÃO AO MODELO
            alvo=solicitacao,
            detalhes={'aprovador': request.user.username}
        )
        messages.info(request, message)
    else: # status == 'FAILED'
        messages.error(request, message)
    
    return redirect('gestao:listar_solicitacoes_exclusao_logs')