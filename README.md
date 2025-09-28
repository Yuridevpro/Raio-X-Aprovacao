
# 🚀 Raio-X da Aprovação - Plataforma de Estudos Gamificada

Sistema web completo e robusto para preparação para concursos públicos e exames, combinando um vasto banco de questões com um sistema de gamificação avançado para motivar e engajar os estudantes em sua jornada de aprovação.

## ✨ Acesso à Plataforma

**Acesse a aplicação em produção no seguinte link:**
### [https://raio-x-aprovacao.onrender.com/](https://raio-x-aprovacao.onrender.com/)

![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento%20Ativo-blue)![Versão](https://img.shields.io/badge/Versão-1.0-blue)![Python](https://img.shields.io/badge/Python-3.x-blue)![Django](https://img.shields.io/badge/Django-5.x-darkgreen)![Database](https://img.shields.io/badge/Database-PostgreSQL-blueviolet)

---

## ⚙️ Início Rápido (Ambiente de Desenvolvimento)

### 1. Pré-requisitos
- Python 3.x
- Git
- PostgreSQL (Recomendado para simular o ambiente de produção)

### 2. Configuração do Ambiente
```bash
# Clone o repositório
git clone https://github.com/seu-usuario/raio-x-aprovacao.git
cd raio-x-aprovacao

# Crie e ative um ambiente virtual
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
```

### 3. Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto e preencha com as suas chaves. Use o exemplo abaixo como base.
```ini
# .env

# Configurações Gerais do Django
ENVIRONMENT='development'
SECRET_KEY='sua-chave-secreta-django-super-segura'
ALLOWED_HOSTS='127.0.0.1,localhost'

# Configurações do Banco de Dados (PostgreSQL)
DB_NAME='seu_db_name'
DB_USER='seu_db_user'
DB_PASSWORD='sua_db_password'
DB_HOST='localhost'
DB_PORT='5432'

# Chaves do Amazon S3 para armazenamento de mídia
AWS_ACCESS_KEY_ID='sua_aws_access_key'
AWS_SECRET_ACCESS_KEY='sua_aws_secret_key'
AWS_STORAGE_BUCKET_NAME='seu-bucket-name'
AWS_S3_REGION_NAME='sua-aws-region' # Ex: us-east-1

# Chaves do SendGrid para envio de e-mails
SENDGRID_API_KEY='sua_chave_api_do_sendgrid'
DEFAULT_FROM_EMAIL='seu-email-verificado@exemplo.com'

# Credenciais de Acesso Privilegiado ao Django Admin
# Usado pelo middleware para uma camada extra de segurança
SUPERUSER_ADMIN_USERNAME='admin_mestre'
SUPERUSER_ADMIN_PASSWORD='senha_mestra_super_secreta'
```

### 4. Banco de Dados e Execução
```bash
# Crie as migrações com base nos modelos
python manage.py makemigrations

# Aplique as migrações no banco de dados
python manage.py migrate

# (Opcional) Crie um superusuário para acessar o painel de gestão
python manage.py createsuperuser

# Inicie o servidor de desenvolvimento
python manage.py runserver
```

### 5. Acesso
Abra seu navegador e acesse: **http://127.0.0.1:8000/**

---

## ✨ Funcionalidades Principais

### 👨‍🎓 Para Alunos (Usuários)
- **Autenticação Segura:** Cadastro com confirmação por e-mail, login e fluxo completo de recuperação de senha.
- **Prática de Questões:** Resolva questões individuais com um sistema de filtros avançado (disciplina, assunto, banca, ano, etc.), com verificação de resposta em tempo real.
- **Simulados:** Crie simulados personalizados ou resolva simulados oficiais criados pela equipe de gestão. Acompanhe seu desempenho e histórico detalhado a cada sessão.
- **Dashboard de Desempenho:** Analise suas estatísticas de acertos e erros com gráficos e tabelas, filtrando por período, disciplina, banca e mais.
- **Interação Social:** Favorite questões, adicione comentários e interaja com a comunidade em cada questão.
- **Perfil Público:** Visualize seu progresso, conquistas, itens cosméticos equipados e histórico.

### 🎮 Sistema de Gamificação Completo
- **Progressão e Níveis:** Ganhe XP ao resolver questões e concluir simulados para subir de nível.
- **Economia Virtual:** Acumule "Fragmentos de Conhecimento" (moedas) para gastar na loja.
- **Streaks de Prática:** Mantenha a consistência nos estudos e seja recompensado por sequências diárias.
- **Trilhas de Conquistas:** Desbloqueie centenas de conquistas organizadas em trilhas e séries temáticas, com pré-requisitos e condições complexas.
- **Recompensas Cosméticas:** Personalize seu perfil com Avatares, Bordas e Banners de diferentes raridades.
- **Loja e Caixa de Recompensas:** Use suas moedas para comprar itens na loja ou resgate prêmios ganhos em sua "Câmara dos Tesouros".
- **Ranking Competitivo:** Dispute com outros usuários nos rankings Geral, Semanal e Mensal.
- **Campanhas e Eventos:** Participe de eventos sazonais com regras e prêmios exclusivos, baseados em um motor de regras data-driven.

### 🛠️ Para a Gestão (Staff & Admins)
- **Painel de Gestão Centralizado:** Um dashboard completo com as principais métricas da plataforma.
- **Gerenciamento de Conteúdo:** CRUD completo para Questões, Disciplinas, Bancas, Assuntos e Simulados Oficiais.
- **Lixeira (Soft Delete):** Sistema de exclusão segura para Questões e Logs de Atividade, com restauração e exclusão permanente controlada.
- **Gerenciamento de Usuários:** Ferramentas para listar, filtrar, editar permissões (staff) e remover usuários.
- **Sistema de Quórum:** Processos de segurança robustos que exigem aprovação de múltiplos superusuários para ações críticas como promover, rebaixar ou excluir um superusuário.
- **Painel de Moderação:** Interface para analisar e resolver denúncias de erros em questões e comentários inadequados.
- **Controle Total da Gamificação:** Crie e gerencie todos os aspectos do sistema de gamificação, desde as regras de XP até as Campanhas, Conquistas e itens da Loja, sem precisar de código.
- **Auditoria Completa:** Um registro detalhado e imutável de todas as ações importantes realizadas no painel de gestão, com sistema de arquivamento e exclusão segura por quórum.

---

## 🎯 Público-Alvo e Casos de Uso

### 📚 Concurseiros e Vestibulandos
- **Problema:** A dificuldade de encontrar uma plataforma centralizada, motivadora e com feedback claro sobre o progresso nos estudos.
- **Solução:** O Raio-X da Aprovação oferece um vasto banco de questões, simulados realistas e um sistema de gamificação que transforma a rotina de estudos em uma jornada engajante, incentivando a consistência e recompensando o esforço.

### 🏫 Cursinhos e Instituições de Ensino
- **Problema:** Falta de ferramentas modernas para acompanhar o desempenho dos alunos e criar conteúdo personalizado.
- **Solução:** A plataforma pode ser usada como uma ferramenta de apoio, onde professores (atuando como `staff`) podem criar simulados oficiais, monitorar o desempenho da turma através dos rankings e utilizar o painel de gestão para gerenciar o conteúdo.

---

## 🏛️ Arquitetura do Projeto

O sistema é modularizado em apps Django, cada um com uma responsabilidade clara:

- `usuarios`: Gerencia a autenticação (cadastro, login, etc.), perfis de usuário e a personalização de itens cosméticos (avatares, bordas).
- `questoes`: Define os modelos de dados centrais como `Questao`, `Disciplina`, `Banca`, `Assunto`, etc. É a base de todo o conteúdo de estudo.
- `pratica`: Controla a interação do usuário com questões individuais, incluindo a lógica de resposta, comentários e filtros.
- `simulados`: Engloba toda a funcionalidade de criação e resolução de simulados, tanto os oficiais quanto os gerados pelos usuários.
- `desempenho`: Fornece a lógica e as views para o dashboard de análise de desempenho do usuário.
- `gamificacao`: O coração da experiência de engajamento. Contém o motor de regras para XP, moedas, níveis, streaks, conquistas, rankings, loja e campanhas.
- `gestao`: Um backend completo e seguro para a administração da plataforma, exclusivo para membros da equipe (`staff`) e superusuários.

---

## 🔬 Tecnologias Utilizadas

- **Backend:** Python, Django, Gunicorn
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5
- **Banco de Dados:** PostgreSQL (Produção), SQLite3 (Desenvolvimento)
- **Armazenamento de Mídia:** Amazon S3
- **Envio de E-mails:** SendGrid
- **Infraestrutura (Produção):** Render (PaaS)




## 📬 Contato

**Yuri Silva**

- **LinkedIn:** [https://www.linkedin.com/in/yuri-silva-a5b9b3299](https://www.linkedin.com/in/yuri-silva-a5b9b3299)
- **GitHub:** [https://github.com/Yuridevpro/](https://github.com/Yuridevpro/)
- **E-mail:** yuridev524@gmail.com

---

**Versão:** 1.0 | **Status do Projeto:** ✅ Em Desenvolvimento Ativo
```