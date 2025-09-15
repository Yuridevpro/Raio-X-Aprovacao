# questoes/views.py

from django.http import JsonResponse,  HttpResponse # ✅ Adicio
from .models import Assunto

# questoes/views.py (ARQUIVO MODIFICADO)

from django.http import JsonResponse,  HttpResponse
from .models import Assunto

# questoes/views.py

from django.http import JsonResponse
from .models import Assunto
from django.db.models import F # ✅ ADIÇÃO: Importar a função F

def get_assuntos_por_disciplina(request):
    """
    Retorna uma lista de assuntos em formato JSON, filtrados por uma ou mais disciplinas.
    Esta versão é otimizada e segura, garantindo que nenhum dado inválido seja enviado.
    """
    # A lógica para obter os IDs da URL está correta.
    disciplina_ids_str_list = request.GET.getlist('disciplina_ids[]')
    
    if not disciplina_ids_str_list:
        return JsonResponse({'assuntos': []})

    # Converte a lista de IDs em uma lista de inteiros
    try:
        disciplina_ids = [int(id_str) for id_str in disciplina_ids_str_list]
    except (ValueError, TypeError):
        return JsonResponse({'assuntos': []})

    # ===================================================================
    # ✅ CORREÇÃO DEFINITIVA: Usando F() para renomear o campo
    # ===================================================================
    # 1. `select_related('disciplina')`: Otimiza a busca.
    # 2. `values()`: Seleciona os campos que precisamos.
    # 3. `F('disciplina__nome')`: É a forma correta de dizer ao Django para pegar o
    #    campo 'nome' da relação 'disciplina' e renomeá-lo para 'disciplina_nome'
    #    na saída do JSON.
    # ===================================================================
    assuntos = Assunto.objects.filter(
        disciplina_id__in=disciplina_ids
    ).select_related('disciplina').annotate(
        disciplina_nome=F('disciplina__nome')  # Cria um novo campo chamado 'disciplina_nome'
    ).values(
        'id', 
        'nome', 
        'disciplina_nome' # Agora podemos usar o campo que criamos
    )

    # Converte o queryset para uma lista de dicionários
    assuntos_list = list(assuntos)
    
    return JsonResponse({'assuntos': assuntos_list})

def get_assuntos(request, disciplina_id):
    assuntos = Assunto.objects.filter(disciplina_id=disciplina_id).order_by('nome')
    data = [{"id": a.id, "nome": a.nome} for a in assuntos]
    return JsonResponse(data, safe=False)

def get_assuntos(request, disciplina_id):
    assuntos = Assunto.objects.filter(disciplina_id=disciplina_id).order_by('nome')
    data = [{"id": a.id, "nome": a.nome} for a in assuntos]
    return JsonResponse(data, safe=False)

