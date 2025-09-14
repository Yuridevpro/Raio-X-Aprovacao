# questoes/views.py

from django.http import JsonResponse,  HttpResponse # ✅ Adicio
from .models import Assunto

# questoes/views.py (ARQUIVO MODIFICADO)

from django.http import JsonResponse,  HttpResponse
from .models import Assunto

def get_assuntos_por_disciplina(request):
    """
    View de API centralizada para buscar assuntos de uma ou mais disciplinas.
    """
    disciplina_ids = request.GET.getlist('disciplina_ids[]')
    if not disciplina_ids:
        return JsonResponse({'assuntos': []})

    # =======================================================================
    # INÍCIO DA OTIMIZAÇÃO: Adicionado .select_related('disciplina')
    # Isso força o Django a usar um JOIN na query, prevenindo o problema N+1
    # e garantindo a máxima performance, mesmo que a view seja alterada no futuro.
    # =======================================================================
    assuntos = Assunto.objects.filter(
        disciplina_id__in=disciplina_ids
    ).select_related(
        'disciplina'
    ).values(
        'id', 'nome', 'disciplina__nome'
    ).order_by('disciplina__nome', 'nome')
    # =======================================================================
    # FIM DA OTIMIZAÇÃO
    # =======================================================================
    
    return JsonResponse({'assuntos': list(assuntos)})

def get_assuntos(request, disciplina_id):
    assuntos = Assunto.objects.filter(disciplina_id=disciplina_id).order_by('nome')
    data = [{"id": a.id, "nome": a.nome} for a in assuntos]
    return JsonResponse(data, safe=False)

