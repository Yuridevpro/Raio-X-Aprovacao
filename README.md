# Raio-X da Aprovação - Plataforma Inteligente de Preparação para Concursos

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)![Django](https://img.shields.io/badge/Django-4.2-092E20?style=for-the-badge&logo=django)![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql)![AWS S3](https://img.shields.io/badge/AWS_S3-569A31?style=for-the-badge&logo=amazon-aws)![Deployment](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render)

O **Raio-X da Aprovação** é uma plataforma web completa, segura e de alto desempenho, desenvolvida em Django, projetada para otimizar a preparação de candidatos para concursos públicos. A aplicação oferece um ambiente robusto para praticar com um vasto banco de questões, analisar o desempenho através de dashboards interativos e gerenciar todo o conteúdo com um painel de gestão avançado e seguro.

## 🚀 Demonstração Ao Vivo

Acesse a aplicação em produção no seguinte link:

### **[https://raio-x-aprovacao-1.onrender.com](https://raio-x-aprovacao-1.onrender.com)**

> **Nota:** A aplicação está hospedada no plano gratuito do Render. O primeiro acesso pode levar alguns segundos para carregar enquanto o serviço é inicializado ("cold start").

---

## ✨ Funcionalidades Principais

A plataforma é dividida em módulos que atendem tanto aos estudantes quanto aos administradores, garantindo uma experiência completa e segura.

### Para Estudantes:
*   **Banco de Questões Completo**: Acesso a milhares de questões com filtros avançados por disciplina, assunto, banca, instituição e ano.
*   **Dashboard de Desempenho**: Análise visual e detalhada do progresso, com gráficos de acertos/erros, desempenho por disciplina e por banca.
*   **Sistema de Prática Inteligente**: Resolva questões e receba feedback imediato, com gabarito e explicações detalhadas.
*   **Interação Social**: Comente, curta e discuta as questões com outros usuários.
*   **Personalização**: Favorite questões, salve filtros customizados para sessões de estudo futuras e gerencie seu perfil.
*   **Report de Erros**: Contribua com a qualidade da plataforma notificando erros nas questões diretamente para a equipe de gestão.

### Para a Equipe de Gestão (Painel de Gestão):
*   **CRUD Completo de Questões**: Gerenciamento total do banco de questões com um editor de texto rico (Tiptap.js).
*   **Lixeira Inteligente (Soft-Delete)**: Questões são movidas para uma lixeira, permitindo restauração ou exclusão permanente após um período de segurança.
*   **Moderação de Conteúdo**: Painel centralizado para revisar e gerenciar notificações de erros reportados pelos usuários.
*   **Gerenciamento de Usuários**: Controle de permissões, visualização de usuários e um sistema de solicitação/aprovação para exclusão de contas.
*   **Auditoria e Rastreabilidade**: Um registro de atividades detalhado que monitora todas as ações críticas realizadas no painel.

---

## 🛡️ Destaques de Arquitetura e Segurança

Este projeto foi construído com uma forte ênfase em segurança, integridade de dados e boas práticas de desenvolvimento, implementando funcionalidades de nível empresarial.

*   **Sistema de Quórum para Superusuários**: Ações de altíssimo risco, como promover, rebaixar ou excluir um superusuário, exigem a aprovação de um quórum de outros superusuários, prevenindo ações maliciosas ou unilaterais.
*   **Integridade de Logs (Blockchain-Inspired)**: Cada registro de atividade no painel de gestão possui um hash criptográfico que leva em conta o hash do registro anterior, criando uma cadeia imutável que garante a integridade e a não-repudiação dos logs.
*   **Alertas Proativos com Django Signals**: Ações críticas, como tentativas de exclusão em massa que excedem um limite de segurança, disparam alertas em tempo real via e-mail para todos os superusuários.
*   **Transações Atômicas**: Operações críticas no banco de dados, como o cadastro de usuários, são envoltas em transações atômicas (`@transaction.atomic`), garantindo que a operação seja concluída por completo ou revertida, prevenindo estados inconsistentes de dados.
*   **Defesa em Profundidade**:
    *   **Rate Limiting**: Proteção contra ataques de força bruta e abuso de API com `django-ratelimit`.
    *   **Controle de Volume**: Limites rígidos no backend para ações em massa, prevenindo abuso de funcionalidades.
    *   **Segregação de Permissões**: Uma clara distinção entre as capacidades de `Usuários Comuns`, `Staff` e `Superusuários` em todas as camadas da aplicação.
*   **Gerenciamento de Mídia Seguro**: Upload de imagens de questões diretamente para um bucket **AWS S3**, isolando arquivos de usuários da infraestrutura principal da aplicação.

---

## 💻 Pilha Tecnológica (Technology Stack)

| Backend                                                                                                                                                                                           | Frontend                                                                                                                                                                                               | Infraestrutura                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" width="24"/> **Python 3.11**                                                                                | <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.svg" width="24"/> **HTML5**                                                                                           | <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg" width="24"/> **PostgreSQL**                                                     |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/django/django-plain.svg" width="24"/> **Django 4.2**                                                                                    | <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/css3/css3-original.svg" width="24"/> **CSS3**                                                                                              | <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/amazonwebservices/amazonwebservices-original.svg" width="24"/> **AWS S3** (Armazenamento de Mídia)                    |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/djangorest/djangorest-original.svg" width="24"/> **Django Rest Framework** <br/><sub>(Implicitamente, para APIs AJAX)</sub> | <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/bootstrap/bootstrap-original.svg" width="24"/> **Bootstrap 5.3**                                                                     | <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/render/render-original.svg" width="24"/> **Render** (Hospedagem)                                                        |
|                                                                                                                                                                                                   | <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.svg" width="24"/> **JavaScript (ES6+)**                                                                   | <img src="https://user-images.githubusercontent.com/1393946/205132019-53090623-453d-42b7-a068-23340f6b4a3a.svg" width="24"/> **WhiteNoise** (Serviço de Arquivos Estáticos) |
|                                                                                                                                                                                                   | <img src="https://user-images.githubusercontent.com/1393946/205132019-53090623-453d-42b7-a068-23340f6b4a3a.svg" width="24"/> **Chart.js & Tiptap.js** <br/><sub>(Gráficos e Editor de Texto)</sub> |                                                                                                                                                                                  |

---

## ⚙️ Configuração do Ambiente Local

Siga os passos abaixo para executar o projeto em sua máquina local.

### Pré-requisitos
*   Python 3.10+
*   PostgreSQL
*   Git

### Passos
1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-usuario/raio-x-aprovacao.git
    cd raio-x-aprovacao
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    *Primeiro, gere o arquivo `requirements.txt` no ambiente de produção e adicione-o ao seu repositório.*
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as variáveis de ambiente:**
    Crie um arquivo `.env` na raiz do projeto, baseado no `qconcurso/settings.py`. Preencha com suas credenciais locais:

    ```ini
    # .env

    # Configurações do Django
    SECRET_KEY='sua-chave-secreta-muito-forte-aqui'
    ENVIRONMENT='development' # Use 'development' para local
    DEBUG=True
    ALLOWED_HOSTS='127.0.0.1,localhost'

    # Configurações do Banco de Dados (PostgreSQL Local)
    DB_NAME='raiox_db'
    DB_USER='postgres'
    DB_PASSWORD='sua_senha_do_postgres'
    DB_HOST='localhost'
    DB_PORT='5432'

    # Configurações de E-mail (use o backend de console para dev local)
    # Ou configure um SMTP real (ex: Gmail com senha de app)
    EMAIL_HOST_USER='seu-email@gmail.com'
    EMAIL_HOST_PASSWORD='sua-senha-de-app'

    # Configurações da AWS S3 (Opcional para dev local, mas necessário para uploads)
    AWS_ACCESS_KEY_ID='seu_access_key'
    AWS_SECRET_ACCESS_KEY='seu_secret_access_key'
    AWS_STORAGE_BUCKET_NAME='seu-bucket-name'
    AWS_S3_REGION_NAME='sua-regiao-ex-us-east-1'
    ```

5.  **Execute as migrações do banco de dados:**
    ```bash
    python manage.py migrate
    ```

6.  **Crie um superusuário para acessar o painel de gestão:**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Inicie o servidor de desenvolvimento:**
    ```bash
    python manage.py runserver
    ```

Acesse [http://127.0.0.1:8000](http://127.0.0.1:8000) em seu navegador.

---

## 🗺️ Roadmap de Futuras Implementações

O projeto possui uma base sólida que permite a expansão para novas funcionalidades de alto valor:

*   [ ] **Autenticação de Dois Fatores (2FA)**: Implementar 2FA com `django-otp` para contas de `Staff` e `Superuser`, elevando a segurança a um novo patamar.
*   [ ] **Gamificação**: Introduzir elementos como conquistas, medalhas e sequências de dias de estudo ("streaks") para aumentar o engajamento dos usuários.
*   [ ] **Simulados e Cadernos de Estudo**: Permitir que os usuários criem simulados cronometrados e "cadernos de questões" (conjuntos de filtros salvos) para estudo focado.
*   [ ] **Testes Automatizados**: Desenvolver uma suíte de testes (com `pytest-django`) para garantir a estabilidade do código e facilitar futuras manutenções e refatorações.

---