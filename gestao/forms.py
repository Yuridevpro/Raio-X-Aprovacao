# gestao/forms.py
from django import forms
from django.contrib.auth.models import User
from django.forms import inlineformset_factory

from .models import SolicitacaoExclusao
from gamificacao.models import (
    Conquista, GamificationSettings, Campanha, Avatar, Borda, Banner,
    TrilhaDeConquistas, TipoDesbloqueio, VariavelDoJogo, Condicao, SerieDeConquistas
)
from simulados.models import Simulado, StatusSimulado, NivelDificuldade
from questoes.models import Questao, Disciplina, Banca, Assunto, Instituicao
import json
from gamificacao.services import _obter_valor_variavel 
import inspect
from django.db.models import Max

# =======================================================================
# FORMULÁRIOS DE CONFIGURAÇÃO E GESTÃO GERAL
# =======================================================================

class GamificationSettingsForm(forms.ModelForm):
    """ Formulário para gerenciar as configurações globais de gamificação. """
    class Meta:
        model = GamificationSettings
        fields = '__all__'
        widgets = {
            'xp_por_acerto': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_por_erro': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_acerto_primeira_vez': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_acerto_redencao': forms.NumberInput(attrs={'class': 'form-control'}),
            'acertos_consecutivos_para_bonus': forms.NumberInput(attrs={'class': 'form-control'}),
            'bonus_multiplicador_acertos_consecutivos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'xp_bonus_meta_diaria': forms.NumberInput(attrs={'class': 'form-control'}),
            'meta_diaria_questoes': forms.NumberInput(attrs={'class': 'form-control'}),
            'habilitar_teto_xp_diario': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'teto_xp_diario': forms.NumberInput(attrs={'class': 'form-control'}),
            'cooldown_mesma_questao_horas': forms.NumberInput(attrs={'class': 'form-control'}),
            'tempo_minimo_entre_respostas_segundos': forms.NumberInput(attrs={'class': 'form-control'}),
            'cooldown_mesmo_simulado_horas': forms.NumberInput(attrs={'class': 'form-control'}),
            'usar_xp_dinamico_simulado': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'xp_dinamico_considera_erros': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'multiplicador_xp_simulado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'xp_base_simulado_concluido': forms.NumberInput(attrs={'class': 'form-control'}),
            'moedas_por_acerto': forms.NumberInput(attrs={'class': 'form-control'}),
            'moedas_por_meta_diaria': forms.NumberInput(attrs={'class': 'form-control'}),
            'moedas_por_conclusao_simulado': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class StaffUserForm(forms.ModelForm):
    """ Formulário para promover/rebaixar usuários a membros da equipe (staff). """
    class Meta: 
        model = User
        fields = ['username', 'email', 'is_staff']
        widgets = {'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'})}
    
    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs)
        # Campos de usuário e email são apenas para exibição, não editáveis
        self.fields['username'].disabled = True
        self.fields['email'].disabled = True

class ExclusaoUsuarioForm(forms.Form):
    """ Formulário para justificar a exclusão de um usuário. """
    MOTIVO_CHOICES = [('', '---------'), ('TERMOS_DE_SERVICO', 'Violação dos Termos de Serviço'), ('CONDUTA_INADEQUADA', 'Conduta Inadequada / Abusiva'), ('INATIVIDADE', 'Conta Inativa por Longo Período'), ('SEGURANCA', 'Atividade Suspeita / Risco de Segurança'), ('SOLICITACAO_USUARIO', 'A Pedido do Próprio Usuário'), ('OUTRO', 'Outro (detalhar abaixo)')]
    motivo_predefinido = forms.ChoiceField(choices=MOTIVO_CHOICES, label="Selecione o motivo principal", widget=forms.Select(attrs={'class': 'form-select'}), required=True)
    justificativa = forms.CharField(label="Justificativa Detalhada", widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Forneça detalhes específicos sobre o motivo da exclusão.'}), required=False)

# =======================================================================
# FORMULÁRIOS DE ITENS (SIMULADOS E RECOMPENSAS)
# =======================================================================

class SimuladoForm(forms.ModelForm):
    """ Formulário genérico para editar metadados de Simulados. """
    class Meta: 
        model = Simulado
        fields = ['nome', 'questoes']
    
    questoes = forms.ModelMultipleChoiceField(queryset=Questao.objects.all(), widget=forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'tom-select-questoes'}), label="Questões do Simulado", required=False)
    banca = forms.ModelChoiceField(queryset=Banca.objects.all().order_by('nome'), label="Banca", widget=forms.Select(attrs={'class': 'form-select'}), required=True)
    disciplina = forms.ModelChoiceField(queryset=Disciplina.objects.all().order_by('nome'), label="Disciplina (opcional)", widget=forms.Select(attrs={'class': 'form-select'}), required=False)
    assunto = forms.ModelChoiceField(queryset=Assunto.objects.none(), label="Assunto", widget=forms.Select(attrs={'class': 'form-select'}), required=True)
    instituicao = forms.ModelChoiceField(queryset=Instituicao.objects.all().order_by('nome'), label="Instituição (opcional)", widget=forms.Select(attrs={'class': 'form-select'}), required=False)
    
    def __init__(self, *args, **kwargs):
        # Permite mostrar apenas um subconjunto de campos dinamicamente
        fields_to_show = kwargs.pop('fields_to_show', None)
        super().__init__(*args, **kwargs)
        # Lógica para carregar assuntos dinamicamente com base na disciplina selecionada
        if 'disciplina' in self.data:
            try: 
                disciplina_id = int(self.data.get('disciplina'))
                self.fields['assunto'].queryset = Assunto.objects.filter(disciplina_id=disciplina_id).order_by('nome')
            except (ValueError, TypeError): 
                pass
        # Remove campos que não foram especificados em 'fields_to_show'
        if fields_to_show is not None:
            allowed = set(fields_to_show)
            existing = set(self.fields.keys())
            for field_name in existing - allowed: 
                self.fields.pop(field_name)

class SimuladoMetaForm(forms.ModelForm):
    """ Formulário específico para editar metadados de um Simulado via AJAX. """
    class Meta: 
        model = Simulado
        fields = ['nome', 'status', 'dificuldade']
        widgets = {'nome': forms.TextInput(attrs={'class': 'form-control'}),'status': forms.Select(attrs={'class': 'form-select'}),'dificuldade': forms.Select(attrs={'class': 'form-select'})}

class SimuladoWizardForm(forms.Form):
    """ Formulário para a primeira etapa de criação de um Simulado, definindo os filtros. """
    nome = forms.CharField(label="Nome do Simulado", max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Simulado de Direito Constitucional - FGV'}))
    dificuldade = forms.ChoiceField(choices=NivelDificuldade.choices, label="Nível de Dificuldade", widget=forms.Select(attrs={'class': 'form-select'}), initial=NivelDificuldade.MEDIO, required=True)
    disciplinas = forms.ModelMultipleChoiceField(queryset=Disciplina.objects.all().order_by('nome'), widget=forms.SelectMultiple(), required=False)
    assuntos = forms.ModelMultipleChoiceField(queryset=Assunto.objects.none(), widget=forms.SelectMultiple(), required=False)
    bancas = forms.ModelMultipleChoiceField(queryset=Banca.objects.all().order_by('nome'), widget=forms.SelectMultiple(), required=False)
    instituicoes = forms.ModelMultipleChoiceField(queryset=Instituicao.objects.all().order_by('nome'), widget=forms.SelectMultiple(), required=False)
    anos = forms.MultipleChoiceField(choices=[], widget=forms.SelectMultiple(), required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Popula dinamicamente as opções de anos com base nos anos existentes nas questões
        anos_disponiveis = Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano')
        self.fields['anos'].choices = [(ano, ano) for ano in anos_disponiveis]
        # Carrega assuntos dinamicamente se disciplinas forem pré-selecionadas
        if 'disciplinas' in self.data:
            try: 
                disciplina_ids = self.data.getlist('disciplinas')
                self.fields['assuntos'].queryset = Assunto.objects.filter(disciplina_id__in=disciplina_ids).order_by('nome')
            except (ValueError, TypeError): 
                pass

# gestao/forms.py

# gestao/forms.py

class RecompensaBaseForm(forms.ModelForm):
    """ Formulário base com lógica compartilhada para Avatares, Bordas e Banners. """
    def __init__(self, *args, **kwargs):
        # Garante que os tipos de desbloqueio essenciais existam no banco de dados
        tipos_essenciais = ['NIVEL', 'CONQUISTA', 'EVENTO', 'CAMPANHA', 'LOJA']
        tipos_existentes = set(TipoDesbloqueio.objects.values_list('nome', flat=True))
        tipos_para_criar = [TipoDesbloqueio(nome=chave) for chave in tipos_essenciais if chave not in tipos_existentes]
        if tipos_para_criar:
            TipoDesbloqueio.objects.bulk_create(tipos_para_criar)
        
        super().__init__(*args, **kwargs)

        # =======================================================================
        # INÍCIO DA CORREÇÃO: Filtrando o queryset para remover a opção "CONQUISTA"
        # Isso impede que o checkbox "Por Conquista" seja renderizado no template.
        # =======================================================================
        if 'tipos_desbloqueio' in self.fields:
            self.fields['tipos_desbloqueio'].queryset = TipoDesbloqueio.objects.exclude(nome='CONQUISTA')
        # =======================================================================
        # FIM DA CORREÇÃO
        # =======================================================================
        
        self.fields['preco_moedas'].required = False
        self.fields['nivel_necessario'].required = False

    class Meta:
        model = Avatar # Usa um modelo como base, será sobrescrito nas classes filhas
        fields = ['nome', 'descricao', 'imagem', 'raridade', 'tipos_desbloqueio', 'nivel_necessario', 'preco_moedas']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'imagem': forms.FileInput(attrs={'class': 'form-control'}),
            'raridade': forms.Select(attrs={'class': 'form-select'}),
            'tipos_desbloqueio': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'nivel_necessario': forms.NumberInput(attrs={'class': 'form-control'}),
            'preco_moedas': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = { 'tipos_desbloqueio': 'Formas de Desbloqueio' }
        help_texts = {
            'nome': 'O nome do item como aparecerá para o usuário.',
            'descricao': 'Um texto curto que aparece na loja e na coleção, explicando o que é o item.',
            'raridade': 'Define a cor e a importância do item. Itens mais raros são mais desejados.',
            'tipos_desbloqueio': 'Marque todas as formas que este item pode ser obtido. Campos adicionais aparecerão abaixo conforme a sua seleção.',
        }
    
    def clean(self):
        """ Validação condicional com base nos tipos de desbloqueio selecionados. """
        cleaned_data = super().clean()
        tipos_desbloqueio = cleaned_data.get('tipos_desbloqueio')
        if not tipos_desbloqueio:
            self.add_error('tipos_desbloqueio', 'Você deve selecionar pelo menos uma forma de desbloqueio.')
            return cleaned_data
        
        tipos_desbloqueio_chaves = [tipo.nome for tipo in tipos_desbloqueio]
        
        if 'LOJA' in tipos_desbloqueio_chaves:
            preco = cleaned_data.get('preco_moedas')
            if not preco or preco <= 0:
                self.add_error('preco_moedas', 'Se o item é comprável, o preço deve ser maior que zero.')
        else:
            cleaned_data['preco_moedas'] = None
            
        if 'NIVEL' in tipos_desbloqueio_chaves:
            nivel = cleaned_data.get('nivel_necessario')
            if not nivel:
                self.add_error('nivel_necessario', 'Se o desbloqueio é por nível, este campo é obrigatório.')
        else:
            cleaned_data['nivel_necessario'] = None
            
        return cleaned_data
    
class AvatarForm(RecompensaBaseForm):
    class Meta(RecompensaBaseForm.Meta):
        model = Avatar

class BordaForm(RecompensaBaseForm):
    class Meta(RecompensaBaseForm.Meta):
        model = Borda

class BannerForm(RecompensaBaseForm):
    class Meta(RecompensaBaseForm.Meta):
        model = Banner

# =======================================================================
# FORMULÁRIOS DE TRILHAS, CONQUISTAS E CONDIÇÕES
# =======================================================================

# gestao/forms.py

class TrilhaDeConquistasForm(forms.ModelForm):
    """
    Formulário para criar e editar Trilhas de Conquistas, com validação
    para garantir que o campo 'ordem' seja sempre único.
    """
    class Meta:
        model = TrilhaDeConquistas
        fields = ['nome', 'descricao', 'icone', 'ordem']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: fas fa-road'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'nome': 'O nome da categoria principal de conquistas. Ex: "Jornada do Conhecimento", "Mestre dos Simulados".',
            'icone': 'Use uma classe do Font Awesome para representar a trilha visualmente. Ex: "fas fa-road".',
        }
    
    def clean_ordem(self):
        """
        Validação customizada para o campo 'ordem'.
        Verifica se a ordem já está em uso por outra trilha.
        """
        ordem = self.cleaned_data.get('ordem')
        
        # Cria a consulta base para verificar duplicatas
        queryset = TrilhaDeConquistas.objects.filter(ordem=ordem)
        
        # Se estiver editando uma trilha existente (self.instance.pk existe),
        # devemos excluí-la da verificação para que ela não conflite consigo mesma.
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        # Se, após as exclusões, ainda existir alguma trilha com essa ordem, é um erro.
        if queryset.exists():
            trilha_existente = queryset.first()
            
            # Busca a próxima ordem livre para sugerir uma solução ao admin
            max_ordem = TrilhaDeConquistas.objects.all().aggregate(Max('ordem'))['ordem__max'] or 0
            proxima_ordem_sugerida = max_ordem + 1

            # Levanta o erro de validação com uma mensagem clara e útil
            raise forms.ValidationError(
                f"A ordem '{ordem}' já está em uso pela trilha '{trilha_existente.nome}'. "
                f"Por favor, utilize um número diferente. A próxima ordem livre sugerida é {proxima_ordem_sugerida}."
            )
            
        return ordem

class SerieDeConquistasForm(forms.ModelForm):
    """ Formulário para criar e editar Séries de Conquistas. """
    class Meta:
        model = SerieDeConquistas
        fields = ['nome', 'descricao', 'ordem']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'nome': 'O nome do agrupamento. Ex: "Jornada do Conhecimento", "Mestre dos Simulados".',
            'ordem': 'Um número menor aparecerá primeiro na lista de séries da trilha.',
        }

# =======================================================================
# FORMULÁRIO MODIFICADO: ConquistaForm
# =======================================================================
# gestao/forms.py
class ConquistaForm(forms.ModelForm):
    """ Formulário principal para criar e editar uma Conquista. """
    recompensa_xp = forms.IntegerField(label="XP Extra", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    recompensa_moedas = forms.IntegerField(label="Moedas Extras", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    recompensa_avatares = forms.ModelMultipleChoiceField(queryset=Avatar.objects.all(), required=False, label="Avatares", widget=forms.SelectMultiple(attrs={'class': 'd-none'}))
    recompensa_bordas = forms.ModelMultipleChoiceField(queryset=Borda.objects.all(), required=False, label="Bordas", widget=forms.SelectMultiple(attrs={'class': 'd-none'}))
    recompensa_banners = forms.ModelMultipleChoiceField(queryset=Banner.objects.all(), required=False, label="Banners", widget=forms.SelectMultiple(attrs={'class': 'd-none'}))
    
    class Meta:
        model = Conquista
        fields = ['nome', 'descricao', 'icone', 'cor', 'is_secreta', 'pre_requisitos', 'trilha', 'serie']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: fas fa-fire'}),
            'cor': forms.TextInput(attrs={'class': 'form-control form-control-color-text', 'type': 'text'}),
            'is_secreta': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'pre_requisitos': forms.SelectMultiple(attrs={'class': 'form-select tom-select-multiple'}),
            'trilha': forms.HiddenInput(), # Oculto, será gerenciado pela view
            'serie': forms.HiddenInput(),  # Oculto, será gerenciado pela view
        }
        help_texts = { 'is_secreta': 'Se marcado, a conquista não será visível para o usuário até que ele a desbloqueie.', 'pre_requisitos': 'O usuário precisa ter desbloqueado todas as conquistas selecionadas aqui ANTES de poder ganhar esta.'}

    def __init__(self, *args, **kwargs):
        # Parâmetros de contexto passados pela view
        self.trilha = kwargs.pop('trilha', None)
        self.serie = kwargs.pop('serie', None)
        self.previous_conquista = kwargs.pop('previous_conquista', None)

        super().__init__(*args, **kwargs)

        # 1. Configura o queryset dos pré-requisitos para mostrar apenas conquistas da mesma trilha
        if self.trilha:
            # =======================================================================
            # INÍCIO DA LÓGICA DE PRÉ-REQUISITOS APRIMORADA
            # =======================================================================
            # 1. Pega todas as conquistas individuais da trilha
            qs_individuais = Conquista.objects.filter(trilha=self.trilha, serie__isnull=True)

            # 2. Pega a ÚLTIMA conquista de cada série dentro da trilha
            series_da_trilha = SerieDeConquistas.objects.filter(trilha=self.trilha).prefetch_related('conquistas')
            ultimas_conquistas_de_series_ids = []
            for s in series_da_trilha:
                ultima = s.conquistas.order_by('-ordem_na_serie').first()
                if ultima:
                    ultimas_conquistas_de_series_ids.append(ultima.id)
            
            qs_ultimas_de_series = Conquista.objects.filter(id__in=ultimas_conquistas_de_series_ids)

            # 3. Combina os dois querysets para formar a lista final de pré-requisitos disponíveis
            queryset = qs_individuais | qs_ultimas_de_series
            # =======================================================================
            # FIM DA LÓGICA DE PRÉ-REQUISITOS APRIMORADA
            # =======================================================================

            if self.instance and self.instance.pk: 
                queryset = queryset.exclude(pk=self.instance.pk)
            # Aplica o queryset final e ordena para uma exibição consistente
            self.fields['pre_requisitos'].queryset = queryset.distinct().order_by('serie__nome', 'nome')
        
        # 2. Lógica para o fluxo de criação sequencial
        if self.serie:
            # Preenche os campos ocultos com os valores corretos
            self.fields['trilha'].initial = self.serie.trilha_id
            self.fields['serie'].initial = self.serie.id
            
            if self.previous_conquista:
                # É uma nova conquista na sequência
                self.instance.sequencia_automatica = True
                self.fields['pre_requisitos'].queryset = Conquista.objects.filter(pk=self.previous_conquista.pk)
                self.fields['pre_requisitos'].initial = [self.previous_conquista.pk]
                self.fields['pre_requisitos'].disabled = True
                self.fields['pre_requisitos'].help_text = "Pré-requisito definido automaticamente pela sequência da série."
                
                # Herda as condições para facilitar
                condicoes_herdadas = self.previous_conquista.condicoes.all()
                self.initial['condicoes'] = condicoes_herdadas

        # 3. Lógica para edição de uma conquista já em série
        elif self.instance.pk and self.instance.serie:
            self.fields['pre_requisitos'].disabled = True
            self.fields['pre_requisitos'].help_text = "Pré-requisito definido automaticamente pela sequência da série."

        # 4. Popula os campos de recompensa se a instância já existir
        if self.instance and self.instance.pk and self.instance.recompensas:
            recompensas = self.instance.recompensas
            self.fields['recompensa_xp'].initial = recompensas.get('xp')
            self.fields['recompensa_moedas'].initial = recompensas.get('moedas')
            self.fields['recompensa_avatares'].initial = Avatar.objects.filter(id__in=recompensas.get('avatares', []))
            self.fields['recompensa_bordas'].initial = Borda.objects.filter(id__in=recompensas.get('bordas', []))
            self.fields['recompensa_banners'].initial = Banner.objects.filter(id__in=recompensas.get('banners', []))

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Garante que trilha e série sejam salvas corretamente a partir do contexto
        if self.serie:
            instance.serie = self.serie
            instance.trilha = self.serie.trilha
        elif self.trilha:
            instance.trilha = self.trilha
            
        if commit:
            instance.save()
            self.save_m2m() # Salva o ManyToMany de pré-requisitos
        
        return instance

class CondicaoForm(forms.ModelForm):
    """ Formulário para uma única condição, com campos de contexto e widgets padronizados. """
    disciplina_contexto = forms.ModelChoiceField(queryset=Disciplina.objects.all().order_by('nome'), required=False, label="Filtrar por Disciplina", widget=forms.Select(attrs={'class': 'form-select form-select-sm mb-2 tom-select-single'}))
    banca_contexto = forms.ModelChoiceField(queryset=Banca.objects.all().order_by('nome'), required=False, label="Filtrar por Banca", widget=forms.Select(attrs={'class': 'form-select form-select-sm mb-2 tom-select-single'}))
    assunto_contexto = forms.ModelChoiceField(queryset=Assunto.objects.all().order_by('nome'), required=False, label="Filtrar por Assunto", widget=forms.Select(attrs={'class': 'form-select form-select-sm mb-2 tom-select-single'}))
    dificuldade_contexto = forms.ChoiceField(choices=[('', 'Qualquer Dificuldade')] + NivelDificuldade.choices, required=False, label="Filtrar por Dificuldade", widget=forms.Select(attrs={'class': 'form-select form-select-sm tom-select-single'}))

    class Meta:
        model = Condicao
        fields = ('variavel', 'operador', 'valor', 'disciplina_contexto', 'banca_contexto', 'assunto_contexto', 'dificuldade_contexto')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.contexto_json:
            contexto = self.instance.contexto_json
            try:
                if contexto.get('disciplina_id'): self.fields['disciplina_contexto'].initial = Disciplina.objects.get(pk=contexto['disciplina_id'])
                if contexto.get('banca_id'): self.fields['banca_contexto'].initial = Banca.objects.get(pk=contexto['banca_id'])
                if contexto.get('assunto_id'): self.fields['assunto_contexto'].initial = Assunto.objects.get(pk=contexto['assunto_id'])
                if contexto.get('dificuldade'): self.fields['dificuldade_contexto'].initial = contexto['dificuldade']
            except (Disciplina.DoesNotExist, Banca.DoesNotExist, Assunto.DoesNotExist): pass

    def save(self, commit=True):
        contexto = {}
        if disciplina := self.cleaned_data.get('disciplina_contexto'): contexto['disciplina_id'] = disciplina.id
        if banca := self.cleaned_data.get('banca_contexto'): contexto['banca_id'] = banca.id
        if assunto := self.cleaned_data.get('assunto_contexto'): contexto['assunto_id'] = assunto.id
        if dificuldade := self.cleaned_data.get('dificuldade_contexto'): contexto['dificuldade'] = dificuldade
        self.instance.contexto_json = contexto
        instance = super(forms.ModelForm, self).save(commit=False)
        if commit: instance.save()
        return instance

CondicaoFormSet = inlineformset_factory(
    Conquista, Condicao, form=CondicaoForm, fields=('variavel', 'operador', 'valor'),
    extra=1, can_delete=True,
    widgets={
        'variavel': forms.Select(attrs={'class': 'form-select form-select-sm tom-select-single'}),
        'operador': forms.Select(attrs={'class': 'form-select form-select-sm tom-select-single'}),
        'valor': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
    }
)


class VariavelDoJogoForm(forms.ModelForm):
    """ Formulário para criar/editar as variáveis, agora com widget padronizado. """
    chave = forms.ChoiceField(
        label="Chave do Sistema", 
        help_text="Selecione a lógica pré-programada que esta variável irá usar.", 
        # ATUALIZAÇÃO: Classe padronizada para TomSelect.
        widget=forms.Select(attrs={'class': 'form-select tom-select-single'})
    )

    class Meta:
        model = VariavelDoJogo
        fields = ['nome_exibicao', 'chave', 'descricao']
        widgets = {'nome_exibicao': forms.TextInput(attrs={'class': 'form-control'}), 'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        codigo_fonte = inspect.getsource(_obter_valor_variavel)
        chaves_implementadas = [line.split("'")[1] for line in codigo_fonte.split('\n') if "if chave_variavel ==" in line]
        chaves_cadastradas = set(VariavelDoJogo.objects.values_list('chave', flat=True))
        opcoes_disponiveis = [(chave, chave) for chave in chaves_implementadas if chave not in chaves_cadastradas]
        if self.instance and self.instance.pk:
            opcoes_disponiveis.insert(0, (self.instance.chave, self.instance.chave))
        self.fields['chave'].choices = opcoes_disponiveis
        
# =======================================================================
# FORMULÁRIOS DE CAMPANHAS
# =======================================================================

class CampanhaForm(forms.ModelForm):
    """
    Formulário para os dados gerais de uma Campanha, com widgets padronizados para TomSelect.
    """
    class Meta:
        model = Campanha
        fields = ['nome', 'ativo', 'gatilho', 'simulado_especifico', 'data_inicio', 'data_fim', 'tipo_recorrencia']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            # ATUALIZAÇÃO: Classe padronizada para TomSelect.
            'gatilho': forms.Select(attrs={'class': 'form-select tom-select-single', 'id': 'id_gatilho_select'}),
            'simulado_especifico': forms.Select(attrs={'class': 'form-select tom-select-single'}),
            'data_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'data_fim': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'tipo_recorrencia': forms.Select(attrs={'class': 'form-select tom-select-single'}),
        }
        help_texts = {
            'gatilho': 'O evento que fará o sistema verificar as condições desta campanha.',
            'simulado_especifico': 'Se o gatilho for "Completar um Simulado", você pode restringir a campanha a apenas UM simulado específico.',
            'data_fim': 'Deixe em branco para uma campanha sem data de término.',
            'tipo_recorrencia': 'Define com que frequência um usuário pode ganhar os prêmios desta campanha.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_fim'].required = False
        self.fields['simulado_especifico'].queryset = Simulado.objects.filter(is_oficial=True).order_by('-data_criacao')
        self.fields['simulado_especifico'].required = False
# =======================================================================
# FORMULÁRIO DE CONCESSÃO MANUAL
# =======================================================================

class ConcessaoManualForm(forms.Form):
    """ Formulário para concessão manual, agora com widgets padronizados. """
    TIPO_RECOMPENSA_CHOICES = [('', '---------'), ('MOEDAS', 'Moedas (Fragmentos de Conhecimento)'), ('AVATAR', 'Avatar'), ('BORDA', 'Borda'), ('BANNER', 'Banner')]
    
    usuario = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True, is_staff=False).select_related('userprofile'), label="Usuário", widget=forms.Select(attrs={'class': 'form-select tom-select-user'}), help_text="Selecione o usuário que receberá a recompensa.")
    # ATUALIZAÇÃO: Classe padronizada para TomSelect.
    tipo_recompensa = forms.ChoiceField(choices=TIPO_RECOMPENSA_CHOICES, label="Tipo de Recompensa", widget=forms.Select(attrs={'class': 'form-select tom-select-single'}))
    
    quantidade_moedas = forms.IntegerField(label="Quantidade de Moedas", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    # ATUALIZAÇÃO: Classe padronizada para TomSelect.
    avatar = forms.ModelChoiceField(queryset=Avatar.objects.all().order_by('nome'), label="Avatar Específico", required=False, widget=forms.Select(attrs={'class': 'form-select tom-select-single'}))
    borda = forms.ModelChoiceField(queryset=Borda.objects.all().order_by('nome'), label="Borda Específica", required=False, widget=forms.Select(attrs={'class': 'form-select tom-select-single'}))
    banner = forms.ModelChoiceField(queryset=Banner.objects.all().order_by('nome'), label="Banner Específico", required=False, widget=forms.Select(attrs={'class': 'form-select tom-select-single'}))
    
    justificativa = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), help_text="Motivo da concessão (ex: prêmio de evento, correção de erro, etc.). Ficará registrado nos logs.")

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_recompensa')
        if tipo == 'MOEDAS' and not cleaned_data.get('quantidade_moedas'): self.add_error('quantidade_moedas', 'Este campo é obrigatório.')
        elif tipo == 'AVATAR' and not cleaned_data.get('avatar'): self.add_error('avatar', 'Este campo é obrigatório.')
        elif tipo == 'BORDA' and not cleaned_data.get('borda'): self.add_error('borda', 'Este campo é obrigatório.')
        elif tipo == 'BANNER' and not cleaned_data.get('banner'): self.add_error('banner', 'Este campo é obrigatório.')
        return cleaned_data