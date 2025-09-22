# gestao/forms.py (ARQUIVO COMPLETO E REFATORADO)

from django import forms
from django.contrib.auth.models import User
from django.forms import inlineformset_factory

from .models import SolicitacaoExclusao
from gamificacao.models import (
    Conquista, GamificationSettings, Campanha, Avatar, Borda, Banner,
    TrilhaDeConquistas, TipoDesbloqueio, VariavelDoJogo, Condicao
)
from simulados.models import Simulado, StatusSimulado, NivelDificuldade
from questoes.models import Questao, Disciplina, Banca, Assunto, Instituicao
import json
from gamificacao.services import _obter_valor_variavel # <-- Importamos a função chave!
import inspect # <-- Precisamos desta biblioteca padrão

# =======================================================================
# FORMULÁRIOS DE CONFIGURAÇÃO E GESTÃO GERAL
# =======================================================================
class GamificationSettingsForm(forms.ModelForm):
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
    class Meta: model = User; fields = ['username', 'email', 'is_staff']; widgets = {'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'})}
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.fields['username'].disabled = True; self.fields['email'].disabled = True

class ExclusaoUsuarioForm(forms.Form):
    MOTIVO_CHOICES = [('', '---------'), ('TERMOS_DE_SERVICO', 'Violação dos Termos de Serviço'), ('CONDUTA_INADEQUADA', 'Conduta Inadequada / Abusiva'), ('INATIVIDADE', 'Conta Inativa por Longo Período'), ('SEGURANCA', 'Atividade Suspeita / Risco de Segurança'), ('SOLICITACAO_USUARIO', 'A Pedido do Próprio Usuário'), ('OUTRO', 'Outro (detalhar abaixo)')]
    motivo_predefinido = forms.ChoiceField(choices=MOTIVO_CHOICES, label="Selecione o motivo principal", widget=forms.Select(attrs={'class': 'form-select'}), required=True)
    justificativa = forms.CharField(label="Justificativa Detalhada", widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Forneça detalhes específicos sobre o motivo da exclusão.'}), required=False)

# =======================================================================
# FORMULÁRIOS DE ITENS (SIMULADOS E RECOMPENSAS)
# =======================================================================
class SimuladoForm(forms.ModelForm):
    class Meta: model = Simulado; fields = ['nome', 'questoes']
    questoes = forms.ModelMultipleChoiceField(queryset=Questao.objects.all(), widget=forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'tom-select-questoes'}), label="Questões do Simulado", required=False)
    banca = forms.ModelChoiceField(queryset=Banca.objects.all().order_by('nome'), label="Banca", widget=forms.Select(attrs={'class': 'form-select'}), required=True)
    disciplina = forms.ModelChoiceField(queryset=Disciplina.objects.all().order_by('nome'), label="Disciplina (opcional)", widget=forms.Select(attrs={'class': 'form-select'}), required=False)
    assunto = forms.ModelChoiceField(queryset=Assunto.objects.none(), label="Assunto", widget=forms.Select(attrs={'class': 'form-select'}), required=True)
    instituicao = forms.ModelChoiceField(queryset=Instituicao.objects.all().order_by('nome'), label="Instituição (opcional)", widget=forms.Select(attrs={'class': 'form-select'}), required=False)
    def __init__(self, *args, **kwargs):
        fields_to_show = kwargs.pop('fields_to_show', None)
        super().__init__(*args, **kwargs)
        if 'disciplina' in self.data:
            try: disciplina_id = int(self.data.get('disciplina')); self.fields['assunto'].queryset = Assunto.objects.filter(disciplina_id=disciplina_id).order_by('nome')
            except (ValueError, TypeError): pass
        if fields_to_show is not None:
            allowed = set(fields_to_show); existing = set(self.fields.keys())
            for field_name in existing - allowed: self.fields.pop(field_name)

class SimuladoMetaForm(forms.ModelForm):
    class Meta: model = Simulado; fields = ['nome', 'status', 'dificuldade']; widgets = {'nome': forms.TextInput(attrs={'class': 'form-control'}),'status': forms.Select(attrs={'class': 'form-select'}),'dificuldade': forms.Select(attrs={'class': 'form-select'})}

class SimuladoWizardForm(forms.Form):
    nome = forms.CharField(label="Nome do Simulado", max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Simulado de Direito Constitucional - FGV'}))
    dificuldade = forms.ChoiceField(choices=NivelDificuldade.choices, label="Nível de Dificuldade", widget=forms.Select(attrs={'class': 'form-select'}), initial=NivelDificuldade.MEDIO, required=True)
    disciplinas = forms.ModelMultipleChoiceField(queryset=Disciplina.objects.all().order_by('nome'), widget=forms.SelectMultiple(), required=False)
    assuntos = forms.ModelMultipleChoiceField(queryset=Assunto.objects.none(), widget=forms.SelectMultiple(), required=False)
    bancas = forms.ModelMultipleChoiceField(queryset=Banca.objects.all().order_by('nome'), widget=forms.SelectMultiple(), required=False)
    instituicoes = forms.ModelMultipleChoiceField(queryset=Instituicao.objects.all().order_by('nome'), widget=forms.SelectMultiple(), required=False)
    anos = forms.MultipleChoiceField(choices=[], widget=forms.SelectMultiple(), required=False)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        anos_disponiveis = Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano')
        self.fields['anos'].choices = [(ano, ano) for ano in anos_disponiveis]
        if 'disciplinas' in self.data:
            try: disciplina_ids = self.data.getlist('disciplinas'); self.fields['assuntos'].queryset = Assunto.objects.filter(disciplina_id__in=disciplina_ids).order_by('nome')
            except (ValueError, TypeError): pass

# gestao/forms.py (Apenas a classe RecompensaBaseForm na íntegra)

class RecompensaBaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        tipos_essenciais = ['NIVEL', 'CONQUISTA', 'EVENTO', 'CAMPANHA', 'LOJA']
        tipos_existentes = set(TipoDesbloqueio.objects.values_list('nome', flat=True))
        tipos_para_criar = [TipoDesbloqueio(nome=chave) for chave in tipos_essenciais if chave not in tipos_existentes]
        if tipos_para_criar:
            TipoDesbloqueio.objects.bulk_create(tipos_para_criar)
        super().__init__(*args, **kwargs)
        self.fields['conquista_necessaria'].queryset = Conquista.objects.all().order_by('nome')
        self.fields['conquista_necessaria'].required = False
        self.fields['preco_moedas'].required = False
        self.fields['nivel_necessario'].required = False

    class Meta:
        fields = ['nome', 'descricao', 'imagem', 'raridade', 'tipos_desbloqueio', 'nivel_necessario', 'conquista_necessaria', 'preco_moedas']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'imagem': forms.FileInput(attrs={'class': 'form-control'}),
            'raridade': forms.Select(attrs={'class': 'form-select'}),
            
            # =======================================================================
            # CORREÇÃO DEFINITIVA: Voltando para CheckboxSelectMultiple
            # Este é o widget correto para renderizar múltiplos checkboxes.
            # =======================================================================
            'tipos_desbloqueio': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            # =======================================================================
            
            'nivel_necessario': forms.NumberInput(attrs={'class': 'form-control'}),
            'conquista_necessaria': forms.Select(attrs={'class': 'form-select'}),
            'preco_moedas': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = { 'tipos_desbloqueio': 'Formas de Desbloqueio' }

    def clean(self):
        # A lógica de validação robusta que já implementamos continua perfeita.
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
        if 'CONQUISTA' in tipos_desbloqueio_chaves:
            conquista = cleaned_data.get('conquista_necessaria')
            if not conquista:
                self.add_error('conquista_necessaria', 'Se o desbloqueio é por conquista, este campo é obrigatório.')
        else:
            cleaned_data['conquista_necessaria'] = None
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
# FORMULÁRIOS DE TRILHAS, CONQUISTAS E CONDIÇÕES (FLUXO NOVO E UNIFICADO)
# =======================================================================
class TrilhaDeConquistasForm(forms.ModelForm):
    class Meta:
        model = TrilhaDeConquistas
        fields = ['nome', 'descricao', 'icone', 'ordem']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: fas fa-road'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ConquistaForm(forms.ModelForm):
    # Campos para recompensas diretas (sem alterações)
    recompensa_xp = forms.IntegerField(label="XP Extra", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    recompensa_moedas = forms.IntegerField(label="Moedas Extras", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    recompensa_avatares = forms.ModelMultipleChoiceField(
        queryset=Avatar.objects.all(), 
        required=False,
        label="Avatares",
        widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'})
    )
    recompensa_bordas = forms.ModelMultipleChoiceField(
        queryset=Borda.objects.all(), 
        required=False,
        label="Bordas",
        widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'})
    )
    recompensa_banners = forms.ModelMultipleChoiceField(
        queryset=Banner.objects.all(), 
        required=False,
        label="Banners",
        widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'})
    )

    class Meta:
        model = Conquista
        fields = ['nome', 'descricao', 'icone', 'cor', 'is_secreta', 'pre_requisitos']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: fas fa-fire'}),
            'cor': forms.TextInput(attrs={'class': 'form-control', 'type': 'color', 'style': 'width: 100px;'}),
            'is_secreta': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'pre_requisitos': forms.SelectMultiple(attrs={'class': 'form-select tom-select'}),
        }

    def __init__(self, *args, **kwargs):
        trilha = kwargs.pop('trilha', None)
        super().__init__(*args, **kwargs)

        # =======================================================================
        # CORREÇÃO DA COR:
        # Garante que o campo de cor sempre tenha um valor hexadecimal válido
        # para novas conquistas, evitando o aviso do navegador.
        # =======================================================================
        if not self.instance.pk and not self.initial.get('cor'):
            self.initial['cor'] = '#0D6EFD'  # Define um azul padrão do Bootstrap como cor inicial
        # =======================================================================

        if trilha:
            queryset = Conquista.objects.filter(trilha=trilha)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            self.fields['pre_requisitos'].queryset = queryset
            
        if self.instance and self.instance.pk and self.instance.recompensas:
            recompensas = self.instance.recompensas
            self.fields['recompensa_xp'].initial = recompensas.get('xp')
            self.fields['recompensa_moedas'].initial = recompensas.get('moedas')
            self.fields['recompensa_avatares'].initial = Avatar.objects.filter(id__in=recompensas.get('avatares', []))
            self.fields['recompensa_bordas'].initial = Borda.objects.filter(id__in=recompensas.get('bordas', []))
            self.fields['recompensa_banners'].initial = Banner.objects.filter(id__in=recompensas.get('banners', []))


CondicaoFormSet = inlineformset_factory(
    parent_model=Conquista, 
    model=Condicao,
    fields=('variavel', 'operador', 'valor'),
    extra=1,
    can_delete=True,
    widgets={
        'variavel': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        'operador': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        'valor': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
    }
)

class VariavelDoJogoForm(forms.ModelForm):
    # =======================================================================
    # MUDANÇA PRINCIPAL: Transformar o campo 'chave' em um ChoiceField
    # =======================================================================
    chave = forms.ChoiceField(
        label="Chave do Sistema",
        help_text="Selecione a lógica pré-programada que esta variável irá usar.",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = VariavelDoJogo
        fields = ['nome_exibicao', 'chave', 'descricao']
        widgets = {
            'nome_exibicao': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # --- LÓGICA DINÂMICA PARA POPULAR AS OPÇÕES ---
        # 1. Pega todas as chaves já implementadas no services.py
        #    (Esta é uma técnica avançada de introspecção de código)
        codigo_fonte = inspect.getsource(_obter_valor_variavel)
        chaves_implementadas = [line.split("'")[1] for line in codigo_fonte.split('\n') if "if chave_variavel ==" in line]

        # 2. Pega todas as chaves que já estão cadastradas no banco
        chaves_cadastradas = set(VariavelDoJogo.objects.values_list('chave', flat=True))
        
        # 3. Oferece apenas as chaves que foram implementadas mas AINDA NÃO foram cadastradas
        opcoes_disponiveis = [(chave, chave) for chave in chaves_implementadas if chave not in chaves_cadastradas]

        # Se estiver editando uma variável existente, adiciona a chave atual à lista de opções
        if self.instance and self.instance.pk:
            opcoes_disponiveis.insert(0, (self.instance.chave, self.instance.chave))
            
        self.fields['chave'].choices = opcoes_disponiveis
        
# =======================================================================
# FORMULÁRIOS DE CAMPANHAS
# =======================================================================
class CampanhaForm(forms.ModelForm):
    class Meta:
        model = Campanha
        fields = ['nome', 'ativo', 'gatilho', 'data_inicio', 'data_fim', 'tipo_recorrencia']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'gatilho': forms.Select(attrs={'class': 'form-select', 'id': 'id_gatilho_select'}),
            
            # =======================================================================
            # CORREÇÃO PRINCIPAL AQUI:
            # Usamos um widget específico para o formato correto do HTML5.
            # O Django se encarregará de formatar a data de 'DD/MM/YYYY' para 'YYYY-MM-DDTHH:MM'.
            # =======================================================================
            'data_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'data_fim': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            # =======================================================================
            
            'tipo_recorrencia': forms.Select(attrs={'class': 'form-select'}),
        }
    
    # Adicionamos um __init__ para garantir que os campos de data não sejam obrigatórios
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_fim'].required = False

# =======================================================================
# FORMULÁRIO DE CONCESSÃO MANUAL
# =======================================================================
class ConcessaoManualForm(forms.Form):
    TIPO_RECOMPENSA_CHOICES = [('', '---------'), ('MOEDAS', 'Moedas (Fragmentos de Conhecimento)'), ('AVATAR', 'Avatar'), ('BORDA', 'Borda'), ('BANNER', 'Banner')]
    usuario = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True, is_staff=False).select_related('userprofile'), label="Usuário", widget=forms.Select(attrs={'class': 'form-select tom-select-user'}), help_text="Selecione o usuário que receberá a recompensa.")
    tipo_recompensa = forms.ChoiceField(choices=TIPO_RECOMPENSA_CHOICES, label="Tipo de Recompensa", widget=forms.Select(attrs={'class': 'form-select'}))
    quantidade_moedas = forms.IntegerField(label="Quantidade de Moedas", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    avatar = forms.ModelChoiceField(queryset=Avatar.objects.all().order_by('nome'), label="Avatar Específico", required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    borda = forms.ModelChoiceField(queryset=Borda.objects.all().order_by('nome'), label="Borda Específica", required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    banner = forms.ModelChoiceField(queryset=Banner.objects.all().order_by('nome'), label="Banner Específico", required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    justificativa = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), help_text="Motivo da concessão (ex: prêmio de evento, correção de erro, etc.). Ficará registrado nos logs.")

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_recompensa')
        if tipo == 'MOEDAS' and not cleaned_data.get('quantidade_moedas'): self.add_error('quantidade_moedas', 'Este campo é obrigatório.')
        elif tipo == 'AVATAR' and not cleaned_data.get('avatar'): self.add_error('avatar', 'Este campo é obrigatório.')
        elif tipo == 'BORDA' and not cleaned_data.get('borda'): self.add_error('borda', 'Este campo é obrigatório.')
        elif tipo == 'BANNER' and not cleaned_data.get('banner'): self.add_error('banner', 'Este campo é obrigatório.')
        return cleaned_data