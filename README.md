# Confira Outras Ferramentas Desenvolvidas por Mim

Hub profissional em Flask para apresentar ferramentas, organizar categorias e gerenciar todo o conteúdo por uma área administrativa protegida.

## Recursos

- Página inicial premium com busca instantânea e filtros por categoria.
- Cards de ferramentas com imagem, descrição, tags, status e destaque.
- Página individual para cada ferramenta com recursos, versão, atualização, autor e link de acesso.
- Painel administrativo em `/admin`.
- Cadastro, edição, exclusão, duplicação, ordenação e ocultação de ferramentas.
- Criação, edição e exclusão segura de categorias.
- Tela `Editar site` para alterar textos públicos, link principal do site, rodapé e senha administrativa.
- Upload de imagem para ferramentas.
- Estatísticas de ferramentas, categorias, destaques e acessos.
- SQLite inicial, senha com hash, sessão, CSRF, validação e limite de tentativas de login.

## Instalar localmente

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
```

No macOS ou Linux:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Configurar administrador

Copie `.env.example` para `.env` e ajuste:

```env
SECRET_KEY=troque-por-uma-chave-grande
ADMIN_USERNAME=admin
ADMIN_PASSWORD=85518510
FORCE_HTTPS=0
```

Se nenhuma variável for definida, o primeiro administrador local será:

```text
Usuário: admin
Senha: 85518510
```

Troque isso antes de publicar.

## Executar

```bash
python app.py
```

Acesse:

```text
http://127.0.0.1:5000
```

Área administrativa:

```text
http://127.0.0.1:5000/admin
```

## Cadastrar ferramentas

1. Entre em `/admin`.
2. Clique em `Nova Ferramenta`.
3. Preencha nome, categoria, descrições, tags, imagem, link, versão e status.
4. Marque `Destaque`, `Novidade`, `Beta` ou `Esconder` quando necessário.
5. Salve e volte ao portal público.

## Editar ferramentas

No painel administrativo, use os botões de ação ao lado de cada ferramenta:

- lápis: editar;
- cópia: duplicar;
- lixeira: excluir.

## Editar o site

No painel administrativo, clique em `Editar site`.

Nessa tela você pode alterar:

- textos do topo, hero, ferramentas, categorias, sobre e rodapé;
- link principal exibido no final do site;
- texto do botão final;
- senha do administrador.

## Publicar no Render

O projeto já inclui `render.yaml` e `Procfile`.

1. Envie o repositório para o GitHub.
2. Entre no Render.
3. Crie um novo Web Service usando este repositório.
4. Use:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Configure as variáveis:
   - `SECRET_KEY`
   - `ADMIN_USERNAME`
   - `ADMIN_PASSWORD`
   - `FORCE_HTTPS=1`
6. Faça o deploy e abra a URL gerada.

## Estrutura

```text
app.py
database.py
requirements.txt
Procfile
render.yaml
.env.example
templates/
  admin/
static/
  css/
  js/
  images/
  uploads/
data/
```

## Produção

- Use HTTPS.
- Defina `SECRET_KEY` e `ADMIN_PASSWORD` no ambiente.
- Não envie `.env` nem banco SQLite com dados reais para o GitHub.
- Faça backup periódico da pasta `data/` se usar SQLite em produção.

## Rodapé

Desenvolvido por João Guilherme
