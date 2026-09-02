# Publicar no Streamlit Community Cloud

O app está pronto para subir. Falta **uma coisa que só você pode fazer**:
criar um Postgres na nuvem. O Streamlit Cloud roda o Python, mas não
oferece banco de dados.

---

## Antes de começar: o que muda no Community Cloud

A `ARQUITETURA-lavacar-streamlit.md` (seção 2.1) recomenda **não** usar o
Community Cloud, e vale saber o que você está aceitando:

| | Community Cloud (grátis) | VM Oracle da arquitetura |
|---|---|---|
| Custo | R$ 0 | R$ 0 |
| Cold start | dorme depois de ~7 dias sem visita; primeira carga leva ~30s | nunca dorme |
| Latência | servidor nos EUA, ~130 ms por clique | São Paulo, ~10 ms |
| Banco | externo, por sua conta | Postgres na mesma máquina |
| Landing SEO | não hospeda (é Nginx) | hospeda |
| Trabalho para subir | 10 minutos | uma tarde |

Para um lava car de bairro o cold start é o ponto sensível: o cliente
clica no link do WhatsApp às 21h e encara tela branca por meio minuto.
Como primeiro ar, para validar com o Leite, está ótimo. Quando virar o
canal de venda de verdade, a VM da Oracle é o passo seguinte — e nada do
código muda, só o lugar onde roda.

---

## 1. Criar o banco (5 min)

Qualquer Postgres 14+ com internet serve. O mais rápido é o
[Neon](https://neon.tech) no plano grátis:

1. Crie um projeto, região **AWS São Paulo (sa-east-1)** se disponível.
2. Copie a *connection string*. Ela tem esta cara:

```
postgresql://usuario:senha@ep-algo-123.sa-east-1.aws.neon.tech/neondb?sslmode=require
```

O app cria as tabelas e o catálogo sozinho no primeiro acesso — schema e
seed são idempotentes e rodam a cada boot sem estragar nada. Não precisa
rodar `psql`.

> Supabase, Railway e Render também servem. Só evite banco sem SSL.

## 2. Subir o app (3 min)

1. Entre em [share.streamlit.io](https://share.streamlit.io) com a conta
   do GitHub que tem acesso ao repositório.
2. **New app** → repositório `mondragon-data-services/LeitCar`, branch
   `main`, arquivo principal `app.py`.
3. Em **Advanced settings**, escolha **Python 3.12** e cole os secrets
   (o conteúdo abaixo, com seus valores).
4. **Deploy**.

## 3. Secrets

Cole em *Advanced settings → Secrets*, ou depois em *Settings → Secrets*.
É o mesmo formato do `.streamlit/secrets.toml`, que **não** vai para o
repositório.

```toml
[connections.postgresql]
url = "postgresql://usuario:senha@host.neon.tech/neondb?sslmode=require"

[admin]
senha = "escolha-uma-senha-forte"

[loja]
nome = "Leite Estética Automotiva"
telefone = "14998904665"
endereco = "Duartina - SP"
cidade = "Duartina"
chamada = "Lavagem, detalhamento e higienização com acabamento de loja especializada."
url_publica = "https://SEU-APP.streamlit.app"
url_site = "https://SEU-APP.streamlit.app"

# Deixe a chave vazia para não cobrar nada (pagamento na entrega).
[pix]
chave = ""
nome = "LEITE ESTETICA AUTOMOTIVA"
cidade = "DUARTINA"
sinal_centavos = 2000
centavos_unicos = true
```

Depois do primeiro deploy você descobre a URL do app. Volte nos secrets e
corrija `url_publica` — é ela que vai no link do comprovante que o cliente
recebe no WhatsApp.

## 4. Carregar as fotos (1 min)

O banco novo nasce sem galeria. As 27 fotos originais estão versionadas em
`fotos/`, então:

1. Abra `https://SEU-APP.streamlit.app/?area=admin` e entre com a senha.
2. **Portfólio** → **Importar tudo da pasta `fotos/`**.
3. Ajuste legendas e ordem se quiser.

Dali em diante o upload pelo admin é o caminho normal.

---

## Por que as fotos aguentam o redeploy

O disco do Community Cloud é efêmero: a cada deploy ou reinício, tudo que
foi gravado em `static/` desaparece. Se as fotos morassem só no disco, a
galeria voltaria vazia toda vez que o Leite subisse uma foto nova e o app
reiniciasse.

Por isso os bytes de cada foto ficam **no Postgres** (`portfolio.imagem` e
`portfolio.miniatura`), e o disco é só um cache: quando a vitrine percebe
que falta um arquivo, `db.materializar_fotos()` reescreve a partir do
banco. Isso foi testado apagando `static/portfolio/` inteiro — na carga
seguinte as 27 fotos voltaram sozinhas.

O custo é uns 250 KB por foto no banco. Para um portfólio de lava car,
irrelevante.

## O que não vai junto

- **A landing estática do SEO** (`landing/`) precisa de Nginx e fica de
  fora. Enquanto isso o app não é indexável pelo Google — é o problema da
  seção 2.5 da arquitetura, que só se resolve com a VM. Se quiser SEO
  antes disso, publique o HTML gerado em qualquer host estático grátis
  (GitHub Pages, Netlify) apontando o botão "Agendar agora" para o app.
- **O `docker-compose.yml`** continua no repositório, para desenvolvimento
  local. O Streamlit Cloud ignora.

## Rodar local continua igual

```
docker compose up -d
```

Nada do que foi feito para a nuvem quebrou o ambiente local: o mesmo
código lê `DATABASE_URL` (Docker) ou os secrets (nuvem).
