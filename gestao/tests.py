# gestao/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from faker import Faker
import json
from django.core import management

from questoes.models import Questao, Disciplina, Assunto, Banca
from gestao.models import LogAtividade, SolicitacaoExclusao
from usuarios.models import UserProfile

class GestaoViewsTestCase(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        """
        Configuração executada uma vez para toda a classe de testes.
        Cria uma base de usuários e conteúdo para ser usada nos testes.
        """
        fake = Faker('pt_BR')
        
        # --- Criar Usuários ---
        cls.superuser = User.objects.create_superuser('superadmin', 'su@test.com', 'password123')
        cls.staff_user = User.objects.create_user('staffmember', 'staff@test.com', 'password123', is_staff=True)
        cls.normal_user = User.objects.create_user('commonuser', 'user@test.com', 'password123')
        UserProfile.objects.create(user=cls.superuser, nome='Super', sobrenome='Admin')
        UserProfile.objects.create(user=cls.staff_user, nome='Staff', sobrenome='Member')
        UserProfile.objects.create(user=cls.normal_user, nome='Common', sobrenome='User')

        # --- Criar Conteúdo ---
        cls.disciplina = Disciplina.objects.create(nome="Direito de Teste")
        cls.banca = Banca.objects.create(nome="Banca de Teste")
        cls.assunto = Assunto.objects.create(disciplina=cls.disciplina, nome="Assunto de Teste")
        
        # Criar uma questão ativa
        cls.questao_ativa = Questao.objects.create(
            disciplina=cls.disciplina, assunto=cls.assunto, banca=cls.banca, ano=2023,
            enunciado="Enunciado da questão ativa.", alternativas={'A': '1', 'B': '2'}, gabarito='A',
            criada_por=cls.superuser
        )
        
        # Criar uma questão já na lixeira (soft-deleted)
        cls.questao_deletada = Questao.objects.create(
            disciplina=cls.disciplina, assunto=cls.assunto, banca=cls.banca, ano=2023,
            enunciado="Enunciado da questão deletada.", alternativas={'A': '1', 'B': '2'}, gabarito='A'
        )
        cls.questao_deletada.delete(user=cls.superuser) # Soft delete

    def setUp(self):
        """ Configuração executada antes de cada teste. """
        self.client = Client()
        self.superuser_client = Client()
        self.staff_client = Client()
        self.user_client = Client()
        
        self.superuser_client.login(username='superadmin', password='password123')
        self.staff_client.login(username='staffmember', password='password123')
        self.user_client.login(username='commonuser', password='password123')

    # ========================================================
    # TESTES DE ACESSO E PERMISSÃO
    # ========================================================
    
    def test_dashboard_acesso(self):
        """ Apenas staff e superusers podem acessar o dashboard de gestão. """
        response_su = self.superuser_client.get(reverse('gestao:dashboard'))
        self.assertEqual(response_su.status_code, 200)

        response_staff = self.staff_client.get(reverse('gestao:dashboard'))
        self.assertEqual(response_staff.status_code, 200)

        response_user = self.user_client.get(reverse('gestao:dashboard'))
        self.assertEqual(response_user.status_code, 302) # Redirecionado para login
        
    # ========================================================
    # TESTES DE CRUD DE QUESTÕES
    # ========================================================

    def test_listar_questoes_gestao(self):
        """ Verifica se a página de listagem de questões carrega e contém a questão ativa. """
        response = self.staff_client.get(reverse('gestao:listar_questoes'))
        self.assertEqual(response.status_code, 200)
        # =======================================================================
        # ✅ CORREÇÃO: Verificar pelo código da questão, que está visível na lista.
        # =======================================================================
        self.assertContains(response, self.questao_ativa.codigo)
        self.assertNotContains(response, self.questao_deletada.codigo)

    def test_criar_questao_view(self):
        """ Testa a criação de uma nova questão via POST. """
        data = {
            'disciplina': self.disciplina.id,
            'assunto': self.assunto.id,
            'banca': self.banca.id,
            'ano': 2024,
            'enunciado': '<h2>Novo Enunciado de Teste</h2>',
            'explicacao': '<p>Nova explicação de teste.</p>',
            'gabarito': 'A',
            'alternativa_a': 'Alt A', 'alternativa_b': 'Alt B', 'alternativa_c': 'Alt C', 'alternativa_d': 'Alt D',
        }
        response = self.staff_client.post(reverse('gestao:adicionar_questao'), data)
        self.assertEqual(response.status_code, 302) # Redireciona após sucesso
        self.assertTrue(Questao.objects.filter(enunciado__icontains='Novo Enunciado de Teste').exists())
        self.assertTrue(LogAtividade.objects.filter(acao=LogAtividade.Acao.QUESTAO_CRIADA).exists())

    def test_soft_delete_questao_ajax(self):
        """ Testa o soft delete de uma questão via chamada AJAX. """
        url = reverse('gestao:deletar_questao', args=[self.questao_ativa.id])
        response = self.staff_client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        self.questao_ativa.refresh_from_db()
        self.assertTrue(self.questao_ativa.is_deleted)
        self.assertIsNotNone(self.questao_ativa.deleted_at)

    # ========================================================
    # TESTES DA LIXEIRA
    # ========================================================

    def test_listar_questoes_deletadas(self):
        """ Verifica se a lixeira contém a questão deletada e não a ativa. """
        response = self.staff_client.get(reverse('gestao:listar_questoes_deletadas'))
        self.assertEqual(response.status_code, 200)
        # =======================================================================
        # ✅ CORREÇÃO: Verificar pelo código da questão, que está visível na lista.
        # =======================================================================
        self.assertContains(response, self.questao_deletada.codigo)
        self.assertNotContains(response, self.questao_ativa.codigo)
    
    def test_restaurar_questao_ajax(self):
        """ Testa a restauração de uma questão da lixeira. """
        url = reverse('gestao:restaurar_questao', args=[self.questao_deletada.id])
        response = self.staff_client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')

        self.questao_deletada.refresh_from_db()
        self.assertFalse(self.questao_deletada.is_deleted)

    def test_deletar_permanente_permissao(self):
        """ Apenas superusuários podem deletar permanentemente. """
        management.call_command('age_item', 'questao', self.questao_deletada.id, dias=30)
        
        url = reverse('gestao:deletar_questao_permanente', args=[self.questao_deletada.id])
        
        response_staff = self.staff_client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_staff.status_code, 302)
        
        response_su = self.superuser_client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_su.status_code, 200)
        self.assertEqual(response_su.json()['status'], 'success')
        self.assertFalse(Questao.all_objects.filter(id=self.questao_deletada.id).exists())

    # ========================================================
    # TESTES DE GERENCIAMENTO DE USUÁRIOS
    # ========================================================

    def test_listar_usuarios_acesso_superuser(self):
        """ Superuser vê todos os outros usuários (exceto ele mesmo). """
        response = self.superuser_client.get(reverse('gestao:listar_usuarios'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.staff_user.username)
        self.assertContains(response, self.normal_user.username)
        self.assertNotContains(response, self.superuser.username)

    def test_sugerir_exclusao_usuario_staff(self):
        """ Staff pode criar uma solicitação de exclusão para um usuário comum. """
        url = reverse('gestao:sugerir_exclusao_usuario', args=[self.normal_user.id])
        data = {'motivo_predefinido': 'CONDUTA_INADEQUADA', 'justificativa': 'Teste de sugestão.'}
        
        response = self.staff_client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(SolicitacaoExclusao.objects.filter(usuario_a_ser_excluido=self.normal_user, status='PENDENTE').exists())

    def test_aprovar_exclusao_usuario_superuser(self):
        """ Superuser pode aprovar uma solicitação e deletar o usuário. """
        solicitacao = SolicitacaoExclusao.objects.create(
            usuario_a_ser_excluido=self.normal_user,
            solicitado_por=self.staff_user,
            motivo='Teste'
        )
        url = reverse('gestao:aprovar_solicitacao_exclusao', args=[solicitacao.id])
        response = self.superuser_client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertFalse(User.objects.filter(id=self.normal_user.id).exists())